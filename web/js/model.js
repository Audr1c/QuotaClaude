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

  /* weekly % used at a given moment (last reading before it; the oldest reading when the history starts later) */
  function usedAt(history, ts, current) {
    const pts = (history || []).map(r => ({ t: Date.parse(r.t), v: r.d7 })).filter(p => p.v != null && !isNaN(p.t));
    if (!pts.length) return current;
    let p = pts[0];
    for (const q of pts) if (q.t <= ts) p = q;
    return p.v > current ? 0 : p.v;                // a higher value means the week reset since: start from 0
  }

  CU.compute = function (D, now = Date.now(), opts = {}) {
    if (!D || !D.seven_day) return null;
    const ratio = D.ratio_estimate || D.ratio_default;   // % of the week one full 5-hour window costs

    const seven = win(D.seven_day, SEVEN_D, now);
    seven.remaining = 100 - seven.used;
    // Hours of Claude per day (slider): the rest of the week is spread over the hours you actually work,
    // not over every hour of the week. 24 = no assumption (the old behaviour).
    const hours = clamp(opts.hoursPerDay || 24, 1, 24);
    seven.sessionsLeft = seven.remaining / ratio;

    // Daily budget (like a data-plan app): what was left of the week when today began, split over the days
    // until the reset. Staying below `limit` = still inside today's budget.
    const dayStart = new Date(now); dayStart.setHours(0, 0, 0, 0);
    const startUsed = usedAt(D.history, dayStart.getTime(), seven.used);
    const daysLeft = seven.active ? Math.max((seven.reset.getTime() - dayStart.getTime()) / (24 * H), 0.25) : 1;
    seven.dailyBudget = (100 - startUsed) / daysLeft;                 // weekly % per day
    seven.limit = seven.active ? clamp(startUsed + seven.dailyBudget) : null;   // cumulative weekly % allowed by now
    seven.todayUsed = Math.max(0, seven.used - startUsed);
    seven.todayLeft = seven.limit == null ? 0 : Math.max(0, seven.limit - seven.used);
    seven.ratePerDay = seven.dailyBudget;
    seven.ratePerHour = seven.dailyBudget / hours;                    // spread over the hours you work (slider)

    const five = win(D.five_hour, FIVE_H, now);
    // today's remaining budget expressed in % of a 5-hour window: the 5-hour usage you can reach and still be on budget
    five.limit = five.active && seven.limit != null ? Math.min(100, five.used + seven.todayLeft * 100 / ratio) : null;
    five.maxRate = (100 - five.used) / (five.left / H);      // 5h-% per hour to end exactly at the reset
    five.paceRate = seven.ratePerHour * 100 / ratio;          // 5h-% per hour at the weekly pace


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
