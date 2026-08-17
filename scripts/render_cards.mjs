// AURA — Visual Designer v2: illustrated-interior post cards
// Usage: PW_EXEC=/opt/pw-browsers/chromium node scripts/render_cards.mjs [--only YYYY-MM-DD]
import { chromium } from 'playwright';
import { readFileSync, mkdirSync, existsSync } from 'fs';
import { dirname, join, extname } from 'path';
import { fileURLToPath } from 'url';
import { roomScene } from './scene.mjs';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const cal = JSON.parse(readFileSync(join(ROOT, 'content/calendar.json'), 'utf8'));
const only = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1] : null;
mkdirSync(join(ROOT, 'content/queue'), { recursive: true });

// ---- Real photo pool (Openverse-fetched by scripts/fetch_images.py) ----
// content/assets/credits.json: { "<filename>": { room, license, creator, source, ... } }
const ASSETS_DIR = join(ROOT, 'content/assets');
const CREDITS_PATH = join(ASSETS_DIR, 'credits.json');
const credits = existsSync(CREDITS_PATH) ? JSON.parse(readFileSync(CREDITS_PATH, 'utf8')) : {};
const photosByRoom = {};
for (const [file, meta] of Object.entries(credits)) {
  const room = meta.room || 'living';
  (photosByRoom[room] ||= []).push({ file, ...meta });
}
// deterministic per-day pick: same photo for IG+Pin of a day, different across days
const mime = f => ({ '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' }[extname(f).toLowerCase()] || 'image/jpeg');

