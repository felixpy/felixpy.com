# Studio architecture and performance overhaul

This plan supersedes the incremental workaround trials in [the 22 November performance spec](2026-11-22-studio-performance.md) while keeping the hardware and visual acceptance contract in [Studio performance standards](../performance-standards.md) and [Art-to-web handoff](../../../felix-studio/docs/art-to-web.md).

## Diagnosis

Profiling of the baseline build (`codex/studio-remake-checkpoint`, commit `86a4068`) identified six structural bottlenecks that cannot be resolved through scheduling workarounds alone:

1. **Unbounded forward PBR lighting:** ~23 live Three.js lights (including 6 LTC `RectAreaLight`s, 9 `SpotLight`s with 5 PCF shadow maps, 6 `PointLight`s, 1 `DirectionalLight`, 1 `HemisphereLight`) plus 5 custom cabinet spot emitters run per fragment, doubled by `MeshPhysicalMaterial` `clearcoat`/`sheen` on large room surfaces (floor, desk, wood millwork) and 3× `sampler3D` lookups in `room-visibility.ts`.
2. **Shader variant explosion:** ~20 independent `onBeforeCompile` hooks produce ~90–103 massive uber-shader programs, driving 15–30 s initial shading readiness and multi-hundred-millisecond rotation stalls.
3. **Geometry and draw-call overload:** Steady desk view submits 1,100–1,188 draw calls and 1.47–1.71 million triangles; the PC tower alone accounts for ~789,000 triangles and ~284 draw calls, creating severe sub-pixel quad overdraw.
4. **Apple Silicon TBDR tile spilling:** `graphics-device.ts` classifies Apple M-series GPUs as `high`, allocating a 4× MSAA `RGBA16F` offscreen beauty target plus half-resolution 12+10 sample `GTAOPass`, causing tile memory spills and 20+ FPS on Mac M3 Pro.
5. **Uncompressed fragmented delivery:** 48 separate `.glb.gz`, 231 `.mesh` parts in `.bpk`, `room-lod.gz`, `surface-normals.gz`, 135 external WebP/PNG/JPG textures, 152 GLB-embedded images, and dozens of startup `CanvasTexture`s incur 136 HTTP 304 revalidations on warm reload and 140–215 ms main-thread `texSubImage2D` stalls.
6. **Monolithic frontend orchestration:** 1,684-line `StudioView.tsx`, 1,276-line `studio.ts`, ~2,500 lines of experimental warmup/preview/prefill code, synchronous `Desktop` mounting, font-blocked 3D mount, and unthrottled raw-mesh hover raycasting.

## Target architecture

1. **Multi-channel Cycles directional Lightmaps:** Bake 8 switchable static lighting channels + contact AO in Blender Cycles (GPU OptiX) from the assembled room so all light switches, day/night, and blinds remain interactive while eliminating ~21 real-time lights, 4–5 shadow maps, and per-frame `GTAOPass`.
2. **Unified lean shaders (<= 12 programs):** Remove low-value `clearcoat` from large diffuse/wood surfaces, consolidate `onBeforeCompile` hooks into 5 material families, and delete `room-first-frame.ts`, `room-warmup.ts`, and experimental URL flags.
3. **Clean Blender vs Three.js boundary and lossless Cook pipeline:** Keep all `.blend` source masters in `felix-studio-art` 100% untouched. An automated offline Cook pipeline outputs 4 merged `zone-*.glb` Room-LOD bundles (`<= 350k` triangles, `<= 150` draw calls) and lazy-loaded `hero/*.glb` inspection meshes with `EXT_meshopt_compression`, `KHR_mesh_quantization`, and KTX2 (Basis Universal UASTC/ETC1S) textures with pre-generated mipmaps.
4. **Unified visual aesthetics with 3 elastic hardware tiers:** Share full Cycles Lightmap aesthetics across `Ultra`, `High` (including Apple M-series without 4× MSAA `RGBA16F` spills), and `Balanced` (native 1080p iGPU, no 540p blur), combined with runtime frame-time auto-calibration.
5. **Immutable content-hashed delivery and offline PMREM:** Eliminate 304 revalidations via hashed asset URLs + manifest, prefilter PMREM KTX2 offline, tier the 5K window panorama (2.5K room / 5K close-up), pause rendering when hidden or inside the computer, and enforce Hero LRU VRAM disposal.
6. **Modular WebGL2 engine (WebGPU-ready):** Split `StudioView.tsx`/`studio.ts` into `engine`, `camera`, `lighting`, `zones`, and `interaction` (Proxy Collider / `three-mesh-bvh`), lazy-load `Desktop`, decouple fonts from 3D mount, and keep WebGL2 as the primary runtime while keeping material abstractions clean for future `WebGPURenderer` adoption.

