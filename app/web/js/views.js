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

  /* ---------------- detailed view: two cards ---------------- */
  function detail(m) {
    const { five, seven } = m;
    const card5 = `
      <section class="card">
        <div class="card-head"><h2>${t("card.five")}</h2>${pill(CU.status(five.used, five.pace))}</div>
        ${CU.gauge({
          label: t("card.five"),
          rings: [{ r: 118, width: 20, used: five.used, color: BLUE, limit: five.limit,
                    markers: [{ v: five.pace, color: BLUE_INK }, { v: five.limit, color: CLAY_INK }] }],
          center: [{ dy: 10, text: big(five.used), size: 56, serif: true },
                   { dy: 36, text: t("gauge.used"), size: 13, fill: "var(--muted)" }],
          footer: resetText(five),
        })}
        <ul class="legend">
          ${li("dot", BLUE, t("legend.used"), pct(five.used))}
          ${li("tri", BLUE_INK, t("legend.pace5"), pct(five.pace))}
          ${li("tri", CLAY_INK, t("legend.limit5"), pct(five.limit))}
          ${li("sp", "", t("legend.max5"), pct(five.maxRate, 1) + t("unit.perhour"))}
          ${li("sp", "", t("legend.advice5"), pct(five.paceRate, 1) + t("unit.perhour"))}
        </ul>
      </section>`;

    const card7 = `
      <section class="card">
        <div class="card-head"><h2>${t("card.seven")}</h2>${pill(CU.status(seven.used, seven.pace))}</div>
        ${CU.gauge({
          label: t("card.seven"),
          rings: [{ r: 118, width: 20, used: seven.used, color: CLAY, limit: seven.limit, markers: [{ v: seven.pace, color: CLAY_INK }] }],
          center: [{ dy: 10, text: big(seven.used), size: 56, serif: true },
                   { dy: 36, text: t("gauge.used"), size: 13, fill: "var(--muted)" }],
          footer: resetText(seven),
        })}
        <ul class="legend">
          ${li("dot", CLAY, t("legend.used"), pct(seven.used))}
          ${li("tri", CLAY_INK, t("legend.pace7"), pct(seven.pace))}
          ${li("sp", "", t("legend.perday"), pct(seven.ratePerDay, 1) + " " + t("unit.perday"))}
          ${li("sp", "", t("legend.sessions"), "≈ " + num(seven.sessionsLeft))}
          ${li("sp", "", t("legend.today"), pct(seven.todayLeft, 1))}
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
        { r: 126, width: 16, used: seven.used, color: CLAY, limit: seven.limit, markers: [{ v: seven.pace, color: CLAY_INK, side: "out" }] },
        { r: 92, width: 16, used: five.used, color: BLUE, limit: five.limit,
          markers: [{ v: five.pace, color: BLUE_INK, side: "in" }, { v: five.limit, color: CLAY_INK, side: "out" }] },
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
          ${li("tri", CLAY_INK, t("compact.legend.limit5"), pct(five.limit))}
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
  /* One segment per day inside each bar. data-labels = the day name from longest to shortest; CU.fitBars keeps
     the longest one that fits once the bar has its real width. */
  const esc = x => String(x).replace(/[&<>"|]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "|": "" }[c]));
  function daySegment(s) {
    if (s.day === undefined) return `<span class="day" style="flex-grow:1"></span>`;   // no per-day data yet
    const loc = CU.lang === "fr" ? "fr-FR" : "en-GB", cap = x => x.charAt(0).toUpperCase() + x.slice(1);
    let labels = [], when = t("breakdown.earlier.title");
    if (s.day) {
      const d = new Date(s.day + "T12:00:00");
      labels = ["long", "short", "narrow"].map(w => cap(d.toLocaleDateString(loc, { weekday: w })));
      when = cap(d.toLocaleDateString(loc, { weekday: "long", day: "numeric", month: "short" }));
    } else if (s.day === null) {
      labels = [t("breakdown.earlier"), t("breakdown.earlier.short"), "…"];
    }
    const title = when + " · " + t("breakdown.quota", { n: num(s.pts) }) + (s.est ? " · " + t("breakdown.est") : "");
    return `<span class="day" style="flex-grow:${s.pts}" data-labels="${labels.map(esc).join("|")}" title="${esc(title)}"></span>`;
  }

  CU.fitBars = function (root) {
    const ctx = (CU.fitBars.ctx = CU.fitBars.ctx || document.createElement("canvas").getContext("2d"));
    root.querySelectorAll(".bars .day").forEach(el => {
      const labels = (el.dataset.labels || "").split("|").filter(Boolean);
      if (!labels.length) return;
      ctx.font = getComputedStyle(el).font;
      const room = el.clientWidth - 6;
      el.textContent = labels.find(l => ctx.measureText(l).width <= room) || "";
    });
  };

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
              <span class="bar"><span class="fill" style="width:${(r.share / max * 100).toFixed(1)}%">${(r.days.length ? r.days : [{ pts: 1 }]).map(daySegment).join("")}</span></span>
              <b>${pct(r.share)}</b>
              <span class="q">${t("breakdown.quota", { n: num(r.quota) })}</span>
            </li>`).join("")}
        </ul>
        <p class="note">${t("breakdown.note", { pct: pct(m.seven.used) })} ${t("breakdown.days")}</p>
      </details>`;
  };

  /* ---------------- "how it is computed" panel: every equation, with your current numbers ---------------- */
  const hhmm = ms => new Date(ms).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  CU.formulas = function (m, open) {
    const { five, seven } = m, H = 3600e3, dash = "—";
    const hl5 = five.left / H, dl7 = seven.left / (24 * H);
    const p1 = v => v == null ? dash : pct(v, 1), n2 = v => v == null ? dash : num(v, 2);
    const rows = [
      ["used", "", "", `${p1(five.used)} / ${p1(seven.used)}`],
      ["pace5", "", `(5 h − ${n2(hl5)} h) / 5 h`, p1(five.pace)],
      ["start", "", "", seven.work && seven.work.startToday ? hhmm(seven.work.startToday.ms) + " " + (seven.work.startToday.auto ? t("f.start.auto") : t("f.start.def")) : dash],
      ["pace7", "slider", seven.work ? `${n2(seven.work.elapsedH)} h / ${n2(seven.work.totalH)} h` : "", p1(seven.pace)],
      ["ratio", "", m.ratioEstimated ? t("f.ratio.est") : t("f.ratio.def"), p1(m.ratio)],
      ["u0", "", "", p1(seven.startUsed)],
      ["days", "", "", n2(seven.daysLeft) + " d"],
      ["budget", "", `(100 − ${p1(seven.startUsed)}) / ${n2(seven.daysLeft)}`, p1(seven.dailyBudget)],
      ["l7", "", `${p1(seven.startUsed)} + ${p1(seven.dailyBudget)}`, p1(seven.limit)],
      ["left", "", `max(0, ${p1(seven.limit)} − ${p1(seven.used)})`, p1(seven.todayLeft)],
      ["l5", "", `${p1(five.used)} + ${p1(seven.todayLeft)} × 100 / ${p1(m.ratio)}`, p1(five.limit)],
      ["rate", "slider", `${p1(seven.dailyBudget)} / ${m.hours} h × 100 / ${p1(m.ratio)}`, p1(five.paceRate) + t("unit.perhour")],
      ["max", "", `(100 − ${p1(five.used)}) / ${n2(hl5)} h`, p1(five.maxRate) + t("unit.perhour")],
      ["win", "", `(100 − ${p1(seven.used)}) / ${p1(m.ratio)}`, "≈ " + num(seven.sessionsLeft)],
      ["share", "", "", ""],
    ];
    return `
      <details class="card formulas" data-key="formulas"${open ? " open" : ""}>
        <summary><h2>${t("formulas.title")}</h2><span class="hint">${t("formulas.hint")}</span></summary>
        <p class="note">${t("formulas.slider")}</p>
        <table class="eqs">
          ${rows.map(([id, flag, calc, val]) => `
            <tr${flag ? ' class="flag"' : ""}>
              <th>${t("f." + id + ".name")}${flag ? ` <span class="badge">${t("formulas.badge")}</span>` : ""}</th>
              <td><code>${t("f." + id + ".eq")}</code>${calc || val ? `<br><span class="calc">${calc}${val ? (calc ? " = " : "") + "<b>" + val + "</b>" : ""}</span>` : ""}</td>
            </tr>`).join("")}
        </table>
      </details>`;
  };

  CU.views = { detail, compact };
})(window.CU);
