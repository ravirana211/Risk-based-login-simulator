"""Build a single-file, backend-free demo of the web app.

The demo swaps the HTTP API for web/mock-api.js (a JavaScript port of the
risk engine and auth service) and bundles CSS, the QR library and the app
into one HTML file that can be hosted anywhere as a static page.

Usage: python scripts/build_web_demo.py OUT.html
"""
from __future__ import annotations

import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"


def swap(src: str, old: str, new: str, count: int = 1) -> str:
    found = src.count(old)
    if found != count:
        raise SystemExit(f"build_web_demo: expected {count} match(es), found {found}:\n{old[:120]}")
    return src.replace(old, new)


def build_app_js() -> str:
    js = (WEB / "app.js").read_text()

    # 1. Talk to the in-browser API instead of the network.
    js = swap(js, """    const r = await fetch(S.apiBase.replace(/\\/$/, "") + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    const text = await r.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch { data = { status: "bad_response", message: "The server sent an unexpected reply." }; }
    return { status: r.status, data };""", """    return await MockAPI.handle(path, { method, headers, body });""")
    js = swap(js, "Can't reach the login service. Check your connection or the API address in Settings.",
              "The demo couldn't start. Check that this browser allows site storage and try again.")

    # 2. "settings" is a reserved page name on the host; route to #options instead.
    js = swap(js, '["settings", "gear", "Settings"]', '["options", "gear", "Settings"]')
    js = swap(js, 'settings: "settings" }', 'options: "options" }')
    js = swap(js, 'href="#settings"', 'href="#options"')
    js = swap(js, "ROUTES.settings = {", "ROUTES.options = {")

    # 3. The host controls the theme and there is no server address to configure.
    start = js.index('      <section class="stack"><h2 class="section-label">Appearance</h2>')
    end = js.index('      <p class="muted tiny" style="text-align:center">RiskLogin 0.1')
    js = js[:start] + """      <section class="stack"><h2 class="section-label">Demo data</h2>
        <div class="card stack">
          <p class="small sub">Everything runs in this browser: the risk engine, accounts, codes and the activity log. Nothing is sent to a server.</p>
          <button class="btn danger block" id="resetData">${icon("refresh")}Reset demo data</button>
        </div></section>
""" + js[end:]
    js = swap(js, '    segs("theme", (v) => { S.theme = v; store.set("theme", v); applyTheme(); });\n', "")
    start = js.index('    $("#test", root).addEventListener("click", async (e) => {')
    end = js.index("  },\n};\n\n/* ============================== boot")
    js = js[:start] + """    $("#resetData", root).addEventListener("click", async () => {
      MockAPI.reset(); clearSession(); store.del("demoSecrets"); S.labRun = null; S.lastCheck = null;
      await checkHealth(); toast("Demo data reset"); go("account");
    });
""" + js[end:]
    js = swap(js, """  if (S.theme === "system") delete r.dataset.theme; else r.dataset.theme = S.theme;""", "  void r;")
    js = swap(js, """  if ("serviceWorker" in navigator && location.protocol !== "file:") navigator.serviceWorker.register("sw.js").catch(() => {});\n""", "")

    # 4. Demo wording and a ready-made account.
    js = swap(js, '"Connected · simulation mode"', '"Demo · runs entirely in your browser"')
    js = swap(js, """        <a class="btn secondary block" href="#signup">Create account</a>
      </div>""", """        <a class="btn secondary block" href="#signup">Create account</a>
      </div>
      <div class="card stack">
        <div class="row-gap"><span class="badge-ic accent">${icon("user")}</span><h2 style="font-size:18px">Try the demo account</h2></div>
        <p class="small sub">Username <b class="mono">${MockAPI.DEMO.username}</b>, password <b class="mono">${MockAPI.DEMO.password}</b>. It has a week of normal sign-ins from London, so the engine has history to compare against.</p>
        <button class="btn outline block" id="useDemo">Sign in as ${MockAPI.DEMO.username}</button>
        <p class="hint">Tip: set the network to Mobile data in Settings first to see a code check.</p>
      </div>""")
    js = swap(js, """ROUTES.account.mount = (root) => {
  _accountMount();""", """ROUTES.account.mount = (root) => {
  _accountMount();
  $("#useDemo", root)?.addEventListener("click", () => { store.set("lastUser", MockAPI.DEMO.username); S.demoPw = MockAPI.DEMO.password; go("signin"); });""")
    js = swap(js, """required minlength="${signup ? 8 : 1}" maxlength="128">""",
              """required minlength="${signup ? 8 : 1}" maxlength="128" value="${!signup && S.demoPw ? esc(S.demoPw) : ""}">""")
    js = swap(js, """  const form = $("#cred", root), u = $("#u", root), p = $("#p", root), msg = $("#formMsg", root);""",
              """  const form = $("#cred", root), u = $("#u", root), p = $("#p", root), msg = $("#formMsg", root);
  S.demoPw = null;""")
    js = swap(js, """placeholder="Attackers in these scenarios already have it">""",
              """placeholder="Attackers in these scenarios already have it" value="${(S.me?.username || store.get("lastUser", "")) === MockAPI.DEMO.username ? esc(MockAPI.DEMO.password) : ""}">""")
    return js


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "risklogin-demo.html")
    css = (WEB / "app.css").read_text()
    qr = (WEB / "vendor" / "qrcode.js").read_text()
    app = build_app_js() + "\n" + (WEB / "mock-api.js").read_text()
    for name, text in (("qrcode.js", qr), ("app.js", app)):
        if "</script" in text.lower():
            raise SystemExit(f"build_web_demo: {name} contains </script")
    out.write_text(f"""<title>RiskLogin</title>
<meta name="description" content="Risk-based sign-in demo: a phone app whose risk engine runs in your browser.">
<style>
{css}
</style>
<div id="app" class="shell" aria-live="polite"></div>
<nav id="tabbar" class="tabbar" aria-label="Main"></nav>
<div id="toast" class="toast" role="status" hidden></div>
<script>
{qr}
</script>
<script>
{app}
</script>
""")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
