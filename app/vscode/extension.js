/* extension.js: Claude Usage for VS Code (VSC-1). It only reads what the tracker already collected (same storage as
   the widget): data/latest.json on this machine, or /api/v1/latest of the tracker's server. It never sees the Claude
   token and never calls Anthropic.
     - status bar (bottom right): two small bars with the 5-hour and weekly %, coloured by thresholds, dimmed when old;
       hover: resets, pace, age of the reading; click: the side view;
     - side view: the widget's own components (web/js), at the compactness level that fits the width of the view. */
"use strict";
const vscode = require("vscode");
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const vm = require("vm");
const status = require("./lib/status");

function cfg() { return vscode.workspace.getConfiguration("claudeUsage"); }
function appFolder() { return cfg().get("appFolder") || path.resolve(__dirname, ".."); }

/* the widget's texts and formats (web/js/i18n.js), in a sandbox: no globals in the extension host */
function loadTexts(lang) {
  const sandbox = { window: {}, localStorage: { getItem() { return null; }, setItem() {} }, navigator: { language: lang },
    location: { search: "" }, document: { documentElement: {}, querySelectorAll() { return []; } }, URLSearchParams };
  sandbox.window = sandbox;
  vm.runInNewContext(fs.readFileSync(path.join(appFolder(), "web", "js", "i18n.js"), "utf8"), sandbox);
  sandbox.CU.setLang(lang);
  return sandbox.CU;
}

function readState() {
  if (cfg().get("source") === "api") {
    const url = cfg().get("apiUrl").replace(/\/+$/, "") + "/api/v1/latest";
    const lib = url.startsWith("https:") ? https : http;
    return new Promise(resolve => {
      const req = lib.get(url, { timeout: 5000 }, res => {
        let body = "";
        res.on("data", c => { body += c; if (body.length > 8e6) req.destroy(); });
        res.on("end", () => { try { resolve(res.statusCode === 200 ? JSON.parse(body) : null); } catch (e) { resolve(null); } });
      });
      req.on("error", () => resolve(null));
      req.on("timeout", () => req.destroy());
    });
  }
  return fs.promises.readFile(path.join(appFolder(), "data", "latest.json"), "utf8").then(JSON.parse).catch(() => null);
}

class View {
  constructor(ctx) { this.ctx = ctx; this.view = null; }
  resolveWebviewView(view) {
    this.view = view;
    const web = vscode.Uri.file(path.join(appFolder(), "web")), media = vscode.Uri.file(path.join(__dirname, "media"));
    view.webview.options = { enableScripts: true, localResourceRoots: [web, media] };
    const w = rel => view.webview.asWebviewUri(vscode.Uri.joinPath(web, rel));
    const m = rel => view.webview.asWebviewUri(vscode.Uri.joinPath(media, rel));
    const src = view.webview.cspSource;
    view.webview.html = `<!doctype html><html><head><meta charset="utf-8">
      <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${src} data:; style-src ${src} 'unsafe-inline'; script-src ${src};">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <link rel="stylesheet" href="${w("css/style.css")}"><link rel="stylesheet" href="${m("vscode.css")}"></head>
      <body><main id="app"></main>
      ${["js/i18n.js", "js/model.js", "js/gauge.js", "js/views.js", "js/charts.js"].map(f => `<script src="${w(f)}"></script>`).join("")}
      <script src="${m("view.js")}"></script></body></html>`;
    view.webview.onDidReceiveMessage(msg => { if (msg && msg.ready) this.ctx.update(); });
    view.onDidChangeVisibility(() => view.visible && this.ctx.update());
  }
  post(state, lang) { if (this.view && this.view.visible) this.view.webview.postMessage({ state, lang }); }
}

function activate(context) {
  const lang = (vscode.env.language || "en").toLowerCase().startsWith("fr") ? "fr" : "en";
  let cu = null;
  try { cu = loadTexts(lang); } catch (e) { /* app folder not found: shown in the status bar */ }
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  item.command = "claudeUsage.focus";
  item.name = "Claude Usage";
  item.show();
  let last = null;
  const ctx = { update: () => {} };
  const view = new View(ctx);

  async function update() {
    if (!cu) {
      item.text = "$(warning) Claude";
      item.tooltip = "Claude Usage: set claudeUsage.appFolder to the tracker's app folder (the one with run.py).";
      return;
    }
    const state = await readState();
    last = state || last;
    const c = cfg(), s = status.summary(last, Date.now(), { warnAt: c.get("warnAt"), errorAt: c.get("errorAt") });
    item.text = status.text(s, cu, c.get("template"));
    const md = new vscode.MarkdownString(status.tooltip(s, cu));
    md.supportThemeIcons = false;
    item.tooltip = md;
    item.backgroundColor = s && s.level === "error" ? new vscode.ThemeColor("statusBarItem.errorBackground")
      : s && s.level === "warning" ? new vscode.ThemeColor("statusBarItem.warningBackground") : undefined;
    item.color = s && s.level === "stale" ? new vscode.ThemeColor("disabledForeground") : undefined;
    view.post(last, lang);
  }
  ctx.update = update;

  context.subscriptions.push(item,
    vscode.window.registerWebviewViewProvider("claudeUsage.view", view, { webviewOptions: { retainContextWhenHidden: false } }),
    vscode.commands.registerCommand("claudeUsage.focus", () => vscode.commands.executeCommand("claudeUsage.view.focus")),
    vscode.commands.registerCommand("claudeUsage.openWidget", () => vscode.env.openExternal(vscode.Uri.parse(cfg().get("apiUrl") + "/"))),
    vscode.commands.registerCommand("claudeUsage.reload", update),
    vscode.workspace.onDidChangeConfiguration(e => { if (e.affectsConfiguration("claudeUsage")) { try { cu = loadTexts(lang); } catch (err) { cu = null; } update(); } }));

  // the poller rewrites latest.json atomically (rename): watch the folder, not the file
  let timer = null;
  try {
    const watcher = fs.watch(path.join(appFolder(), "data"), (ev, name) => {
      if (name && name !== "latest.json") return;
      clearTimeout(timer); timer = setTimeout(update, 300);
    });
    context.subscriptions.push({ dispose: () => watcher.close() });
  } catch (e) { /* no data folder yet, or source = api: the interval below is enough */ }
  const every = setInterval(update, Math.max(5, cfg().get("intervalSeconds") || 30) * 1000);
  context.subscriptions.push({ dispose: () => clearInterval(every) });
  update();
}

function deactivate() {}

module.exports = { activate, deactivate };
