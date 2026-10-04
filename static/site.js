// Hell/Dunkel-Umschalter (Standard Dunkel) und Farbschema-Umschalter (Glass, Nord, Neon, Pastell), beide merken sich die Wahl, Menü-Button für schmale Bildschirme, Kopieren-Button für Code-Blöcke
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

    // Farbschemata: der Knopf schaltet reihum weiter und wählt jeweils den passenden Hell/Dunkel-Modus vor
    var PALETTES = [
      { id: 'glass', name: 'Modern Glass', mode: 'dark' },
      { id: 'nord', name: 'Nord', mode: 'dark' },
      { id: 'neon', name: 'Neon', mode: 'dark' },
      { id: 'pastel', name: 'Pastell', mode: 'light' }
    ];
    var currentPalette = function () {
      for (var i = 0; i < PALETTES.length; i++) {
        if (PALETTES[i].id === (root.dataset.palette || 'glass')) return i;
      }
      return 0;
    };
    var paletteBtn = document.getElementById('palette-toggle');
    if (paletteBtn) {
      var label = function () {
        paletteBtn.title = 'Farbschema: ' + PALETTES[currentPalette()].name + ' (wechseln)';
      };
      label();
      paletteBtn.addEventListener('click', function () {
        var next = PALETTES[(currentPalette() + 1) % PALETTES.length];
        root.dataset.palette = next.id;
        root.dataset.theme = next.mode;
        try {
          localStorage.setItem('palette', next.id);
          localStorage.setItem('theme', next.mode);
        } catch (e) {}
        syncTheme();
        label();
        // kurzer Hinweis mit dem Namen, damit man auch auf dem Handy sieht, welches Schema aktiv ist
        var toast = document.createElement('div');
        toast.className = 'toast';
        toast.setAttribute('role', 'status');
        toast.textContent = next.name;
        document.body.appendChild(toast);
        setTimeout(function () { toast.remove(); }, 1600);
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
