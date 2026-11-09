/* RiskLogin web app — vanilla JS, no build step.
   Screens: account (welcome / home), signin, signup, enroll, verify, activity, lab, settings. */
"use strict";

/* ============================== storage ============================== */
const store = {
  get(k, d = null) { try { const v = localStorage.getItem("rl." + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("rl." + k, JSON.stringify(v)); } catch {} },
  del(k) { try { localStorage.removeItem("rl." + k); } catch {} },
};

/* ============================== icons ============================== */
const ICONS = {
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
  home: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
  lab: '<path d="M9 3h6M10 3v6L4.5 18.5A2 2 0 006.2 21h11.6a2 2 0 001.7-2.5L14 9V3"/><path d="M7 15h10"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  key: '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3L21 2M16 7l3 3M14 9l2 2"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 018 0v4"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M3 3l18 18M10.6 10.6a3 3 0 004.2 4.2M9.9 5.2A10.8 10.8 0 0112 5c6.4 0 10 7 10 7a17.6 17.6 0 01-3.2 4.2M6.6 6.6C3.9 8.4 2 12 2 12s3.6 7 10 7a10.6 10.6 0 005.4-1.4"/>',
  back: '<path d="M15 18l-6-6 6-6"/>',
  chev: '<path d="M9 18l6-6-6-6"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 01-1-1V4a1 1 0 011-1h10a1 1 0 011 1v1"/>',
  device: '<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 010 18M12 3a14 14 0 000 18"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  wifi: '<path d="M2 8.8a15 15 0 0120 0M5 12.6a10 10 0 0114 0M8.5 16.3a5 5 0 017 0M12 20h.01"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 14h.01M15 14h.01"/>',
  plane: '<path d="M10.2 13.8L3 11l1.5-1.5 8 1 4.3-4.3a2 2 0 012.8 2.8l-4.3 4.3 1 8L14.8 23l-2.8-7.2-3.3 3.3V22l-1.5-1.5-1.5-3.5-3.5-1.5L1 14h2.9z"/>',
  moon: '<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/>',
  pin: '<path d="M12 21s-7-6.3-7-12a7 7 0 0114 0c0 5.7-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  spray: '<path d="M4 20l6-6M14 4h6v6M20 4l-7 7"/><circle cx="7" cy="7" r="1"/><circle cx="4" cy="11" r="1"/><circle cx="11" cy="4" r="1"/>',
  hammer: '<path d="M15 12l-8.5 8.5a2.1 2.1 0 01-3-3L12 9"/><path d="M17.6 6.4L20 4M13 4l7 7-3 3-7-7z"/>',
  refresh: '<path d="M21 12a9 9 0 01-15.5 6.2L3 16M3 12a9 9 0 0115.5-6.2L21 8M21 3v5h-5M3 21v-5h5"/>',
  logout: '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0116 0"/>',
};
const icon = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ""}</svg>`;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ============================== world data (matches risksim/generator.py) ============================== */
const CITIES = [
  ["New York", "US", 40.71, -74.01], ["San Francisco", "US", 37.77, -122.42], ["Chicago", "US", 41.88, -87.63],
  ["Toronto", "CA", 43.65, -79.38], ["Mexico City", "MX", 19.43, -99.13], ["Sao Paulo", "BR", -23.55, -46.63],
  ["London", "GB", 51.51, -0.13], ["Amsterdam", "NL", 52.37, 4.90], ["Berlin", "DE", 52.52, 13.40],
  ["Paris", "FR", 48.86, 2.35], ["Lagos", "NG", 6.52, 3.38], ["Moscow", "RU", 55.76, 37.62],
  ["Dubai", "AE", 25.20, 55.27], ["Mumbai", "IN", 19.08, 72.88], ["Bangalore", "IN", 12.97, 77.59],
  ["Singapore", "SG", 1.35, 103.82], ["Jakarta", "ID", -6.21, 106.85], ["Seoul", "KR", 37.57, 126.98],
  ["Tokyo", "JP", 35.68, 139.69], ["Sydney", "AU", -33.87, 151.21],
].map(([city, country, lat, lon]) => ({ city, country, lat, lon }));
const COUNTRIES = [...new Set(CITIES.map((c) => c.country))].sort();
const resiAsn = (country, k = 0) => 60000 + COUNTRIES.indexOf(country) * 10 + k;
const cityByName = (n) => CITIES.find((c) => c.city === n) || CITIES[6];
const ipFor = (seed, k) => `${80 + (seed % 120)}.${(seed * 7 + k * 13) % 250}.${(seed * 3 + k) % 250}.${10 + k}`;
function km(a, b) {
  const r = (d) => (d * Math.PI) / 180, dl = r(b.lat - a.lat), dn = r(b.lon - a.lon);
  const h = Math.sin(dl / 2) ** 2 + Math.cos(r(a.lat)) * Math.cos(r(b.lat)) * Math.sin(dn / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}
const randHex = (n) => Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => b.toString(16).padStart(2, "0")).join("");

const RULES = {
  new_device: "New device", known_device: "Known device", asn_hosting: "Datacenter or VPN network",
  asn_tor: "Tor network", asn_new: "Network not seen before", country_new: "New country",
  impossible_travel: "Impossible travel", acct_failures: "Recent failed passwords",
  acct_failures_heavy: "Many failed passwords", ip_spray: "One IP trying many accounts",
  headless: "Automated browser", odd_hour: "Unusual time of day",
};
const NETWORK_LABEL = { residential: "Home or office network", mobile: "Mobile data", hosting: "Datacenter or VPN", tor: "Tor" };

/* ============================== app state ============================== */
const S = {
  apiBase: store.get("apiBase", "/api"),
  health: null, // {status, sim_mode} or null when unreachable
  token: store.get("token"),
  me: null,
  device: store.get("device"),
  location: store.get("location", "London"),
  network: store.get("network", "home"), // home | mobile | vpn
  theme: store.get("theme", "system"),
  lastCheck: store.get("lastCheck"), // risk info of the sign-in behind this session
  pending: null, // {challenge_id, expires_at, risk, username}
  enroll: null, // {username, secret, uri}
  flash: null,
  labRun: null,
  labScenario: store.get("labScenario", "impossible_travel"),
};

/* ============================== device id ============================== */
async function ensureDevice() {
  if (S.device) return S.device;
  const seed = [navigator.userAgent, navigator.language, Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen.width + "x" + screen.height, devicePixelRatio, randHex(8)].join("|");
  let id = "web-" + randHex(10);
  if (crypto.subtle) {
    const h = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(seed)));
    id = "web-" + Array.from(h.slice(0, 10), (b) => b.toString(16).padStart(2, "0")).join("");
  }
  S.device = id; store.set("device", id);
  return id;
}
const deviceInfo = () => ({ id: S.device, headless: !!navigator.webdriver });

/* ============================== TOTP (demo authenticator) ============================== */
function b32decode(s) {
  const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; let bits = "", out = [];
  for (const ch of s.replace(/=+$/, "").toUpperCase()) { const v = A.indexOf(ch); if (v >= 0) bits += v.toString(2).padStart(5, "0"); }
  for (let i = 0; i + 8 <= bits.length; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2));
  return new Uint8Array(out);
}
async function totp(secret, t = Date.now()) {
  if (!crypto.subtle) return null;
  const counter = Math.floor(t / 1000 / 30), msg = new Uint8Array(8);
  new DataView(msg.buffer).setUint32(4, counter);
  new DataView(msg.buffer).setUint32(0, Math.floor(counter / 2 ** 32));
  const key = await crypto.subtle.importKey("raw", b32decode(secret), { name: "HMAC", hash: "SHA-1" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, msg));
  const o = sig[19] & 15;
  const n = (((sig[o] & 127) << 24) | (sig[o + 1] << 16) | (sig[o + 2] << 8) | sig[o + 3]) % 1e6;
  return String(n).padStart(6, "0");
}
const demoSecrets = () => store.get("demoSecrets", {});

/* ============================== API ============================== */
function simContext(overrides = {}) {
  const c = cityByName(S.location), idx = CITIES.indexOf(c);
  let ctx = { ip: ipFor(idx + 1, 1), asn: resiAsn(c.country, 0), asn_type: "residential", ...c, label: "good" };
  if (S.network === "mobile") ctx = { ...ctx, ip: ipFor(idx + 1, 2), asn: resiAsn(c.country, 9), asn_type: "mobile" };
  if (S.network === "vpn") {
    const exit = c.city === "Amsterdam" ? cityByName("London") : cityByName("Amsterdam");
    ctx = { ...ctx, ...exit, ip: "185.156.46.20", asn: 9009, asn_type: "hosting" };
  }
  return { ...ctx, ...overrides };
}
async function api(path, { method = "GET", body, sim, auth } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && S.token) headers.Authorization = "Bearer " + S.token;
  if (sim && S.health?.sim_mode) headers["X-Sim-Context"] = JSON.stringify(sim === true ? simContext() : sim);
  try {
    const r = await fetch(S.apiBase.replace(/\/$/, "") + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    const text = await r.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch { data = { status: "bad_response", message: "The server sent an unexpected reply." }; }
    return { status: r.status, data };
  } catch {
    return { status: 0, data: { status: "offline", message: "Can't reach the login service. Check your connection or the API address in Settings." } };
  }
}
async function checkHealth() {
  const r = await api("/health");
  S.health = r.status === 200 ? r.data : null;
  return S.health;
}
function errorText(r) {
  if (r.status === 422) return "Check the details and try again.";
  return r.data?.message || "Something went wrong. Try again.";
}

/* ============================== session ============================== */
function setSession(token, username, check) {
  S.token = token; store.set("token", token);
  S.me = { username };
  S.lastCheck = check ? { ...check, at: new Date().toISOString(), username } : null;
  store.set("lastCheck", S.lastCheck);
}
async function loadMe() {
  if (!S.token) { S.me = null; return; }
  const r = await api("/me", { auth: true });
  if (r.status === 200) S.me = r.data;
  else if (r.status === 401) { clearSession(); }
}
function clearSession() { S.token = null; S.me = null; store.del("token"); }

/* ============================== UI helpers ============================== */
let toastTimer;
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.hidden = true), 2600);
}
async function copy(text, label = "Copied") {
  try { await navigator.clipboard.writeText(text); toast(label); }
  catch { toast("Couldn't copy. Select the text and copy it instead."); }
}
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
function busy(btn, on, label) {
  if (!btn) return;
  if (on) { btn.dataset.label = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spinner" aria-hidden="true"></span>${esc(label || "Working…")}`; }
  else { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
}
function bar({ title = "", back = null, action = "" } = {}) {
  return `<header class="bar">
    ${back ? `<a class="icon-btn" href="#${back}" aria-label="Back">${icon("back")}</a>` : "<span></span>"}
    <span class="bar-title">${esc(title)}</span>${action || "<span></span>"}</header>`;
}
function alertBox(kind, title, text) {
  const ic = { crit: "alert", warn: "alert", good: "check", info: "info" }[kind];
  return `<div class="alert ${kind}" role="${kind === "crit" ? "alert" : "status"}">${icon(ic)}<div>${title ? `<b>${esc(title)}</b>` : ""}${esc(text)}</div></div>`;
}
function pill(decision) {
  const m = { allow: ["allow", "check", "Allowed"], step_up: ["step", "key", "Code required"], block: ["block", "x", "Blocked"], signup: ["neutral", "user", "New account"] }[decision] || ["neutral", "info", decision];
  return `<span class="pill ${m[0]}">${icon(m[1])}${m[2]}</span>`;
}
function parseReasons(r) {
  if (Array.isArray(r)) return r.map((x) => ({ rule: x.rule, points: x.points }));
  return String(r || "").split(";").filter(Boolean).map((s) => { const [rule, p] = s.split(":"); return { rule, points: parseFloat(p) }; });
}
function chips(reasons) {
  if (!reasons.length) return `<p class="muted small">No risk signals fired.</p>`;
  return `<div class="chips">${reasons.map((x) => `<span class="chip">${esc(RULES[x.rule] || x.rule)}<span class="pts ${x.points < 0 ? "neg" : ""}">${x.points > 0 ? "+" : ""}${x.points}</span></span>`).join("")}</div>`;
}
function meter(score) {
  const s = Math.max(0, Math.min(100, Number(score) || 0));
  return `<div class="meter" role="img" aria-label="Risk score ${s} out of 100">
    <div class="meter-head"><span class="meter-num">${Math.round(s)}<small> / 100 risk</small></span></div>
    <div class="meter-track"><span class="z1"></span><span class="z2"></span><span class="z3"></span><span class="meter-mark" style="left:${s}%"></span></div>
    <div class="meter-scale"><span>Allow · 0–29</span><span>Code · 30–69</span><span>Block · 70+</span></div></div>`;
}
const fmtTime = (iso) => new Date(iso.endsWith("Z") ? iso : iso + "Z").toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
function fmtDay(iso) {
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z"), t = new Date();
  const y = new Date(t); y.setDate(t.getDate() - 1);
  if (d.toDateString() === t.toDateString()) return "Today";
  if (d.toDateString() === y.toDateString()) return "Yesterday";
  return d.toLocaleDateString([], { weekday: "long", day: "numeric", month: "short" });
}
const shortDev = (id) => (id === S.device ? "This device" : (id || "").slice(0, 14));
const contextLine = () => S.health?.sim_mode
  ? `${esc(S.location)} · ${S.network === "vpn" ? "VPN" : S.network === "mobile" ? "Mobile data" : "Home Wi-Fi"} <span class="muted">(simulated)</span>`
  : "Your real network";

