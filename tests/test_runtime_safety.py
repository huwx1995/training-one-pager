import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import server


class RuntimeSafetyTests(unittest.TestCase):
    def fake_handler(self, headers, body=b""):
        handler = server.Handler.__new__(server.Handler)
        handler.headers = headers
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.request_id = "test-request"
        handler.send_response = lambda status: setattr(handler, "status", status)
        handler.send_header = lambda *_: None
        handler.end_headers = lambda: None
        return handler

    def test_local_host_and_origin_required(self):
        local = self.fake_handler({"Host": "127.0.0.1:8000", "Origin": "http://127.0.0.1:8000"})
        self.assertTrue(server._local_request_allowed(local, True))
        remote = self.fake_handler({"Host": "example.com:8000"})
        self.assertFalse(server._local_request_allowed(remote, False))
        self.assertEqual(403, remote.status)
        cross_site = self.fake_handler({"Host": "127.0.0.1:8000", "Origin": "https://example.com"})
        self.assertFalse(server._local_request_allowed(cross_site, True))
        self.assertEqual(403, cross_site.status)
        malformed = self.fake_handler({"Host": "localhost:invalid"})
        self.assertFalse(server._local_request_allowed(malformed, False))
        self.assertEqual(403, malformed.status)
        malformed_origin = self.fake_handler({"Host": "localhost:8000", "Origin": "http://[bad"})
        self.assertFalse(server._local_request_allowed(malformed_origin, True))
        self.assertEqual(403, malformed_origin.status)

    def test_multipart_is_staged_without_in_memory_file_part(self):
        boundary = "test-boundary"
        body = (b"--test-boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"sample.txt\"\r\n"
                b"Content-Type: text/plain\r\n\r\nfirst\nsecond\r\n--test-boundary--\r\n")
        handler = self.fake_handler({"Content-Type": f"multipart/form-data; boundary={boundary}"}, body)
        parts = server.receive_multipart(handler, len(body))
        try:
            self.assertEqual("sample.txt", parts[0]["filename"])
            self.assertEqual(b"first\nsecond", parts[0]["path"].read_bytes())
            self.assertNotIn("data", parts[0])
        finally:
            parts[0]["path"].unlink(missing_ok=True)

    def test_json_size_and_busy_parser_return_actionable_errors(self):
        handler = self.fake_handler({"Host": "127.0.0.1:8000", "Content-Length": str(server.MAX_JSON_BYTES + 1)})
        handler.path = "/api/detect-sensitive"
        handler.do_POST()
        self.assertEqual(413, handler.status)
        busy = self.fake_handler({"Host": "127.0.0.1:8000", "Content-Length": "0"})
        busy.path = "/api/extract"
        server.PARSE_LOCK.acquire()
        try:
            busy.do_POST()
        finally:
            server.PARSE_LOCK.release()
        self.assertEqual(429, busy.status)

    def test_generation_status_uses_random_job_id(self):
        job_id = "a" * 32
        server.GENERATION_JOBS[job_id] = {"message": "正在分析材料第 1/2 批", "updated_at": 1}
        try:
            handler = self.fake_handler({"Host": "127.0.0.1:8000"})
            handler.path = f"/api/generation-status/{job_id}"
            handler.do_GET()
            self.assertEqual(200, handler.status)
            self.assertIn("1/2", handler.wfile.getvalue().decode())
        finally:
            server.GENERATION_JOBS.pop(job_id, None)

    def test_lite_edition_blocks_audio_routes_and_marks_page(self):
        with patch.object(server, 'AUDIO_ENABLED', False):
            for method, path in [('do_GET', '/api/audio/model-status'),
                                 ('do_POST', '/api/audio/model-download'),
                                 ('do_POST', '/api/audio/upload')]:
                handler = self.fake_handler({'Host': '127.0.0.1:8000', 'Content-Length': '0'})
                handler.path = path
                getattr(handler, method)()
                self.assertEqual(404, handler.status)
            page = self.fake_handler({'Host': '127.0.0.1:8000'})
            page.path = '/'
            page.do_GET()
            self.assertEqual(200, page.status)
            self.assertIn(b'data-edition="lite"', page.wfile.getvalue())

    def test_stale_runtime_is_removed_but_other_directories_remain(self):
        with tempfile.TemporaryDirectory() as root:
            runs = Path(root)
            stale = runs / "run-99999999-deadbeef"
            stale.mkdir()
            kept = runs / "models"
            kept.mkdir()
            with patch.object(server, "RUNS_DIR", runs), patch.object(server, "_process_alive", return_value=False):
                server._cleanup_stale_runs()
            self.assertFalse(stale.exists())
            self.assertTrue(kept.exists())

    def test_document_clear_removes_owned_copies_and_keeps_other_materials_and_model(self):
        with tempfile.TemporaryDirectory() as root:
            run = Path(root) / "run"
            assets = run / "assets"
            records = run / "records"
            model = Path(root) / "models" / "speech.bin"
            assets.mkdir(parents=True)
            records.mkdir()
            model.parent.mkdir()
            model.write_bytes(b"model")
            document_id, other_id = uuid.uuid4().hex, uuid.uuid4().hex
            original = run / f"{document_id}.doc"
            supplement = run / "supplement.pdf"
            other = run / f"{other_id}.txt"
            image = assets / "preview.png"
            for path in (original, supplement, other, image):
                path.write_bytes(b"content")
            record = records / f"{document_id}.json"
            record.write_text("private")
            store = server.SessionStore(server.STATE_LOCK)
            parsed = {"segments": [], "blocks": [], "image_assets": [], "page_count": 1}
            with patch.object(server, "UPLOAD_DIR", run), patch.object(server, "RECORD_DIR", records), \
                 patch.object(server, "SESSION_STORE", store), patch.object(server, "DOCUMENT_SESSIONS", store.sessions), \
                 patch.object(server, "IMAGE_ASSET_INDEX", {}), patch.object(server, "AUDIO_JOBS", {}):
                server.create_document_session(document_id, parsed, "first.doc", ".doc", original)
                server.append_document_content(document_id, [parsed], [supplement])
                server.create_document_session(other_id, parsed, "other.txt", ".txt", other)
                server.IMAGE_ASSET_INDEX["preview"] = {"path": image, "document_id": f"{document_id}-S1-abcd"}
                server.AUDIO_JOBS[document_id] = {"status": "done", "document": {"id": document_id}}
                body = json.dumps({"document_id": document_id}).encode()
                handler = self.fake_handler({"Content-Length": str(len(body))}, body)
                handler.handle_clear_document()
                self.assertEqual(200, handler.status)
                self.assertTrue(json.loads(handler.wfile.getvalue())["removed"])
                self.assertFalse(any(path.exists() for path in (original, supplement, image, record)))
                self.assertNotIn(document_id, store.sessions)
                self.assertNotIn("preview", server.IMAGE_ASSET_INDEX)
                self.assertNotIn(document_id, server.AUDIO_JOBS)
                self.assertTrue(other.exists())
                self.assertIn(other_id, store.sessions)
                self.assertTrue(model.exists())

    def test_failed_clear_keeps_session_for_retry(self):
        with tempfile.TemporaryDirectory() as root:
            run = Path(root)
            document_id = uuid.uuid4().hex
            source = run / f"{document_id}.txt"
            source.write_text("private")
            store = server.SessionStore(server.STATE_LOCK)
            parsed = {"segments": [], "blocks": [], "image_assets": [], "page_count": 1}
            with patch.object(server, "UPLOAD_DIR", run), patch.object(server, "RECORD_DIR", run), \
                 patch.object(server, "SESSION_STORE", store), patch.object(server, "DOCUMENT_SESSIONS", store.sessions), \
                 patch.object(server, "IMAGE_ASSET_INDEX", {}):
                server.create_document_session(document_id, parsed, "first.txt", ".txt", source)
                original_unlink = Path.unlink

                def fail_once(path, *args, **kwargs):
                    if path == source:
                        raise OSError("permission denied")
                    return original_unlink(path, *args, **kwargs)

                with patch.object(Path, "unlink", fail_once):
                    with self.assertRaises(OSError):
                        server.delete_document_session(document_id)
                self.assertIn(document_id, store.sessions)
                self.assertTrue(source.exists())
                self.assertTrue(server.delete_document_session(document_id))
                self.assertFalse(source.exists())

    def test_failed_parse_discards_uploaded_copy(self):
        with tempfile.TemporaryDirectory() as root:
            run = Path(root)
            staged = run / "part-test.tmp"
            staged.write_text("private")
            handler = self.fake_handler({"Content-Length": "1", "Content-Type": "multipart/form-data"})
            with patch.object(server, "UPLOAD_DIR", run), patch.object(server, "IMAGE_ASSET_INDEX", {}), \
                 patch.object(server, "receive_multipart", return_value=[
                     {"name": "file", "filename": "failed.txt", "path": staged}]), \
                 patch.object(server, "parse_document", side_effect=ValueError("parse failed")):
                with self.assertRaisesRegex(ValueError, "parse failed"):
                    handler.handle_extract()
            self.assertEqual([], list(run.iterdir()))

    def test_safe_log_does_not_include_exception_payload(self):
        try:
            raise ValueError("customer-name-and-secret-key")
        except ValueError as exc:
            with patch.object(server.LOGGER, "error") as log:
                server.log_safe_exception("request_id=test", exc)
        self.assertNotIn("customer-name-and-secret-key", str(log.call_args))


if __name__ == "__main__":
    unittest.main()
