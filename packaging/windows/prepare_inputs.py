"""Fetch public, fixed-source inputs. Never inspect user material or credentials."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]


def fetch(url, destination, expected, algorithm='sha256'):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        temporary = destination.with_suffix(destination.suffix + '.download')
        try:
            subprocess.run(['curl','--fail','--location','--retry','3','--connect-timeout','20',
                '--max-time','900','--output',str(temporary),url],check=True)
            with temporary.open('rb') as stream:
                if hashlib.file_digest(stream,algorithm).hexdigest() != expected:
                    raise ValueError('Downloaded input hash mismatch: ' + destination.name)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    with destination.open('rb') as stream:
        if hashlib.file_digest(stream,algorithm).hexdigest() != expected:
            raise ValueError('Input hash mismatch: ' + destination.name)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('build',type=Path)
    parser.add_argument('--model-file',type=Path)
    args=parser.parse_args()
    build=args.build.resolve();build.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(ROOT/'packaging/macos/fetch_sources.py'),str(build/'upstream')],check=True)
    for row in json.loads((ROOT/'packaging/windows/ocr-downloads.json').read_text()):
        fetch(row['url'],build/'tessdata'/row['file'],row['sha256'])
    model=json.loads((ROOT/'packaging/macos/speech-model.json').read_text())
    destination=build/'model'/model['filename']
    if args.model_file:
        with args.model_file.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha1').hexdigest()==model['sha1'],'Provided model hash mismatch'
        destination.parent.mkdir(exist_ok=True)
        if args.model_file.resolve()!=destination.resolve():shutil.copyfile(args.model_file,destination)
    fetch(model['url'],destination,model['sha1'],'sha1')
    sources=json.loads((ROOT/'packaging/macos/upstream-sources.json').read_text())
    for row in sources[2:]:
        url=row['url']
        if row['file'].startswith('pymupdf-'):
            with urllib.request.urlopen('https://pypi.org/pypi/PyMuPDF/1.28.2/json',timeout=60) as response:
                metadata=json.load(response)
            entry=next(item for item in metadata['urls'] if item['packagetype']=='sdist' and item['digests']['sha256']==row['sha256'])
            url=entry['url']
        fetch(url,build/'upstream'/row['file'],row['sha256'])
    print('Public source, OCR and speech inputs verified.')


if __name__=='__main__':main()
