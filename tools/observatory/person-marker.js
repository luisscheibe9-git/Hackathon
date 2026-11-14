// Person marker, presence state machine, side panel and the simulated fall demo for the
// Stillpoint Observatory. Kept out of observatory.js so merges with live-capture work stay easy.
//
// Honesty rules (hackathon judging disqualifies faked sensing):
//  - The figure stands on an ESTIMATED ZONE (midpoint of the most disturbed path, or a
//    disturbance-weighted blend of path midpoints), never a measured x/y spot. The halo
//    radius shows the uncertainty: large with one path, smaller when several paths agree.
//  - No heart-rate or respiration numbers. `?breathing=1` only shows the words
//    "breathing band: experimental".
//  - The fall rule is untested on real falls, so it is OFF in live/replay unless `?fall=1`.
//    `?demo=fall` runs a scripted, clearly labelled "simulated" sequence.
//
// URL flags: ?replay=1 (detection/replay.py), ?demo=fall, ?fall=1, ?door=<receiver port>,
// ?emptyAfter=<seconds> (default 900), ?breathing=1.
import * as THREE from "three";

const params = new URLSearchParams(location.search);
export const demoMode = params.get("demo") === "fall";
const replayMode = params.has("replay");
const fallRuleOn = demoMode || params.get("fall") === "1";
const doorPort = params.get("door");
const emptyAfterS = Number(params.get("emptyAfter") || 900);
const showBreathing = params.get("breathing") === "1";

const FALLBACK_THRESHOLD = 0.15; // team change score: walking ~0.19, empty ~0.10, standing ~0.09
export const P_HIGH = 0.7;
const P_LOW = 0.3;
const FALL = { burstRatio: 2.5, burstP: 0.95, stillBeforeSuspectS: 2, alertAfterS: demoMode ? 6 : 20 };

// ---------------- presence state machine ----------------
export class PresenceStateMachine {
  constructor() { this.reset(); }
  reset() {
    this.state = "EMPTY";
    this.moving = false;
    this.since = performance.now();
    this.lastMotion = -Infinity;
    this.movingTicks = 0;
    this.burstAt = -Infinity;
    this.doorAt = -Infinity;
    this.fallAt = null;
  }
  set(state, now) { if (state !== this.state) { this.state = state; this.since = now; } }
  // moving: bool, burst: bool (very strong disturbance), door: bool (doorway path active)
  step({ moving, burst, door }, now) {
    this.moving = moving;
    this.movingTicks = moving ? this.movingTicks + 1 : 0;
    if (moving) this.lastMotion = now;
    if (burst) this.burstAt = now;
    if (door) this.doorAt = now;
    const quietS = (now - this.lastMotion) / 1000;
    switch (this.state) {
      case "EMPTY":
        if (this.movingTicks >= 2) this.set("PRESENT", now);
        break;
      case "PRESENT":
        if (fallRuleOn && !moving && now - this.burstAt < 4000 && quietS >= FALL.stillBeforeSuspectS) {
          this.fallAt = new Date();
          this.set("FALL_SUSPECTED", now);
        } else if (doorPort && now - this.doorAt < 20000 && quietS > 15) {
          this.set("EMPTY", now); // left through the doorway path, then quiet
        } else if (quietS > emptyAfterS) {
          this.set("EMPTY", now); // long empty timeout
        }
        break;
      case "FALL_SUSPECTED":
        if (this.movingTicks >= 3) this.set("PRESENT", now); // got up / moving normally again
        else if ((now - this.since) / 1000 >= FALL.alertAfterS) this.set("FALL_ALERT", now);
        break;
      case "FALL_ALERT":
        break; // stays until a caregiver acknowledges (reload) - deliberate
    }
    return this.state;
  }
}

// ---------------- scripted fall demo (simulated, not sensed) ----------------
const DEMO_PATHS = ["sim-receiver-A", "sim-receiver-B"];
const demoHistory = new Map(DEMO_PATHS.map(p => [p, []]));
// timeline seconds: 0-4 empty, 4-14 walk in, 14-22 stand still, 22-23 fall impact, then lie still
export function demoReceivers(nowMs) {
  const t = (nowMs / 1000) % 60;
  const noise = () => (Math.random() - 0.5) * 0.02;
  return DEMO_PATHS.map((port, i) => {
    let motion = 0.09, p = 0.02;
    if (t >= 4 && t < 14) { const near = i === 0 ? (t < 9 ? 1 : 0.55) : (t < 9 ? 0.45 : 1); motion = 0.11 + 0.12 * near; p = 0.35 + 0.6 * near; }
    else if (t >= 22 && t < 23) { motion = 0.62; p = 0.99; }
    motion += noise();
    const hist = demoHistory.get(port);
    hist.push([nowMs, motion]);
    while (hist.length && hist[0][0] < nowMs - 30000) hist.shift();
    return { port, motion, rate: 30, rssi: -58 - 6 * i, status: "Simulated", p_moving: p,
      label: p >= P_HIGH ? "moving" : p <= P_LOW ? "still" : "unknown",
      samples: hist.map(([ts, m]) => [(nowMs - ts) / 1000, m]) };
  });
}

