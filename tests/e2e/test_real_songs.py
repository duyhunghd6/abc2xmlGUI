"""Real song files through the GUI's reader, conversion method and save callback."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
import abc2xmlGUI
import test_conversion as validators
from test_conversion import run, midi_diagnostics


class Value:
    def get(self):
        return ''


class RealSongsE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        validators.ConversionE2E.setUpClass()

    def test_actual_songs_through_gui_conversion(self):
        fixtures = Path(os.environ.get('ABC_E2E_SONGS_DIR', HERE / 'fixtures/songs'))
        output = ROOT / 'abcxml-output/song-e2e'
        output.mkdir(parents=True, exist_ok=True)
        manifest = json.loads((HERE / 'fixtures/songs/manifest.json').read_text())
        songs = [fixtures / item['filename'] for item in manifest]
        for source, item in zip(songs, manifest):
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), item['sha256'],
                             f'Source changed: {source}')
        report = []
        failures = []
        for source in songs:
            with self.subTest(song=source.name):
                # Exercise the actual GUI method without opening native file dialogs.
                gui = abc2xmlGUI.abc2xmlGUI.__new__(abc2xmlGUI.abc2xmlGUI)
                gui.pathXml2Abc = 'import'
                gui.scoreLineBreak = Value()
                gui.txt = abc2xmlGUI.readScoreFile(str(source))
                gui.messages = 'off'
                gui.filename = ''
                target = output / (source.stem + '.abc')
                gui.saveFile = lambda text: target.write_text(text, encoding='utf-8')
                gui.xml2abc()
                midi = run(validators.ConversionE2E.midi, target, '-c', cwd=output)
                browser = run('node', HERE / 'check_abcjs.cjs', target)
                parsed = json.loads(browser.stdout) if browser.stdout.strip() else {}
                item = {
                    'source': str(source),
                    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'abc': target.name,
                    'abcmidi_exit': midi.returncode,
                    'abcmidi_diagnostics': midi_diagnostics(midi),
                    'abcmidi_output': midi.stdout + midi.stderr,
                    'abcjs_exit': browser.returncode,
                    'abcjs': parsed,
                    'browser_stderr': browser.stderr,
                }
                report.append(item)
                if midi.returncode or item['abcmidi_diagnostics'] or browser.returncode:
                    failures.append(source.name)
        (output / 'validation-report.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        self.assertEqual(failures, [], 'See abcxml-output/song-e2e/validation-report.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
