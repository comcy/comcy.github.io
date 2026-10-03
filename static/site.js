// Hell/Dunkel-Umschalter (Standard Dunkel) und Farbschema-Umschalter (Glass/Nord), beide merken sich die Wahl, Menü-Button für schmale Bildschirme, Kopieren-Button für Code-Blöcke
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
    if (toggle) {
      var sync = function () { toggle.textContent = isDark() ? '☀️' : '🌙'; };
      sync();
      toggle.addEventListener('click', function () {
        root.dataset.theme = isDark() ? 'light' : 'dark';
        try { localStorage.setItem('theme', root.dataset.theme); } catch (e) {}
        sync();
      });
    }

    // Farbschema: Glass (Standard) <-> Nord
    var paletteBtn = document.getElementById('palette-toggle');
    if (paletteBtn) {
      var label = function () {
        paletteBtn.title = 'Farbschema: ' + (root.dataset.palette === 'nord' ? 'Nord' : 'Glass') + ' (wechseln)';
      };
      label();
      paletteBtn.addEventListener('click', function () {
        root.dataset.palette = root.dataset.palette === 'nord' ? 'glass' : 'nord';
        try { localStorage.setItem('palette', root.dataset.palette); } catch (e) {}
        label();
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
