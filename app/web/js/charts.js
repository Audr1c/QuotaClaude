/* charts.js: the history charts (plain SVG, no dependency).
     1. usage per hour, in % of the 5-hour window, against the pace you can afford;
     2. evolution of the 5h -> week ratio (how many % of the week one full 5-hour window costs), day by day;
     3. tokens and cache read from the local transcripts, split by model.
   Each chart has a range: preset buttons, and (charts 1 and 2) a small overview below it, like a market chart:
   drag the window to move it, drag its edges to zoom, click outside to jump there. The range is kept in
   localStorage. While a drag is going on, CU.dragging is true and the page does not re-render. */
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
  const bucketHours = n => n <= 48 ? 1 : n <= 96 ? 3 : n <= 240 ? 6 : 24;
  function bucketStart(ms, bh) {
    const d = new Date(ms);
    if (bh >= 24) d.setHours(0, 0, 0, 0); else d.setHours(Math.floor(d.getHours() / bh) * bh, 0, 0, 0);
    return d.getTime();
  }
  function nextStart(s, bh) {
    const n = bucketStart(s + (bh >= 24 ? 30 * H : bh * H + H / 2), bh);
    return n > s ? n : s + bh * H;                                     // DST: never loop
  }
  const hourlyDomain = m => {
    const hi = Math.ceil(Date.now() / H) * H, first = m.firstAt ? Date.parse(m.firstAt) : hi - DAY;
    return [Math.min(Math.floor(first / H) * H, hi - DAY), hi];
  };
  function hourlyBuckets(m, a, b) {
    const bh = bucketHours((b - a) / H), out = [];
    for (let s = bucketStart(a, bh); s < b && out.length < 400; ) { const e = nextStart(s, bh); out.push({ t: s, e, v: 0 }); s = e; }
    for (const [iso, v] of m.hourly5) {
      const ts = Date.parse(iso), bk = out.find(x => ts >= x.t && ts < x.e);
      if (bk) bk.v += v;
    }
    return { bh, bars: out };
  }
  function hourlyPlot(m, a, b) {
    const { bh, bars } = hourlyBuckets(m, a, b), rate = bh <= 6 ? m.five.paceRate * bh : null;
    const peak = Math.max(...bars.map(d => d.v), rate || 0, 1), step = niceStep(peak * 1.1), max = Math.ceil(peak * 1.1 / step) * step;
    const y = v => HT - B - (HT - B - T) * v / max, bw = (W - L - R) / bars.length, stride = Math.max(1, Math.ceil(bars.length / 9));
    let grid = "";
    for (let v = 0; v <= max + 1e-9; v += step)
      grid += `<line x1="${L}" x2="${W - R}" y1="${f(y(v))}" y2="${f(y(v))}" stroke="var(--line)"/><text x="${L - 6}" y="${f(y(v) + 4)}" text-anchor="end" class="ax">${Math.round(v * 10) / 10}</text>`;
    const body = bars.map((d, i) => {
      const x = L + i * bw, hr = new Date(d.t).getHours(), over = rate != null && d.v > rate;
      const show = bh === 1 || bh === 24 ? i % stride === 0 : hr === 0;            // 3 h / 6 h bars: label each midnight
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
  function ratioPlot(m, a, b) {
    const days = ratioDays(m).filter(d => d.ms >= a && d.ms <= b);
    const vals = days.flatMap(d => [d.ratio, d.cum]).filter(v => v != null).concat(m.ratio);
    const lo = Math.floor(Math.min(...vals) - 1), hi = Math.ceil(Math.max(...vals) + 1), step = niceStep(hi - lo);
    const y = v => HT - B - (HT - B - T) * (v - lo) / (hi - lo), x = ms => L + (W - L - R) * (ms - a) / (b - a);
    let grid = "";
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step)
      grid += `<line x1="${L}" x2="${W - R}" y1="${f(y(v))}" y2="${f(y(v))}" stroke="var(--line)"/><text x="${L - 6}" y="${f(y(v) + 4)}" text-anchor="end" class="ax">${Math.round(v * 10) / 10}</text>`;
    const path = days.filter(d => d.cum != null).map((d, i) => (i ? "L" : "M") + f(x(d.ms)) + " " + f(y(d.cum))).join(" ");
    const dots = days.map(d => d.ratio == null ? "" :
      `<circle cx="${f(x(d.ms))}" cy="${f(y(d.ratio))}" r="3.5" fill="var(--blue)"><title>${d.day} · ${CU.fmt.pct(d.ratio, 1)} (${t("chart.ratio.tip", { a: CU.fmt.num(d.d5), b: CU.fmt.num(d.d7) })})</title></circle>`).join("");
    const stride = Math.max(1, Math.ceil(days.length / 8));
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

  /* ---------- 3. tokens and cache, split by model ---------- */
  const modelColor = n => /opus/i.test(n) ? "var(--clay)" : /sonnet/i.test(n) ? "var(--blue)" : /haiku/i.test(n) ? "var(--sage)" : "var(--muted)";
  const modelName = n => n.replace(/^claude-/, "");
  const worked = v => v[0] + v[1] + v[3];                                // input + output + cache writes
  const hit = v => { const tot = v[0] + v[2] + v[3]; return tot > 0 ? 100 * v[2] / tot : null; };
  const hitTxt = h => h == null ? "—" : CU.fmt.pct(h, h < 99.5 ? 0 : 1);
  function tokensPlot(m, a, b, span) {
    const tk = m.tokens;
    const cut = span ? new Date(Date.now() - (span / DAY - 1) * DAY).toISOString().slice(0, 10) : "";
    const days = tk.days.filter(d => d.day >= cut).reverse();
    const agg = {}, tot = [0, 0, 0, 0, 0];
    let d7 = 0;
    for (const d of days) {
      d7 += d.d7 || 0;
      for (const [n, v] of Object.entries(d.models || {})) {
        const x = agg[n] || (agg[n] = [0, 0, 0, 0, 0]);
        v.forEach((q, i) => { x[i] += q; tot[i] += q; });
      }
    }
    const models = Object.entries(agg).filter(x => worked(x[1]) > 0).sort((p, q) => worked(q[1]) - worked(p[1]));
    const all = worked(tot) || 1, top = models.slice(0, 2).map(x => x[0]);
    const share = `<div class="share">${models.map(([n, v]) => `<span style="flex-grow:${worked(v)};background:${modelColor(n)}" title="${modelName(n)} · ${k(worked(v))}"></span>`).join("")}</div>`;
    const mrows = models.map(([n, v]) => `<tr><th><span class="dot" style="color:${modelColor(n)}"></span>${modelName(n)}</th>`
      + `<td>${CU.fmt.pct(100 * worked(v) / all, 0)}</td><td>${k(worked(v))}</td><td>${k(v[1])}</td><td>${hitTxt(hit(v))}</td><td>${k(v[4])}</td></tr>`).join("");
    const maxDay = Math.max(...days.map(d => Object.values(d.models || {}).reduce((s, v) => s + worked(v), 0)), 1);
    const drows = days.map(d => {
      const ms = Object.entries(d.models || {}).sort((p, q) => worked(q[1]) - worked(p[1])), dw = ms.reduce((s, x) => s + worked(x[1]), 0);
      const bar = ms.map(([n, v]) => `<span style="width:${(worked(v) / maxDay * 100).toFixed(1)}%;background:${modelColor(n)}" title="${modelName(n)} · ${k(worked(v))} · ${t("chart.tokens.c.hit")} ${hitTxt(hit(v))}"></span>`).join("");
      const hits = top.map(n => d.models && d.models[n] ? `<span style="color:${modelColor(n)}">${hitTxt(hit(d.models[n]))}</span>` : "<span>—</span>").join(" ");
      return `<tr><th>${dm(Date.parse(d.day + "T12:00:00Z"))}</th><td><span class="tbar">${bar}</span></td><td>${k(dw)}</td><td class="hits">${hits}</td>`
        + `<td>${d.d7 ? CU.fmt.pct(d.d7, 0) : "—"}</td><td>${k(d.tokens_per_pct)}</td></tr>`;
    }).join("");
    const hitHead = top.map(n => `<span style="color:${modelColor(n)}">${modelName(n).split("-")[0]}</span>`).join(" ");
    return { svg: `
        <div class="stats">
          <div><b>${hitTxt(hit(tot))}</b><span>${t("chart.tokens.s.hit")}</span></div>
          <div><b>${k(worked(tot))}</b><span>${t("chart.tokens.s.fresh")}</span></div>
          <div><b>${k(d7 > 0 ? Math.round(worked(tot) / d7) : null)}</b><span>${t("chart.tokens.s.perpct")}</span></div>
        </div>
        <h3 class="sub">${t("chart.tokens.bymodel")}</h3>${share}
        <table class="eqs tokens"><tr><th></th><td>${t("chart.tokens.m.share")}</td><td>${t("chart.tokens.c.fresh")}</td><td>${t("chart.tokens.m.out")}</td><td>${t("chart.tokens.c.hit")}</td><td>${t("chart.tokens.m.msgs")}</td></tr>${mrows}</table>
        <h3 class="sub">${t("chart.tokens.byday")}</h3>
        <table class="eqs tokens"><tr><th></th><td></td><td>${t("chart.tokens.c.fresh")}</td><td class="hits">${t("chart.tokens.c.hit")} ${hitHead}</td><td>${t("chart.tokens.c.week")}</td><td>${t("chart.tokens.c.perpct")}</td></tr>${drows}</table>` };
  }

  /* ---------- the chart definitions ---------- */
  const P = (key, ms) => [key, ms];
  const DEFS = {
    hourly: {
      key: "hourly", span: DAY, minSpan: 6 * H, presets: [P("24h", DAY), P("3d", 3 * DAY), P("7d", 7 * DAY), P("14d", 14 * DAY), P("all", 0)],
      ready: m => m.hourly5 && m.hourly5.length, domain: hourlyDomain, mini: hourlyMini, plot: hourlyPlot,
      label: (r, a, b) => `${dmh(a)} → ${dmh(b)} · ${r.bh < 24 ? t("chart.bucket.h", { n: r.bh }) : t("chart.bucket.d")} · ${t("chart.hourly.total", { n: CU.fmt.pct(r.total) })}`,
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
      plot: (m, a, b, s) => tokensPlot(m, a, b, s.span),
      label: () => "", hint: m => t("chart.tokens.hit", { n: hitTxt(m.tokens.week.cache_hit) }), note: () => t("chart.tokens.note"), legend: () => "",
    },
  };

  /* what a chart shows for the current range */
  function parts(def, m) {
    const s = state(def), [lo, hi] = def.domain(m), [a, b] = win(s, lo, hi, def.minSpan), r = def.plot(m, a, b, s);
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

  function card(def, m) {
    const p = parts(def, m);
    const buttons = def.presets.map(([key, ms]) =>
      `<button type="button" data-span="${ms}" aria-pressed="${pressed(def, ms, p.s.span, p.lo, p.hi, p.a, p.b)}">${t("range." + key)}</button>`).join("");
    const mini = def.noMini ? "" : `
        <svg class="mini" viewBox="0 0 ${W} ${MH}" aria-label="${t("chart.range.hint")}">${miniBody(def, m, p.lo, p.hi)}
          <rect class="dim dl" y="0" height="${MH}"/><rect class="dim dr" y="0" height="${MH}"/>
          <rect class="win" y="0.5" height="${MH - 1}" rx="3"/><rect class="hdl hl" y="${MH / 2 - 10}" width="6" height="20" rx="2"/><rect class="hdl hr" y="${MH / 2 - 10}" width="6" height="20" rx="2"/>
        </svg>`;
    const html = `
      <details class="card chart" data-key="${def.key}">
        <summary><h2>${t(def.title)}</h2><span class="hint">${def.hint(m, p.r)}</span></summary>
        <div class="presets seg" role="group">${buttons}</div>
        ${def.key === "tokens" ? `<div class="plot">${p.r.svg}</div>` : `<svg class="plot" viewBox="0 0 ${W} ${HT}" role="img" aria-label="${t(def.title)}">${p.r.svg}</svg>`}
        ${mini}
        <p class="rlabel">${p.label}${def.noMini ? "" : ` <span>${t("chart.range.hint")}</span>`}</p>
        ${def.legend()}
        <p class="note">${def.note(m)}</p>
      </details>`;
    return html;
  }

  /* after a change of range: redraw the plot, the label, the window and the buttons, never the overview itself */
  function refresh(el) {
    const def = DEFS[el.dataset.key], m = CU.lastModel;
    if (!def || !m) return;
    const p = parts(def, m), plot = el.querySelector(".plot");
    plot.innerHTML = p.r.svg;
    const rl = el.querySelector(".rlabel");
    if (rl.firstChild && rl.firstChild.nodeType === 3) rl.firstChild.textContent = p.label + " ";
    el.querySelector("summary .hint").innerHTML = def.hint(m, p.r);
    el.querySelectorAll(".presets button").forEach(b => b.setAttribute("aria-pressed", String(pressed(def, +b.dataset.span, p.s.span, p.lo, p.hi, p.a, p.b))));
    const svg = el.querySelector("svg.mini");
    if (svg) place(svg, p.lo, p.hi, p.a, p.b);
  }

  CU.charts = function (m) {
    CU.lastModel = m;
    const html = Object.values(DEFS).filter(d => d.ready(m)).map(d => card(d, m)).join("");
    return html;
  };
  CU.chartsAfterRender = function (root) {                              // window rectangles need the overview to exist
    const m = CU.lastModel;
    root.querySelectorAll(".chart").forEach(el => {
      const def = DEFS[el.dataset.key], svg = el.querySelector("svg.mini");
      if (def && svg && m) { const p = parts(def, m); place(svg, p.lo, p.hi, p.a, p.b); }
    });
  };

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
    const px = ms => r.left + mx(ms, lo, hi) * k_, x = e.clientX, edge = 9;
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
  const stop = () => { if (!drag) return; drag = null; CU.dragging = false; save(); };
  document.addEventListener("pointerup", stop);
  document.addEventListener("pointercancel", stop);
})(window.CU);
