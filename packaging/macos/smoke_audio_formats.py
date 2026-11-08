"""Check bundled decoders against synthetic audio encoded by a development FFmpeg."""
from pathlib import Path
import array
import math
import subprocess
import sys
import tempfile
import wave

tools=Path(sys.argv[1]).resolve();encoder=Path(sys.argv[2]).resolve()
with tempfile.TemporaryDirectory(prefix='onepager-formats-') as temporary:
    root=Path(temporary);sound=root/'source.wav'
    samples=array.array('h',(int(6000*math.sin(2*math.pi*440*i/16000)) for i in range(16000)))
    with wave.open(str(sound),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(samples.tobytes())
    cases=[('mp3','libmp3lame'),('m4a','aac'),('flac','flac'),('aac','aac'),('ogg','vorbis'),
           ('opus','libopus'),('webm','libopus'),('mp4','aac')]
    for extension,codec in cases:
        path=root/f'synthetic.{extension}'
        subprocess.run([str(encoder),'-v','error','-i',str(sound),'-strict','-2','-ac','2','-c:a',codec,str(path)],capture_output=True,check=True)
        subprocess.run([str(tools/'ffprobe'),'-v','error','-show_format','-of','json',str(path)],capture_output=True,check=True,
                       env={'PATH':'/usr/bin:/bin'})
        output=root/f'decoded-{extension}.wav'
        subprocess.run([str(tools/'ffmpeg'),'-v','error','-i',str(path),'-af',
            'asetpts=PTS-STARTPTS,silencedetect=noise=-38dB:d=0.45','-ar','16000','-ac','1','-c:a','pcm_s16le',str(output)],
            capture_output=True,check=True,env={'PATH':'/usr/bin:/bin'})
        assert output.stat().st_size>16000,extension
    print('内置音频解码验证通过：MP3、M4A、FLAC、AAC、OGG、Opus、WebM、MP4；WAV 已由流程检查覆盖。')
