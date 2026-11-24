/**
 * Offline PMREM prefilter baker for Felix Studio.
 *
 * Runs Three.js's own PMREMGenerator on public/media/lighting/desk-{day,night}.hdr
 * inside headless Chrome, reads back every GGX-filtered cubemap face and mip level,
 * downsamples 2x in linear radiance (matching the 512x256 equirectangular Nyquist
 * frequency of 128 px per 90-degree face while preserving all 6 GGX roughness levels
 * 128..4), encodes planar channel-delta RGBE (PMR2 binary format), and writes
 * gzipped .pmrem.gz files so runtime startup skips PMREMGenerator shader compilation
 * and GPU blur passes.
 */
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { execSync, spawn } from 'node:child_process';
import { gzipSync } from 'node:zlib';
import { chromium } from 'playwright';

const PROBES = ['desk-day', 'desk-night'];
const PORT = 4187;

async function startDevServer() {
  const server = spawn(
    process.execPath,
    [
      resolve('node_modules/vite/bin/vite.js'),
      '--host',
      '127.0.0.1',
      '--port',
      String(PORT),
      '--strictPort',
    ],
    { stdio: 'pipe' },
  );
  await new Promise((res, rej) => {
    const timer = setTimeout(() => rej(new Error('Vite dev server timed out')), 20000);
    server.stdout.on('data', (chunk) => {
      if (String(chunk).includes(String(PORT))) {
        clearTimeout(timer);
        res();
      }
    });
    server.on('exit', (code) => {
      clearTimeout(timer);
      rej(new Error(`Vite exited early with code ${code}`));
    });
  });
  return server;
}

function stopServer(server) {
  try {
    if (process.platform === 'win32' && server.pid) {
      execSync(`taskkill /PID ${server.pid} /T /F`, { stdio: 'ignore' });
    } else {
      server.kill('SIGTERM');
    }
  } catch {
    // Already exited.
  }
}

