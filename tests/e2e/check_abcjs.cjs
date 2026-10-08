// Parse and render with the pinned upstream abcjs distribution in real Chromium.
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setContent('<!doctype html><html><body><div id="score"></div></body></html>');
    await page.addScriptTag({ path: path.resolve(__dirname, '../../.e2e-deps/abcjs/dist/abcjs-basic.js') });
    const result = await page.evaluate(abc => {
      const parsed = ABCJS.parseOnly(abc);
      const rendered = ABCJS.renderAbc('score', abc);
      const lines = parsed.flatMap(tune => tune.lines.filter(line => line.staff).map(line =>
        line.staff.flatMap(staff => staff.voices.flatMap(voice =>
          voice.filter(item => item.el_type === 'note').map(item => ({
            pitches: (item.pitches || []).map(pitch => ({
              pitch: pitch.pitch, accidental: pitch.accidental || null,
              startTie: !!pitch.startTie, endTie: !!pitch.endTie,
              startSlur: !!pitch.startSlur, endSlur: !!pitch.endSlur
            })),
            duration: item.duration,
            rest: !!item.rest,
            lyrics: (item.lyric || []).map(lyric => lyric.syllable)
          }))))));
      return {
        tunes: parsed.length, rendered: rendered.length,
        warnings: [...new Set([...parsed, ...rendered].flatMap(tune => tune.warnings || []))],
        lines,
        bars: parsed.flatMap(tune => tune.lines.flatMap(line => (line.staff || []).flatMap(staff =>
          staff.voices.flatMap(voice => voice.filter(item => item.el_type === 'bar').map(item => item.type))))),
        svgCount: document.querySelectorAll('#score svg').length,
        pathCount: document.querySelectorAll('#score svg path').length,
        text: document.getElementById('score').textContent
      };
    }, fs.readFileSync(process.argv[2], 'utf8'));
    result.errors = errors;
    process.stdout.write(JSON.stringify(result));
    if (errors.length || result.warnings.length || !result.tunes || !result.svgCount || !result.pathCount)
      process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
