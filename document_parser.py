from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import io
import json
import os
import re
import shutil
import subprocess
from platform_runtime import run_tool
import sys
import tempfile
import zipfile
from datetime import date, datetime, time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable
from app_paths import bundled_tool, resource_dir
from xml.etree import ElementTree as ET


PREVIEW_MAX_EDGE = 1400
PREVIEW_QUALITY = 75


def _local_tool(name: str) -> str | None:
    bundled = bundled_tool(name)
    if bundled:
        return bundled
    if name == "soffice" and sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            directory = os.getenv(variable)
            if directory:
                office = Path(directory) / "LibreOffice/program/soffice.exe"
                if office.is_file():
                    return str(office)
    if name == "soffice":
        office = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if office.is_file():
            return str(office)
    found = shutil.which(name)
    if found:
        return found
    executable = Path(sys.executable).resolve()
    for parent in executable.parents:
        candidate = parent / "bin" / "override" / name
        if candidate.is_file():
            return str(candidate)
    return None


def _render_pptx_pages(path: Path, pages: set[int]) -> dict[int, bytes]:
    """Render only requested slides so native charts can be cropped as images."""
    if not pages:
        return {}
    soffice = _local_tool("soffice")
    pdftoppm = _local_tool("pdftoppm")
    if not soffice or not pdftoppm:
        return {}
    rendered: dict[int, bytes] = {}
    try:
        with tempfile.TemporaryDirectory(prefix="onepager-pptx-") as temp_name:
            temp_dir = Path(temp_name)
            profile_dir = temp_dir / "profile"
            run_tool(
                [soffice, f"-env:UserInstallation={profile_dir.as_uri()}", "--headless",
                 "--convert-to", "pdf", "--outdir", str(temp_dir), str(path)],
                check=True, capture_output=True, timeout=90,
            )
            pdf_path = temp_dir / f"{path.stem}.pdf"
            if not pdf_path.exists():
                return {}
            for page in sorted(pages):
                output_prefix = temp_dir / f"slide-{page}"
                run_tool(
                    [pdftoppm, "-f", str(page), "-l", str(page), "-singlefile", "-png", "-r", "144",
                     str(pdf_path), str(output_prefix)],
                    check=True, capture_output=True, timeout=45,
                )
                output_path = output_prefix.with_suffix(".png")
                if output_path.exists():
                    rendered[page] = output_path.read_bytes()
    except (OSError, subprocess.SubprocessError):
        return {}
    return rendered


def _crop_slide_render(
    page_bytes: bytes | None,
    left: int,
    top: int,
    width: int,
    height: int,
    slide_width: int,
    slide_height: int,
) -> bytes | None:
    if not page_bytes or width <= 0 or height <= 0 or slide_width <= 0 or slide_height <= 0:
        return None
    try:
        from PIL import Image

        with Image.open(io.BytesIO(page_bytes)) as page_image:
            x1 = max(0, min(page_image.width - 1, round(left / slide_width * page_image.width)))
            y1 = max(0, min(page_image.height - 1, round(top / slide_height * page_image.height)))
            x2 = max(x1 + 1, min(page_image.width, round((left + width) / slide_width * page_image.width)))
            y2 = max(y1 + 1, min(page_image.height, round((top + height) / slide_height * page_image.height)))
            cropped = page_image.crop((x1, y1, x2, y2)).convert("RGB")
            output = io.BytesIO()
            cropped.save(output, "PNG", optimize=True)
            return output.getvalue()
    except Exception:
        return None


def _pptx_chart_text(shape: Any) -> str:
    try:
        chart = shape.chart
        title = ""
        if getattr(chart, "has_title", False):
            title = _clean_text(chart.chart_title.text_frame.text)
        categories: list[str] = []
        if chart.plots:
            categories = [_clean_text(str(item)) for item in chart.plots[0].categories]
        parts = [f"图表标题：{title}" if title else "PowerPoint 图表"]
        if categories:
            parts.append("分类：" + "、".join(categories))
        for series in chart.series:
            name = _clean_text(str(series.name or "未命名系列"))
            values = ["" if value is None else str(value) for value in series.values]
            if categories and len(categories) == len(values):
                parts.append(f"系列“{name}”：" + "；".join(
                    f"{category}={value}" for category, value in zip(categories, values)
                ))
            else:
                parts.append(f"系列“{name}”：" + "、".join(values))
        return _clean_text("。".join(parts))
    except Exception:
        return "PowerPoint 图表"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()


def _asset_id(document_id: str, locator: str) -> str:
    digest = hashlib.sha1(f"{document_id}\0{locator}".encode("utf-8")).hexdigest()[:18]
    return f"img-{digest}"


def _save_preview(
    image_bytes: bytes,
    asset_id: str,
    document_id: str,
    file_name: str,
    page: int,
    source: dict[str, Any],
    asset_root: Path,
    register_asset: Callable[[str, Path, str], None],
) -> dict[str, Any] | None:
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(image_bytes)) as opened:
            image = ImageOps.exif_transpose(opened)
            original_width, original_height = image.size
            if original_width < 1 or original_height < 1:
                return None
            image = image.convert("RGB")
            image.thumbnail((PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE))
            preview_width, preview_height = image.size
            document_dir = asset_root / document_id
            document_dir.mkdir(parents=True, exist_ok=True)
            preview_path = document_dir / f"{asset_id}.jpg"
            image.save(preview_path, "JPEG", quality=PREVIEW_QUALITY, optimize=True)
    except Exception:
        return None

    register_asset(asset_id, preview_path, document_id)
    return {
        "id": asset_id,
        "document_id": document_id,
        "file_name": file_name,
        "page": page,
        "original_width": original_width,
        "original_height": original_height,
        "preview_width": preview_width,
        "preview_height": preview_height,
        "preview_url": f"/api/image-assets/{asset_id}",
        "source": source,
    }


def _segment(segment_cls: type, file_name: str, page: int, index: int, text: str, prefix: str = "") -> Any:
    base_id = f"P{page}-{index:02d}"
    return segment_cls(
        id=f"{prefix}-{base_id}" if prefix else base_id,
        file_name=file_name,
        page=page,
        index=index,
        text=_clean_text(text),
    )


def _text_block(segment: Any, order: int, block_id: str | None = None) -> dict[str, Any]:
    return {
        "id": block_id or f"block-{segment.id}",
        "type": "text",
        "segment_id": segment.id,
        "file_name": segment.file_name,
        "page": segment.page,
        "order": order,
    }


