// Dark-Mode-Umschalter (merkt sich die Wahl) und Kopieren-Button für Code-Blöcke
(function () {
  var root = document.documentElement;
  try { var saved = localStorage.getItem('theme'); if (saved) root.dataset.theme = saved; } catch (e) {}

  function isDark() {
    return root.dataset.theme
      ? root.dataset.theme === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

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
