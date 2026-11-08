"""DOCX export and image masking for the local one-pager app."""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any


def _select_docx_cjk_font() -> str:
    """Choose an installed Simplified Chinese font for the generated DOCX."""
    override = os.getenv("DOCX_CJK_FONT", "").strip()
    if override:
        return override

    if sys.platform == "darwin":
        candidates = (
            ("PingFang SC", Path("/System/Library/Fonts/PingFang.ttc")),
            ("Hiragino Sans GB", Path("/System/Library/Fonts/Hiragino Sans GB.ttc")),
            ("Heiti SC", Path("/System/Library/Fonts/STHeiti Medium.ttc")),
            ("Arial Unicode MS", Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")),
        )
    elif os.name == "nt":
        fonts_dir = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
        candidates = (
            ("Microsoft YaHei", fonts_dir / "msyh.ttc"),
            ("DengXian", fonts_dir / "Deng.ttf"),
            ("SimSun", fonts_dir / "simsun.ttc"),
        )
    else:
        candidates = (
            ("Noto Sans CJK SC", Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")),
            ("Source Han Sans SC", Path("/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf")),
            ("WenQuanYi Zen Hei", Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")),
        )

    installed = next((name for name, path in candidates if path.exists()), "")
    if installed:
        return installed
    raise RuntimeError(
        "当前环境未检测到可用的中文字体，无法可靠导出 Word。"
        "请安装 Noto Sans CJK SC，或通过 DOCX_CJK_FONT 指定已安装字体。"
    )


def _apply_docx_cjk_typography(document: Any, font_name: str) -> None:
    """Write explicit OOXML CJK font and language metadata to styles and text runs."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def apply_properties(run_properties: Any) -> None:
        fonts = run_properties.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            run_properties.insert(0, fonts)
        for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn(f"w:{attribute}"), font_name)
        fonts.set(qn("w:hint"), "eastAsia")
        for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            fonts.attrib.pop(qn(f"w:{attribute}"), None)

        language = run_properties.find(qn("w:lang"))
        if language is None:
            language = OxmlElement("w:lang")
            run_properties.append(language)
        language.set(qn("w:val"), "zh-CN")
        language.set(qn("w:eastAsia"), "zh-CN")

    styles_element = document.styles.element
    doc_defaults = styles_element.find(qn("w:docDefaults"))
    if doc_defaults is None:
        doc_defaults = OxmlElement("w:docDefaults")
        styles_element.insert(0, doc_defaults)
    run_defaults = doc_defaults.find(qn("w:rPrDefault"))
    if run_defaults is None:
        run_defaults = OxmlElement("w:rPrDefault")
        doc_defaults.insert(0, run_defaults)
    default_properties = run_defaults.find(qn("w:rPr"))
    if default_properties is None:
        default_properties = OxmlElement("w:rPr")
        run_defaults.append(default_properties)
    apply_properties(default_properties)

    for style in document.styles:
        apply_properties(style._element.get_or_add_rPr())

    for run_element in document.element.iter(qn("w:r")):
        apply_properties(run_element.get_or_add_rPr())


def build_one_pager_docx(
    one_pager: dict[str, Any], *, clean_text, clean_item_text, normalize_business_contact, font_selector=None,
    diagram_png: bytes = b"",
) -> bytes:
    try:
        from docx import Document
        from docx.enum.section import WD_SECTION
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Cm, Pt, RGBColor
    except ImportError as exc:
        raise RuntimeError("当前环境缺少 python-docx，无法导出 Word。") from exc

    document = Document()
    section = document.sections[0]
    framework = (one_pager.get("generation_requirements") or {}).get("presentation_mode") == "framework"
    section.page_width = Cm(29.7 if framework else 21)
    section.page_height = Cm(21 if framework else 29.7)
    section.top_margin = Cm(1.1)
    section.bottom_margin = Cm(1.1)
    section.left_margin = Cm(1.15)
    section.right_margin = Cm(1.15)
    styles = document.styles
    cjk_font = (font_selector or _select_docx_cjk_font)()
    styles["Normal"].font.name = cjk_font
    styles["Normal"].font.size = Pt(9 if one_pager.get("schema_version") == "3.0" else 8.5)
    styles["Normal"].paragraph_format.space_after = Pt(2)

    meta = one_pager.get("meta", {})
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(clean_text(meta.get("title", "")) if one_pager.get("schema_version") == "3.0" else clean_item_text(meta.get("title"), 40))
    run.bold = True
    run.font.size = Pt(19)
    run.font.color.rgb = RGBColor(15, 77, 62)
    if one_pager.get("schema_version") != "3.0":
        subtitle = document.add_paragraph(clean_item_text(meta.get("subtitle"), 60))
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.runs[0].font.size = Pt(9)
    info = document.add_paragraph(
        f"{meta.get('file_name', '')}  |  {meta.get('page_count', 1)}页  |  {meta.get('document_type', '')}  |  {meta.get('generated_at', '')}"
    )
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info.runs[0].font.size = Pt(7.5)
    info.runs[0].font.color.rgb = RGBColor(102, 117, 133)

    contact = normalize_business_contact(one_pager.get("business_contact"))
    if contact["name"] or contact["method"]:
        contact_line = document.add_paragraph()
        contact_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
        contact_line.add_run("业务联系：" + "  ".join(part for part in (contact["name"], contact["method"]) if part))
        contact_line.runs[0].font.size = Pt(8)

    if one_pager.get("schema_version") == "3.0":
        requirements = one_pager.get("generation_requirements") or {}
        if requirements.get("include_overview") is not False and meta.get("overview"):
            overview_heading = document.add_paragraph()
            overview_heading.add_run("核心结论").bold = True
            document.add_paragraph(meta.get("overview", ""))

        if requirements.get("include_full_structure") and one_pager.get("original_structure"):
            structure_heading = document.add_paragraph()
            structure_heading.add_run("全文架构").bold = True
            document.add_paragraph("  ·  ".join(item.get("title", "") for item in one_pager["original_structure"]))

        architecture = one_pager.get("knowledge_architecture", {})
        nodes = architecture.get("modules", []) if (requirements.get("include_architecture") is not False
            and architecture.get("show_diagram") is not False and architecture.get("modules")) else []
        if framework and nodes and diagram_png:
            document.add_picture(io.BytesIO(diagram_png), width=Cm(26.8))
        elif nodes:
            architecture_heading = document.add_paragraph()
            architecture_heading.add_run(f"知识架构 · {architecture.get('type', 'grouped')}").bold = True
            for index, node in enumerate(nodes, start=1):
                paragraph = document.add_paragraph()
                run = paragraph.add_run(f"{index}. {node.get('title', '')}")
                run.bold = True
                run.font.color.rgb = RGBColor(23, 63, 100)
                if node.get("description"):
                    paragraph.add_run("：" + node["description"])

        knowledge_groups = [] if framework or requirements.get("include_knowledge_modules") is False else one_pager.get("knowledge_modules", [])
        if knowledge_groups:
            knowledge_heading = document.add_paragraph()
            knowledge_heading.add_run({"policy": "关键规定", "operation": "办理步骤", "product": "产品要点"}.get(meta.get("training_type"), "核心知识")).bold = True
            columns = 1 if requirements.get("max_chars") and requirements["max_chars"] <= 500 else 2
            knowledge_table = document.add_table(rows=1, cols=columns)
            cells = list(knowledge_table.rows[0].cells)
            for index, group in enumerate(knowledge_groups):
                if index >= columns and index % columns == 0:
                    cells = list(knowledge_table.add_row().cells)
                cell = cells[index % columns]
                heading = cell.paragraphs[0]
                heading.add_run(group.get("title", "")).bold = True
                for point in group.get("points", []):
                    cell.add_paragraph(point.get("text", ""), style=None)

        if requirements.get("include_practice") is not False and one_pager.get("practical_application"):
            practice_heading = document.add_paragraph()
            practice_heading.add_run("工作中怎么做").bold = True
            for group in one_pager.get("practical_application", []):
                paragraph = document.add_paragraph()
                paragraph.add_run(f"{group.get('title', '')}：").bold = True
                paragraph.add_run("；".join(item.get("text", "") for item in group.get("items", [])))

        if one_pager.get("key_reminders"):
            reminder_heading = document.add_paragraph()
            reminder_heading.add_run("关键提醒").bold = True
            for item in one_pager.get("key_reminders", []):
                paragraph = document.add_paragraph()
                run = paragraph.add_run(f"• {item.get('text', '')}")
                run.bold = True
                run.font.color.rgb = RGBColor(145, 64, 49)

        if one_pager.get("qa_items"):
            document.add_paragraph("材料问答").runs[0].bold = True
            for item in one_pager["qa_items"]:
                document.add_paragraph(f"问：{item['question']}\n答：{item['answer']}")
        _apply_docx_cjk_typography(document, cjk_font)
        stream = io.BytesIO()
        document.save(stream)
        return stream.getvalue()

    table = document.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Cm(10.2)
    table.columns[1].width = Cm(8.2)
    left, right = table.rows[0].cells
    for cell in (left, right):
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
    heading = left.paragraphs[0]
    heading.add_run("核心结论").bold = True
    for index, item in enumerate(one_pager.get("conclusions", []), 1):
        paragraph = left.add_paragraph(style=None)
        paragraph.add_run(f"{index}. ").bold = True
        paragraph.add_run(item.get("text", ""))
    heading = right.paragraphs[0]
    heading.add_run("关键数据").bold = True
    for item in one_pager.get("metrics", []):
        paragraph = right.add_paragraph()
        value = paragraph.add_run(f"{item.get('value', '')} ")
        value.bold = True
        value.font.size = Pt(12)
        paragraph.add_run(f"{item.get('label', '')} {item.get('comparison', '')}".strip())

    logic = one_pager.get("logic", {})
    paragraph = document.add_paragraph()
    paragraph.add_run(f"逻辑结构 · {logic.get('type', '总分总')}").bold = True
    nodes = logic.get("nodes", [])
    document.add_paragraph("  →  ".join(f"{node.get('title', '')}：{node.get('text', '')}" for node in nodes))

    paragraph = document.add_paragraph()
    paragraph.add_run("重点事项").bold = True
    actions_table = document.add_table(rows=1, cols=4)
    for cell, value in zip(actions_table.rows[0].cells, ("优先级/类型", "事项", "负责人", "时间")):
        cell.text = value
    priority_names = {"high": "高", "medium": "中", "low": "低"}
    for item in one_pager.get("actions", []):
        cells = actions_table.add_row().cells
        cells[0].text = f"{priority_names.get(item.get('priority'), '中')}·{item.get('kind', '待办')}"
        cells[1].text = item.get("text", "")
        cells[2].text = item.get("owner", "") or "—"
        cells[3].text = item.get("due", "") or "—"

    if one_pager.get("supplements"):
        paragraph = document.add_paragraph()
        paragraph.add_run("补充信息").bold = True
        for item in one_pager["supplements"]:
            document.add_paragraph(f"{item.get('term', '')}：{item.get('explanation', '')}")

    if one_pager.get("qa_items"):
        document.add_paragraph("材料问答").runs[0].bold = True
        for item in one_pager["qa_items"]:
            document.add_paragraph(f"问：{item['question']}\n答：{item['answer']}")
    _apply_docx_cjk_typography(document, cjk_font)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def mosaicked_asset_bytes(
    asset_id: str, image_regions: list[dict[str, Any]], asset_index: dict[str, dict[str, Any]], lock: Any
) -> bytes:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("当前环境缺少 Pillow，无法导出图片。") from exc

    with lock:
        indexed = asset_index.get(asset_id)
    if not indexed or not indexed["path"].exists():
        raise ValueError("图片预览已失效，请重新上传并解析材料。")

    with Image.open(indexed["path"]) as opened:
        image = opened.convert("RGB")
        for region in image_regions:
            if region.get("asset_id") != asset_id or region.get("status") != "confirmed":
                continue
            left = max(0, min(image.width - 1, round(float(region["x"]) * image.width)))
            top = max(0, min(image.height - 1, round(float(region["y"]) * image.height)))
            right = max(left + 1, min(image.width, round((float(region["x"]) + float(region["width"])) * image.width)))
            bottom = max(top + 1, min(image.height, round((float(region["y"]) + float(region["height"])) * image.height)))
            crop = image.crop((left, top, right, bottom))
            mosaic_width = max(1, crop.width // 18)
            mosaic_height = max(1, crop.height // 18)
            crop = crop.resize((mosaic_width, mosaic_height), Image.Resampling.BILINEAR)
            crop = crop.resize((right - left, bottom - top), Image.Resampling.NEAREST)
            image.paste(crop, (left, top))
        output = io.BytesIO()
        image.save(output, "PNG", optimize=True)
        return output.getvalue()


def _select_export_cjk_font() -> str:
    override = os.getenv("DOCX_CJK_FONT", "").strip()
    if override:
        return override
    if sys.platform == "darwin":
        candidates = (
            ("PingFang SC", Path("/System/Library/Fonts/PingFang.ttc")),
            ("Hiragino Sans GB", Path("/System/Library/Fonts/Hiragino Sans GB.ttc")),
            ("Heiti SC", Path("/System/Library/Fonts/STHeiti Medium.ttc")),
        )
    elif os.name == "nt":
        fonts_dir = Path(os.getenv("WINDIR", r"C:\Windows")) / "Fonts"
        candidates = (
            ("Microsoft YaHei", fonts_dir / "msyh.ttc"),
            ("DengXian", fonts_dir / "Deng.ttf"),
            ("SimSun", fonts_dir / "simsun.ttc"),
        )
    else:
        candidates = (
            ("Noto Sans CJK SC", Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")),
            ("Source Han Sans SC", Path("/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf")),
            ("WenQuanYi Zen Hei", Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")),
        )
    installed = next((name for name, path in candidates if path.exists()), "")
    if installed:
        return installed
    raise RuntimeError(
        "当前环境未检测到可用的中文字体，无法可靠导出 Word。"
        "请安装 Noto Sans CJK SC，或通过 DOCX_CJK_FONT 指定已安装字体。"
    )


def _apply_export_cjk_typography(document: Any, font_name: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def apply_properties(run_properties: Any) -> None:
        fonts = run_properties.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            run_properties.insert(0, fonts)
        for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn(f"w:{attribute}"), font_name)
        fonts.set(qn("w:hint"), "eastAsia")
        for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            fonts.attrib.pop(qn(f"w:{attribute}"), None)
        language = run_properties.find(qn("w:lang"))
        if language is None:
            language = OxmlElement("w:lang")
            run_properties.append(language)
        language.set(qn("w:val"), "zh-CN")
        language.set(qn("w:eastAsia"), "zh-CN")

    for style in document.styles:
        apply_properties(style._element.get_or_add_rPr())
    for run_element in document.element.iter(qn("w:r")):
        apply_properties(run_element.get_or_add_rPr())


def build_intermediate_docx(
    session: dict[str, Any],
    segments: list[dict[str, Any]],
    image_regions: list[dict[str, Any]] | None = None,
    redacted: bool = False,
    *, font_selector=None, image_reader, source_location,
) -> bytes:
    """Build a readable, editable Word document from the normalized local parse stream."""
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor
    except ImportError as exc:
        raise RuntimeError("当前环境缺少 python-docx，无法导出 Word。") from exc

    document = Document()
    section = document.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    cjk_font = (font_selector or _select_export_cjk_font)()
    for style_name, size in (("Normal", 11), ("Title", 20), ("Heading 1", 15), ("Heading 2", 12)):
        style = document.styles[style_name]
        style.font.name = cjk_font
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style._element.rPr.rFonts.set(qn("w:eastAsia"), cjk_font)
        style._element.rPr.rFonts.set(qn("w:ascii"), cjk_font)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), cjk_font)
    title_style_ppr = document.styles["Title"]._element.get_or_add_pPr()
    title_border = title_style_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_style_ppr.remove(title_border)
    document.styles["Normal"].paragraph_format.space_after = Pt(6)

    stem = Path(session.get("file_name") or "材料").stem
    kind = "脱敏文件" if redacted else "解析文件"
    title = document.add_paragraph(f"{stem} {kind}", style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.runs[0].font.color.rgb = RGBColor(0, 0, 0)
    title.runs[0].underline = False
    direct_border = title._p.get_or_add_pPr().find(qn("w:pBdr"))
    if direct_border is not None:
        title._p.get_or_add_pPr().remove(direct_border)
    intro = document.add_paragraph(
        "本文档由本地解析结果重排生成，便于编辑和复用；不等同于原文件版式复刻。"
        + ("文字已按最终确认结果替换，已确认的图片框已做马赛克。" if redacted
           else "该文档可能包含未脱敏信息，请仅在受控环境中使用。")
    )
    intro.alignment = WD_ALIGN_PARAGRAPH.LEFT

    segment_map = {item["id"]: item for item in segments}
    asset_map = {item["id"]: item for item in session.get("image_assets", [])}
    regions = image_regions or []
    blocks = list(session.get("blocks", []))
    current_file = ""
    current_page: tuple[str, int] | None = None
    emitted_segments: set[str] = set()

    for block in blocks:
        file_name = block.get("file_name") or session.get("file_name") or "材料"
        page = int(block.get("page") or 1)
        if file_name != current_file:
            document.add_paragraph(file_name, style="Heading 1")
            current_file = file_name
            current_page = None
        page_key = (file_name, page)
        if page_key != current_page:
            page_label = "幻灯片" if Path(file_name).suffix.lower() in {".ppt", ".pptx"} else "第"
            sheet = segment_map.get(block.get("segment_id", ""), {}).get("sheet", "")
            page_text = f"工作表「{sheet}」" if sheet else (f"{page_label} {page}" if page_label == "幻灯片" else f"第 {page} 页")
            document.add_paragraph(page_text, style="Heading 2")
            current_page = page_key
        if block.get("type") == "text":
            segment_id = block.get("segment_id", "")
            segment = segment_map.get(segment_id)
            if segment and segment_id not in emitted_segments:
                document.add_paragraph(segment.get("text", ""))
                emitted_segments.add(segment_id)
        elif block.get("type") == "image":
            asset_id = block.get("asset_id", "")
            asset = asset_map.get(asset_id)
            if not asset:
                continue
            try:
                image_stream = io.BytesIO(image_reader(asset_id, regions if redacted else []))
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.add_run().add_picture(image_stream, width=Inches(5.8))
                caption = document.add_paragraph(
                    f"{'图表' if asset.get('source', {}).get('kind') == 'pptx_chart' else '图片'}  第 {page} 页"
                )
                caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption.runs[0].font.size = Pt(9)
            except (ValueError, OSError):
                document.add_paragraph(f"[图片无法加载：{asset.get('file_name', file_name)} 第 {page} 页]")

    remaining = [item for item in segments if item["id"] not in emitted_segments]
    if remaining:
        document.add_paragraph("图表数据与备注", style="Heading 1")
        for item in remaining:
            paragraph = document.add_paragraph()
            paragraph.add_run(f"{item.get('file_name', '')} {source_location(item)}  ").bold = True
            paragraph.add_run(item.get("text", ""))

    _apply_export_cjk_typography(document, cjk_font)
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()

