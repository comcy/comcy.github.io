// Browser-Prüfung des Nachladens (manuell, nicht Teil von tests/run.sh): zählt Einträge der Timeline nach Scrollen.
// Ablauf: Seite mit mehr als TL_MAX Einträgen bauen und per http.server ausliefern, Chromium mit
//   chromium --headless --no-sandbox --remote-debugging-port=9333 about:blank
// starten, dann: node tests/browser/timeline-nachladen.mjs http://localhost:8000/ 9333
// Erwartung bei 25 Einträgen: am Ende 25 Einträge, zwei abgerufene Fragmente, keine Doppelungen, keine Marke mehr.
const [,, url, port] = process.argv;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const tab = await (await fetch(`http://localhost:${port}/json/new?${url}`, { method: 'PUT' })).json();
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) pending.get(m.id)(m.result); });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value;
await sleep(1500);
const count = () => ev(`document.querySelectorAll('.timeline-scroll .tl-item').length`);
const fetched = () => ev(`performance.getEntriesByType('resource').filter(r => /chunk-/.test(r.name)).map(r => r.name.split('/').pop()).join(',')`);
const out = [`start: ${await count()} Einträge`];
for (let k = 1; k <= 5; k++) {
  await ev(`(b => { b.scrollTop = b.scrollHeight; })(document.querySelector('.timeline-scroll'))`);
  await sleep(700);
  out.push(`nach Scroll ${k}: ${await count()} Einträge, abgerufen: [${await fetched()}], Marke: ${await ev(`document.querySelectorAll('.tl-sentinel').length`)}, Link: ${await ev(`!!document.querySelector('.timeline-more a')`)}`);
}
const dups = await ev(`(() => { const h = [...document.querySelectorAll('.timeline-scroll .tl-item a')].map(a => a.getAttribute('href')); return h.length - new Set(h).size; })()`);
out.push(`Doppelungen: ${dups}`);
console.log(out.join('\n'));
ws.close(); process.exit(0);
