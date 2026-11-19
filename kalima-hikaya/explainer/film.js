// كلمة وراها حكاية: an explainer for the table game. Pure function of time: window.seek(t) paints frame t.
// Scenes follow the narration (timing.js: Scribe word times of the ElevenLabs take); accents sit on the 96 bpm grid.
// Arabic is always drawn a whole word at a time (never per letter) so the letters stay joined.
import * as M from './lib/motion.js';
import { LINES, VO_OFFSET } from './timing.js';

const { W, H, FORMAT, E, prog, lerp, clamp, spring, SPRING, wobble, font, cover, rrect, mulberry32 } = M;

// Harmony colours (harmony-platform CLAUDE.md): green, forest, beige, paper. The five round colours appear only on
// the app's own word cards, as they do in the app.
const C = { felt: '#0C6C47', forest: '#1E3A2B', beige: '#F4ECDB', paper: '#F5EEDF', ink: '#1E3A2B', dim: 'rgba(245,238,223,0.72)' };
const SUIT = ['#2D4AA3', '#2A7A5C', '#A2650E', '#AD3E29', '#723788'];
const DISPLAY = 'Display', UI = 'UI';
const P = FORMAT.portrait;

// ---------------------------------------------------------------- narration timing (film seconds)
const T = (i) => LINES[i - 1].start + VO_OFFSET;
const TE = (i) => LINES[i - 1].end + VO_OFFSET;
const norm = (s) => s.replace(/[أإآ]/g, 'ا').replace(/ة/g, 'ه');
const WT = (i, w) => { const x = LINES[i - 1].words.find((z) => z[0].includes(norm(w))); return x ? x[1] + VO_OFFSET : T(i); };
const B = (t) => (t - 0.0015) / 0.625;          // seconds -> beats on the measured grid (96 bpm)
const sp = (t, t0, cfg = SPRING.bouncy) => (t <= t0 ? 0 : spring(t - t0, cfg));

// Real content from the app: round titles and the actual deal for table 7, round 1 (seats 1..8).
const ROUNDS = ['مهاراتنا بالشغل', 'كيف منفصل عن ضغط الشغل؟', 'شو مندوّر عليه بمكان الشغل؟', 'تحدّيات منواجهها بالشغل', 'العلاقات والتواصل بعالم الشغل'];
const DEAL7 = ['المرونة', 'المبادرة', 'التواصل', 'القيادة', 'العمل الجماعي', 'تحمّل المسؤولية', 'الإبداع', 'إدارة الوقت'];
const DECK = ['القيادة', 'العمل الجماعي', 'التواصل', 'الإبداع', 'حلّ المشاكل', 'إدارة الوقت', 'المرونة', 'اتخاذ القرارات', 'تحمّل المسؤولية', 'المبادرة'];

// Scene starts: a hair before each narration line.
const S = {
  hook: 0, deck: T(2) - 0.15, scan: T(3) - 0.15, name: T(4) - 0.15, manager: T(5) - 0.15, intro: T(6) - 0.15,
  rounds: T(7) - 0.15, shuffle: WT(7, 'اكبسوا') - 0.1, words: T(8) - 0.15, story: T(9) - 0.15, bridge: T(10) - 0.15,
  talk: T(11) - 0.15, give: T(12) - 0.15, mycard: T(13) - 0.15, end: T(14) - 0.15,
};

// Every accent, voiced by sfx.mjs: [beat, label, sfx, opts].
const HITS = [
  [B(0.02), 'card slams', 'thud', { pitch: 'D2' }],
  [B(WT(1, 'حكايه') - 0.05), 'bubble pops', 'pop', { pitch: 'A5' }],
  [B(S.deck), 'deck fans', 'whoosh', { len: 0.5 }],
  [B(S.scan + 0.05), 'table card lands', 'thud'],
  [B(WT(3, 'امسحوه') + 0.5), 'scan', 'blip', { pitch: 'E6' }],
  [B(S.name), 'phone', 'whoosh', { len: 0.4 }],
  [B(WT(4, 'رقم') - 0.1), 'number pops', 'pop', { pitch: 'D6' }],
  [B(S.manager), 'table', 'click'],
  [B(S.manager + 1.2), 'manager seat', 'bell', { pitch: 'A5' }],
  [B(S.rounds), 'rounds dealt', 'click'],
  [B(S.shuffle), 'phone', 'whoosh', { len: 0.4 }],
  [B(S.shuffle + 1.1), 'card flips', 'whoosh', { len: 0.3, from: 2400, to: 700 }],
  [B(S.shuffle + 1.4), 'word lands', 'pop', { pitch: 'G5' }],
  [B(S.words), 'words to seats', 'click'],
  [B(WT(9, 'صح') - 0.1), 'no right or wrong', 'tok', { pitch: 'D5' }],
  [B(S.bridge + 0.3), 'bridge drawn', 'riser', { len: 0.6 }],
  [B(S.talk), 'open talk', 'pop', { pitch: 'C6' }],
  [B(S.give + 0.4), 'give & get swap', 'whoosh', { len: 0.5 }],
  [B(S.mycard + 1.0), 'card scanned', 'blip', { pitch: 'E6' }],
  [B(WT(14, 'امسحوا')), 'end word 1', 'tok', { pitch: 'D5' }],
  [B(WT(14, 'احكوا')), 'end word 2', 'tok', { pitch: 'F5' }],
  [B(WT(14, 'واسمعوا')), 'end word 3', 'tok', { pitch: 'A5' }],
  [B(WT(14, 'وراها') - 0.1), 'wordmark', 'impact'],
  [B(WT(14, 'حكايه') + 0.6), 'logo', 'bell', { pitch: 'D6' }],
];

