import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var window: NSWindow!
    var backend: Process?
    var timer: Timer?
    var address: URL?
    var servicePID: Int32?
    var status: NSTextField!
    var openButton: NSButton!
    var readyFile: URL!
    var temporary: URL!
    var logHandle: FileHandle?
    var shuttingDown = false
    var terminateSignal: DispatchSourceSignal?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "退出培训一纸通", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let item = NSMenuItem(); item.submenu = appMenu; menu.addItem(item); NSApp.mainMenu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 500, height: 290),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "培训一纸通"; window.delegate = self; window.center()
        let title = NSTextField(labelWithString: "培训一纸通")
        title.font = .boldSystemFont(ofSize: 25)
        status = NSTextField(wrappingLabelWithString: "正在启动本机工作台……")
        status.font = .systemFont(ofSize: 14)
        let detail = NSTextField(wrappingLabelWithString: "工作台在默认浏览器中打开。结束使用后，请在此退出应用。")
        detail.textColor = .secondaryLabelColor
        openButton = NSButton(title: "打开工作台", target: self, action: #selector(openWorkbench))
        openButton.bezelStyle = .rounded; openButton.isEnabled = false
        let data = NSButton(title: "打开数据文件夹", target: self, action: #selector(openData))
        let license = NSButton(title: "许可证与源码", target: self, action: #selector(openLicense))
        let quit = NSButton(title: "退出", target: NSApp, action: #selector(NSApplication.terminate(_:)))
        let buttons = NSStackView(views: [openButton, quit]); buttons.spacing = 12
        let links = NSStackView(views: [data, license]); links.spacing = 12
        let stack = NSStackView(views: [title, status, detail, buttons, links])
        stack.orientation = .vertical; stack.alignment = .leading; stack.spacing = 18
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 28),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -28),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 28)])
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        signal(SIGTERM, SIG_IGN)
        terminateSignal = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
        terminateSignal?.setEventHandler { NSApp.terminate(nil) }
        terminateSignal?.resume()
        startBackend()
    }
    var dataDirectory: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent(Bundle.main.bundleIdentifier == "org.trainingonepager.desktop.lite" ? "TrainingOnePagerLite" : "TrainingOnePager", isDirectory: true)
    }
    func startBackend() {
        do {
            temporary = FileManager.default.temporaryDirectory.appendingPathComponent("training-onepager-" + UUID().uuidString, isDirectory: true)
            try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            readyFile = temporary.appendingPathComponent("ready.json")
            let process = Process()
            process.executableURL = Bundle.main.resourceURL!.appendingPathComponent("backend/onepager-backend")
            process.arguments = ["--ready-file", readyFile.path]
            // Do not inherit private credentials or developer tool paths.
            process.environment = ["HOME": NSHomeDirectory(), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                "LANG": "zh_CN.UTF-8", "TMPDIR": NSTemporaryDirectory(),
                "ONEPAGER_DATA_DIR": dataDirectory.path,
                "SSL_CERT_FILE": Bundle.main.resourceURL!.appendingPathComponent("backend/_internal/certifi/cacert.pem").path]
            let log = temporary.appendingPathComponent("startup.log")
            FileManager.default.createFile(atPath: log.path, contents: nil, attributes: [.posixPermissions: 0o600])
            logHandle = try FileHandle(forWritingTo: log)
            process.standardOutput = logHandle; process.standardError = logHandle
            process.terminationHandler = { [weak self] child in
                DispatchQueue.main.async {
                    guard let self = self, !self.shuttingDown else { return }
                    self.timer?.invalidate(); self.openButton.isEnabled = false
                    self.status.stringValue = "工作台已停止（状态 \(child.terminationStatus)），请退出后重新打开。"
                }
            }
            try process.run(); backend = process
            var attempts = 0
            timer = Timer.scheduledTimer(withTimeInterval: 0.25, repeats: true) { [weak self] timer in
                guard let self = self else { timer.invalidate(); return }
                attempts += 1
                if let data = try? Data(contentsOf: self.readyFile),
                   let payload = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let value = payload["url"] as? String, let url = URL(string: value),
                   url.host == "127.0.0.1" {
                    if let pid = payload["pid"] as? Int { self.servicePID = Int32(pid) }
                    self.address = url; self.status.stringValue = "工作台正在本机运行。"
                    self.openButton.isEnabled = true; timer.invalidate()
                    if ProcessInfo.processInfo.environment["ONEPAGER_NO_BROWSER"] != "1" { self.openWorkbench() }
                } else if attempts >= 240 {
                    timer.invalidate(); self.status.stringValue = "启动等待超时，请退出后重试。"
                    if self.backend?.isRunning == true { self.backend?.terminate() }
                }
            }
        } catch { status.stringValue = "无法启动工作台，请检查应用是否完整，然后重新打开。" }
    }
    @objc func openWorkbench() { if let address = address { NSWorkspace.shared.open(address) } }
    @objc func openData() { NSWorkspace.shared.open(dataDirectory) }
    @objc func openLicense() { NSWorkspace.shared.open(Bundle.main.resourceURL!.appendingPathComponent("发行说明.txt")) }
    func windowShouldClose(_ sender: NSWindow) -> Bool { NSApp.terminate(nil); return false }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        shuttingDown = true; timer?.invalidate()
        if let pid = servicePID {
            _ = kill(-pid, SIGTERM)
        } else if let process = backend, process.isRunning {
            process.terminate()
        }
        cleanup()
        return .terminateNow
    }

    func cleanup() {
        try? logHandle?.close()
        if let temporary = temporary { try? FileManager.default.removeItem(at: temporary) }
    }
}
let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
