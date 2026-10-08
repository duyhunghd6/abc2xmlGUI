"""Regression coverage for physical music lines and their lyric alignment."""
import unittest

import xml2abc


SCORE = '''<score-partwise version="3.1">
<part-list><score-part id="P1"><part-name>Voice</part-name></score-part></part-list>
<part id="P1">
<measure number="1"><attributes><divisions>1</divisions>
<key><fifths>0</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time>
<clef><sign>G</sign><line>2</line></clef></attributes>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration>
<type>whole</type><lyric number="1"><syllabic>single</syllabic><text>First</text></lyric></note>
</measure>
<measure number="2"><print new-system="yes"/>
<note><pitch><step>D</step><octave>4</octave></pitch><duration>4</duration>
<type>whole</type><lyric number="1"><syllabic>single</syllabic><text>Second</text></lyric></note>
<barline location="right"><bar-style>light-heavy</bar-style></barline></measure>
</part></score-partwise>'''


class AbcjsOutputTests(unittest.TestCase):
    def test_system_break_keeps_lyrics_with_corresponding_music(self):
        abc, diagnostics = xml2abc.vertaal(SCORE, abcjs=True)
        self.assertTrue(abc, diagnostics)
        self.assertNotIn('$', abc)
        first, second = abc.index('w: First|'), abc.index('w: Second|')
        self.assertLess(abc.index('%1'), first)
        self.assertLess(first, abc.index('%2'))
        self.assertLess(abc.index('%2'), second)
        self.assertNotIn('w: First|Second|', abc)

    def test_legacy_mode_retains_custom_breaks(self):
        abc, diagnostics = xml2abc.vertaal(SCORE)
        self.assertTrue(abc, diagnostics)
        self.assertIn('I:linebreak $', abc)
        self.assertIn('$', abc.split('K:C', 1)[1])
        self.assertIn('w: First|Second|', abc)

    def test_no_source_breaks_option_remains_effective(self):
        abc, diagnostics = xml2abc.vertaal(SCORE, abcjs=True, x=True)
        self.assertTrue(abc, diagnostics)
        self.assertNotIn('$', abc)
        self.assertIn('w: First|Second|', abc)


if __name__ == '__main__':
    unittest.main()
