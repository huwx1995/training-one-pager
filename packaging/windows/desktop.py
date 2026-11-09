"""Windows desktop launcher and local backend. No external credentials are inherited."""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser

_JOB_HANDLES = []
_MUTEX_HANDLE = None


def attach_lifetime_job():
    """All descendants terminate if the desktop or backend exits unexpectedly."""
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class BasicLimits(ctypes.Structure):
        _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                    ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                    ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                    ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]
    class IOCounts(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount',
            'OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
    class ExtendedLimits(ctypes.Structure):
        _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IOCounts),
                    ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                    ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = ExtendedLimits()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise ctypes.WinError(error)
    _JOB_HANDLES.append(handle)  # Keep open until process exit, including abrupt exit.


def sanitized_environment():
    allowed = {'SYSTEMROOT', 'WINDIR', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA', 'TEMP', 'TMP',
               'PATH', 'HOMEDRIVE', 'HOMEPATH', 'COMSPEC', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
               'PROGRAMW6432'}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    return environment


def check_tls(result_file):
    import certifi
    import ssl
    context = ssl.create_default_context(cafile=certifi.where())
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    Path(result_file).write_text(json.dumps({'tls_verified': True, 'credential_sent': False}), encoding='utf-8')


def serve(ready_file):
    attach_lifetime_job()
    for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'):
        os.environ.pop(key, None)
    from http.server import ThreadingHTTPServer
    import errno
    import server
    for port in [*range(8765, 8775), 0]:
        try:
            httpd = ThreadingHTTPServer(('127.0.0.1', port), server.Handler)
            break
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE and getattr(exc, 'winerror', None) != 10048:
                raise
    def stop_on_input():
        # The launcher owns the pipe. A stop request or a closed pipe ends service.
        try:
            sys.stdin.readline()
        finally:
            httpd.shutdown()
    threading.Thread(target=stop_on_input, daemon=True).start()
    ready = Path(ready_file)
    ready.parent.mkdir(parents=True, exist_ok=True)
    temporary = ready.with_suffix('.tmp')
    temporary.write_text(json.dumps({'url': f'http://127.0.0.1:{httpd.server_port}', 'pid': os.getpid()}), encoding='utf-8')
    temporary.replace(ready)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        # Explicitly clean before process teardown; open audio handles may require
        # stale-run cleanup next launch after a forced exit.
        import shutil
        shutil.rmtree(server.UPLOAD_DIR, ignore_errors=True)
        ready.unlink(missing_ok=True)


def claim_desktop_instance():
    global _MUTEX_HANDLE
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    ctypes.set_last_error(0)
    _MUTEX_HANDLE = kernel.CreateMutexW(None, False, 'TrainingOnePagerDesktop')
    if not _MUTEX_HANDLE:
        raise ctypes.WinError(ctypes.get_last_error())
    return ctypes.get_last_error() != 183


def launch():
    import tkinter as tk
    from tkinter import messagebox
    from app_paths import user_data_dir, resource_dir
    root = tk.Tk()
    root.title('培训一纸通')
    root.geometry('490x260')
    root.resizable(False, False)
    if not claim_desktop_instance():
        messagebox.showinfo('软件已打开', '培训一纸通已经在运行，请使用已有控制窗口打开工作台。')
        root.destroy()
        return
    status = tk.StringVar(value='正在启动，请稍候……')
    tk.Label(root, text='培训一纸通', font=('Microsoft YaHei', 20)).pack(pady=(24, 10))
    tk.Label(root, textvariable=status, wraplength=440).pack(pady=8)
    data = user_data_dir()
    data.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix='training-onepager-')
    ready = Path(temporary.name) / 'ready.json'
    process = None
    url = None
    closing = False
    open_button = tk.Button(root, text='打开工作台', state='disabled', command=lambda: webbrowser.open(url) if url else None)
    open_button.pack(pady=4)
    tk.Button(root, text='打开本机数据文件夹', command=lambda: os.startfile(data)).pack(pady=4)
    tk.Button(root, text='查看许可', command=lambda: os.startfile(resource_dir() / 'LICENSE.txt')).pack(pady=4)
    def finish_close(deadline):
        if process and process.poll() is None:
            if time.monotonic() < deadline:
                root.after(100, lambda: finish_close(deadline))
                return
            process.terminate()
        temporary.cleanup()
        root.destroy()
    def close():
        nonlocal closing
        if closing:
            return
        closing = True
        status.set('正在退出并清理本次材料……')
        open_button.config(state='disabled')
        if process and process.poll() is None:
            try:
                process.stdin.write('stop\n')
                process.stdin.flush()
            except (OSError, ValueError):
                pass
        finish_close(time.monotonic() + 15)
    tk.Button(root, text='退出', command=close).pack(pady=4)
    root.protocol('WM_DELETE_WINDOW', close)
    try:
        attach_lifetime_job()
        command = [str(Path(sys.executable).with_name('onepager-backend.exe')), '--backend', '--ready-file', str(ready)] if getattr(sys, 'frozen', False) else [sys.executable, str(Path(__file__).resolve()), '--backend', '--ready-file', str(ready)]
        process = subprocess.Popen(command, env=sanitized_environment(), stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True, creationflags=0x08000000)
    except Exception:
        messagebox.showerror('启动未完成', '无法启动本机服务。请确认已完整安装软件，且安全软件没有阻止运行。')
        temporary.cleanup()
        root.destroy()
        return
    deadline = time.monotonic() + 60
    def poll():
        nonlocal url
        if closing:
            return
        if ready.exists():
            payload = json.loads(ready.read_text(encoding='utf-8'))
            if payload.get('pid') != process.pid or not payload.get('url', '').startswith('http://127.0.0.1:'):
                close()
                return
            url = payload['url']
            status.set('工作台已在浏览器中打开。使用结束后，请在这里点击“退出”。')
            open_button.config(state='normal')
            webbrowser.open(url)
            return
        if process.poll() is not None or time.monotonic() > deadline:
            status.set('启动未完成，请退出后重试。若仍失败，请检查安全软件是否拦截。')
            return
        root.after(150, poll)
    root.after(100, poll)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', action='store_true')
    parser.add_argument('--ready-file')
    parser.add_argument('--check-tls-local', action='store_true')
    parser.add_argument('--result-file')
    args = parser.parse_args()
    if args.check_tls_local:
        if not args.result_file:
            parser.error('--result-file is required')
        check_tls(args.result_file)
    elif args.backend:
        if not args.ready_file:
            parser.error('--ready-file is required')
        serve(args.ready_file)
    else:
        launch()


if __name__ == '__main__':
    main()
