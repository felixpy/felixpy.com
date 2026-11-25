import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readdirSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, extname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, '..', '..');
const mediaRoot = join(repoRoot, 'public', 'media');

const SCAN_DIRS = ['materials', 'photography', 'panoramas'];
const EXPLICIT_HIGH_QUALITY_SRGB = new Set([
  'graphics/world-atlas.webp',
  'graphics/shelf-covers.webp',
]);
const SOURCE_EXTS = new Set(['.webp', '.png', '.jpg', '.jpeg']);
const MIN_SOURCE_BYTES = 4000;

// Textures whose UV space in Three.js uses flipY = false (glTF upper-left origin).
const UPPER_LEFT_ORIGIN = new Set(['photography/desk-portrait.webp']);

// Linear normal / directional slope textures (must NOT use --normal_mode because
// Three.js reads RGB .xyz directly, whereas toktx --normal_mode swizzles into RGB=X, A=Y).
const EXPLICIT_NORMAL_MAPS = new Set([
  'materials/cork-grain.webp',
  'panoramas/river-slopes.webp',
  'panoramas/glass-rain-beads.png',
]);

// Linear scalar / roughness textures.
const EXPLICIT_LINEAR_MAPS = new Set(['materials/tolomeo-axial-grain.png']);

function isExcluded(relPath) {
  if (relPath.startsWith('photography/field-notes/')) {
    return 'replaced by field-notes-atlas.webp';
  }
  if (relPath.startsWith('panoramas/') && /-depth\.png$/i.test(relPath)) {
    return 'depth map (exact scalar values, no block compression)';
  }
  if (relPath === 'panoramas/river-ferry-reflection.png') {
    return 'small RGBA reflection atlas';
  }
  return null;
}

export function classifyTexture(relPath) {
  if (EXPLICIT_HIGH_QUALITY_SRGB.has(relPath)) {
    return 'srgb-uastc';
  }
  if (EXPLICIT_NORMAL_MAPS.has(relPath) || /-normal\.[^.]+$/i.test(relPath)) {
    return 'normal';
  }
  if (EXPLICIT_LINEAR_MAPS.has(relPath) || /-rough(?:ness)?\.[^.]+$/i.test(relPath)) {
    return 'linear';
  }
  return 'srgb';
}

export function locateToktx() {
  const candidates = [];
  if (process.env.TOKTX_BIN) candidates.push(process.env.TOKTX_BIN);

  const locator = process.platform === 'win32' ? 'where' : 'which';
  const found = spawnSync(locator, ['toktx'], { encoding: 'utf8' });
  if (found.status === 0 && found.stdout) {
    for (const line of found.stdout.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (trimmed) candidates.push(trimmed);
    }
  }

  candidates.push('D:\\Creative\\KTX-Software\\bin\\toktx.exe');

  for (const candidate of candidates) {
    if (candidate && existsSync(candidate)) return candidate;
  }
  throw new Error(
    'Could not locate toktx binary. Set TOKTX_BIN or install KTX-Software (expected D:\\Creative\\KTX-Software\\bin\\toktx.exe).',
  );
}

function toktxArgsFor(relPath, role) {
  const originFlag = UPPER_LEFT_ORIGIN.has(relPath)
    ? '--upper_left_maps_to_s0t0'
    : '--lower_left_maps_to_s0t0';
  if (role === 'srgb-uastc') {
    return [
      '--t2',
      '--encode',
      'uastc',
      '--uastc_quality',
      '3',
      '--uastc_rdo_l',
      '0.5',
      '--zcmp',
      '19',
      '--genmipmap',
      originFlag,
      '--assign_oetf',
      'srgb',
    ];
  }
  if (role === 'normal' || role === 'linear') {
    return [
      '--t2',
      '--encode',
      'uastc',
      '--uastc_quality',
      '2',
      '--uastc_rdo_l',
      '1.2',
      '--zcmp',
      '18',
      '--genmipmap',
      originFlag,
      '--assign_oetf',
      'linear',
    ];
  }
  return [
    '--t2',
    '--encode',
    'etc1s',
    '--clevel',
    '3',
    '--qlevel',
    '220',
    '--genmipmap',
    originFlag,
    '--assign_oetf',
    'srgb',
  ];
}

