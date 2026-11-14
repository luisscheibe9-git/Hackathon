import * as THREE from "three";
import { PresenceCartography } from "./vendor/presence-cartography.js";
import { createPersonLayer, demoMode, demoReceivers } from "./person-marker.js";

const scene = new THREE.Scene();
const stage = document.querySelector("#scene");
const status = document.querySelector("#status");
const motionStatus = document.querySelector("#motion-status");
const motionDetail = document.querySelector("#motion-detail");
const calibrate = document.querySelector("#calibrate");
const transmitterLabel = document.querySelector("#transmitter");
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
} catch (error) {
  status.textContent = "3D view requires WebGL";
  throw error;
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
stage.append(renderer.domElement);
const camera = new THREE.PerspectiveCamera(44, 1, 0.1, 50);
const floor = new THREE.GridHelper(5.3, 20, 0x365779, 0x263c56);
floor.position.set(-0.12, -0.06, -0.12);
scene.add(floor);
const field = new PresenceCartography(scene);
field.setQuality(0);
const router = new THREE.Vector3(0, 0.18, -1.8);
const receiverPositions = [new THREE.Vector3(-1.8, 0.18, 1.55), new THREE.Vector3(1.55, 0.18, 1.55)];
const colors = [0x51e9c6, 0x8dbaff, 0xffb86b, 0xd99bff, 0xff7f9f];
// Receivers beyond the first two are spread on an arc opposite the router (schematic only).
function receiverPosition(index) {
  if (index < receiverPositions.length) return receiverPositions[index];
  const angle = Math.PI * (0.15 + 0.7 * ((index - 2) % 5) / 4);
  return new THREE.Vector3(-2.1 * Math.cos(angle), 0.18, -1.8 + 3.6 * Math.sin(angle));
}
const replayMode = new URLSearchParams(location.search).has("replay");
const wire = new THREE.Mesh(new THREE.SphereGeometry(0.56, 18, 10),
  new THREE.MeshBasicMaterial({ color: 0x617aff, wireframe: true, transparent: true, opacity: 0.32 }));
wire.position.copy(router);
wire.position.y = 0.5;
scene.add(wire);

const links = new Map();
const tiles = new Float32Array(400);
let calibration = null;
let thresholds = new Map();
let livePorts = [];
let lastMotion = -Infinity;
let activePath = null;
const motionMarker = document.createElement("div");
motionMarker.className = "marker motion-marker";
motionMarker.hidden = true;
motionMarker.textContent = "Motion on this path";
stage.append(motionMarker);
const markerPosition = new THREE.Vector3();
const person = createPersonLayer({ scene, stage, camera, router, positionLabel });
const liveFetch = demoMode ? async () => new Response(JSON.stringify(demoReceivers(performance.now()))) : fetch.bind(window);

calibrate.addEventListener("click", () => {
  const start = performance.now() + 7000;
  calibration = { start, end: start + 12000, byPort: new Map(livePorts.map(port => [port, []])) };
  thresholds = new Map();
  lastMotion = -Infinity;
  activePath = null;
  calibrate.disabled = true;
});

function detectMotion(receivers) {
  const now = performance.now();
  const live = receivers.filter(receiver => receiver.motion !== null && receiver.rate >= 5);
  livePorts = live.map(receiver => receiver.port);
  calibrate.disabled = !!calibration || !live.length;
  motionStatus.dataset.active = "false";
  if (calibration) {
    if (now < calibration.start) {
      motionStatus.textContent = "Leave the room in " + Math.ceil((calibration.start - now) / 1000) + "s";
      motionDetail.textContent = "Keep the transmitter and receivers fixed.";
      return;
    }
    if (now < calibration.end) {
      for (const { port, motion } of live) calibration.byPort.get(port)?.push(motion);
      motionStatus.textContent = "Recording quiet baseline · " + Math.ceil((calibration.end - now) / 1000) + "s";
      motionDetail.textContent = "Keep the monitored area empty.";
      return;
    }
    for (const [port, values] of calibration.byPort) {
      if (values.length < 24) continue;
      values.sort((a, b) => a - b);
      const median = values[Math.floor(values.length / 2)];
      const upper = values[Math.floor(values.length * 0.9)];
      thresholds.set(port, Math.max(upper + 0.02, median + 0.035));
    }
    calibration = null;
    calibrate.disabled = !live.length;
    if (!thresholds.size) {
      motionStatus.textContent = "Calibration incomplete";
      motionDetail.textContent = "Too few live readings. Try again with the receivers connected.";
      return;
    }
  }
  const calibrated = live.filter(({ port }) => thresholds.has(port));
  const active = calibrated.filter(({ port, motion }) => motion >= thresholds.get(port));
  if (!calibrated.length) {
    activePath = null;
    motionStatus.textContent = thresholds.size ? "Motion status unavailable" : "Calibration needed";
    motionDetail.textContent = "Clear the room before recording the quiet baseline.";
    return;
  }
  if (active.length) {
    lastMotion = now;
    activePath = active.length === 1 ? active[0].port : null;
    motionDetail.textContent = "Activity above the quiet baseline on " + active.map(({port}) => port).join(" and ") + ".";
  }
  const moving = now - lastMotion < 1300;
  motionStatus.dataset.active = String(moving);
  motionStatus.textContent = moving ? "Motion detected" : "No motion detected";
  if (!moving) {
    activePath = null;
    motionDetail.textContent = "Occupancy is unknown when someone is still.";
  }
}

function makeLink(port, index) {
  const endpoint = receiverPosition(index);
  const color = colors[index % colors.length];
  const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.3 });
  const path = new THREE.Line(new THREE.BufferGeometry().setFromPoints([router, endpoint]), material);
  const packet = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 8),
    new THREE.MeshBasicMaterial({ color }));
  const node = new THREE.Mesh(new THREE.BoxGeometry(0.19, 0.27, 0.19),
    new THREE.MeshBasicMaterial({ color, wireframe: true }));
  node.position.copy(endpoint);
  scene.add(path, packet, node);

  const marker = document.createElement("div");
  marker.className = "marker";
  marker.textContent = port;
  document.querySelector("#markers").append(marker);

  const card = document.createElement("article");
  card.innerHTML = "<header><h2></h2><span></span></header><p></p><canvas width='600' height='90' aria-label='CSI change over the last 30 seconds'></canvas>";
  card.querySelector("h2").textContent = port;
  document.querySelector("#receivers").append(card);
  return { endpoint, material, packet, marker, card, motion: null };
}

