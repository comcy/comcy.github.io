// Kontrast-Prüfung der ganzen Seite (manuell, nicht Teil von tests/run.sh): Links und gedämpfter Text in allen acht
// Farbvarianten, WCAG AA (4,5:1 für Text, 3:1 für Punkte der Timeline) gegen den schwächeren Wert von --bg und --bg2.
// Ablauf: Seite bauen und ausliefern (mit Beiträgen mit Tags und mehr als einem Timeline-Eintrag), Chromium mit
//   chromium --headless --no-sandbox --remote-debugging-port=9333 about:blank
// starten, dann: node tests/browser/kontrast.mjs http://localhost:8000 9333 /blog/<slug-eines-beitrags>/
const [,, base, port, post = '/blog/'] = process.argv;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PAGES = ['/', '/blog/', post, '/tags/', '/timeline/', '/about/'];
// Bezeichnung, Selektor, Mindestkontrast
const KINDS = [
  ['Link im Text', 'main p a, article a, .timeline-more a', 4.5],
  ['Beitragskarte (Titel)', '.posts li > a', 4.5],
  ['Tag', 'a.tag', 4.5],
  ['Menü', 'nav a', 4.5],
  ['Footer-Link', 'footer.site a', 4.5],
  ['Timeline-Link', '.tl-item a, .tl-item summary', 4.5],
  ['Datum und Meta', '.meta, .posts .date, .tl-item time, .tl-item details p', 4.5],
  ['Footer-Text', 'footer.site p', 4.5],
  ['Timeline-Punkt', '.tl-item::before', 3],
];
const tab = await (await fetch(`http://localhost:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) pending.get(m.id)(m.result); });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value;
const lum = ([r, g, b]) => { const f = c => { c /= 255; return c <= .03928 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + .05) / (y + .05); };
const rgb = s => {
  let m = s.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/); if (m) return [+m[1], +m[2], +m[3]];
  m = s.match(/color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)/); // color-mix liefert dieses Format
  return m ? [m[1] * 255, m[2] * 255, m[3] * 255] : null;
};
let fails = 0; const worstOf = new Map();
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
for (const page of PAGES) {
  await send('Page.navigate', { url: base + page }); await sleep(1200);
  for (const pal of ['glass', 'nord', 'neon', 'pastel']) for (const mode of ['dark', 'light']) {
    const found = await ev(`(() => {
      const h = document.documentElement; h.dataset.palette = '${pal}'; h.dataset.theme = '${mode}';
      const v = n => getComputedStyle(h).getPropertyValue(n).trim();
      const hex = x => { const m = x.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i); return m ? 'rgb(' + parseInt(m[1],16) + ',' + parseInt(m[2],16) + ',' + parseInt(m[3],16) + ')' : x; };
      const out = { bg: hex(v('--bg')), bg2: hex(v('--bg2')), kinds: {} };
      for (const [label, sel] of ${JSON.stringify(KINDS.map(k => [k[0], k[1]]))}) {
        const parts = sel.split(',').map(s => s.trim());
        const colors = [];
        for (const p of parts) {
          const pseudo = p.endsWith('::before') ? '::before' : null; const q = pseudo ? p.slice(0, -8) : p;
          document.querySelectorAll(q).forEach(el => { if (el.offsetParent === null && el.tagName !== 'BODY') return; const cs = getComputedStyle(el, pseudo); colors.push(pseudo ? cs.backgroundColor : cs.color); });
        }
        out.kinds[label] = [...new Set(colors)];
      }
      return out;
    })()`);
    const bgs = [rgb(found.bg), rgb(found.bg2)];
    for (const [label, , min] of KINDS) for (const c of found.kinds[label] || []) {
      const col = rgb(c); if (!col) continue;
      const w = Math.min(...bgs.map(b => ratio(col, b)));
      const key = `${label} | ${pal} ${mode}`; const prev = worstOf.get(key);
      if (!prev || w < prev.w) worstOf.set(key, { w, min, page });
    }
  }
}
for (const [key, { w, min, page }] of worstOf) {
  const ok = w >= min; if (!ok) fails++;
  console.log(`${ok ? 'ok    ' : 'FEHLER'} ${key}: ${w.toFixed(2)}:1 (min ${min}:1, schwächste Seite ${page})`);
}
console.log(fails ? `ERGEBNIS: ${fails} Fehler` : 'ERGEBNIS: alles ok');
ws.close(); process.exit(fails ? 1 : 0);
