"""Local HTTP origin and streaming multipart helpers."""
from __future__ import annotations

import mmap
import re
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def local_request_allowed(handler: BaseHTTPRequestHandler, mutation: bool, error_response) -> bool:
    host = handler.headers.get("Host", "")
    try:
        parsed_host = urlsplit(f"http://{host}")
        host_name = parsed_host.hostname
        parsed_host.port
    except ValueError:
        host_name = None
    if host_name not in {"127.0.0.1", "localhost", "::1"}:
        error_response(handler, 403, "只能通过本机地址访问此工具。")
        return False
    origin = handler.headers.get("Origin", "")
    if mutation and origin:
        try:
            parsed_origin = urlsplit(origin)
            valid_origin = parsed_origin.scheme == "http" and parsed_origin.netloc.lower() == host.lower()
        except ValueError:
            valid_origin = False
        if not valid_origin:
            error_response(handler, 403, "请求来源与本地服务地址不一致，请刷新页面后重试。")
            return False
    return True



def receive_multipart_to_dir(handler: BaseHTTPRequestHandler, size: int, upload_dir: Path) -> list[dict[str, Any]]:
    """Stage a request in chunks, then copy each file part without loading it into RAM."""
    boundary_match = re.search(r"boundary=([^;]+)", handler.headers.get("Content-Type", ""))
    if not boundary_match:
        raise ValueError("上传请求缺少 boundary。")
    boundary = boundary_match.group(1).strip().strip('"').encode()
    if not boundary or len(boundary) > 200:
        raise ValueError("上传请求 boundary 无效。")
    staging = upload_dir / f"request-{uuid.uuid4().hex}.tmp"
    parts: list[dict[str, Any]] = []
    try:
        with staging.open("wb") as output:
            remaining = size
            while remaining:
                chunk = handler.rfile.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("上传中断，请重新选择文件。")
                output.write(chunk)
                remaining -= len(chunk)
        with staging.open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as body:
            delimiter = b"--" + boundary
            cursor = body.find(delimiter)
            if cursor < 0:
                raise ValueError("上传内容格式无效。")
            while len(parts) < 32:
                cursor += len(delimiter)
                if body[cursor:cursor + 2] == b"--":
                    break
                if body[cursor:cursor + 2] != b"\r\n":
                    raise ValueError("上传内容格式无效。")
                header_end = body.find(b"\r\n\r\n", cursor + 2)
                if header_end < 0 or header_end - cursor > 8192:
                    raise ValueError("上传文件头无效。")
                headers = body[cursor + 2:header_end].decode("utf-8", errors="replace")
                name_match = re.search(r'name="([^"]+)"', headers)
                filename_match = re.search(r'filename="([^"]*)"', headers)
                data_start = header_end + 4
                data_end = body.find(b"\r\n" + delimiter, data_start)
                if not name_match or data_end < 0:
                    raise ValueError("上传内容格式无效。")
                part = {"name": name_match.group(1), "filename": filename_match.group(1) if filename_match else None}
                if filename_match:
                    path = upload_dir / f"part-{uuid.uuid4().hex}.tmp"
                    with path.open("wb") as output:
                        for offset in range(data_start, data_end, 1024 * 1024):
                            output.write(body[offset:min(offset + 1024 * 1024, data_end)])
                    part["path"] = path
                else:
                    if data_end - data_start > 4096:
                        raise ValueError("上传表单字段过长。")
                    part["data"] = body[data_start:data_end]
                parts.append(part)
                cursor = data_end + 2
            else:
                raise ValueError("上传文件数量过多。")
        return parts
    except Exception:
        for part in parts:
            if "path" in part:
                part["path"].unlink(missing_ok=True)
        raise
    finally:
        staging.unlink(missing_ok=True)


