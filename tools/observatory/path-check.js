import { P_HIGH } from "./person-marker.js?v=peer-path-1";

const ports = ["ESP32 #2", "ESP32 #3"];
const phases = [
  { title: "Clear both paths", detail: "Move outside the triangle and stop moving. Keep all three boards fixed.", seconds: 5 },
  { title: "Quiet baseline", detail: "Stay still outside the triangle.", seconds: 8, collect: "quiet" },
  { title: "Walk across #1 → #2", detail: "Cross the middle of the #1–#2 path back and forth. Stay away from the #1–#3 path.", seconds: 12, collect: "left" },
  { title: "Switch sides", detail: "Move toward the #1–#3 path.", seconds: 5 },
  { title: "Walk across #1 → #3", detail: "Cross the middle of the #1–#3 path back and forth. Stay away from the #1–#2 path.", seconds: 12, collect: "right" },
];

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function highShare(values) {
  return values.filter(value => value >= P_HIGH).length / values.length;
}

export function createPathCheck() {
  const panel = document.querySelector("#path-check");
  const status = document.querySelector("#path-check-status");
  const detail = document.querySelector("#path-check-detail");
  const button = document.querySelector("#path-check-button");
  let run = null;
  const show = (title, text) => {
    status.textContent = title;
    detail.textContent = text;
  };
  button.addEventListener("click", () => {
    if (run) {
      run = null;
      button.textContent = "Start path check";
      show("Path check canceled", "Start again when both paths are clear.");
      return;
    }
    run = { phase: 0, start: performance.now(), scores: { quiet: [[], []], left: [[], []], right: [[], []] } };
    button.textContent = "Cancel path check";
    show(phases[0].title, phases[0].detail);
  });

  function finish() {
    const { quiet, left, right } = run.scores;
    run = null;
    button.textContent = "Run again";
    if ([...quiet, ...left, ...right].some(values => values.length < 8)) {
      show("Not enough live data", "Check that both receivers are streaming, then run the path check again.");
      return;
    }
    const pct = value => Math.round(value * 100) + "%";
    const pair = values => values.map(pct).join(" / ");
    const baseline = quiet.map(highShare);
    const across2 = left.map(highShare);
    const across3 = right.map(highShare);
    const quietEnough = baseline.every(value => value <= 0.15);
    const separate = across2[0] >= 0.25 && across3[1] >= 0.25 &&
      across2[0] - across2[1] >= 0.15 && across3[1] - across3[0] >= 0.15;
    const note = "Share of updates above the motion threshold (#2 / #3): quiet " + pair(baseline) +
      "; across #2 " + pair(across2) + "; across #3 " + pair(across3) + ". ";
    const weak = left[0].length && mean(left[0]) <= mean(quiet[0]) ? "#2" :
      mean(right[1]) <= mean(quiet[1]) ? "#3" : null;
    show(!quietEnough ? "The baseline picked up motion" : separate ? "Both paths responded separately" : "The two paths did not separate clearly",
      note + (!quietEnough ? "Keep the room and nearby traffic quiet, then retry." :
        separate ? "Try walking slowly across both paths in sequence. The marker shows the strongest motion zone." :
        weak ? "Check the placement and antenna on " + weak + ", then retry." :
        "Cross one path at a time away from the gateway. If it still overlaps, adjust the board placement and rerun."));
  }

  function update(available, receivers) {
    const ready = available && ports.every(port => receivers.some(r => r.port === port && r.rate >= 5 && Number.isFinite(r.p_moving)));
    panel.hidden = !available && !run;
    button.disabled = !run && !ready;
    if (!run) return;
    const now = performance.now();
    let phase = phases[run.phase];
    if (now - run.start >= phase.seconds * 1000) {
      if (++run.phase === phases.length) {
        finish();
        return;
      }
      run.start = now;
      phase = phases[run.phase];
    }
    const elapsed = (now - run.start) / 1000;
    show(phase.title + " · " + Math.ceil(phase.seconds - elapsed) + "s",
      ready ? phase.detail : "Receiver data missing. This run may be incomplete.");
    // Ignore the first two seconds after each cue so the previous motion window can clear.
    if (ready && phase.collect && elapsed >= 2) {
      ports.forEach((port, i) => run.scores[phase.collect][i].push(receivers.find(r => r.port === port).p_moving));
    }
  }

  return { update };
}
