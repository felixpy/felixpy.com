import { execFile, spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { gzipSync } from 'node:zlib';
import { MeshoptDecoder, MeshoptEncoder } from 'meshoptimizer';
import { assembleProducts, readProduct } from '../build/static-product.mjs';
import { locateToktx } from './encode-ktx2.mjs';

const execFileAsync = promisify(execFile);
const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, '..', '..');
const modelsDir = join(repoRoot, 'public', 'media', 'models');

// Nodes in vitrine-inventory.glb subject to a strict < 1,000,000-byte per-casting size budget
// in tests/installed-products.spec.mjs (already quantized Int8 normals + meshopt + WebP).
const PRESERVE_CASTING_ITEMS = new Set([
  'Sun Wukong · The Great Victory',
  'Tongshifu · Iron Man Mark 85',
]);

// Models with fine typography / silkscreen / printed labels where UASTC+Zstd preserves crisp text.
const UASTC_SRGB_MODELS = new Set([
  'cfexpress-type-b.glb',
  'codex-micro.glb',
  'dji-mic-2.glb',
  'gr701-lighting-board.glb',
  'mac-studio-m5-ultra-room.glb',
  'mac-studio-m5-ultra.glb',
  'mitsubishi-9850.glb',
  'prograde-pg05-5.glb',
  'rog-azoth-extreme.glb',
  'rog-harpe-extreme.glb',
  'rog-herculx-xh01.glb',
  'samsung-t7.glb',
  'selphy-cp1500.glb',
  'skog-20303.glb',
  'strix-z890-a.glb',
  'window-controller.glb',
  'xpg-d50-fubuki.glb',
]);

const LINEAR_ROLES = new Set([
  'normal',
  'mr',
  'ao',
  'clearcoatNormal',
  'clearcoatRoughness',
  'sheenRoughness',
  'specular',
]);

const SRGB_ROLES = new Set(['baseColor', 'emissive', 'sheenColor', 'specularColor']);

const COMPONENT_TYPED_ARRAY = {
  5120: Int8Array,
  5121: Uint8Array,
  5122: Int16Array,
  5123: Uint16Array,
  5125: Uint32Array,
  5126: Float32Array,
};

const COMPONENT_BYTE_SIZE = {
  5120: 1,
  5121: 1,
  5122: 2,
  5123: 2,
  5125: 4,
  5126: 4,
};

const TYPE_COMPONENTS = {
  SCALAR: 1,
  VEC2: 2,
  VEC3: 3,
  VEC4: 4,
  MAT2: 4,
  MAT3: 9,
  MAT4: 16,
};

const MIN_KTX2_PIXELS = 64 * 64;

