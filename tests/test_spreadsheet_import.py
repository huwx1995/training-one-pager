import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from docx import Document
from openpyxl import Workbook

import document_parser
import server


class SpreadsheetImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        server.DOCUMENT_SESSIONS.clear()

    def tearDown(self):
        self.temp.cleanup()

    def parse(self, path, prefix=""):
        return document_parser.parse_document(
            path, path.name, "spreadsheet-test", server.SourceSegment,
            self.root / "assets", lambda *_: None, prefix=prefix,
        )

    def test_xlsx_rows_sheets_redaction_sources_and_export(self):
        path = self.root / "training.xlsx"
        book = Workbook()
        first = book.active
        first.title = "规则"
        first.append(["客户", "电话", "比例"])
        first.append(["张三", "13800138000", 0.8])
        second = book.create_sheet("补充")
        second.append(["归还前须清点配件"])
        book.save(path)

        parsed = self.parse(path)
        rows = server.serializable_result(parsed)["segments"]
        self.assertEqual(3, len(rows))
        self.assertEqual(("规则", 2), (rows[1]["sheet"], rows[1]["index"]))
        self.assertIn("B: 13800138000", rows[1]["text"])
        self.assertEqual("补充", rows[2]["sheet"])
        self.assertEqual("table_row", parsed["document_preview"]["flow_blocks"][0]["kind"])
        self.assertIn("工作表「规则」第2行", server.source_location(rows[1]))

        candidates = server.detect_sensitive_candidates(rows)
        self.assertTrue(any(item["value"] == "13800138000" for item in candidates))
        session = server.create_document_session("sheet-doc", parsed, path.name, ".xlsx")
        for candidate in candidates:
            for occurrence in candidate["occurrences"]:
                occurrence["status"] = "confirmed"
        confirmation = server.create_confirmation("sheet-doc", session["version"], candidates, [])
        self.assertNotIn("13800138000", " ".join(item["text"] for item in confirmation["masked_segments"]))
        with mock.patch.object(server, "_select_export_cjk_font", return_value="Arial"):
            output = server.build_intermediate_docx(session, confirmation["masked_segments"], redacted=True)
        exported = Document(io.BytesIO(output))
        self.assertIn("工作表「规则」", " ".join(p.text for p in exported.paragraphs))

    def test_supplement_ids_and_empty_workbook(self):
        path = self.root / "extra.xlsx"
        book = Workbook()
        book.active["A1"] = "补充规则"
        book.save(path)
        parsed = self.parse(path, prefix="S1")
        self.assertEqual("S1-P1-01", parsed["segments"][0].id)
        self.assertIn(".xlsx", server.SUPPORTED_EXTENSIONS)
        self.assertIn(".xls", server.SUPPORTED_EXTENSIONS)
        primary = server.create_document_session("primary", parsed, path.name, ".xlsx")
        initial_version = primary["version"]
        appended = server.append_document_content("primary", [parsed])
        self.assertEqual(1, len(appended["segments"]))
        self.assertNotEqual(initial_version, appended["document_version"])

    def test_xls_reader_maps_cells_and_dates(self):
        path = self.root / "legacy.xls"
        path.write_bytes(b"fixture handled by mocked xlrd reader")
        fake = types.SimpleNamespace(
            XL_CELL_DATE=3, XL_CELL_EMPTY=0, XL_CELL_BLANK=6, XL_CELL_BOOLEAN=4,
            XL_CELL_ERROR=5, error_text_from_code={},
            xldate_as_datetime=lambda value, mode: __import__("datetime").datetime(2024, 1, 2),
        )
        sheet = types.SimpleNamespace(name="旧表", nrows=1, row=lambda index: [
            types.SimpleNamespace(ctype=1, value="借用"),
            types.SimpleNamespace(ctype=3, value=45293),
        ])
        book = types.SimpleNamespace(datemode=0, sheets=lambda: [sheet], release_resources=lambda: None)
        fake.open_workbook = lambda *args, **kwargs: book
        with mock.patch.dict("sys.modules", {"xlrd": fake}):
            parsed = self.parse(path)
        self.assertIn("B: 2024-01-02 00:00:00", parsed["segments"][0].text)
        self.assertEqual("旧表", parsed["segments"][0].sheet)

    def test_html_table_saved_as_xls(self):
        path = self.root / "html-export.xls"
        path.write_text("""<html><head><meta charset='UTF-8'></head><body>
        <table><tr><th>项目</th><th>金额</th></tr>
        <tr><td>估值</td><td>100 &amp; 200</td></tr></table>
        </body></html>""", encoding="utf-8")
        parsed = self.parse(path)
        self.assertEqual(2, len(parsed["segments"]))
        self.assertIn("A: 估值；B: 100 & 200", parsed["segments"][1].text)
        self.assertEqual("表格1", parsed["segments"][1].sheet)

    def test_invalid_xlsx_has_clear_error(self):
        path = self.root / "bad.xlsx"
        path.write_bytes(b"not an Excel workbook")
        with self.assertRaisesRegex(ValueError, "无法打开表格文件"):
            self.parse(path)


if __name__ == "__main__":
    unittest.main()
