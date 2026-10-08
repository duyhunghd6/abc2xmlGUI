# abc2xml GUI

This is a Python GUI to convert music from abc notation to MusicXML and vice versa. It uses abc2xml and xml2abc from [wim.vree.org](https://wim.vree.org/svgParse)   
Download the newest versions and copy them into the GUI's folder.

Thanks to Willem Vree for his extensive beta testing.   
Tested on Windows 10 and Linux Mint 21.

## MusicXML to ABC

The GUI can open compressed `.mxl` scores and plain `.xml` / `.musicxml` files.
It reads the archive's `META-INF/container.xml` to find the score. Invalid input
and failed conversions are reported before saving.

For ABC intended for the bhajan composer or another abcjs viewer:

```sh
python3 xml2abc.py --abcjs -o /path/to/output /path/to/song.mxl
```

`--abcjs` writes source system breaks as physical music lines, with each line's
lyrics immediately below it. It preserves pitches, durations, ties, slurs,
repeats and lyric verse positions. The GUI enables this mode automatically.
The CLI's default retains its existing `$` / `I:linebreak` output format.
Source lyrics and titles are preserved as supplied; missing lyrics are not
reconstructed.

Regression checks: `python3 -m unittest discover -s tests -v`.

## End-to-end output validation

The E2E suite runs the real `xml2abc.py --abcjs` CLI, checks its output with
[abcMIDI](https://github.com/sshlien/abcmidi) (`abc2midi -c`), and parses and
renders it with [abcjs](https://github.com/paulrosen/abcjs) in headless Chromium.
Both upstream repositories are cloned into ignored `.e2e-deps/` directories at
revisions recorded in `tests/e2e/repos.json`. Playwright is locked separately.

On macOS or Linux, install Python 3, Git, a C compiler, Make, and Node.js 20+
with npm, then run from the project directory:

```sh
python3 tests/e2e/setup.py          # one-time download/build; safe to rerun
python3 tests/e2e/test_conversion.py
python3 -m unittest discover -s tests -v
```

On minimal Linux installations, Chromium may also need system libraries:
`cd tests/e2e && npx --no-install playwright install-deps chromium`.

The E2E suite covers `.xml`, `.musicxml`, and manifest-selected `.mxl` scores,
source system breaks, rendered lyrics (including Unicode), pitches, durations,
accidentals, rests, ties, slurs, and repeats. Invalid archives and deliberately
malformed ABC verify that failures are detected. abcMIDI diagnostics are checked
in addition to its exit status; both validators' warnings fail the valid fixtures.
Missing dependencies fail explicitly. The ordinary unit-test command does not
run the browser suite, so run both commands. This exercises conversion and viewer
compatibility; it does not automate the Tk GUI or guarantee every score's layout.

## Windows
On Windows both the Python and exe versions can be used.  
Python has to be in the PATH environment variable.

## Translations
abc2xml GUI speaks English, French, German, Irish and Portuguese.  
Thanks to Batt O'Connor for his help with the Irish.  
Thanks to Benoît Rouits for the French translation and Celestino Gomes for the Portuguese one.  
If you can provide translations into other languages, please be in touch.

## Further Information
For more detailed info visit [blechtrottel.net](http://blechtrottel.net/en/abc2xmlgui.html)

## Version History
1.3  
Exe now finds converters in same folder  
Better detection of system locale  
Better handling of source files  
Better display of converter and Python messages

1.2  
Input and output directories remembered  
Part of tune can be selected for conversion  
UTF-8 handling improved  
Detection of converters improved  
Other minor changes

1.1  
Exe version  
Icon file  
Portuguese translation.

1.0  
Initial release.

## Real song regression cases

Three byte-identical `.mxl` fixtures from
`/Users/steve/Desktop/SahajaYoga/Songs` are stored in
`tests/e2e/fixtures/songs/`, with SHA-256 hashes in `manifest.json`.
This suite calls the GUI's real `readScoreFile` and `xml2abc` methods, replacing
the file-save dialog with a disk-writing callback; it does not click the Tk UI.

```sh
python3 tests/e2e/test_real_songs.py
# To read the original files directly:
ABC_E2E_SONGS_DIR=/Users/steve/Desktop/SahajaYoga/Songs python3 tests/e2e/test_real_songs.py
```

ABC outputs and detailed validation results are written to
`abcxml-output/song-e2e/`. Current real-song results fail abcMIDI validation:
Ganesha has an uneven repeat bar; Mana Mantra has broken-rhythm/tie errors
and an ignored tenuto instruction; Swagata has unclosed repeats. All three
parse and render in abcjs without warnings. These diagnostics remain failing
regression cases rather than being suppressed. GUI imports require Pillow
and Python's tkinter support.

## Recovering markings missing from recognition output

MusicXML exported by optical music recognition may omit lyrics and chords that
are visible in the original scan. In abcjs mode the converter reports source
annotation counts and warns when a category is absent. It cannot infer the
original words or harmony from the notes.

`recover_annotations.py` applies an explicit transcription to a separate
MusicXML file. Annotation JSON includes the source SHA-256, part, measure and
note positions, lyrics, chord labels, and provenance. A mismatched source is
rejected. Swagata's transcription is in `recovery/swagata.annotations.json`:

```sh
python3 recover_annotations.py song.mxl recovery/swagata.annotations.json song.recovered.musicxml
python3 xml2abc.py --abcjs -o output song.recovered.musicxml
```

This recovery replaces recognized lyrics in the specified measures and adds
transcribed chord labels. Pitches, durations, ties, slurs and repeat markings
remain as recognized. Swagata's measure 13 has a recognized tie between the
syllables “ji” and “Ke” that needs articulation review. Optional Gm labels in
measures 9 and 17 retain their onset but not their printed parentheses. Guitar
diagram fingerings are not recovered. `Gm(Eb)` retains the printed alternative
as one chord label; the converter supports custom MusicXML `kind=other` text.