def _image_block(asset: dict[str, Any], order: int, block_id: str | None = None) -> dict[str, Any]:
    return {
        "id": block_id or f"block-{asset['id']}",
        "type": "image",
        "asset_id": asset["id"],
        "file_name": asset["file_name"],
        "page": asset["page"],
        "order": order,
    }


def _recognize_images(paths: list[Path]) -> tuple[dict[str, list[str]], bool]:
    """Recognize locally; an unavailable engine never causes content to be discarded."""
    if not paths:
        return {}, True
    native_ocr = bundled_tool("local-ocr")
    if native_ocr:
        try:
            result = run_tool([native_ocr, *(str(path) for path in paths)],
                check=True, capture_output=True, timeout=max(30, len(paths) * 5))
            return json.loads(result.stdout), True
        except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
            pass
    if sys.platform == "darwin" and shutil.which("clang"):
        try:
            with tempfile.TemporaryDirectory(prefix="onepager-ocr-") as temp_name:
                executable = Path(temp_name) / "local-ocr"
                source = Path(__file__).with_name("local_ocr.m")
                run_tool(["clang", "-fobjc-arc", "-framework", "Foundation", "-framework", "Vision",
                                str(source), "-o", str(executable)], check=True, capture_output=True, timeout=30)
                output: dict[str, list[str]] = {}
                for start in range(0, len(paths), 100):
                    batch = paths[start:start + 100]
                    completed = run_tool([str(executable), *(str(path) for path in batch)],
                                               check=True, capture_output=True, timeout=max(30, len(batch) * 5))
                    output.update(json.loads(completed.stdout))
                return output, True
        except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
            pass
    tesseract = _local_tool("tesseract")
    if tesseract:
        try:
            bundled_data = resource_dir() / "tessdata"
            tessdata_args = ["--tessdata-dir", str(bundled_data)] if bundled_data.is_dir() else []
            languages = run_tool([tesseract, *tessdata_args, "--list-langs"], capture_output=True, text=True,
                                       check=True, timeout=10).stdout
            if "chi_sim" in languages or "chi_tra" in languages:
                language = "chi_sim" if "chi_sim" in languages else "chi_tra"
                if "eng" in languages:
                    language += "+eng"
                output = {}
                for path in paths:
                    completed = run_tool([tesseract, str(path), "stdout", *tessdata_args, "-l", language],
                                               capture_output=True, text=True, check=True, timeout=30)
                    output[str(path)] = completed.stdout.splitlines()
                return output, True
        except (OSError, subprocess.SubprocessError):
            pass
    return {}, False


def _filter_and_ocr_images(result: dict[str, Any], asset_root: Path, document_id: str,
                           file_name: str, segment_cls: type, prefix: str,
                           include_all_images: bool = False) -> None:
    assets = [asset for asset in result["image_assets"] if asset.get("source", {}).get("kind") != "pptx_chart"]
    paths = {asset["id"]: asset_root / document_id / f"{asset['id']}.jpg" for asset in assets}
    # A byte-identical image at the same normalized position on several PDF pages
    # is a converter-produced template layer. Its coordinates make it safe to
    # reject before OCR, which avoids repeatedly recognizing large backgrounds.
    repeated_templates = {
        asset["id"] for asset in assets
        if asset.get("source", {}).get("kind") == "pdf_image"
        and asset.get("source", {}).get("repeat_page_count", 0) >= 2
    }
    def safe_repeated_template(asset: dict[str, Any]) -> bool:
        source = asset.get("source", {})
        bbox = source.get("bbox") or []
        page_width, page_height = source.get("page_width"), source.get("page_height")
        if len(bbox) != 4 or not page_width or not page_height:
            return False
        left, top, right, bottom = bbox
        width, height = (right - left) / page_width, (bottom - top) / page_height
        area = width * height
        touches_edge = (left / page_width < 0.02 or top / page_height < 0.02 or
                        right / page_width > 0.98 or bottom / page_height > 0.98)
        return area >= 0.85 or area < 0.03 or min(width, height) < 0.035 or (
            touches_edge and area > 0.15 and max(width, height) > 0.5
        )
    safe_repeated_templates = {
        asset["id"] for asset in assets
        if asset["id"] in repeated_templates and safe_repeated_template(asset)
    }
    ocr_paths = [path for asset_id, path in paths.items()
                 if include_all_images or asset_id not in safe_repeated_templates]
    recognized, available = _recognize_images(ocr_paths)
    def placement(asset: dict[str, Any]) -> tuple[float, ...] | None:
        source = asset["source"]
        if source.get("kind") == "pptx_picture" and result.get("slide_size"):
            width, height = result["slide_size"]
            return tuple(round(source[key] / dimension, 2) for key, dimension in
                         (("left", width), ("top", height), ("width", width), ("height", height)))
        if source.get("kind") == "pdf_image" and source.get("page_width") and source.get("page_height"):
            left, top, right, bottom = source["bbox"]
            width, height = source["page_width"], source["page_height"]
            return tuple(round(value, 2) for value in
                         (left / width, top / height, (right - left) / width, (bottom - top) / height))
        return None

    fingerprints: dict[str, str] = {}
    same_positions: dict[tuple[str, tuple[float, ...]], set[int]] = {}
    for asset in assets:
        path = paths[asset["id"]]
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        fingerprints[asset["id"]] = digest
        box = placement(asset)
        if box:
            same_positions.setdefault((digest, box), set()).add(asset["page"])
    discarded: set[str] = set()
    added: list[tuple[dict[str, Any], str]] = []
    existing = {item.page: " ".join(segment.text for segment in result["segments"] if segment.page == item.page)
                for item in result["segments"]}
    for asset in assets:
        path = paths[asset["id"]]
        lines = [_clean_text(line) for line in recognized.get(str(path), []) if _clean_text(line)]
        text = _clean_text(" ".join(lines))
        characters = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))
        box = placement(asset)
        repeated_at_same_place = (asset["id"] in repeated_templates or
                                  bool(box and len(same_positions.get(
                                      (fingerprints.get(asset["id"], ""), box), set())) >= 2))
        header_or_footer = asset["source"].get("kind", "").startswith(("docx_header", "docx_footer"))
        repeated_short_label = (repeated_at_same_place and asset["source"].get("kind") != "pdf_image")
        short_template_label = (repeated_short_label or asset["id"] in safe_repeated_templates or
                                header_or_footer) and len(lines) <= 2 and characters <= 60
        meaningful = characters >= 8 and not short_template_label
        if meaningful:
            if text not in existing.get(asset["page"], ""):
                added.append((asset, text))
            continue
        if asset["id"] in safe_repeated_templates and not include_all_images:
            discarded.add(asset["id"])
            continue
        if not available:
            continue
        width, height = asset["original_width"], asset["original_height"]
        ratio = min(width, height) / max(width, height)
        page_area = box[2] * box[3] if box else None
        small_on_page = page_area is not None and page_area < 0.015
        narrow_on_page = box is not None and min(box[2], box[3]) < 0.035
        single_background = False
        if (box and asset["source"].get("kind") in {"pptx_picture", "pdf_image"} and page_area >= 0.85
                and existing.get(asset["page"]) and path.exists()):
            try:
                from PIL import Image
                with Image.open(path) as image:
                    single_background = image.convert("L").resize((128, 128)).entropy() < 3
            except Exception:
                pass
        # Preserve uncertain body images and full-page scans for review.
        if not include_all_images and (repeated_at_same_place or single_background or
                (header_or_footer and characters <= 60) or
                small_on_page or narrow_on_page or (box is None and width * height < 25000) or
                (box is None and ratio < 0.08)):
            discarded.add(asset["id"])
    result["image_assets"] = [asset for asset in result["image_assets"] if asset["id"] not in discarded]
    result["blocks"] = [block for block in result["blocks"] if block.get("asset_id") not in discarded]
    for asset_id in discarded:
        try:
            paths[asset_id].unlink(missing_ok=True)
        except OSError:
            pass
    next_index: dict[int, int] = {}
    for segment in result["segments"]:
        next_index[segment.page] = max(next_index.get(segment.page, 0), segment.index)
    for asset, text in added:
        page = asset["page"]
        next_index[page] = next_index.get(page, 0) + 1
        segment = _segment(segment_cls, file_name, page, next_index[page], text, prefix)
        result["segments"].append(segment)
        image_block = next((block for block in result["blocks"] if block.get("asset_id") == asset["id"]), None)
        block = _text_block(segment, (image_block or {}).get("order", 0) + 0.01)
        block["source"] = {**asset["source"], "kind": "image_ocr", "asset_id": asset["id"]}
        result["blocks"].append(block)
    result["image_filter"] = {
        "ignored_count": len(discarded) + int(result.pop("_preignored_image_count", 0)),
        "merged_fragment_count": int(result.pop("_merged_fragment_count", 0)),
        "ocr_available": available,
        "recognized_count": len(added),
    }


