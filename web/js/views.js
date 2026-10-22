/* views.js : les deux presentations. Chacune recoit le modele (CU.compute) et renvoie du HTML.
   Couleurs : bleu = fenetre 5 h ; orange (clay) = tout ce qui parle de la semaine. */
window.CU = window.CU || {};

(function (CU) {
  const F = CU.fmt;
  const BLUE = "var(--blue)", BLUE_INK = "var(--blue-ink)", CLAY = "var(--clay)", CLAY_INK = "var(--clay-ink)";
  const big = v => `${Math.round(v)}<tspan font-size="0.48em">%</tspan>`;

  const pill = (st, prefix = "") => st ? `<span class="pill ${st.kind}">${prefix}${st.text}</span>` : "";
  const li = (kind, color, lbl, val) =>
    `<li><span class="${kind}" style="color:${color || "inherit"}"></span><span class="lbl">${lbl}</span>`
    + `<b${kind === "sp" ? "" : ` style="color:${color}"`}>${val}</b></li>`;
  const resetText = w => w.active ? `reset dans ${F.left(w.left)} · ${F.when(w.reset)}` : "pas de fenêtre en cours";
  const budgetText = b => b >= 100 ? "100 % (plafond)" : F.pct(b);

  /* ---------------- vue détaillée : deux cartes ---------------- */
  function detail(m) {
    const { five, seven } = m;
    const card5 = `
      <section class="card">
        <div class="card-head"><h2>Fenêtre 5 heures</h2>${pill(CU.status(five.used, five.pace))}</div>
        ${CU.gauge({
          label: "Fenêtre 5 heures",
          rings: [{ r: 118, width: 20, used: five.used, color: BLUE,
                    markers: [{ v: five.pace, color: BLUE_INK }, { v: five.budget, color: CLAY_INK }] }],
          center: [{ dy: 10, text: big(five.used), size: 56, serif: true },
                   { dy: 36, text: "utilisés", size: 13, fill: "var(--muted)" }],
          footer: resetText(five),
        })}
        <ul class="legend">
          ${li("dot", BLUE, "Utilisé", F.pct(five.used))}
          ${li("tri", BLUE_INK, "Rythme 5 h (temps écoulé)", F.pct(five.pace))}
          ${li("tri", CLAY_INK, "Limite au rythme de la semaine", budgetText(five.budget))}
          ${li("sp", "", "Max possible d'ici le reset", F.pct(five.maxRate, 1) + "/h")}
          ${li("sp", "", "Conseillé pour tenir la semaine", F.pct(five.paceRate, 1) + "/h")}
        </ul>
      </section>`;

    const card7 = `
      <section class="card">
        <div class="card-head"><h2>Semaine (7 jours)</h2>${pill(CU.status(seven.used, seven.pace))}</div>
        ${CU.gauge({
          label: "Semaine",
          rings: [{ r: 118, width: 20, used: seven.used, color: CLAY, markers: [{ v: seven.pace, color: CLAY_INK }] }],
          center: [{ dy: 10, text: big(seven.used), size: 56, serif: true },
                   { dy: 36, text: "utilisés", size: 13, fill: "var(--muted)" }],
          footer: resetText(seven),
        })}
        <ul class="legend">
          ${li("dot", CLAY, "Utilisé", F.pct(seven.used))}
          ${li("tri", CLAY_INK, "Rythme semaine (temps écoulé)", F.pct(seven.pace))}
          ${li("sp", "", "Dépense possible", F.pct(seven.ratePerDay, 1) + " / jour")}
          ${li("sp", "", "Fenêtres 5 h pleines restantes", "≈ " + F.num(seven.sessionsLeft))}
          ${li("sp", "", "Reste", F.pct(seven.remaining))}
        </ul>
      </section>`;

    return `<div class="grid">${card5}${card7}</div>`;
  }

  /* ---------------- vue compacte : un bloc, deux anneaux concentriques ---------------- */
  function compact(m) {
    const { five, seven } = m;
    const svg = CU.gauge({
      label: "Semaine (anneau extérieur) et fenêtre 5 heures (anneau intérieur)",
      rings: [
        { r: 120, width: 16, used: seven.used, color: CLAY, markers: [{ v: seven.pace, color: CLAY_INK, side: "out" }] },
        { r: 92, width: 16, used: five.used, color: BLUE,
          markers: [{ v: five.pace, color: BLUE_INK, side: "in" }, { v: five.budget, color: CLAY_INK, side: "in" }] },
      ],
      center: [
        { dy: -38, text: "5 HEURES", size: 10, fill: "var(--muted)", spacing: "1.2" },
        { dy: -6, text: big(five.used), size: 34, fill: BLUE_INK, serif: true },
        { dy: 20, text: "7 JOURS", size: 10, fill: "var(--muted)", spacing: "1.2" },
        { dy: 52, text: big(seven.used), size: 34, fill: CLAY_INK, serif: true },
      ],
    });
    const st5 = CU.status(five.used, five.pace), st7 = CU.status(seven.used, seven.pace);
    return `
      <section class="card compact">
        <div class="card-head"><h2>Quota</h2><div class="pills">${pill(st5, "5 h · ")}${pill(st7, "7 j · ")}</div></div>
        ${svg}
        <div class="resets">
          <div><span class="dot" style="color:${BLUE}"></span>5 h : ${resetText(five)}</div>
          <div><span class="dot" style="color:${CLAY}"></span>7 j : ${resetText(seven)}</div>
        </div>
        <ul class="legend">
          ${li("tri", BLUE_INK, "Rythme 5 h", F.pct(five.pace))}
          ${li("tri", CLAY_INK, "Limite 5 h au rythme semaine", budgetText(five.budget))}
          ${li("tri", CLAY_INK, "Rythme semaine", F.pct(seven.pace))}
        </ul>
        <div class="stats">
          <div><b>${F.num(five.paceRate)} %</b><span>/h conseillé (5 h)</span></div>
          <div><b>${F.num(seven.ratePerDay)} %</b><span>/jour possible</span></div>
          <div><b>≈ ${F.num(seven.sessionsLeft)}</b><span>fenêtres 5 h</span></div>
        </div>
      </section>`;
  }

  /* ---------------- repartition par produit (deroulant ferme par defaut) ---------------- */
  CU.breakdown = function (m, open) {
    const rows = m.breakdown.filter(r => r.share > 0).sort((a, b) => b.share - a.share);
    if (!rows.length) return "";
    const max = Math.max(...rows.map(r => r.share));
    return `
      <details class="card breakdown"${open ? " open" : ""}>
        <summary><h2>Répartition de la semaine</h2><span class="hint">${rows.length} produits</span></summary>
        <ul class="bars">
          ${rows.map(r => `
            <li>
              <span class="name">${r.name}</span>
              <span class="bar"><span style="width:${(r.share / max * 100).toFixed(1)}%"></span></span>
              <b>${F.pct(r.share)}</b>
              <span class="q">≈ ${F.num(r.quota)} pts du quota</span>
            </li>`).join("")}
        </ul>
        <p class="note">Part de ce que tu as consommé cette semaine (${F.pct(m.seven.used)} du quota) par produit.</p>
      </details>`;
  };

  CU.views = { detail, compact };
})(window.CU);
