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
- `npm run test:ci`: **69 / 69** passed (`35.1 s`).
- Targeted `@webgl` Playwright suite (`studio.spec.ts`, `room-picking.spec.ts`, `rear-loading.spec.ts`, `workstation-fit.spec.ts`, `case-accent-lighting.spec.ts`, `room-warmup.spec.ts`, `studio-gpu-color-passes.spec.mjs`): all passed.
- 5-camera visual regression verified via full-resolution screenshots: Desk (night & daylight), PC Tower close-up (`case` Hero swap), East Workbench (`bench` seated), South Collection Cabinet (`cabinet`), and West Window (`window`), plus Intel UHD 770 native 1080p render.