function pickPhoto(tag, seed) {
  const pool = (photosByRoom[tag] || photosByRoom.living || []).slice().sort((a, b) => a.file.localeCompare(b.file));
  if (!pool.length) return null;
  let h = 0;
  for (const ch of String(seed || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const chosen = pool[h % pool.length];
  try {
    const data = readFileSync(join(ASSETS_DIR, chosen.file));
    return { dataUri: `data:${mime(chosen.file)};base64,${data.toString('base64')}`, ...chosen };
  } catch {
    return null;
  }
}
const needsCredit = lic => lic && /by/i.test(lic); // any CC BY variant requires attribution; CC0/PDM don't

const C = {
  ivory: '#faf7f2', ink: '#1f2937', ink2: '#6b7280',
  terra: '#b45309', amber: '#d97706', gold: '#f59e0b', dark: '#1c1917'
};
const esc = s => (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
const firstSentences = (s, n = 2) => s.split('।').slice(0, n).map(x => x.trim()).filter(Boolean).join('। ') + '।';

function shell(inner, { w, h, dark = false }) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Noto+Sans+Devanagari:wght@500;700&display=swap');
  *{margin:0;padding:0;box-sizing:border-box}
  body{width:${w}px;height:${h}px;font-family:'Manrope','Noto Sans Devanagari',sans-serif;
    background:${dark ? C.dark : C.ivory};color:${dark ? C.ivory : C.ink};overflow:hidden;position:relative;display:flex;flex-direction:column}
  .topbar{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;align-items:center;gap:14px;padding:40px 56px;
    background:linear-gradient(180deg,rgba(20,15,10,.55),transparent)}
  .logo{width:60px;height:60px;border-radius:16px;background:linear-gradient(135deg,${C.terra},${C.amber});
    color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:24px;box-shadow:0 4px 14px rgba(0,0,0,.3)}
  .bname{font-weight:800;font-size:27px;color:#fff;text-shadow:0 1px 6px rgba(0,0,0,.4)}
  .btag{font-size:18px;color:#f5f0e8;opacity:.9;text-shadow:0 1px 4px rgba(0,0,0,.4)}
  .scene{position:relative;line-height:0}
  .scene img{display:block;object-fit:cover}
  .scene .fade{position:absolute;left:0;right:0;bottom:-2px;height:130px;
    background:linear-gradient(180deg,transparent,${dark ? C.dark : C.ivory})}
  .badge{position:absolute;z-index:4;padding:9px 20px;border-radius:99px;font-size:21px;font-weight:800;letter-spacing:.02em}
  .credit{position:absolute;z-index:4;font-size:15px;color:#fff;background:#00000070;padding:5px 12px;border-radius:8px}
  .content{flex:1;display:flex;flex-direction:column;justify-content:center;padding:24px 64px 0}
  .kicker{font-size:20px;font-weight:800;letter-spacing:.15em;text-transform:uppercase;color:${C.amber}}
  .accent{height:6px;width:110px;border-radius:99px;background:linear-gradient(90deg,${C.terra},${C.gold});margin:22px 0 26px}
  .hook{font-weight:800;line-height:1.1}
  .sub{line-height:1.5;opacity:.92}
  .foot{display:flex;justify-content:space-between;align-items:center;padding:0 56px 40px;font-size:19px;color:${dark ? '#a8a29e' : C.ink2}}
  .cta{background:${dark ? C.amber : C.ink};color:${dark ? C.dark : '#fff'};padding:13px 24px;border-radius:99px;font-weight:700;font-size:19px}
  </style></head><body>
  <div class="topbar"><div class="logo">DI</div><div><div class="bname">Design Infra</div><div class="btag">Turnkey Interiors · Delhi NCR → Pan-India</div></div></div>
  ${inner}
  <div class="foot"><span>@designinfra · Free consultation — link in bio</span><span class="cta">एक टीम। एक कॉन्ट्रैक्ट।</span></div>
  </body></html>`;
}

// Returns { media: <img> or <svg> sized exactly w×h, credit: attribution chip html or '' }
// AI-generated concept photos (scripts/fetch_images.py's Cloudflare Workers AI fallback,
// credits.json entry has ai_generated:true) ALWAYS get their own distinct badge here —
// per brand/BRAND.md's "honest Concept visualisation labels on AI concept images" rule,
// they must never look identical to a real CC BY-credited photo on the card.
function sceneMedia(tag, w, h, fallbackStyle, seed) {
  const photo = pickPhoto(tag, seed);
  if (photo) {
    let credit = '';
    if (photo.ai_generated) {
      credit = `<span class="credit" style="left:20px;bottom:20px">🎨 Concept visualisation (AI)</span>`;
    } else if (needsCredit(photo.license)) {
      credit = `<span class="credit" style="left:20px;bottom:20px">📷 ${esc(photo.creator || 'Unknown')} · CC BY</span>`;
    }
    const media = `<div style="width:${w}px;height:${h}px;overflow:hidden">` +
      `<img src="${photo.dataUri}" style="width:100%;height:100%;object-fit:cover;display:block"></div>`;
    return { media, credit };
  }
  return { media: roomScene(w, h, fallbackStyle), credit: '' };
}

function heroCard(d, { w, h, dark, scene, badge }) {
  const sceneH = Math.round(h * 0.52);
  const hookSize = d.ig.hook_en.length > 38 ? 62 : 76;
  const { media, credit } = sceneMedia(d.photo_tag || 'living', w, sceneH, scene, d.date);
  return shell(`
    <div class="scene">${media}
      ${badge ? `<span class="badge" style="right:40px;top:${sceneH - 64}px;background:#ffffffe6;color:${C.terra}">${badge}</span>` : ''}
      ${credit}
      <div class="fade"></div></div>
    <div class="content">
      <span class="kicker">${esc(d.occasion || d.pillar)}</span><div class="accent"></div>
      <div class="hook" style="font-size:${hookSize}px">${esc(d.ig.hook_en)}</div>
      <div class="sub" style="font-size:31px;margin-top:30px">${esc(firstSentences(d.ig.caption_hi))}</div>
    </div>`, { w, h, dark });
}

function beforeAfterCard(d, { w, h, dark }) {
  const half = Math.round(h * 0.335);
  // BEFORE stays illustrated (we don't fake a "messy" real photo — honesty over drama).
  // AFTER uses a real photo when the researcher found one for this room, else falls back to illustration.
  const after = sceneMedia(d.photo_tag || 'living', w, half, 'warm', d.date);
  return shell(`
    <div class="scene">${roomScene(w, half, 'plain')}
      <span class="badge" style="left:40px;bottom:26px;background:#1f2937d9;color:#fff">BEFORE</span></div>
    <div class="scene">${after.media}
      <span class="badge" style="left:40px;bottom:26px;background:#ffffffe6;color:${C.terra}">AFTER ✨</span>
      ${after.credit}
      <div class="fade"></div></div>
    <div class="content" style="justify-content:flex-start;padding-top:30px">
      <div class="hook" style="font-size:58px">${esc(d.ig.hook_en)}</div>
      <div class="sub" style="font-size:24px;margin-top:16px;opacity:.7">Concept visualisation — असली प्रोजेक्ट फ़ोटो जल्द।</div>
    </div>`, { w, h, dark });
}

function listCard(d, { w, h, dark, items, rows }) {
  const sceneH = Math.round(h * 0.30);
  const { media, credit } = sceneMedia(d.photo_tag || 'living', w, sceneH, 'warm', d.date);
  const body = items
    ? items.map((t, i) => `<div style="display:flex;gap:18px;align-items:center;margin-bottom:21px">
        <div style="min-width:50px;height:50px;border-radius:50%;background:${C.amber}26;color:${C.terra};font-weight:800;font-size:23px;display:flex;align-items:center;justify-content:center">${i + 1}</div>
        <div style="font-size:29px;font-weight:700">${t}</div></div>`).join('')
    : rows.map(r => `<div style="display:flex;justify-content:space-between;padding:17px 0;border-bottom:2px solid ${C.ink}14">
        <span style="font-size:28px;font-weight:700">${r[0]}</span><span style="font-size:28px;font-weight:800;color:${C.terra}">${r[1]}</span></div>`).join('') +
      `<div style="font-size:20px;margin-top:20px;opacity:.7">*साधारण 2BHK, mid-premium रेंज। सटीक बजट डिज़ाइन के बाद।</div>`;
  return shell(`
    <div class="scene">${media}${credit}<div class="fade"></div></div>
    <div class="content" style="justify-content:flex-start;padding-top:8px">
      <span class="kicker">${esc(d.pillar)}</span><div class="accent" style="margin:16px 0 20px"></div>
      <div class="hook" style="font-size:50px;margin-bottom:32px">${esc(d.ig.hook_en)}</div>
      ${body}
    </div>`, { w, h, dark });
}

function cardHTML(d, w, h) {
  switch (d.ig.format) {
    case 'concept transformation (labeled)': return beforeAfterCard(d, { w, h, dark: false });
    case 'tips card / carousel':
      return listCard(d, { w, h, dark: false, items: ['ज़रूरत से पहले लुक चुनना', 'वेंटिलेशन भूल जाना', 'सस्ता हार्डवेयर — सबसे महँगी ग़लती!', 'वर्क-ट्राएंगल इग्नोर करना', 'बिजली पॉइंट कम रखना'] });
    case 'checklist card':
      return listCard(d, { w, h, dark: false, items: ['दीवारों का फ्रेश टच-अप', 'लाइटिंग अपग्रेड', 'पर्दे और फ़ैब्रिक', 'एंट्रेंस का पहला इम्प्रेशन', 'पूरा मेकओवर? — अभी सही समय है'] });
    case 'cost breakdown card':
      return listCard(d, { w, h, dark: false, rows: [['मॉड्यूलर किचन', '₹3.5–6 लाख'], ['वॉर्डरोब (3 बेडरूम)', '₹2.5–4.5 लाख'], ['फ़ॉल्स सीलिंग + लाइटिंग', '₹1.5–2.5 लाख'], ['पेंट + फ़िनिशेस', '₹1–2 लाख'], ['फ़र्नीचर + डेकोर', '₹3–6 लाख']] });
    case 'quote card':
      return heroCard(d, { w, h, dark: true, scene: 'night', badge: null });
    default: // trend card / explainer card
      return heroCard(d, { w, h, dark: false, scene: 'warm', badge: d.ig.format === 'trend card' ? 'Trend 2026' : null });
  }
}

const browser = await chromium.launch(process.env.PW_EXEC ? { executablePath: process.env.PW_EXEC } : {});
const page = await browser.newPage();
for (const d of cal.days) {
  if (only && d.date !== only) continue;
  await page.setViewportSize({ width: 1080, height: 1350 });
  await page.setContent(cardHTML(d, 1080, 1350), { waitUntil: 'networkidle' });
  await page.screenshot({ path: join(ROOT, `content/queue/${d.date}-ig.png`) });
  await page.setViewportSize({ width: 1000, height: 1500 });
  await page.setContent(cardHTML(d, 1000, 1500), { waitUntil: 'networkidle' });
  await page.screenshot({ path: join(ROOT, `content/queue/${d.date}-pin.png`) });
  console.log('rendered', d.date);
}
await browser.close();
