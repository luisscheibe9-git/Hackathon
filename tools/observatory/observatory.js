import * as THREE from "three";
import { PresenceCartography } from "./vendor/presence-cartography.js";

const scene = new THREE.Scene();
const stage = document.querySelector("#scene");
const status = document.querySelector("#status");
const motionStatus = document.querySelector("#motion-status");
const motionDetail = document.querySelector("#motion-detail");
const calibrate = document.querySelector("#calibrate");
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
const colors = [0x51e9c6, 0x8dbaff];
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

calibrate.addEventListener("click", () => {
  const start = performance.now() + 7000;
  calibration = { start, end: start + 12000, byPort: new Map(livePorts.map(port => [port, []])) };
  thresholds = new Map();
  lastMotion = -Infinity;
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
      motionDetail.textContent = "Keep the router and ESP32s fixed.";
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
    motionStatus.textContent = thresholds.size ? "Motion status unavailable" : "Calibration needed";
    motionDetail.textContent = "Clear the room before recording the quiet baseline.";
    return;
  }
  if (active.length) {
    lastMotion = now;
    motionDetail.textContent = "Activity above the quiet baseline on " + active.map(({port}) => port).join(" and ") + ".";
  }
  const moving = now - lastMotion < 1300;
  motionStatus.dataset.active = String(moving);
  motionStatus.textContent = moving ? "Motion detected" : "No motion detected";
  if (!moving) motionDetail.textContent = "Occupancy is unknown when someone is still.";
}

function makeLink(port, index) {
  const endpoint = receiverPositions[index];
  const color = colors[index];
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
    "CSI " + receiver.motion.toFixed(3) + "   ·   " + receiver.rate.toFixed(1) + " frames/s   ·   " + receiver.rssi + " dBm";
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
    const response = await fetch("/live", { signal: AbortSignal.timeout(2000) });
    if (!response.ok) throw new Error(response.status);
    const receivers = await response.json();
    detectMotion(receivers);
    for (const [index, receiver] of receivers.slice(0, 2).entries()) {
      if (!links.has(receiver.port)) links.set(receiver.port, makeLink(receiver.port, index));
      updateTrace(links.get(receiver.port), receiver);
    }
    const count = receivers.filter(receiver => receiver.motion !== null).length;
    status.textContent = count ? count + (count === 1 ? " receiver live" : " receivers live") : "Waiting for CSI";
  } catch {
    detectMotion([]);
    for (const [port, link] of links) updateTrace(link, { port, motion: null, status: "Disconnected", samples: [] });
    status.textContent = "Capture service disconnected";
  } finally {
    updateFloor();
    setTimeout(readLive, 300);
  }
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
  positionLabel(document.querySelector("#router"), wire.position);
  for (const link of links.values()) {
    link.packet.position.lerpVectors(router, link.endpoint, (time % 1250) / 1250);
    positionLabel(link.marker, link.endpoint);
  }
  renderer.render(scene, camera);
});
readLive();
