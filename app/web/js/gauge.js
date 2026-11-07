/* gauge.js: SVG drawing of the gauges (270 degree arc, from bottom-left to bottom-right).
   CU.gauge({ rings, center, footer, label }) -> SVG string.
     rings  : [{ r, width, used, color, limit (optional: green up to it, red beyond), markers: [{ v, color, side: "out" | "in" }],
                time (optional): { side: "out" | "in", marks: [{ v, len: 1 | 2 | 3 }], labels: [{ v, text }] } }]
              (the first one is the outermost). Time marks sit outside the outer ring (or inside an inner ring), the
              % graduations (every 10 %) inside the outer ring, so the two scales never mix.
     center : [{ dy, text, size, fill, serif }]  centered text lines (dy relative to the center)
     footer : text under the arc */
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

  const line = (a, b, stroke, w) => `<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}" stroke="${stroke}" stroke-width="${w}"/>`;

  /* % graduations, every 10 %, pointing inwards from radius r */
  function ticks(r) {
    let s = "";
    for (let v = 0; v <= 100; v += 10) {
      const major = v % 50 === 0;
      s += line(pt(v, r), pt(v, r - (major ? 7 : 4)), "var(--tick)", major ? 1.4 : 0.9);
    }
    return s;
  }

  /* time graduations: len 1 / 2 / 3 = short / medium / long, from the edge of the ring outwards (or inwards) */
  function timeTicks(ring) {
    const tm = ring.time;
    if (!tm) return "";
    const dir = tm.side === "in" ? -1 : 1, edge = ring.r + dir * (ring.width / 2 + 3);
    let s = "";
    for (const m of tm.marks || []) {
      if (m.v < 0 || m.v > 100) continue;
      s += line(pt(m.v, edge), pt(m.v, edge + dir * (2 + 3 * m.len)), m.len === 3 ? "var(--muted)" : "var(--tick)", m.len === 3 ? 1.6 : 1);
    }
    const lr = edge + dir * 19;
    for (const l of tm.labels || []) {
      if (l.v < 0 || l.v > 100) continue;
      const [x, y] = pt(l.v, lr);
      s += `<text x="${f(x)}" y="${f(y + 3.5)}" text-anchor="middle" font-size="11" fill="var(--muted)" class="tlabel">${l.text}</text>`;
    }
    return s;
  }

  // Marker: a tick across the ring + a triangle outside (out) or inside (in) pointing at the ring.
  function marker(m, ring) {
    if (m.v == null || !isFinite(m.v) || m.v > 100) return "";
    const v = clamp(m.v), half = ring.width / 2;
    const ang = (START + SWEEP * v / 100) * Math.PI / 180, px = -Math.sin(ang), py = Math.cos(ang);
    const [a, b] = [pt(v, ring.r - half - 4), pt(v, ring.r + half + 4)];
    const dir = m.side === "in" ? -1 : 1;
    const tip = pt(v, ring.r + dir * (half + 5)), base = pt(v, ring.r + dir * (half + 16));
    return `<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}" stroke="var(--card)" stroke-width="7" stroke-linecap="round"/>`
      + `<line x1="${f(a[0])}" y1="${f(a[1])}" x2="${f(b[0])}" y2="${f(b[1])}" stroke="${m.color}" stroke-width="3.2" stroke-linecap="round"/>`
      + `<polygon points="${f(tip[0])},${f(tip[1])} ${f(base[0] + 6 * px)},${f(base[1] + 6 * py)} ${f(base[0] - 6 * px)},${f(base[1] - 6 * py)}" fill="${m.color}"/>`;
  }

  let uid = 0;
  /* Speedometer zones on the unfilled track: green up to `limit`, red beyond it. Masked by the track shape so the
     ends stay round. */
  function zones(ring) {
    const lim = ring.limit;
    if (lim == null || !isFinite(lim)) return "";
    const id = "zm" + (++uid), L = clamp(lim);
    const track = `<path d="${arc(0, 100, ring.r)}" fill="none" stroke="#fff" stroke-width="${ring.width}" stroke-linecap="round"/>`;
    // red everywhere (round caps cover the ring end), then green over it up to the limit (+ a dot for the round start)
    const [x0, y0] = pt(0, ring.r);
    let s = `<mask id="${id}">${track}</mask><g mask="url(#${id})" opacity=".34">`;
    s += `<path d="${arc(0, 100, ring.r)}" fill="none" stroke="var(--bad)" stroke-width="${ring.width + 2}" stroke-linecap="round"/>`;
    if (L >= 100) s += `<path d="${arc(0, 100, ring.r)}" fill="none" stroke="var(--ok)" stroke-width="${ring.width + 2}" stroke-linecap="round"/>`;
    else if (L > 0) s += `<path d="${arc(0, L, ring.r)}" fill="none" stroke="var(--ok)" stroke-width="${ring.width + 2}"/>`
      + `<circle cx="${f(x0)}" cy="${f(y0)}" r="${ring.width / 2 + 1}" fill="var(--ok)"/>`;
    return s + `</g>`;
  }

  /* time graduations of a window [end - length, end] (ms). 5 hours: a mark every 15 min, hours labelled 1 h..5 h.
     A week: a long mark at each local midnight, the day's initial in the middle of each day (when there is room). */
  CU.gaugeTime = function (kind, end, labels = true) {
    if (!end) return null;
    const H = 3600e3, len = kind === "five" ? 5 * H : 7 * 24 * H, start = end - len, v = ms => (ms - start) / len * 100;
    const marks = [], lbl = [];
    if (kind === "five") {
      for (let k = 0; k <= 20; k++) marks.push({ v: k * 5, len: k % 4 === 0 ? 3 : k % 2 === 0 ? 2 : 1 });
      if (labels) for (let h = 1; h <= 5; h++) lbl.push({ v: h * 20, text: h + " h" });
      return { marks, labels: lbl };
    }
    const loc = CU.lang === "fr" ? "fr-FR" : "en-GB", d = new Date(start);
    d.setHours(0, 0, 0, 0);
    for (; d.getTime() < end; d.setDate(d.getDate() + 1)) {
      const a = Math.max(d.getTime(), start), next = new Date(d); next.setDate(next.getDate() + 1);
      const b = Math.min(next.getTime(), end);
      if (d.getTime() > start) marks.push({ v: v(d.getTime()), len: 3 });
      if (labels && (b - a) / len > 0.06) {
        const day = d.toLocaleDateString(loc, { weekday: "narrow" });
        lbl.push({ v: (v(a) + v(b)) / 2, text: day.charAt(0).toUpperCase() + day.slice(1) });
      }
    }
    return { marks, labels: lbl };
  };

  CU.gauge = function ({ rings, center = [], footer = "", label = "" }) {
    const outer = rings[0];
    let s = `<svg class="gauge" viewBox="-16 -16 352 316" role="img" aria-label="${label}">`;
    s += ticks(outer.r - outer.width / 2 - 3);
    for (const ring of rings) s += timeTicks(ring);
    for (const ring of rings) {
      s += `<path d="${arc(0, 100, ring.r)}" fill="none" stroke="var(--track)" stroke-width="${ring.width}" stroke-linecap="round"/>`;
      s += zones(ring);
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
