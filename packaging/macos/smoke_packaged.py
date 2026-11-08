"""Exercise the actual frozen service with synthetic files and a clean environment."""
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


def main():
    executable = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='onepager-packaged-') as name:
        root = Path(name)
        data_dir = root / 'user-data'
        ready = root/'ready.json'
        environment = {'PATH':'/usr/bin:/bin', 'HOME':str(root), 'LANG':'zh_CN.UTF-8',
                       'TMPDIR':str(root), 'ONEPAGER_DATA_DIR':str(data_dir)}
        with (root/'service.log').open('wb') as log:
            process = subprocess.Popen([str(executable), '--ready-file', str(ready)], env=environment,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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
                font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',64)
                draw.text((30,70),'Synthetic drawing workshop',fill='black',font=font)
                picture=root/'synthetic.png';image.save(picture)
                ocr=subprocess.run([str(tools/'local-ocr'),str(picture)],env=environment,capture_output=True,check=True)
                assert any('drawing' in row.lower() for row in json.loads(ocr.stdout)[str(picture)])
                print('安装版格式验证通过：DOCX、PPTX、XLSX、PDF 和内置图片 OCR。')
                connection.close()
                print('安装版验证通过：启动、页面、TXT解析、脱敏确认、本地生成、Word导出、清空材料和内置音频工具。')
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=15)
            assert not ready.exists()
            assert not list((data_dir/'runs').glob('run-*'))
            print('退出验证通过：后端退出，材料运行目录已清理。')


if __name__=='__main__':main()