function positionLabel(element, point) {
  const projected = point.clone().project(camera);
  element.style.left = ((projected.x + 1) * stage.clientWidth / 2) + "px";
  element.style.top = ((1 - projected.y) * stage.clientHeight / 2) + "px";
}

function updateTrace(link, receiver) {
  link.motion = receiver.motion;
  const message = receiver.status;
  link.card.querySelector("span").textContent = message.includes("Access is denied") ? "Serial port in use" :
    message.includes("FileNotFoundError") ? "Board disconnected" : message;
  link.card.querySelector("p").textContent = receiver.motion === null ? "Waiting for live samples" :
    "CSI " + receiver.motion.toFixed(3) + "   ·   " + receiver.rate.toFixed(1) + " frames/s   ·   " + receiver.rssi + " dBm" +
    (receiver.label ? "   ·   model: " + receiver.label + (receiver.p_moving == null ? "" : " (P(moving) " + receiver.p_moving.toFixed(2) + ")") : "");
  const canvas = link.card.querySelector("canvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#" + link.material.color.getHexString();
  ctx.lineWidth = 3;
  ctx.beginPath();
  for (const [age, change] of receiver.samples) {
    ctx.lineTo((30 - age) * canvas.width / 30, (1 - Math.min(1, change / 0.55)) * canvas.height);
  }
  ctx.stroke();
}

function updateFloor() {
  tiles.fill(0);
  for (const link of links.values()) {
    const strength = link.motion === null ? 0 : Math.min(1, link.motion / 0.3);
    link.material.opacity = 0.17 + strength * 0.7;
    link.packet.visible = link.motion !== null;
    const dx = link.endpoint.x - router.x;
    const dz = link.endpoint.z - router.z;
    for (let i = 0; i < tiles.length; i++) {
      const x = (i % 20 - 10) * 0.242;
      const z = (Math.floor(i / 20) - 10) * 0.242;
      const t = Math.min(1, Math.max(0, ((x - router.x) * dx + (z - router.z) * dz) / (dx * dx + dz * dz)));
      const distance = Math.hypot(x - router.x - t * dx, z - router.z - t * dz);
      tiles[i] = Math.max(tiles[i], strength * Math.exp(-distance * distance / 0.28));
    }
  }
  field.update(0, 0, { signal_field: { values: tiles } });
}

async function readLive() {
  try {
    const response = await liveFetch("/live", { signal: AbortSignal.timeout(2000) });
    if (!response.ok) throw new Error(response.status);
    const source = response.headers.get("X-Stillpoint-Source");
    transmitterLabel.textContent = source === "esp32" ? "ESP32 transmitter" :
      source === "router" ? "Wi-Fi router" : "Wi-Fi transmitter";
    const receivers = await response.json();
    detectMotion(receivers);
    for (const [index, receiver] of (replayMode ? receivers : receivers.slice(0, 2)).entries()) {
      if (!links.has(receiver.port)) links.set(receiver.port, makeLink(receiver.port, index));
      updateTrace(links.get(receiver.port), receiver);
    }
    person.update(receivers, links, thresholds);
    const count = receivers.filter(receiver => receiver.motion !== null).length;
    status.textContent = count ? count + (count === 1 ? " receiver" : " receivers") + (replayMode ? " replaying" : demoMode ? " simulated" : " live") : "Waiting for CSI";
    if (replayMode && !demoMode) await readReplay();
  } catch {
    detectMotion([]);
    for (const [port, link] of links) updateTrace(link, { port, motion: null, status: "Disconnected", samples: [] });
    status.textContent = "Capture service disconnected";
  } finally {
    updateFloor();
    setTimeout(readLive, 300);
  }
}

// ---- offline replay (detection/replay.py serves /replay/*; live mode never runs this) ----
const replayBar = document.querySelector("#replay");
const replaySeek = document.querySelector("#replay-seek");
const replayToggle = document.querySelector("#replay-toggle");
let seeking = false;
function fmt(seconds) { return Math.floor(seconds / 60) + ":" + String(Math.floor(seconds % 60)).padStart(2, "0"); }
async function replayControl(query) { await fetch("/replay/control?" + query); }
if (replayMode) {
  replayBar.hidden = false;
  document.querySelector("header p").textContent = "Offline replay of a saved CSI recording";
  replayToggle.addEventListener("click", () => replayControl("cmd=" + (replayToggle.textContent === "Pause" ? "pause" : "play")));
  replaySeek.addEventListener("input", () => { seeking = true; });
  replaySeek.addEventListener("change", () => { seeking = false; replayControl("cmd=seek&t=" + replaySeek.value); });
  document.querySelector("#replay-speed").addEventListener("change", (e) => replayControl("speed=" + e.target.value));
}
async function readReplay() {
  const state = await (await fetch("/replay/state")).json();
  const verdict = document.querySelector("#replay-verdict");
  verdict.textContent = state.verdict;
  verdict.dataset.level = state.verdict.startsWith("Likely") ? "moving" : state.verdict.startsWith("No movement") ? "still" : "unknown";
  const paths = state.paths.map(p => p.port + " " + (p.p_moving == null ? "n/a" : p.p_moving.toFixed(2))).join(" · ");
  document.querySelector("#replay-detail").textContent = fmt(state.t) + " / " + fmt(state.duration) +
    "   ·   recorded: " + (state.truth || "gap") + "   ·   P(moving) per path: " + paths;
  replayToggle.textContent = state.playing ? "Pause" : "Play";
  replaySeek.max = state.duration;
  if (!seeking) replaySeek.value = state.t;
  for (const [port, link] of links) link.card.style.borderColor = state.top === port && state.verdict.startsWith("Likely") ? "#ffcf6e" : "";
}

new ResizeObserver(() => {
  const width = stage.clientWidth;
  const height = stage.clientHeight;
  camera.aspect = width / height;
  const distance = Math.max(1, 1.12 / camera.aspect);
  camera.position.set(4.25 * distance, 4.6 * distance, 5.7 * distance);
  camera.lookAt(0, 0, 0);
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}).observe(stage);

renderer.setAnimationLoop((time) => {
  wire.rotation.y = time / 2200;
  positionLabel(transmitterLabel, wire.position);
  for (const link of links.values()) {
    link.packet.position.lerpVectors(router, link.endpoint, (time % 1250) / 1250);
    positionLabel(link.marker, link.endpoint);
  }
  const activeLink = links.get(activePath);
  motionMarker.hidden = !activeLink;
  if (activeLink) {
    markerPosition.lerpVectors(router, activeLink.endpoint, 0.55);
    markerPosition.y = 0.47;
    positionLabel(motionMarker, markerPosition);
  }
  person.frame(time);
  renderer.render(scene, camera);
});
readLive();
