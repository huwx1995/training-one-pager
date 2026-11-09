# Apple 芯片 Mac 构建

版本：0.1.0-beta.3。目标 macOS 14 及以上；目前只在一台开发 Mac 验证。没有 Developer ID 签名及 Apple 公证，产物仅供本机和受控内测验证，不能据此承诺所有 Mac 均可安装。

## 构建环境

需要 Apple 芯片 Mac、Python 3.12、Xcode Command Line Tools（clang、Swift）及系统 hdiutil。用户安装成品时不需要这些开发工具。

```sh
python3 -m venv .build-venv
.build-venv/bin/python -m pip install -r requirements-packaging.txt
.build-venv/bin/python packaging/macos/fetch_sources.py .build/upstream
.build-venv/bin/python packaging/macos/build_tools.py .build .build-venv/bin/cmake
.build-venv/bin/python packaging/macos/build_app.py .build .build/base-app
```

构建脚本只读取程序文件、明确列出的资源和官方固定版本源码。运行数据、用户模型、虚拟环境、开发日志及个人环境变量不进入基础应用。发布时应另用明确文件清单制作项目源码包，并提供所用上游对应源码及构建配置。

## 内置与外部条件

- 内置 Python、文档解析依赖、FFmpeg 8.1.2、ffprobe、whisper.cpp 1.7.6（CPU/Accelerate）和预编译 Vision OCR。
- FFmpeg 构建关闭网络、自动探测及 GPL/nonfree 选项，仅启用录音预处理所需格式和滤镜。应用通过独立进程调用音频工具。
- 基础应用不内置语音模型；发行组装脚本只接收显式指定且通过上游 SHA-1 校验的模型，制作内置模型的完整版，不收集用户数据。
- 未内置 LibreOffice。旧 DOC/PPT 需另装 LibreOffice，或先另存为 DOCX/PPTX；PPTX 原生图表仍可提取数据并使用本地预览回退。
- 中文字体使用系统已安装字体，没有复制系统字体文件。

## 安装版行为

双击应用后显示控制窗口并打开默认浏览器。应用优先使用本机 8765 端口；占用时换用其他端口。退出控制窗口时终止本机服务及其音频子进程；关闭浏览器标签不等于退出应用。

安装版数据位于用户的 `Library/Application Support/TrainingOnePager`。应用资源目录只读，不把上传副本写入应用包。每次启动不会继承开发环境中的模型密钥。

## 验证

```sh
.build-venv/bin/python packaging/macos/smoke_packaged.py '.build/base-app/培训一纸通.app/Contents/Resources/backend/onepager-backend'
.build-venv/bin/python packaging/macos/smoke_native.py '.build/base-app/培训一纸通.app'
```

这些检查使用合成材料，验证本机服务、解析、脱敏、本地生成、导出、内置工具及退出清理，不验证真实模型平台的生成质量和费用。

项目自身许可为 AGPL-3.0-only。第三方许可和确切版本来源见第三方说明、源码包及发行构建清单。Ad-hoc 签名只满足本机 arm64 加载要求，不代表 Developer ID 签名、公证或平台认证。

## HTTPS 证书策略资源

本构建使用的 Codex Python 运行时在 `ssl.py` 中明确加载 `codex-rejected-cas.pem`，用于拒绝信任 emSign ECC Root CA - G3。它是公开的根证书及拒绝信任标记，不是私钥或 API Key，也不是绕过 TLS 验证的文件。由于运行时会按名称加载它，直接从安装包删除会使建立 HTTPS 上下文时抛出 `FileNotFoundError`。本项目保留此资源及原有拒绝策略，并使用 certifi 证书包进行正常的 TLS 与主机名验证。若改用未经此补丁的 Python 构建运行时，应重新构建并验证 TLS 后再移除该资源。

制作安装包后还需运行冻结后端的 `--check-tls`，不携带凭据请求公开的模型服务地址；收到 HTTP 401 等响应说明 TLS 已建立，不代表真实 Key 验证成功。

## 完整版安装

完整版在只读应用资源中包含语音模型，用户无需另装模型。

组装：`python packaging/macos/assemble_release.py BUILD OUTPUT MANIFEST MODEL_FILE`。产物包含一个完整版 DMG，以及项目源码和配套上游源码。模型来源及许可见 speech-model.json 和 third_party/licenses/Whisper-LICENSE。

## 轻量版安装

轻量版从单独构建的基础应用组装：`python packaging/macos/assemble_lite.py BASE_APP OUTPUT`。它只保留文档解析需要的 Vision OCR，去掉 FFmpeg、Whisper 和语音模型，并在包内放置 `lite-edition.flag`。后端禁止录音接口，界面不提供录音入口。应用名、Bundle ID 和本机数据目录与完整版不同，可同时保留；它不覆盖现有完整版 DMG。
