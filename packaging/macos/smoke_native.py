"""Validate native launcher startup and graceful application termination."""
from pathlib import Path
import http.client
import json
import os
import subprocess
import sys
import tempfile
import time

app = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix='onepager-native-') as name:
    temporary=Path(name)
    environment=dict(os.environ, ONEPAGER_NO_BROWSER='1')
    state_root=Path(subprocess.check_output(['getconf','DARWIN_USER_TEMP_DIR'],text=True).strip())
    previous=set(state_root.glob('training-onepager-*'))
    with (temporary/'native.log').open('wb') as log:
        process=subprocess.Popen([str(app/'Contents/MacOS/OnePager')],env=environment,stdout=log,stderr=subprocess.STDOUT)
        try:
            ready=None
            for _ in range(240):
                paths=[directory/'ready.json' for directory in state_root.glob('training-onepager-*')
                       if directory not in previous and (directory/'ready.json').exists()]
                if paths:ready=paths[0];break
                if process.poll() is not None:raise RuntimeError((temporary/'native.log').read_text())
                time.sleep(0.1)
            assert ready is not None,('Native launcher did not publish readiness',(temporary/'native.log').read_text())
            info=json.loads(ready.read_text());port=int(info['url'].rsplit(':',1)[1])
            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
            connection.request('GET','/');response=connection.getresponse()
            assert response.status==200 and b'app.js' in response.read()
            connection.close()
            process.terminate();process.wait(timeout=20)
            assert not ready.exists()
            for _ in range(100):
                try:os.kill(info['pid'],0)
                except ProcessLookupError:break
                time.sleep(0.1)
            else:raise AssertionError('Backend survived native application exit')
            print('原生应用验证通过：窗口启动、后端就绪、网页可用、退出后无残留后端。')
        finally:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait()