async function main() {
  const server = await startDevServer();
  const browser = await chromium.launch({
    headless: true,
    channel: 'chrome',
    args: ['--use-angle=d3d11', '--enable-gpu'],
  });
  try {
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:${PORT}/robots.txt`);

    for (const name of PROBES) {
      const encoded = await page.evaluate(async (probeName) => {
        const T = await import('/node_modules/three/build/three.module.js');
        const { HDRLoader } = await import('/node_modules/three/examples/jsm/loaders/HDRLoader.js');
        const canvas = document.createElement('canvas');
        const renderer = new T.WebGLRenderer({ canvas, antialias: false });
        const gl = renderer.getContext();
        gl.getExtension('EXT_color_buffer_float');
        gl.getExtension('EXT_color_buffer_half_float');

        const hdr = await new HDRLoader().loadAsync(`/media/lighting/${probeName}.hdr`);
        const generator = new T.PMREMGenerator(renderer);
        const rt = generator.fromEquirectangular(hdr);
        hdr.dispose();

        const baseSize = rt.width;
        const mipCount = rt.texture.mipmaps.length;
        const outBase = baseSize >= 256 ? baseSize >> 1 : baseSize;
        const downsample = outBase !== baseSize;

        const props = renderer.properties.get(rt.texture);
        const glTex = props.__webglTexture;
        const fbo = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);

        let totalPixels = 0;
        for (let m = 0; m < mipCount; m++) {
          const d = Math.max(1, outBase >> m);
          totalPixels += 6 * d * d;
        }
        const out = new Uint8Array(12 + totalPixels * 4);
        const view = new DataView(out.buffer);
        out[0] = 0x50; // P
        out[1] = 0x4d; // M
        out[2] = 0x52; // R
        out[3] = 0x32; // 2 (planar + horizontal delta RGBE)
        view.setUint16(4, outBase, true);
        view.setUint16(6, mipCount, true);
        view.setUint32(8, 0, true);

        let offset = 12;
        for (let m = 0; m < mipCount; m++) {
          const sDim = Math.max(1, baseSize >> m);
          const dDim = Math.max(1, outBase >> m);
          const halfBuf = new Uint16Array(sDim * sDim * 4);
          for (let face = 0; face < 6; face++) {
            gl.framebufferTexture2D(
              gl.FRAMEBUFFER,
              gl.COLOR_ATTACHMENT0,
              gl.TEXTURE_CUBE_MAP_POSITIVE_X + face,
              glTex,
              m,
            );
            const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
            if (status !== gl.FRAMEBUFFER_COMPLETE) {
              throw new Error(
                `Incomplete FBO for ${probeName} lod=${m} face=${face}: 0x${status.toString(16)}`,
              );
            }
            gl.readPixels(0, 0, sDim, sDim, gl.RGBA, gl.HALF_FLOAT, halfBuf);
            const rgbe = new Uint8Array(dDim * dDim * 4);
            for (let y = 0; y < dDim; y++) {
              for (let x = 0; x < dDim; x++) {
                let r = 0;
                let g = 0;
                let b = 0;
                if (downsample && sDim >= 2) {
                  for (let dy = 0; dy < 2; dy++) {
                    for (let dx = 0; dx < 2; dx++) {
                      const si = ((y * 2 + dy) * sDim + (x * 2 + dx)) * 4;
                      r += Math.max(0, T.DataUtils.fromHalfFloat(halfBuf[si]));
                      g += Math.max(0, T.DataUtils.fromHalfFloat(halfBuf[si + 1]));
                      b += Math.max(0, T.DataUtils.fromHalfFloat(halfBuf[si + 2]));
                    }
                  }
                  r *= 0.25;
                  g *= 0.25;
                  b *= 0.25;
                } else {
                  const si = (y * sDim + x) * 4;
                  r = Math.max(0, T.DataUtils.fromHalfFloat(halfBuf[si]));
                  g = Math.max(0, T.DataUtils.fromHalfFloat(halfBuf[si + 1]));
                  b = Math.max(0, T.DataUtils.fromHalfFloat(halfBuf[si + 2]));
                }
                const maxVal = Math.max(r, g, b);
                const di = (y * dDim + x) * 4;
                if (maxVal >= 1e-32) {
                  const exp = Math.floor(Math.log2(maxVal)) + 1;
                  const scale = Math.pow(2, -exp) * 256.0;
                  rgbe[di] = Math.min(255, Math.max(0, Math.floor(r * scale)));
                  rgbe[di + 1] = Math.min(255, Math.max(0, Math.floor(g * scale)));
                  rgbe[di + 2] = Math.min(255, Math.max(0, Math.floor(b * scale)));
                  rgbe[di + 3] = Math.min(255, Math.max(0, exp + 128));
                }
              }
            }
            const n = dDim * dDim;
            for (let c = 0; c < 4; c++) {
              let prev = 0;
              for (let p = 0; p < n; p++) {
                const v = rgbe[p * 4 + c];
                out[offset++] = (v - prev) & 0xff;
                prev = v;
              }
            }
          }
        }
        gl.deleteFramebuffer(fbo);
        rt.dispose();
        generator.dispose();
        renderer.dispose();
        return { baseSize: outBase, mipCount, bytes: Array.from(out) };
      }, name);

      const raw = Buffer.from(encoded.bytes);
      const gz = gzipSync(raw, { level: 9 });
      const outPath = resolve(`public/media/lighting/${name}.pmrem.gz`);
      writeFileSync(outPath, gz);
      console.log(
        `${name}.pmrem.gz: base=${encoded.baseSize}, mips=${encoded.mipCount}, raw=${(raw.length / 1024).toFixed(1)} KB, gz=${(gz.length / 1024).toFixed(1)} KB`,
      );
    }
  } finally {
    await browser.close();
    stopServer(server);
  }
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
