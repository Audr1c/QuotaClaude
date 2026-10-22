/* model.js: all the pace calculations, no display code.
   Input: the state written by claude_usage.py (data/latest.json). */
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
      used: active ? (w.pct || 0) : 0,               // a window that expired since the reading counts as 0
      left: active ? reset - now : length,            // ms remaining
      pace: active ? clamp((now - (reset - length)) / length * 100) : null, // where usage "should" be
    };
  }

  /* Positive increments only: a drop is a window reset, not negative consumption. Returns null without enough data. */
  function increments(history, key, span, now) {
    const pts = (history || []).map(r => ({ t: Date.parse(r.t), v: r[key] })).filter(p => p.t >= now - span && p.t <= now && p.v != null);
    if (pts.length < 2) return null;
    let sum = 0;
    for (let i = 1; i < pts.length; i++) sum += Math.max(0, pts[i].v - pts[i - 1].v);
    return { sum, hours: (pts[pts.length - 1].t - pts[0].t) / H };
  }
  function recentRate(history, key, span, now, win5) {
    const inc = increments(history, key, span, now);
    if (inc && inc.hours > 0.05) return inc.sum / inc.hours;
    if (win5) {                                       // too few readings: average since the window opened
      const elapsed = (FIVE_H - win5.left) / H;
      if (elapsed > 0.1) return win5.used / elapsed;
    }
    return null;
  }
  function recentUsed(history, key, span, now) {
    const inc = increments(history, key, span, now);
    return inc ? inc.sum : null;
  }

  CU.compute = function (D, now = Date.now(), opts = {}) {
    if (!D || !D.seven_day) return null;
    const ratio = D.ratio_estimate || D.ratio_default;   // % of the week one full 5-hour window costs

    const seven = win(D.seven_day, SEVEN_D, now);
    seven.remaining = 100 - seven.used;
    // Hours of Claude per day (slider): the rest of the week is spread over the hours you actually work,
    // not over every hour of the week. 24 = no assumption (the old behaviour).
    const hours = clamp(opts.hoursPerDay || 24, 1, 24);
    const activeHoursLeft = Math.max(seven.left / H * hours / 24, 0.25);
    seven.ratePerHour = seven.remaining / activeHoursLeft;    // weekly % per hour worked
    seven.ratePerDay = seven.remaining / (seven.left / H / 24); // weekly % per calendar day left
    seven.sessionsLeft = seven.remaining / ratio;

    const five = win(D.five_hour, FIVE_H, now);
    // share of the remaining weekly budget that falls inside this window, converted to % of a 5-hour window
    const weeklyShare = seven.ratePerHour * Math.min(five.left, seven.left) / H;
    five.budget = five.used + weeklyShare * 100 / ratio;
    five.maxRate = (100 - five.used) / (five.left / H);      // 5h-% per hour to end exactly at the reset
    five.paceRate = seven.ratePerHour * 100 / ratio;          // 5h-% per hour at the weekly pace

    seven.activeHoursLeft = activeHoursLeft;
    five.currentRate = recentRate(D.history, "h5", H, now, five.active ? five : null);   // 5h-% per hour, last hour
    seven.usedLast24h = recentUsed(D.history, "d7", 24 * H, now);                       // weekly % consumed over 24 h
    seven.plannedWindows = activeHoursLeft / 5;                                           // 5-hour windows you plan to work

    const fetched = D.fetched_at ? Date.parse(D.fetched_at) : null;
    return {
      five, seven, ratio, hours,
      ratioEstimated: !!D.ratio_estimate,
      ratioPoints: D.ratio_points,
      samples: D.samples,
      fetched: fetched ? new Date(fetched) : null,
      age: fetched ? now - fetched : Infinity,
      error: D.error,
      errorCode: D.error_code,
      history: D.history || [],
      // per-product breakdown: share of what was used, and the equivalent in points of the weekly quota
      breakdown: D.breakdown && D.breakdown.rows
        ? D.breakdown.rows.map(r => ({ name: r.name, share: r.pct || 0, quota: (r.pct || 0) * seven.used / 100 }))
        : [],
    };
  };

  /* ahead of / behind the pace -> {kind, n}; the views turn it into text */
  CU.status = function (used, pace) {
    if (pace == null) return null;
    const d = used - pace;
    if (d > 5) return { kind: "ahead", n: Math.round(d) };
    if (d < -5) return { kind: "margin", n: Math.round(-d) };
    return { kind: "even", n: 0 };
  };
})(window.CU);