function scanCandidates(filterSubstr) {
  const included = [];
  const skipped = [];

  for (const dir of SCAN_DIRS) {
    const absDir = join(mediaRoot, dir);
    if (!existsSync(absDir)) continue;
    const entries = readdirSync(absDir, { recursive: true, withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isFile()) continue;
      const fullPath = join(entry.parentPath, entry.name);
      const ext = extname(entry.name).toLowerCase();
      if (!SOURCE_EXTS.has(ext)) continue;

      const relPath = relative(mediaRoot, fullPath).replaceAll('\\', '/');
      if (filterSubstr && !relPath.includes(filterSubstr)) continue;

      const excludedReason = isExcluded(relPath);
      if (excludedReason) {
        skipped.push({ relPath, bytes: statSync(fullPath).size, reason: excludedReason });
        continue;
      }

      const bytes = statSync(fullPath).size;
      if (bytes < MIN_SOURCE_BYTES) {
        skipped.push({ relPath, bytes, reason: `< ${MIN_SOURCE_BYTES} B` });
        continue;
      }

      const outPath = fullPath.slice(0, -ext.length) + '.ktx2';
      included.push({
        relPath,
        fullPath,
        outPath,
        ext,
        bytes,
        role: classifyTexture(relPath),
      });
    }
  }

  for (const relPath of EXPLICIT_HIGH_QUALITY_SRGB) {
    if (filterSubstr && !relPath.includes(filterSubstr)) continue;
    const fullPath = join(mediaRoot, relPath);
    if (!existsSync(fullPath)) continue;
    const ext = extname(relPath).toLowerCase();
    const bytes = statSync(fullPath).size;
    const outPath = fullPath.slice(0, -ext.length) + '.ktx2';
    included.push({
      relPath,
      fullPath,
      outPath,
      ext,
      bytes,
      role: classifyTexture(relPath),
    });
  }

  included.sort((a, b) => a.relPath.localeCompare(b.relPath));
  skipped.sort((a, b) => a.relPath.localeCompare(b.relPath));
  return { included, skipped };
}

function prepareInputsWithPillow(items, tempDir) {
  const payload = items.map((item, idx) => ({
    relPath: item.relPath,
    src: item.fullPath,
    tmpPng: join(tempDir, `${String(idx).padStart(4, '0')}.png`),
  }));

  const pyScript = `
import json, sys
from PIL import Image

items = json.loads(sys.stdin.read())
results = []
for it in items:
    src = it["src"]
    tmp_png = it["tmpPng"]
    with Image.open(src) as im:
        orig_w, orig_h = im.size
        orig_mode = im.mode
        target_w = max(4, round(orig_w / 4) * 4)
        target_h = max(4, round(orig_h / 4) * 4)
        resized = (target_w != orig_w) or (target_h != orig_h)
        needs_convert = (
            src.lower().endswith(".webp")
            or resized
            or orig_mode not in ("RGB", "RGBA")
        )
        if needs_convert:
            work = im
            if orig_mode in ("RGBA", "LA") or (orig_mode == "P" and "transparency" in im.info):
                work = work.convert("RGBA")
            else:
                work = work.convert("RGB")
            if resized:
                work = work.resize((target_w, target_h), Image.Resampling.LANCZOS)
            work.save(tmp_png, format="PNG")
            input_path = tmp_png
        else:
            input_path = src
        results.append({
            "relPath": it["relPath"],
            "inputPath": input_path,
            "origW": orig_w,
            "origH": orig_h,
            "targetW": target_w,
            "targetH": target_h,
            "mode": orig_mode,
            "resized": resized,
        })
print(json.dumps(results))
`;

  const res = spawnSync('uv', ['run', '--with', 'pillow', 'python', '-c', pyScript], {
    input: JSON.stringify(payload),
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
  });
  if (res.status !== 0) {
    throw new Error(`Pillow preprocessing failed:\n${res.stderr || res.stdout}`);
  }
  const parsed = JSON.parse(res.stdout);
  return new Map(parsed.map((entry) => [entry.relPath, entry]));
}