// ---------------------------------------------------------------- drawing helpers
let FELT = null;                                  // static felt texture, built once in init (seeded noise)
function feltBg(ctx, glow = 0) {
  ctx.drawImage(FELT, 0, 0);
  if (glow) { ctx.save(); ctx.globalAlpha = glow; ctx.fillStyle = C.paper; ctx.fillRect(0, 0, W, H); ctx.restore(); }
}
function setFont(ctx, size, weight, fam) { ctx.font = font(size, weight, fam); ctx.direction = 'rtl'; }
function arW(ctx, str, size, weight, fam) { ctx.save(); setFont(ctx, size, weight, fam); const w = ctx.measureText(str).width; ctx.restore(); return w; }
function ar(ctx, str, x, y, size, weight, fam, color, align = 'center') {
  ctx.save(); setFont(ctx, size, weight, fam); ctx.fillStyle = color; ctx.textAlign = align; ctx.fillText(str, x, y); ctx.restore();
}
function fitAr(ctx, str, weight, fam, maxW, max) { return Math.min(max, Math.floor(100 * maxW / arW(ctx, str, 100, weight, fam))); }
// One Arabic line whose words spring in one by one (each word drawn whole), laid out right to left about cx.
function arWords(ctx, t, words, cx, y, size, weight, fam, color, times, { rise = 0.5, cfg = SPRING.bouncy } = {}) {
  const ws = words.map((w) => arW(ctx, w, size, weight, fam)), gap = size * 0.28;
  const total = ws.reduce((a, b) => a + b, 0) + gap * (words.length - 1);
  let x = cx + total / 2;
  words.forEach((w, i) => {
    const wx = x - ws[i] / 2; x -= ws[i] + gap;
    const k = sp(t, times[i], cfg); if (k <= 0) return;
    ctx.save(); ctx.translate(wx, y + (1 - k) * size * rise); ctx.scale(lerp(0.6, 1, Math.min(k, 1.2)), lerp(0.6, 1, Math.min(k, 1.2)));
    ctx.globalAlpha *= clamp(k * 2); ar(ctx, w, 0, 0, size, weight, fam, color); ctx.restore();
  });
}
function shadowOn(ctx, blur = 34, dy = 16, a = 0.35) { ctx.shadowColor = `rgba(8,24,16,${a})`; ctx.shadowBlur = blur; ctx.shadowOffsetY = dy; }
// A word card like the app's: rounded, suit colour or paper, word in Lalezar.
function card(ctx, cx, cy, w, h, { color = C.paper, rot = 0, s = 1, sx = 1, word = '', wordColor = '#fff', size = 0, tag = '', shadow = true } = {}) {
  if (s <= 0.001) return;
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(s * sx, s);
  if (shadow) shadowOn(ctx);
  rrect(ctx, -w / 2, -h / 2, w, h, Math.min(w, h) * 0.09); ctx.fillStyle = color; ctx.fill();
  ctx.shadowColor = 'transparent';
  if (word && Math.abs(sx) > 0.05) {
    const fs = size || fitAr(ctx, word, 400, DISPLAY, w * 0.8, h * 0.34);
    ar(ctx, word, 0, fs * 0.36, fs, 400, DISPLAY, wordColor);
  }
  if (tag) ar(ctx, tag, 0, h / 2 - h * 0.09, h * 0.075, 600, UI, wordColor === '#fff' ? 'rgba(255,255,255,0.8)' : C.forest);
  ctx.restore();
}
// The app's speech bubble (its logo shape) with text inside.
function bubble(ctx, cx, cy, w, h, s, text, { size = 0, color = C.paper, ink = C.forest, tail = 1 } = {}) {
  if (s <= 0.001) return;
  ctx.save(); ctx.translate(cx, cy); ctx.scale(s, s); shadowOn(ctx, 26, 10, 0.3);
  const r = h * 0.28, x = -w / 2, y = -h / 2;
  ctx.beginPath(); ctx.roundRect(x, y, w, h, r);
  const tx = tail * w * 0.22;
  ctx.moveTo(tx - h * 0.18, h / 2 - 1); ctx.lineTo(tx + h * 0.06 * tail, h / 2 + h * 0.36); ctx.lineTo(tx + h * 0.16, h / 2 - 1);
  ctx.fillStyle = color; ctx.fill(); ctx.shadowColor = 'transparent';
  if (text) { const fs = size || fitAr(ctx, text, 400, DISPLAY, w * 0.82, h * 0.52); ar(ctx, text, 0, fs * 0.36, fs, 400, DISPLAY, ink); }
  ctx.restore();
}
// A phone holding a real screenshot.
function phone(ctx, img, cx, cy, h, { rot = 0, s = 1, fy = 0, zoom = 1 } = {}) {
  if (s <= 0.001 || !img) return;
  const w = h * 0.4705;
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(s, s);
  shadowOn(ctx, 60, 26, 0.45); rrect(ctx, -w / 2, -h / 2, w, h, w * 0.14); ctx.fillStyle = '#14161E'; ctx.fill(); ctx.shadowColor = 'transparent';
  const b = w * 0.035; cover(ctx, img, -w / 2 + b, -h / 2 + b, w - 2 * b, h - 2 * b, { fy, zoom, radius: w * 0.11 });
  rrect(ctx, -w * 0.13, -h / 2 + b + h * 0.008, w * 0.26, h * 0.022, h * 0.011); ctx.fillStyle = '#14161E'; ctx.fill();
  ctx.restore();
}
// Top-down round table with 8 numbered seats, seat 1 at the top, clockwise.
const seatPos = (i, cx, cy, R) => { const a = -Math.PI / 2 + (i * Math.PI * 2) / 8; return [cx + Math.cos(a) * R, cy + Math.sin(a) * R]; };
function table(ctx, t, cx, cy, R, { appear = 0, lit = () => 0, label = () => '', mgr = 0, ring = null } = {}) {
  const k = sp(t, appear, SPRING.gentle);
  ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ctx.translate(-cx, -cy);
  shadowOn(ctx, 50, 20, 0.4);
  ctx.beginPath(); ctx.arc(cx, cy, R * 0.72, 0, Math.PI * 2); ctx.fillStyle = C.forest; ctx.fill(); ctx.shadowColor = 'transparent';
  ctx.lineWidth = R * 0.03; ctx.strokeStyle = 'rgba(245,238,223,0.25)'; ctx.stroke();
  if (ring) {   // a timer ring round the table: ring = [progress 0..1, label]
    ctx.lineWidth = R * 0.05; ctx.strokeStyle = 'rgba(245,238,223,0.18)'; ctx.beginPath(); ctx.arc(cx, cy, R * 0.6, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = C.paper; ctx.lineCap = 'round'; ctx.beginPath(); ctx.arc(cx, cy, R * 0.6, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * ring[0]); ctx.stroke();
    ctx.save(); ctx.direction = 'ltr'; ctx.font = font(R * 0.26, 600, UI); ctx.fillStyle = C.paper; ctx.textAlign = 'center'; ctx.fillText(ring[1], cx, cy + R * 0.09); ctx.restore();
    if (ring[2]) ar(ctx, ring[2], cx, cy + R * 0.3, R * 0.1, 500, UI, C.dim);
  }
  for (let i = 0; i < 8; i++) {
    const [x, y] = seatPos(i, cx, cy, R), si = sp(t, appear + 0.1 + i * 0.07, SPRING.bouncy), r = R * 0.15;
    if (si <= 0) continue;
    const l = clamp(lit(i + 1));
    ctx.save(); ctx.translate(x, y); ctx.scale(si * (1 + 0.12 * l), si * (1 + 0.12 * l));
    shadowOn(ctx, 18, 8, 0.3); ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fillStyle = i + 1 === 1 && mgr ? '#F6A424' : M.mix(C.paper, '#FFFFFF', l); ctx.fill(); ctx.shadowColor = 'transparent';
    if (l > 0) { ctx.lineWidth = r * 0.18; ctx.strokeStyle = M.mix(C.forest, '#F6A424', l); ctx.globalAlpha = l; ctx.stroke(); ctx.globalAlpha = 1; }
    ctx.direction = 'ltr'; ctx.font = font(r * 1.05, 700, UI); ctx.fillStyle = C.forest; ctx.textAlign = 'center'; ctx.fillText(String(i + 1), 0, r * 0.38);
    ctx.restore();
    const lab = label(i + 1);
    if (lab) {
      const [lx0, ly] = seatPos(i, cx, cy, R * 1.36), ls = typeof lab === 'object' ? lab : { text: lab, s: 1 };
      const lx = inX(lx0, arW(ctx, ls.text, ls.size || R * 0.13, 400, DISPLAY) / 2);
      if (ls.s > 0) { ctx.save(); ctx.translate(lx, ly); ctx.scale(ls.s, ls.s); ar(ctx, ls.text, 0, R * 0.05, ls.size || R * 0.13, 400, DISPLAY, ls.color || C.paper); ctx.restore(); }
    }
  }
  ctx.restore();
}
// Burned-in subtitles of the narration line being spoken.
function subtitles(ctx, t) {
  const i = LINES.findIndex((l) => t >= l.start + VO_OFFSET - 0.05 && t <= l.end + VO_OFFSET + 0.35);
  if (i < 0) return;
  const txt = LINES[i].text.replace(/\s+/g, ' ').trim();
  const size = P ? 50 : 46, maxW = P ? W - 200 : W * 0.78, words = txt.split(' '), rows = [''];
  for (const w of words) { const tryRow = rows[rows.length - 1] ? rows[rows.length - 1] + ' ' + w : w; if (arW(ctx, tryRow, size, 600, UI) > maxW && rows[rows.length - 1]) rows.push(w); else rows[rows.length - 1] = tryRow; }
  const lh = size * 1.42, h = rows.length * lh + size * 0.6, y0 = P ? H - 470 - h : H - 52 - h;
  const bw = Math.max(...rows.map((r) => arW(ctx, r, size, 600, UI))) + size * 1.2;
  const a = clamp((t - (LINES[i].start + VO_OFFSET - 0.05)) / 0.12) * clamp((LINES[i].end + VO_OFFSET + 0.35 - t) / 0.12);
  ctx.save(); ctx.globalAlpha = a;
  rrect(ctx, W / 2 - bw / 2, y0, bw, h, 22); ctx.fillStyle = 'rgba(20,40,30,0.82)'; ctx.fill();
  rows.forEach((r, k) => ar(ctx, r, W / 2, y0 + size * 0.3 + (k + 0.82) * lh - size * 0.18, size, 600, UI, C.paper));
  ctx.restore();
}
// Content box for each format (portrait keeps clear of the subtitle band).
const BOX = P ? { x: 72, y: 250, w: W - 144, h: H - 250 - 640 } : { x: 96, y: 60, w: W - 192, h: H - 60 - 200 };
const CX = BOX.x + BOX.w / 2, CY = BOX.y + BOX.h / 2;
const inX = (x, half, m = 28) => clamp(x, half + m, W - half - m);
// Portrait: one headline band at the top, the table and phones below it, clear of the subtitles.
const HEAD_Y = BOX.y + 110;
const TAB = P ? { R: 270, cx: CX, cy: CY + 120 } : { R: 300, cx: CX + 300, cy: CY + 20 };
const PHONE_H = P ? 860 : 840, PHONE_Y = P ? 860 : CY + 20;

// ---------------------------------------------------------------- scenes (t in seconds)
function sHook(ctx, t, IMG) {
  feltBg(ctx);
  const k = sp(t, -0.14, SPRING.bouncy), q = 0.08 * wobble(t - 0.05, 2.6, 6);
  const cw = P ? 640 : 560, ch = cw * 0.66, cy = CY - (P ? 120 : 60);
  ctx.save(); ctx.translate(CX, cy); ctx.scale(1 + q, 1 - q); ctx.translate(-CX, -cy);
  card(ctx, CX, lerp(cy - H * 0.32, cy, Math.min(k, 1.05)), cw, ch, { color: C.paper, word: 'كلمة', wordColor: C.forest, rot: lerp(-0.25, -0.04, Math.min(k, 1)), s: lerp(1.5, 1, Math.min(k, 1)) });
  ctx.restore();
  const tb = WT(1, 'حكايه') - 0.12, kb = sp(t, tb, SPRING.bouncy);
  bubble(ctx, CX + cw * 0.33, cy - ch * 0.62 - (1 - Math.min(kb, 1)) * 40, cw * 0.62, ch * 0.42, kb, 'حكاية', { color: SUIT[0], ink: '#fff' });
  const kw = sp(t, tb + 0.25, SPRING.gentle);
  if (kw > 0 && IMG.wordmark) { const ww = P ? W * 0.78 : W * 0.42, wh = ww * IMG.wordmark.height / IMG.wordmark.width;
    ctx.save(); ctx.globalAlpha = clamp(kw); ctx.drawImage(IMG.wordmark, CX - ww / 2, cy + ch * 0.62 + (1 - kw) * 60, ww, wh); ctx.restore(); }
}
function sDeck(ctx, t) {
  feltBg(ctx);
  const t0 = S.deck, n = P ? 6 : 8, cols = P ? 2 : 4, cw = P ? 400 : 330, ch = cw * 0.62;
  const gx = P ? 450 : 400, gy = P ? 262 : 250, rows = Math.ceil(n / cols);
  const ox = CX - ((cols - 1) * gx) / 2, oy = (P ? CY + 115 : CY + 70) - ((rows - 1) * gy) / 2;
  for (let i = 0; i < n; i++) {
    const ti = t0 + 0.05 + i * 0.12, f = E.outCubic(prog(t, ti, ti + 0.4)), k = sp(t, ti + 0.3, SPRING.bouncy);
    if (f <= 0) continue;
    const c = i % cols, r = Math.floor(i / cols), jx = (M.hash01(i, 3) - 0.5) * 40, jy = (M.hash01(i, 7) - 0.5) * 30;
    const x = ox + (cols - 1 - c) * gx + jx, y = oy + r * gy + jy, rot = (M.hash01(i, 9) - 0.5) * 0.22;
    card(ctx, lerp(CX, x, f), lerp(H + ch, y, f), cw, ch, { color: SUIT[0], word: DECK[i], rot: lerp(0.8, rot, f), s: 1 + 0.06 * (1 - Math.min(k, 1)) });
  }
  const tw = WT(2, 'بطريقه');
  arWords(ctx, t, ['بطريقة', 'غير'], CX, HEAD_Y, P ? 120 : 110, 400, DISPLAY, C.paper, [tw, tw + 0.25]);
}
function sScan(ctx, t, IMG) {
  feltBg(ctx);
  const t0 = S.scan, kc = sp(t, t0, SPRING.bouncy), q = 0.06 * wobble(t - t0 - 0.15, 2.4, 6);
  const qrW = P ? 560 : 430, qrH = qrW * 1.25, qx = P ? CX : CX + 300, qy = P ? CY - 150 : CY;
  if (IMG.qr) { ctx.save(); ctx.translate(qx, qy); ctx.rotate(0.05); ctx.scale(lerp(1.4, 1, Math.min(kc, 1)) * (1 + q), lerp(1.4, 1, Math.min(kc, 1)) * (1 - q)); ctx.globalAlpha = clamp(kc * 2);
    shadowOn(ctx); rrect(ctx, -qrW / 2, -qrH / 2, qrW, qrH, 24); ctx.fillStyle = '#fff'; ctx.fill(); ctx.shadowColor = 'transparent';
    ctx.drawImage(IMG.qr, -qrW / 2, -qrH / 2, qrW, qrH); ctx.restore(); }
  const tp = WT(3, 'امسحوه') - 0.3, kp = sp(t, tp, SPRING.gentle);
  const ph = P ? 760 : 620, px = P ? CX + 40 : CX - 360, py = lerp(H + ph, P ? CY + 330 : CY + 40, kp);
  phone(ctx, IMG.scanPhone, px, py, ph, { rot: lerp(0.3, P ? -0.12 : -0.08, kp) });
  // the scan line sweeps the code once the phone is over it
  const sw = prog(t, tp + 0.55, tp + 1.35);
  if (sw > 0 && sw < 1) { const y = qy - qrH * 0.4 + qrH * 0.62 * sw; ctx.save(); ctx.globalAlpha = Math.sin(sw * Math.PI);
    ctx.fillStyle = '#4ADE80'; ctx.shadowColor = '#4ADE80'; ctx.shadowBlur = 24; ctx.fillRect(qx - qrW * 0.42, y, qrW * 0.84, 6); ctx.restore(); }
}
function sName(ctx, t, IMG) {
  feltBg(ctx);
  const t0 = S.name, tn = WT(4, 'رقم') - 0.25, k = sp(t, t0, SPRING.gentle);
  const ph = PHONE_H, px = P ? CX - 110 : CX - 330, py = lerp(H + ph / 2, PHONE_Y, k);
  const swap = prog(t, tn - 0.3, tn);                       // push from the name step to the number
  phone(ctx, IMG.nameTyped, px - swap * 80, py, ph, { s: 1 - swap * 0.06, rot: -0.02 });
  if (swap > 0) { ctx.save(); ctx.globalAlpha = swap; phone(ctx, IMG.welcome, px, py, ph, { rot: -0.02 }); ctx.restore(); }
  // the number jumps out of the screen
  const kn = sp(t, tn + 0.15, SPRING.bouncy);
  if (kn > 0) { const nx = P ? W - 200 : CX + 330, ny = P ? BOX.y + 300 : CY - 60, ns = P ? 270 : 360;
    ctx.save(); ctx.translate(lerp(px + 80, nx, Math.min(kn, 1)), lerp(py - ph * 0.3, ny, Math.min(kn, 1))); ctx.scale(kn, kn);
    shadowOn(ctx, 40, 16, 0.4); ctx.beginPath(); ctx.arc(0, 0, ns * 0.5, 0, Math.PI * 2); ctx.fillStyle = C.paper; ctx.fill(); ctx.shadowColor = 'transparent';
    ctx.direction = 'ltr'; ctx.font = font(ns * 0.62, 400, DISPLAY); ctx.fillStyle = SUIT[0]; ctx.textAlign = 'center'; ctx.fillText('7', 0, ns * 0.2); ctx.restore();
    const kt = sp(t, WT(4, 'دوره') - 0.1, SPRING.bouncy);
    if (kt > 0) { ctx.save(); ctx.translate(nx, ny + ns * 0.62); ctx.scale(kt, kt); ar(ctx, 'دورك بالحكي', 0, 10, P ? 52 : 62, 400, DISPLAY, C.paper); ctx.restore(); }
  }
}
function sManager(ctx, t, IMG) {
  feltBg(ctx);
  const t0 = S.manager, { R, cx, cy } = TAB;
  const km = sp(t, t0 + 1.0, SPRING.bouncy);
  table(ctx, t, cx, cy, R, { appear: t0, mgr: km > 0.5 ? 1 : 0, lit: (i) => (i === 1 ? km : 0), label: (i) => (i === 1 ? { text: 'المدير', s: km, color: '#F6A424', size: R * 0.17 } : '') });
  const kp = sp(t, t0 + 1.5, SPRING.gentle), ph = P ? 640 : 760;
  if (kp > 0 && !P) phone(ctx, IMG.mgrReady, P ? CX - 250 : CX - 600, P ? CY + 470 - (1 - kp) * 300 : CY + (1 - kp) * H, ph, { rot: P ? -0.1 : -0.04, s: Math.min(kp, 1) });
  const tw = WT(5, 'بيدير');
  arWords(ctx, t, ['الأدوار', 'والوقت'], P ? CX : CX - 190, P ? HEAD_Y : CY - 250, P ? 92 : 76, 400, DISPLAY, C.paper, [tw + 0.25, tw + 0.6]);
}
function sIntro(ctx, t) {
  feltBg(ctx);
  const t0 = S.intro, { R, cx, cy } = TAB, per = 0.62;
  const cur = Math.floor((t - t0 - 0.6) / per);             // seats light one by one
  const p30 = prog(t, t0 + 0.6, TE(6) + 0.4);
  table(ctx, t, cx, cy, R, { appear: t0 - 2, mgr: 1, lit: (i) => (i - 1 === ((cur % 8) + 8) % 8 && cur >= 0 ? 1 : 0), ring: [1 - (p30 * 8) % 1, '0:30', 'لكل واحد'] });
  const tags = [['اسمه', WT(6, 'اسمه')], ['شو بيشتغل', WT(6, 'بيشتغل') - 0.2], ['شو بيدوّر عليه', WT(6, 'بيدور') - 0.2]];
  tags.forEach(([w, tw], j) => {
    const k = sp(t, tw, SPRING.bouncy); if (k <= 0) return;
    const x = P ? CX + (j - 1) * -310 : CX - 420, y = P ? HEAD_Y + 150 : BOX.y + 250 + j * 190;
    ctx.save(); ctx.translate(x, y); ctx.scale(k, k); const w2 = arW(ctx, w, P ? 58 : 64, 400, DISPLAY) + 70;
    shadowOn(ctx, 20, 8, 0.3); rrect(ctx, -w2 / 2, -58, w2, 98, 49); ctx.fillStyle = SUIT[j + 1]; ctx.fill(); ctx.shadowColor = 'transparent';
    ar(ctx, w, 0, 12, P ? 58 : 64, 400, DISPLAY, '#fff'); ctx.restore();
  });
  arWords(ctx, t, ['تعارف', 'سريع'], P ? CX : CX - 420, P ? HEAD_Y : BOX.y + 110, P ? 100 : 90, 400, DISPLAY, C.paper, [t0 + 0.05, t0 + 0.3]);
}
function sRounds(ctx, t) {
  feltBg(ctx);
  const t0 = S.rounds;
  arWords(ctx, t, ['خمس', 'جولات'], CX, HEAD_Y, P ? 130 : 120, 400, DISPLAY, C.paper, [t0 + 0.05, t0 + 0.3]);
  for (let i = 0; i < 5; i++) {
    const k = sp(t, t0 + 0.35 + i * 0.22, SPRING.bouncy);
    const x = CX, y = HEAD_Y + (P ? 170 : 130) + i * (P ? 168 : 128);
    const w = P ? 820 : 900, h = P ? 140 : 108;
    card(ctx, lerp(-W, x, Math.min(k, 1)), y, w, h, { color: SUIT[i], word: ROUNDS[i], rot: (i - 2) * 0.012, s: clamp(k * 2) ? 1 : 0, size: P ? 62 : 56 });
  }
}
function sShuffle(ctx, t, IMG) {
  feltBg(ctx);
  const t0 = S.shuffle, k = sp(t, t0, SPRING.gentle), ph = PHONE_H, px = P ? CX : CX - 300, py = lerp(H + ph, PHONE_Y, k);
  const tf = t0 + 0.9, f = prog(t, tf, tf + 0.5), tq = WT(7, 'وتحتها') - 0.2;
  const sx = Math.cos(f * Math.PI);                           // flip the phone round from the face-down card to the word
  const img = f < 0.5 ? IMG.cardBack : (t < tq ? IMG.cardWord : IMG.cardQuestion);
  const fy = t < tq ? 0 : lerp(0, 1, E.inOutCubic(prog(t, tq, tq + 0.6)));
  ctx.save(); ctx.translate(px, py); ctx.scale(Math.abs(sx) < 0.02 ? 0.02 : Math.abs(sx), 1); ctx.translate(-px, -py);
  phone(ctx, img, px, py, ph, { rot: 0.02, fy: img === IMG.cardQuestion ? 1 : 0 });
  ctx.restore();
  // «اخلط» as a big word, said aloud
  const tw = WT(7, 'اخلط');
  if (!P) arWords(ctx, t, ['اكبسوا', '«اخلط»'], CX + 400, CY - 120, 110, 400, DISPLAY, C.paper, [tw - 0.45, tw]);
  else arWords(ctx, t, ['اكبسوا', '«اخلط»'], CX, HEAD_Y, 96, 400, DISPLAY, C.paper, [tw - 0.45, tw]);
  const tk = WT(7, 'كلمه') - 0.1;
  if (!P) { arWords(ctx, t, ['كلمة'], CX + 400, CY + 60, 96, 400, DISPLAY, C.paper, [tk]); arWords(ctx, t, ['وسؤال'], CX + 400, CY + 200, 96, 400, DISPLAY, C.paper, [tq + 0.2]); }
  void fy;
}
function sWords(ctx, t) {
  feltBg(ctx);
  const t0 = S.words, { R, cx, cy } = TAB;
  table(ctx, t, cx, cy, R, { appear: t0 - 2, mgr: 1, label: (i) => { const k = sp(t, t0 + 0.2 + (i - 1) * 0.16, SPRING.bouncy); return { text: DEAL7[i - 1], s: k, color: '#fff', size: R * (P ? 0.13 : 0.12) }; } });
  // each word flies from the deck in the middle to its seat, on a suit-1 card
  for (let i = 0; i < 8; i++) {
    const ti = t0 + 0.05 + i * 0.16, f = E.outCubic(prog(t, ti, ti + 0.35)); if (f <= 0 || f >= 1) continue;
    const [x, y] = seatPos(i, cx, cy, R * 1.36);
    card(ctx, lerp(cx, x, f), lerp(cy, y, f), 150, 100, { color: SUIT[0], s: 0.9, rot: (1 - f) * 0.6 });
  }
  arWords(ctx, t, ['كلمة', 'غير', 'لكل', 'واحد'], P ? CX : CX - 470, P ? HEAD_Y : CY - 20, P ? 100 : 92, 400, DISPLAY, C.paper, [t0 + 0.1, t0 + 0.3, t0 + 0.5, t0 + 0.7]);
}
function sStory(ctx, t) {
  feltBg(ctx);
  const t0 = S.story, { R, cx, cy } = TAB;
  const prep = prog(t, t0 + 0.1, WT(9, 'وبعدين'));
  const talking = t > WT(9, 'وبعدين');
  table(ctx, t, cx, cy, R, { appear: t0 - 2, mgr: 1, lit: (i) => (talking && i === 2 ? 1 : 0), ring: talking ? null : [1 - prep, '1:00', 'دقيقة تحضير'] });
  const kb = sp(t, WT(9, 'بيحكي') - 0.2, SPRING.bouncy), [bx, by] = seatPos(1, cx, cy, R);
  const tOut = WT(9, 'صح') - 0.75, kbo = 1 - E.inBack(prog(t, tOut, tOut + 0.3), 1.2);
  bubble(ctx, inX(bx + (P ? 40 : 160), (P ? 420 : 400) / 2), by - R * 0.55, P ? 420 : 400, P ? 160 : 150, kb * kbo, 'من تجربتي…');
  // «ما في جواب صح أو غلط»: a tick and a cross, both struck through
  const tn = WT(9, 'صح') - 0.6, kn = sp(t, tn, SPRING.bouncy);
  if (kn > 0) {
    const x = P ? CX : CX - 470, y = P ? HEAD_Y - 20 : CY - 60, s = P ? 0.92 : 0.95;
    ctx.save(); ctx.translate(x, y); ctx.scale(kn * s, kn * s);
    ar(ctx, 'ما في جواب', 0, 0, 96, 400, DISPLAY, C.paper);
    ar(ctx, 'صح أو غلط', 0, 130, 96, 400, DISPLAY, C.paper);
    const st = E.outCubic(prog(t, tn + 0.55, tn + 0.85));    // strike-through line across «صح أو غلط»
    if (st > 0) { const ww = arW(ctx, 'صح أو غلط', 96, 400, DISPLAY) + 30; ctx.strokeStyle = '#F6A424'; ctx.lineWidth = 12; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(ww / 2, 96); ctx.lineTo(ww / 2 - ww * st, 96); ctx.stroke(); }
    ctx.restore();
  }
}
function sBridge(ctx, t) {
  feltBg(ctx);
  const t0 = S.bridge, { R, cx, cy } = TAB;
  table(ctx, t, cx, cy, R, { appear: t0 - 2, mgr: 1, lit: (i) => (i === 3 ? 1 : i === 2 ? 0.4 : 0) });
  const [ax, ay] = seatPos(1, cx, cy, R * 1.25), [bx, by] = seatPos(2, cx, cy, R * 1.25);
  const kb1 = sp(t, t0, SPRING.bouncy), kb2 = sp(t, t0 + 1.2, SPRING.bouncy);
  const b1x = inX(ax + 40, 165), b2x = inX(bx + 80, 180);
  bubble(ctx, b1x, ay - 120, 330, 130, kb1, 'حكايتي…', { size: 62 });
  bubble(ctx, b2x, by + 40, 360, 130, kb2, 'إشي لفتني…', { size: 58, color: '#F6A424', ink: C.forest, tail: -1 });
  // the bridge: an arc drawn from one story to the next
  const d = E.inOutCubic(prog(t, t0 + 0.35, t0 + 1.3));
  if (d > 0) { ctx.save(); ctx.strokeStyle = C.paper; ctx.lineWidth = 10; ctx.lineCap = 'round'; ctx.setLineDash([2, 22]);
    ctx.beginPath(); const mx = Math.min((ax + bx) / 2 + 240, W - 60), my = (ay + by) / 2 - 260, N = 40;
    for (let s = 0; s <= N * d; s++) { const u = s / N; const x = (1 - u) ** 2 * b1x + 2 * (1 - u) * u * mx + u * u * b2x; const y = (1 - u) ** 2 * (ay - 120) + 2 * (1 - u) * u * my + u * u * (by + 40); if (s === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }
    ctx.stroke(); ctx.restore(); }
  arWords(ctx, t, ['الجسر'], P ? CX : CX - 470, P ? HEAD_Y : CY - 60, P ? 140 : 130, 400, DISPLAY, '#F6A424', [t0 + 0.6]);
  const ts2 = t0 + 1.0;
  if (!P) arWords(ctx, t, ['جملة', 'عن', 'اللي', 'قبلك'], CX - 470, CY + 90, 74, 400, DISPLAY, C.paper, [ts2, ts2 + 0.15, ts2 + 0.3, ts2 + 0.45]);
}
function sTalk(ctx, t) {
  feltBg(ctx);
  const t0 = S.talk, { R, cx, cy } = TAB;
  const p = prog(t, t0, S.give);
  table(ctx, t, cx, cy, R, { appear: t0 - 2, mgr: 1, lit: () => 0.5 + 0.5 * Math.sin(t * 6), ring: [1 - p * 0.3, '3:00', 'نقاش مفتوح'] });
  const rnd = mulberry32(11);
  for (let i = 0; i < 14; i++) {
    const seat = Math.floor(rnd() * 8), ti = t0 + 0.2 + i * 0.32 + rnd() * 0.1, k = sp(t, ti, SPRING.bouncy), life = 1 - prog(t, ti + 1.6, ti + 1.9);
    if (k <= 0 || life <= 0) continue;
    const [x, y] = seatPos(seat, cx, cy, R * (1.45 + rnd() * 0.25));
    bubble(ctx, x, y - 50, 150, 90, k * life, '…', { size: 70, tail: rnd() > 0.5 ? 1 : -1 });
  }
  arWords(ctx, t, ['مين', 'مرّ', 'بتجربة', 'مشابهة؟'], P ? CX : CX - 470, P ? HEAD_Y : CY - 20, P ? 92 : 84, 400, DISPLAY, C.paper,
    [WT(11, 'مين'), WT(11, 'مر'), WT(11, 'بتجربه'), WT(11, 'مشابهه')]);
}
function sGive(ctx, t) {
  feltBg(ctx);
  const t0 = S.give, { R, cx, cy } = TAB;
  table(ctx, t, cx, cy, R, { appear: t0 - 2, mgr: 1, lit: (i) => (i === 3 || i === 7 ? 1 : 0) });
  const [ax0, ay] = seatPos(2, cx, cy, R * 1.5), [bx0, by] = seatPos(6, cx, cy, R * 1.5), ax = inX(ax0, 130), bx = inX(bx0, 130);
  const sw = E.inOutCubic(prog(t, t0 + 0.4, t0 + 1.4)), lift = Math.sin(sw * Math.PI) * 220;
  card(ctx, lerp(ax, bx, sw), lerp(ay, by, sw) - lift, 260, 140, { color: SUIT[3], word: 'بقدّم', size: 70, rot: lerp(0.1, -0.1, sw) });
  card(ctx, lerp(bx, ax, sw), lerp(by, ay, sw) + lift, 260, 140, { color: SUIT[4], word: 'بدوّر على', size: 58, rot: lerp(-0.1, 0.1, sw) });
  arWords(ctx, t, ['طلب', 'وعرض'], P ? CX : CX - 470, P ? HEAD_Y : CY - 230, P ? 130 : 120, 400, DISPLAY, '#F6A424', [WT(12, 'طلب'), WT(12, 'وعرض')]);
}
function sMyCard(ctx, t, IMG) {
  feltBg(ctx);
  const t0 = S.mycard, k = sp(t, t0, SPRING.gentle), ph = PHONE_H, px = P ? CX - 90 : CX - 260, py = lerp(H + ph, PHONE_Y, k);
  phone(ctx, IMG.myCard, px, py, ph, { rot: -0.03 });
  const k2 = sp(t, t0 + 0.6, SPRING.gentle), qx = px + ph * 0.02, qy = py - ph * 0.08;
  phone(ctx, IMG.scanPhone, P ? CX + 300 : CX + 260, lerp(H + 600, P ? PHONE_Y + 170 : CY + 120, k2), P ? 500 : 640, { rot: 0.18 });
  const sw = prog(t, t0 + 1.0, t0 + 1.8);
  if (sw > 0 && sw < 1) { const y = qy - ph * 0.12 + ph * 0.22 * sw; ctx.save(); ctx.globalAlpha = Math.sin(sw * Math.PI); ctx.fillStyle = '#4ADE80'; ctx.shadowColor = '#4ADE80'; ctx.shadowBlur = 24; ctx.fillRect(qx - ph * 0.17, y, ph * 0.34, 6); ctx.restore(); }
  arWords(ctx, t, ['«بطاقتي»'], P ? CX : CX + 610, P ? HEAD_Y : CY - 200, P ? 110 : 120, 400, DISPLAY, C.paper, [WT(13, 'بطاقتي') - 0.1]);
}
function sEnd(ctx, t, IMG) {
  feltBg(ctx);
  const words = ['امسحوا', 'احكوا', 'واسمعوا'], times = [WT(14, 'امسحوا'), WT(14, 'احكوا'), WT(14, 'واسمعوا')];
  const out = E.inBack(prog(t, WT(14, 'لانه'), WT(14, 'لانه') + 0.35), 1.3);
  ctx.save(); ctx.globalAlpha = 1 - out;
  const es = Math.min(P ? 140 : 150, fitAr(ctx, words.join(' '), 400, DISPLAY, W - 160, 150));
  arWords(ctx, t, words, CX, P ? CY - 40 : CY - 20, es, 400, DISPLAY, C.paper, times);
  ctx.restore();
  const tw = WT(14, 'لانه') + 0.2, kw = sp(t, tw, SPRING.gentle);
  if (kw > 0 && IMG.wordmark) { const ww = P ? W * 0.84 : W * 0.5, wh = ww * IMG.wordmark.height / IMG.wordmark.width;
    ctx.save(); ctx.globalAlpha = clamp(kw); const y = (P ? CY - 160 : CY - 150) + (1 - kw) * 80; ctx.drawImage(IMG.wordmark, CX - ww / 2, y, ww, wh); ctx.restore(); }
  const kb = sp(t, WT(14, 'حكايه') + 0.55, SPRING.bouncy);
  if (kb > 0 && IMG.badge) { const bs = P ? 210 : 180, y = P ? CY + 200 : CY + 140;
    ctx.save(); ctx.translate(CX, y); ctx.scale(kb, kb); ctx.drawImage(IMG.badge, -bs / 2, -bs / 2, bs, bs); ctx.restore();
    ctx.save(); ctx.globalAlpha = clamp(kb); ar(ctx, 'مجتمع هارموني', CX, y + bs / 2 + 70, P ? 54 : 48, 600, UI, C.paper); ctx.restore(); }
}

// ---------------------------------------------------------------- film
M.film({
  fonts: [font(100, 400, DISPLAY), font(40, 600, UI)],
  samples: 6,
  images: {
    wordmark: 'assets/wordmark_cream.png', badge: 'assets/harmony-badge.png', qr: 'assets/qr-table-07.png',
    scanPhone: 'assets/shots/01_scan_landing.png', nameTyped: 'assets/shots/02_name_typed.png', welcome: 'assets/shots/03_welcome_number.png',
    cardBack: 'assets/shots/04_card_back.png', cardWord: 'assets/shots/05b_card_word_top.png', cardQuestion: 'assets/shots/05_card_word_question.png',
    mgrReady: 'assets/shots/07_manager_intro_turn.png', myCard: 'assets/shots/10_my_card.png',
  },
  hits: HITS,
  init() {
    // felt: Harmony green with a soft vignette to forest and fine seeded fibre noise, painted once
    FELT = document.createElement('canvas'); FELT.width = W; FELT.height = H;
    const f = FELT.getContext('2d');
    const g = f.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.1, W / 2, H / 2, Math.max(W, H) * 0.75);
    g.addColorStop(0, '#0F7A50'); g.addColorStop(0.6, C.felt); g.addColorStop(1, C.forest);
    f.fillStyle = g; f.fillRect(0, 0, W, H);
    const img = f.getImageData(0, 0, W, H), d = img.data, rnd = mulberry32(5);
    for (let i = 0; i < d.length; i += 4) { const n = (rnd() - 0.5) * 14; d[i] += n; d[i + 1] += n; d[i + 2] += n; }
    f.putImageData(img, 0, 0);
  },
  draw(ctx, u, t, IMG) {
    if (t < S.deck) sHook(ctx, t, IMG);
    else if (t < S.scan) sDeck(ctx, t);
    else if (t < S.name) sScan(ctx, t, IMG);
    else if (t < S.manager) sName(ctx, t, IMG);
    else if (t < S.intro) sManager(ctx, t, IMG);
    else if (t < S.rounds) sIntro(ctx, t);
    else if (t < S.shuffle) sRounds(ctx, t);
    else if (t < S.words) sShuffle(ctx, t, IMG);
    else if (t < S.story) sWords(ctx, t);
    else if (t < S.bridge) sStory(ctx, t);
    else if (t < S.talk) sBridge(ctx, t);
    else if (t < S.give) sTalk(ctx, t);
    else if (t < S.mycard) sGive(ctx, t);
    else if (t < S.end) sMyCard(ctx, t, IMG);
    else sEnd(ctx, t, IMG);
    if (t > 0.3 && t < S.end - 0.05) subtitles(ctx, t);
  },
});