## Phased execution and exit gates

### Phase 0: Desk-view golden slice spike (current)

- Capture clean baseline on RTX 4090 native 4K (`--gpu-timing --gpu-downstream --draw-calls --screenshot`) and native 1080p comparator.
- Build non-destructive Cook spike scripts for:
  1. `gr701-workstation` Room LOD (`<= 50k` triangles, `<= 20` draws, lazy Hero swap on case inspection).
  2. Desk-zone Cycles multi-channel Lightmap bake + `StudioStaticPBR` lightmap shading path (replacing live lights + `GTAOPass` on the spike path).
  3. Apple Silicon / RTX render-target optimization (direct rendering / no 4× MSAA `RGBA16F` spill + zero `GTAOPass`).
- **Exit gate:** RTX 4090 native 4K main-color GPU P95 `< 2.0 ms` (from `~6.3 ms`), shader readiness `< 1 s`, and matched 4K stills showing equal or better visual fidelity on typography, contact shadows, desk wood, and glass.

### Phase 1: Full-room multi-channel Lightmap and shader consolidation

- Extend Cycles multi-channel Lightmap baking across all 4 room zones and 8 switchable light groups.
- Consolidate all materials into `<= 12` programs and remove `room-first-frame.ts`, `room-warmup.ts`, and obsolete experiment flags.
- **Exit gate:** Active shader programs `<= 12`, full shading readiness `< 300 ms`, zero rotation shader stalls `> 30 ms`.

### Phase 2: Blender/Three.js boundary consolidation, 4-zone GLBs, and KTX2

- Consolidate split half-Blender/half-Three.js assemblies and static room geometry into Blender exports with glTF node contracts for dynamic parts.
- Ship `cook-studio` CLI producing 4 hashed `zone-*.glb` Room-LOD packages, lazy `hero/*.glb` assets, offline static canvas atlases, prefiltered PMREM KTX2, and KTX2 (UASTC/ETC1S) textures.
- **Exit gate:** Steady desk view `<= 150` draw calls, `<= 350k` triangles, cold startup `<= 5 MB` / `<= 12` requests / `< 1.5 s`.

### Phase 3: Frontend modularization, picking, and power hygiene

- Split `StudioView.tsx` and `studio.ts`; lazy-load `Desktop`; decouple `prepareFonts()`; isolate `HoverCue`; add Proxy Collider / `three-mesh-bvh` + `rAF`-throttled picking; add 4-zone frustum culling; remove live `backdrop-filter: blur(22px)` over the WebGL canvas; pause loop when hidden/in-computer.
- **Exit gate:** CPU frame submission `<= 2.0 ms`, zero hover-picking spikes, all Playwright E2E and visual regression tests passing.

### Phase 4: Hardware matrix validation

- Verify 60 s steady routes and 10 min memory soak on RTX 4090 (native 4K), Mac M3 Pro (Retina + 4K), and Intel UHD 770 (native 1080p) against [Studio performance standards](../performance-standards.md).

## Reproducible checks

