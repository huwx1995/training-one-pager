"""Run the frozen audio workflow against system-synthesized speech and a local model."""
from pathlib import Path
import http.client
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

backend=Path(sys.argv[1]).resolve();model=Path(sys.argv[2]).resolve()
assert model.is_file()
with tempfile.TemporaryDirectory(prefix='onepager-speech-') as name:
    root=Path(name);ready=root/'ready.json';aiff=root/'synthetic.aiff';sound=root/'synthetic.wav'
    subprocess.run(['/usr/bin/say','Synthetic drawing workshop. Please prepare paper and brushes.',
                    '--file-format=WAVE','--data-format=LEI16@16000','-o',str(sound)],check=True)
    tools=backend.parent/'_internal/tools'
    environment={'PATH':'/usr/bin:/bin','HOME':str(root),'LANG':'zh_CN.UTF-8','ONEPAGER_DATA_DIR':str(root/'data'),
                 'WHISPER_MODEL_PATH':str(model),'TMPDIR':str(root)}
    with (root/'server.log').open('wb') as log:
        process=subprocess.Popen([str(backend),'--ready-file',str(ready)],env=environment,
                                 stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            for _ in range(200):
                if ready.exists():break
                if process.poll() is not None:raise RuntimeError((root/'server.log').read_text())
                time.sleep(0.1)
            port=int(json.loads(ready.read_text())['url'].rsplit(':',1)[1])
            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=30)
            connection.request('POST','/api/audio/upload',sound.read_bytes(),{'X-Audio-File-Name':'synthetic.wav'})
            response=connection.getresponse();payload=json.loads(response.read());assert response.status==202,payload
            job=payload['job_id'];started=time.monotonic()
            for _ in range(180):
                connection.request('GET','/api/audio/status/'+job)
                response=connection.getresponse();payload=json.loads(response.read())
                assert payload['status']!='error',payload.get('message')
                if payload['status']=='done':break
                time.sleep(1)
            else:raise AssertionError('Synthetic audio transcription timed out')
            assert any(row['text'].strip() for row in payload['document']['segments'])
            print('安装版合成语音转写通过，用时约 %.1f 秒；此检查不代表真实录音识别质量。'%(time.monotonic()-started))
            connection.close()
        finally:
            if process.poll() is None:os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=15)
