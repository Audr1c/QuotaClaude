/* diag.js: if a script fails to load (ad blocker, missing file) or crashes, say so on the page.
   Bilingual on purpose: it must work even when i18n.js itself is the script that failed.
   It is a file of its own (not inline in index.html) so that the page's Content-Security-Policy can forbid inline scripts. */
window.addEventListener("error", function (e) {
  var src = e.target && e.target.src, el = document.getElementById("err");
  if (!el || (src && src.indexOf("latest.js") !== -1)) return;   // no data yet: normal
  el.hidden = false;
  el.textContent = src
    ? "Script blocked or missing / bloqu\u00e9 ou introuvable: " + src
      + " - ad blocker (uBlock...)? Disable it for 127.0.0.1 / d\u00e9sactive-le pour 127.0.0.1."
    : "JavaScript error / Erreur JavaScript: " + e.message + " (" + (e.filename || "") + ":" + (e.lineno || "") + ")";
}, true);