def parse_pptx_structured(
    path: Path,
    file_name: str,
    document_id: str,
    segment_cls: type,
    asset_root: Path,
    register_asset: Callable[[str, Path, str], None],
    prefix: str = "",
) -> dict[str, Any]:
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except Exception as exc:
        raise RuntimeError("当前 Python 环境缺少 python-pptx，无法解析 PowerPoint。") from exc

    presentation = Presentation(str(path))
    segments: list[Any] = []
    blocks: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []

    def shape_type_or_none(shape: Any):
        try:
            return shape.shape_type
        except NotImplementedError:
            return None

    def walk_shapes(shapes: Any):
        for shape in shapes:
            yield shape
            if shape_type_or_none(shape) == MSO_SHAPE_TYPE.GROUP:
                yield from walk_shapes(shape.shapes)

    chart_pages = {
        page
        for page, slide in enumerate(presentation.slides, start=1)
        if any(getattr(shape, "has_chart", False) for shape in walk_shapes(slide.shapes))
    }
    rendered_chart_pages = _render_pptx_pages(path, chart_pages)
    slide_width = int(presentation.slide_width)
    slide_height = int(presentation.slide_height)

    for page, slide in enumerate(presentation.slides, start=1):
        text_index = 0
        order = 0
        for shape_order, shape in enumerate(walk_shapes(slide.shapes), start=1):
            order += 1
            if shape_type_or_none(shape) == MSO_SHAPE_TYPE.PICTURE:
                locator = f"slide:{page}:shape:{shape.shape_id}"
                asset_id = _asset_id(document_id, locator)
                source = {
                    "kind": "pptx_picture",
                    "slide": page,
                    "shape_id": shape.shape_id,
                    "shape_order": shape_order,
                    "left": int(shape.left),
                    "top": int(shape.top),
                    "width": int(shape.width),
                    "height": int(shape.height),
                    "rotation": float(shape.rotation or 0),
                    "crop_left": float(shape.crop_left or 0),
                    "crop_top": float(shape.crop_top or 0),
                    "crop_right": float(shape.crop_right or 0),
                    "crop_bottom": float(shape.crop_bottom or 0),
                }
                asset = _save_preview(
                    shape.image.blob, asset_id, document_id, file_name, page,
                    source, asset_root, register_asset,
                )
                if asset:
                    assets.append(asset)
                    blocks.append(_image_block(asset, order))
                continue

            if getattr(shape, "has_chart", False):
                locator = f"slide:{page}:chart:{shape.shape_id}"
                asset_id = _asset_id(document_id, locator)
                chart_text = _pptx_chart_text(shape)
                source = {
                    "kind": "pptx_chart",
                    "slide": page,
                    "shape_id": shape.shape_id,
                    "shape_order": shape_order,
                    "left": int(shape.left),
                    "top": int(shape.top),
                    "width": int(shape.width),
                    "height": int(shape.height),
                    "chart_type": str(shape.chart.chart_type),
                }
                chart_bytes = _crop_slide_render(
                    rendered_chart_pages.get(page),
                    int(shape.left), int(shape.top), int(shape.width), int(shape.height),
                    slide_width, slide_height,
                )
                if chart_bytes:
                    asset = _save_preview(
                        chart_bytes, asset_id, document_id, file_name, page,
                        source, asset_root, register_asset,
                    )
                    if asset:
                        assets.append(asset)
                        blocks.append(_image_block(asset, order))
                if chart_text:
                    text_index += 1
                    segment = _segment(segment_cls, file_name, page, text_index, chart_text, prefix)
                    segments.append(segment)
                    chart_block = _text_block(segment, order, f"block-{segment.id}-{shape.shape_id}-chart-data")
                    chart_block["source"] = {
                        **source,
                        "kind": "pptx_chart_data",
                        "annotation": True,
                    }
                    blocks.append(chart_block)
                continue

            texts: list[str] = []
            if getattr(shape, "has_text_frame", False):
                value = _clean_text(shape.text)
                if value:
                    texts.append(value)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    value = " | ".join(_clean_text(cell.text) for cell in row.cells if _clean_text(cell.text))
                    if value:
                        texts.append(value)
            for value in texts:
                text_index += 1
                segment = _segment(segment_cls, file_name, page, text_index, value, prefix)
                segments.append(segment)
                block = _text_block(segment, order, f"block-{segment.id}-{shape.shape_id}")
                block["source"] = {
                    "kind": "pptx_text",
                    "shape_id": shape.shape_id,
                    "left": int(shape.left),
                    "top": int(shape.top),
                    "width": int(shape.width),
                    "height": int(shape.height),
                }
                blocks.append(block)

    return {"segments": segments, "blocks": blocks, "image_assets": assets,
            "page_count": len(presentation.slides), "slide_size": (slide_width, slide_height)}


