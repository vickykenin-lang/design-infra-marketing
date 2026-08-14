// AURA — illustrated interior scene generator (SVG, zero external assets)
// styles: 'warm' (styled room) | 'plain' (bare room) | 'night' (evening mood)
export function roomScene(w, h, style = 'warm') {
  const warm = style === 'warm' || style === 'night';
  const night = style === 'night';
  const wallA = night ? '#2d2420' : warm ? '#f3e3cf' : '#d6d3d1';
  const wallB = night ? '#1c1613' : warm ? '#e7cdae' : '#c7c2bc';
  const floor = night ? '#3a2d24' : warm ? '#c89b6d' : '#b0a89f';
  const floorDark = night ? '#2b211a' : warm ? '#b0834f' : '#9c948a';
  const sofa = warm ? '#b45309' : '#8a8580';
  const sofaDark = warm ? '#92400e' : '#767168';
  const cushion1 = warm ? '#f59e0b' : '#a39d96';
  const cushion2 = warm ? '#fde8c8' : '#bab4ac';
  const winSky = night ? '#0f172a' : '#dbeafe';
  const winGlow = night ? '#f59e0b' : '#fef3c7';
  const plant = warm ? '#3f6212' : '#6b7280';
  const lampOn = warm;
  return `
<svg viewBox="0 0 1000 720" width="${w}" height="${h}" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${wallA}"/><stop offset="1" stop-color="${wallB}"/>
    </linearGradient>
    <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${floor}"/><stop offset="1" stop-color="${floorDark}"/>
    </linearGradient>
    <radialGradient id="lampglow" cx=".5" cy=".35" r=".6">
      <stop offset="0" stop-color="#fbbf24" stop-opacity=".85"/><stop offset="1" stop-color="#fbbf24" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="winlight" cx=".5" cy=".5" r=".7">
      <stop offset="0" stop-color="${winGlow}" stop-opacity=".9"/><stop offset="1" stop-color="${winGlow}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1000" height="520" fill="url(#wall)"/>
  <rect y="520" width="1000" height="200" fill="url(#floor)"/>
  <rect y="514" width="1000" height="10" fill="${night ? '#15100d' : '#00000018'}"/>

  <!-- window -->
  <g transform="translate(80,80)">
    <rect x="-14" y="-14" width="288" height="348" rx="10" fill="${night ? '#4a3a2c' : '#fff'}" opacity="${night ? .9 : .95}"/>
    <rect width="260" height="320" fill="${winSky}"/>
    ${night ? '<circle cx="200" cy="60" r="26" fill="#fde68a"/><circle cx="190" cy="52" r="24" fill="' + winSky + '"/><circle cx="60" cy="40" r="2.5" fill="#fff"/><circle cx="110" cy="90" r="2" fill="#fff"/><circle cx="40" cy="130" r="2" fill="#fff"/>' : '<circle cx="70" cy="70" r="34" fill="#fde68a"/><path d="M0 210 Q70 160 140 205 T260 200 V320 H0 Z" fill="#bfdbfe"/>'}
    <rect x="126" width="9" height="320" fill="${night ? '#4a3a2c' : '#fff'}"/>
    <rect y="156" width="260" height="9" fill="${night ? '#4a3a2c' : '#fff'}"/>
    <ellipse cx="130" cy="420" rx="220" ry="60" fill="url(#winlight)" opacity="${night ? .25 : .6}"/>
  </g>

  <!-- wall art -->
  <g transform="translate(470,110)">
    <rect width="150" height="190" rx="8" fill="${night ? '#241c17' : '#fff'}" stroke="${warm ? '#b45309' : '#9c948a'}" stroke-width="6"/>
    ${warm ? '<path d="M25 140 L60 85 L90 120 L115 70 L128 140 Z" fill="#d97706"/><circle cx="45" cy="55" r="14" fill="#f59e0b"/>' : '<rect x="30" y="40" width="90" height="110" fill="#d6d3d1"/>'}
    <rect x="185" y="34" width="120" height="122" rx="8" fill="${night ? '#241c17' : '#fff'}" stroke="${warm ? '#78350f' : '#9c948a'}" stroke-width="6"/>
    ${warm ? '<path d="M210 120 Q245 60 290 118 Z" fill="#b45309"/>' : ''}
  </g>

  <!-- shelf -->
  ${warm ? `<g transform="translate(830,150)">
    <rect width="120" height="10" rx="5" fill="#78350f"/>
    <rect x="12" y="-46" width="26" height="46" rx="4" fill="#d97706"/>
    <rect x="48" y="-34" width="20" height="34" rx="4" fill="#f59e0b"/>
    <path d="M86 0 q14 -40 26 0 Z" fill="#3f6212"/>
    <rect y="120" width="120" height="10" rx="5" fill="#78350f"/>
    <rect x="20" y="86" width="34" height="34" rx="6" fill="#fde8c8"/>
    <rect x="66" y="74" width="18" height="46" rx="4" fill="#b45309"/>
  </g>` : ''}

  <!-- sofa -->
  <g transform="translate(320,380)">
    <rect x="0" y="60" width="420" height="150" rx="26" fill="${sofa}"/>
    <rect x="18" y="-10" width="384" height="110" rx="24" fill="${sofaDark}"/>
    <rect x="-26" y="40" width="70" height="150" rx="22" fill="${sofaDark}"/>
    <rect x="376" y="40" width="70" height="150" rx="22" fill="${sofaDark}"/>
    <rect x="46" y="30" width="150" height="86" rx="18" fill="${cushion1}" transform="rotate(-4 121 73)"/>
    <rect x="230" y="30" width="150" height="86" rx="18" fill="${cushion2}" transform="rotate(3 305 73)"/>
    <rect x="30" y="206" width="18" height="34" fill="#57534e"/><rect x="380" y="206" width="18" height="34" fill="#57534e"/>
  </g>

  <!-- rug -->
  <ellipse cx="530" cy="660" rx="330" ry="44" fill="${warm ? '#92400e' : '#a39d96'}" opacity=".55"/>
  <ellipse cx="530" cy="660" rx="250" ry="32" fill="${warm ? '#d97706' : '#b0a89f'}" opacity=".45"/>

  <!-- coffee table -->
  <g transform="translate(430,570)">
    <ellipse cx="100" cy="66" rx="120" ry="20" fill="#00000022"/>
    <rect x="0" y="0" width="200" height="16" rx="8" fill="${night ? '#4a3a2c' : '#78350f'}"/>
    <rect x="24" y="16" width="12" height="52" fill="${night ? '#3a2d24' : '#57534e'}"/>
    <rect x="164" y="16" width="12" height="52" fill="${night ? '#3a2d24' : '#57534e'}"/>
    ${warm ? '<rect x="70" y="-26" width="40" height="26" rx="6" fill="#3f6212"/><rect x="84" y="-42" width="12" height="18" fill="#65a30d"/>' : ''}
  </g>

  <!-- floor lamp -->
  <g transform="translate(120,430)">
    ${lampOn ? '<ellipse cx="40" cy="10" rx="130" ry="90" fill="url(#lampglow)"/>' : ''}
    <path d="M8 0 h64 l-14 -52 h-36 Z" fill="${lampOn ? '#fbbf24' : '#8a8580'}"/>
    <rect x="36" y="0" width="8" height="210" fill="${night ? '#8a8580' : '#57534e'}"/>
    <rect x="8" y="210" width="64" height="12" rx="6" fill="${night ? '#8a8580' : '#57534e'}"/>
  </g>

  <!-- plant -->
  <g transform="translate(880,470)">
    <path d="M0 130 h84 l-12 90 h-60 Z" fill="${warm ? '#b45309' : '#8a8580'}"/>
    <g fill="${plant}">
      <path d="M42 130 C 10 90 -18 60 6 10 C 30 44 40 80 42 130Z"/>
      <path d="M42 130 C 74 86 96 62 82 6 C 56 40 46 80 42 130Z"/>
      <path d="M42 130 C 40 76 42 40 42 -18 C 58 30 56 84 42 130Z" opacity=".85"/>
    </g>
  </g>

  ${night ? '<rect width="1000" height="720" fill="#78350f" opacity=".08"/>' : ''}
</svg>`;
}
