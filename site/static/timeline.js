// Lädt weitere Timeline-Einträge nach, wenn das Ende des Containers erreicht ist: Fragmente /timeline/chunk-N.html (siehe build.sh)
(function () {
  var box = document.querySelector('.timeline-scroll[data-chunks]');
  if (!box || !('IntersectionObserver' in window) || !window.fetch) return;
  var total = parseInt(box.getAttribute('data-chunks'), 10), src = box.getAttribute('data-src');
  var list = box.querySelector('.timeline-list'), loaded = 0, busy = false;
  // Marke am Listenende: sobald sie im Container sichtbar wird, kommt das nächste Fragment
  var sentinel = document.createElement('li');
  sentinel.className = 'tl-sentinel';
  sentinel.setAttribute('aria-hidden', 'true');
  list.appendChild(sentinel);
  var io = new IntersectionObserver(function (entries) {
    if (entries[0].isIntersecting) next();
  }, { root: box });
  function done() { io.disconnect(); sentinel.remove(); }
  function next() {
    if (busy || loaded >= total) return;
    busy = true; loaded++;
    fetch(src + loaded + '.html').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    }).then(function (html) {
      sentinel.insertAdjacentHTML('beforebegin', html);
      busy = false;
      if (loaded >= total) { done(); return; }
      io.unobserve(sentinel); io.observe(sentinel); // erneut prüfen, falls die Marke noch sichtbar ist
    }).catch(done); // bei Fehler Schluss, der Link "Alles ansehen" bleibt
  }
  io.observe(sentinel);
})();
