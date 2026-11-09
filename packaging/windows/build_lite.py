"""Derive a document-only ZIP from the tested frozen Windows application."""
from pathlib import Path
import argparse
import hashlib
import shutil
import zipfile

from source_snapshot import archive_source


VERSION = "0.1.0-beta.5"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("frozen", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    app = args.frozen.resolve()
    output = args.output.resolve()
    if not (app / "TrainingOnePager.exe").is_file():
        raise ValueError("Missing frozen Windows application")
    output.mkdir(parents=True, exist_ok=True)
    stage = output / "lite-stage" / "TrainingOnePagerLite"
    if stage.parent.exists():
        shutil.rmtree(stage.parent)
    shutil.copytree(app, stage)
    internal = stage / "_internal"
    for name in ("ffmpeg.exe", "ffprobe.exe", "whisper-cli.exe", "whisper-cli-avx2.exe"):
        (internal / "tools" / name).unlink(missing_ok=True)
    shutil.rmtree(internal / "models", ignore_errors=True)
    (internal / "lite-edition.flag").write_text("document-only\n", encoding="utf-8")
    if any((internal / "tools" / name).exists() for name in ("ffmpeg.exe", "ffprobe.exe", "whisper-cli.exe", "whisper-cli-avx2.exe")):
        raise AssertionError("Audio tool remained in lite edition")
    (stage / "使用说明.txt").write_text(
        "培训一纸通 Windows 轻量版\n\n"
        "适用于 Windows 10/11 64 位 Intel/AMD 电脑。完整解压后双击 TrainingOnePager.exe。\n"
        "本版支持文档解析、生成和导出，不支持录音转写；需要录音功能请下载完整版。\n"
        "请保留 _internal 和 sources 文件夹。旧 DOC/PPT 仍需 LibreOffice 或另存为新格式。\n",
        encoding="utf-8",
    )
    source = output / f"TrainingOnePager-{VERSION}-source.zip"
    archive_source(source)
    sources = stage / "sources"
    for old in sources.glob("TrainingOnePager-*-windows-source.zip"):
        old.unlink()
    shutil.copyfile(source, sources / source.name)
    package = output / f"TrainingOnePager-{VERSION}-windows-x64-lite.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                archive.write(path, (Path("TrainingOnePagerLite") / path.relative_to(stage)).as_posix())
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {package.name}\n", encoding="utf-8")
    print(package)


if __name__ == "__main__":
    main()
