/* theme.js: custom colours and font (THM-1). The palette is made of CSS variables on :root (style.css); a theme only
   overrides some of them, separately for the light and the dark mode. Format (shared with the other clients through
   /api/v1/config, validated by settings.py):  { name, preset, light: {five, seven, ok, bad}, dark: {...}, font }
   Colours are #rrggbb only and fonts come from a fixed list of system fonts: an imported theme cannot inject anything. */
window.CU = window.CU || {};

(function (CU) {
  const KEYS = ["five", "seven", "ok", "bad"];
  const VARS = { five: "--blue", seven: "--clay", ok: "--ok", bad: "--bad" };
  const INK = { five: "--blue-ink", seven: "--clay-ink" };             // markers and figures: a darker / lighter shade
  const PRESETS = {
    claude: { light: {}, dark: {} },
    contrast: { light: { five: "#1f5fa8", seven: "#a8380f", ok: "#2e7d32", bad: "#b00020" },
                dark: { five: "#9cc7f0", seven: "#ffab85", ok: "#9cd67e", bad: "#ff8a80" } },
    // no green / red pair (Okabe-Ito colours): the zones are blue (inside the budget) and vermilion (over it)
    colorblind: { light: { five: "#56b4e9", seven: "#e69f00", ok: "#0072b2", bad: "#d55e00" },
                  dark: { five: "#56b4e9", seven: "#e69f00", ok: "#3d9ae0", bad: "#ff7a2e" } },
    mono: { light: { five: "#6b6b6b", seven: "#2b2b2b", ok: "#a6a6a6", bad: "#111111" },
            dark: { five: "#9a9a9a", seven: "#e8e8e8", ok: "#6f6f6f", bad: "#ffffff" } },
  };
  const FONTS = {
    default: null,
    sans: { sans: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif', serif: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif' },
    serif: { sans: 'Georgia, "Times New Roman", serif', serif: 'Georgia, "Times New Roman", serif' },
    mono: { sans: 'ui-monospace, "Cascadia Mono", "SF Mono", Consolas, monospace', serif: 'ui-monospace, "Cascadia Mono", "SF Mono", Consolas, monospace' },
  };
  const HEX = /^#[0-9a-f]{6}$/i;
  const DEFAULT = { preset: "claude", light: {}, dark: {}, font: "default" };

  /* keep only what the format allows (same rules as settings.py) */
  function clean(th) {
    const out = { preset: PRESETS[th && th.preset] ? th.preset : "claude", light: {}, dark: {}, font: FONTS.hasOwnProperty(th && th.font) ? th.font : "default" };
    for (const mode of ["light", "dark"]) for (const k of KEYS) {
      const c = th && th[mode] && th[mode][k];
      if (typeof c === "string" && HEX.test(c)) out[mode][k] = c.toLowerCase();
    }
    if (th && typeof th.name === "string" && /^[\w .,'()-]{0,40}$/.test(th.name) && th.name) out.name = th.name;
    return out;
  }

  const mode = () => {
    const forced = document.documentElement.dataset.theme;
    if (forced === "light" || forced === "dark") return forced;
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };
  /* mix a colour with black (light mode) or white (dark mode) for the "ink" shade */
  function shade(hex, m) {
    const n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255], to = m === "dark" ? 255 : 0, k = 0.3;
    return "#" + c.map(v => Math.round(v + (to - v) * k).toString(16).padStart(2, "0")).join("");
  }
  /* WCAG contrast ratio of two #rrggbb colours */
  CU.contrast = function (a, b) {
    const L = h => { const n = parseInt(h.slice(1), 16);
      const ch = [n >> 16, (n >> 8) & 255, n & 255].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
      return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]; };
    const [x, y] = [L(a), L(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };

  let current = clean(null);
  /* the colours in effect for a mode: the preset, then the user's own */
  CU.themeColors = (th, m) => Object.assign({}, PRESETS[th.preset][m], th[m]);
  CU.defaultColor = function (k) {                                     // the stylesheet's own value, for the colour inputs
    const st = document.documentElement.style, v = VARS[k], keep = st.getPropertyValue(v);
    st.removeProperty(v);
    const c = getComputedStyle(document.documentElement).getPropertyValue(v).trim();
    if (keep) st.setProperty(v, keep);
    return HEX.test(c) ? c.toLowerCase() : "#888888";
  };

  CU.applyTheme = function (th) {
    current = clean(th);
    const st = document.documentElement.style, m = mode(), colors = CU.themeColors(current, m);
    for (const k of KEYS) {
      if (colors[k]) { st.setProperty(VARS[k], colors[k]); if (INK[k]) st.setProperty(INK[k], shade(colors[k], m)); }
      else { st.removeProperty(VARS[k]); if (INK[k]) st.removeProperty(INK[k]); }
    }
    const font = FONTS[current.font];
    if (font) { st.setProperty("--sans", font.sans); st.setProperty("--serif", font.serif); }
    else { st.removeProperty("--sans"); st.removeProperty("--serif"); }
    try { localStorage.setItem("cu.theme", JSON.stringify(current)); } catch (e) { /* ignore */ }
    return current;
  };
  CU.theme = () => current;
  CU.themeClean = clean;
  CU.themePresets = Object.keys(PRESETS);
  CU.themeFonts = Object.keys(FONTS);
  CU.themeKeys = KEYS;
  CU.themeMode = mode;

  // the saved theme, before the first render (the server copy, if any, comes later through app.js)
  try { CU.applyTheme(JSON.parse(localStorage.getItem("cu.theme")) || DEFAULT); } catch (e) { CU.applyTheme(DEFAULT); }
  if (window.matchMedia) {
    const mq = matchMedia("(prefers-color-scheme: dark)");
    (mq.addEventListener ? mq.addEventListener.bind(mq, "change") : mq.addListener.bind(mq))(() => CU.applyTheme(current));
  }
})(window.CU);

/* the theme panel (a side dialog opened from the header): presets, one colour input per role for the mode being
   edited (the page previews that mode while the panel is open), font, reset, export / import as JSON text. */
(function (CU) {
  const t = (k, v) => CU.t(k, v), $ = id => document.getElementById(id);
  const esc = x => String(x).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  let editing = null, before = null, onChange = () => {};

  function draw() {
    const th = CU.theme(), m = editing, colors = CU.themeColors(th, m);
    const card = getComputedStyle(document.documentElement).getPropertyValue("--card").trim();
    const seg = (name, items, cur, label) => `<div class="seg" role="group" aria-label="${label}">${items.map(v =>
      `<button type="button" data-${name}="${v}" aria-pressed="${v === cur}">${t(`theme.${name}.${v}`)}</button>`).join("")}</div>`;
    const rows = CU.themeKeys.map(k => {
      const c = colors[k] || CU.defaultColor(k), low = /^#[0-9a-f]{6}$/i.test(card) && CU.contrast(c, card) < 3;
      return `<label class="trow"><span class="dot" style="color:${c}"></span><span>${t("theme.c." + k)}</span>
        <input type="color" data-color="${k}" value="${c}">${low ? `<small class="warn">${t("theme.low", { n: CU.fmt.num(CU.contrast(c, card), 1) })}</small>` : ""}</label>`;
    }).join("");
    $("theme-body").innerHTML = `
      <h3 class="sub">${t("theme.presets")}</h3>${seg("preset", CU.themePresets, th.preset, t("theme.presets"))}
      <h3 class="sub">${t("theme.colors")}</h3>${seg("mode", ["light", "dark"], m, t("theme.colors"))}
      <div class="trows">${rows}</div>
      <h3 class="sub">${t("theme.font")}</h3>${seg("font", CU.themeFonts, th.font, t("theme.font"))}
      <p><button type="button" class="btn" id="theme-reset">${t("theme.reset")}</button></p>
      <h3 class="sub">${t("theme.share")}</h3>
      <textarea id="theme-json" rows="5" spellcheck="false" aria-label="${t("theme.share")}">${esc(JSON.stringify(th))}</textarea>
      <p class="tbtns"><button type="button" class="btn" id="theme-copy">${t("theme.copy")}</button>
        <button type="button" class="btn" id="theme-import">${t("theme.import")}</button> <span id="theme-msg" class="hint" role="status"></span></p>
      <p class="lead">${t("theme.note")}</p>`;
  }
  function set(th) { CU.applyTheme(th); onChange(CU.theme()); draw(); }

  CU.themePanel = function (dialog, changed) {
    onChange = changed || onChange;
    dialog.addEventListener("click", e => {
      const b = e.target.closest("button");
      if (!b) { if (e.target === dialog) dialog.close(); return; }
      const th = JSON.parse(JSON.stringify(CU.theme()));
      if (b.dataset.preset) set(Object.assign(th, { preset: b.dataset.preset, light: {}, dark: {} }));
      else if (b.dataset.mode) { editing = b.dataset.mode; document.documentElement.dataset.theme = editing; CU.applyTheme(th); draw(); }
      else if (b.dataset.font) set(Object.assign(th, { font: b.dataset.font }));
      else if (b.id === "theme-reset") set({});
      else if (b.id === "theme-copy") {
        const ta = $("theme-json"); ta.select();
        (navigator.clipboard ? navigator.clipboard.writeText(ta.value) : Promise.reject()).then(
          () => { $("theme-msg").textContent = t("theme.copied"); }, () => { document.execCommand && document.execCommand("copy"); $("theme-msg").textContent = t("theme.copied"); });
      } else if (b.id === "theme-import") {
        let parsed = null;
        try { parsed = JSON.parse($("theme-json").value); } catch (err) { /* reported below */ }
        if (!parsed || typeof parsed !== "object") { $("theme-msg").textContent = t("theme.bad"); return; }
        set(CU.themeClean(parsed));
        $("theme-msg").textContent = t("theme.imported");
      } else if (b.id === "theme-close") dialog.close();
    });
    dialog.addEventListener("input", e => {
      const k = e.target.dataset && e.target.dataset.color;
      if (!k) return;
      const th = JSON.parse(JSON.stringify(CU.theme()));
      th[editing] = Object.assign({}, th[editing], { [k]: e.target.value });
      CU.applyTheme(th); onChange(CU.theme());
      e.target.closest(".trow").querySelector(".dot").style.color = e.target.value;
    });
    dialog.addEventListener("change", e => { if (e.target.dataset && e.target.dataset.color) draw(); });   // contrast warnings
    dialog.addEventListener("close", () => {          // back to the mode the system asks for
      if (before == null) delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = before;
      CU.applyTheme(CU.theme());
    });
    return function open() {
      before = document.documentElement.dataset.theme || null;
      editing = CU.themeMode();
      draw();
      dialog.showModal ? dialog.showModal() : dialog.setAttribute("open", "");
    };
  };
})(window.CU);
