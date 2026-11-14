// Hintergrund: gepixelter Planet unten rechts, Staub, Rauschen. Farben aus den CSS-Variablen des Farbschemas.
(() => {
  const c = document.createElement("canvas"), x = c.getContext("2d"), S = 3;
  c.setAttribute("aria-hidden", "true");
  c.style.cssText = "position:fixed;inset:0;width:100%;height:100%;z-index:-1;image-rendering:pixelated;pointer-events:none";
  document.body.prepend(c);
  const b = document.createElement("canvas"), bx = b.getContext("2d");
  let w, h, img, r1, r2, P = [], last = 0, ft = 0, Rp = 1, col;
  const probe = document.createElement("i");
  const rgb = v => { probe.style.color = v; document.body.append(probe); const m = getComputedStyle(probe).color.match(/[\d.]+/g); probe.remove(); return m.slice(0, 3).map(Number) };
  const mixc = (a, z, t) => a.map((v, i) => v + (z[i] - v) * t);
  const colors = () => {
    const s = getComputedStyle(document.documentElement), g = n => rgb(s.getPropertyValue(n).trim());
    const bg = g("--bg"), ac = g("--accent"), ac2 = g("--accent2"), fg = g("--fg");
    col = { bg, lit: ac, dim: mixc(bg, ac, .3), rim: ac2, dust: fg };
  };
  const spawn = (p, far) => { p.th = Math.PI * (1 + .5 * Math.random()); p.d = far ? Math.random() * h * .7 : 0; p.v = .004 + .014 * Math.random(); p.max = h * (.3 + .4 * Math.random()); p.a = .4 + .6 * Math.random() };
  const mk = () => {
    w = Math.ceil(innerWidth / S); h = Math.ceil(innerHeight / S); c.width = b.width = w; c.height = b.height = h;
    img = x.createImageData(w, h);
    r1 = Float32Array.from({ length: w * h }, Math.random); r2 = Float32Array.from({ length: w * h }, Math.random);
    P = Array.from({ length: w * h / 450 | 0 }, () => { const p = {}; spawn(p, 1); return p });
    c.style.opacity = innerWidth < 900 ? .3 : .55;   // gedämpft, damit der Text lesbar bleibt
  };
  const draw = t => {
    const cx = w * 1.25, cy = h * 2, R0 = Math.hypot(w * .6 - cx, h - cy), R = R0 * (1 + .03 * Math.sin(t * .00005)), L = h * .09, D = img.data;
    Rp = R;
    const { bg, lit, dim, rim, dust } = col;
    for (let y = 0, i = 0; y < h; y++) for (let xx = 0; xx < w; xx++, i++) {
      const e = R - Math.hypot(xx - cx, y - cy), n = r1[i], o = i * 4; let q;
      if (e >= 0) {
        if (e < 1.6) q = rim;
        else {
          const k = Math.min(1, e / (R * .22)), f = Math.min(1, (h - y) / (h * .12));
          q = n < .85 - .55 * k ? mixc(lit, dim, k * .6) : dim;   // Dither: nach innen dunkler
          q = mixc(bg, q, f);                                                 // unten ausblenden
        }
      } else if (r2[i] < Math.exp(e / L) * .25 + .0008) q = mixc(bg, dust, .35 + .65 * n);  // Staub am Rand
      else q = mixc(bg, dust, .03 * n);                                       // Grundrauschen
      D[o] = q[0]; D[o + 1] = q[1]; D[o + 2] = q[2]; D[o + 3] = 255;
    }
    bx.putImageData(img, 0, 0);
  };
  const frame = dt => {
    x.drawImage(b, 0, 0);
    const cx = w * 1.25, cy = h * 2, d = col.dust;
    for (const p of P) {
      p.d += p.v * dt; if (p.d > p.max) spawn(p, 0);
      const q = Rp + p.d, X = cx + q * Math.cos(p.th), Y = cy + q * Math.sin(p.th);
      if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
      x.fillStyle = `rgba(${d[0]},${d[1]},${d[2]},${p.a * (1 - p.d / p.max)})`; x.fillRect(X | 0, Y | 0, 1, 1);
    }
  };
  const loop = t => { if (t - last > 80) { draw(t); last = t } if (t - ft > 33) { frame(t - ft); ft = t } requestAnimationFrame(loop) };
  const still = matchMedia("(prefers-reduced-motion:reduce)").matches;
  const refresh = () => { colors(); draw(0); frame(0) };
  colors(); mk();
  addEventListener("resize", () => { mk(); refresh() });
  new MutationObserver(refresh).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "data-palette"] });
  still ? refresh() : requestAnimationFrame(loop);
})();