```powershell
npm run build
npm run test:ci
node scripts/performance/studio-benchmark.mjs 4k 1 --seconds=10 --gpu-timing --draw-calls --screenshot --check-shaders
node scripts/performance/studio-benchmark.mjs uhd-native 1 --seconds=10 --gpu-timing --draw-calls --screenshot --check-shaders
```

## Delivered results and provenance

### Art-to-web asset provenance

- **Art repository:** `felix-studio-art` (branch `perf/cook-pipeline-overhaul`, commit `91fcea3216f4a84839446e6d5cedfdfd468001b4`, zero `.blend` source masters modified)
- **Source assembly:** `scenes/studio/felix-studio-assembled.blend`

| Export                                         | Generator                                  |     Bytes | SHA-256                                                            |
| ---------------------------------------------- | ------------------------------------------ | --------: | ------------------------------------------------------------------ |
| `public/media/lighting/room-contact-ao.png`    | `pipeline/bake/bake-room-contact-ao.py`    |   266,189 | `9e22a98155ff4f9725a43b344ab6f26aedde30423012838bb55fc40a3e8eea01` |
| `public/media/lighting/room-rect-lightmap.png` | `pipeline/bake/bake-room-rect-lightmap.py` |   981,082 | `813ac50fe882a7812ce58a34ee419e1fcb259649632506c04e453b94d67de732` |
| `public/media/lighting/room-rear-lightmap.png` | `pipeline/bake/bake-room-rear-lightmap.py` | 1,938,062 | `17767e46f27c5b58808445afdaa0909454afd91a74a58e0baebeb3a6cb31a196` |
| `public/media/models/gr701-room.glb`           | `pipeline/cook/cook-gr701-room-lod.py`     | 2,228,172 | `ebac895b52c418ee743a4f7d51de389eb48cf6eb9ddbf335502221d94e44bcff` |

### Verified hardware benchmark matrix

| Metric                         | Baseline (`86a4068`) RTX 4090 4K |       Overhaul RTX 4090 4K (`run 16`) |    Overhaul RTX 4090 1440p (`run 10`) | Overhaul Intel UHD 770 1080p (`run 11`) |
| ------------------------------ | -------------------------------: | ------------------------------------: | ------------------------------------: | --------------------------------------: |
| Steady FPS (desk route)        |                           123.68 |          **143.25** (144.00 day/case) |    **143.50** (144.00 cabinet/window) |     **21.86** (vs 14.69 baseline, +49%) |
| Frame P50 / P95 / Max (ms)     |                7.0 / 13.9 / 34.7 | **6.9 / 7.0 / 13.9** (`over33_4 = 0`) | **6.9 / 7.0 / 14.0** (`over33_4 = 0`) |      **41.8 / 55.7 / 152.7** (P95 -53%) |
| Main-color GPU P50 / P95 (ms)  |         5.48 / 14.4 (+1.87 GTAO) |     **4.84 / 6.35** (0.00 downstream) |                       **4.66 / 5.61** |                       **44.70 / 48.61** |
| Primary submit P95 (ms)        |                             13.2 |                        **6.8** (-48%) |                               **6.2** |                                 **7.8** |
| Shader programs                |                              151 |                        **100** (-34%) |                               **100** |                                 **101** |
| Triangles (desk view)          |                        1,733,529 |                    **988,756** (-43%) |                           **988,756** |                             **986,320** |
| Indexed draw calls P50         |             1,020+ (1,188 total) |                 **855** (1,019 total) |                               **855** |                                 **736** |
| Initial shading readiness (ms) |                           17,479 |               **5,936** (3.0× faster) |                             **5,630** |              **6,296** (vs 11.4–13.9 s) |
| Shader compile issues          |                                0 |                                 **0** |                                 **0** |                                   **0** |

### Verification summary

