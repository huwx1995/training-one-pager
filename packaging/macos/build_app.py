"""Build the macOS application; run in the isolated packaging environment."""
from pathlib import Path
import json
import os
import plistlib
import shutil
import subprocess
import sys

VERSION = '0.1.0-beta.3'
ROOT = Path(__file__).resolve().parents[2]
BUILD = Path(sys.argv[1]).resolve()
OUTPUT = Path(sys.argv[2]).resolve()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cache = BUILD / 'compiler-cache'; cache.mkdir(exist_ok=True)
    env = dict(os.environ, ONEPAGER_BUILD_ROOT=str(BUILD), PYINSTALLER_CONFIG_DIR=str(BUILD/'pyinstaller-cache'),
               CLANG_MODULE_CACHE_PATH=str(cache), SWIFT_MODULECACHE_PATH=str(cache))
    subprocess.run(['clang', '-fobjc-arc', '-mmacosx-version-min=14.0', '-framework', 'Foundation', '-framework', 'Vision',
        str(ROOT/'local_ocr.m'), '-o', str(BUILD/'tools/local-ocr')], check=True, env=env)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--distpath', str(BUILD/'frozen'), '--workpath', str(BUILD/'pyinstaller-work'),
        str(ROOT/'packaging/macos/onepager.spec')], check=True, env=env, cwd=ROOT)
    # Fail the build if the frozen runtime cannot initialize verified TLS.
    subprocess.run([str(BUILD/'frozen/onepager-backend/onepager-backend'), '--check-tls-local'], check=True)
    app = OUTPUT / '培训一纸通.app'
    if app.exists():
        shutil.rmtree(app)
    contents = app/'Contents'; (contents/'MacOS').mkdir(parents=True)
    resources = contents/'Resources'; resources.mkdir()
    shutil.copytree(BUILD/'frozen/onepager-backend', resources/'backend', symlinks=True)
    # Upstream template paths traverse parts/..; the intermediate directory must exist.
    for package in ['docx', 'pptx']:
        (resources/'backend/_internal'/package/'parts').mkdir(parents=True, exist_ok=True)
    subprocess.run(['xcrun', 'swiftc', '-O', '-target', 'arm64-apple-macos14.0',
        '-module-cache-path', str(cache), str(ROOT/'packaging/macos/Launcher.swift'),
        '-o', str(contents/'MacOS/OnePager')], check=True, env=env)
    info = {'CFBundleExecutable':'OnePager', 'CFBundleIdentifier':'org.trainingonepager.desktop',
        'CFBundleName':'培训一纸通', 'CFBundleDisplayName':'培训一纸通', 'CFBundlePackageType':'APPL',
        'CFBundleShortVersionString':'0.1.0', 'CFBundleVersion':'3', 'OnePagerReleaseVersion':VERSION, 'LSMinimumSystemVersion':'14.0',
        'NSHighResolutionCapable':True, 'NSRequiresAquaSystemAppearance':False}
    with (contents/'Info.plist').open('wb') as stream:
        plistlib.dump(info, stream)
    for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
        shutil.copyfile(ROOT/name, resources/name)
    shutil.copytree(ROOT/'docs', resources/'docs')
    shutil.copytree(ROOT/'third_party', resources/'third_party')
    (resources/'发行说明.txt').write_text('''培训一纸通 0.1.0-beta.3 — Apple 芯片 Mac 内测版

采用 AGPL-3.0-only，许可全文见同目录 LICENSE。
对应项目源码和录音工具源码随本次发行文件一并提供；第三方声明见 THIRD_PARTY_NOTICES.md。

最低目标系统 macOS 14；目前只在开发 Mac 验证，尚无 Developer ID 签名及 Apple 公证。
安装：把应用拖入“应用程序”后打开。首次如被系统拦截，请先核实文件来源，再按系统“隐私与安全性”提示处理；不要关闭全局安全保护。

自带 Python、本地音频工具和图片文字识别工具。最终发行仅提供内置语音模型的完整版。
旧版 DOC/PPT 仍需另外安装 LibreOffice，或先另存为 DOCX/PPTX。
本版语音使用 CPU/Accelerate，未启用 Metal GPU，长录音处理可能较慢。

工作台会在默认浏览器中打开。关闭浏览器不会退出后台，请在应用窗口点击“退出”。
本机数据位于用户“资源库/Application Support/TrainingOnePager”，可从应用窗口打开。
生成模型由使用者自行配置，API Key 不随应用提供。请人工核对材料、脱敏和生成结果。
''')
    # Ad-hoc signing satisfies arm64 loading; it is not Developer ID notarization.
    subprocess.run(['codesign', '--force', '--deep', '--sign', '-', str(app)], check=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
    print(app)


if __name__ == '__main__':
    main()
