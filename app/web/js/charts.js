/* charts.js: the history charts (plain SVG, no dependency).
     1. usage per hour, in % of the 5-hour window, against the pace you can afford;
     2. evolution of the 5h -> week ratio (how many % of the week one full 5-hour window costs), day by day;
     3. tokens by type (fresh input, cache write, cache read, output) and their relative cost, from the local transcripts.
   Each chart has a range: preset buttons, and (charts 1 and 2) a small overview below it, like a market chart:
   drag the window to move it, drag its edges to zoom, click outside to jump there. The range is kept in
   localStorage. While a drag is going on, CU.dragging is true and the page does not re-render.
   Compactness level (UI-5): below 8 a chart is a small always-open card (no range buttons, no overview, lighter
   axes); 8 = the full chart; the tokens panel only shows its summary at 7, its tables from 8 and the per-day one at 9. */
window.CU = window.CU || {};

(function (CU) {
  const t = (k, v) => CU.t(k, v);
  const H = 3600e3, DAY = 24 * H;
  const W = 640, HT = 210, L = 38, R = 12, T = 12, B = 26, MH = 46;      // viewBox, margins, overview height
  const f = n => n.toFixed(1);
  const loc = () => CU.lang === "fr" ? "fr-FR" : "en-GB";
  const dm = ms => new Date(ms).toLocaleDateString(loc(), { day: "2-digit", month: "2-digit" });
  const dmh = ms => new Date(ms).toLocaleString(loc(), { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
  const niceStep = max => { const raw = max / 4, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; };
  const k = v => v == null ? "—" : v >= 1e6 ? CU.fmt.num(v / 1e6, 1) + " M" : v >= 1e3 ? CU.fmt.num(v / 1e3, v >= 1e5 ? 0 : 1) + " k" : String(v);
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

  /* ---------- range state (per chart): span in ms (0 = everything), end in ms (null = follows the present) ---------- */
  const STORE = "cu.ranges";
  let RS = {};
  try { RS = JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { /* storage unavailable */ }
  const save = () => { try { localStorage.setItem(STORE, JSON.stringify(RS)); } catch (e) { /* ignore */ } };
  const state = def => RS[def.key] || (RS[def.key] = { span: def.span, end: null });
  function win(s, lo, hi, minSpan) {
    const span = Math.min(s.span ? Math.max(s.span, minSpan) : hi - lo, hi - lo);
    const b = s.end == null ? hi : clamp(s.end, lo + span, hi);
    return [b - span, b];
  }

  /* ---------- 1. usage per hour ---------- */
  const bucketHours = n => n <= 48 ? 1 : n <= 96 ? 3 : n <= 240 ? 6 : n <= 24 * 400 ? 24 : 168;   // never more than ~400 bars
  function bucketStart(ms, bh) {
    const d = new Date(ms);
    if (bh >= 24) d.setHours(0, 0, 0, 0); else d.setHours(Math.floor(d.getHours() / bh) * bh, 0, 0, 0);
    return d.getTime();
  }
  function nextStart(s, bh) {
    const n = bucketStart(s + (bh >= 24 ? bh * H + 6 * H : bh * H + H / 2), bh);
    return n > s ? n : s + bh * H;                                     // DST: never loop
  }
  const hourlyDomain = m => {
    const hi = Math.ceil(Date.now() / H) * H, first = m.firstAt ? Date.parse(m.firstAt) : hi - DAY;
    return [Math.min(Math.floor(first / H) * H, hi - DAY), hi];
  };
  function hourlyBuckets(m, a, b) {
    const bh = bucketHours((b - a) / H), out = [];
    for (let s = bucketStart(a, bh); s < b && out.length < 1200; ) { const e = nextStart(s, bh); out.push({ t: s, e, v: 0 }); s = e; }
    let j = 0;                                                         // hourly5 is sorted by time: one pass
    for (const [iso, v] of m.hourly5) {
      const ts = Date.parse(iso);
      while (j < out.length && ts >= out[j].e) j++;
      if (j < out.length && ts >= out[j].t) out[j].v += v;
    }
    return { bh, bars: out };
  }
  function hourlyPlot(m, a, b, s, lvl = 9) {
    const lite = lvl < 8;
    const { bh, bars } = hourlyBuckets(m, a, b), rate = bh <= 6 ? m.five.paceRate * bh : null;
    const peak = Math.max(...bars.map(d => d.v), rate || 0, 1), step = niceStep(peak * 1.1), max = Math.ceil(peak * 1.1 / step) * step;
    const y = v => HT - B - (HT - B - T) * v / max, bw = (W - L - R) / bars.length, stride = Math.max(1, Math.ceil(bars.length / (lite ? 5 : 9)));
    let grid = "";
    for (let v = 0; v <= max + 1e-9; v += step)
      grid += `<line x1="${L}" x2="${W - R}" y1="${f(y(v))}" y2="${f(y(v))}" stroke="var(--line)"/>`
        + (lite ? "" : `<text x="${L - 6}" y="${f(y(v) + 4)}" text-anchor="end" class="ax">${Math.round(v * 10) / 10}</text>`);
    const body = bars.map((d, i) => {
      const x = L + i * bw, hr = new Date(d.t).getHours(), over = rate != null && d.v > rate;
      const show = bh === 1 || bh >= 24 ? i % stride === 0 : hr === 0;             // 3 h / 6 h bars: label each midnight
      const lbl = !show ? "" : `<text x="${f(x + bw / 2)}" y="${HT - 8}" text-anchor="middle" class="ax">${bh < 24 && hr !== 0 ? hr + " h" : dm(d.t)}</text>`;
      return `<rect x="${f(x + 1.5)}" y="${f(y(d.v))}" width="${f(Math.max(bw - 3, 1))}" height="${f(Math.max(HT - B - y(d.v), 0))}" rx="2" fill="${over ? "var(--clay)" : "var(--blue)"}">`
        + `<title>${bh < 24 ? dmh(d.t) : dm(d.t)} · ${CU.fmt.pct(d.v, 1)}</title></rect>${lbl}`;
    }).join("");
    const line = rate == null ? "" : `<line x1="${L}" x2="${W - R}" y1="${f(y(rate))}" y2="${f(y(rate))}" stroke="var(--clay-ink)" stroke-width="1.5" stroke-dasharray="5 4"/>`;
    return { svg: grid + body + line, bh, total: bars.reduce((s, d) => s + d.v, 0) };
  }
  function hourlyMini(m, lo, hi) {                                      // <= 160 bars over the whole history
    const bin = Math.max(H, Math.ceil((hi - lo) / 160 / H) * H), n = Math.ceil((hi - lo) / bin), v = new Array(n).fill(0);
    for (const [iso, x] of m.hourly5) { const i = Math.floor((Date.parse(iso) - lo) / bin); if (i >= 0 && i < n) v[i] += x; }
    return { kind: "bars", v };
  }

  /* ---------- 2. ratio over time ---------- */
  const ratioDays = m => m.ratioDaily.map(d => Object.assign({ ms: Date.parse(d.day + "T00:00:00Z") + DAY / 2 }, d));
  const ratioDomain = m => { const d = ratioDays(m); return [d[0].ms - DAY / 2, d[d.length - 1].ms + DAY / 2]; };
  function ratioPlot(m, a, b, s, lvl = 9) {
    const lite = lvl < 8;
    const days = ratioDays(m).filter(d => d.ms >= a && d.ms <= b);
    const vals = days.flatMap(d => [d.ratio, d.cum]).filter(v => v != null).concat(m.ratio);
    const lo = Math.floor(Math.min(...vals) - 1), hi = Math.ceil(Math.max(...vals) + 1), step = niceStep(hi - lo);
    const y = v => HT - B - (HT - B - T) * (v - lo) / (hi - lo), x = ms => L + (W - L - R) * (ms - a) / (b - a);
    let grid = "";
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step)
      grid += `<line x1="${L}" x2="${W - R}" y1="${f(y(v))}" y2="${f(y(v))}" stroke="var(--line)"/>`
        + (lite ? "" : `<text x="${L - 6}" y="${f(y(v) + 4)}" text-anchor="end" class="ax">${Math.round(v * 10) / 10}</text>`);
    const path = days.filter(d => d.cum != null).map((d, i) => (i ? "L" : "M") + f(x(d.ms)) + " " + f(y(d.cum))).join(" ");
    const dots = days.map(d => d.ratio == null ? "" :
      `<circle cx="${f(x(d.ms))}" cy="${f(y(d.ratio))}" r="3.5" fill="var(--blue)"><title>${d.day} · ${CU.fmt.pct(d.ratio, 1)} (${t("chart.ratio.tip", { a: CU.fmt.num(d.d5), b: CU.fmt.num(d.d7) })})</title></circle>`).join("");
    const stride = Math.max(1, Math.ceil(days.length / (lite ? 4 : 8)));
    const xl = days.map((d, i) => i % stride ? "" : `<text x="${f(x(d.ms))}" y="${HT - 8}" text-anchor="middle" class="ax">${dm(d.ms)}</text>`).join("");
    const cur = `<line x1="${L}" x2="${W - R}" y1="${f(y(m.ratio))}" y2="${f(y(m.ratio))}" stroke="var(--clay-ink)" stroke-width="1" stroke-dasharray="2 4"/>`;
    return { svg: grid + cur + (path ? `<path d="${path}" fill="none" stroke="var(--clay)" stroke-width="2.5" stroke-linejoin="round"/>` : "") + dots + xl };
  }
  function ratioMini(m, lo, hi) {
    const pts = ratioDays(m).filter(d => d.cum != null);
    if (!pts.length) return { kind: "line", p: [] };
    const vs = pts.map(d => d.cum), mn = Math.min(...vs), mx = Math.max(...vs, mn + 0.5);
    return { kind: "line", p: pts.map(d => [(d.ms - lo) / (hi - lo), 1 - (d.cum - mn) / (mx - mn)]) };
  }

  /* ---------- 3. tokens by type, and what each type costs ---------- */
  /* Relative price of one token of each type, in "plain input tokens" (Anthropic's public price ratios, the same for
     every model; only the base price changes): cache read 0.1x, cache write 1.25x (5 min) or 2x (1 h), output 5x.
     It is an API-price proxy: how the quota itself weights each type is not published. */
  const PRICE = { input: 1, write5: 1.25, write1: 2, read: 0.1, output: 5 };
  function tokenTypes(x) {                     // x: { input, output, cache_read, cache_write, cache_write_1h }
    const w1 = Math.min(x.cache_write_1h || 0, x.cache_write), w5 = x.cache_write - w1;
    return [
      { id: "input", n: x.input, cost: x.input * PRICE.input, color: "var(--blue)" },
      { id: "write", n: x.cache_write, cost: w5 * PRICE.write5 + w1 * PRICE.write1, color: "var(--violet)" },
      { id: "read", n: x.cache_read, cost: x.cache_read * PRICE.read, color: "var(--sage)" },
      { id: "output", n: x.output, cost: x.output * PRICE.output, color: "var(--clay)" },
    ];
  }
  const sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
  const pc = (v, tot) => tot > 0 ? CU.fmt.pct(100 * v / tot, v / tot < 0.1 ? 1 : 0) : "—";
  const times = v => "× " + CU.fmt.num(v, v < 1 ? 1 : v % 1 ? 2 : 0);
  const stack = (types, key, tot, label) => `<div class="share">${types.map(x => x[key] > 0 ?
    `<span style="flex-grow:${x[key]};background:${x.color}" title="${t("chart.tokens.t." + x.id)} · ${pc(x[key], tot)} ${label}"></span>` : "").join("")}</div>`;

  function tokensPlot(m, a, b, span, lvl = 9) {
    const cut = span ? new Date(Date.now() - (span / DAY - 1) * DAY).toISOString().slice(0, 10) : "";
    const days = m.tokens.days.filter(d => d.day >= cut).reverse();
    const tot = { input: 0, output: 0, cache_read: 0, cache_write: 0, cache_write_1h: 0 };
    let d7 = 0;
    for (const d of days) { for (const q in tot) tot[q] += d[q] || 0; d7 += d.d7 || 0; }
    const types = tokenTypes(tot), all = sum(types, x => x.n), cost = sum(types, x => x.cost);
    const noCache = (tot.input + tot.cache_read + tot.cache_write) * PRICE.input + tot.output * PRICE.output;
    const saving = noCache > 0 ? 100 * (1 - cost / noCache) : null;
        const rows = types.map(x => `<tr><th><span class="dot" style="color:${x.color}"></span>${t("chart.tokens.t." + x.id)}<small>${t("chart.tokens.d." + x.id)}</small></th>`
      + `<td>${k(x.n)}</td><td>${pc(x.n, all)}</td><td>${x.n > 0 ? times(x.cost / x.n) : "—"}</td><td><b>${pc(x.cost, cost)}</b></td></tr>`).join("");
    const maxCost = Math.max(...days.map(d => sum(tokenTypes(d), x => x.cost)), 1);
    const drows = days.map(d => {
      const ty = tokenTypes(d), n = sum(ty, x => x.n), c = sum(ty, x => x.cost);
      const bar = ty.map(x => `<span style="width:${(x.cost / maxCost * 100).toFixed(1)}%;background:${x.color}" title="${t("chart.tokens.t." + x.id)} · ${k(x.n)} · ${pc(x.cost, c)} ${t("chart.tokens.ofcost")}"></span>`).join("");
      return `<tr><th>${dm(Date.parse(d.day + "T12:00:00Z"))}</th><td><span class="tbar">${bar}</span></td><td>${k(n)}</td>`
        + `<td>${pc(d.cache_read, n)}</td><td>${k(c)}</td><td>${d.d7 ? CU.fmt.pct(d.d7, 0) : "—"}</td><td>${d.d7 ? k(c / d.d7) : "—"}</td></tr>`;
    }).join("");
    const statsHtml = `
        <div class="stats">
          <div><b>${k(all)}</b><span>${t("chart.tokens.s.total")}</span></div>
          <div><b>${pc(tot.cache_read, all)}</b><span>${t("chart.tokens.s.cached", { n: k(tot.cache_read) })}</span></div>
          <div><b>${saving == null ? "—" : "−" + CU.fmt.pct(saving, 0)}</b><span>${t("chart.tokens.s.saving")}</span></div>
        </div>`;
    if (lvl < 8) return { svg: statsHtml };
    const tables = `
        <h3 class="sub">${t("chart.tokens.h.tokens")}</h3>${stack(types, "n", all, t("chart.tokens.oftokens"))}
        <h3 class="sub">${t("chart.tokens.h.cost")}</h3>${stack(types, "cost", cost, t("chart.tokens.ofcost"))}
        <table class="eqs tokens types"><tr><th></th><td>${t("chart.tokens.c.tokens")}</td><td>${t("chart.tokens.c.pctt")}</td><td>${t("chart.tokens.c.price")}</td><td>${t("chart.tokens.c.pctc")}</td></tr>${rows}</table>
        <p class="note" data-note="tokens">${t("chart.tokens.hitnote")}</p>`;
    if (lvl < 9) return { svg: statsHtml + tables };
    return { svg: statsHtml + tables + `
        <h3 class="sub">${t("chart.tokens.byday")}</h3>
        <div class="hscroll"><table class="eqs tokens"><tr><th></th><td></td><td>${t("chart.tokens.c.tokens")}</td><td>${t("chart.tokens.c.cache")}</td><td>${t("chart.tokens.c.cost")}</td><td>${t("chart.tokens.c.week")}</td><td>${t("chart.tokens.c.costpct")}</td></tr>${drows}</table></div>` };
  }

  /* ---------- the chart definitions ---------- */
  const P = (key, ms) => [key, ms];
  const DEFS = {
    hourly: {
      key: "hourly", span: DAY, minSpan: 6 * H, presets: [P("24h", DAY), P("3d", 3 * DAY), P("7d", 7 * DAY), P("14d", 14 * DAY), P("all", 0)],
      ready: m => m.hourly5 && m.hourly5.length, domain: hourlyDomain, mini: hourlyMini, plot: hourlyPlot,
      label: (r, a, b) => `${dmh(a)} → ${dmh(b)} · ${r.bh < 24 ? t("chart.bucket.h", { n: r.bh }) : r.bh >= 168 ? t("chart.bucket.w") : t("chart.bucket.d")} · ${t("chart.hourly.total", { n: CU.fmt.pct(r.total) })}`,
      hint: (m, r) => t("chart.hourly.total", { n: CU.fmt.pct(r.total) }),
      note: m => t("chart.hourly.note", { rate: CU.fmt.pct(m.five.paceRate, 1) }),
      legend: () => "", title: "chart.hourly.title",
    },
    ratio: {
      key: "ratio", span: 0, minSpan: 3 * DAY, presets: [P("7d", 7 * DAY), P("14d", 14 * DAY), P("all", 0)],
      ready: m => m.ratioDaily.length >= 2, domain: ratioDomain, mini: ratioMini, plot: ratioPlot,
      label: (r, a, b) => `${dm(a)} → ${dm(b)}`,
      hint: m => t("chart.ratio.now", { n: CU.fmt.pct(m.ratio, 1) }), note: () => t("chart.ratio.note"),
      legend: () => `<ul class="legend chart-legend"><li><span class="dot" style="color:var(--blue)"></span><span class="lbl">${t("chart.ratio.day")}</span></li>`
        + `<li><span class="dot" style="color:var(--clay)"></span><span class="lbl">${t("chart.ratio.cum")}</span></li></ul>`,
      title: "chart.ratio.title",
    },
    tokens: {
      key: "tokens", span: 7 * DAY, minSpan: DAY, presets: [P("7d", 7 * DAY), P("14d", 14 * DAY), P("30d", 30 * DAY), P("all", 0)],
      ready: m => m.tokens && m.tokens.days.length, noMini: true, title: "chart.tokens.title",
      domain: () => { const hi = Date.now(); return [hi - DAY, hi]; },
      plot: (m, a, b, s, lvl) => tokensPlot(m, a, b, s.span, lvl),
      label: () => "", hint: m => { const w = m.tokens.week, all = w.input + w.output + w.cache_read + w.cache_write;
        return t("chart.tokens.hit", { n: pc(w.cache_read, all) }); }, note: () => t("chart.tokens.note"), legend: () => "",
    },
  };

  /* what a chart shows for the current range */
  function parts(def, m, lvl = 9) {
    const s = state(def), [lo, hi] = def.domain(m), [a, b] = win(s, lo, hi, def.minSpan), r = def.plot(m, a, b, s, lvl);
    return { s, lo, hi, a, b, r, label: def.label(r, a, b) };
  }
  const pressed = (def, p, span, lo, hi, a, b) => def.key === "tokens" ? p === span : (p ? Math.abs((b - a) - Math.min(p, hi - lo)) < 1000 : b - a >= hi - lo - 1000);

  /* overview below the chart: the whole history, the visible window highlighted */
  const mx = (ms, lo, hi) => L + (W - L - R) * (ms - lo) / (hi - lo);
  function miniBody(def, m, lo, hi) {
    const d = def.mini(m, lo, hi), w = W - L - R;
    if (d.kind === "bars") {
      const mx_ = Math.max(...d.v, 1), bw = w / d.v.length;
      return d.v.map((v, i) => v > 0 ? `<rect class="mb" x="${f(L + i * bw)}" y="${f(MH - 4 - (MH - 8) * v / mx_)}" width="${f(Math.max(bw - 0.4, 0.6))}" height="${f((MH - 8) * v / mx_)}"/>` : "").join("");
    }
    const path = d.p.map((q, i) => (i ? "L" : "M") + f(L + w * q[0]) + " " + f(4 + (MH - 8) * q[1])).join(" ");
    return path ? `<path class="ml" d="${path}"/>` : "";
  }
  function place(svg, lo, hi, a, b) {
    const xa = mx(a, lo, hi), xb = mx(b, lo, hi), set = (c, o) => { const e = svg.querySelector("." + c); for (const q in o) e.setAttribute(q, o[q]); };
    set("dl", { x: L, width: Math.max(xa - L, 0) });
    set("dr", { x: xb, width: Math.max(W - R - xb, 0) });
    set("win", { x: f(xa), width: f(Math.max(xb - xa, 1)) });
    set("hl", { x: f(xa - 3) });
    set("hr", { x: f(xb - 3) });
  }

  const qbtn = key => `<button type="button" class="qbtn" data-note-for="${key}" aria-label="${t("notes.one")}" title="${t("notes.one")}">?</button>`;
  function card(def, m, lvl) {
    const p = parts(def, m, lvl);
    if (lvl < 8) {                                                      // small version: always open, no range controls
      const plot = def.key === "tokens" ? `<div class="plot">${p.r.svg}</div>` : `<svg class="plot" viewBox="0 0 ${W} ${HT}" role="img" aria-label="${t(def.title)}">${p.r.svg}</svg>`;
      return `
      <section class="card chart lite" data-key="${def.key}" data-level="${lvl}">
        <div class="card-head"><h2>${t(def.title)}</h2><span class="hint">${def.hint(m, p.r)}</span>${qbtn(def.key)}</div>
        ${plot}${def.key === "tokens" ? "" : def.legend()}
        <p class="note" data-note="${def.key}">${def.note(m)}</p>
      </section>`;
    }
    const buttons = def.presets.map(([key, ms]) =>
      `<button type="button" data-span="${ms}" aria-pressed="${pressed(def, ms, p.s.span, p.lo, p.hi, p.a, p.b)}">${t("range." + key)}</button>`).join("");
    const mini = def.noMini ? "" : `
        <svg class="mini" viewBox="0 0 ${W} ${MH}" tabindex="0" role="slider" aria-orientation="horizontal" aria-valuemin="0" aria-valuemax="100"
             aria-valuenow="50" aria-valuetext="${p.label}" aria-label="${t("chart.range.aria")}">${miniBody(def, m, p.lo, p.hi)}
          <rect class="dim dl" y="0" height="${MH}"/><rect class="dim dr" y="0" height="${MH}"/>
          <rect class="win" y="0.5" height="${MH - 1}" rx="3"/><rect class="hdl hl" y="${MH / 2 - 10}" width="6" height="20" rx="2"/><rect class="hdl hr" y="${MH / 2 - 10}" width="6" height="20" rx="2"/>
        </svg>`;
    const html = `
      <details class="card chart" data-key="${def.key}" data-level="${lvl}">
        <summary><h2>${t(def.title)}</h2><span class="hint">${def.hint(m, p.r)}</span>${qbtn(def.key)}</summary>
        <div class="presets seg" role="group" aria-label="${t(def.title)}">${buttons}</div>
        ${def.key === "tokens" ? `<div class="plot">${p.r.svg}</div>` : `<svg class="plot" viewBox="0 0 ${W} ${HT}" role="img" aria-label="${t(def.title)}">${p.r.svg}</svg>`}
        ${mini}
        <p class="rlabel">${p.label}${def.noMini ? "" : ` <span class="note" data-note="${def.key}">${t("chart.range.hint")}</span>`}</p>
        ${def.legend()}
        <p class="note" data-note="${def.key}">${def.note(m)}</p>
      </details>`;
    return html;
  }

  /* after a change of range: redraw the plot, the label, the window and the buttons, never the overview itself */
  function refresh(el) {
    const def = DEFS[el.dataset.key], m = CU.lastModel;
    if (!def || !m) return;
    const p = parts(def, m, +el.dataset.level || 9), plot = el.querySelector(".plot");
    plot.innerHTML = p.r.svg;
    const rl = el.querySelector(".rlabel");
    if (rl && rl.firstChild && rl.firstChild.nodeType === 3) rl.firstChild.textContent = p.label + " ";
    el.querySelector("summary .hint").innerHTML = def.hint(m, p.r);
    el.querySelectorAll(".presets button").forEach(b => b.setAttribute("aria-pressed", String(pressed(def, +b.dataset.span, p.s.span, p.lo, p.hi, p.a, p.b))));
    const svg = el.querySelector("svg.mini");
    if (svg) { place(svg, p.lo, p.hi, p.a, p.b); aria(svg, p); }
  }
  function aria(svg, p) {                                              // what a screen reader says about the window
    svg.setAttribute("aria-valuenow", String(Math.round(((p.a + p.b) / 2 - p.lo) / (p.hi - p.lo) * 100)));
    svg.setAttribute("aria-valuetext", p.label);
  }

  CU.charts = function (m, keys, lvl = 9) {                             // keys: which charts (default: all); lvl: compactness level
    CU.lastModel = m;
    return Object.values(DEFS).filter(d => (!keys || keys.includes(d.key)) && d.ready(m)).map(d => card(d, m, lvl)).join("");
  };
  CU.charts.internals = { hourlyBuckets, bucketHours };                 // for the tests (test_audit.py)
  CU.chartsAfterRender = function (root) {                              // window rectangles need the overview to exist
    const m = CU.lastModel;
    root.querySelectorAll(".chart").forEach(el => {
      const def = DEFS[el.dataset.key], svg = el.querySelector("svg.mini");
      if (def && svg && m) { const p = parts(def, m, +el.dataset.level || 9); place(svg, p.lo, p.hi, p.a, p.b); aria(svg, p); }
    });
  };

  /* The page is rebuilt every 10 s: keep the keyboard focus on the same control (mini view, range button, title). */
  CU.captureFocus = function (root) {
    const a = document.activeElement, el = a && a.closest && root.contains(a) ? a.closest(".chart") : null;
    if (!el) return () => {};
    const key = el.dataset.key;
    let sel = null;
    if (a.matches("svg.mini")) sel = "svg.mini";
    else if (a.matches("summary")) sel = "summary";
    else if (a.matches(".presets button")) sel = `.presets button:nth-child(${[...a.parentNode.children].indexOf(a) + 1})`;
    return () => {
      const n = sel && root.querySelector(`.chart[data-key="${key}"] ${sel}`);
      if (n) n.focus({ preventScroll: true });
    };
  };

  /* keyboard on the overview: arrows move the window, up/down (or + / -) zoom, Home / End jump to the start / the present */
  document.addEventListener("keydown", e => {
    const svg = e.target.closest && e.target.closest("svg.mini");
    if (!svg || !CU.lastModel) return;
    const el = svg.closest(".chart"), def = DEFS[el.dataset.key], s = state(def);
    const [lo, hi] = def.domain(CU.lastModel), [a, b] = win(s, lo, hi, def.minSpan);
    const span = b - a, step = Math.max(def.key === "hourly" ? H : DAY, span / 10), c = (a + b) / 2;
    let na = a, nb = b;
    switch (e.key) {
      case "ArrowLeft": na -= step; nb -= step; break;
      case "ArrowRight": na += step; nb += step; break;
      case "ArrowUp": case "+": { const sp = Math.max(def.minSpan, span * 0.7); na = c - sp / 2; nb = c + sp / 2; break; }
      case "ArrowDown": case "-": { const sp = Math.min(hi - lo, span / 0.7); na = c - sp / 2; nb = c + sp / 2; break; }
      case "Home": na = lo; nb = lo + span; break;
      case "End": nb = hi; na = hi - span; break;
      default: return;
    }
    e.preventDefault();
    const sp = Math.min(nb - na, hi - lo);
    if (na < lo) { na = lo; nb = lo + sp; }
    if (nb > hi) { nb = hi; na = hi - sp; }
    s.span = nb - na; s.end = nb >= hi - (hi - lo) * 0.004 ? null : nb;
    save(); refresh(el);
  });

  /* ---------- interaction (delegated: the page is re-rendered often) ---------- */
  let drag = null;
  document.addEventListener("click", e => {
    const b = e.target.closest && e.target.closest(".chart .presets button");
    if (!b) return;
    const el = b.closest(".chart"), def = DEFS[el.dataset.key], s = state(def);
    s.span = +b.dataset.span; s.end = null;
    save(); refresh(el);
  });
  document.addEventListener("pointerdown", e => {
    const svg = e.target.closest && e.target.closest("svg.mini");
    if (!svg || !CU.lastModel) return;
    const el = svg.closest(".chart"), def = DEFS[el.dataset.key], m = CU.lastModel, s = state(def);
    const [lo, hi] = def.domain(m), [a, b] = win(s, lo, hi, def.minSpan), r = svg.getBoundingClientRect(), k_ = r.width / W;
    const px = ms => r.left + mx(ms, lo, hi) * k_, x = e.clientX, edge = e.pointerType === "touch" ? 22 : 9;
    let mode = Math.abs(x - px(a)) <= edge ? "l" : Math.abs(x - px(b)) <= edge ? "r" : x > px(a) && x < px(b) ? "m" : "c", a0 = a, b0 = b;
    if (mode === "c") {                                               // click outside: centre the window there
      const at = lo + (x - px(lo)) / (px(hi) - px(lo)) * (hi - lo), span = b - a;
      a0 = clamp(at - span / 2, lo, hi - span); b0 = a0 + span; mode = "m";
    }
    drag = { svg, el, def, lo, hi, mode, a0, b0, x0: x, perMs: (W - L - R) * k_ / (hi - lo) };
    svg.setPointerCapture(e.pointerId);
    CU.dragging = true;
    e.preventDefault();
    apply(x);
  });
  function apply(x) {
    const d = drag, dms = (x - d.x0) / d.perMs, min = d.def.minSpan;
    let a = d.a0, b = d.b0;
    if (d.mode === "m") { const sh = clamp(dms, d.lo - d.a0, d.hi - d.b0); a += sh; b += sh; }
    else if (d.mode === "l") a = clamp(d.a0 + dms, d.lo, d.b0 - Math.min(min, d.b0 - d.lo));
    else b = clamp(d.b0 + dms, d.a0 + Math.min(min, d.hi - d.a0), d.hi);
    const s = state(d.def);
    s.span = b - a; s.end = b >= d.hi - (d.hi - d.lo) * 0.004 ? null : b;
    refresh(d.el);
  }
  document.addEventListener("pointermove", e => { if (drag) apply(e.clientX); });

  /* Main plot (charts with an overview): drag to move the range, pinch with two fingers to zoom. A press that
     barely moves is a tap: it is left to the tooltip (CU.tip). */
  const touch = { pts: new Map(), el: null, start: null };
  function plotRange(el) {
    const def = DEFS[el.dataset.key], m = CU.lastModel, s = state(def), [lo, hi] = def.domain(m), [a, b] = win(s, lo, hi, def.minSpan);
    return { def, s, lo, hi, a, b };
  }
  document.addEventListener("pointerdown", e => {
    const svg = e.target.closest && e.target.closest("svg.plot");
    const el = svg && svg.closest(".chart");
    if (!el || !CU.lastModel || !el.querySelector("svg.mini")) return;
    touch.pts.set(e.pointerId, e.clientX);
    if (touch.el !== el) { touch.el = el; touch.pts = new Map([[e.pointerId, e.clientX]]); }
    const r = svg.getBoundingClientRect(), xs = [...touch.pts.values()];
    touch.start = Object.assign(plotRange(el), { xs, px: (W - L - R) * r.width / W, left: r.left + L * r.width / W, moved: false });
    try { svg.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
  });
  document.addEventListener("pointermove", e => {
    if (!touch.start || !touch.pts.has(e.pointerId)) return;
    touch.pts.set(e.pointerId, e.clientX);
    const st = touch.start, xs = [...touch.pts.values()], span0 = st.b - st.a, perPx = span0 / st.px;
    let a, b;
    if (xs.length >= 2 && st.xs.length >= 2) {                         // pinch: keep the point under the fingers' middle
      const d0 = Math.abs(st.xs[0] - st.xs[1]) || 1, d1 = Math.abs(xs[0] - xs[1]) || 1;
      const span = clamp(span0 * d0 / d1, st.def.minSpan, st.hi - st.lo);
      const c0 = st.a + ((st.xs[0] + st.xs[1]) / 2 - st.left) * perPx, f_ = (c0 - st.a) / span0;
      const c1 = (xs[0] + xs[1]) / 2;
      a = c0 - f_ * span - (c1 - (st.xs[0] + st.xs[1]) / 2) * span / st.px; b = a + span;
    } else {
      const dx = xs[0] - st.xs[0];
      if (!st.moved && Math.abs(dx) < 6) return;
      a = st.a - dx * perPx; b = st.b - dx * perPx;
    }
    st.moved = true; CU.dragging = true;
    const span = b - a;
    if (a < st.lo) { a = st.lo; b = a + span; }
    if (b > st.hi) { b = st.hi; a = b - span; }
    st.s.span = b - a; st.s.end = b >= st.hi - (st.hi - st.lo) * 0.004 ? null : b;
    refresh(touch.el);
  });
  const endTouch = e => {
    if (!touch.pts.delete(e.pointerId)) return;
    if (touch.start && touch.start.moved) { CU.tipSuppress = Date.now(); save(); }
    if (touch.pts.size && touch.start) {                               // one finger left: go on from the current range
      const pr = plotRange(touch.el);
      touch.start = Object.assign({}, touch.start, { xs: [...touch.pts.values()], a: pr.a, b: pr.b });
      return;
    }
    touch.start = null; touch.el = null;
    if (!drag) CU.dragging = false;
  };
  document.addEventListener("pointerup", endTouch);
  document.addEventListener("pointercancel", endTouch);
  const stop = () => { if (!drag) return; drag = null; CU.dragging = false; save(); };
  document.addEventListener("pointerup", stop);
  document.addEventListener("pointercancel", stop);
})(window.CU);