def _relationship_images(element: Any, document_part: Any) -> list[tuple[str, bytes, str]]:
    namespace = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    output: list[tuple[str, bytes, str]] = []
    seen: set[str] = set()
    for blip in element.findall(".//a:blip", namespace):
        relationship_id = blip.get(f"{{{namespace['r']}}}embed")
        if not relationship_id or relationship_id in seen:
            continue
        seen.add(relationship_id)
        related = document_part.related_parts.get(relationship_id)
        blob = getattr(related, "blob", None)
        if blob:
            output.append((relationship_id, blob, getattr(related, "content_type", "application/octet-stream")))
    return output


def parse_docx_structured(
    path: Path,
    file_name: str,
    document_id: str,
    segment_cls: type,
    asset_root: Path,
    register_asset: Callable[[str, Path, str], None],
    prefix: str = "",
) -> dict[str, Any]:
    try:
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except Exception as exc:
        raise RuntimeError("当前 Python 环境缺少 python-docx，无法解析 Word。") from exc

    document = Document(str(path))
    segments: list[Any] = []
    blocks: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    text_index = 0
    order = 0
    image_index = 0

    def append_images(element: Any, source_kind: str, owning_part: Any | None = None) -> None:
        nonlocal order, image_index
        for relationship_id, blob, content_type in _relationship_images(element, owning_part or document.part):
            image_index += 1
            order += 1
            locator = f"word:image:{image_index}:{relationship_id}"
            asset_id = _asset_id(document_id, locator)
            asset = _save_preview(
                blob, asset_id, document_id, file_name, 1,
                {"kind": source_kind, "relationship_id": relationship_id, "content_type": content_type,
                 "order": image_index},
                asset_root, register_asset,
            )
            if asset:
                assets.append(asset)
                blocks.append(_image_block(asset, order))

    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph = Paragraph(child, document)
            value = _clean_text(paragraph.text)
            if value:
                text_index += 1
                order += 1
                segment = _segment(segment_cls, file_name, 1, text_index, value, prefix)
                segments.append(segment)
                blocks.append(_text_block(segment, order))
            # python-docx 的 Paragraph.text 不一定包含浮动文本框中的 w:t。
            # 单独读取文本框，确保可见文字也参与扫描和预览。
            textbox_nodes = child.findall(
                ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}txbxContent"
            )
            for textbox_index, textbox in enumerate(textbox_nodes, start=1):
                textbox_value = _clean_text(" ".join(
                    node.text or "" for node in textbox.iter()
                    if node.tag.rsplit("}", 1)[-1] == "t"
                ))
                if not textbox_value or textbox_value == value:
                    continue
                text_index += 1
                order += 1
                segment = _segment(segment_cls, file_name, 1, text_index, textbox_value, prefix)
                segments.append(segment)
                block = _text_block(segment, order)
                block["source"] = {"kind": "docx_textbox", "textbox": textbox_index}
                blocks.append(block)
            append_images(child, "docx_picture")
        elif tag == "tbl":
            table = Table(child, document)
            for row_index, row in enumerate(table.rows, start=1):
                value = " | ".join(_clean_text(cell.text) for cell in row.cells if _clean_text(cell.text))
                if value:
                    text_index += 1
                    order += 1
                    segment = _segment(segment_cls, file_name, 1, text_index, value, prefix)
                    segments.append(segment)
                    block = _text_block(segment, order)
                    block["source"] = {"kind": "docx_table", "row": row_index}
                    blocks.append(block)
            append_images(child, "docx_table_picture")

    seen_story_parts: set[str] = set()
    for section in document.sections:
        for story_kind, story in (("docx_header", section.header), ("docx_footer", section.footer)):
            part_name = str(story.part.partname)
            if part_name in seen_story_parts:
                continue
            seen_story_parts.add(part_name)
            for paragraph in story.paragraphs:
                value = _clean_text(paragraph.text)
                if value:
                    text_index += 1
                    order += 1
                    segment = _segment(segment_cls, file_name, 1, text_index, value, prefix)
                    segments.append(segment)
                    block = _text_block(segment, order)
                    block["source"] = {"kind": story_kind}
                    blocks.append(block)
                append_images(paragraph._element, f"{story_kind}_picture", story.part)
            for table in story.tables:
                for row_index, row in enumerate(table.rows, start=1):
                    value = " | ".join(_clean_text(cell.text) for cell in row.cells if _clean_text(cell.text))
                    if value:
                        text_index += 1
                        order += 1
                        segment = _segment(segment_cls, file_name, 1, text_index, value, prefix)
                        segments.append(segment)
                        block = _text_block(segment, order)
                        block["source"] = {"kind": f"{story_kind}_table", "row": row_index}
                        blocks.append(block)
                append_images(table._element, f"{story_kind}_table_picture", story.part)

    return {"segments": segments, "blocks": blocks, "image_assets": assets, "page_count": 1}


def _import_pymupdf() -> Any | None:
    try:
        import pymupdf
        return pymupdf
    except Exception:
        try:
            import fitz
            return fitz
        except Exception:
            return None


