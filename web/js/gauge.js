/* gauge.js : dessin SVG des compteurs (arc de 270°, de bas-gauche a bas-droite).
   CU.gauge({ rings, center, footer }) -> chaine SVG.
     rings  : [{ r, width, used, color, markers: [{ v, color, side: "out" | "in" }] }]  (le 1er = le plus a l'exterieur)
     center : [{ dy, text, size, fill, serif }]  lignes de texte centrees (dy relatif au centre)
     footer : texte sous l'arc */
window.CU = window.CU || {};

(function (CU) {
  const CX = 160, CY = 158, START = 135, SWEEP = 270;
  const clamp = v => Math.min(100, Math.max(0, v));
  const f = n => n.toFixed(2);

  function pt(v, r) {
    const a = (START + SWEEP * clamp(v) / 100) * Math.PI / 180;
    return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
  }
  function arc(v0, v1, r) {
    const [x0, y0] = pt(v0, r), [x1, y1] = pt(v1, r);
    const large = SWEEP * (v1 - v0) / 100 > 180 ? 1 : 0;
    return `M${f(x0)} ${f(y0)} A${r} ${r} 0 ${large} 1 ${f(x1)} ${f(y1)}`;
  }

  function ticks(r) {
    let s = "";
    for (let v = 0; v <= 100; v += 10) {
      const major = v % 50 === 0, [a, b] = [pt(v, r), pt(v, r + (major ? 9 : 5))];
      s += `<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}" stroke="var(--tick)" stroke-width="${major ? 1.6 : 1}"/>`;
    }
    return s;
  }

  // Repere : trait a travers l'anneau + triangle a l'exterieur (out) ou a l'interieur (in), pointant vers l'anneau.
  function marker(m, ring) {
    if (m.v == null || !isFinite(m.v)) return "";
    const v = clamp(m.v), half = ring.width / 2;
    const ang = (START + SWEEP * v / 100) * Math.PI / 180, px = -Math.sin(ang), py = Math.cos(ang);
    const [a, b] = [pt(v, ring.r - half - 4), pt(v, ring.r + half + 4)];
    const dir = m.side === "in" ? -1 : 1;
    const tip = pt(v, ring.r + dir * (half + 5)), base = pt(v, ring.r + dir * (half + 16));
    return `<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}" stroke="var(--card)" stroke-width="7" stroke-linecap="round"/>`
      + `<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}" stroke="${m.color}" stroke-width="3.2" stroke-linecap="round"/>`
      + `<polygon points="${f(tip[0])},${f(tip[1])} ${f(base[0] + 6 * px)},${f(base[1] + 6 * py)} ${f(base[0] - 6 * px)},${f(base[1] - 6 * py)}" fill="${m.color}"/>`;
  }

  CU.gauge = function ({ rings, center = [], footer = "", label = "" }) {
    const outer = rings[0];
    let s = `<svg class="gauge" viewBox="0 0 320 290" role="img" aria-label="${label}">`;
    s += ticks(outer.r + outer.width / 2 + 5);
    for (const ring of rings) {
      s += `<path d="${arc(0, 100, ring.r)}" fill="none" stroke="var(--track)" stroke-width="${ring.width}" stroke-linecap="round"/>`;
      if (ring.used > 0.3)
        s += `<path d="${arc(0, clamp(ring.used), ring.r)}" fill="none" stroke="${ring.color}" stroke-width="${ring.width}" stroke-linecap="round"/>`;
    }
    for (const ring of rings) for (const m of ring.markers || []) s += marker(m, ring);
    for (const t of center) {
      s += `<text x="${CX}" y="${CY + t.dy}" text-anchor="middle" font-size="${t.size}" fill="${t.fill || "var(--text)"}"`
        + `${t.serif ? ' font-family="var(--serif)"' : ""}${t.spacing ? ` letter-spacing="${t.spacing}"` : ""}>${t.text}</text>`;
    }
    if (footer) s += `<text x="${CX}" y="${CY + 122}" text-anchor="middle" font-size="13" fill="var(--text)">${footer}</text>`;
    return s + `</svg>`;
  };
})(window.CU);