// ---------------- 3D figure ----------------
function glowTexture() {
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const g = c.getContext("2d");
  const grad = g.createRadialGradient(64, 64, 4, 64, 64, 64);
  grad.addColorStop(0, "rgba(255,255,255,0.9)");
  grad.addColorStop(0.35, "rgba(255,255,255,0.35)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}

function makeFigure(scene) {
  const mat = (opacity) => new THREE.MeshBasicMaterial({ color: 0x51ffb0, transparent: true, opacity,
    blending: THREE.AdditiveBlending, depthWrite: false });
  const root = new THREE.Group();   // sits on the floor at the zone
  const body = new THREE.Group();   // pivots at the feet so it can tip over
  root.add(body);
  const parts = [];
  const add = (mesh, glow) => { body.add(mesh); parts.push({ mesh, base: glow }); return mesh; };
  // ~1.7 m: legs+torso capsule, head sphere, outer glow shells
  add(new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 1.0, 6, 14), mat(0.8)), 0.8).position.y = 0.67;
  add(new THREE.Mesh(new THREE.SphereGeometry(0.13, 16, 12), mat(0.85)), 0.85).position.y = 1.55;
  add(new THREE.Mesh(new THREE.CapsuleGeometry(0.28, 1.05, 6, 14), mat(0.22)), 0.22).position.y = 0.72;
  add(new THREE.Mesh(new THREE.SphereGeometry(0.24, 16, 12), mat(0.2)), 0.2).position.y = 1.55;
  const halo = new THREE.Mesh(new THREE.CircleGeometry(1, 48),
    new THREE.MeshBasicMaterial({ map: glowTexture(), color: 0x51ffb0, transparent: true, opacity: 0.55,
      blending: THREE.AdditiveBlending, depthWrite: false }));
  halo.rotation.x = -Math.PI / 2;
  halo.position.y = -0.04;
  root.add(halo);
  root.visible = false;
  scene.add(root);
  return { root, body, parts, halo };
}

// ---------------- panel + overlay DOM ----------------
function el(tag, cls, parent, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  parent.append(e);
  return e;
}