def parse_pdf_structured(
    path: Path,
    file_name: str,
    document_id: str,
    segment_cls: type,
    asset_root: Path,
    register_asset: Callable[[str, Path, str], None],
    prefix: str = "",
) -> dict[str, Any]:
    pymupdf = _import_pymupdf()
    if pymupdf is None:
        return _parse_pdf_fallback(path, file_name, document_id, segment_cls, asset_root, register_asset, prefix)

    document = pymupdf.open(str(path))
    segments: list[Any] = []
    blocks: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    page_images: dict[int, list[dict[str, Any]]] = {}
    occurrence_pages: dict[tuple[str, tuple[float, ...]], set[int]] = {}
    duplicate_count = 0
    merged_fragment_count = 0

    try:
        # Read all coordinates first. PDF converters commonly emit the same
        # master-slide bitmap on every page and split one diagram into dozens of
        # overlapping XObjects; both patterns need document-level context.
        for page_number, page in enumerate(document, start=1):
            page_dict = page.get_text("dict", sort=True)
            text_index = 0
            order = 0
            image_index = 0
            seen_on_page: set[tuple[str, tuple[float, ...]]] = set()
            page_width, page_height = float(page.rect.width), float(page.rect.height)
            for raw_block in page_dict.get("blocks", []):
                order += 1
                if raw_block.get("type") == 0:
                    lines: list[str] = []
                    for line in raw_block.get("lines", []):
                        value = "".join(span.get("text", "") for span in line.get("spans", []))
                        if _clean_text(value):
                            lines.append(value)
                    value = _clean_text(" ".join(lines))
                    if not value:
                        continue
                    text_index += 1
                    segment = _segment(segment_cls, file_name, page_number, text_index, value, prefix)
                    segments.append(segment)
                    block = _text_block(segment, order)
                    block["source"] = {"kind": "pdf_text", "bbox": list(raw_block.get("bbox", ())) }
                    blocks.append(block)
                elif raw_block.get("type") == 1 and raw_block.get("image"):
                    bbox = tuple(float(value) for value in raw_block.get("bbox", ()))
                    if len(bbox) != 4 or bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                        continue
                    image_index += 1
                    digest = hashlib.sha256(raw_block["image"] + (raw_block.get("mask") or b"")).hexdigest()
                    normalized = tuple(round(value, 3) for value in (
                        bbox[0] / page_width, bbox[1] / page_height,
                        (bbox[2] - bbox[0]) / page_width, (bbox[3] - bbox[1]) / page_height,
                    ))
                    occurrence_key = (digest, normalized)
                    if occurrence_key in seen_on_page:
                        duplicate_count += 1
                        continue
                    seen_on_page.add(occurrence_key)
                    occurrence_pages.setdefault(occurrence_key, set()).add(page_number)
                    page_images.setdefault(page_number, []).append({
                        "image": raw_block["image"], "bbox": bbox,
                        "occurrence_key": occurrence_key, "order": order,
                        "image_index": image_index, "extension": raw_block.get("ext", ""),
                        "has_mask": bool(raw_block.get("mask")),
                        "page_width": page_width, "page_height": page_height,
                    })

        for page_number, entries in page_images.items():
            page = document[page_number - 1]
            ordinary = [entry for entry in entries
                        if len(occurrence_pages[entry["occurrence_key"]]) < 2]
            templates = [entry for entry in entries
                         if len(occurrence_pages[entry["occurrence_key"]]) >= 2]
            groups: list[list[dict[str, Any]]] = []
            remaining = list(ordinary)
            while remaining:
                group = [remaining.pop(0)]
                changed = True
                while changed:
                    changed = False
                    left = min(item["bbox"][0] for item in group)
                    top = min(item["bbox"][1] for item in group)
                    right = max(item["bbox"][2] for item in group)
                    bottom = max(item["bbox"][3] for item in group)
                    for candidate in list(remaining):
                        box = candidate["bbox"]
                        if (min(right, box[2]) > max(left, box[0]) and
                                min(bottom, box[3]) > max(top, box[1])):
                            group.append(candidate)
                            remaining.remove(candidate)
                            changed = True
                groups.append(group)
            # A page with many adjacent converter fragments is one logical
            # diagram even if transparent gaps prevent geometric overlap.
            if len(ordinary) >= 8:
                groups = [ordinary]

            prepared: list[dict[str, Any]] = list(templates)
            for group in groups:
                if len(group) == 1:
                    prepared.extend(group)
                    continue
                bbox = (
                    min(item["bbox"][0] for item in group), min(item["bbox"][1] for item in group),
                    max(item["bbox"][2] for item in group), max(item["bbox"][3] for item in group),
                )
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(bbox), alpha=False)
                prepared.append({
                    **group[0], "image": pixmap.tobytes("png"), "bbox": bbox,
                    "extension": "png", "composite": True, "fragment_count": len(group),
                    "order": min(item["order"] for item in group),
                })
                merged_fragment_count += len(group) - 1

            for output_index, entry in enumerate(sorted(prepared, key=lambda item: item["order"]), start=1):
                repeat_page_count = len(occurrence_pages.get(entry["occurrence_key"], ()))
                image_bytes = entry["image"]
                extension = entry["extension"]
                if entry.get("has_mask") and not entry.get("composite") and repeat_page_count < 2:
                    # PyMuPDF exposes the base bitmap and transparency mask
                    # separately. Saving only the base produces black-backed
                    # logos, so render the visible page crop for review/OCR.
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2),
                                             clip=pymupdf.Rect(entry["bbox"]), alpha=False)
                    image_bytes, extension = pixmap.tobytes("png"), "png"
                locator = f"pdf:page:{page_number}:image:{output_index}"
                asset_id = _asset_id(document_id, locator)
                source = {
                    "kind": "pdf_image", "bbox": list(entry["bbox"]),
                    "page_width": entry["page_width"], "page_height": entry["page_height"],
                    "image_index": output_index, "extension": extension,
                    "repeat_page_count": repeat_page_count,
                }
                if entry.get("composite"):
                    source.update({"composite": True, "fragment_count": entry["fragment_count"]})
                asset = _save_preview(image_bytes, asset_id, document_id, file_name, page_number,
                                      source, asset_root, register_asset)
                if asset:
                    assets.append(asset)
                    blocks.append(_image_block(asset, entry["order"]))
        page_count = len(document)
    finally:
        document.close()
    return {"segments": segments, "blocks": blocks, "image_assets": assets, "page_count": page_count,
            "pdf_positioning_available": True,
            "_preignored_image_count": duplicate_count, "_merged_fragment_count": merged_fragment_count}


