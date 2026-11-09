/* In-browser stand-in for the login API, used by the hosted demo build only.
   A JavaScript port of risksim (signals, weights, policy) and api/service.py
   (signup, login, decoy challenges, TOTP step-up, sessions, event log).
   Data lives in this browser's localStorage. Keep weights in sync with risksim/engine.py. */
"use strict";
const MockAPI = (() => {
  const KEY = "rl.mockdb";
  const W = {
    new_device: 25, known_device: -15, asn_hosting: 30, asn_tor: 45, asn_new: 10, country_new: 15,
    impossible_travel: 35, it_kmh: 1000, it_km: 500, acct_failures: 15, acct_failures_at: 3,
    acct_failures_heavy: 30, ip_spray: 35, ip_spray_at: 5, headless: 30, odd_hour: 10, odd_min: 4, odd_sig: 2.5,
  };
  const POLICY = { step_up_at: 30, block_at: 70 };
  const DEMO = { username: "alex", password: "correct horse battery", device: "dev-alex-laptop-01" };
  const DENIED = { status: "denied", message: "We couldn't sign you in with those details." };
  const HOUR = 3600e3;

  let db, st, ready;
  const blank = () => ({ users: {}, events: [], challenges: {}, sessions: {}, nextId: 1 });
  function load() { try { const v = JSON.parse(localStorage.getItem(KEY)); if (v && v.users) return v; } catch {} return blank(); }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(db)); } catch {} }
  const iso = (ms) => new Date(ms).toISOString().slice(0, 23); // naive UTC, like the Python API
  const ms = (s) => Date.parse(s.endsWith("Z") ? s : s + "Z");
  const rnd = (n) => Array.from(crypto.getRandomValues(new Uint8Array(n)), (b) => b.toString(16).padStart(2, "0")).join("");

  /* ---------- risk state (risksim/state.py) ---------- */
  function rebuild() {
    st = { users: {}, acctFail: {}, ipFail: {}, ipAcc: {} };
    for (const e of db.events) { recordAttempt(e); if (e.outcome === "success") recordSuccess(e); }
  }
  function recordAttempt(ev) {
    const t = ms(ev.ts);
    (st.ipAcc[ev.ip] ||= []).push([t, ev.username]);
    if (!ev.password_ok) { (st.acctFail[ev.username] ||= []).push(t); (st.ipFail[ev.ip] ||= []).push(t); }
  }
  function recordSuccess(ev) {
    const h = (st.users[ev.username] ||= { devices: [], asns: [], countries: [], last: null, n: 0, sin: 0, cos: 0 });
    if (!h.devices.includes(ev.device_id)) h.devices.push(ev.device_id);
    if (!h.asns.includes(ev.asn)) h.asns.push(ev.asn);
    if (!h.countries.includes(ev.country)) h.countries.push(ev.country);
    const t = ms(ev.ts), d = new Date(t), a = (2 * Math.PI * (d.getUTCHours() + d.getUTCMinutes() / 60)) / 24;
    h.last = [t, ev.lat, ev.lon]; h.n += 1; h.sin += Math.sin(a); h.cos += Math.cos(a);
  }
  const inWindow = (arr, t) => (arr || []).filter((x) => (Array.isArray(x) ? x[0] : x) >= t - HOUR);

  /* ---------- signals + score (risksim/signals.py, engine.py) ---------- */
  function extract(ev) {
    const h = st.users[ev.username], has = !!(h && h.n > 0), t = ms(ev.ts);
    let km = 0, kmh = 0;
    if (has && h.last) {
      km = haversine(h.last[1], h.last[2], ev.lat, ev.lon);
      kmh = km / Math.max((t - h.last[0]) / HOUR, 1 / 60);
    }
    let dev = null, sd = null;
    if (has && h.n >= 5) {
      const s = h.sin / h.n, c = h.cos / h.n, r = Math.min(Math.max(Math.hypot(s, c), 1e-9), 1);
      const mean = ((Math.atan2(s, c) + 2 * Math.PI) % (2 * Math.PI)) * 24 / (2 * Math.PI);
      sd = Math.sqrt(-2 * Math.log(r)) * 24 / (2 * Math.PI);
      const d = new Date(t), hour = d.getUTCHours() + d.getUTCMinutes() / 60, diff = Math.abs(hour - mean) % 24;
      dev = Math.min(diff, 24 - diff);
    }
    return {
      device_known: has && h.devices.includes(ev.device_id), asn_type: ev.asn_type,
      asn_new: has && !h.asns.includes(ev.asn), country_new: has && !h.countries.includes(ev.country),
      km, kmh, acct_failures: inWindow(st.acctFail[ev.username], t).length,
      ip_distinct: new Set(inWindow(st.ipAcc[ev.ip], t).map((x) => x[1])).size,
      hour_dev: dev, hour_sd: sd, headless: !!ev.headless,
    };
  }
  function score(f) {
    const hits = [];
    hits.push(f.device_known ? ["known_device", W.known_device] : ["new_device", W.new_device]);
    if (f.asn_type === "tor") hits.push(["asn_tor", W.asn_tor]);
    else if (f.asn_type === "hosting") hits.push(["asn_hosting", W.asn_hosting]);
    if (f.asn_new) hits.push(["asn_new", W.asn_new]);
    if (f.country_new) hits.push(["country_new", W.country_new]);
    if (f.kmh > W.it_kmh && f.km > W.it_km) hits.push(["impossible_travel", W.impossible_travel]);
    if (f.acct_failures >= 10) hits.push(["acct_failures_heavy", W.acct_failures_heavy]);
    else if (f.acct_failures >= W.acct_failures_at) hits.push(["acct_failures", W.acct_failures]);
    if (f.ip_distinct >= W.ip_spray_at) hits.push(["ip_spray", W.ip_spray]);
    if (f.headless) hits.push(["headless", W.headless]);
    if (f.hour_dev !== null && f.hour_dev > Math.max(W.odd_min, W.odd_sig * f.hour_sd)) hits.push(["odd_hour", W.odd_hour]);
    const total = hits.reduce((a, [, p]) => a + p, 0);
    return { score: Math.max(0, Math.min(100, total)), hits };
  }
  const decide = (s) => (s >= POLICY.block_at ? "block" : s >= POLICY.step_up_at ? "step_up" : "allow");
  function haversine(la1, lo1, la2, lo2) {
    const r = (d) => (d * Math.PI) / 180, dp = r(la2 - la1), dl = r(lo2 - lo1);
    const a = Math.sin(dp / 2) ** 2 + Math.cos(r(la1)) * Math.cos(r(la2)) * Math.sin(dl / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(a));
  }

  /* ---------- crypto ---------- */
  async function hashPw(pw, saltHex) {
    const salt = saltHex || rnd(16);
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveBits"]);
    const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", salt: new TextEncoder().encode(salt), iterations: 60000, hash: "SHA-256" }, key, 256);
    return `pbkdf2$${salt}$${Array.from(new Uint8Array(bits), (b) => b.toString(16).padStart(2, "0")).join("")}`;
  }
  async function checkPw(pw, stored) { const [, salt] = stored.split("$"); return (await hashPw(pw, salt)) === stored; }
  function b32secret() {
    const A = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    return Array.from(crypto.getRandomValues(new Uint8Array(32)), (b) => A[b % 32]).join("");
  }
  async function checkTotp(user, code, now) {
    if (!/^\d{6}$/.test(code || "")) return false;
    for (const off of [0, -1, 1]) {
      const t = now + off * 30e3;
      if ((await totp(user.totp_secret, t)) === code) {
        const step = Math.floor(t / 30e3);
        if (step <= user.totp_last_step) return false; // each code works once
        user.totp_last_step = step; return true;
      }
    }
    return false;
  }

  /* ---------- service (api/service.py) ---------- */
  const err = (status, code, message, extra = {}) => ({ status, data: { status: code, message, ...extra } });
  function makeEvent(username, ctx, pwOk, device) {
    return { ts: ctx.ts || iso(Date.now()), username, ip: ctx.ip, asn: ctx.asn, asn_type: ctx.asn_type,
      country: ctx.country, city: ctx.city, lat: ctx.lat, lon: ctx.lon, device_id: device.id,
      headless: !!device.headless, password_ok: pwOk, sim_label: ctx.label || null };
  }
  function storeEvent(ev, sc, hits, decision, outcome) {
    const row = { id: db.nextId++, ...ev, score: sc, reasons: hits.map(([n, p]) => `${n}:${p > 0 ? "+" : ""}${p}`).join(";"), decision, outcome };
    db.events.push(row); return row;
  }
  const riskOut = (sc, hits, decision) => ({ score: sc, decision, reasons: hits.map(([rule, points]) => ({ rule, points })) });
  function session(username, deviceId) {
    const token = rnd(24), exp = Date.now() + 12 * HOUR;
    db.sessions[token] = { username, device_id: deviceId, expires_at: iso(exp) };
    return { session_token: token, expires_at: iso(exp) + "Z" };
  }
  function openChallenge(row, sc, hits, decision) {
    const id = rnd(12), exp = Date.now() + 5 * 60e3;
    db.challenges[id] = { event_id: row.id, username: row.username, expires_at: iso(exp), attempts_left: 3, status: "open" };
    return { status: 200, data: { status: "step_up", method: "totp", challenge_id: id, expires_at: iso(exp) + "Z", risk: riskOut(sc, hits, decision) } };
  }

  async function signup({ username = "", password = "", device }, ctx) {
    if (!/^[A-Za-z0-9_.@-]{3,64}$/.test(username)) return err(400, "invalid_username", "Use 3–64 letters, digits or . _ @ -");
    if (password.length < 8 || password.length > 128) return err(400, "weak_password", "Use a password of 8 to 128 characters.");
    if (db.users[username]) return err(409, "username_taken", "That username is already registered.");
    const secret = b32secret();
    db.users[username] = { pw_hash: await hashPw(password), totp_secret: secret, totp_last_step: -1, created_at: iso(Date.now()) };
    const ev = makeEvent(username, ctx, true, device);
    storeEvent(ev, 0, [], "signup", "success"); recordAttempt(ev); recordSuccess(ev);
    const uri = `otpauth://totp/RiskLoginSim:${encodeURIComponent(username)}?secret=${secret}&issuer=RiskLoginSim`;
    return { status: 201, data: { status: "ok", totp_secret: secret, otpauth_uri: uri, ...session(username, device.id) } };
  }
  async function login({ username = "", password = "", device }, ctx) {
    const user = db.users[username];
    const pwOk = user ? await checkPw(password, user.pw_hash) : (await hashPw(password), false);
    const ev = makeEvent(username, ctx, pwOk, device);
    const { score: sc, hits } = score(extract(ev)), decision = decide(sc);
    recordAttempt(ev);
    if (!pwOk) {
      const row = storeEvent(ev, sc, hits, decision, "bad_password");
      if (decision === "step_up") return openChallenge(row, sc, hits, decision); // decoy: can never pass
      return { status: 401, data: DENIED };
    }
    if (decision === "block") { storeEvent(ev, sc, hits, decision, "blocked"); return { status: 401, data: DENIED }; }
    if (decision === "step_up") return openChallenge(storeEvent(ev, sc, hits, decision, "pending"), sc, hits, decision);
    storeEvent(ev, sc, hits, decision, "success"); recordSuccess(ev);
    return { status: 200, data: { status: "ok", risk: riskOut(sc, hits, decision), ...session(username, device.id) } };
  }
  async function stepUp({ challenge_id, code }) {
    const ch = db.challenges[challenge_id];
    if (!ch || ch.status !== "open") return err(410, "challenge_closed", "This sign-in request has ended. Sign in again.");
    const row = db.events.find((e) => e.id === ch.event_id), now = Date.now();
    if (now > ms(ch.expires_at)) { ch.status = "expired"; row.outcome = "challenge_expired"; return err(410, "challenge_expired", "The code request expired. Sign in again."); }
    const user = db.users[ch.username];
    if (row.password_ok && user && (await checkTotp(user, code, now))) {
      ch.status = "passed"; row.outcome = "success"; recordSuccess(row);
      return { status: 200, data: { status: "ok", ...session(row.username, row.device_id) } };
    }
    ch.attempts_left -= 1;
    if (ch.attempts_left <= 0) { ch.status = "failed"; if (row.password_ok) row.outcome = "challenge_failed"; return err(410, "challenge_failed", "Too many wrong codes. Sign in again."); }
    return err(401, "invalid_code", "That code didn't work.", { attempts_left: ch.attempts_left });
  }

  /* ---------- demo seed: an account with a normal week of history ---------- */
  async function seed() {
    const london = { city: "London", country: "GB", lat: 51.51, lon: -0.13 };
    const home = { ...london, ip: "81.2.69.10", asn: 60060, asn_type: "residential", label: "good" };
    const dev = { id: DEMO.device }, day = 24 * HOUR, start = Date.now() - 9 * day;
    const at = (d, h) => { const x = new Date(start + d * day); x.setUTCHours(h, Math.floor(Math.random() * 50), 0, 0); return iso(x.getTime()); };
    const r = await signup({ username: DEMO.username, password: DEMO.password, device: dev }, { ...home, ts: at(0, 10) });
    for (const [d, h] of [[1, 9], [2, 13], [3, 18], [4, 9], [5, 12], [6, 19], [7, 10], [8, 14]]) {
      await login({ username: DEMO.username, password: DEMO.password, device: dev }, { ...home, ts: at(d, h) });
    }
    db.sessions = {}; db.seeded = true;
    return r.data.totp_secret;
  }

  async function init() {
    db = load();
    rebuild();
    if (!db.seeded) {
      const secret = await seed();
      const d = store.get("demoSecrets", {}); d[DEMO.username] = secret; store.set("demoSecrets", d);
      save();
    }
  }

  /* ---------- router ---------- */
  async function handle(path, { method = "GET", headers = {}, body } = {}) {
    ready ||= init();
    await ready;
    const ctx = headers["X-Sim-Context"] ? JSON.parse(headers["X-Sim-Context"]) : {};
    if (ctx.ts) ctx.ts = String(ctx.ts).replace(/Z$/, "").slice(0, 23);
    const [route, query] = path.split("?");
    let res;
    if (route === "/health") res = { status: 200, data: { status: "ok", sim_mode: true, demo: true } };
    else if (route === "/signup" && method === "POST") res = await signup(body, ctx);
    else if (route === "/login" && method === "POST") res = await login(body, ctx);
    else if (route === "/login/step-up" && method === "POST") res = await stepUp(body);
    else if (route === "/me" || route === "/logout") {
      const token = (headers.Authorization || "").replace(/^Bearer /, ""), s = db.sessions[token];
      if (!s || Date.now() > ms(s.expires_at)) res = err(401, "unauthenticated", "Sign in to continue.");
      else if (route === "/logout") { delete db.sessions[token]; res = { status: 204, data: {} }; }
      else res = { status: 200, data: { username: s.username, device_id: s.device_id, expires_at: s.expires_at + "Z" } };
    } else if (route === "/admin/events") {
      const limit = Math.min(Math.max(parseInt(new URLSearchParams(query).get("limit") || "100", 10), 1), 1000);
      res = { status: 200, data: db.events.slice(-limit).reverse() };
    } else res = err(404, "not_found", "Not found.");
    save();
    return res;
  }
  function reset() { try { localStorage.removeItem(KEY); } catch {} db = blank(); ready = null; }
  return { handle, reset, DEMO };
})();
