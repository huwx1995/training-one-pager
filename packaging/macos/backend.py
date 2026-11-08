"""Frozen local service managed by the native macOS launcher."""
import argparse
import json
import os
from pathlib import Path
import signal
import threading
from http.server import ThreadingHTTPServer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ready-file')
    parser.add_argument('--check-tls', action='store_true')
    parser.add_argument('--check-tls-local', action='store_true')
    args = parser.parse_args()
    if args.check_tls or args.check_tls_local:
        import ssl
        import urllib.request
        import urllib.error
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        status = None
        if args.check_tls:
            try:
                with urllib.request.urlopen('https://api.deepseek.com/models', context=context, timeout=25) as response:
                    status = response.status
            except urllib.error.HTTPError as exc:
                status = exc.code
        print(json.dumps({'tls_verified': True, 'http_status': status, 'credential_sent': False}))
        return
    if not args.ready_file:
        parser.error('--ready-file is required when starting the service')
    # The packaged app always starts disconnected; never inherit model credentials.
    for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'):
        os.environ.pop(key, None)
    if os.getpgrp() != os.getpid():
        os.setsid()
    import server
    import errno
    for port in [*range(8765, 8775), 0]:
        try:
            httpd = ThreadingHTTPServer(('127.0.0.1', port), server.Handler)
            break
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
    def stop(*_):
        threading.Thread(target=httpd.shutdown, daemon=True).start()
    parent_pid = os.getppid()
    def watch_parent():
        import time
        while os.getppid() == parent_pid:
            time.sleep(1)
        stop()
    threading.Thread(target=watch_parent, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    ready = Path(args.ready_file)
    ready.parent.mkdir(parents=True, exist_ok=True)
    temporary = ready.with_suffix('.tmp')
    temporary.write_text(json.dumps({'url': f'http://127.0.0.1:{httpd.server_port}', 'pid': os.getpid()}))
    temporary.chmod(0o600)
    temporary.replace(ready)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        if os.getpgrp() == os.getpid():
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                os.killpg(os.getpgrp(), signal.SIGTERM)
            except ProcessLookupError:
                pass
        ready.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