export function createPersonLayer({ scene, stage, positionLabel }) {
  const fig = makeFigure(scene);
  const fsm = new PresenceStateMachine();
  const badge = el("div", "marker person-badge", stage, "PRESENT");
  const caption = el("div", "marker person-caption", stage, "estimated zone");
  badge.hidden = caption.hidden = true;
  const banner = el("div", "fall-banner", stage);
  banner.hidden = true;
  const panel = el("aside", "person-panel", stage);
  panel.setAttribute("aria-label", "Presence status");
  const rows = {};
  el("h3", "", panel, "Presence");
  for (const [key, label] of [["state", "State"], ["motion", "Motion score"], ["p", "P(moving)"],
    ["rssi", "RSSI"], ["path", "Active path"], ["conf", "Confidence"], ["fall", "Fall rule"]]) {
    const row = el("div", "row", panel);
    el("span", "", row, label);
    rows[key] = el("b", "", row, "—");
  }
  if (showBreathing) { const row = el("div", "row", panel); el("span", "", row, "Breathing band"); el("b", "", row, "experimental"); }
  if (demoMode) {
    el("p", "sim-note", panel, "SIMULATED sequence (?demo=fall): scripted walk in, stand, fall. Not sensor data.");
    const sub = document.querySelector("header p");
    if (sub) sub.textContent = "Simulated fall demo · scripted, not sensor data";
    const tag = el("div", "sim-tag", stage, "SIMULATED");
    tag.title = "Scripted demo, not sensed";
  }
  if (replayMode || demoMode) { // the live calibration panel does not apply here
    const cal = document.querySelector("section.detection:not(.replay)");
    if (cal) cal.hidden = true;
  }
  rows.fall.textContent = fallRuleOn ? (demoMode ? "on (simulated)" : "on (untested on real falls)") : "off (no fall data yet)";

  const zone = new THREE.Vector3();
  const target = new THREE.Vector3();
  let haveZone = false, haloRadius = 1.1, lastTick = performance.now();
  let lastFrame = null;
  let tip = 0, info = { state: "EMPTY" };

  function update(receivers, links, thresholds) {
    const now = performance.now();
    const dt = Math.min(1, (now - lastTick) / 1000);
    lastTick = now;
    const paths = [];
    for (const r of receivers) {
      const link = links.get(r.port);
      if (!link || r.motion == null) continue;
      if (r.model_active && r.p_moving == null) continue;
      const thr = thresholds?.get(r.port) ?? FALLBACK_THRESHOLD;
      const ratio = r.motion / thr;
      // disturbance in [0,1]: detector probability if we have it, else motion vs threshold
      const d = r.p_moving != null ? r.p_moving : Math.min(1, Math.max(0, (ratio - 0.6) / 0.8));
      const moving = r.p_moving != null ? r.p_moving >= P_HIGH : ratio >= 1;
      const burst = ratio >= FALL.burstRatio || (r.p_moving != null && r.p_moving >= FALL.burstP && r.motion >= 0.4);
      paths.push({ r, link, d, moving, burst, calibrated: thresholds?.has(r.port) || r.p_moving != null });
    }
    const moving = paths.some(p => p.moving);
    const state = fsm.step({ moving, burst: paths.some(p => p.burst), door: paths.some(p => p.r.port === doorPort && p.moving) }, now);
    const top = paths.reduce((a, b) => (!a || b.d > a.d ? b : a), null);
    const agreeing = paths.filter(p => p.d >= 0.5);
    if (moving && agreeing.length) {
      // estimated zone: weighted blend of the midpoints of the disturbed paths
      target.set(0, 0, 0);
      let w = 0;
      for (const p of agreeing) {
        const mid = new THREE.Vector3().lerpVectors(p.link.start, p.link.endpoint, 0.55);
        target.addScaledVector(mid, p.d);
        w += p.d;
      }
      target.multiplyScalar(1 / w);
      target.y = 0;
      if (!haveZone) { zone.copy(target); haveZone = true; }
      haloRadius += ((agreeing.length >= 2 ? 1.1 / Math.sqrt(agreeing.length) : 1.1) - haloRadius) * (1 - Math.exp(-dt));
    }
    if (state === "EMPTY") haveZone = false;
    const nPaths = paths.length;
    const conf = !nPaths ? "none" : state !== "EMPTY" && !moving ? "zone held from last motion" : !paths.some(p => p.calibrated) ? "low (uncalibrated)" :
      nPaths === 1 ? "low (1 path, zone only)" : agreeing.length >= 2 ? "medium (" + agreeing.length + " paths agree)" : "low (1 of " + nPaths + " paths)";
    info = { state, moving, top, conf };
    rows.state.textContent = state.replace("_", " ") + (state === "PRESENT" ? (moving ? " · moving" : " · still") : "");
    rows.state.dataset.state = state;
    rows.motion.textContent = top ? top.r.motion.toFixed(3) : "—";
    rows.p.textContent = top?.r.p_moving != null ? top.r.p_moving.toFixed(2) : "n/a (no model in live stream)";
    rows.rssi.textContent = top?.r.rssi != null ? top.r.rssi + " dBm" : "—";
    rows.path.textContent = top && top.d >= 0.5 ? top.r.port : "none";
    rows.conf.textContent = conf;
    if (state === "FALL_SUSPECTED" || state === "FALL_ALERT") {
      banner.hidden = false;
      banner.dataset.level = state;
      const where = top ? "near path " + top.r.port : "last zone";
      const when = (fsm.fallAt || new Date()).toLocaleTimeString();
      banner.textContent = (state === "FALL_ALERT" ? "FALL ALERT" : "Fall suspected") + " · zone " + where + " · " + when +
        (demoMode ? " · SIMULATED" : "");
    } else banner.hidden = true;
  }

  function frame(time) {
    const dt = lastFrame == null ? 0 : Math.max(0, Math.min(0.1, (time - lastFrame) / 1000));
    lastFrame = time;
    const s = info.state;
    const show = s !== "EMPTY" && haveZone;
    fig.root.visible = show;
    badge.hidden = caption.hidden = !show;
    if (!show) return;
    // Finish sliding to the last observed zone even if this motion burst ends.
    zone.lerp(target, 1 - Math.exp(-dt / 0.22));
    fig.root.position.copy(zone);
    const fallen = s === "FALL_SUSPECTED" || s === "FALL_ALERT";
    tip += ((fallen ? 1 : 0) - tip) * 0.06;
    fig.body.rotation.z = -tip * Math.PI / 2;
    const color = s === "FALL_ALERT" ? 0xff3b3b : s === "FALL_SUSPECTED" ? 0xffb020 : 0x51ffb0;
    // moving: bright with a gentle pulse; still: dimmer with a slow breathing-like pulse (visual only)
    const pulse = fallen ? 0.8 + 0.2 * Math.sin(time / 180) :
      info.moving ? 0.9 + 0.1 * Math.sin(time / 260) : 0.42 + 0.1 * Math.sin(time / 1300);
    for (const { mesh, base } of fig.parts) { mesh.material.color.setHex(color); mesh.material.opacity = base * pulse; }
    fig.halo.material.color.setHex(color);
    fig.halo.material.opacity = 0.5 * pulse;
    fig.halo.scale.setScalar(haloRadius);
    badge.textContent = s === "PRESENT" ? (info.moving ? "MOTION" : "LAST MOTION") : s === "FALL_ALERT" ? "FALL ALERT" : "FALL SUSPECTED";
    badge.dataset.state = s;
    const head = new THREE.Vector3(zone.x - tip * 1.55, 1.85 - tip * 1.5, zone.z);
    positionLabel(badge, head);
    positionLabel(caption, new THREE.Vector3(zone.x, -0.05, zone.z + haloRadius * 0.6));
  }

  return { update, frame, fsm };
}
