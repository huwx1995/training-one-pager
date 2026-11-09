"""Check the frozen document-only Windows edition with synthetic material."""
from pathlib import Path
import http.client
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile


def main():
    executable = Path(sys.argv[1]).resolve()
    app = executable.parent
    internal = app / "_internal"
    assert (internal / "lite-edition.flag").is_file()
    assert not (internal / "models").exists()
    for name in ("ffmpeg.exe", "ffprobe.exe", "whisper-cli.exe", "whisper-cli-avx2.exe"):
        assert not (internal / "tools" / name).exists(), name
    assert (internal / "tools/tesseract.exe").is_file()
    with tempfile.TemporaryDirectory(prefix="onepager-lite-") as directory:
        root = Path(directory)
        ready = root / "ready.json"
        env = {"PATH": str(Path(os.environ["SystemRoot"]) / "System32"),
               "SystemRoot": os.environ["SystemRoot"], "WINDIR": os.environ["SystemRoot"],
               "USERPROFILE": str(root), "LOCALAPPDATA": str(root / "local"),
               "TEMP": str(root), "TMP": str(root), "ONEPAGER_DATA_DIR": str(root / "data")}
        process = subprocess.Popen([str(executable), "--backend", "--ready-file", str(ready)],
                                   env=env, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, text=True, creationflags=0x08000000)
        try:
            for _ in range(300):
                if ready.exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError(f"Backend exited: {process.returncode}")
                time.sleep(0.1)
            else:
                raise TimeoutError("Lite backend did not start")
            port = int(json.loads(ready.read_text())["url"].rsplit(":", 1)[1])
            def request(method, path, body=None, headers=None):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
                conn.request(method, path, body=body,
                             headers={"Host": f"127.0.0.1:{port}", **(headers or {})})
                response = conn.getresponse()
                payload = response.read()
                status = response.status
                kind = response.getheader("Content-Type", "")
                conn.close()
                return status, json.loads(payload) if kind.startswith("application/json") else payload
            status, page = request("GET", "/")
            assert status == 200 and b'data-edition="lite"' in page
            for method, path in (("GET", "/api/audio/model-status"),
                                 ("POST", "/api/audio/model-download"),
                                 ("POST", "/api/audio/upload")):
                status, _ = request(method, path)
                assert status == 404, (method, path, status)
            boundary = "lite-synthetic-boundary"
            text = "虚构社团工具借用培训。借用期限为3天，归还前必须清点配件。".encode()
            upload = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.txt"\r\n'
                      'Content-Type: text/plain\r\n\r\n').encode() + text + f'\r\n--{boundary}--\r\n'.encode()
            status, payload = request("POST", "/api/extract", upload,
                                      {"Content-Type": f"multipart/form-data; boundary={boundary}"})
            assert status == 200, (status, payload)
            document = payload["document"]
            def post(path, value):
                return request("POST", path, json.dumps(value, ensure_ascii=False).encode(),
                               {"Content-Type": "application/json", "X-Generation-Mode": "local"})
            status, confirmed = post("/api/desensitize", {"document_id": document["id"],
                "document_version": document["document_version"], "candidates": document["sensitive_candidates"],
                "image_regions": [], "confirmed": True})
            assert status == 200, (status, confirmed)
            token = confirmed["confirmation_token"]
            status, generated = post("/api/generate", {"document_id": document["id"],
                "confirmation_token": token, "audience": "社团成员", "template": "knowledge-operation",
                "requirements": {"version": 1, "max_chars": 500, "detail_depth": "normal", "tone": "plain",
                    "detail_target": "", "must_keep": "", "include_overview": True,
                    "include_architecture": True, "include_practice": True, "explain_terms": False}})
            assert status == 200, (status, generated)
            status, word = post("/api/export/docx", {"document_id": document["id"],
                "confirmation_token": token, "one_pager": generated["one_pager"]})
            assert status == 200
            with zipfile.ZipFile(io.BytesIO(word)) as archive:
                assert "word/document.xml" in archive.namelist()
            print("Windows lite: audio blocked; TXT parsing, generation and Word export passed.")
        finally:
            if process.poll() is None:
                process.stdin.write("stop\n")
                process.stdin.flush()
                process.wait(timeout=20)


if __name__ == "__main__":
    main()