/* ============================== router ============================== */
const ROUTES = {};
const TABS = [["account", "home", "Account"], ["activity", "list", "Activity"], ["lab", "lab", "Attack lab"], ["settings", "gear", "Settings"]];
const TAB_OF = { account: "account", signin: "account", signup: "account", enroll: "account", verify: "account", activity: "activity", lab: "lab", settings: "settings" };
const NO_TABS = new Set(["signin", "signup", "enroll", "verify"]);

function go(route) { if (location.hash === "#" + route) render(); else location.hash = route; }
async function render() {
  let route = location.hash.slice(1) || "account";
  if (!ROUTES[route]) route = "account";
  if (route === "verify" && !S.pending) route = "signin";
  if (route === "enroll" && !S.enroll) route = "account";
  const app = document.getElementById("app");
  app.className = "shell" + (NO_TABS.has(route) ? " no-tabs" : "");
  app.innerHTML = `<div class="screen">${ROUTES[route].view()}</div>`;
  renderTabs(route);
  window.scrollTo(0, 0);
  ROUTES[route].mount?.(app);
  const h = app.querySelector("h1"); if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); }
}
function renderTabs(route) {
  const nav = document.getElementById("tabbar");
  nav.hidden = NO_TABS.has(route);
  nav.innerHTML = TABS.map(([r, ic, label]) =>
    `<a class="tab" href="#${r}" ${TAB_OF[route] === r ? 'aria-current="page"' : ""}>${icon(ic)}<span>${label}</span></a>`).join("");
}
window.addEventListener("hashchange", render);