def _parse_pdf_fallback(
    path: Path,
    file_name: str,
    document_id: str,
    segment_cls: type,
    asset_root: Path,
    register_asset: Callable[[str, Path, str], None],
    prefix: str,
) -> dict[str, Any]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("当前 Python 环境缺少 PyMuPDF 或 pypdf，无法解析 PDF。") from exc
    reader = PdfReader(str(path))
    segments: list[Any] = []
    blocks: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        lines = [_clean_text(line) for line in (page.extract_text() or "").splitlines() if _clean_text(line)]
        for index, value in enumerate(lines, start=1):
            segment = _segment(segment_cls, file_name, page_number, index, value, prefix)
            segments.append(segment)
            blocks.append(_text_block(segment, index))
        for image_index, image_file in enumerate(getattr(page, "images", []), start=1):
            asset_id = _asset_id(document_id, f"pdf:page:{page_number}:fallback:{image_index}")
            asset = _save_preview(
                image_file.data, asset_id, document_id, file_name, page_number,
                {"kind": "pdf_image", "image_index": image_index, "fallback": True,
                 "bbox": [0, 0, 0, 0], "position_known": False},
                asset_root, register_asset,
            )
            if asset:
                assets.append(asset)
                blocks.append(_image_block(asset, len(blocks) + 1))
    return {"segments": segments, "blocks": blocks, "image_assets": assets, "page_count": len(reader.pages),
            "pdf_positioning_available": False}


def parse_txt_structured(path: Path, file_name: str, segment_cls: type, prefix: str = "") -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    segments: list[Any] = []
    blocks: list[dict[str, Any]] = []
    for index, raw_line in enumerate((line for line in raw.splitlines() if _clean_text(line)), start=1):
        segment = _segment(segment_cls, file_name, 1, index, raw_line, prefix)
        segments.append(segment)
        blocks.append(_text_block(segment, index))
    return {"segments": segments, "blocks": blocks, "image_assets": [], "page_count": 1,
            "document_preview": {"mode": "flow", "format": "txt", "flow_blocks": [
                {"id": f"flow-{item.id}", "kind": "paragraph", "segment_ids": [item.id], "order": index}
                for index, item in enumerate(segments, start=1)
            ]}}


def _spreadsheet_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    return _clean_text(str(value))


