"""Create the document-only Apple Silicon DMG from a freshly built base app."""
from pathlib import Path
import argparse
import hashlib
import plistlib
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packaging/windows"))
from source_snapshot import archive_source  # noqa: E402

VERSION = "0.1.0-beta.5"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_app", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    base = args.base_app.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stage = output / "lite-stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    app = stage / "培训一纸通轻量版.app"
    shutil.copytree(base, app, symlinks=True)
    resources = app / "Contents/Resources"
    internal = resources / "backend/_internal"
    for name in ("ffmpeg", "ffprobe", "whisper-cli"):
        (internal / "tools" / name).unlink(missing_ok=True)
    shutil.rmtree(internal / "models", ignore_errors=True)
    (internal / "lite-edition.flag").write_text("document-only\n", encoding="utf-8")
    info_path = app / "Contents/Info.plist"
    with info_path.open("rb") as stream:
        info = plistlib.load(stream)
    info.update(CFBundleIdentifier="org.trainingonepager.desktop.lite",
                CFBundleName="培训一纸通轻量版", CFBundleDisplayName="培训一纸通轻量版",
                CFBundleVersion="5", OnePagerReleaseVersion=VERSION + "-lite")
    with info_path.open("wb") as stream:
        plistlib.dump(info, stream)
    (resources / "发行说明.txt").write_text(
        "培训一纸通 0.1.0-beta.5 — Apple 芯片 Mac 轻量版\n\n"
        "支持文档解析、生成和导出，不提供录音转写。需要录音功能请下载完整版。\n"
        "适用于 macOS 14 及以上的 Apple 芯片 Mac。\n"
        "与完整版使用不同的应用名称和本机数据文件夹，可以同时保留。\n"
        "本版未做 Developer ID 签名或公证；首次打开请核对文件来源。\n"
        "旧 DOC/PPT 仍需 LibreOffice 或先另存为新格式。\n",
        encoding="utf-8",
    )
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    source = output / f"TrainingOnePager-{VERSION}-source.zip"
    archive_source(source)
    shutil.copyfile(source, stage / source.name)
    shutil.copyfile(ROOT / "LICENSE", stage / "LICENSE.txt")
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    (stage / "安装说明.txt").write_text(
        "将“培训一纸通轻量版”拖到“应用程序”后打开。\n"
        "本版只处理文档，不处理录音；完整版可另行安装。\n",
        encoding="utf-8",
    )
    dmg = output / f"TrainingOnePager-{VERSION}-macOS-arm64-lite.dmg"
    subprocess.run(["hdiutil", "create", "-volname", "培训一纸通-轻量版", "-srcfolder", str(stage),
                    "-format", "UDZO", "-ov", str(dmg)], check=True)
    with (output / "SHA256SUMS.txt").open("w", encoding="utf-8") as stream:
        for path in (dmg, source):
            with path.open("rb") as content:
                stream.write(f"{hashlib.file_digest(content, 'sha256').hexdigest()}  {path.name}\n")
    print(dmg)


if __name__ == "__main__":
    main()
