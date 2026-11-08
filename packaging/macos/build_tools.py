"""Build isolated audio helpers from the fixed upstream source archives."""
from pathlib import Path
import os
import shutil
import subprocess
import sys


def run(command, cwd, log):
    with log.open('ab') as stream:
        subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=True)


def main():
    root = Path(sys.argv[1]).resolve()
    cmake = Path(sys.argv[2]).resolve()
    tools = root / 'tools'; tools.mkdir(exist_ok=True)
    ffmpeg = root / 'upstream/ffmpeg-8.1.2'
    flags = ['--disable-autodetect', '--disable-network', '--disable-doc', '--disable-debug',
        '--disable-shared', '--enable-static', '--disable-programs', '--enable-ffmpeg', '--enable-ffprobe',
        '--disable-everything', '--enable-avcodec', '--enable-avformat', '--enable-avfilter', '--enable-swresample',
        '--enable-filter=aresample,asetpts,silencedetect,aformat,anull',
        '--enable-decoder=aac,aac_fixed,alac,mp3,mp3float,flac,opus,vorbis,pcm_s16le,pcm_s24le,pcm_s32le,pcm_u8,pcm_f32le,pcm_f64le,pcm_s16be,pcm_s24be,adpcm_ima_wav',
        '--enable-parser=aac,aac_latm,mpegaudio,flac,opus,vorbis',
        '--enable-demuxer=mov,matroska,wav,mp3,flac,ogg,aac', '--enable-muxer=wav',
        '--enable-encoder=pcm_s16le', '--enable-protocol=file,pipe',
        '--cc=clang', '--extra-cflags=-mmacosx-version-min=14.0', '--extra-ldflags=-mmacosx-version-min=14.0']
    if not (tools / 'ffmpeg').exists():
        run(['sh', 'configure', *flags], ffmpeg, root/'ffmpeg-build.log')
        run(['make', '-j8'], ffmpeg, root/'ffmpeg-build.log')
        for name in ['ffmpeg', 'ffprobe']:
            shutil.copy2(ffmpeg/name, tools/name)
            subprocess.run(['strip', '-x', str(tools/name)], check=True)
    whisper = root / 'upstream/whisper.cpp-1.7.6'
    build = root / 'whisper-build'
    if not (tools / 'whisper-cli').exists():
        run([str(cmake), '-S', str(whisper), '-B', str(build),
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_OSX_DEPLOYMENT_TARGET=14.0',
             '-DBUILD_SHARED_LIBS=OFF', '-DGGML_METAL=OFF', '-DGGML_OPENMP=OFF',
             '-DGGML_NATIVE=OFF', '-DWHISPER_BUILD_TESTS=OFF', '-DWHISPER_BUILD_SERVER=OFF',
             '-DWHISPER_CURL=OFF', f'-DCMAKE_C_FLAGS=-ffile-prefix-map={whisper}=whisper.cpp',
             f'-DCMAKE_CXX_FLAGS=-ffile-prefix-map={whisper}=whisper.cpp'], root, root/'whisper-build.log')
        run([str(cmake), '--build', str(build), '--target', 'whisper-cli', '-j8'], root, root/'whisper-build.log')
        shutil.copy2(build/'bin/whisper-cli', tools/'whisper-cli')
        subprocess.run(['strip', '-x', str(tools/'whisper-cli')], check=True)
    print('独立音频工具构建完成。')


if __name__ == '__main__':
    main()