def _column_label(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


class _HtmlSpreadsheetParser(HTMLParser):
    """Read the HTML table format commonly exported with an .xls suffix."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str | None]]] = []
        self._table_depth = 0
        self._row: list[str | None] | None = None
        self._cell: list[str] | None = None
        self._colspan = 1
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self.tables.append([])
        elif tag == "tr" and self._table_depth == 1:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None and self._cell is None:
            self._cell = []
            raw = dict(attrs).get("colspan") or "1"
            self._colspan = min(1000, max(1, int(raw))) if raw.isdigit() else 1
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(_clean_text("".join(self._cell)))
            self._row.extend([None] * (self._colspan - 1))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.tables[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._cell is not None and not self._skip_depth:
            self._cell.append(data)


def _html_spreadsheet_rows(path: Path) -> list[tuple[str, list[list[str | None]]]] | None:
    raw = path.read_bytes()
    if not re.match(rb"\s*(?:\xef\xbb\xbf)?\s*(?:<!doctype\s+html|<html\b)", raw[:512], re.I):
        return None
    declared = re.search(rb"<meta[^>]+charset\s*=\s*['\"]?([\w-]+)", raw[:4096], re.I)
    encodings = [declared.group(1).decode("ascii", "ignore") if declared else "utf-8", "utf-8-sig", "gb18030"]
    content = None
    for encoding in encodings:
        try:
            content = raw.decode(encoding)
            break
        except (UnicodeError, LookupError):
            continue
    if content is None:
        raise ValueError("无法识别 HTML 表格的文字编码。")
    parser = _HtmlSpreadsheetParser()
    parser.feed(content)
    if not parser.tables:
        raise ValueError("该 .xls 文件是 HTML 页面，但没有可读取的表格。")
    return [(f"表格{index}", rows) for index, rows in enumerate(parser.tables, start=1)]


def parse_spreadsheet_structured(path: Path, file_name: str, segment_cls: type,
                                 prefix: str = "") -> dict[str, Any]:
    extension = path.suffix.lower()
    book = None
    html_rows = _html_spreadsheet_rows(path) if extension == ".xls" else None
    try:
        if html_rows is not None:
            sheets = html_rows
        elif extension == ".xlsx":
            from openpyxl import load_workbook
            book = load_workbook(path, read_only=True, data_only=True)
            sheets = [(sheet.title, sheet.iter_rows(values_only=True)) for sheet in book.worksheets]
        else:
            import xlrd
            book = xlrd.open_workbook(path, on_demand=True)
            def xls_rows(sheet: Any) -> Any:
                for row_number in range(sheet.nrows):
                    values = []
                    for cell in sheet.row(row_number):
                        if cell.ctype == xlrd.XL_CELL_DATE:
                            values.append(xlrd.xldate_as_datetime(cell.value, book.datemode))
                        elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                            values.append(None)
                        elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                            values.append(bool(cell.value))
                        elif cell.ctype == xlrd.XL_CELL_ERROR:
                            values.append(xlrd.error_text_from_code.get(cell.value, "#ERROR"))
                        else:
                            values.append(cell.value)
                    yield values
            sheets = [(sheet.name, xls_rows(sheet)) for sheet in book.sheets()]
    except ImportError as exc:
        raise RuntimeError("缺少表格解析依赖，请安装 requirements.txt 中的 openpyxl 和 xlrd。") from exc
    except Exception as exc:
        raise ValueError(f"无法打开表格文件：{exc}") from exc

    segments, blocks, flow_blocks = [], [], []
    cell_count = char_count = 0
    try:
        for sheet_number, (sheet_name, rows) in enumerate(sheets, start=1):
            for row_number, row in enumerate(rows, start=1):
                if row_number > 50000:
                    raise ValueError("表格超过每个工作表 50000 行的解析上限。")
                cells = [(column, _spreadsheet_value(value)) for column, value in enumerate(row, start=1)
                         if value is not None]
                cells = [(column, value) for column, value in cells if value]
                if not cells:
                    continue
                cell_count += len(cells)
                if cell_count > 250000:
                    raise ValueError("表格超过 250000 个非空单元格的解析上限。")
                content = "；".join(f"{_column_label(column)}: {value}" for column, value in cells)
                text = f"工作表「{sheet_name}」第{row_number}行｜{content}"
                char_count += len(text)
                if char_count > 5000000:
                    raise ValueError("表格超过 500 万字符的解析上限。")
                segment = _segment(segment_cls, file_name, sheet_number, row_number, text, prefix)
                segment.sheet = sheet_name
                segments.append(segment)
                blocks.append(_text_block(segment, len(blocks) + 1))
                flow_blocks.append({"id": f"flow-{segment.id}", "kind": "table_row",
                                    "segment_ids": [segment.id], "order": len(flow_blocks) + 1})
    finally:
        if book is not None:
            book.close() if extension == ".xlsx" else book.release_resources()
    return {"segments": segments, "blocks": blocks, "image_assets": [], "page_count": len(sheets),
            "document_preview": {"mode": "flow", "format": extension.lstrip("."),
                                 "flow_blocks": flow_blocks,
                                 "spreadsheet_notice": "仅提取单元格内容；未复刻格式或解析图表。公式只读取文件中保存的结果，无结果的公式不会显示。"}}


def _normalized_box(source: dict[str, Any], width: float, height: float) -> dict[str, float]:
    if "bbox" in source and len(source.get("bbox") or []) == 4:
        left, top, right, bottom = source["bbox"]
        return {"x": max(0, left / width), "y": max(0, top / height),
                "width": max(0.002, (right - left) / width), "height": max(0.002, (bottom - top) / height)}
    return {"x": max(0, float(source.get("left", 0)) / width),
            "y": max(0, float(source.get("top", 0)) / height),
            "width": max(0.002, float(source.get("width", 0)) / width),
            "height": max(0.002, float(source.get("height", 0)) / height)}


def _pptx_preview(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    from pptx import Presentation
    presentation = Presentation(str(path))
    width, height = float(presentation.slide_width), float(presentation.slide_height)
    pages = []
    for page in range(1, len(presentation.slides) + 1):
        grouped: dict[str, dict[str, Any]] = {}
        annotations: list[dict[str, Any]] = []
        for block in [item for item in result["blocks"] if item.get("page") == page]:
            source = block.get("source") or {}
            if source.get("annotation"):
                annotations.append({"id": block["id"], "kind": source.get("kind", "annotation"),
                                    "segment_ids": [block["segment_id"]], "order": block.get("order", 0)})
                continue
            if block["type"] == "image":
                asset = next((item for item in result["image_assets"] if item["id"] == block.get("asset_id")), None)
                source = (asset or {}).get("source") or source
                element_id = block["id"]
                grouped[element_id] = {"id": element_id, "kind": "image", "asset_id": block.get("asset_id"),
                                       "order": block.get("order", 0), "box": _normalized_box(source, width, height)}
                continue
            shape_id = str(source.get("shape_id", block["id"]))
            element = grouped.setdefault(shape_id, {"id": f"shape-{page}-{shape_id}", "kind": "text",
                "segment_ids": [], "order": block.get("order", 0), "box": _normalized_box(source, width, height)})
            element["segment_ids"].append(block["segment_id"])
        pages.append({"id": f"slide-{page}", "number": page, "width": width, "height": height,
                      "aspect_ratio": width / height, "elements": sorted(grouped.values(), key=lambda x: x["order"]),
                      "annotations": annotations})
    return {"mode": "paged", "format": "pptx", "pages": pages, "legacy_layout_warning": False}


def _docx_preview(result: dict[str, Any]) -> dict[str, Any]:
    flow = []
    for order, block in enumerate(result["blocks"], start=1):
        if block["type"] == "image":
            flow.append({"id": f"flow-{block['id']}", "kind": "image", "asset_id": block.get("asset_id"), "order": order})
        else:
            source = block.get("source") or {}
            flow.append({"id": f"flow-{block['id']}", "kind": "table_row" if "table" in source.get("kind", "") else "paragraph",
                         "segment_ids": [block["segment_id"]], "order": order, "story": source.get("kind", "body")})
    return {"mode": "flow", "format": "docx", "flow_blocks": flow, "legacy_layout_warning": False}


def _pdf_preview(path: Path, result: dict[str, Any], document_id: str, file_name: str,
                 asset_root: Path, register_asset: Callable[[str, Path, str], None]) -> dict[str, Any]:
    pymupdf = _import_pymupdf()
    if pymupdf is None:
        return {"mode": "paged", "format": "pdf", "pages": [
            {"id": f"pdf-page-{page}", "number": page, "width": 1, "height": 1, "aspect_ratio": 0.707,
             "elements": [{"id": block["id"], "kind": block["type"], "order": block.get("order", 0),
                           **({"segment_ids": [block["segment_id"]]} if block["type"] == "text"
                              else {"asset_id": block.get("asset_id")})}
                          for block in result["blocks"] if block.get("page") == page]}
            for page in range(1, result.get("page_count", 1) + 1)
        ], "legacy_layout_warning": True}
    document = pymupdf.open(str(path))
    pages = []
    for number, page in enumerate(document, start=1):
        rect = page.rect
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.35, 1.35), alpha=False)
        page_asset = _save_preview(pixmap.tobytes("png"), _asset_id(document_id, f"pdf-page-preview:{number}"),
                                   document_id, file_name, number, {"kind": "pdf_page_preview"},
                                   asset_root, register_asset)
        elements = []
        for block in [item for item in result["blocks"] if item.get("page") == number]:
            source = block.get("source") or {}
            box = _normalized_box(source, float(rect.width), float(rect.height))
            elements.append({"id": block["id"], "kind": block["type"], "order": block.get("order", 0), "box": box,
                             **({"segment_ids": [block["segment_id"]]} if block["type"] == "text" else {"asset_id": block.get("asset_id")})})
        pages.append({"id": f"pdf-page-{number}", "number": number, "width": rect.width, "height": rect.height,
                      "aspect_ratio": rect.width / rect.height, "background_url": (page_asset or {}).get("preview_url", ""),
                      "elements": sorted(elements, key=lambda x: x["order"])})
    document.close()
    return {"mode": "paged", "format": "pdf", "pages": pages, "legacy_layout_warning": False}


def _append_ooxml_annotations(path: Path, result: dict[str, Any], file_name: str,
                              segment_cls: type, prefix: str = "") -> None:
    patterns = []
    if path.suffix.lower() == ".pptx":
        patterns = [(re.compile(r"ppt/notesSlides/notesSlide(\d+)\.xml$"), "pptx_note"),
                    (re.compile(r"ppt/comments/comment(\d+)\.xml$"), "pptx_comment")]
    elif path.suffix.lower() == ".docx":
        patterns = [(re.compile(r"word/comments\.xml$"), "docx_comment")]
    if not patterns:
        return
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                matched = next(((pattern, kind, pattern.search(name)) for pattern, kind in patterns if pattern.search(name)), None)
                if not matched:
                    continue
                _, kind, match = matched
                page = int(match.group(1)) if match.lastindex else 1
                root = ET.fromstring(archive.read(name))
                texts = [_clean_text(node.text or "") for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "t"]
                value = _clean_text(" ".join(item for item in texts if item))
                if not value:
                    continue
                same_page = [item for item in result["segments"] if item.page == page]
                index = max((item.index for item in same_page), default=0) + 1
                segment = _segment(segment_cls, file_name, page, index, value, prefix)
                result["segments"].append(segment)
                block = _text_block(segment, len(result["blocks"]) + 1, f"block-{kind}-{segment.id}")
                block["source"] = {"kind": kind, "annotation": True}
                result["blocks"].append(block)
    except (OSError, zipfile.BadZipFile, ET.ParseError):
        return


def parse_legacy_ppt(path: Path, file_name: str, document_id: str, segment_cls: type,
                     asset_root: Path, register_asset: Callable[[str, Path, str], None],
                     prefix: str = "", include_all_images: bool = False) -> dict[str, Any]:
    soffice = _local_tool("soffice")
    if not soffice:
        raise ValueError("旧版 PPT 需要本机安装 LibreOffice 才能解析。请安装后重试，或将文件另存为 PPTX 再上传。")
    # Keep conversion files beside the uploaded material so the runtime cleanup also covers crashes.
    with tempfile.TemporaryDirectory(prefix="onepager-legacy-ppt-", dir=path.parent) as temp_name:
        temp_dir = Path(temp_name)
        converted = temp_dir / f"{path.stem}.pptx"
        try:
            run_tool(
                [soffice, f"-env:UserInstallation={(temp_dir / 'profile').as_uri()}",
                 "--headless", "--convert-to", "pptx", "--outdir", str(temp_dir), str(path)],
                check=True, capture_output=True, timeout=120,
            )
            if not converted.is_file() or converted.stat().st_size == 0:
                raise ValueError("转换结果为空")
            result = parse_document(converted, file_name, document_id, segment_cls, asset_root,
                                    register_asset, prefix, include_all_images)
        except (OSError, subprocess.SubprocessError, ValueError, zipfile.BadZipFile) as exc:
            raise ValueError("旧版 PPT 转换或解析失败。请用 PowerPoint/WPS 将文件另存为 PPTX 后重新上传。") from exc
    result["document_preview"]["format"] = "ppt"
    result["document_preview"]["legacy_layout_warning"] = True
    return result


def parse_legacy_doc(path: Path, file_name: str, document_id: str, segment_cls: type,
                     asset_root: Path, register_asset: Callable[[str, Path, str], None],
                     prefix: str = "", include_all_images: bool = False) -> dict[str, Any]:
    soffice = _local_tool("soffice")
    if not soffice:
        raise ValueError("旧版 Word 需要本机安装 LibreOffice 才能解析。请安装后重试，或将文件另存为 DOCX 再上传。")
    with tempfile.TemporaryDirectory(prefix="onepager-legacy-doc-", dir=path.parent) as temp_name:
        temp_dir = Path(temp_name)
        converted = temp_dir / f"{path.stem}.docx"
        try:
            run_tool(
                [soffice, f"-env:UserInstallation={(temp_dir / 'profile').as_uri()}",
                 "--headless", "--convert-to", "docx", "--outdir", str(temp_dir), str(path)],
                check=True, capture_output=True, timeout=120,
            )
            if not converted.is_file() or converted.stat().st_size == 0:
                raise ValueError("转换结果为空")
            result = parse_document(converted, file_name, document_id, segment_cls, asset_root,
                                    register_asset, prefix, include_all_images)
        except (OSError, subprocess.SubprocessError, ValueError, zipfile.BadZipFile) as exc:
            raise ValueError("旧版 Word 转换或解析失败。请用 Word/WPS 将文件另存为 DOCX 后重新上传。") from exc
    result["document_preview"]["format"] = "doc"
    result["document_preview"]["legacy_layout_warning"] = True
    return result


def parse_document(
    path: Path,
    file_name: str,
    document_id: str,
    segment_cls: type,
    asset_root: Path,
    register_asset: Callable[[str, Path, str], None],
    prefix: str = "",
    include_all_images: bool = False,
) -> dict[str, Any]:
    extension = path.suffix.lower()
    if extension == ".pptx":
        result = parse_pptx_structured(path, file_name, document_id, segment_cls, asset_root, register_asset, prefix)
        _append_ooxml_annotations(path, result, file_name, segment_cls, prefix)
        _filter_and_ocr_images(result, asset_root, document_id, file_name, segment_cls, prefix, include_all_images)
        result["document_preview"] = _pptx_preview(path, result)
        return result
    if extension == ".docx":
        result = parse_docx_structured(path, file_name, document_id, segment_cls, asset_root, register_asset, prefix)
        _append_ooxml_annotations(path, result, file_name, segment_cls, prefix)
        _filter_and_ocr_images(result, asset_root, document_id, file_name, segment_cls, prefix, include_all_images)
        result["document_preview"] = _docx_preview(result)
        return result
    if extension == ".pdf":
        result = parse_pdf_structured(path, file_name, document_id, segment_cls, asset_root, register_asset, prefix)
        _filter_and_ocr_images(result, asset_root, document_id, file_name, segment_cls, prefix, include_all_images)
        result["document_preview"] = _pdf_preview(path, result, document_id, file_name, asset_root, register_asset)
        return result
    if extension == ".txt":
        return parse_txt_structured(path, file_name, segment_cls, prefix)
    if extension in {".xls", ".xlsx"}:
        return parse_spreadsheet_structured(path, file_name, segment_cls, prefix)
    if extension == ".ppt":
        return parse_legacy_ppt(path, file_name, document_id, segment_cls, asset_root,
                                register_asset, prefix, include_all_images)
    if extension == ".doc":
        return parse_legacy_doc(path, file_name, document_id, segment_cls, asset_root,
                                register_asset, prefix, include_all_images)
    raise ValueError(f"暂不支持 {extension} 文件。支持格式：PPT、PPTX、DOC、DOCX、PDF、TXT、XLS、XLSX。")


def serializable_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        **result,
        "segments": [asdict(item) if not isinstance(item, dict) else item for item in result["segments"]],
    }
