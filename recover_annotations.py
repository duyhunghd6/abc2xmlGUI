"""Restore explicitly transcribed lyrics/chords to a matching MusicXML source.

Usage: python3 recover_annotations.py source.mxl annotations.json recovered.musicxml
The annotation file is bound to the source hash; no music is inferred.
"""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, is_zipfile


def recover(source, annotations):
    data = Path(source).read_bytes()
    if hashlib.sha256(data).hexdigest() != annotations['source_sha256']:
        raise ValueError('Annotations do not match this source file.')
    if is_zipfile(source):
        with ZipFile(source) as archive:
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            names = [e.get('full-path') for e in container.iter()
                     if e.tag.rsplit('}', 1)[-1] == 'rootfile']
            data = archive.read(names[0])
    root = ET.fromstring(data)
    part = root.find("part[@id='%s']" % annotations['part'])
    if part is None:
        raise ValueError('Annotation part is missing.')
    for record in annotations['measures']:
        measure = part.find("measure[@number='%s']" % record['number'])
        if measure is None:
            raise ValueError('Annotation measure is missing.')
        notes = measure.findall('note')
        if len(notes) != len(record['lyrics']):
            raise ValueError('Annotation note count does not match measure %s.' % record['number'])
        for note in notes:
            for lyric in note.findall('lyric'):
                note.remove(lyric)
        previous_token = None
        for index, (note, token) in enumerate(zip(notes, record['lyrics'])):
            if token is None:
                continue
            if note.find('rest') is not None:
                raise ValueError('Cannot attach a lyric to a rest.')
            lyric = ET.SubElement(note, 'lyric', number='1')
            syllabic = 'begin' if token.endswith('-') else 'single'
            if previous_token and previous_token.endswith('-'):
                syllabic = 'middle' if token.endswith('-') else 'end'
            ET.SubElement(lyric, 'syllabic').text = syllabic
            ET.SubElement(lyric, 'text').text = token.rstrip('-')
            previous_token = token
            if index + 1 < len(notes) and record['lyrics'][index + 1] is None and notes[index + 1].find('rest') is None:
                ET.SubElement(lyric, 'extend')
        for note_number, symbol in record['chords']:
            note = notes[note_number - 1]
            harmony = ET.Element('harmony')
            chord_root = ET.SubElement(harmony, 'root')
            ET.SubElement(chord_root, 'root-step').text = symbol[0]
            suffix = symbol[1:]
            if suffix.startswith('b'):
                ET.SubElement(chord_root, 'root-alter').text = '-1'
                suffix = suffix[1:]
            if suffix in ('', 'm'):
                ET.SubElement(harmony, 'kind').text = 'minor' if suffix == 'm' else 'major'
            elif suffix.startswith('m(') and suffix.endswith(')'):
                # Retain a printed alternative as one label, not a new chord change.
                ET.SubElement(harmony, 'kind', text=suffix).text = 'other'
            else:
                raise ValueError('Unsupported transcribed chord: ' + symbol)
            measure.insert(list(measure).index(note), harmony)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    source, annotations, output = sys.argv[1:]
    Path(output).write_bytes(recover(source, json.loads(Path(annotations).read_text())))
