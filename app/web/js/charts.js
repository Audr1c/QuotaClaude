/* charts.js: the two history charts (plain SVG, no dependency).
     1. usage per hour over the last 24 h, in % of the 5-hour window, against the pace you can afford;
     2. evolution of the 5h -> week ratio (how many % of the week one full 5-hour window costs), day by day. */
window.CU = window.CU || {};

(function (CU) {
  const t = (k, v) => CU.t(k, v);
  const W = 640, HT = 210, L = 38, R = 12, T = 12, B = 26;          // viewBox and margins
  const f = n => n.toFixed(1);
  const axisY = (max, step, y) => {
    let s = "";
    for (let v = 0; v <= max + 1e-9; v += step)
      s += `<line x1="${L}" x2="${W - R}" y1="${f(y(v))}" y2="${f(y(v))}" stroke="var(--line)"/>`
        + `<text x="${L - 6}" y="${f(y(v) + 4)}" text-anchor="end" class="ax">${Math.round(v * 10) / 10}</text>`;
    return s;
  };
  const niceStep = max => { const raw = max / 4, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; };
  const hh = ms => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

  /* ---------- 1. hourly usage ---------- */
  function hourlyChart(m) {
    const data = CU.hourly(m.history, Date.now(), 24), rate = m.five.paceRate;
    const peak = Math.max(...data.map(d => d.v), rate || 0, 1), step = niceStep(peak * 1.1), max = Math.ceil(peak * 1.1 / step) * step;
    const y = v => HT - B - (HT - B - T) * v / max, bw = (W - L - R) / data.length;
    const bars = data.map((d, i) => {
      const x = L + i * bw, h = HT - B - y(d.v), over = rate != null && d.v > rate;
      const lbl = i % 3 === 0 || i === data.length - 1 ? `<text x="${f(x + bw / 2)}" y="${HT - 8}" text-anchor="middle" class="ax">${new Date(d.t).getHours()} h</text>` : "";
      return `<rect x="${f(x + 2)}" y="${f(y(d.v))}" width="${f(bw - 4)}" height="${f(Math.max(h, 0))}" rx="2" fill="${over ? "var(--clay)" : "var(--blue)"}">`
        + `<title>${hh(d.t)} · ${CU.fmt.pct(d.v, 1)}</title></rect>${lbl}`;
    }).join("");
    const line = rate == null ? "" : `<line x1="${L}" x2="${W - R}" y1="${f(y(rate))}" y2="${f(y(rate))}" stroke="var(--clay-ink)" stroke-width="1.5" stroke-dasharray="5 4"/>`;
    const total = data.reduce((a, d) => a + d.v, 0);
    return `
      <details class="card chart" data-key="hourly">
        <summary><h2>${t("chart.hourly.title")}</h2><span class="hint">${t("chart.hourly.total", { n: CU.fmt.pct(total) })}</span></summary>
        <svg viewBox="0 0 ${W} ${HT}" role="img" aria-label="${t("chart.hourly.title")}">${axisY(max, step, y)}${bars}${line}</svg>
        <p class="note">${t("chart.hourly.note", { rate: rate == null ? "—" : CU.fmt.pct(rate, 1) })}</p>
      </details>`;
  }

  /* ---------- 2. ratio over time ---------- */
  function ratioChart(m) {
    const days = m.ratioDaily;
    if (days.length < 2) return "";
    const vals = days.flatMap(d => [d.ratio, d.cum]).filter(v => v != null).concat(m.ratio);
    const lo = Math.floor(Math.min(...vals) - 1), hi = Math.ceil(Math.max(...vals) + 1), step = niceStep(hi - lo);
    const y = v => HT - B - (HT - B - T) * (v - lo) / (hi - lo);
    const x = i => L + (W - L - R) * (days.length === 1 ? .5 : i / (days.length - 1));
    let grid = "";
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step)
      grid += `<line x1="${L}" x2="${W - R}" y1="${f(y(v))}" y2="${f(y(v))}" stroke="var(--line)"/><text x="${L - 6}" y="${f(y(v) + 4)}" text-anchor="end" class="ax">${Math.round(v * 10) / 10}</text>`;
    const path = key => days.map((d, i) => d[key] == null ? null : [x(i), y(d[key])]).reduce((acc, p) => {
      if (p) acc.push((acc.length && acc.open ? "L" : "M") + f(p[0]) + " " + f(p[1])), acc.open = true; else acc.open = false; return acc; }, []).join(" ");
    const dots = days.map((d, i) => d.ratio == null ? "" :
      `<circle cx="${f(x(i))}" cy="${f(y(d.ratio))}" r="3.5" fill="var(--blue)"><title>${d.day} · ${CU.fmt.pct(d.ratio, 1)} (${t("chart.ratio.tip", { a: CU.fmt.num(d.d5), b: CU.fmt.num(d.d7) })})</title></circle>`).join("");
    const labelEvery = Math.ceil(days.length / 8);
    const xl = days.map((d, i) => i % labelEvery && i !== days.length - 1 ? "" :
      `<text x="${f(x(i))}" y="${HT - 8}" text-anchor="middle" class="ax">${d.day.slice(8)}/${d.day.slice(5, 7)}</text>`).join("");
    const cur = `<line x1="${L}" x2="${W - R}" y1="${f(y(m.ratio))}" y2="${f(y(m.ratio))}" stroke="var(--clay-ink)" stroke-width="1" stroke-dasharray="2 4"/>`;
    return `
      <details class="card chart" data-key="ratio">
        <summary><h2>${t("chart.ratio.title")}</h2><span class="hint">${t("chart.ratio.now", { n: CU.fmt.pct(m.ratio, 1) })}</span></summary>
        <svg viewBox="0 0 ${W} ${HT}" role="img" aria-label="${t("chart.ratio.title")}">${grid}${cur}
          <path d="${path("cum")}" fill="none" stroke="var(--clay)" stroke-width="2.5" stroke-linejoin="round"/>${dots}${xl}</svg>
        <ul class="legend chart-legend">
          <li><span class="dot" style="color:var(--blue)"></span><span class="lbl">${t("chart.ratio.day")}</span></li>
          <li><span class="dot" style="color:var(--clay)"></span><span class="lbl">${t("chart.ratio.cum")}</span></li>
        </ul>
        <p class="note">${t("chart.ratio.note")}</p>
      </details>`;
  }

  CU.charts = m => hourlyChart(m) + ratioChart(m);
})(window.CU);
