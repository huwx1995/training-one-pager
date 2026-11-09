import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import app_paths
import document_parser
import platform_runtime

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('windows_desktop',ROOT/'packaging/windows/desktop.py')
desktop=importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class PlatformRuntimeTests(unittest.TestCase):
    def test_current_process_is_alive_without_termination(self):
        self.assertTrue(platform_runtime.process_alive(os.getpid()))
        self.assertFalse(platform_runtime.process_alive(0))

    def test_windows_query_never_uses_os_kill(self):
        with patch.object(platform_runtime.os,'name','nt'), \
             patch.object(platform_runtime,'_windows_process_alive',return_value=True) as query, \
             patch.object(platform_runtime.os,'kill') as kill:
            self.assertTrue(platform_runtime.process_alive(123))
            query.assert_called_once_with(123)
            kill.assert_not_called()

    def test_windows_helpers_hide_console(self):
        with patch.object(platform_runtime.os,'name','nt'), patch.object(platform_runtime.subprocess,'run') as run:
            platform_runtime.run_tool(['synthetic.exe'],check=True,text=True)
            self.assertEqual(0x08000000,run.call_args.kwargs['creationflags'])
            self.assertEqual('utf-8',run.call_args.kwargs['encoding'])

    def test_bundled_windows_executable_resolves_exe_suffix(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'tools').mkdir();program=root/'tools/ffmpeg.exe';program.touch()
            with patch.object(app_paths,'resource_dir',return_value=root), patch.object(app_paths.sys,'platform','win32'):
                self.assertEqual(str(program),app_paths.bundled_tool('ffmpeg'))
                self.assertEqual(str(program),app_paths.bundled_tool('ffmpeg.exe'))

    def test_windows_launcher_does_not_inherit_credentials_or_model_overrides(self):
        with patch.dict(os.environ,{'LLM_API_KEY':'synthetic-private-value','WHISPER_MODEL_PATH':'synthetic-model','PATH':'synthetic-path'},clear=True):
            environment=desktop.sanitized_environment()
        self.assertNotIn('LLM_API_KEY',environment)
        self.assertNotIn('WHISPER_MODEL_PATH',environment)
        self.assertEqual('synthetic-path',environment['PATH'])

    def test_packaged_ocr_passes_explicit_language_directory(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'tessdata').mkdir()
            program=root/'tesseract.exe';program.touch()
            responses=[Mock(stdout='List of available languages:\nchi_sim\neng\n'),Mock(stdout='Synthetic drawing text')]
            with patch.object(document_parser,'resource_dir',return_value=root), \
                 patch.object(document_parser,'bundled_tool',return_value=None), \
                 patch.object(document_parser.sys,'platform','win32'), \
                 patch.object(document_parser,'_local_tool',return_value=str(program)), \
                 patch.object(document_parser,'run_tool',side_effect=responses) as run:
                recognized,available=document_parser._recognize_images([root/'synthetic.png'])
                self.assertTrue(available)
                self.assertEqual(['Synthetic drawing text'],recognized[str(root/'synthetic.png')])
                for call in run.call_args_list:
                    self.assertIn(str(root/'tessdata'),call.args[0])


if __name__=='__main__':unittest.main()