function formatKB(bytes) {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatMB(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

// Estimate full mipmap chain GPU VRAM: sum of 1 + 1/4 + 1/16 + ... ≈ 4/3 of base level.
function vramBytes(width, height, bytesPerPixel) {
  let w = width;
  let h = height;
  let total = 0;
  while (true) {
    total += Math.max(4, w) * Math.max(4, h) * bytesPerPixel;
    if (w <= 1 && h <= 1) break;
    w = Math.max(1, Math.floor(w / 2));
    h = Math.max(1, Math.floor(h / 2));
  }
  return total;
}

function main() {
  const args = process.argv.slice(2);
  const force = args.includes('--force');
  const dryRun = args.includes('--dry-run');
  const filterIdx = args.indexOf('--filter');
  const filterSubstr = filterIdx >= 0 ? args[filterIdx + 1] : undefined;

  const toktx = locateToktx();
  const { included, skipped } = scanCandidates(filterSubstr);

  console.log(`Using toktx: ${toktx}`);
  console.log(`Found ${included.length} textures to encode, ${skipped.length} skipped.\n`);

  if (dryRun) {
    for (const item of included) {
      const origin = UPPER_LEFT_ORIGIN.has(item.relPath) ? 'upper-left' : 'lower-left';
      console.log(
        `[encode] ${item.relPath.padEnd(46)} role=${item.role.padEnd(6)} origin=${origin.padEnd(10)} ${formatKB(item.bytes)}`,
      );
    }
    console.log('');
    for (const item of skipped) {
      console.log(
        `[skip]   ${item.relPath.padEnd(46)} ${formatKB(item.bytes).padStart(9)}  (${item.reason})`,
      );
    }
    return;
  }

  const tempDir = mkdtempSync(join(tmpdir(), 'felix-ktx2-'));
  try {
    const metaMap = prepareInputsWithPillow(included, tempDir);
    const rows = [];
    let encodedCount = 0;
    let cachedCount = 0;

    for (const item of included) {
      const meta = metaMap.get(item.relPath);
      const srcMtime = statSync(item.fullPath).mtimeMs;
      const upToDate =
        !force && existsSync(item.outPath) && statSync(item.outPath).mtimeMs >= srcMtime;

      if (!upToDate) {
        const toktxArgs = [...toktxArgsFor(item.relPath, item.role), item.outPath, meta.inputPath];
        execFileSync(toktx, toktxArgs, { stdio: 'pipe' });
        encodedCount++;
      } else {
        cachedCount++;
      }

      const ktx2Bytes = statSync(item.outPath).size;
      // RGBA8 uncompressed = 4 B/px; BC7 / ASTC 4x4 compressed = 1 B/px (8 bpp).
      const rgbaVram = vramBytes(meta.origW, meta.origH, 4);
      const bc7Vram = vramBytes(meta.targetW, meta.targetH, 1);

      rows.push({
        relPath: item.relPath,
        role: item.role,
        codec: item.role === 'srgb' ? 'etc1s' : 'uastc',
        dims: meta.resized
          ? `${meta.origW}x${meta.origH}->${meta.targetW}x${meta.targetH}`
          : `${meta.targetW}x${meta.targetH}`,
        srcBytes: item.bytes,
        ktx2Bytes,
        rgbaVram,
        bc7Vram,
        status: upToDate ? 'cached' : 'encoded',
      });
    }

    const header =
      'Texture'.padEnd(44) +
      'Role'.padEnd(8) +
      'Codec'.padEnd(7) +
      'Dimensions'.padEnd(22) +
      'Source'.padStart(10) +
      'KTX2'.padStart(10) +
      'RGBA VRAM'.padStart(11) +
      'BC7 VRAM'.padStart(10);
    console.log(header);
    console.log('-'.repeat(header.length));

    let totalSrc = 0;
    let totalKtx2 = 0;
    let totalRgbaVram = 0;
    let totalBc7Vram = 0;

    for (const row of rows) {
      totalSrc += row.srcBytes;
      totalKtx2 += row.ktx2Bytes;
      totalRgbaVram += row.rgbaVram;
      totalBc7Vram += row.bc7Vram;
      console.log(
        row.relPath.padEnd(44) +
          row.role.padEnd(8) +
          row.codec.padEnd(7) +
          row.dims.padEnd(22) +
          formatKB(row.srcBytes).padStart(10) +
          formatKB(row.ktx2Bytes).padStart(10) +
          formatMB(row.rgbaVram).padStart(11) +
          formatMB(row.bc7Vram).padStart(10),
      );
    }

    console.log('-'.repeat(header.length));
    console.log(
      `TOTAL (${rows.length} textures: ${encodedCount} encoded, ${cachedCount} cached)`.padEnd(81) +
        formatMB(totalSrc).padStart(10) +
        formatMB(totalKtx2).padStart(10) +
        formatMB(totalRgbaVram).padStart(11) +
        formatMB(totalBc7Vram).padStart(10),
    );
    const vramSavingsPct = (((totalRgbaVram - totalBc7Vram) / totalRgbaVram) * 100).toFixed(1);
    console.log(
      `\nEstimated GPU VRAM savings (RGBA8+mips -> BC7/ASTC 4x4+mips): ${formatMB(totalRgbaVram - totalBc7Vram)} (-${vramSavingsPct}%)`,
    );

    if (skipped.length > 0) {
      console.log('\nSkipped textures:');
      for (const item of skipped) {
        console.log(`  - ${item.relPath} (${formatKB(item.bytes)}): ${item.reason}`);
      }
    }
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
