// Browser-Abnahme der Timeline (manuell, nicht Teil von tests/run.sh): Tastatur, reduzierte Bewegung, kein horizontales
// Scrollen bei 375 px. Die Kontraste prüft tests/browser/kontrast.mjs für die ganze Seite.
// Ablauf wie bei timeline-nachladen.mjs: Seite bauen und ausliefern, Chromium mit --remote-debugging-port starten, dann
//   node tests/browser/timeline-abnahme.mjs http://localhost:8000 9333
const [,, base, port] = process.argv;
const sleep = ms => new Promise(r => setTimeout(r, ms));
let fails = 0;
const check = (ok, text) => { console.log(`${ok ? 'ok    ' : 'FEHLER'} ${text}`); if (!ok) fails = 1; };

const tab = await (await fetch(`http://localhost:${port}/json/new?about:blank`, { method: 'PUT' })).json();
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) pending.get(m.id)(m.result); });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result.value;
const open = async (path, width = 1280) => {
  await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: base + path }); await sleep(1500);
};
const key = (k, code, vk, text) => send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code, windowsVirtualKeyCode: vk, text })
  .then(() => send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk }));

// 2. Kein horizontales Scrollen bei 375 px (Startseite und /timeline/)
for (const p of ['/', '/timeline/']) {
  await open(p, 375);
  const w = await ev(`[document.documentElement.scrollWidth, window.innerWidth]`);
  check(w[0] <= w[1], `kein horizontales Scrollen bei 375 px auf ${p} (scrollWidth ${w[0]}, innerWidth ${w[1]})`);
}

// 3. Tastatur: Tab erreicht ein Bookmark, Enter und Leertaste klappen es auf und zu, der Fokus ist sichtbar
await open('/');
let found = false;
for (let i = 0; i < 40 && !found; i++) { await key('Tab', 'Tab', 9); found = await ev(`document.activeElement && document.activeElement.tagName === 'SUMMARY'`); }
check(found, 'Tab erreicht eine aufklappbare Zeile (summary)');
if (found) {
  const o = await ev(`(() => { const s = getComputedStyle(document.activeElement); return [s.outlineStyle, parseFloat(s.outlineWidth)]; })()`);
  check(o[0] !== 'none' && o[1] > 0, `Fokus sichtbar (outline ${o[0]} ${o[1]}px)`);
  const state = () => ev(`document.activeElement.parentElement.open`);
  const before = await state();
  await key('Enter', 'Enter', 13, '\r'); await sleep(100); const afterEnter = await state();
  await key(' ', 'Space', 32, ' '); await sleep(100); const afterSpace = await state();
  check(before === false && afterEnter === true, 'Enter klappt auf');
  check(afterSpace === false, 'Leertaste klappt wieder zu');
}

// 4. Reduzierte Bewegung: keine Übergänge oder Animationen an der Timeline
await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
await open('/');
const motion = await ev(`['.tl-item', '.tl-item a', '.tl-item summary', '.timeline-scroll'].map(s => { const c = getComputedStyle(document.querySelector(s)); return parseFloat(c.transitionDuration) + parseFloat(c.animationDuration); }).reduce((a, b) => a + b, 0)`);
check(motion === 0, `reduzierte Bewegung: keine Übergänge oder Animationen (Summe ${motion}s)`);
console.log(fails ? 'ERGEBNIS: Fehler' : 'ERGEBNIS: alles ok');
ws.close(); process.exit(fails);
