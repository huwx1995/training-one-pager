#!/usr/bin/env bash
set -euo pipefail
build_root="$(cd "$1" && pwd)"
cd "$build_root/upstream/ffmpeg-8.1.2"
./configure --target-os=mingw32 --arch=x86_64 --cc=gcc \
  --disable-autodetect --disable-network --disable-doc --disable-debug \
  --disable-shared --enable-static --disable-programs --enable-ffmpeg --enable-ffprobe \
  --disable-everything --enable-avcodec --enable-avformat --enable-avfilter --enable-swresample \
  --enable-filter=aresample,asetpts,silencedetect,aformat,anull \
  --enable-decoder=aac,aac_fixed,alac,mp3,mp3float,flac,opus,vorbis,pcm_s16le,pcm_s24le,pcm_s32le,pcm_u8,pcm_f32le,pcm_f64le,pcm_s16be,pcm_s24be,adpcm_ima_wav \
  --enable-parser=aac,aac_latm,mpegaudio,flac,opus,vorbis \
  --enable-demuxer=mov,matroska,wav,mp3,flac,ogg,aac --enable-muxer=wav \
  --enable-encoder=pcm_s16le --enable-protocol=file,pipe \
  --extra-cflags=-D_WIN32_WINNT=0x0A00 --extra-ldflags=-static
make -j4
mkdir -p "$build_root/tools"
cp ffmpeg.exe ffprobe.exe "$build_root/tools/"
# Record redistributable runtime provenance; no developer environment is archived.
pacman -Q mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-crt \
  > "$build_root/mingw-toolchain.txt"
mkdir -p "$build_root/windows-licenses/mingw"
pacman -Ql mingw-w64-ucrt-x86_64-crt mingw-w64-ucrt-x86_64-gcc | \
  awk '$2 ~ /share\/licenses\/.*[^\/]$/ {print $2}' | while IFS= read -r file; do
    if [ -f "$file" ]; then
      relative="${file#*/share/licenses/}"
      mkdir -p "$build_root/windows-licenses/mingw/$(dirname "$relative")"
      cp "$file" "$build_root/windows-licenses/mingw/$relative"
    fi
  done
