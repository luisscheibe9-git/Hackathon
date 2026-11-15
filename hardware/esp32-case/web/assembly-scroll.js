// Scroll-scrubbed product assembly: parts drop in from above as the page scrolls.
// No dependencies. Frames are transparent WebP renders from blender/build_scene.py.
//
//   <script src="assembly-scroll.js"></script>      (plain script: also works from file://)
//   mountAssembly(document.querySelector('.assembly'), { src: 'frames/frame_%03d.webp', count: 96 });
//
// Markup: <section class="assembly"><div class="assembly-stage"><canvas></canvas>
//           <p class="assembly-caption" data-from="1" data-to="20">...</p>...</div></section>
// The section's height sets the scroll distance; the stage is position: sticky.

function mountAssembly(section, { src, count, start = 1 }) {
  const stage = section.querySelector('.assembly-stage');
  const canvas = stage.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const captions = [...stage.querySelectorAll('[data-from]')];
  const frames = new Array(count);
  const url = (i) => src.replace(/%0(\d)d/, (_, w) => String(i + start).padStart(+w, '0'));
  let current = -1;
  let pending = false;

  function load(i) {
    if (frames[i]) return frames[i];
    const img = new Image();
    img.decoding = 'async';
    img.src = url(i);
    frames[i] = img;
    img.onload = () => { if (Math.abs(i - target()) < 2) draw(true); };
    return img;
  }

  // nearest frame that has finished loading, so fast scrolling never shows a blank
  function nearestLoaded(i) {
    for (let d = 0; d < count; d++) {
      for (const j of [i - d, i + d]) {
        const f = frames[j];
        if (j >= 0 && j < count && f && f.complete && f.naturalWidth) return f;
      }
    }
    return null;
  }

  function progress() {
    const r = section.getBoundingClientRect();
    const travel = r.height - window.innerHeight;
    return travel > 0 ? Math.min(1, Math.max(0, -r.top / travel)) : 0;
  }

  const target = () => Math.round(progress() * (count - 1));

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const { width, height } = canvas.getBoundingClientRect();
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    draw(true);
  }

  function draw(force) {
    const i = target();
    if (i === current && !force) return;
    const img = nearestLoaded(i);
    if (!img) return;
    current = i;
    const cw = canvas.width, ch = canvas.height;
    // contain, but on narrow screens allow cropping the empty side margins of the 16:9 frame
    const s = Math.min(ch / img.naturalHeight, (cw / img.naturalWidth) * (cw < ch ? 1.5 : 1));
    const w = img.naturalWidth * s, h = img.naturalHeight * s;
    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
    const f = i + start;
    for (const c of captions) {
      c.classList.toggle('is-active', f >= +c.dataset.from && f <= +c.dataset.to);
    }
  }

  function onScroll() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => { pending = false; draw(false); });
  }

  // first frame now, then the rest in order (every 4th first so scrubbing is usable early)
  load(0).onload = () => resize();
  const order = [];
  for (let step of [4, 1]) for (let i = 0; i < count; i += step) if (!order.includes(i)) order.push(i);
  let k = 0;
  (function next() {
    for (let n = 0; n < 6 && k < order.length; n++) load(order[k++]);
    if (k < order.length) setTimeout(next, 30);
  })();

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', resize);
  resize();
  return () => {
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('resize', resize);
  };
}

window.mountAssembly = mountAssembly;
