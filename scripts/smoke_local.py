# 测试中的机构、姓名、联系方式、业务条件和制度片段均为虚构测试数据。
"""Exercise the local HTTP flow with synthetic material and no model key."""
from __future__ import annotations

import http.client
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


def main() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=20)

    def request(method: str, path: str, body: bytes | None = None, headers: dict[str, str] | None = None):
        connection.request(method, path, body=body, headers={"Host": f"127.0.0.1:{httpd.server_port}", **(headers or {})})
        response = connection.getresponse()
        data = response.read()
        return response.status, json.loads(data) if response.getheader("Content-Type", "").startswith("application/json") else data

    try:
        status, html = request("GET", "/")
        assert status == 200 and b"app.js" in html

        status, model = request("POST", "/api/test-llm", b"{}", {"Content-Type": "application/json"})
        assert status == 400 and model["code"] == "INVALID_REQUEST"

        boundary = "onepager-smoke-boundary"
        material = "客户姓名：张三。联系电话13800138000。".encode("utf-8")
        upload = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"smoke.txt\"\r\n"
                  "Content-Type: text/plain\r\n\r\n").encode() + material + f"\r\n--{boundary}--\r\n".encode()
        status, parsed = request("POST", "/api/extract", upload,
                                 {"Content-Type": f"multipart/form-data; boundary={boundary}"})
        assert status == 200 and parsed["ok"] and parsed["document"]["segments"]
        document = parsed["document"]
        candidates = document["sensitive_candidates"]
        assert candidates
        for candidate in candidates:
            for occurrence in candidate["occurrences"]:
                occurrence["status"] = "confirmed"
        confirmation = json.dumps({"document_id": document["id"], "document_version": document["document_version"],
                                   "candidates": candidates, "image_regions": [], "confirmed": True}, ensure_ascii=False).encode()
        status, masked = request("POST", "/api/desensitize", confirmation, {"Content-Type": "application/json"})
        assert status == 200 and masked["redaction_confirmed"]
        assert "张三" not in masked["segments"][0]["text"]
        assert "13800138000" not in masked["segments"][0]["text"]

        status, denied = request("POST", "/api/test-llm", b"{}",
                                 {"Content-Type": "application/json", "Origin": "http://example.com"})
        assert status == 403 and denied["code"] == "LOCAL_ACCESS_ONLY"
        print("本地接口冒烟检查通过：页面、模型提示、抽取、脱敏确认、来源拦截。")
    finally:
        connection.close()
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
