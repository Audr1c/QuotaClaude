/* views.js: the two presentations. Each one receives the model (CU.compute) and returns HTML.
   Colors: blue = 5-hour window; orange (clay) = everything that is about the week. */
window.CU = window.CU || {};

(function (CU) {
  const BLUE = "var(--blue)", BLUE_INK = "var(--blue-ink)", CLAY = "var(--clay)", CLAY_INK = "var(--clay-ink)";
  const t = (k, v) => CU.t(k, v);
  const pct = (v, d) => CU.fmt.pct(v, d);
  const num = (v, d) => CU.fmt.num(v, d);
  const big = v => `${Math.round(v)}<tspan font-size="0.48em">%</tspan>`;

  const pill = (st, prefix = "") => st ? `<span class="pill ${st.kind}">${prefix}${t("status." + st.kind, { n: st.n })}</span>` : "";
  const li = (kind, color, lbl, val) =>
    `<li><span class="${kind}" style="color:${color || "inherit"}"></span><span class="lbl">${lbl}</span>`
    + `<b${kind === "sp" ? "" : ` style="color:${color}"`}>${val}</b></li>`;
  const resetText = w => w.active
    ? t("reset.in", { left: CU.fmt.left(w.left), when: CU.fmt.when(w.reset) })
    : t("reset.none");
  const budgetText = b => b >= 100 ? t("cap") : pct(b);

  /* ---------------- detailed view: two cards ---------------- */
  function detail(m) {
    const { five, seven } = m;
    const card5 = `
      <section class="card">
        <div class="card-head"><h2>${t("card.five")}</h2>${pill(CU.status(five.used, five.pace))}</div>
        ${CU.gauge({
          label: t("card.five"),
          rings: [{ r: 118, width: 20, used: five.used, color: BLUE, limit: five.active ? five.budget : null,
                    markers: [{ v: five.pace, color: BLUE_INK }, { v: five.budget, color: CLAY_INK }] }],
          center: [{ dy: 10, text: big(five.used), size: 56, serif: true },
                   { dy: 36, text: t("gauge.used"), size: 13, fill: "var(--muted)" }],
          footer: resetText(five),
        })}
        <ul class="legend">
          ${li("dot", BLUE, t("legend.used"), pct(five.used))}
          ${li("tri", BLUE_INK, t("legend.pace5"), pct(five.pace))}
          ${li("tri", CLAY_INK, t("legend.limit5"), budgetText(five.budget))}
          ${li("sp", "", t("legend.max5"), pct(five.maxRate, 1) + t("unit.perhour"))}
          ${li("sp", "", t("legend.advice5"), pct(five.paceRate, 1) + t("unit.perhour"))}
        </ul>
      </section>`;

    const card7 = `
      <section class="card">
        <div class="card-head"><h2>${t("card.seven")}</h2>${pill(CU.status(seven.used, seven.pace))}</div>
        ${CU.gauge({
          label: t("card.seven"),
          rings: [{ r: 118, width: 20, used: seven.used, color: CLAY, limit: seven.pace, markers: [{ v: seven.pace, color: CLAY_INK }] }],
          center: [{ dy: 10, text: big(seven.used), size: 56, serif: true },
                   { dy: 36, text: t("gauge.used"), size: 13, fill: "var(--muted)" }],
          footer: resetText(seven),
        })}
        <ul class="legend">
          ${li("dot", CLAY, t("legend.used"), pct(seven.used))}
          ${li("tri", CLAY_INK, t("legend.pace7"), pct(seven.pace))}
          ${li("sp", "", t("legend.perday"), pct(seven.ratePerDay, 1) + " " + t("unit.perday"))}
          ${li("sp", "", t("legend.sessions"), "≈ " + num(seven.sessionsLeft))}
          ${li("sp", "", t("legend.remaining"), pct(seven.remaining))}
        </ul>
      </section>`;

    return `<div class="grid">${card5}${card7}</div>`;
  }

  /* ---------------- compact view: one block, two concentric rings ---------------- */
  function compact(m) {
    const { five, seven } = m;
    const svg = CU.gauge({
      label: t("gauge.aria.compact"),
      rings: [
        { r: 126, width: 16, used: seven.used, color: CLAY, limit: seven.pace, markers: [{ v: seven.pace, color: CLAY_INK, side: "out" }] },
        { r: 92, width: 16, used: five.used, color: BLUE, limit: five.active ? five.budget : null,
          markers: [{ v: five.pace, color: BLUE_INK, side: "in" }, { v: five.budget, color: CLAY_INK, side: "out" }] },
      ],
      center: [
        { dy: -38, text: t("compact.label.five"), size: 10, fill: "var(--muted)", spacing: "1.2" },
        { dy: -6, text: big(five.used), size: 34, fill: BLUE_INK, serif: true },
        { dy: 20, text: t("compact.label.seven"), size: 10, fill: "var(--muted)", spacing: "1.2" },
        { dy: 52, text: big(seven.used), size: 34, fill: CLAY_INK, serif: true },
      ],
    });
    const st5 = CU.status(five.used, five.pace), st7 = CU.status(seven.used, seven.pace);
    return `
      <section class="card compact">
        <div class="card-head"><h2>${t("card.compact")}</h2>
          <div class="pills">${pill(st5, t("compact.five") + " · ")}${pill(st7, t("compact.seven") + " · ")}</div></div>
        ${svg}
        <div class="resets">
          <div><span class="dot" style="color:${BLUE}"></span>${t("compact.five")}: ${resetText(five)}</div>
          <div><span class="dot" style="color:${CLAY}"></span>${t("compact.seven")}: ${resetText(seven)}</div>
        </div>
        <ul class="legend">
          ${li("tri", BLUE_INK, t("compact.legend.pace5"), pct(five.pace))}
          ${li("tri", CLAY_INK, t("compact.legend.limit5"), budgetText(five.budget))}
          ${li("tri", CLAY_INK, t("compact.legend.pace7"), pct(seven.pace))}
        </ul>
        <div class="stats">
          <div><b>${pct(five.paceRate, 1)}</b><span>${t("stat.rate")}</span></div>
          <div><b>${pct(seven.ratePerDay, 1)}</b><span>${t("stat.day")}</span></div>
          <div><b>≈ ${num(seven.sessionsLeft)}</b><span>${t("stat.windows")}</span></div>
        </div>
      </section>`;
  }

  /* ---------------- per-product breakdown (collapsed by default) ---------------- */
  CU.breakdown = function (m, open) {
    const rows = m.breakdown.filter(r => r.share > 0).sort((a, b) => b.share - a.share);
    if (!rows.length) return "";
    const max = Math.max(...rows.map(r => r.share));
    const count = rows.length === 1 ? t("breakdown.count.one") : t("breakdown.count", { n: rows.length });
    return `
      <details class="card breakdown"${open ? " open" : ""}>
        <summary><h2>${t("breakdown.title")}</h2><span class="hint">${count}</span></summary>
        <ul class="bars">
          ${rows.map(r => `
            <li>
              <span class="name">${r.name}</span>
              <span class="bar"><span style="width:${(r.share / max * 100).toFixed(1)}%"></span></span>
              <b>${pct(r.share)}</b>
              <span class="q">${t("breakdown.quota", { n: num(r.quota) })}</span>
            </li>`).join("")}
        </ul>
        <p class="note">${t("breakdown.note", { pct: pct(m.seven.used) })}</p>
      </details>`;
  };

  CU.views = { detail, compact };
})(window.CU);
