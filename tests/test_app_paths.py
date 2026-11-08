import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths
import audio_transcriber
import document_parser


class AppPathTests(unittest.TestCase):
    def test_model_uses_bundle_on_clean_install_and_user_copy_after_upgrade(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict('os.environ', {}, clear=True):
            root = Path(temporary)
            data = root / 'user-data'
            bundled = root / 'resources/models' / audio_transcriber.MODEL_NAME
            bundled.parent.mkdir(parents=True)
            bundled.touch()
            with patch.object(audio_transcriber, 'resource_dir', return_value=root / 'resources'):
                self.assertEqual(bundled, audio_transcriber.model_path(data))
                installed = data / 'models' / audio_transcriber.MODEL_NAME
                installed.parent.mkdir(parents=True)
                installed.touch()
                self.assertEqual(installed, audio_transcriber.model_path(data))
                bundled.unlink()
                installed.unlink()
                self.assertEqual(installed, audio_transcriber.model_path(data))

    def test_explicit_model_path_overrides_bundle(self):
        with patch.dict('os.environ', {'WHISPER_MODEL_PATH': '/synthetic-model.bin'}):
            self.assertEqual(Path('/synthetic-model.bin'), audio_transcriber.model_path(Path('/synthetic-data')))

    def test_source_keeps_local_uploads(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(app_paths.sys, 'frozen', False, create=True):
            self.assertEqual(app_paths.resource_dir() / 'uploads', app_paths.user_data_dir())

    def test_frozen_mac_data_is_outside_bundle(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(app_paths.sys, 'frozen', True, create=True), \
             patch.object(app_paths.sys, 'platform', 'darwin'), patch.object(app_paths.Path, 'home', return_value=Path('/synthetic-user')):
            self.assertEqual(Path('/synthetic-user/Library/Application Support/TrainingOnePager'), app_paths.user_data_dir())

    def test_configured_data_dir_is_resolved(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict('os.environ', {'ONEPAGER_DATA_DIR': temporary}):
            self.assertEqual(Path(temporary).resolve(), app_paths.user_data_dir())

    def test_audio_prefers_bundled_program(self):
        with tempfile.NamedTemporaryFile() as program, patch.dict('os.environ', {}, clear=True), \
             patch.object(audio_transcriber, 'bundled_tool', return_value=program.name):
            with patch.object(audio_transcriber.shutil, 'which') as search:
                self.assertEqual(program.name, audio_transcriber.executable('ffmpeg'))
                search.assert_not_called()

    def test_ocr_uses_bundled_engine_without_compiler(self):
        import types
        with patch.object(document_parser, 'bundled_tool', return_value='/synthetic-tools/local-ocr'), \
             patch.object(document_parser.subprocess, 'run', return_value=types.SimpleNamespace(stdout=b'{"image.png":["test"]}')) as run:
            recognized, available = document_parser._recognize_images([Path('image.png')])
            self.assertTrue(available)
            self.assertEqual(['test'], recognized['image.png'])
            self.assertEqual('/synthetic-tools/local-ocr', run.call_args.args[0][0])