/* ============================== screen: account ============================== */
ROUTES.account = {
  view() {
    if (S.me) return homeView();
    const online = S.health, sim = online?.sim_mode;
    return `${bar()}
    <main class="content">
      <section class="hero">
        <div class="logo">${icon("shield")}</div>
        <h1 class="large">Sign in that knows when to ask for more</h1>
        <p class="lead">RiskLogin checks every sign-in. Familiar devices go straight through. Anything unusual gets a code request or is stopped.</p>
      </section>
      <div class="flow" aria-label="How sign-in decisions work">
        <div><span class="badge-ic good">${icon("check")}</span><b>Allow</b><span>Known device, usual place</span></div>
        <div><span class="badge-ic warn">${icon("key")}</span><b>Ask for a code</b><span>Something new, like a device or network</span></div>
        <div><span class="badge-ic crit">${icon("x")}</span><b>Block</b><span>Bots, impossible travel</span></div>
      </div>
      ${S.flash ? alertBox(S.flash.kind, S.flash.title, S.flash.text) : ""}
      <div class="stack">
        <a class="btn primary block" href="#signin">Sign in</a>
        <a class="btn secondary block" href="#signup">Create account</a>
      </div>
      <p class="status-dot ${online ? "on" : "off"}">${online ? (sim ? "Connected · simulation mode" : "Connected") : "Login service unreachable · check Settings"}</p>
    </main>`;
  },
  mount() { S.flash = null; },
};

function homeView() {
  const c = S.lastCheck && S.lastCheck.username === S.me.username ? S.lastCheck : null;
  const sim = S.health?.sim_mode;
  let check = "";
  if (c) {
    const reasons = parseReasons(c.reasons || []);
    const how = c.decision === "signup" ? "You created your account here, so this device and network are now trusted."
      : c.decision === "step_up" ? "This sign-in looked unusual, so we asked for a code. You entered it, and this device is now trusted."
      : "Nothing unusual, so no extra checks were needed.";
    check = `<section class="stack">
      <h2 class="section-label">How this sign-in was checked</h2>
      <div class="card stack-lg">
        <div class="row-gap" style="justify-content:space-between">${pill(c.decision)}<span class="muted small">${fmtTime(c.at)}</span></div>
        ${c.decision === "signup" ? "" : meter(c.score)}
        <p class="sub">${how}</p>
        ${sim && c.decision !== "signup" ? `<div class="stack"><span class="muted small">Signals the engine saw</span>${chips(reasons)}</div>` : ""}
      </div></section>`;
  }
  return `${bar({ title: "" })}
  <main class="content">
    <h1 class="large">Hi, ${esc(S.me.username)}</h1>
    <div class="card flush list" aria-label="Session">
      <div class="item"><span class="badge-ic good">${icon("check")}</span><div><div class="v">You're signed in</div><div class="k">Session ends at ${S.me.expires_at ? fmtTime(S.me.expires_at) : "—"}</div></div><span></span></div>
      <div class="item"><span class="badge-ic accent">${icon("device")}</span><div><div class="v">This device is trusted</div><div class="k mono">${esc(S.device)}</div></div><span></span></div>
      <div class="item"><span class="badge-ic">${icon("pin")}</span><div><div class="v">Signing in from</div><div class="k">${contextLine()}</div></div><span></span></div>
    </div>
    ${check}
    <div class="card flush list">
      <a class="item" href="#activity" style="text-decoration:none;color:inherit"><span class="badge-ic">${icon("list")}</span><div><div class="v">Security activity</div><div class="k">Every sign-in attempt on your account</div></div>${icon("chev")}</a>
      <a class="item" href="#lab" style="text-decoration:none;color:inherit"><span class="badge-ic crit">${icon("lab")}</span><div><div class="v">Try an attack</div><div class="k">See how the engine responds</div></div>${icon("chev")}</a>
    </div>
    <button class="btn danger block" id="signout">${icon("logout")}Sign out</button>
  </main>`;
}
const _accountMount = ROUTES.account.mount;
ROUTES.account.mount = (root) => {
  _accountMount();
  $("#signout", root)?.addEventListener("click", async (e) => {
    busy(e.currentTarget, true, "Signing out…");
    await api("/logout", { method: "POST", auth: true });
    clearSession(); S.flash = { kind: "info", title: "Signed out", text: "Sign in again whenever you need to." };
    go("account");
  });
};

