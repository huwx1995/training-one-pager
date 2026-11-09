"""Verify and archive only reviewed source files, regardless of build directory contents."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'packaging/windows/reviewed-files.json'


def reviewed_files():
    rows=json.loads(MANIFEST.read_text(encoding='utf-8'))
    seen=set()
    for row in rows:
        name=row['path']
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or name in seen:
            raise ValueError('Invalid source path')
        seen.add(name)
        path=ROOT.joinpath(*relative.parts)
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            raise ValueError('Invalid source path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Reviewed file changed: '+name)
        yield path,name
    # The manifest does not hash itself; it is also included in the archive.
    yield MANIFEST,MANIFEST.relative_to(ROOT).as_posix()


def archive_source(destination):
    paths=list(reviewed_files())
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path,name in paths:archive.write(path,name)
    return len(paths)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--zip',type=Path);args=parser.parse_args()
    if args.zip:
        args.zip.parent.mkdir(parents=True,exist_ok=True)
        print('Archived reviewed files:',archive_source(args.zip))
    else:print('Verified reviewed files:',len(list(reviewed_files())))


if __name__=='__main__':main()