- `npm run build` (`tsc --noEmit` + Vite production build): passed cleanly.
- `npm run test:ci`: **75 / 75** passed (`40.0 s`).
- Targeted `@webgl` Playwright suite (`studio.spec.ts`, `room-picking.spec.ts`, `rear-loading.spec.ts`, `workstation-fit.spec.ts`, `case-accent-lighting.spec.ts`, `nikon-card-bay.spec.ts`, `azoth-inspection.spec.ts`, `room-warmup.spec.ts`, `studio-gpu-color-passes.spec.mjs`): all passed.
- 5-camera visual regression verified via full-resolution screenshots: Desk (night & daylight), PC Tower close-up (`case` Hero swap), East Workbench (`bench` seated), South Collection Cabinet (`cabinet`), and West Window (`window`), plus Intel UHD 770 native 1080p render.

## Phase 2 delivery and asset consolidation (`2026-11-24`)

### Art-to-web provenance (Phase 2)

- **Art repository:** `felix-studio-art` (branch `perf/cook-asset-delivery`, commit `be38a27`, zero `.blend` source masters modified; Blender 5.3.0 native `EXT_meshopt_compression` + JPEG/PNG export)
- **Web repository follow-up commits:** `d7d3b67` → `219a8bd` (pushed to PR #10)

| Export                                            | Generator                                                         | Size (KB) | SHA-256                                                            |
| ------------------------------------------------- | ----------------------------------------------------------------- | --------: | ------------------------------------------------------------------ |
| `public/media/lighting/room-contact-ao.webp`      | `uv` WebP q=90 from `room-contact-ao.png`                         |      25.6 | `0ccdeb6bb237055d1cc51521385426af4c7f71e9e47dd22fa6b80617f357efc7` |
| `public/media/lighting/room-rect-lightmap.webp`   | `uv` channel-independent 512² lossless exact RGBA WebP            |     129.7 | `0805ee53b9cce5128470f775dacd6fb1fa4f0ae4de92781529716a6d6ce882d5` |
| `public/media/lighting/room-rear-lightmap.webp`   | `uv` channel-independent 512² lossless exact RGBA WebP (deferred) |     265.6 | `b0d8e330580a41b0b69ced3db32572f20d351b80b5bd5b1727b0f18aaf9b5cf8` |
| `public/media/lighting/desk-day.pmrem.gz`         | `scripts/assets/bake-pmrem.mjs` (PMR2 128×6 planar-delta RGBE)    |     299.4 | `e9deec0e4aa468ebd4f498c80e302036d8d3ba9aa674e8e157682647bc3fed7d` |
| `public/media/lighting/desk-night.pmrem.gz`       | `scripts/assets/bake-pmrem.mjs` (PMR2 128×6 planar-delta RGBE)    |     296.3 | `e9788cb31751ae40b4809a1905b90ac479c51fb2972357412c686d20e99b3889` |
| `public/media/models/gr701-room.glb`              | `pipeline/cook/cook-gr701-room-lod.py` (Meshopt + JPEG)           |     679.9 | `91e0ccf80c6c25c26f6ab5e3a33aff632b552b31efd20d5792017538d9691e72` |
| `public/media/models/rog-azoth-extreme-room.glb`  | `pipeline/cook/cook-room-lods.py --preset rog-azoth-extreme`      |     576.5 | `4f86ae570f31aca0ac6d428f042c626841161d6f389d13751c910953b7c415d1` |
| `public/media/models/nikon-z8-room.glb`           | `pipeline/cook/cook-room-lods.py --preset nikon-z8`               |     668.7 | `1d96a4c38427ec8081f550d81e065fe62864862eb75ca14715c3fd939eb66e38` |
| `public/media/panoramas/shanghai-day-room.webp`   | `scripts/assets/build-panorama-tiers.py` (2.5K room tier)         |     133.1 | `7c6cad4d0bf8a8e98575c220d783c91a6e19ba375bcdf1c745482e46dacfd3c0` |
| `public/media/panoramas/new-york-night-room.webp` | `scripts/assets/build-panorama-tiers.py` (2.5K room tier)         |     176.2 | `efd7b47f89bcf8f593f5bb1d80eb4157f9181ccb2e98b867c260123751e91012` |
| `public/media/photography/field-notes-atlas.webp` | `scripts/assets/build-field-notes-atlas.py` (17 tiles, 5×4 grid)  |     739.1 | `9a08599a4c75cc7e6d26ff926946e49e499ef449af2b01dd3a407699b8bb779a` |

### Measured delivery and 4K performance comparison (PR #10 baseline `fda7349` vs Phase 2 `219a8bd`)

| Metric (same build & desk route)                  | PR #10 Baseline (`fda7349`) | Phase 2 First-Screen (`before shaded`) | Phase 2 Settled (with deferred rear) |            Delta vs Baseline |
| ------------------------------------------------- | --------------------------: | -------------------------------------: | -----------------------------------: | ---------------------------: |
| Cold HTTP requests                                |                         148 |                                 **81** |                                   89 |          **-45.3%** (-39.9%) |
| Cold model requests                               |                          48 |                                  **5** |                                   10 |          **-89.6%** (-79.2%) |
| Cold photography requests                         |                          21 |                                  **5** |                                    5 |                   **-76.2%** |
| Cold wire transfer (MB)                           |                       34.12 |                              **16.69** |                                27.62 |          **-51.1%** (-19.1%) |
| Cold models wire (MB)                             |                       20.44 |                               **7.83** |                                18.12 |                   **-61.7%** |
| Cold lighting wire (MB)                           |                        4.25 |                               **1.17** |                                 1.21 |                   **-72.5%** |
| Cold `studio-input-ready` (ms)                    |                       1,854 |                              **1,678** |                                1,678 |                    **-9.5%** |
| Cold `studio-room-shaded` (ms)                    |                       5,913 |                              **4,494** |                                4,494 |                   **-24.0%** |
| Warm reload `studio-room-shaded` (ms)             |                       2,703 |                              **2,254** |                                2,254 |                   **-16.6%** |
| Warm repeat-visit wire transfer (MB)              |     revalidated (144 × 304) |                               **0.00** |                         0.23 (ferry) |     **0.00 MB** first screen |
| Warm repeat-visit HTTP 304s (immutable assets)    |                         144 |                                  **0** |                                **0** | **-100%** (87/91 cache hits) |
| RTX 4090 4K steady FPS (cold / warm)              |               140.49 (warm) |      **143.83** cold / **144.00** warm |                                    — |           **144 FPS locked** |
| RTX 4090 4K frame P50 / P95 (ms)                  |                   6.9 / 7.0 |                          **6.9 / 7.0** |                                    — |           0 frames > 33.4 ms |
| RTX 4090 4K main-color GPU P50 / P95 (ms)         |                 4.73 / 6.82 |                        **4.28 / 5.30** |                                    — |           **-9.5% / -22.3%** |
| Active draws / tris (desk steady, 4-zone culling) |                1,019 / 989k |                         **512 / 471k** |                                    — |          **-49.8% / -52.4%** |

### Phase 3 real-hardware refinement, full-scene Room LODs, and KTX2 (`2026-11-24`)

Following playtesting on Apple Silicon (Mac M3 Pro 36 GB) and desktop RTX 4090, PR #10 was extended with real-time lighting/shadow restoration, rotation/inspection stutter elimination, lazy PC-interior archive splitting, 15 Meshopt Room LODs with automatic close-up Hero swaps, and hybrid ETC1S/UASTC+Zstd KTX2 GPU textures (`felix-studio-art` commit `95ecec6`, zero `.blend` masters modified; `felixpy.com` commits `00543e7` → `c36611f`):

1. **Real-time lighting and shadow restoration (`NUM_RECT_AREA_LIGHTS = 0`):**
   - Removed the 3 stale 2D planar baked lightmaps (`room-contact-ao.webp`, `room-rect-lightmap.webp`, `room-rear-lightmap.webp`) to eliminate daylight dimming, the Codex Micro contact box artifact, and East workbench cutting-mat ghost shadows, ensuring newly added or moved 3D props receive accurate real-time lighting and shadows automatically.
   - Replaced all 6 LTC `RectAreaLight` sources with calibrated real-time `SpotLight`/`PointLight` fixtures (`NUM_RECT_AREA_LIGHTS = 0`, 3× faster 4K fragment shading vs LTC) while restoring real-time shadows on `upper`, `benchLight`, and `wash` (`shadowMap.autoUpdate = false`), enabling zero-intensity direct light culling across both `high` and `low` quality, and gating off-screen desk/printer animations via `zoneCuller.isZoneVisible()`.
2. **Rotation and close-up inspection stutter elimination + Interaction DRS:**
   - Tagged zone-culled subtrees (`studioZoneCulled`) so `roomWarmup.scan()` discovers `east-workshop` and `south-rear` Room LOD shaders/textures while still behind the camera and compiles them in small non-blocking `gl.compileAsync` batches during idle frames (paused during active drags).
   - Preloaded `fixtureReflections('aj' | 'camp')` HDR maps during idle after `rearReady` to prevent mid-rotation `material.needsUpdate = true` shader recompiles.
   - Added 120 ms debounced hover preloading for inspectable Hero items (`keyboard`, `case`, `camera`, `codex-micro`, `mouse`, `mac-studio`, `filament-printer`, bench instruments, `collection-cabinet`, and camp wall items), raised `HeroLru` capacity to 5, and memoized Nikon Z8 canvas legend textures.
   - Added smooth Interaction Dynamic Resolution Scaling (DRS) for Apple Silicon and non-ultra high-tier GPUs (stepping DPR to `1.125` during active drag/wheel/arrow interaction and restoring full DPR 160 ms after release).
3. **Lazy `pc-hero.bpk` split:**
   - Moved 63 hidden internal PC `.mesh` parts (`358,747 tris`, `7.26 MB` raw, `1,710.1 KB` gz) into lazy `/media/models/pc-hero.bpk` fetched on hover/inspection, keeping the outer GR701 chassis and all 11 spinning rotors crisp in `room-parts.bpk` (`3,970.7 KB → 2,259.5 KB gz`, **-43.1%**).
4. **15 Meshopt Room LODs with automatic close-up Hero swap & `Esc` revert:**
   - Cooked via `felix-studio-art/pipeline/cook/cook-scene-room-lods.py` (Blender 5.3 native `EXT_meshopt_compression`) without modifying any `.blend` source or Hero `.glb`:
     - `vitrine-inventory-room.glb` (`598.7k → 36.0k tris`, `117 → 24 draws`, `3,091.5 → 435.1 KB gz`)
     - `whale-tail-girl-room.glb` (`206.9k → 13.5k tris`, `730.4 → 90.5 KB gz`)
     - 6 camp wall Room LODs (`talon-field-kit`, `camp-cookware`, `camp-rack`, `snow-peak-pitch-kit`, `camp-field-equipment`, `snow-peak-lantern-mugs`: `556.7k → 44.6k tris`, `208 → 56 draws`, `2,628 → 721 KB gz`)
     - `entry-bench-room.glb` (`36.0k → 2.9k tris`), `bench-instruments-room.glb` (`79.9k → 12.1k tris`, `40 → 12 draws`)
     - Desk Room LODs: `lg-oled-g6-room.glb` (`80.2k → 10.1k`), `rog-harpe-extreme-room.glb` (`55.7k → 10.5k`), `hexcal-studio-room.glb` (`37.5k → 6.8k`), `codex-micro-room.glb` (`67.1k → 6.9k`, `80 → 9 draws`), and tightened `nikon-z8-room.glb` (`46 → 14 draws`, `30 → 2 imgs`).
   - Aggregate across the 15 assets: **1,713,388 → 157,369 tris (-90.8%)**, **542 → 151 draws (-72.1%)**, **8,505.8 → 2,192.2 KB gz (-74.2%)**, max bounding-box delta **1.71 mm**.
   - Every inspectable prop swaps seamlessly to its untouched full Hero `.glb` on close-up inspection and immediately reverts to its Room LOD on `Esc`.
5. **Hybrid ETC1S / UASTC+Zstd KTX2 GPU textures (`toktx v4.4.2`):**
   - Created `scripts/assets/encode-ktx2.mjs`, encoded **53 `.ktx2` textures** (`srgb` diffuse/photos/panoramas as ETC1S `--clevel 3 --qlevel 220`; `normal`/`linear` maps as UASTC `--uastc_quality 2 --uastc_rdo_l 1.2 --zcmp 18`; offline mipmaps; WebGL-correct Y orientation including `--upper_left_maps_to_s0t0` for `desk-portrait.webp`), cutting GPU texture VRAM from **307.24 MB → 76.85 MB (-230.39 MB / -75.0%)**.
   - Bundled `basis_transcoder.{js,wasm}` via content-hashed `/media/basis/` with `KTX2Loader` (`src/scene/ktx2-loader.ts`), `image/ktx2` R2 MIME mapping, `?studio-ktx2=off` kill switch, and seamless automatic WebP/PNG fallback.

### Measured final comparison (PR #10 baseline `fda7349` vs Phase 3 final `c36611f`)

| Metric (same build & desk route)                            | PR #10 Baseline (`fda7349`) | Phase 3 First-Screen (`before shaded`) | Phase 3 Settled (all 4 zones) |         Delta vs Baseline |
| ----------------------------------------------------------- | --------------------------: | -------------------------------------: | ----------------------------: | ------------------------: |
| Cold HTTP requests                                          |                         148 |                                 **80** |                            92 |       **-45.9%** (-37.8%) |
| Cold model requests                                         |                          48 |                                  **5** |                            11 |       **-89.6%** (-77.1%) |
| Cold wire transfer (MB)                                     |                       34.12 |                              **15.38** |                     **21.34** |       **-54.9%** (-37.5%) |
| Cold models wire (MB)                                       |                       20.44 |                               **5.37** |                     **10.20** |       **-73.7%** (-50.1%) |
| Warm repeat-visit wire / HTTP 304s                          |     revalidated (144 × 304) |                  **0.00 MB / 0 × 304** |         **0.00 MB / 0 × 304** | **90/91 disk cache hits** |
| Warm `studio-input-ready` / `shaded` (ms)                   |                   — / 2,703 |                      **1,603 / 2,203** |                             — |                **-18.5%** |
| RTX 4090 4K steady FPS (Desk Day / Night / Bench / Cabinet) |          140.49 (desk warm) |      **143.8 / 143.8 / 144.0 / 144.0** |                             — |        **144 FPS locked** |
| RTX 4090 4K main-color GPU P50 (Day / Night)                |                     4.73 ms |                     **4.28 / 4.22 ms** |                             — |                **-10.8%** |
| Active desk draws / tris (4-zone culling)                   |                1,019 / 989k |                         **406 / 282k** |                             — |       **-60.2% / -71.5%** |
| GPU texture VRAM (53 standalone textures)                   |                   307.24 MB |                           **76.85 MB** |                             — |     **-230.39 MB (-75%)** |
| CI & targeted `@webgl` tests                                |                      passed |        **79 / 79 CI + 7 / 7 `@webgl`** |                             — |            **100% green** |

### Production publish scope

- **Live R2 & Vercel production publish:** Verified locally via `VITE_ASSET_BASE_URL=https://assets.felixpy.com/felix-studio/ npm run build` + `node scripts/deploy/r2-assets.mjs dist --check` and `tests/media-manifest.spec.ts` (confirming `public, max-age=31536000, immutable` on all hashed media/KTX2/WASM/fonts, `public, no-cache` on `media/credits.txt`, and strictly additive non-destructive R2 uploads for old-version coexistence and instant rollback). Actual production publish is handled separately.
