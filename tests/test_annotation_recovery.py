import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

import xml2abc
from recover_annotations import recover
from test_abcjs_output import SCORE


class AnnotationRecoveryTests(unittest.TestCase):
    def annotations(self):
        return {'source_sha256': hashlib.sha256(SCORE.encode()).hexdigest(),
                'part': 'P1', 'measures': [
                    {'number': 1, 'lyrics': ['Hari'], 'chords': [[1, 'Gm(Eb)']]},
                    {'number': 2, 'lyrics': ['Bol'], 'chords': [[1, 'Dm']]}]}

    def test_lyrics_and_custom_chord_survive_conversion_without_music_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.musicxml'
            source.write_text(SCORE)
            restored = recover(source, self.annotations())
        before, after = ET.fromstring(SCORE), ET.fromstring(restored)
        def music(root):
            root = copy.deepcopy(root)
            for parent in root.iter():
                for child in list(parent):
                    if child.tag in ('lyric', 'harmony'):
                        parent.remove(child)
            return ET.tostring(root)
        self.assertEqual(music(before), music(after))
        abc, diagnostics = xml2abc.vertaal(restored, abcjs=True)
        self.assertTrue(abc, diagnostics)
        self.assertIn('"Gm(Eb)"', abc)
        self.assertIn('"Dm"', abc)
        self.assertIn('w: Hari|', abc)
        self.assertIn('w: Bol|', abc)
        self.assertNotIn('First', abc)

    def test_rejects_annotations_for_different_source(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.musicxml'
            source.write_text(SCORE + '\n')
            with self.assertRaisesRegex(ValueError, 'do not match'):
                recover(source, self.annotations())

    def test_reports_missing_source_annotations(self):
        root = ET.fromstring(SCORE)
        for note in root.findall('.//note'):
            for lyric in note.findall('lyric'):
                note.remove(lyric)
        abc, diagnostics = xml2abc.vertaal(ET.tostring(root), abcjs=True)
        self.assertTrue(abc)
        self.assertIn('0 lyric text entries, 0 chord symbols', diagnostics)
        self.assertIn('Missing source annotations', diagnostics)


if __name__ == '__main__':
    unittest.main()
