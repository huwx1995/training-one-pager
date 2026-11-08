# Build with: python -m PyInstaller packaging/macos/onepager.spec
from pathlib import Path
import os
import certifi
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parents[1]
build_root = Path(os.environ['ONEPAGER_BUILD_ROOT'])
data = [(str(root/'prototype'), 'prototype'), (str(build_root/'tools'), 'tools'),
        (str(root/'LICENSE'), '.'), (str(root/'third_party'), 'third_party'),
        (certifi.where(), 'certifi'),
        # The packaged Codex Python ssl.py loads this explicit rejection policy
        # when constructing SSLContext. Omitting it breaks HTTPS initialization.
        (str(root/'packaging/macos/runtime-certs/codex-rejected-cas.pem'), '.')]
for name in ['docx', 'pptx']:
    data += collect_data_files(name)
a = Analysis([str(root/'packaging/macos/backend.py')], pathex=[str(root)], datas=data,
    binaries=[], hiddenimports=collect_submodules('pymupdf'),
    hookspath=[], runtime_hooks=[], excludes=['tkinter', 'numpy', 'pandas', 'matplotlib', 'reportlab',
        'pytest', 'scipy', 'IPython', 'torch', 'setuptools'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='onepager-backend', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=True, target_arch='arm64', codesign_identity=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='onepager-backend')
