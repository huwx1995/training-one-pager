"""Exercise the frozen Windows service using only synthetic files."""
from pathlib import Path
import http.client
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
import hashlib
import shutil


def main():
    executable = Path(sys.argv[1]).resolve()
    app = executable.parent
    model_info = json.loads((Path(__file__).resolve().parents[1] / 'macos/speech-model.json').read_text(encoding='utf-8'))
    model = app / '_internal/models' / model_info['filename']
    with model.open('rb') as stream:
        assert model.stat().st_size == model_info['bytes']
        assert hashlib.file_digest(stream, 'sha1').hexdigest() == model_info['sha1']
    with tempfile.TemporaryDirectory(prefix='onepager-packaged-') as name:
        root = Path(name)
        data_dir = root / 'user-data'
        ready = root/'ready.json'
        environment = {'PATH':str(Path(os.environ['SystemRoot'])/'System32'),
                       'SystemRoot':os.environ['SystemRoot'], 'WINDIR':os.environ['SystemRoot'],
                       'USERPROFILE':str(root),'LOCALAPPDATA':str(root/'local'), 'HOME':str(root),
                       'TEMP':str(root),'TMP':str(root),'ONEPAGER_DATA_DIR':str(data_dir)}
        sample = app.parents[1] / 'upstream/whisper.cpp-1.7.6/samples/jfk.wav'
        assert sample.is_file(), 'Public upstream speech sample is missing'
        transcript_prefix = root / 'speech-check'
        speech_started = time.monotonic()
        speech = subprocess.run([str(app/'_internal/tools/whisper-cli-avx2.exe'), '-m', str(model),
            '-f', str(sample), '-l', 'en', '-oj', '-of', str(transcript_prefix)],
            env=environment, capture_output=True, timeout=180)
        assert speech.returncode == 0, speech.stderr[-1000:]
        recognized = json.loads(transcript_prefix.with_suffix('.json').read_text(encoding='utf-8'))
        assert any(str(item.get('text', '')).strip() for item in recognized.get('transcription', []))
        print(f'Windows bundled AVX2 speech transcription passed in {time.monotonic() - speech_started:.1f}s', flush=True)
        # Exercise the exact failure reported by users who unpacked the app below a Chinese directory.
        unicode_root = root / '中文目录'
        unicode_root.mkdir()
        unicode_model = unicode_root / '语音模型.bin'
        try:
            os.link(model, unicode_model)
        except OSError:
            shutil.copyfile(model, unicode_model)
        unicode_audio = unicode_root / '录音.wav'
        shutil.copyfile(sample, unicode_audio)
        for cli_name in ('whisper-cli-avx2.exe', 'whisper-cli.exe'):
            unicode_output = unicode_root / cli_name.replace('.exe', '')
            result = subprocess.run([str(app/'_internal/tools'/cli_name), '-m', str(unicode_model),
                '-f', str(unicode_audio), '-l', 'en', '-oj', '-of', str(unicode_output)],
                env=environment, capture_output=True, timeout=180)
            assert result.returncode == 0, (cli_name, result.returncode, result.stderr[-1000:])
            assert unicode_output.with_suffix('.json').is_file(), cli_name
        print('Windows Whisper accepted Chinese model, audio and output paths.', flush=True)
        tls_result = root / 'tls.json'
        subprocess.run([str(executable), '--check-tls-local', '--result-file', str(tls_result)],
                       env=environment, check=True, timeout=30, creationflags=0x08000000)
        assert json.loads(tls_result.read_text(encoding='utf-8'))['tls_verified']
        with (root/'service.log').open('wb') as log:
            process = subprocess.Popen([str(executable), '--backend', '--ready-file', str(ready)], env=environment,
                                       stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True, creationflags=0x08000000)
            try:
                for _ in range(200):
                    if ready.exists(): break
                    if process.poll() is not None: raise RuntimeError((root/'service.log').read_text())
                    time.sleep(0.1)
                info = json.loads(ready.read_text())
                port = int(info['url'].rsplit(':',1)[1])
                connection = http.client.HTTPConnection('127.0.0.1',port,timeout=30)
                def request(method,path,body=None,headers=None):
                    connection.request(method,path,body=body,headers={'Host':f'127.0.0.1:{port}',**(headers or {})})
                    response=connection.getresponse();payload=response.read()
                    assert response.status==200,(path,response.status,payload[:300],(root/'service.log').read_text())
                    if response.getheader('Content-Type','').startswith('application/json'):return json.loads(payload)
                    return payload
                def post(path,payload):
                    return request('POST',path,json.dumps(payload,ensure_ascii=False).encode(),
                                   {'Content-Type':'application/json','X-Generation-Mode':'local'})
                assert b'app.js' in request('GET','/')
                assert request('GET','/workbench-theme.css')
                boundary='packaged-synthetic-boundary'
                material='虚构社团工具借用培训。工具借用期限为3天，归还前必须清点配件，不得遗失工具。'.encode()
                payload=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="synthetic.txt"\r\nContent-Type: text/plain\r\n\r\n'.encode()+material+f'\r\n--{boundary}--\r\n'.encode())
                document=request('POST','/api/extract',payload,{'Content-Type':f'multipart/form-data; boundary={boundary}'})['document']
                confirmation=post('/api/desensitize',{'document_id':document['id'],'document_version':document['document_version'],
                    'candidates':document['sensitive_candidates'],'image_regions':[],'confirmed':True})
                token=confirmation['confirmation_token']
                generated=post('/api/generate',{'document_id':document['id'],'confirmation_token':token,
                    'audience':'社团成员','template':'knowledge-operation','requirements':{'version':1,'max_chars':500,
                    'detail_depth':'normal','tone':'plain','detail_target':'','must_keep':'','include_overview':True,
                    'include_architecture':True,'include_practice':True,'explain_terms':False}})
                draft=generated['one_pager']
                body=request('POST','/api/export/docx',json.dumps({'document_id':document['id'],
                    'confirmation_token':token,'one_pager':draft}).encode(),{'Content-Type':'application/json'})
                with zipfile.ZipFile(io.BytesIO(body)) as archive:assert 'word/document.xml' in archive.namelist()
                post('/api/document/clear',{'document_id':document['id']})
                tools=executable.parent/'_internal/tools'
                for binary in ['ffmpeg','ffprobe']:
                    subprocess.run([str(tools/binary),'-version'],env=environment,capture_output=True,check=True)
                # A synthetic WAV exercises both decoding and silence pre-processing.
                import wave
                sound=root/'synthetic.wav'
                with wave.open(str(sound),'wb') as stream:
                    stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000);stream.writeframes(b'\0\0'*16000)
                probe=subprocess.run([str(tools/'ffprobe'),'-v','error','-show_format','-of','json',str(sound)],
                    env=environment,capture_output=True,check=True)
                assert 'format' in json.loads(probe.stdout)
                subprocess.run([str(tools/'ffmpeg'),'-v','error','-i',str(sound),'-af',
                    'asetpts=PTS-STARTPTS,silencedetect=noise=-38dB:d=0.45','-ar','16000','-ac','1',
                    '-c:a','pcm_s16le',str(root/'converted.wav')],env=environment,capture_output=True,check=True)
                # Exercise parsers from the frozen bundle, not the development interpreter.
                from docx import Document
                from pptx import Presentation
                from pptx.util import Inches
                from openpyxl import Workbook
                import pymupdf
                fixtures=[]
                word=Document();word.add_paragraph('Synthetic drawing workshop: prepare paper and brushes.')
                path=root/'synthetic.docx';word.save(path);fixtures.append(path)
                slides=Presentation();slide=slides.slides.add_slide(slides.slide_layouts[6])
                slide.shapes.add_textbox(Inches(1),Inches(1),Inches(6),Inches(1)).text='Synthetic drawing workshop'
                path=root/'synthetic.pptx';slides.save(path);fixtures.append(path)
                book=Workbook();book.active.append(['Synthetic paper','12'])
                path=root/'synthetic.xlsx';book.save(path);fixtures.append(path)
                pdf=pymupdf.open();page=pdf.new_page();page.insert_text((72,72),'Synthetic drawing workshop')
                path=root/'synthetic.pdf';pdf.save(path);pdf.close();fixtures.append(path)
                for path in fixtures:
                    print('验证格式：', path.suffix, flush=True)
                    upload=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                            'Content-Type: application/octet-stream\r\n\r\n').encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
                    parsed=request('POST','/api/extract',upload,{'Content-Type':f'multipart/form-data; boundary={boundary}'})['document']
                    assert parsed['segments'],path.suffix
                    post('/api/document/clear',{'document_id':parsed['id']})
                from PIL import Image,ImageDraw,ImageFont
                image=Image.new('RGB',(1400,240),'white')
                draw=ImageDraw.Draw(image)
                font=ImageFont.truetype(str(Path(os.environ['WINDIR'])/'Fonts/arial.ttf'),64)
                draw.text((30,70),'Synthetic drawing workshop',fill='black',font=font)
                picture=root/'synthetic.png';image.save(picture)
                ocr=subprocess.run([str(tools/'tesseract.exe'),str(picture),'stdout','--tessdata-dir',str(executable.parent/'_internal/tessdata'),'-l','chi_sim+eng'],env=environment,capture_output=True,check=True)
                assert b'drawing' in ocr.stdout.lower()
                print('安装版格式验证通过：DOCX、PPTX、XLSX、PDF 和内置图片 OCR。')
                connection.close()
                print('安装版验证通过：启动、页面、TXT解析、脱敏确认、本地生成、Word导出、清空材料和内置音频工具。')
            finally:
                if process.poll() is None:
                    process.stdin.write('stop\n');process.stdin.flush()
                    try:process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=10)
                        raise AssertionError('Backend did not exit gracefully')
            assert not ready.exists()
            assert not list((data_dir/'runs').glob('run-*'))
            print('退出验证通过：后端退出，材料运行目录已清理。')


if __name__=='__main__':main()
