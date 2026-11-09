# Build on 64-bit Windows with the reviewed tool and OCR data directories.
from pathlib import Path
import os
import certifi
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parents[1]
build = Path(os.environ['ONEPAGER_WINDOWS_BUILD'])
data = [(str(root/'prototype'),'prototype'), (str(build/'tools'),'tools'),
        (str(build/'tessdata'),'tessdata'), (str(root/'LICENSE'),'.'),
        (str(root/'THIRD_PARTY_NOTICES.md'),'.'),
        (str(root/'third_party'),'third_party'), (str(build/'windows-licenses'),'windows-licenses'),
        (str(root/'docs'),'docs'), (certifi.where(),'certifi')]
for package in ['docx','pptx']:
    data += collect_data_files(package)
a = Analysis([str(root/'packaging/windows/desktop.py')], pathex=[str(root)], datas=data,
    binaries=[], hiddenimports=collect_submodules('pymupdf'), excludes=['numpy','pandas','matplotlib',
        'reportlab','pytest','scipy','IPython','torch','setuptools'], noarchive=False)
pyz = PYZ(a.pure)
launcher = EXE(pyz,a.scripts,[],exclude_binaries=True,name='TrainingOnePager',debug=False,
    strip=False,upx=False,console=False)
# A console-subsystem backend keeps stdin available for graceful shutdown.
# The launcher starts it with CREATE_NO_WINDOW so no terminal is shown.
backend = EXE(pyz,a.scripts,[],exclude_binaries=True,name='onepager-backend',debug=False,
    strip=False,upx=False,console=True)
coll = COLLECT(launcher,backend,a.binaries,a.datas,strip=False,upx=False,name='TrainingOnePager')
