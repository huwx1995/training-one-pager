"""Download fixed upstream sources; keep archives next to build output for recipients."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
import urllib.request
import subprocess


def main():
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    expected = {'ffmpeg-8.1.2.tar.gz': '9fd092511605bbebafe095ea6d38d9e40f34d12f7386e1258372df8be0576eb7',
                'whisper.cpp-1.7.6.tar.gz': '166140e9a6d8a36f787a2bd77f8f44dd64874f12dd8359ff7c1f4f9acb86202e'}
    items = [
        ('ffmpeg-8.1.2.tar.gz', 'https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/refs/tags/n8.1.2'),
        ('whisper.cpp-1.7.6.tar.gz', 'https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v1.7.6'),
    ]
    for filename, url in items:
        path = destination / filename
        if not path.exists():
            subprocess.run(['curl', '--fail', '--location', '--retry', '3', '--connect-timeout', '20', '--max-time', '240', '--output', str(path), url], check=True)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected[filename]:
            raise RuntimeError('Upstream archive hash mismatch: ' + filename)
        extract = destination / filename.split('.tar.')[0]
        if not extract.exists():
            extract.mkdir()
            with tarfile.open(path) as archive:
                for member in archive.getmembers():
                    parts = Path(member.name).parts
                    relative = Path(*parts[1:])
                    if not parts or '..' in relative.parts or member.issym() or member.islnk():
                        continue
                    if member.isdir():
                        (extract / relative).mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        target = extract / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(archive.extractfile(member).read())
                        target.chmod(member.mode & 0o777)
        records.append({'file': filename, 'url': url, 'sha256': digest})
        print(filename, digest, flush=True)
    (destination / 'upstream-sources.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
