// Hell/Dunkel-Umschalter (Standard Dunkel) und Farbschema-Auswahl (Glass, Nord, Neon, Pastell, je Dunkel und Hell), beide merken sich die Wahl, Menü-Button für schmale Bildschirme, Kopieren-Button für Code-Blöcke
(function () {
  var root = document.documentElement;
  try {
    var saved = localStorage.getItem('theme'); if (saved) root.dataset.theme = saved;
    var palette = localStorage.getItem('palette'); if (palette) root.dataset.palette = palette;
  } catch (e) {}

  // Dark ist der Standard, nur ein gespeichertes "light" schaltet auf Hell
  function isDark() { return root.dataset.theme !== 'light'; }

  document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.getElementById('theme-toggle');
    var syncTheme = function () { if (toggle) toggle.textContent = isDark() ? '☀️' : '🌙'; };
    syncTheme();
    if (toggle) {
      toggle.addEventListener('click', function () {
        root.dataset.theme = isDark() ? 'light' : 'dark';
        try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
        syncTheme();
      });
    }

    // Farbschemata: Der Palette-Knopf öffnet eine Auswahl mit allen Schemata, je in Dunkel und Hell
    var PALETTES = [
      { id: 'glass', name: 'Modern Glass', dots: ['#8b8bff', '#2dd4df', '#0d1020'] },
      { id: 'nord', name: 'Nord', dots: ['#88c0d0', '#81a1c1', '#2e3440'] },
      { id: 'neon', name: 'Neon', dots: ['#ff4fd8', '#faff4f', '#3dff9a', '#b86bff'] },
      { id: 'pastel', name: 'Pastell', dots: ['#ffb8e8', '#fff0a6', '#b6f2cf', '#c9b6ff'] }
    ];
    var paletteId = function () { return root.dataset.palette || 'glass'; };
    var paletteName = function () {
      for (var i = 0; i < PALETTES.length; i++) if (PALETTES[i].id === paletteId()) return PALETTES[i].name;
      return PALETTES[0].name;
    };
    var apply = function (id, mode) {
      root.dataset.palette = id;
      root.dataset.theme = mode;
      try {
        localStorage.setItem('palette', id);
        localStorage.setItem('theme', mode);
      } catch (e) {}
      syncTheme();
    };
    var paletteBtn = document.getElementById('palette-toggle');
    var panel = null;
    var closePanel = function () {
      if (!panel) return;
      panel.remove();
      panel = null;
      paletteBtn.setAttribute('aria-expanded', 'false');
    };
    if (paletteBtn) {
      paletteBtn.setAttribute('aria-expanded', 'false');
      paletteBtn.title = 'Farbschema wählen';
      var renderPanel = function () {
        if (panel) panel.remove();
        panel = document.createElement('div');
        panel.className = 'theme-panel';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-label', 'Farbschema wählen');
        PALETTES.forEach(function (p) {
          var row = document.createElement('div');
          row.className = 'theme-row';
          var dots = document.createElement('span');
          dots.className = 'theme-dots';
          p.dots.forEach(function (c) {
            var d = document.createElement('i');
            d.style.background = c;
            dots.appendChild(d);
          });
          var name = document.createElement('span');
          name.className = 'theme-name';
          name.textContent = p.name;
          row.appendChild(dots);
          row.appendChild(name);
          [['dark', 'Dunkel'], ['light', 'Hell']].forEach(function (m) {
            var b = document.createElement('button');
            b.type = 'button';
            b.className = 'theme-opt';
            b.textContent = m[1];
            var active = paletteId() === p.id && (root.dataset.theme === 'light') === (m[0] === 'light');
            if (active) { b.classList.add('active'); b.setAttribute('aria-pressed', 'true'); }
            else b.setAttribute('aria-pressed', 'false');
            b.addEventListener('click', function () {
              apply(p.id, m[0]);
              renderPanel();
            });
            row.appendChild(b);
          });
          panel.appendChild(row);
        });
        document.querySelector('header.site').appendChild(panel);
        paletteBtn.setAttribute('aria-expanded', 'true');
      };
      paletteBtn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        if (panel) closePanel(); else renderPanel();
      });
      document.addEventListener('click', function (ev) {
        if (panel && !panel.contains(ev.target) && ev.target !== paletteBtn) closePanel();
      });
      document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape' && panel) { closePanel(); paletteBtn.focus(); }
      });
    }

    var menu = document.getElementById('menu-toggle');
    var header = document.querySelector('header.site');
    if (menu && header) {
      menu.addEventListener('click', function () {
        var open = header.classList.toggle('open');
        menu.setAttribute('aria-expanded', open);
        menu.textContent = open ? '✕' : '☰';
      });
    }

    document.querySelectorAll('div.sourceCode').forEach(function (block) {
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Kopieren';
      btn.addEventListener('click', function () {
        var code = block.querySelector('pre').innerText;
        navigator.clipboard.writeText(code).then(function () {
          btn.textContent = 'Kopiert';
          setTimeout(function () { btn.textContent = 'Kopieren'; }, 1500);
        });
      });
      block.appendChild(btn);
    });
  });
})();
