"""Real CLI -> abcMIDI check -> abcjs parse/render. Run directly; no silent skips."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_abcjs_output import SCORE

MUSICAL_SCORE = '''<score-partwise version="3.1">
<part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
<part id="P1"><measure number="1">
<attributes><divisions>1</divisions><key><fifths>0</fifths></key>
<time><beats>4</beats><beat-type>4</beat-type></time>
<clef><sign>G</sign><line>2</line></clef></attributes>
<barline location="left"><repeat direction="forward"/></barline>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration>
<tie type="start"/><type>quarter</type><notations><tied type="start"/></notations>
<lyric><syllabic>single</syllabic><text>Hé</text></lyric></note>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration>
<tie type="stop"/><type>quarter</type><notations><tied type="stop"/></notations></note>
<note><pitch><step>D</step><alter>1</alter><octave>4</octave></pitch><duration>1</duration>
<type>quarter</type><accidental>sharp</accidental></note>
<note><rest/><duration>1</duration><type>quarter</type></note>
</measure><measure number="2"><print new-system="yes"/>
<note><pitch><step>E</step><octave>4</octave></pitch><duration>2</duration><type>half</type>
<notations><slur type="start" number="1"/></notations>
<lyric><syllabic>single</syllabic><text>World</text></lyric></note>
<note><pitch><step>F</step><octave>4</octave></pitch><duration>2</duration><type>half</type>
<notations><slur type="stop" number="1"/></notations></note>
<barline location="right"><repeat direction="backward"/></barline>
</measure></part></score-partwise>'''


def run(*args, cwd=ROOT):
    return subprocess.run([str(arg) for arg in args], cwd=cwd, text=True,
                          capture_output=True, timeout=60)


def midi_diagnostics(result):
    # abc2midi can return zero even when the input contains errors.
    return re.findall(r'^.*\b(?:Error|Warning|Fatal)\b.*$',
                      result.stdout + '\n' + result.stderr, re.I | re.M)


class ConversionE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.midi = ROOT / '.e2e-deps/abcmidi/abc2midi'
        if not cls.midi.is_file():
            raise RuntimeError('Run python3 tests/e2e/setup.py first.')
        for name, spec in json.loads((HERE / 'repos.json').read_text()).items():
            result = run('git', 'rev-parse', 'HEAD', cwd=ROOT / '.e2e-deps' / name)
            if result.returncode or result.stdout.strip() != spec['revision']:
                raise RuntimeError(f'{name} revision mismatch; run tests/e2e/setup.py.')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='abc-e2e-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def validate(self, abc):
        midi = run(self.midi, abc, '-c', cwd=self.folder)
        self.assertEqual(midi.returncode, 0, midi.stdout + midi.stderr)
        self.assertEqual(midi_diagnostics(midi), [], midi.stdout + midi.stderr)
        self.assertFalse(list(self.folder.glob('*.mid')), 'Check mode must not generate MIDI')
        browser = run('node', HERE / 'check_abcjs.cjs', abc)
        self.assertEqual(browser.returncode, 0, browser.stdout + browser.stderr)
        result = json.loads(browser.stdout)
        self.assertEqual(result['tunes'], 1)
        self.assertEqual(result['rendered'], 1)
        return result

    def convert(self, score, extension):
        source = self.folder / ('score' + extension)
        if extension == '.mxl':
            with zipfile.ZipFile(source, 'w', zipfile.ZIP_DEFLATED) as archive:
                # A decoy catches converters that take the first XML file in the ZIP.
                archive.writestr('decoy.xml', '<not-a-score/>')
                archive.writestr('META-INF/container.xml', '''<container
                  xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
                  <rootfiles><rootfile full-path="scores/main.musicxml"
                  media-type="application/vnd.recordare.musicxml+xml"/></rootfiles></container>''')
                archive.writestr('scores/main.musicxml', score)
        else:
            source.write_text(score, encoding='utf-8')
        result = run(sys.executable, ROOT / 'xml2abc.py', '--abcjs', '-o', self.folder, source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        abc = self.folder / 'score.abc'
        self.assertTrue(abc.is_file(), result.stdout + result.stderr)
        self.assertTrue(abc.read_text(encoding='utf-8').strip())
        return self.validate(abc)

    def test_system_breaks_and_lyrics_for_all_input_formats(self):
        for extension in ('.xml', '.musicxml', '.mxl'):
            with self.subTest(extension=extension):
                result = self.convert(SCORE, extension)
                self.assertEqual(len(result['lines']), 2)
                self.assertEqual([line[0]['lyrics'] for line in result['lines']],
                                 [['First'], ['Second']])
                notes = [note for line in result['lines'] for note in line]
                self.assertEqual([note['pitches'][0]['pitch'] for note in notes], [0, 1])
                self.assertEqual([note['duration'] for note in notes], [1, 1])
                for lyric in ('First', 'Second'):
                    self.assertIn(lyric, result['text'])

    def test_music_semantics_survive_conversion_and_rendering(self):
        result = self.convert(MUSICAL_SCORE, '.musicxml')
        notes = [note for line in result['lines'] for note in line]
        self.assertEqual([note['duration'] for note in notes], [.25, .25, .25, .25, .5, .5])
        self.assertEqual([p['pitch'] for note in notes for p in note['pitches']], [0, 0, 1, 2, 3])
        self.assertTrue(notes[0]['pitches'][0]['startTie'])
        self.assertTrue(notes[1]['pitches'][0]['endTie'])
        self.assertEqual(notes[2]['pitches'][0]['accidental'], 'sharp')
        self.assertTrue(notes[3]['rest'])
        self.assertTrue(notes[4]['pitches'][0]['startSlur'])
        self.assertTrue(notes[5]['pitches'][0]['endSlur'])
        self.assertIn('bar_left_repeat', result['bars'])
        self.assertIn('bar_right_repeat', result['bars'])
        for lyric in ('Hé', 'World'):
            self.assertIn(lyric, result['text'])

    def test_invalid_mxl_manifests_fail_without_output(self):
        cases = (
            (None, 'no META-INF/container.xml'),
            ('<container><rootfiles/></container>', 'does not identify a score file'),
            ('<container><rootfiles><rootfile full-path="missing.xml"/></rootfiles></container>',
             'score file listed in the archive is missing'),
        )
        for manifest, expected in cases:
            with self.subTest(manifest=manifest):
                source = self.folder / 'invalid.mxl'
                with zipfile.ZipFile(source, 'w') as archive:
                    archive.writestr('decoy.xml', SCORE)
                    if manifest is not None:
                        archive.writestr('META-INF/container.xml', manifest)
                result = run(sys.executable, ROOT / 'xml2abc.py', '--abcjs',
                             '-o', self.folder, source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assertFalse((self.folder / 'invalid.abc').exists())

    def test_both_validators_detect_malformed_abc(self):
        abc = self.folder / 'invalid.abc'
        abc.write_text('X:1\nT:Invalid\nM:4/4\nL:1/8\nK:C\nC8 @ |\n', encoding='utf-8')
        midi = run(self.midi, abc, '-c', cwd=self.folder)
        self.assertTrue(midi_diagnostics(midi), midi.stdout + midi.stderr)
        browser = run('node', HERE / 'check_abcjs.cjs', abc)
        self.assertEqual(browser.returncode, 1, browser.stdout + browser.stderr)
        self.assertTrue(browser.stdout.strip(), browser.stderr)
        self.assertTrue(json.loads(browser.stdout)['warnings'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