function mipVramBytes(width, height, bytesPerPixel) {
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

function collectImageRoles(doc) {
  const roles = new Map();
  const addRole = (texIdx, role) => {
    const tex = doc.textures?.[texIdx];
    if (!tex) return;
    const src =
      tex.source ??
      tex.extensions?.EXT_texture_webp?.source ??
      tex.extensions?.KHR_texture_basisu?.source;
    if (src === undefined) return;
    if (!roles.has(src)) roles.set(src, new Set());
    roles.get(src).add(role);
  };

  for (const mat of doc.materials ?? []) {
    const pbr = mat.pbrMetallicRoughness;
    if (pbr?.baseColorTexture) addRole(pbr.baseColorTexture.index, 'baseColor');
    if (pbr?.metallicRoughnessTexture) addRole(pbr.metallicRoughnessTexture.index, 'mr');
    if (mat.normalTexture) addRole(mat.normalTexture.index, 'normal');
    if (mat.occlusionTexture) addRole(mat.occlusionTexture.index, 'ao');
    if (mat.emissiveTexture) addRole(mat.emissiveTexture.index, 'emissive');
    if (mat.extensions) {
      for (const [extName, extVal] of Object.entries(mat.extensions)) {
        if (!extVal || typeof extVal !== 'object') continue;
        for (const [key, val] of Object.entries(extVal)) {
          if (
            !key.endsWith('Texture') ||
            !val ||
            typeof val !== 'object' ||
            val.index === undefined
          )
            continue;
          if (key === 'clearcoatNormalTexture') addRole(val.index, 'clearcoatNormal');
          else if (key === 'clearcoatRoughnessTexture') addRole(val.index, 'clearcoatRoughness');
          else if (key === 'sheenColorTexture') addRole(val.index, 'sheenColor');
          else if (key === 'sheenRoughnessTexture') addRole(val.index, 'sheenRoughness');
          else if (key === 'specularColorTexture') addRole(val.index, 'specularColor');
          else if (key === 'specularTexture') addRole(val.index, 'specular');
          else addRole(val.index, `${extName}.${key}`);
        }
      }
    }
  }
  return roles;
}

function decodeBufferViewBytes(doc, data, viewIndex) {
  const view = doc.bufferViews[viewIndex];
  const stream = view.extensions?.EXT_meshopt_compression;
  const range = stream ?? view;
  const start = range.byteOffset ?? 0;
  const raw = Uint8Array.from(data.subarray(start, start + range.byteLength));
  if (!stream) return raw;
  const decoded = new Uint8Array(stream.count * stream.byteStride);
  MeshoptDecoder.decodeGltfBuffer(
    decoded,
    stream.count,
    stream.byteStride,
    raw,
    stream.mode,
    stream.filter ?? 'NONE',
  );
  return decoded;
}

function readAccessorValues(doc, data, accessorIndex) {
  const acc = doc.accessors[accessorIndex];
  if (acc.sparse || acc.bufferView === undefined) {
    throw new Error(`Unsupported sparse or bufferless accessor ${accessorIndex}`);
  }
  const view = doc.bufferViews[acc.bufferView];
  const bytes = decodeBufferViewBytes(doc, data, acc.bufferView);
  const TypedArray = COMPONENT_TYPED_ARRAY[acc.componentType];
  const elemSize = COMPONENT_BYTE_SIZE[acc.componentType];
  const comps = TYPE_COMPONENTS[acc.type];
  const packedStride = comps * elemSize;
  const stride = view.byteStride ?? packedStride;
  const accOffset = acc.byteOffset ?? 0;

  if (stride === packedStride && accOffset === 0 && bytes.byteLength === acc.count * packedStride) {
    return new TypedArray(bytes.buffer, bytes.byteOffset, acc.count * comps);
  }
  const out = new TypedArray(acc.count * comps);
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  for (let i = 0; i < acc.count; i++) {
    const base = accOffset + i * stride;
    for (let c = 0; c < comps; c++) {
      const pos = base + c * elemSize;
      switch (acc.componentType) {
        case 5120:
          out[i * comps + c] = dv.getInt8(pos);
          break;
        case 5121:
          out[i * comps + c] = dv.getUint8(pos);
          break;
        case 5122:
          out[i * comps + c] = dv.getInt16(pos, true);
          break;
        case 5123:
          out[i * comps + c] = dv.getUint16(pos, true);
          break;
        case 5125:
          out[i * comps + c] = dv.getUint32(pos, true);
          break;
        case 5126:
          out[i * comps + c] = dv.getFloat32(pos, true);
          break;
      }
    }
  }
  return out;
}

function prepareImagesWithPillow(items, tempDir) {
  if (!items.length) return new Map();
  const payload = items.map((it) => ({
    id: it.id,
    rawPath: it.rawPath,
    pngPath: join(tempDir, `${it.id}.png`),
  }));

  const pyScript = `
import json, sys
from PIL import Image

items = json.loads(sys.stdin.read())
results = []
for it in items:
    with Image.open(it["rawPath"]) as im:
        orig_w, orig_h = im.size
        orig_mode = im.mode
        has_alpha = orig_mode in ("RGBA", "LA") or (orig_mode == "P" and "transparency" in im.info)
        target_w = max(4, round(orig_w / 4) * 4)
        target_h = max(4, round(orig_h / 4) * 4)
        resized = (target_w != orig_w) or (target_h != orig_h)
        work = im.convert("RGBA" if has_alpha else "RGB")
        if resized:
            work = work.resize((target_w, target_h), Image.Resampling.LANCZOS)
        work.save(it["pngPath"], format="PNG")
        results.append({
            "id": it["id"],
            "pngPath": it["pngPath"],
            "origW": orig_w,
            "origH": orig_h,
            "targetW": target_w,
            "targetH": target_h,
            "hasAlpha": has_alpha,
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
  return new Map(parsed.map((entry) => [entry.id, entry]));
}

async function runPool(tasks, concurrency) {
  let cursor = 0;
  const workers = Array.from({ length: Math.min(concurrency, tasks.length) }, async () => {
    while (cursor < tasks.length) {
      const idx = cursor++;
      await tasks[idx]();
    }
  });
  await Promise.all(workers);
}

function toktxArgsForGlbImage(fileName, roles, hasAlpha, targetW, targetH) {
  const hasLinear = [...roles].some((r) => LINEAR_ROLES.has(r));
  const hasSrgb = [...roles].some((r) => SRGB_ROLES.has(r));
  if (hasLinear && hasSrgb) return null;
  const isLarge = targetW * targetH >= 1024 * 1024;
  if (hasLinear) {
    return {
      codec: 'uastc',
      bpp: 1,
      args: [
        '--t2',
        '--encode',
        'uastc',
        '--uastc_quality',
        '2',
        '--uastc_rdo_l',
        isLarge ? '2.0' : '1.2',
        '--zcmp',
        '18',
        '--genmipmap',
        '--upper_left_maps_to_s0t0',
        '--assign_oetf',
        'linear',
      ],
    };
  }
  const useUastc = hasAlpha || roles.has('emissive') || UASTC_SRGB_MODELS.has(fileName);
  if (useUastc) {
    return {
      codec: 'uastc',
      bpp: 1,
      args: [
        '--t2',
        '--encode',
        'uastc',
        '--uastc_quality',
        '2',
        '--uastc_rdo_l',
        isLarge ? '2.2' : '1.5',
        '--zcmp',
        '18',
        '--genmipmap',
        '--upper_left_maps_to_s0t0',
        '--assign_oetf',
        'srgb',
      ],
    };
  }
  return {
    codec: 'etc1s',
    bpp: 0.5,
    args: [
      '--t2',
      '--encode',
      'etc1s',
      '--clevel',
      '3',
      '--qlevel',
      '255',
      '--genmipmap',
      '--upper_left_maps_to_s0t0',
      '--assign_oetf',
      'srgb',
    ],
  };
}

function collectPreservedRefs(doc) {
  const images = new Set();
  const accessors = new Set();
  const walkNode = (nodeIdx) => {
    const node = doc.nodes?.[nodeIdx];
    if (!node) return;
    if (node.mesh !== undefined) {
      for (const prim of doc.meshes[node.mesh].primitives ?? []) {
        if (prim.indices !== undefined) accessors.add(prim.indices);
        for (const accIdx of Object.values(prim.attributes ?? {})) accessors.add(accIdx);
        if (prim.material !== undefined) {
          const walkMat = (obj) => {
            for (const [k, v] of Object.entries(obj ?? {})) {
              if (!v || typeof v !== 'object') continue;
              if (k.endsWith('Texture') && v.index !== undefined) {
                const tex = doc.textures?.[v.index];
                const src =
                  tex?.source ??
                  tex?.extensions?.EXT_texture_webp?.source ??
                  tex?.extensions?.KHR_texture_basisu?.source;
                if (src !== undefined) images.add(src);
              } else {
                walkMat(v);
              }
            }
          };
          walkMat(doc.materials[prim.material]);
        }
      }
    }
    for (const childIdx of node.children ?? []) walkNode(childIdx);
  };
  for (const rootIdx of doc.scenes?.[doc.scene ?? 0]?.nodes ?? []) {
    const node = doc.nodes?.[rootIdx];
    if (PRESERVE_CASTING_ITEMS.has(node?.extras?.cabinetItem)) {
      walkNode(rootIdx);
    }
  }
  return { images, accessors };
}

async function optimizeGlb(fileName, toktx, tempDir, { dryRun = false } = {}) {
  const fullPath = join(modelsDir, fileName);
  const origBytes = readFileSync(fullPath);
  const origGz = gzipSync(origBytes, { level: 9 }).length;
  const { doc, data } = readProduct(origBytes);

  const chunks = [Buffer.from(data)];
  let binOffset = data.length;
  const appendChunk = (bytes) => {
    const start = binOffset;
    const pad = (4 - (bytes.length % 4)) % 4;
    chunks.push(Buffer.from(bytes), Buffer.alloc(pad));
    binOffset += bytes.length + pad;
    return start;
  };

  let vboBeforeBytes = 0;
  let vboAfterBytes = 0;
  let quantizedNormals = 0;
  let quantizedUvs = 0;
  let quantizedColors = 0;
  let newlyMeshoptedViews = 0;

  // Classify how every accessor is used across meshes & instancing.
  const accessorRoles = new Map();
  const addAccRole = (idx, role) => {
    if (idx === undefined) return;
    if (!accessorRoles.has(idx)) accessorRoles.set(idx, new Set());
    accessorRoles.get(idx).add(role);
  };
  for (const node of doc.nodes ?? []) {
    const inst = node.extensions?.EXT_mesh_gpu_instancing?.attributes;
    if (inst) {
      for (const idx of Object.values(inst)) addAccRole(idx, 'INSTANCING');
    }
  }
  for (const mesh of doc.meshes ?? []) {
    for (const prim of mesh.primitives ?? []) {
      if (prim.indices !== undefined) {
        const mode = prim.mode ?? 4;
        addAccRole(prim.indices, mode === 4 ? 'TRIANGLES' : 'INDICES');
      }
      for (const [sem, idx] of Object.entries(prim.attributes ?? {})) {
        addAccRole(idx, sem);
      }
    }
  }

  // Count how many accessors share each bufferView.
  const viewUsers = new Map();
  for (const [idx, acc] of (doc.accessors ?? []).entries()) {
    if (acc.bufferView === undefined) continue;
    if (!viewUsers.has(acc.bufferView)) viewUsers.set(acc.bufferView, []);
    viewUsers.get(acc.bufferView).push(idx);
  }

  const addCompressedAccessorView = (rawBytes, count, byteStride, mode, filter, target) => {
    const encoded = MeshoptEncoder.encodeGltfBuffer(rawBytes, count, byteStride, mode, 0);
    const start = appendChunk(encoded);
    const stream = {
      buffer: 0,
      byteOffset: start,
      byteLength: encoded.length,
      count,
      byteStride,
      mode,
    };
    if (filter && filter !== 'NONE') stream.filter = filter;
    const view = {
      buffer: 1,
      byteLength: count * byteStride,
      extensions: { EXT_meshopt_compression: stream },
    };
    if (mode === 'ATTRIBUTES') view.byteStride = byteStride;
    if (target) view.target = target;
    return doc.bufferViews.push(view) - 1;
  };

  const preserved = collectPreservedRefs(doc);

  for (const [accIdx, acc] of (doc.accessors ?? []).entries()) {
    if (acc.bufferView === undefined || acc.sparse) continue;
    const roles = accessorRoles.get(accIdx);
    if (!roles || roles.has('INSTANCING')) continue;

    const view = doc.bufferViews[acc.bufferView];
    const origElemBytes = COMPONENT_BYTE_SIZE[acc.componentType] * TYPE_COMPONENTS[acc.type];
    const origStride = view.byteStride ?? origElemBytes;
    vboBeforeBytes += acc.count * origStride;

    if (preserved.accessors.has(accIdx)) {
      vboAfterBytes += acc.count * origStride;
      continue;
    }

    // 1. Quantize Float32 NORMAL -> Int8 normalized OCTAHEDRAL (12B -> 4B/vert)
    if (
      roles.size === 1 &&
      roles.has('NORMAL') &&
      acc.componentType === 5126 &&
      acc.type === 'VEC3'
    ) {
      const floats = readAccessorValues(doc, data, accIdx);
      const padded = new Float32Array(acc.count * 4);
      for (let i = 0; i < acc.count; i++) {
        padded[i * 4] = floats[i * 3];
        padded[i * 4 + 1] = floats[i * 3 + 1];
        padded[i * 4 + 2] = floats[i * 3 + 2];
        padded[i * 4 + 3] = 0;
      }
      const oct = MeshoptEncoder.encodeFilterOct(padded, acc.count, 4, 8);
      acc.bufferView = addCompressedAccessorView(
        oct,
        acc.count,
        4,
        'ATTRIBUTES',
        'OCTAHEDRAL',
        34962,
      );
      acc.componentType = 5120;
      acc.normalized = true;
      delete acc.byteOffset;
      delete acc.min;
      delete acc.max;
      quantizedNormals++;
      vboAfterBytes += acc.count * 4;
      continue;
    }

    // 2. Quantize Float32 TEXCOORD_* in [0, 1] -> Uint16 normalized (8B -> 4B/vert)
    if (
      roles.size === 1 &&
      [...roles][0].startsWith('TEXCOORD_') &&
      acc.componentType === 5126 &&
      acc.type === 'VEC2'
    ) {
      const floats = readAccessorValues(doc, data, accIdx);
      let inUnitRange = true;
      for (let i = 0; i < floats.length; i++) {
        const v = floats[i];
        if (!Number.isFinite(v) || v < 0 || v > 1) {
          inUnitRange = false;
          break;
        }
      }
      if (inUnitRange) {
        const u16 = new Uint16Array(acc.count * 2);
        for (let i = 0; i < floats.length; i++) {
          u16[i] = Math.round(floats[i] * 65535);
        }
        acc.bufferView = addCompressedAccessorView(
          new Uint8Array(u16.buffer),
          acc.count,
          4,
          'ATTRIBUTES',
          'NONE',
          34962,
        );
        acc.componentType = 5123;
        acc.normalized = true;
        delete acc.byteOffset;
        delete acc.min;
        delete acc.max;
        quantizedUvs++;
        vboAfterBytes += acc.count * 4;
        continue;
      }
    }

    // 3. Quantize Float32 COLOR_0 in [0, 1] -> Uint8 normalized (12-16B -> 4B/vert)
    if (
      roles.size === 1 &&
      roles.has('COLOR_0') &&
      acc.componentType === 5126 &&
      (acc.type === 'VEC3' || acc.type === 'VEC4')
    ) {
      const floats = readAccessorValues(doc, data, accIdx);
      let inUnitRange = true;
      for (let i = 0; i < floats.length; i++) {
        const v = floats[i];
        if (!Number.isFinite(v) || v < 0 || v > 1) {
          inUnitRange = false;
          break;
        }
      }
      if (inUnitRange) {
        const comps = TYPE_COMPONENTS[acc.type];
        const u8 = new Uint8Array(acc.count * 4);
        for (let i = 0; i < acc.count; i++) {
          for (let c = 0; c < comps; c++) {
            u8[i * 4 + c] = Math.round(floats[i * comps + c] * 255);
          }
          if (comps === 3) u8[i * 4 + 3] = 255;
        }
        acc.bufferView = addCompressedAccessorView(u8, acc.count, 4, 'ATTRIBUTES', 'NONE', 34962);
        acc.componentType = 5121;
        acc.normalized = true;
        delete acc.byteOffset;
        delete acc.min;
        delete acc.max;
        quantizedColors++;
        vboAfterBytes += acc.count * 4;
        continue;
      }
    }

    // 4. Losslessly compress any remaining uncompressed geometry accessor (POSITION, UVs outside [0,1], indices)
    if (!view.extensions?.EXT_meshopt_compression) {
      const values = readAccessorValues(doc, data, accIdx);
      const isIndex = roles.has('TRIANGLES') || roles.has('INDICES');
      const mode = isIndex
        ? roles.has('TRIANGLES') && acc.count % 3 === 0
          ? 'TRIANGLES'
          : 'INDICES'
        : 'ATTRIBUTES';
      const byteStride = COMPONENT_BYTE_SIZE[acc.componentType] * TYPE_COMPONENTS[acc.type];
      if (!isIndex && byteStride % 4 === 0) {
        const rawBytes = new Uint8Array(values.buffer, values.byteOffset, values.byteLength);
        const encoded = MeshoptEncoder.encodeGltfBuffer(rawBytes, acc.count, byteStride, mode, 0);
        const check = new Uint8Array(rawBytes.length);
        MeshoptDecoder.decodeGltfBuffer(check, acc.count, byteStride, encoded, mode, 'NONE');
        if (Buffer.from(rawBytes).equals(Buffer.from(check)) && encoded.length < rawBytes.length) {
          acc.bufferView = addCompressedAccessorView(
            rawBytes,
            acc.count,
            byteStride,
            mode,
            'NONE',
            34962,
          );
          delete acc.byteOffset;
          newlyMeshoptedViews++;
        }
      } else if (isIndex && (byteStride === 2 || byteStride === 4)) {
        const rawBytes = new Uint8Array(values.buffer, values.byteOffset, values.byteLength);
        const encoded = MeshoptEncoder.encodeGltfBuffer(rawBytes, acc.count, byteStride, mode, 0);
        const check = new Uint8Array(rawBytes.length);
        MeshoptDecoder.decodeGltfBuffer(check, acc.count, byteStride, encoded, mode, 'NONE');
        if (Buffer.from(rawBytes).equals(Buffer.from(check)) && encoded.length < rawBytes.length) {
          acc.bufferView = addCompressedAccessorView(
            rawBytes,
            acc.count,
            byteStride,
            mode,
            'NONE',
            34963,
          );
          delete acc.byteOffset;
          newlyMeshoptedViews++;
        }
      }
    }

    vboAfterBytes += acc.count * origStride;
  }

  // 5. Embedded images -> KHR_texture_basisu (KTX2)
  const imageRoles = collectImageRoles(doc);
  const rawImageInputs = [];
  const glbTempDir = join(tempDir, fileName.replace(/[^a-z0-9.-]/gi, '_'));
  const imgStats = { total: 0, converted: 0, skipped: 0, rgbaVram: 0, ktx2Vram: 0 };

  if ((doc.images?.length ?? 0) > 0) {
    mkdirSync(glbTempDir, { recursive: true });
    for (const [imgIdx, img] of doc.images.entries()) {
      imgStats.total++;
      if (img.mimeType === 'image/ktx2' || preserved.images.has(imgIdx)) {
        imgStats.skipped++;
        continue;
      }
      if (img.bufferView === undefined) {
        imgStats.skipped++;
        continue;
      }
      const bv = doc.bufferViews[img.bufferView];
      const start = bv.byteOffset ?? 0;
      const raw = data.subarray(start, start + bv.byteLength);
      const ext =
        img.mimeType === 'image/png' ? '.png' : img.mimeType === 'image/webp' ? '.webp' : '.jpg';
      const rawPath = join(glbTempDir, `img_${imgIdx}${ext}`);
      writeFileSync(rawPath, raw);
      rawImageInputs.push({ id: `img_${imgIdx}`, imgIdx, rawPath });
    }
  }

  const metaMap = prepareImagesWithPillow(rawImageInputs, glbTempDir);
  const encodeTasks = [];
  const convertedImages = new Map();

  for (const input of rawImageInputs) {
    const meta = metaMap.get(input.id);
    const roles = imageRoles.get(input.imgIdx) ?? new Set(['baseColor']);
    const origVram = mipVramBytes(meta.origW, meta.origH, 4);
    imgStats.rgbaVram += origVram;

    if (meta.origW * meta.origH < MIN_KTX2_PIXELS) {
      imgStats.skipped++;
      imgStats.ktx2Vram += origVram;
      continue;
    }

    const plan = toktxArgsForGlbImage(fileName, roles, meta.hasAlpha, meta.targetW, meta.targetH);
    if (!plan) {
      imgStats.skipped++;
      imgStats.ktx2Vram += origVram;
      continue;
    }

    imgStats.ktx2Vram += mipVramBytes(meta.targetW, meta.targetH, plan.bpp);
    const ktx2Path = join(glbTempDir, `${input.id}.ktx2`);
    encodeTasks.push(async () => {
      if (!dryRun) {
        await execFileAsync(toktx, [...plan.args, ktx2Path, meta.pngPath]);
        convertedImages.set(input.imgIdx, readFileSync(ktx2Path));
      } else {
        convertedImages.set(input.imgIdx, Buffer.alloc(0));
      }
    });
  }

  await runPool(encodeTasks, 6);

  if (!dryRun && convertedImages.size > 0) {
    for (const [imgIdx, ktx2Bytes] of convertedImages.entries()) {
      const start = appendChunk(ktx2Bytes);
      const newViewIdx =
        doc.bufferViews.push({
          buffer: 0,
          byteOffset: start,
          byteLength: ktx2Bytes.length,
        }) - 1;
      doc.images[imgIdx].bufferView = newViewIdx;
      doc.images[imgIdx].mimeType = 'image/ktx2';
      imgStats.converted++;
    }

    for (const tex of doc.textures ?? []) {
      const src =
        tex.source ??
        tex.extensions?.EXT_texture_webp?.source ??
        tex.extensions?.KHR_texture_basisu?.source;
      if (src !== undefined && convertedImages.has(src)) {
        delete tex.source;
        if (tex.extensions) {
          delete tex.extensions.EXT_texture_webp;
        }
        (tex.extensions ??= {}).KHR_texture_basisu = { source: src };
      }
    }
  } else if (dryRun) {
    imgStats.converted = convertedImages.size;
  }

  // Recompute extensionsUsed and extensionsRequired accurately.
  const used = new Set(doc.extensionsUsed ?? []);
  const required = new Set(doc.extensionsRequired ?? []);

  const hasWebp = (doc.textures ?? []).some((t) => t.extensions?.EXT_texture_webp);
  if (!hasWebp) {
    used.delete('EXT_texture_webp');
    required.delete('EXT_texture_webp');
  }
  const hasBasisu = (doc.textures ?? []).some((t) => t.extensions?.KHR_texture_basisu);
  if (hasBasisu) {
    used.add('KHR_texture_basisu');
    required.add('KHR_texture_basisu');
  }
  const hasQuantized = (doc.accessors ?? []).some((acc, idx) => {
    const roles = accessorRoles.get(idx);
    if (!roles || roles.has('TRIANGLES') || roles.has('INDICES') || roles.has('INSTANCING'))
      return false;
    return [5120, 5121, 5122, 5123].includes(acc.componentType);
  });
  if (hasQuantized) {
    used.add('KHR_mesh_quantization');
    required.add('KHR_mesh_quantization');
  }
  const hasMeshopt = (doc.bufferViews ?? []).some((bv) => bv.extensions?.EXT_meshopt_compression);
  if (hasMeshopt) {
    used.add('EXT_meshopt_compression');
    required.add('EXT_meshopt_compression');
  }

  if (used.size > 0) doc.extensionsUsed = [...used].sort();
  else delete doc.extensionsUsed;
  if (required.size > 0) doc.extensionsRequired = [...required].sort();
  else delete doc.extensionsRequired;

  let outBytes = origBytes;
  let outGz = origGz;
  if (!dryRun) {
    const product = { doc, data: Buffer.concat(chunks) };
    const sceneNodes = doc.scenes[doc.scene ?? 0].nodes;
    outBytes = assembleProducts(
      [product],
      sceneNodes.map((nodeIdx) => [product, nodeIdx]),
    );
    writeFileSync(fullPath, outBytes);
    outGz = gzipSync(outBytes, { level: 9 }).length;
  }

  return {
    fileName,
    origLen: origBytes.length,
    outLen: outBytes.length,
    origGz,
    outGz,
    vboBeforeBytes,
    vboAfterBytes,
    quantizedNormals,
    quantizedUvs,
    quantizedColors,
    newlyMeshoptedViews,
    imgStats,
  };
}

function fmtKB(bytes) {
  return `${(bytes / 1024).toFixed(0)} KB`;
}

function fmtMB(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const filterIdx = args.indexOf('--filter');
  const filter = filterIdx >= 0 ? args[filterIdx + 1] : undefined;

  const toktx = locateToktx();
  await Promise.all([MeshoptDecoder.ready, MeshoptEncoder.ready]);

  const files = readdirSync(modelsDir, { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.glb'))
    .map((entry) => relative(modelsDir, join(entry.parentPath, entry.name)).replaceAll('\\', '/'))
    .filter((rel) => !filter || rel.includes(filter))
    .sort();

  console.log(`Using toktx: ${toktx}`);
  console.log(`Processing ${files.length} GLBs${dryRun ? ' (dry run)' : ''}...\n`);

  const tempDir = mkdtempSync(join(tmpdir(), 'felix-glb-opt-'));
  try {
    const rows = [];
    for (const fileName of files) {
      rows.push(await optimizeGlb(fileName, toktx, tempDir, { dryRun }));
    }

    let totOrig = 0;
    let totOut = 0;
    let totOrigGz = 0;
    let totOutGz = 0;
    let totVboBefore = 0;
    let totVboAfter = 0;
    let totImgBefore = 0;
    let totImgAfter = 0;
    let totImgConverted = 0;
    let totImgSkipped = 0;
    let totNorms = 0;
    let totUvs = 0;
    let totColors = 0;

    console.log(
      'GLB'.padEnd(32) +
        'Disk'.padStart(18) +
        'Gzip'.padStart(18) +
        'Imgs'.padStart(9) +
        'Tex VRAM'.padStart(19) +
        'VBO VRAM'.padStart(17),
    );
    console.log('-'.repeat(113));

    for (const r of rows) {
      totOrig += r.origLen;
      totOut += r.outLen;
      totOrigGz += r.origGz;
      totOutGz += r.outGz;
      totVboBefore += r.vboBeforeBytes;
      totVboAfter += r.vboAfterBytes;
      totImgBefore += r.imgStats.rgbaVram;
      totImgAfter += r.imgStats.ktx2Vram;
      totImgConverted += r.imgStats.converted;
      totImgSkipped += r.imgStats.skipped;
      totNorms += r.quantizedNormals;
      totUvs += r.quantizedUvs;
      totColors += r.quantizedColors;

      console.log(
        r.fileName.padEnd(32) +
          `${fmtKB(r.origLen)}->${fmtKB(r.outLen)}`.padStart(18) +
          `${fmtKB(r.origGz)}->${fmtKB(r.outGz)}`.padStart(18) +
          `${r.imgStats.converted}/${r.imgStats.total}`.padStart(9) +
          `${fmtMB(r.imgStats.rgbaVram)}->${fmtMB(r.imgStats.ktx2Vram)}`.padStart(19) +
          `${fmtKB(r.vboBeforeBytes)}->${fmtKB(r.vboAfterBytes)}`.padStart(17),
      );
    }

    console.log('-'.repeat(113));
    console.log(
      `TOTAL (${rows.length} GLBs)`.padEnd(32) +
        `${fmtMB(totOrig)}->${fmtMB(totOut)}`.padStart(18) +
        `${fmtMB(totOrigGz)}->${fmtMB(totOutGz)}`.padStart(18) +
        `${totImgConverted}/${totImgConverted + totImgSkipped}`.padStart(9) +
        `${fmtMB(totImgBefore)}->${fmtMB(totImgAfter)}`.padStart(19) +
        `${fmtMB(totVboBefore)}->${fmtMB(totVboAfter)}`.padStart(17),
    );
    console.log(
      `\nQuantized accessors: ${totNorms} NORMAL (Int8 oct), ${totUvs} TEXCOORD (Uint16 norm), ${totColors} COLOR (Uint8 norm)`,
    );
    console.log(
      `GPU Texture VRAM savings: ${fmtMB(totImgBefore - totImgAfter)} (-${(((totImgBefore - totImgAfter) / Math.max(1, totImgBefore)) * 100).toFixed(1)}%)`,
    );
    console.log(
      `GPU Vertex Buffer VRAM savings: ${fmtMB(totVboBefore - totVboAfter)} (-${(((totVboBefore - totVboAfter) / Math.max(1, totVboBefore)) * 100).toFixed(1)}%)`,
    );
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
