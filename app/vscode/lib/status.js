/* status.js: what the status bar item shows, without any VS Code dependency (tested with node, see test_vscode.py).
   cu = the widget's CU object (web/js/i18n.js loaded), for the texts and number formats in both languages. */
"use strict";

const H = 3600e3;

/* three cells, filled by thirds: ▱▱▱ 0 %, ▰▱▱ up to 33 %, ▰▰▱ up to 66 %, ▰▰▰ above */
function bars(pct, cells = 3) {
  const n = pct == null ? 0 : Math.min(cells, Math.ceil(Math.max(0, pct) / 100 * cells - 1e-9));
  return "▰".repeat(n) + "▱".repeat(cells - n);
}

function windowOf(w, length, now) {
  const reset = w && w.resets_at ? Date.parse(w.resets_at) : null;
  const active = reset != null && reset > now;
  return { active, used: active ? (w.pct || 0) : 0, reset: active ? reset : null,
           pace: active ? Math.min(100, Math.max(0, (now - (reset - length)) / length * 100)) : null };
}

function summary(state, now, opts = {}) {
  if (!state || !state.seven_day) return null;
  const five = windowOf(state.five_hour, 5 * H, now), seven = windowOf(state.seven_day, 7 * 24 * H, now);
  const fetched = state.fetched_at ? Date.parse(state.fetched_at) : null;
  const age = fetched ? now - fetched : Infinity;
  const top = Math.max(five.used, seven.used);
  const level = age > 30 * 60e3 ? "stale" : top >= (opts.errorAt || 95) ? "error" : top >= (opts.warnAt || 80) ? "warning" : "ok";
  return { five, seven, age, level, error: state.error || null, samples: state.samples };
}

function text(s, cu, template = "{b5} {p5} · {b7} {p7}") {
  if (!s) return "Claude —";
  const p = v => cu.fmt.pct(v);
  return template.replace("{b5}", bars(s.five.used)).replace("{p5}", p(s.five.used))
    .replace("{b7}", bars(s.seven.used)).replace("{p7}", p(s.seven.used));
}

/* Markdown for the tooltip: a little more than the bar, never everything */
function tooltip(s, cu, now = Date.now()) {
  if (!s) return cu.t("empty").replace(/<[^>]+>/g, " ");
  const line = (label, w) => `**${label}** ${cu.fmt.pct(w.used)}` + (w.pace != null ? ` · ${cu.t("strip.pace", { n: cu.fmt.pct(w.pace) })}` : "")
    + `  \n${w.active ? cu.t("reset.in", { left: cu.fmt.left(w.reset - now), when: cu.fmt.when(new Date(w.reset)) }) : cu.t("reset.none")}`;
  const out = [line(cu.t("card.five"), s.five), line(cu.t("card.seven"), s.seven),
    isFinite(s.age) ? cu.t("meta.updated", { ago: cu.fmt.left(s.age), n: s.samples }) : ""];
  if (s.error) out.push("⚠ " + s.error);
  out.push(`_${cu.t("vsc.click")}_`);
  return out.filter(Boolean).join("\n\n");
}

module.exports = { bars, summary, text, tooltip };
