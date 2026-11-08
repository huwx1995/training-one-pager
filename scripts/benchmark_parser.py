"""Reproducible synthetic parser benchmark; writes only to a temporary directory."""

import json
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import document_parser  # noqa: E402
from server import SourceSegment  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        text = root / "synthetic.txt"
        text.write_text("\n".join(f"第{i}条：客户号CIF{i:06d}，办理流程与风险提醒。" for i in range(20000)), encoding="utf-8")
        book = Workbook()
        sheet = book.active
        for i in range(3000):
            sheet.append([f"项目{i}", f"CIF{i:06d}", "业务条件与办理说明"])
        spreadsheet = root / "synthetic.xlsx"
        book.save(spreadsheet)
        deck = Presentation()
        for i in range(60):
            slide = deck.slides.add_slide(deck.slide_layouts[6])
            box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(7), Inches(2))
            box.text = f"第{i}页培训内容：办理流程、材料清单和风险提醒。"
        slides = root / "synthetic.pptx"
        deck.save(slides)
        for path in (text, spreadsheet, slides):
            tracemalloc.start()
            started = time.perf_counter()
            parsed = document_parser.parse_document(path, path.name, path.stem, SourceSegment,
                                                    root / "assets", lambda *_: None)
            seconds = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(json.dumps({"format": path.suffix, "bytes": path.stat().st_size,
                              "segments": len(parsed["segments"]), "seconds": round(seconds, 3),
                              "python_peak_mb": round(peak / 1024 / 1024, 1)}))


if __name__ == "__main__":
    main()
