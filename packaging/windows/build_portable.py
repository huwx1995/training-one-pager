"""Create one complete portable Windows ZIP; run only on Windows x64."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from source_snapshot import archive_source


ROOT = Path(__file__).resolve().parents[2]
VERSION = "0.1.0-beta.3"


def digest(path: Path, algorithm: str = "sha256") -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise SystemExit("Build the Windows package on Windows x64.")

    build = args.build.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    tools = build / "tools"
    for name in ("ffmpeg.exe", "ffprobe.exe", "whisper-cli.exe", "whisper-cli-avx2.exe", "tesseract.exe"):
        if not (tools / name).is_file():
            raise ValueError(f"Missing Windows tool: {name}")
    for name in ("chi_sim.traineddata", "eng.traineddata"):
        if not (build / "tessdata" / name).is_file():
            raise ValueError(f"Missing OCR data: {name}")
    model_meta = json.loads((ROOT / "packaging/macos/speech-model.json").read_text(encoding="utf-8"))
    model = build / "model" / model_meta["filename"]
    if model.stat().st_size != model_meta["bytes"] or digest(model, "sha1") != model_meta["sha1"]:
        raise ValueError("Speech model does not match the reviewed model")
    if not (build / "windows-licenses").is_dir():
        raise ValueError("Windows dependency licenses were not collected")

    source_zip = output / f"TrainingOnePager-{VERSION}-windows-source.zip"
    archive_source(source_zip)
    environment = dict(os.environ, ONEPAGER_WINDOWS_BUILD=str(build),
                       PYINSTALLER_CONFIG_DIR=str(build / "pyinstaller-cache"))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(build / "frozen"), "--workpath", str(build / "pyinstaller-work"),
                    str(ROOT / "packaging/windows/onepager.spec")],
                   cwd=ROOT, env=environment, check=True)
    app = build / "frozen" / "TrainingOnePager"
    if not (app / "TrainingOnePager.exe").is_file() or not (app / "onepager-backend.exe").is_file():
        raise ValueError("Windows launcher or backend was not built")
    for package in ("docx", "pptx"):
        (app / "_internal" / package / "parts").mkdir(parents=True, exist_ok=True)
    models = app / "_internal" / "models"
    models.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(model, models / model.name)
    if digest(models / model.name, "sha1") != model_meta["sha1"]:
        raise ValueError("Copied speech model failed validation")
    source_dir = app / "sources"
    source_dir.mkdir(exist_ok=True)
    shutil.copy2(source_zip, source_dir / source_zip.name)
    (app / "使用说明.txt").write_text(
        "培训一纸通 Windows 测试版\n\n"
        "适用于 Windows 10/11 64 位 Intel/AMD 电脑。解压整个压缩包后，双击 TrainingOnePager.exe。\n"
        "首次运行会打开控制窗口和默认浏览器。结束使用时请在控制窗口点击“退出”。\n"
        "请勿只复制 EXE；_internal 和 sources 文件夹必须保持在同一目录。\n"
        "语音模型已包含。旧 DOC/PPT 如需解析，请安装 LibreOffice 或另存为 DOCX/PPTX。\n"
        "本版尚未经过普通 Windows 电脑完整验收；请勿使用真实敏感材料进行首次测试。\n"
        "如系统拦截启动，请先核对文件来源，不要关闭全局安全保护。\n",
        encoding="utf-8",
    )
    zip_path = output / f"TrainingOnePager-{VERSION}-windows-x64-full.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for path in sorted(app.rglob("*")):
            if path.is_file():
                archive.write(path, (Path("TrainingOnePager") / path.relative_to(app)).as_posix())
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{digest(path)}  {path.name}\n" for path in (zip_path, source_zip)),
        encoding="utf-8",
    )
    print("Windows complete portable ZIP:", zip_path)


if __name__ == "__main__":
    main()
