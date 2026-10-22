/* model.js : tous les calculs de rythme, sans aucun affichage.
   Entree : l'etat ecrit par claude_usage.py (data/latest.json). */
window.CU = window.CU || {};

(function (CU) {
  const H = 3600e3, FIVE_H = 5 * H, SEVEN_D = 7 * 24 * H;
  const clamp = (v, a = 0, b = 100) => Math.min(b, Math.max(a, v));

  function win(w, length, now) {
    const reset = w && w.resets_at ? Date.parse(w.resets_at) : null;
    const active = !!reset && reset > now;
    return {
      active,
      reset: active ? new Date(reset) : null,
      used: active ? (w.pct || 0) : 0,               // fenetre expiree depuis le releve = repartie a 0
      left: active ? reset - now : length,            // ms restantes
      pace: active ? clamp((now - (reset - length)) / length * 100) : null, // ou "devrait" etre l'usage
    };
  }

  CU.compute = function (D, now = Date.now()) {
    if (!D || !D.seven_day) return null;
    const ratio = D.ratio_estimate || D.ratio_default;   // % hebdo pour une fenetre 5 h pleine

    const seven = win(D.seven_day, SEVEN_D, now);
    seven.remaining = 100 - seven.used;
    seven.ratePerHour = seven.remaining / (seven.left / H);   // % hebdo / heure
    seven.ratePerDay = seven.ratePerHour * 24;
    seven.sessionsLeft = seven.remaining / ratio;

    const five = win(D.five_hour, FIVE_H, now);
    // part du reste hebdo qui revient a la fin de cette fenetre, convertie en % de fenetre 5 h
    const weeklyShare = seven.ratePerHour * Math.min(five.left, seven.left) / H;
    five.budget = five.used + weeklyShare * 100 / ratio;
    five.maxRate = (100 - five.used) / (five.left / H);      // %5h/h pour finir pile au reset
    five.paceRate = seven.ratePerHour * 100 / ratio;          // %5h/h au rythme de la semaine

    const fetched = D.fetched_at ? Date.parse(D.fetched_at) : null;
    return {
      five, seven, ratio,
      ratioEstimated: !!D.ratio_estimate,
      ratioPoints: D.ratio_points,
      samples: D.samples,
      fetched: fetched ? new Date(fetched) : null,
      age: fetched ? now - fetched : Infinity,
      error: D.error,
      history: D.history || [],
      // repartition par produit : part de ce qui a ete consomme, et equivalent en points du quota hebdo
      breakdown: D.breakdown && D.breakdown.rows
        ? D.breakdown.rows.map(r => ({ name: r.name, share: r.pct || 0, quota: (r.pct || 0) * seven.used / 100 }))
        : [],
    };
  };

  /* --- formatage partage --- */
  CU.fmt = {
    pct(v, d = 0) { return v == null || !isFinite(v) ? "—" : v.toFixed(d).replace(".", ",") + " %"; },
    num(v, d = 1) { return v == null || !isFinite(v) ? "—" : v.toFixed(d).replace(".", ","); },
    left(ms) {
      if (ms <= 0) return "maintenant";
      const m = Math.round(ms / 60e3), j = Math.floor(m / 1440), h = Math.floor(m % 1440 / 60), mm = m % 60;
      if (j) return `${j} j ${h} h`;
      if (h) return `${h} h ${String(mm).padStart(2, "0")}`;
      return `${mm} min`;
    },
    when(d) { return d.toLocaleString("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit" }); },
  };

  /* avance / retard par rapport au rythme */
  CU.status = function (used, pace) {
    if (pace == null) return null;
    const d = used - pace;
    if (d > 5) return { kind: "ahead", text: `En avance de ${Math.round(d)} pts` };
    if (d < -5) return { kind: "margin", text: `Marge de ${Math.round(-d)} pts` };
    return { kind: "even", text: "Dans le rythme" };
  };
})(window.CU);
