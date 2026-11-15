/**
 * assets/genesis/ascii_orb.js
 * ===========================
 * Exact mathematical recreation of Thursday Agent's ASCII Orb.
 * Uses domain-warped fractal Brownian motion (fBm), 3D value noise,
 * and Thursday's authentic multi-tier glyph matrix (RAMP).
 */

(function (window) {
  'use strict';

  // 1. Exact Glyph Matrix from Thursday Agent (ascii.const.ts)
  const RAMP = [
    [" "],
    [" ", ".", "`"],
    [".", ",", "·", "'"],
    [":", ";", "-", "^"],
    ["=", "+", "~", '"'],
    ["*", "?", "◦", "j"],
    ["c", "v", "○", "7"],
    ["o", "x", "◇", "い"],
    ["s", "y", "t", "あ"],
    ["e", "a", "u", "な"],
    ["k", "w", "z", "や"],
    ["q", "h", "n", "米"],
  ];
  const LEVELS = RAMP.length;
  const ALPHA_TOP = 0.95;

  // 2. Deterministic Hash & 3D Value Noise (field.ts)
  function ihash(x, y, z) {
    let n = (x | 0) * 374761393 + (y | 0) * 668265263 + (z | 0) * 1274126177;
    n = Math.imul(n ^ (n >>> 13), 1274126177);
    return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function vnoise(x, y, z) {
    const xi = Math.floor(x);
    const yi = Math.floor(y);
    const zi = Math.floor(z);
    const xf = x - xi;
    const yf = y - yi;
    const zf = z - zi;
    const u = xf * xf * (3 - 2 * xf);
    const v = yf * yf * (3 - 2 * yf);
    const w = zf * zf * (3 - 2 * zf);
    const a = lerp(ihash(xi, yi, zi), ihash(xi + 1, yi, zi), u);
    const b = lerp(ihash(xi, yi + 1, zi), ihash(xi + 1, yi + 1, zi), u);
    const c = lerp(ihash(xi, yi, zi + 1), ihash(xi + 1, yi, zi + 1), u);
    const d = lerp(ihash(xi, yi + 1, zi + 1), ihash(xi + 1, yi + 1, zi + 1), u);
    return lerp(lerp(a, b, v), lerp(c, d, v), w);
  }

  function fbm(x, y, z, octaves = 3) {
    let sum = 0;
    let amp = 0.5;
    let norm = 0;
    for (let i = 0; i < octaves; i++) {
      sum += amp * vnoise(x, y, z);
      norm += amp;
      x *= 2.03;
      y *= 2.03;
      z *= 1.97;
      amp *= 0.5;
    }
    return sum / norm;
  }

  function warp(x, y, z, pull = 3.5) {
    const qx = fbm(x, y, z, 2);
    const qy = fbm(x + 5.2, y + 1.3, z + 2.8, 2);
    return fbm(x + pull * qx, y + pull * qy, z, 3);
  }

  // 3. AsciiOrb Engine Class
  class AsciiOrb {
    constructor(canvas, options = {}) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d', { alpha: true });
      this.size = options.size || 280;
      this.isDark = options.isDark !== undefined ? options.isDark : false;
      this.color = options.color || (this.isDark ? [240, 240, 245] : [15, 23, 42]);
      this.mode = options.mode || 'idle'; // idle | speaking | connecting | working
      this.isSpeaking = false;
      this.speechAmp = 0.0;
      this.lookAt = { x: 0, y: 0 };
      this.currentLook = { x: 0, y: 0 };
      this.running = false;
      this.rafId = null;

      // Glyphs metrics
      this.glyphPx = options.glyphPx || 12;
      this.density = options.density || 1.15;
      this.cellW = (this.glyphPx * 0.95) / this.density;
      this.cellH = (this.glyphPx * 1.25) / this.density;

      this.cells = [];
      this.startTime = performance.now();
      this.resize(this.size);
    }

    resize(newSize) {
      this.size = newSize || this.size;
      const dpr = Math.min(2.0, window.devicePixelRatio || 1);
      this.canvas.width = this.size * dpr;
      this.canvas.height = this.size * dpr;
      this.canvas.style.width = `${this.size}px`;
      this.canvas.style.height = `${this.size}px`;
      this.ctx.scale(dpr, dpr);

      // Rebuild cell coordinate matrix
      this.cells = [];
      const cols = Math.floor(this.size / this.cellW);
      const rows = Math.floor(this.size / this.cellH);
      const cx = this.size / 2;
      const cy = this.size / 2;
      const maxR = this.size * 0.46;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = c * this.cellW + this.cellW / 2;
          const y = r * this.cellH + this.cellH / 2;
          const dx = x - cx;
          const dy = y - cy;
          const dist = Math.hypot(dx, dy);
          if (dist <= maxR * 1.15) {
            this.cells.push({
              x,
              y,
              dx,
              dy,
              dist,
              angle: Math.atan2(dy, dx),
              seed: (r * 137 + c * 359) % 1000
            });
          }
        }
      }
    }

    setMode(mode) {
      this.mode = mode;
      if (mode === 'speaking') {
        this.isSpeaking = true;
      } else if (mode === 'idle') {
        this.isSpeaking = false;
        this.speechAmp = 0.0;
      }
    }

    setSpeaking(speaking, amp = 0.6) {
      this.isSpeaking = Boolean(speaking);
      this.speechAmp = speaking ? amp : 0.0;
    }

    setLookAt(x, y) {
      this.lookAt.x = Math.max(-1.0, Math.min(1.0, x));
      this.lookAt.y = Math.max(-1.0, Math.min(1.0, y));
    }

    setTheme(isDark) {
      this.isDark = isDark;
      this.color = isDark ? [240, 240, 245] : [20, 25, 35];
    }

    start() {
      if (this.running) return;
      this.running = true;
      this.startTime = performance.now();
      const tick = () => {
        if (!this.running) return;
        this.renderFrame();
        this.rafId = requestAnimationFrame(tick);
      };
      this.rafId = requestAnimationFrame(tick);
    }

    stop() {
      this.running = false;
      if (this.rafId) {
        cancelAnimationFrame(this.rafId);
        this.rafId = null;
      }
    }

    renderFrame() {
      const now = (performance.now() - this.startTime) / 1000;
      const ctx = this.ctx;
      let [rC, gC, bC] = this.color;

      // Organic speaking warmth tint towards Brahma sun amber (217, 119, 6)
      if (this.isSpeaking) {
        const blend = Math.min(1.0, 0.35 + this.speechAmp * 0.65);
        rC = Math.round(lerp(rC, 217, blend));
        gC = Math.round(lerp(gC, 119, blend));
        bC = Math.round(lerp(bC, 6, blend));
      }

      ctx.clearRect(0, 0, this.size, this.size);

      // Smooth look-at tracking
      this.currentLook.x += (this.lookAt.x - this.currentLook.x) * 0.1;
      this.currentLook.y += (this.lookAt.y - this.currentLook.y) * 0.1;

      // Base radius with organic breathing and speech swell
      const breath = Math.sin(now * 1.8) * 0.04;
      const speechSwell = this.isSpeaking ? (Math.sin(now * 14.0) * 0.08 + this.speechAmp * 0.12) : 0;
      const baseRadius = (this.size * 0.38) * (1.0 + breath + speechSwell);

      ctx.font = `700 ${this.glyphPx}px ui-monospace, SFMono-Regular, Menlo, monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      const cellCount = this.cells.length;
      for (let i = 0; i < cellCount; i++) {
        const cell = this.cells[i];

        // Domain-warped coordinates
        const lookShiftX = this.currentLook.x * 24.0;
        const lookShiftY = this.currentLook.y * 24.0;
        const ndx = (cell.dx - lookShiftX) / baseRadius;
        const ndy = (cell.dy - lookShiftY) / baseRadius;
        const distNorm = Math.hypot(ndx, ndy);

        if (distNorm > 1.35) continue;

        // Turbulence noise field
        const noiseVal = warp(
          ndx * 1.8 + now * 0.25,
          ndy * 1.8 - now * 0.2,
          now * 0.35,
          2.6
        );

        // Radial falloff + noise
        const coreFalloff = Math.max(0, 1.0 - distNorm);
        const intensity = (coreFalloff * 0.75 + noiseVal * 0.55);

        if (intensity <= 0.08) continue;

        // Level clamp into RAMP index
        const levelIdx = Math.max(0, Math.min(LEVELS - 1, Math.floor(intensity * (LEVELS - 1))));
        const glyphGroup = RAMP[levelIdx];
        const glyph = glyphGroup[(cell.seed + Math.floor(now * 4)) % glyphGroup.length];

        if (!glyph || glyph === ' ') continue;

        // Dynamic alpha
        const alpha = Math.min(ALPHA_TOP, (levelIdx / (LEVELS - 1)) * 0.95);
        ctx.fillStyle = `rgba(${rC}, ${gC}, ${bC}, ${alpha})`;
        ctx.fillText(glyph, cell.x, cell.y);
      }
    }
  }

  window.AsciiOrb = AsciiOrb;
})(window);
