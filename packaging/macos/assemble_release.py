"""Assemble the full-model DMG and source archives from a reviewed manifest."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

VERSION='0.1.0-beta.3'
ROOT=Path(__file__).resolve().parents[2]
BUILD=Path(sys.argv[1]).resolve()
OUTPUT=Path(sys.argv[2]).resolve()
MANIFEST=Path(sys.argv[3]).resolve()
MODEL=Path(sys.argv[4]).resolve()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest=json.loads(MANIFEST.read_text())
    source=OUTPUT/f'TrainingOnePager-{VERSION}-source.zip'
    with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for row in manifest:
            path=ROOT/row['path']
            if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
                raise ValueError('Invalid source path')
            assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'],row['path']
            archive.write(path,row['path'])
        archive.writestr('SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    upstream=OUTPUT/f'TrainingOnePager-{VERSION}-upstream-sources.zip'
    with zipfile.ZipFile(upstream,'w',compression=zipfile.ZIP_STORED) as archive:
        for filename in ['ffmpeg-8.1.2.tar.gz','whisper.cpp-1.7.6.tar.gz','pymupdf-1.28.2.tar.gz','mupdf-1.28.2-source.tar.gz']:
            archive.write(BUILD/'upstream'/filename,filename)
        archive.write(ROOT/'packaging/macos/upstream-sources.json','upstream-sources.json')
        archive.write(ROOT/'packaging/macos/build_tools.py','build_tools.py')
    metadata=json.loads((ROOT/'packaging/macos/speech-model.json').read_text())
    with MODEL.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha1').hexdigest()==metadata['sha1'],'Model hash mismatch'
    assert MODEL.stat().st_size==metadata['bytes'],'Model size mismatch'

    def copy_app(source_app, destination):
        if destination.exists():shutil.rmtree(destination)
        subprocess.run(['ditto',str(source_app),str(destination)],check=True)

    def sign(app):
        subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
        subprocess.run(['codesign','--verify','--deep','--strict',str(app)],check=True)

    full_app=BUILD/'full-app/培训一纸通.app'
    full_app.parent.mkdir(exist_ok=True)
    copy_app(BUILD/'base-app/培训一纸通.app',full_app)
    models=full_app/'Contents/Resources/backend/_internal/models'
    models.mkdir(exist_ok=True)
    shutil.copyfile(MODEL,models/metadata['filename'])
    sign(full_app)

    common = """适用于 Apple 芯片（M 系列）Mac，目标 macOS 14 及以上，目前只在开发 Mac 验证。
没有 Developer ID 签名和公证，首次可能被系统拦截。请核实文件来源，再按系统“隐私与安全性”提示处理，不要关闭全局安全保护。
本项目采用 AGPL-3.0-only；语音模型采用 MIT，保留其原始许可。
项目源码 ZIP 随镜像提供；发行另配 upstream-sources ZIP，包含 FFmpeg、whisper.cpp、PyMuPDF 和 MuPDF 对应源码及构建说明。
旧 DOC/PPT 需 LibreOffice 或先另存为新格式。在线生成需要自行配置 API Key；本地录音识别无需 API Key。
使用结束后在软件控制窗口点“退出”，不要只关闭浏览器。
"""
    stage=BUILD/'dmg-full'
    if stage.exists():shutil.rmtree(stage)
    stage.mkdir()
    subprocess.run(['ditto',str(full_app),str(stage/full_app.name)],check=True)
    (stage/'Applications').symlink_to('/Applications',target_is_directory=True)
    shutil.copyfile(source,stage/source.name)
    shutil.copyfile(ROOT/'LICENSE',stage/'LICENSE.txt')
    shutil.copyfile(ROOT/'third_party/licenses/Whisper-LICENSE',stage/'Whisper-LICENSE.txt')
    description='完整版：已包含语音模型。将“培训一纸通”拖到 Applications（应用程序），再从应用程序打开，即可在本机识别录音。\n'
    (stage/'安装说明.txt').write_text('培训一纸通 0.1.0-beta.3\n\n'+description+'\n'+common)
    dmg=OUTPUT/f'TrainingOnePager-{VERSION}-macOS-arm64-full.dmg'
    subprocess.run(['hdiutil','create','-volname','培训一纸通-完整版','-srcfolder',str(stage),'-format','UDZO','-ov',str(dmg)],check=True)
    print(dmg,flush=True)


if __name__=='__main__':main()
