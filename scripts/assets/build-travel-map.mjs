import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { atlasPoint, atlasPrint } from '../../src/scene/atlas-projection.mjs';

const [countriesPath, seaPath, paperPath, outputPath] = process.argv.slice(2);
if (!countriesPath || !seaPath || !paperPath || !outputPath) {
  throw new Error(
    'Usage: node scripts/assets/build-travel-map.mjs <Natural Earth CHN countries GeoJSON> <CHN maritime lines GeoJSON> <blank paper JPG> <output PNG>',
  );
}
const [countries, maritime, paper] = await Promise.all([
  readFile(countriesPath, 'utf8').then(JSON.parse),
  readFile(seaPath, 'utf8').then(JSON.parse),
  readFile(paperPath, 'base64'),
]);
const { width, height, x, y, spanX, spanY } = atlasPrint;
const path = (points, closed = false) =>
  points
    .map(([lon, lat], i) => {
      const [px, py] = atlasPoint(lon, lat);
      return (i ? 'L' : 'M') + px.toFixed(1) + ',' + py.toFixed(1);
    })
    .join('') + (closed ? 'Z' : '');
const inks = ['#c8ab72', '#809991', '#b99180', '#c6b384', '#9e9e7e', '#a3a595', '#b59b82'];
const outlines = countries.features
  .map(({ geometry }, index) => {
    const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
    const color = inks[index % inks.length];
    return `<path d="${polygons.flatMap((polygon) => polygon.map((ring) => path(ring, true))).join('')}"
    fill="${color}" fill-opacity=".43" stroke="#534c42" stroke-width="1.05" stroke-linejoin="round" fill-rule="evenodd"/>`;
  })
  .join('');
const disputed = maritime.features
  .flatMap(({ geometry }) => {
    const lines = geometry.type === 'LineString' ? [geometry.coordinates] : geometry.coordinates;
    return lines.map((line) => `<path d="${path(line)}"/>`);
  })
  .join('');
const graticule = [
  ...Array.from({ length: 25 }, (_, i) =>
    path([
      [i * 15 - 180, -90],
      [i * 15 - 180, 90],
    ]),
  ),
  ...Array.from({ length: 13 }, (_, i) =>
    path([
      [-180, i * 15 - 90],
      [180, i * 15 - 90],
    ]),
  ),
]
  .map((d) => `<path d="${d}"/>`)
  .join('');
const escape = (value) =>
  value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const labels = [];
const occupied = [];
const editorial = new Map([
  ['United Kingdom', { name: 'UNITED KINGDOM', at: [-7.5, 58] }],
  ['Japan', { name: 'JAPAN', at: [142, 36.3] }],
  ['South Korea', { name: 'S. KOREA', at: [128.5, 33.5] }],
  ['North Korea', { name: 'N. KOREA', at: [127.4, 39.8] }],
  ['Democratic Republic of the Congo', { name: 'D. R. CONGO' }],
  ['New Zealand', { name: 'NEW ZEALAND', at: [166.8, -43.5] }],
  ['Portugal', { name: 'PORTUGAL', at: [-12.1, 39.5] }],
]);
const candidates = countries.features
  .map(({ properties }) => properties)
  .filter(
    (country) =>
      ['Sovereign country', 'Sovereignty'].includes(country.TYPE) ||
      (country.TYPE === 'Country' && country.ADMIN === country.SOVEREIGNT),
  )
  .filter((country) => Number.isFinite(country.LABEL_X) && Number.isFinite(country.LABEL_Y))
  .sort(
    (a, b) =>
      Number(editorial.has(b.ADMIN)) - Number(editorial.has(a.ADMIN)) || a.LABELRANK - b.LABELRANK,
  );
for (const country of candidates) {
  const custom = editorial.get(country.ADMIN);
  const name =
    custom?.name ??
    (country.NAME.length > 20 && country.ABBREV ? country.ABBREV : country.NAME).toUpperCase();
  const [px, py] = atlasPoint(...(custom?.at ?? [country.LABEL_X, country.LABEL_Y]));
  const size = country.LABELRANK <= 2 ? 18 : country.LABELRANK <= 3 ? 14 : 12;
  const wordWidth = name.length * size * 0.69 + 9;
  const box = {
    left: px - wordWidth / 2,
    right: px + wordWidth / 2,
    top: py - size - 1,
    bottom: py + 5,
  };
  if (
    box.left < x ||
    box.right > x + spanX ||
    occupied.some(
      (b) => box.left < b.right && box.right > b.left && box.top < b.bottom && box.bottom > b.top,
    )
  )
    continue;
  occupied.push(box);
  labels.push(`<text x="${px}" y="${py}" font-size="${size}">${escape(name)}</text>`);
}
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
<defs>
  <radialGradient id="edge"><stop offset="40%" stop-color="#f4e6c9" stop-opacity="0"/><stop offset="100%" stop-color="#88612a" stop-opacity=".28"/></radialGradient>
  <pattern id="grain" patternUnits="userSpaceOnUse" width="6" height="6"><circle cx="2" cy="1" r=".55" fill="#493926" opacity=".21"/><circle cx="5" cy="5" r=".42" fill="#614c33" opacity=".16"/></pattern>
  <pattern id="paper" patternUnits="userSpaceOnUse" width="2880" height="540">
    <image href="data:image/jpeg;base64,${paper}" width="2880" height="270" preserveAspectRatio="none"/>
    <image href="data:image/jpeg;base64,${paper}" width="2880" height="270" preserveAspectRatio="none" transform="translate(0 540) scale(1 -1)"/>
  </pattern>
</defs>
<rect width="100%" height="100%" fill="#e1cda6"/>
<rect width="100%" height="100%" fill="url(#paper)" opacity=".78"/>
<rect width="100%" height="100%" fill="url(#edge)"/>
<rect x="36" y="34" width="2808" height="1552" rx="2" fill="none" stroke="#463e34" stroke-width="4"/>
<rect x="46" y="44" width="2788" height="1532" fill="none" stroke="#625343" stroke-width="1.25"/>
<g font-family="Georgia, serif" fill="#332b23" text-anchor="middle">
  <text x="1440" y="111" font-size="43" letter-spacing="8">MAP OF THE WORLD</text>
  <text x="1440" y="1546" font-size="16" letter-spacing="4">THE TRAVEL COLLECTION</text>
</g>
<rect x="${x}" y="${y}" width="${spanX}" height="${spanY}" fill="#9dadab" fill-opacity=".12" stroke="#746453" stroke-width="1.6"/>
<g fill="none" stroke="#726650" stroke-opacity=".46" stroke-width=".9">${graticule}</g>
${outlines}
<g stroke="#756459" fill="none" stroke-width="1.7" stroke-dasharray="9 5">${disputed}</g>
<rect x="${x}" y="${y}" width="${spanX}" height="${spanY}" fill="url(#grain)"/>
<g font-family="Georgia, serif" font-weight="700" fill="#3a3228" paint-order="stroke" stroke="#ede0c2" stroke-opacity=".75" stroke-width="1.6" text-anchor="middle" letter-spacing=".85">${labels.join('')}</g>
</svg>`;
const browser = await chromium.launch({ channel: 'chrome' });
try {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent('<style>body { margin: 0; }</style>' + svg);
  await page.screenshot({ path: outputPath });
  console.log(`${labels.length} country labels at ${width} × ${height}`);
} finally {
  await browser.close();
}