/* ============================== screen: sign in / sign up ============================== */
function credForm({ mode }) {
  const signup = mode === "signup";
  return `${bar({ title: signup ? "Create account" : "Sign in", back: "account" })}
  <main class="content">
    <h1 class="large">${signup ? "Create your account" : "Welcome back"}</h1>
    <p class="sub">${signup ? "This device becomes your first trusted device." : "Sign in with your username and password."}</p>
    <form id="cred" class="stack-lg" novalidate>
      <div id="formMsg"></div>
      <div class="field"><label for="u">Username</label>
        <input class="input" id="u" name="username" autocomplete="username" autocapitalize="none" autocorrect="off" spellcheck="false" required minlength="3" maxlength="64" value="${esc(store.get("lastUser", ""))}"></div>
      <div class="field"><label for="p">Password</label>
        <div class="input-wrap"><input class="input has-btn" id="p" name="password" type="password" autocomplete="${signup ? "new-password" : "current-password"}" required minlength="${signup ? 8 : 1}" maxlength="128">
        <button type="button" class="input-btn" id="peek" aria-label="Show password">${icon("eye")}</button></div>
        ${signup ? `<span class="hint" id="pwHint">Use at least 8 characters. A short phrase is easiest to remember.</span>` : ""}</div>
      <button class="btn primary block" type="submit">${signup ? "Create account" : "Sign in"}</button>
    </form>
    <div class="card flush list">
      <a class="item" href="#settings" style="text-decoration:none;color:inherit"><span class="badge-ic">${icon("device")}</span>
        <div><div class="k">What the server will see</div><div class="v small">${contextLine()}</div></div>${icon("chev")}</a>
    </div>
    <p class="muted small" style="text-align:center">${signup ? `Already have an account? <a href="#signin">Sign in</a>` : `New here? <a href="#signup">Create an account</a>`}</p>
  </main>`;
}
function mountCred(root, mode) {
  const form = $("#cred", root), u = $("#u", root), p = $("#p", root), msg = $("#formMsg", root);
  if (!u.value) u.focus({ preventScroll: true });
  $("#peek", root).addEventListener("click", (e) => {
    const show = p.type === "password"; p.type = show ? "text" : "password";
    e.currentTarget.innerHTML = icon(show ? "eyeOff" : "eye"); e.currentTarget.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
  if (mode === "signup") p.addEventListener("input", () => {
    const h = $("#pwHint", root), ok = p.value.length >= 8;
    h.className = "hint" + (ok ? " ok" : ""); h.textContent = ok ? "Looks good." : `Use at least 8 characters (${p.value.length}/8).`;
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault(); msg.innerHTML = "";
    const username = u.value.trim(), password = p.value;
    u.removeAttribute("aria-invalid"); p.removeAttribute("aria-invalid");
    if (username.length < 3) { u.setAttribute("aria-invalid", "true"); msg.innerHTML = alertBox("crit", "", "Enter a username of at least 3 characters."); return u.focus(); }
    if (mode === "signup" && password.length < 8) { p.setAttribute("aria-invalid", "true"); msg.innerHTML = alertBox("crit", "", "Use a password of at least 8 characters."); return p.focus(); }
    if (!password) { p.setAttribute("aria-invalid", "true"); msg.innerHTML = alertBox("crit", "", "Enter your password."); return p.focus(); }
    const btn = form.querySelector("[type=submit]");
    busy(btn, true, mode === "signup" ? "Creating account…" : "Checking…");
    await ensureDevice();
    const r = await api(mode === "signup" ? "/signup" : "/login", { method: "POST", body: { username, password, device: deviceInfo() }, sim: true });
    busy(btn, false);
    store.set("lastUser", username);
    if (mode === "signup") {
      if (r.status !== 201) { msg.innerHTML = alertBox("crit", "Couldn't create the account", errorText(r)); return; }
      setSession(r.data.session_token, username, { decision: "signup", score: 0, reasons: [] });
      S.enroll = { username, secret: r.data.totp_secret, uri: r.data.otpauth_uri };
      if (S.health?.sim_mode) { const d = demoSecrets(); d[username] = r.data.totp_secret; store.set("demoSecrets", d); }
      await loadMe(); go("enroll"); return;
    }
    if (r.status === 200 && r.data.status === "ok") {
      setSession(r.data.session_token, username, r.data.risk); await loadMe(); toast("Signed in"); go("account"); return;
    }
    if (r.status === 200 && r.data.status === "step_up") {
      S.pending = { ...r.data, username }; go("verify"); return;
    }
    msg.innerHTML = r.status === 401
      ? alertBox("crit", "Couldn't sign you in", "Check your username and password. If this keeps happening, your sign-in may have been blocked for looking unusual.")
      : alertBox("crit", "Couldn't sign you in", errorText(r));
    p.value = ""; p.focus();
  });
}
ROUTES.signin = { view: () => credForm({ mode: "signin" }), mount: (r) => mountCred(r, "signin") };
ROUTES.signup = { view: () => credForm({ mode: "signup" }), mount: (r) => mountCred(r, "signup") };

/* ============================== screen: enroll authenticator ============================== */
ROUTES.enroll = {
  view() {
    const e = S.enroll, groups = e.secret.match(/.{1,4}/g).join(" ");
    return `${bar({ title: "Set up codes" })}
    <main class="content">
      <h1 class="large">Add RiskLogin to your authenticator</h1>
      <p class="sub">You'll only be asked for a code when a sign-in looks unusual, like a new device or a new country.</p>
      <div class="card stack-lg">
        <div class="stack"><h3>1. Scan this code</h3><p class="muted small">Open Google Authenticator, 1Password, Authy or a similar app, and add an account.</p></div>
        <div class="qr" id="qr" role="img" aria-label="QR code for your authenticator app"></div>
        <div class="stack"><h3>2. Or enter this key</h3><div class="secret" id="secret">${esc(groups)}</div>
          <button class="btn outline block" id="copyKey">${icon("copy")}Copy key</button></div>
      </div>
      ${S.health?.sim_mode ? alertBox("info", "Demo authenticator is on", "In simulation mode this browser also shows the current code on the verification screen, so you can test without a phone.") : ""}
      <button class="btn primary block" id="done">I've added it</button>
    </main>`;
  },
  mount(root) {
    try {
      const qr = qrcode(0, "M"); qr.addData(S.enroll.uri); qr.make();
      $("#qr", root).innerHTML = qr.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
    } catch { $("#qr", root).innerHTML = `<p class="muted small">Couldn't draw the QR code. Use the key below.</p>`; }
    $("#copyKey", root).addEventListener("click", () => copy(S.enroll.secret, "Key copied"));
    $("#done", root).addEventListener("click", () => { S.enroll = null; toast("You're all set"); go("account"); });
  },
};

/* ============================== screen: verify (step-up) ============================== */
let verifyTimer;
ROUTES.verify = {
  view() {
    const p = S.pending, reasons = parseReasons(p.risk?.reasons || []).filter((x) => x.points > 0);
    const why = reasons.length ? reasons.map((x) => RULES[x.rule] || x.rule).join(" · ") : "This sign-in looked different from usual.";
    return `${bar({ title: "Verify", back: "signin" })}
    <main class="content">
      <div class="hero" style="padding-top:8px"><div class="logo" style="background:var(--warn-soft);color:var(--warn)">${icon("key")}</div>
      <h1 class="large">Confirm it's you</h1>
      <p class="lead">Enter the 6-digit code from your authenticator app for <b>${esc(p.username)}</b>.</p></div>
      <div class="card tint stack"><span class="small"><b>Why we're asking:</b> ${esc(why)}</span></div>
      <form id="otpForm" class="stack-lg" novalidate>
        <div class="otp" id="otp">${"<div class='cell'></div>".repeat(6)}
          <input id="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]*" maxlength="6" aria-label="6-digit code"></div>
        <div id="otpMsg"></div>
        <button class="btn primary block" type="submit" id="verifyBtn">Verify</button>
      </form>
      <div id="demo"></div>
      <p class="muted small" id="expiry" style="text-align:center"></p>
      <button class="btn ghost" id="cancel">Use a different account</button>
    </main>`;
  },
  mount(root) {
    const input = $("#code", root), cells = $$(".cell", root), box = $("#otp", root), msg = $("#otpMsg", root);
    const paint = () => {
      const v = input.value; box.classList.remove("error");
      cells.forEach((c, i) => { c.textContent = v[i] || ""; c.classList.toggle("active", document.activeElement === input && i === Math.min(v.length, 5)); });
    };
    input.addEventListener("input", () => { input.value = input.value.replace(/\D/g, "").slice(0, 6); paint(); if (input.value.length === 6) submit(); });
    input.addEventListener("focus", paint); input.addEventListener("blur", paint);
    setTimeout(() => input.focus(), 50);
    const submit = async (e) => {
      e?.preventDefault();
      if (input.value.length !== 6) { msg.innerHTML = alertBox("crit", "", "Enter all 6 digits."); return input.focus(); }
      const btn = $("#verifyBtn", root); busy(btn, true, "Verifying…");
      const r = await api("/login/step-up", { method: "POST", body: { challenge_id: S.pending.challenge_id, code: input.value } });
      busy(btn, false);
      if (r.status === 200) {
        setSession(r.data.session_token, S.pending.username, { ...S.pending.risk, decision: "step_up" });
        S.pending = null; clearInterval(verifyTimer); await loadMe(); toast("Verified · this device is now trusted"); go("account"); return;
      }
      if (r.status === 410) {
        S.pending = null; clearInterval(verifyTimer);
        S.flash = { kind: "warn", title: "Sign in again", text: r.data.message || "This verification ended." };
        go("account"); return;
      }
      box.classList.add("error"); input.value = ""; paint();
      const left = r.data.attempts_left;
      msg.innerHTML = alertBox("crit", "That code didn't work", left ? `${left} ${left === 1 ? "try" : "tries"} left. Codes change every 30 seconds and each one works only once.` : errorText(r));
      input.focus();
    };
    $("#otpForm", root).addEventListener("submit", submit);
    $("#cancel", root).addEventListener("click", () => { S.pending = null; clearInterval(verifyTimer); go("signin"); });

    const secret = S.health?.sim_mode ? demoSecrets()[S.pending.username] : null;
    const exp = new Date(S.pending.expires_at).getTime();
    const tick = async () => {
      if (!document.body.contains(input)) return clearInterval(verifyTimer);
      const left = Math.max(0, Math.round((exp - Date.now()) / 1000));
      $("#expiry", root).textContent = left ? `This request expires in ${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}` : "This request has expired. Sign in again.";
      if (secret) {
        const code = await totp(secret), secs = 30 - (Math.floor(Date.now() / 1000) % 30), C = 2 * Math.PI * 12;
        if (code) $("#demo", root).innerHTML = `<button type="button" class="demo-code" id="fill" style="width:100%;background:none;color:inherit">
          <span style="text-align:left"><span class="muted tiny" style="display:block">Demo authenticator · tap to fill</span><span class="code">${code.slice(0, 3)} ${code.slice(3)}</span></span>
          <svg class="ring" viewBox="0 0 30 30" aria-label="${secs} seconds left"><circle class="bg" cx="15" cy="15" r="12"/><circle class="fg" cx="15" cy="15" r="12" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - secs / 30)}"/></svg></button>`;
        $("#fill", root)?.addEventListener("click", () => { input.value = code; paint(); submit(); });
      }
    };
    clearInterval(verifyTimer); tick(); verifyTimer = setInterval(tick, 1000);
  },
};

/* ============================== screen: activity ============================== */
function describe(ev) {
  const d = ev.decision, o = ev.outcome;
  if (d === "signup") return ["Account created", "accent", "user"];
  if (o === "success" && d === "allow") return ["Signed in", "good", "check"];
  if (o === "success" && d === "step_up") return ["Signed in after code check", "good", "key"];
  if (o === "pending") return ["Code requested", "warn", "key"];
  if (o === "blocked") return ["Blocked sign-in", "crit", "x"];
  if (o === "challenge_failed") return ["Code check failed", "crit", "x"];
  if (o === "challenge_expired") return ["Code request expired", "warn", "clock"];
  if (o === "bad_password") return d === "step_up" ? ["Wrong password · decoy code prompt", "warn", "lock"] : ["Wrong password", "warn", "lock"];
  return [o, "", "info"];
}
ROUTES.activity = {
  view() {
    return `${bar({ title: "", action: `<button class="icon-btn" id="refresh" aria-label="Refresh">${icon("refresh")}</button>` })}
    <main class="content"><h1 class="large">Security activity</h1><div id="act" class="stack-lg"><p class="muted">Loading…</p></div></main>`;
  },
  async mount(root) {
    const box = $("#act", root);
    $("#refresh", root).addEventListener("click", () => render());
    if (!S.me) { box.innerHTML = `${alertBox("info", "Sign in to see your activity", "Every sign-in attempt on your account shows up here, including the ones that were blocked.")}<a class="btn primary block" href="#signin">Sign in</a>`; return; }
    if (!S.health?.sim_mode) { box.innerHTML = alertBox("info", "Activity needs simulation mode", "The activity log reads the admin event feed, which this server only exposes in simulation mode."); return; }
    const r = await api("/admin/events?limit=500");
    if (r.status !== 200) { box.innerHTML = alertBox("crit", "Couldn't load activity", errorText(r)); return; }
    const evs = r.data.filter((e) => e.username === S.me.username);
    const count = (f) => evs.filter(f).length;
    const stats = `<div class="stats">
      <div class="stat good"><b>${count((e) => e.outcome === "success")}</b><span>Signed in</span></div>
      <div class="stat warn"><b>${count((e) => e.decision === "step_up")}</b><span>Asked for code</span></div>
      <div class="stat crit"><b>${count((e) => e.outcome === "blocked")}</b><span>Blocked</span></div></div>`;
    if (!evs.length) { box.innerHTML = stats + `<p class="muted">No sign-in attempts yet.</p>`; return; }
    let html = stats, day = null, group = [];
    const flush = () => { if (group.length) html += `<section class="stack"><h2 class="day">${day}</h2><div class="card flush list">${group.join("")}</div></section>`; group = []; };
    for (const e of evs) {
      const dd = fmtDay(e.ts); if (dd !== day) { flush(); day = dd; }
      const [title, tone, ic] = describe(e);
      const attack = e.sim_label && e.sim_label.startsWith("attack");
      group.push(`<div><button class="ev" aria-expanded="false" data-id="${e.id}">
        <span class="badge-ic ${tone}">${icon(ic)}</span>
        <span style="min-width:0"><span class="ev-title">${esc(title)}</span>
          <span class="ev-sub" style="display:block">${esc(e.city)}, ${esc(e.country)} · ${esc(NETWORK_LABEL[e.asn_type] || e.asn_type)} · ${fmtTime(e.ts)}</span></span>
        <span class="score" aria-label="Risk score">${Math.round(e.score)}</span></button>
        <div class="ev-detail" hidden>
          ${attack ? `<span><span class="tag">Simulated ${esc(e.sim_label.replace("attack:", "").replace(/_/g, " "))}</span></span>` : ""}
          ${e.decision !== "signup" ? `<div class="row-gap">${pill(e.decision)}</div>${chips(parseReasons(e.reasons))}` : ""}
          <dl><dt>Device</dt><dd class="mono">${esc(shortDev(e.device_id))}${e.headless ? " · automated" : ""}</dd>
          <dt>IP address</dt><dd class="mono">${esc(e.ip)}</dd><dt>Network</dt><dd>AS${esc(e.asn)} · ${esc(NETWORK_LABEL[e.asn_type] || e.asn_type)}</dd></dl>
        </div></div>`);
    }
    flush(); box.innerHTML = html;
    $$(".ev", box).forEach((b) => b.addEventListener("click", () => {
      const open = b.getAttribute("aria-expanded") === "true";
      b.setAttribute("aria-expanded", String(!open)); b.nextElementSibling.hidden = open;
    }));
  },
};

/* ============================== screen: attack lab ============================== */
const SCENARIOS = [
  { id: "impossible_travel", icon: "plane", name: "Impossible travel", desc: "Your password used on the other side of the world, minutes after your last sign-in.", meta: "1 attempt · new device · residential IP" },
  { id: "local_attacker", icon: "pin", name: "Local attacker", desc: "Someone in your own city, at a normal hour, on a home network.", meta: "1 attempt · the hardest case to catch" },
  { id: "new_device_3am", icon: "moon", name: "New device at 3am", desc: "A sign-in from your country in the middle of the night.", meta: "1 attempt · unusual hour needs 5+ past sign-ins" },
  { id: "credential_stuffing", icon: "bot", name: "Credential stuffing", desc: "A bot on a cloud server tries leaked passwords on many accounts, then yours.", meta: "7 attempts · datacenter IP · headless browser" },
  { id: "smart_stuffing", icon: "spray", name: "Smart stuffing", desc: "The same attack through residential proxies and a real browser.", meta: "4 attempts · a new IP each time" },
  { id: "brute_force", icon: "hammer", name: "Brute force", desc: "Ten wrong guesses on your account, then the right password.", meta: "11 attempts · affects your account's risk for 1 hour" },
];
function plan(id, target, password) {
  const home = cityByName(S.location), now = new Date(), att = "dev-attk-" + randHex(4);
  const fake = () => ["j.smith", "maria", "admin", "test", "k.lee", "sam"][Math.floor(Math.random() * 6)] + Math.floor(Math.random() * 900 + 100);
  const label = "attack:" + id;
  const resi = (c, k, ipk) => ({ ip: ipFor(CITIES.indexOf(c) + 30 + ipk, ipk), asn: resiAsn(c.country, k), asn_type: "residential", ...c, label });
  if (id === "impossible_travel") {
    const far = CITIES.filter((c) => km(c, home) > 3000).sort((a, b) => km(b, home) - km(a, home))[0];
    return [{ user: target, pw: password, dev: att, sim: resi(far, 1, 1) }];
  }
  if (id === "local_attacker") return [{ user: target, pw: password, dev: att, sim: resi(home, 2, 2) }];
  if (id === "new_device_3am") {
    const same = CITIES.filter((c) => c.country === home.country && c.city !== home.city)[0] || home;
    const t = new Date(now); t.setHours(3, 12, 0, 0);
    return [{ user: target, pw: password, dev: att, sim: { ...resi(same, 3, 3), ts: t.toISOString().replace("Z", "") } }];
  }
  if (id === "credential_stuffing") {
    const aws = { ip: "3.5.140." + Math.floor(Math.random() * 200 + 2), asn: 16509, asn_type: "hosting", city: "New York", country: "US", lat: 39.04, lon: -77.49, label };
    return [...Array(6)].map(() => ({ user: fake(), pw: "Summer2024!", dev: att, headless: true, sim: aws }))
      .concat([{ user: target, pw: password, dev: att, headless: true, sim: aws }]);
  }
  if (id === "smart_stuffing") {
    const pick = () => CITIES[Math.floor(Math.random() * CITIES.length)];
    return [...Array(3)].map((_, i) => ({ user: fake(), pw: "Summer2024!", dev: "dev-ss-" + randHex(4), sim: resi(pick(), 1, 40 + i) }))
      .concat([{ user: target, pw: password, dev: "dev-ss-" + randHex(4), sim: resi(pick(), 1, 50) }]);
  }
  if (id === "brute_force") {
    const c = cityByName("Moscow") === home ? cityByName("Berlin") : cityByName("Moscow"), s = resi(c, 1, 60);
    return [...Array(10)].map((_, i) => ({ user: target, pw: "guess" + (1000 + i), dev: att, sim: s }))
      .concat([{ user: target, pw: password, dev: att, sim: s }]);
  }
  return [];
}
function verdictFor(final) {
  const st = final.res.data?.status;
  if (final.res.status === 200 && st === "ok") return { tone: "crit", ic: "alert", title: "The attacker got in", text: "The risk score stayed under the code threshold, so the sign-in was allowed. This is the trade-off: catching it would also challenge more real users." };
  if (st === "step_up") return { tone: "warn", ic: "key", title: "Stopped at the code check", text: "The attacker has your password but now needs your authenticator code. They only get in by phishing or relaying it." };
  if (final.res.status === 401) return { tone: "good", ic: "shield", title: "Blocked", text: "The attacker saw the same \"couldn't sign you in\" message as a wrong password, so they can't even tell the password worked." };
  return { tone: "", ic: "info", title: "No decision", text: errorText(final.res) };
}
ROUTES.lab = {
  view() {
    const sim = S.health?.sim_mode, run = S.labRun;
    return `${bar({ title: "" })}
    <main class="content">
      <h1 class="large">Attack lab</h1>
      <p class="sub">Replay a real attack pattern against an account and see what the risk engine decides, signal by signal.</p>
      ${!sim ? alertBox("warn", "Simulation mode is off", "The lab fakes locations and networks, which the server only allows in simulation mode. Start the API with RISKAUTH_SIM_MODE=1.") : ""}
      ${run ? labResult(run) : ""}
      <form id="labForm" class="stack-lg" novalidate>
        <div class="field"><label for="tgt">Target account</label>
          <input class="input" id="tgt" autocomplete="off" autocapitalize="none" spellcheck="false" value="${esc(S.me?.username || store.get("lastUser", ""))}"></div>
        <div class="field"><label for="vpw">The account's password</label>
          <div class="input-wrap"><input class="input has-btn" id="vpw" type="password" autocomplete="off" placeholder="Attackers in these scenarios already have it">
          <button type="button" class="input-btn" id="peek2" aria-label="Show password">${icon("eye")}</button></div>
          <span class="hint">Used only for this run and never saved.</span></div>
        <div class="field"><span class="label" id="scnLabel">Scenario</span>
          <div class="scenarios" role="radiogroup" aria-labelledby="scnLabel">
          ${SCENARIOS.map((s) => `<button type="button" class="scn" role="radio" aria-checked="${s.id === S.labScenario}" data-id="${s.id}">
            <span class="badge-ic ${s.id === S.labScenario ? "crit" : ""}">${icon(s.icon)}</span>
            <span><b>${s.name}</b><span>${s.desc}</span><span class="meta">${s.meta}</span></span></button>`).join("")}
          </div></div>
        <div class="sticky-cta"><button class="btn primary block" type="submit" id="runBtn" ${sim ? "" : "disabled"}>${icon("lab")}Run attack</button></div>
        <div id="labMsg"></div>
      </form>
    </main>`;
  },
  mount(root) {
    $$(".scn", root).forEach((b) => b.addEventListener("click", () => {
      S.labScenario = b.dataset.id; store.set("labScenario", S.labScenario);
      $$(".scn", root).forEach((x) => { const on = x === b; x.setAttribute("aria-checked", on); x.firstElementChild.classList.toggle("crit", on); });
    }));
    const pw = $("#vpw", root);
    $("#peek2", root).addEventListener("click", (e) => { const s = pw.type === "password"; pw.type = s ? "text" : "password"; e.currentTarget.innerHTML = icon(s ? "eyeOff" : "eye"); });
    $("#labForm", root).addEventListener("submit", async (e) => {
      e.preventDefault();
      const target = $("#tgt", root).value.trim(), password = pw.value, msg = $("#labMsg", root);
      if (!target) { msg.innerHTML = alertBox("crit", "", "Enter the account to attack."); return $("#tgt", root).focus(); }
      if (!password) { msg.innerHTML = alertBox("crit", "", "Enter the account's password. These attackers already have it."); return pw.focus(); }
      const btn = $("#runBtn", root);
      S.labRun = null; $(".verdict", root)?.remove();
      const steps = plan(S.labScenario, target, password), results = [];
      busy(btn, true, steps.length > 1 ? `Attempt 1 of ${steps.length}…` : "Running attack…");
      for (const [i, s] of steps.entries()) {
        if (steps.length > 1) btn.lastChild.textContent = `Attempt ${i + 1} of ${steps.length}…`;
        const res = await api("/login", { method: "POST", body: { username: s.user, password: s.pw, device: { id: s.dev, headless: !!s.headless } }, sim: s.sim });
        results.push({ ...s, res });
      }
      const ev = await api(`/admin/events?limit=${steps.length}`);
      const events = ev.status === 200 ? ev.data.slice().reverse() : [];
      S.labRun = { scenario: S.labScenario, target, results, events };
      busy(btn, false); render();
      $(".verdict")?.scrollIntoView({ block: "start", behavior: "smooth" });
    });
  },
};
function labResult(run) {
  const scn = SCENARIOS.find((s) => s.id === run.scenario), final = run.results[run.results.length - 1];
  const fev = run.events[run.events.length - 1], v = verdictFor(final);
  const outcome = (r) => r.res.data?.status === "ok" ? ["allow", "Allowed"] : r.res.data?.status === "step_up" ? ["step", r.pw === final.pw && r.user === final.user ? "Code required" : "Decoy code prompt"] : ["block", r.res.status === 401 ? "Denied" : "Error"];
  return `<section class="card verdict" aria-label="Attack result">
    <div class="verdict-head"><span class="badge-ic ${v.tone}">${icon(v.ic)}</span>
      <div><span class="muted tiny">${esc(scn.name)} · ${esc(run.target)}</span><h2>${esc(v.title)}</h2></div></div>
    <p class="sub small">${esc(v.text)}</p>
    ${fev ? meter(fev.score) + chips(parseReasons(fev.reasons)) : ""}
    ${run.results.length > 1 ? `<div class="attempts"><span class="muted small">Every attempt</span><ol>${run.results.map((r, i) => {
      const [k, label] = outcome(r), e = run.events[i];
      return `<li><span class="n">${i + 1}</span><span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(r.user)}${r.user === run.target ? "" : " <span class='muted'>(other account)</span>"}</span><span class="pill ${k}" style="font-size:12.5px">${label}${e ? ` · ${Math.round(e.score)}` : ""}</span></li>`;
    }).join("")}</ol></div>` : ""}
    <a class="btn outline block" href="#activity">See it in activity</a>
  </section>`;
}

/* ============================== screen: settings ============================== */
ROUTES.settings = {
  view() {
    const sim = S.health?.sim_mode;
    const seg = (id, val, opts) => `<div class="seg" role="group" id="${id}">${opts.map(([v, l]) => `<button type="button" data-v="${v}" aria-pressed="${v === val}">${l}</button>`).join("")}</div>`;
    return `${bar({ title: "" })}
    <main class="content">
      <h1 class="large">Settings</h1>
      <section class="stack"><h2 class="section-label">Simulated location</h2>
        <div class="card stack-lg">
          <p class="small sub">${sim ? "In simulation mode your own sign-ins are sent from this place and network. Change them to see how the engine reacts, for example by switching on a VPN." : "Simulation mode is off, so the server uses your real network."}</p>
          <div class="field"><label for="loc">City</label><select class="input" id="loc" ${sim ? "" : "disabled"}>
            ${CITIES.map((c) => `<option ${c.city === S.location ? "selected" : ""}>${esc(c.city)}</option>`).join("")}</select></div>
          <div class="field"><span class="label">Network</span>${seg("net", S.network, [["home", "Home Wi-Fi"], ["mobile", "Mobile data"], ["vpn", "VPN"]])}</div>
        </div></section>
      <section class="stack"><h2 class="section-label">This device</h2>
        <div class="card stack">
          <div class="field"><span class="label">Device ID</span><div class="secret" style="font-size:15px;text-align:left">${esc(S.device || "Created on first sign-in")}</div></div>
          <p class="hint">Your browser makes this ID and sends it with each sign-in. Reset it to look like a brand-new device.</p>
          <button class="btn outline block" id="resetDev">${icon("refresh")}Reset device ID</button>
        </div></section>
      <section class="stack"><h2 class="section-label">Appearance</h2>
        <div class="card">${seg("theme", S.theme, [["system", "System"], ["light", "Light"], ["dark", "Dark"]])}</div></section>
      <section class="stack"><h2 class="section-label">Connection</h2>
        <div class="card stack-lg">
          <div class="field"><label for="apiBase">Login API address</label>
            <input class="input" id="apiBase" value="${esc(S.apiBase)}" autocapitalize="none" spellcheck="false" inputmode="url">
            <span class="hint">Use /api when the app is served by web/serve.py. Otherwise use the API's full address, for example http://localhost:8000.</span></div>
          <p class="status-dot ${S.health ? "on" : "off"}" id="conn">${S.health ? (sim ? "Connected · simulation mode" : "Connected") : "Not connected"}</p>
          <button class="btn secondary block" id="test">Save and test</button>
        </div></section>
      <p class="muted tiny" style="text-align:center">RiskLogin 0.1 · <a href="https://github.com/ravirana211/risk-based-login-simulator">Source on GitHub</a></p>
    </main>`;
  },
  mount(root) {
    $("#loc", root).addEventListener("change", (e) => { S.location = e.target.value; store.set("location", S.location); toast("Location: " + S.location); });
    const segs = (id, fn) => $$(`#${id} button`, root).forEach((b) => b.addEventListener("click", () => {
      $$(`#${id} button`, root).forEach((x) => x.setAttribute("aria-pressed", x === b)); fn(b.dataset.v);
    }));
    segs("net", (v) => { S.network = v; store.set("network", v); });
    segs("theme", (v) => { S.theme = v; store.set("theme", v); applyTheme(); });
    $("#resetDev", root).addEventListener("click", async () => { S.device = null; store.del("device"); await ensureDevice(); toast("New device ID created"); render(); });
    $("#test", root).addEventListener("click", async (e) => {
      S.apiBase = $("#apiBase", root).value.trim() || "/api"; store.set("apiBase", S.apiBase);
      busy(e.currentTarget, true, "Testing…"); await checkHealth(); await loadMe(); busy(e.currentTarget, false);
      toast(S.health ? "Connected" : "Couldn't reach the API"); render();
    });
  },
};

/* ============================== boot ============================== */
function applyTheme() {
  const r = document.documentElement;
  if (S.theme === "system") delete r.dataset.theme; else r.dataset.theme = S.theme;
}
(async function boot() {
  applyTheme();
  await ensureDevice();
  await checkHealth();
  await loadMe();
  render();
  if ("serviceWorker" in navigator && location.protocol !== "file:") navigator.serviceWorker.register("sw.js").catch(() => {});
})();
