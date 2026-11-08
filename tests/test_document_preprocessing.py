# 测试中的机构、姓名、联系方式、业务条件和制度片段均为虚构测试数据。
import io
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image
from docx import Document
from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.oxml.ns import qn
from pptx.util import Inches
from reportlab.pdfgen import canvas

import document_parser
import server


def make_image(path: Path, size=(1800, 900)) -> None:
    image = Image.new("RGB", size, (84, 132, 176))
    image.save(path, "PNG")


class DocumentPreprocessingTests(unittest.TestCase):
    def setUp(self):
        server.DOCUMENT_SESSIONS.clear()
        server.IMAGE_ASSET_INDEX.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.asset_root = self.root / "assets"
        self.registered = {}

    def tearDown(self):
        self.temp.cleanup()

    def register(self, asset_id, path, document_id):
        self.registered[asset_id] = (path, document_id)

    def test_legacy_ppt_without_converter_does_not_show_binary_metadata(self):
        path = self.root / "sample.ppt"
        path.write_bytes(b"Root Entry\x00PowerPoint Document\x00" * 20)
        with mock.patch.object(document_parser, "_local_tool", return_value=None):
            with self.assertRaisesRegex(ValueError, "另存为 PPTX"):
                document_parser.parse_document(
                    path, path.name, "doc-legacy", server.SourceSegment, self.asset_root, self.register
                )

    def test_legacy_ppt_uses_converted_pptx_content(self):
        path = self.root / "sample.ppt"
        path.write_bytes(b"legacy ppt")
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_textbox(0, 0, Inches(5), Inches(1)).text = "真正的幻灯片正文"

        def convert(command, **kwargs):
            output_dir = Path(command[command.index("--outdir") + 1])
            presentation.save(output_dir / "sample.pptx")
            return mock.Mock(returncode=0)

        with mock.patch.object(document_parser, "_local_tool", return_value="/usr/bin/soffice"), \
             mock.patch.object(document_parser.subprocess, "run", side_effect=convert):
            result = document_parser.parse_document(
                path, path.name, "doc-legacy", server.SourceSegment, self.asset_root, self.register
            )
        self.assertEqual(["真正的幻灯片正文"], [segment.text for segment in result["segments"]])
        self.assertEqual("ppt", result["document_preview"]["format"])
        self.assertTrue(result["document_preview"]["legacy_layout_warning"])

    def test_legacy_doc_without_converter_does_not_show_binary_metadata(self):
        path = self.root / "sample.doc"
        path.write_bytes(b"Root Entry\x00SummaryInformation\x00WordDocument\x00" * 20)
        with mock.patch.object(document_parser, "_local_tool", return_value=None):
            with self.assertRaisesRegex(ValueError, "另存为 DOCX"):
                document_parser.parse_document(
                    path, path.name, "doc-legacy", server.SourceSegment, self.asset_root, self.register
                )

    def test_legacy_doc_uses_converted_docx_content(self):
        path = self.root / "sample.doc"
        path.write_bytes(b"Root Entry\x00SummaryInformation\x00WordDocument\x00" * 20)
        document = Document()
        document.add_paragraph("真正的 Word 正文")

        def convert(command, **kwargs):
            output_dir = Path(command[command.index("--outdir") + 1])
            document.save(output_dir / "sample.docx")
            return mock.Mock(returncode=0)

        with mock.patch.object(document_parser, "_local_tool", return_value="/usr/bin/soffice"), \
             mock.patch.object(document_parser.subprocess, "run", side_effect=convert):
            result = document_parser.parse_document(
                path, path.name, "doc-legacy", server.SourceSegment, self.asset_root, self.register
            )
        texts = [segment.text for segment in result["segments"]]
        self.assertIn("真正的 Word 正文", texts)
        self.assertNotIn("Root Entry", texts)
        self.assertEqual("doc", result["document_preview"]["format"])
        self.assertTrue(result["document_preview"]["legacy_layout_warning"])

    def test_pptx_mixes_split_run_text_and_compressed_image(self):
        image_path = self.root / "sample.png"
        make_image(image_path)
        path = self.root / "sample.pptx"
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(5), Inches(1))
        paragraph = box.text_frame.paragraphs[0]
        paragraph.add_run().text = "客户姓名：张"
        paragraph.add_run().text = "三，手机号13800138000"
        slide.shapes.add_picture(str(image_path), Inches(1), Inches(2), width=Inches(4))
        presentation.save(path)

        parsed = document_parser.parse_document(
            path, "sample.pptx", "doc-ppt", server.SourceSegment, self.asset_root, self.register
        )
        result = document_parser.serializable_result(parsed)
        self.assertIn("客户姓名：张三", result["segments"][0]["text"])
        self.assertEqual(["text", "image"], [item["type"] for item in result["blocks"]])
        self.assertEqual(1, len(result["image_assets"]))
        asset = result["image_assets"][0]
        self.assertLessEqual(max(asset["preview_width"], asset["preview_height"]), 1400)
        self.assertTrue(self.registered[asset["id"]][0].exists())
        candidates = server.detect_sensitive_candidates(result["segments"])
        self.assertTrue(any(item["value"] == "张三" for item in candidates))

    def test_pptx_unrecognized_shape_type_keeps_its_text(self):
        path = self.root / "unknown-shape.pptx"
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        shape = slide.shapes.add_textbox(0, 0, Inches(2), Inches(1))
        shape.text = "特殊图形中的文字"
        shape._element.find(".//" + qn("p:cNvSpPr")).set("txBox", "0")
        geometry = shape._element.find(".//" + qn("a:prstGeom"))
        geometry.getparent().remove(geometry)
        presentation.save(path)

        parsed = document_parser.parse_document(
            path, path.name, "doc-unknown", server.SourceSegment, self.asset_root, self.register
        )
        result = document_parser.serializable_result(parsed)
        self.assertEqual("特殊图形中的文字", result["segments"][0]["text"])

    def test_image_text_enters_source_segments_and_small_decoration_is_skipped(self):
        screenshot = self.root / "screenshot.png"
        decoration = self.root / "decoration.png"
        make_image(screenshot, (1000, 500))
        make_image(decoration, (60, 60))
        path = self.root / "screenshots.pptx"
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        slide.shapes.add_picture(str(screenshot), Inches(1), Inches(1), width=Inches(6))
        slide.shapes.add_picture(str(decoration), Inches(0.1), Inches(0.1), width=Inches(0.3))
        presentation.save(path)

        def recognize(paths):
            return ({str(paths[0]): ["虚构社团工具借用规则：归还前须清点配件"]}, True)

        with mock.patch.object(document_parser, "_recognize_images", side_effect=recognize):
            result = document_parser.parse_document(
                path, "screenshots.pptx", "doc-ocr", server.SourceSegment, self.asset_root, self.register
            )
        self.assertEqual(1, len(result["image_assets"]))
        self.assertEqual(1, result["image_filter"]["ignored_count"])
        self.assertEqual("虚构社团工具借用规则：归还前须清点配件", result["segments"][0].text)
        self.assertEqual("image_ocr", next(block["source"]["kind"] for block in result["blocks"]
                                           if block.get("segment_id") == result["segments"][0].id))

    def test_repeated_large_decoration_and_text_logo_are_ignored(self):
        decoration = self.root / "large-decoration.png"
        logo = self.root / "logo.png"
        make_image(decoration, (1200, 900))
        make_image(logo, (800, 130))
        presentation = Presentation()
        for page in range(2):
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            slide.shapes.add_picture(str(decoration), Inches(1), Inches(1), width=Inches(5))
            slide.shapes.add_picture(str(logo), Inches(0.2), Inches(0.2), width=Inches(2))
            slide.shapes.add_textbox(Inches(1), Inches(4), Inches(4), Inches(1)).text = f"制度内容{page}"
        path = self.root / "decorations.pptx"
        presentation.save(path)

        def recognize(paths):
            return ({str(paths[1]): ["示例商业银行", "EXAMPLE COMMERCIAL BANK"],
                     str(paths[3]): ["示例商业银行", "EXAMPLE COMMERCIAL BANK"]}, True)

        with mock.patch.object(document_parser, "_recognize_images", side_effect=recognize):
            parsed = document_parser.parse_document(
                path, "decorations.pptx", "doc-decor", server.SourceSegment, self.asset_root, self.register
            )
        self.assertEqual(4, parsed["image_filter"]["ignored_count"])
        self.assertEqual([], parsed["image_assets"])
        self.assertFalse(any("示例商业银行" in segment.text for segment in parsed["segments"]))

    def test_pptx_chart_becomes_image_and_searchable_data(self):
        path = self.root / "chart.pptx"
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        chart_data = ChartData()
        chart_data.categories = ["甲组", "乙组"]
        chart_data.add_series("画纸库存数量", (12, 8))
        slide.shapes.add_chart(
            XL_CHART_TYPE.COLUMN_CLUSTERED,
            Inches(1), Inches(1), Inches(6), Inches(3), chart_data,
        )
        presentation.save(path)
        page_image = Image.new("RGB", (1600, 900), "white")
        page_buffer = io.BytesIO()
        page_image.save(page_buffer, "PNG")

        with mock.patch.object(document_parser, "_render_pptx_pages", return_value={1: page_buffer.getvalue()}):
            parsed = document_parser.parse_document(
                path, "chart.pptx", "doc-chart", server.SourceSegment, self.asset_root, self.register
            )
        result = document_parser.serializable_result(parsed)

        self.assertEqual(1, len(result["image_assets"]))
        self.assertEqual("pptx_chart", result["image_assets"][0]["source"]["kind"])
        chart_segment = next(item for item in result["segments"] if "画纸库存数量" in item["text"])
        self.assertIn("甲组=12", chart_segment["text"])
        self.assertEqual("pptx_chart_data", result["document_preview"]["pages"][0]["annotations"][0]["kind"])

    def test_docx_preserves_paragraph_image_order(self):
        image_path = self.root / "word.png"
        make_image(image_path, (400, 240))
        path = self.root / "sample.docx"
        document = Document()
        paragraph = document.add_paragraph()
        paragraph.add_run("联系人：李")
        paragraph.add_run("四")
        document.add_picture(str(image_path), width=Inches(2))
        document.add_paragraph("联系邮箱lisi@example.com")
        document.save(path)

        parsed = document_parser.parse_document(
            path, "sample.docx", "doc-word", server.SourceSegment, self.asset_root, self.register
        )
        result = document_parser.serializable_result(parsed)
        self.assertEqual(["text", "image", "text"], [item["type"] for item in result["blocks"]])
        self.assertEqual("联系人：李四", result["segments"][0]["text"])
        self.assertEqual(1, len(result["image_assets"]))

    @unittest.skipIf(document_parser._import_pymupdf() is None, "PyMuPDF is required for positioned PDF blocks")
    def test_pdf_uses_positioned_text_and_image_blocks(self):
        image_path = self.root / "pdf.png"
        make_image(image_path, (500, 300))
        path = self.root / "sample.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(600, 800))
        pdf.drawString(60, 740, "Contact: Alice 13800138000")
        pdf.drawImage(str(image_path), 60, 380, width=360, height=216)
        pdf.save()

        parsed = document_parser.parse_document(
            path, "sample.pdf", "doc-pdf", server.SourceSegment, self.asset_root, self.register
        )
        result = document_parser.serializable_result(parsed)
        self.assertIn("Contact: Alice", result["segments"][0]["text"])
        self.assertEqual({"text", "image"}, {item["type"] for item in result["blocks"]})
        self.assertEqual("pdf_image", result["image_assets"][0]["source"]["kind"])
        self.assertEqual(4, len(result["image_assets"][0]["source"]["bbox"]))
        self.assertTrue(result["pdf_positioning_available"])

    def test_pdf_fallback_preview_keeps_ocr_text_and_images(self):
        image_path = self.root / "scan.png"
        make_image(image_path, (800, 300))
        path = self.root / "scan.pdf"
        pdf = canvas.Canvas(str(path))
        pdf.drawImage(str(image_path), 40, 550, width=500, height=180)
        pdf.save()
        with mock.patch.object(document_parser, "_import_pymupdf", return_value=None), \
             mock.patch.object(document_parser, "_recognize_images", return_value=({}, False)):
            parsed = document_parser.parse_document(
                path, "scan.pdf", "doc-scan", server.SourceSegment, self.asset_root, self.register
            )
        self.assertTrue(parsed["image_assets"])
        self.assertTrue(parsed["document_preview"]["pages"][0]["elements"])
        self.assertFalse(parsed["pdf_positioning_available"])

    @unittest.skipIf(document_parser._import_pymupdf() is None, "PyMuPDF is required")
    def test_pdf_repeated_template_is_removed_without_ocr(self):
        background = self.root / "background.png"
        first = self.root / "first.png"
        second = self.root / "second.png"
        make_image(background, (1200, 675))
        Image.new("RGB", (600, 300), (180, 70, 70)).save(first, "PNG")
        Image.new("RGB", (600, 300), (70, 140, 80)).save(second, "PNG")
        path = self.root / "templates.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(600, 338))
        for content in (first, second):
            pdf.drawImage(str(background), 0, 0, width=600, height=338)
            pdf.drawImage(str(content), 120, 90, width=360, height=180)
            pdf.drawString(40, 310, "Policy text remains selectable")
            pdf.showPage()
        pdf.save()

        with mock.patch.object(document_parser, "_recognize_images", return_value=({}, False)):
            parsed = document_parser.parse_document(
                path, "templates.pdf", "doc-template-pdf", server.SourceSegment,
                self.asset_root, self.register,
            )

        self.assertEqual(2, len(parsed["image_assets"]))
        self.assertEqual({1, 2}, {asset["page"] for asset in parsed["image_assets"]})
        self.assertEqual(2, parsed["image_filter"]["ignored_count"])
        self.assertFalse(parsed["image_filter"]["ocr_available"])
        self.assertTrue(any("Policy text" in segment.text for segment in parsed["segments"]))

    @unittest.skipIf(document_parser._import_pymupdf() is None, "PyMuPDF is required")
    def test_pdf_repeated_body_screenshot_with_text_is_preserved(self):
        screenshot = self.root / "repeated-screenshot.png"
        Image.new("RGB", (900, 500), "white").save(screenshot, "PNG")
        path = self.root / "repeated-screenshot.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(600, 400))
        for _ in range(2):
            pdf.drawImage(str(screenshot), 90, 80, width=420, height=240)
            pdf.showPage()
        pdf.save()

        def recognize(paths):
            return ({str(path): ["虚构社团工具借用规则截图，内容需要保留"] for path in paths}, True)

        with mock.patch.object(document_parser, "_recognize_images", side_effect=recognize):
            parsed = document_parser.parse_document(
                path, "repeated-screenshot.pdf", "doc-repeated-body", server.SourceSegment,
                self.asset_root, self.register,
            )

        self.assertEqual(2, len(parsed["image_assets"]))
        self.assertEqual(2, parsed["image_filter"]["recognized_count"])
        self.assertEqual(0, parsed["image_filter"]["ignored_count"])

    @unittest.skipIf(document_parser._import_pymupdf() is None, "PyMuPDF is required")
    def test_pdf_overlapping_fragments_become_one_composite(self):
        fragments = []
        for index, color in enumerate(((200, 60, 60), (60, 160, 70), (60, 90, 200)), start=1):
            fragment = self.root / f"fragment-{index}.png"
            Image.new("RGB", (400, 240), color).save(fragment, "PNG")
            fragments.append(fragment)
        path = self.root / "fragmented.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(600, 400))
        for index, fragment in enumerate(fragments):
            pdf.drawImage(str(fragment), 80 + index * 70, 100 + index * 30, width=260, height=156)
        pdf.save()

        with mock.patch.object(document_parser, "_recognize_images", return_value=({}, False)):
            parsed = document_parser.parse_document(
                path, "fragmented.pdf", "doc-fragment-pdf", server.SourceSegment,
                self.asset_root, self.register,
            )

        self.assertEqual(1, len(parsed["image_assets"]))
        source = parsed["image_assets"][0]["source"]
        self.assertTrue(source["composite"])
        self.assertEqual(3, source["fragment_count"])
        self.assertEqual(2, parsed["image_filter"]["merged_fragment_count"])

    @unittest.skipIf(document_parser._import_pymupdf() is None, "PyMuPDF is required")
    def test_pdf_scan_ocr_enters_redaction_candidates(self):
        scan = self.root / "scan-sensitive.png"
        Image.new("RGB", (1200, 700), "white").save(scan, "PNG")
        path = self.root / "scan-sensitive.pdf"
        pdf = canvas.Canvas(str(path), pagesize=(600, 350))
        pdf.drawImage(str(scan), 0, 0, width=600, height=350)
        pdf.save()

        recognized_text = "客户姓名：张三，手机号13800138000"
        def recognize(paths):
            return ({str(paths[0]): [recognized_text]}, True)

        with mock.patch.object(document_parser, "_recognize_images", side_effect=recognize):
            parsed = document_parser.parse_document(
                path, "scan-sensitive.pdf", "doc-scan-sensitive", server.SourceSegment,
                self.asset_root, self.register,
            )

        self.assertEqual(1, len(parsed["image_assets"]))
        self.assertEqual(1, parsed["image_filter"]["recognized_count"])
        self.assertEqual("image_ocr", next(block["source"]["kind"] for block in parsed["blocks"]
                                           if block.get("segment_id") == parsed["segments"][0].id))
        candidates = server.detect_sensitive_candidates([vars(item) for item in parsed["segments"]])
        self.assertTrue(any(item["value"] == "张三" for item in candidates))
        self.assertTrue(any(item["value"] == "13800138000" for item in candidates))

    def test_confirmation_rejects_pending_and_validates_image_coordinates(self):
        segments = [{"id": "P1-01", "file_name": "材料.txt", "page": 1, "index": 1,
                     "text": "客户姓名：张三"}]
        asset = {"id": "img-1", "file_name": "材料.txt", "page": 1}
        session = server.create_document_session(
            "doc-confirm", {"segments": segments, "blocks": [], "image_assets": [asset], "page_count": 1},
            "材料.txt", ".txt",
        )
        candidates = server.detect_sensitive_candidates(segments)
        with self.assertRaisesRegex(ValueError, "待确认"):
            server.create_confirmation("doc-confirm", session["version"], candidates, [])

        for candidate in candidates:
            for occurrence in candidate["occurrences"]:
                occurrence["status"] = "confirmed"
        bad_region = {"id": "r1", "asset_id": "img-1", "type": "face", "status": "confirmed",
                      "x": 0.9, "y": 0.1, "width": 0.2, "height": 0.2}
        with self.assertRaisesRegex(ValueError, "超出"):
            server.create_confirmation("doc-confirm", session["version"], candidates, [bad_region])

        region = {**bad_region, "x": 0.2, "width": 0.3}
        confirmation = server.create_confirmation("doc-confirm", session["version"], candidates, [region])
        self.assertEqual(1, confirmation["summary"]["image_region_count"])
        self.assertNotIn("张三", confirmation["masked_segments"][0]["text"])
        self.assertIs(server.get_confirmation("doc-confirm", confirmation["token"]), confirmation)
        with self.assertRaisesRegex(ValueError, "凭证"):
            server.get_confirmation("doc-confirm", "forged-token")

    def test_intermediate_docx_exports_parsed_and_redacted_content_with_mosaic(self):
        image_path = self.root / "private.png"
        image = Image.new("RGB", (240, 160), "white")
        for x in range(240):
            for y in range(160):
                image.putpixel((x, y), ((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256))
        image.save(image_path, "PNG")
        original_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()

        segments = [{"id": "P1-01", "file_name": "客户材料.pdf", "page": 1, "index": 1,
                     "text": "客户姓名：张三，手机号13800138000"}]
        asset = {"id": "img-private", "file_name": "客户材料.pdf", "page": 1,
                 "original_width": 240, "original_height": 160, "source": {"kind": "pdf_image"}}
        parsed = {"segments": segments,
                  "blocks": [
                      {"id": "b1", "type": "text", "segment_id": "P1-01", "file_name": "客户材料.pdf", "page": 1, "order": 1},
                      {"id": "b2", "type": "image", "asset_id": "img-private", "file_name": "客户材料.pdf", "page": 1, "order": 2},
                  ], "image_assets": [asset], "page_count": 1}
        session = server.create_document_session("doc-export", parsed, "客户材料.pdf", ".pdf")
        server.IMAGE_ASSET_INDEX["img-private"] = {
            "path": image_path, "document_id": "doc-export", "content_type": "image/png",
        }

        parsed_body = server.build_intermediate_docx(session, session["segments"])
        parsed_document = Document(io.BytesIO(parsed_body))
        parsed_text = "\n".join(item.text for item in parsed_document.paragraphs)
        self.assertIn("客户姓名：张三", parsed_text)
        self.assertIn("可能包含未脱敏信息", parsed_text)

        candidates = server.detect_sensitive_candidates(segments)
        for candidate in candidates:
            for occurrence in candidate["occurrences"]:
                occurrence["status"] = "confirmed"
        region = {"id": "r1", "asset_id": "img-private", "type": "custom", "status": "confirmed",
                  "x": 0.2, "y": 0.2, "width": 0.5, "height": 0.5}
        confirmation = server.create_confirmation("doc-export", session["version"], candidates, [region])
        redacted_body = server.build_intermediate_docx(
            session, confirmation["masked_segments"], confirmation["image_regions"], redacted=True,
        )
        redacted_document = Document(io.BytesIO(redacted_body))
        redacted_text = "\n".join(item.text for item in redacted_document.paragraphs)
        self.assertNotIn("张三", redacted_text)
        self.assertNotIn("13800138000", redacted_text)
        self.assertIn("脱敏文件", redacted_text)

        with zipfile.ZipFile(io.BytesIO(parsed_body)) as parsed_zip, zipfile.ZipFile(io.BytesIO(redacted_body)) as redacted_zip:
            parsed_media = parsed_zip.read(next(name for name in parsed_zip.namelist() if name.startswith("word/media/")))
            redacted_media = redacted_zip.read(next(name for name in redacted_zip.namelist() if name.startswith("word/media/")))
        self.assertNotEqual(hashlib.sha256(parsed_media).hexdigest(), hashlib.sha256(redacted_media).hexdigest())
        self.assertEqual(original_hash, hashlib.sha256(image_path.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
