# Studio performance standards

Use these criteria when changing room rendering, asset loading, graphics defaults or inspection. The hardware targets are product goals. The percentile thresholds are proposed engineering acceptance gates. Record the decision and supporting measurements when changing them.

## Product targets

| Hardware and acceptance quality           | Required 3D drawing buffer | Nominal release target | Minimum average cadence | Stretch target at the same native resolution |
| ----------------------------------------- | -------------------------- | ---------------------: | ----------------------: | -------------------------------------------- |
| RTX 4090, all settings at highest quality | 3840 × 2160 native         |                144 FPS |               136.8 FPS | —                                            |
| Intel UHD 770, low quality                | 1920 × 1080 native         |                 30 FPS |                28.5 FPS | 60 FPS                                       |

Accept an average cadence up to 5% below the nominal release target using the minimum average cadence column. Apply the frame-time gates below at the nominal target. After a tier passes, evaluate its stretch target separately and record the quality settings used. Count distinct rendered scene frames presented at native resolution for both targets.

| Target cadence | Frame budget | Suggested CPU / GPU P95 work budgets | Proposed presented-frame P95 / P99 limits |
| -------------- | ------------ | ------------------------------------ | ----------------------------------------- |
| 144 FPS        | 6.94 ms      | 4.5 / 5.8 ms                         | 7.2 / 7.5 ms                              |
| 60 FPS         | 16.67 ms     | 10 / 14 ms                           | 17.0 / 17.5 ms                            |
| 30 FPS         | 33.33 ms     | 20 / 28 ms                           | 34.0 / 35.0 ms                            |

Provide visible loading feedback at least once a second while the loader is active, reporting each loading stage (engine initialization, full-room geometry & textures, shader compilation, GPU texture upload, and 360° lighting/view prewarm). Enter the room once full-room assets, shaders, GPU uploads, and view prewarming are ready so the first 360° rotation incurs zero resource- or shader-induced stalls. Measure the entire room load through asset and shading readiness.

CPU and GPU work overlap. Record CSS viewport, device pixel ratio, drawing-buffer dimensions and the main render target separately. Report adaptive resolution in a separate row. A 4090 run at 1440p is a repeatable development comparator. Verify the monitor refresh mode and actual presented cadence on the target system.

## Measurement and release gates

1. Pin browser version, adapter/backend, power mode, foreground status, view, weather, day/night and quality. Record browser, OS/driver, refresh rate, monitor scaling, cache policy and actual render sizes with every result. For cold visits start a fresh browser profile with HTTP cache disabled. For warm visits enable caching in a separate context, prime the same origin once, then reload and measure. Avoid Playwright routing on the warm run because it disables the HTTP cache. Use a local weather fixture or targeted CDP interception and verify actual cache hits in the network trace. Software GPU emulation is useful for functional coverage only.
2. Record the first visible loader paint, progress and activity indicator changes, loader removal, first input, main room asset readiness, rear asset readiness and full-quality room rendering. Use a compositor trace or display recording to check visible loader feedback. Measure room rendering intervals, main-thread long tasks, asynchronous GPU timer queries and actual presents separately. Discard disjoint GPU queries.
3. For release, run five cold and five warm visits per target and sample 60 seconds per steady route. Include desk rotation, glass PC, bookcase, cabinet, equipment wall, printer, snow/rain at the window and first/repeat inspections. Hold weather, blinds, time, camera and exposure constant for comparisons. Run 10 minutes of repeated turns and inspections for memory growth, cache eviction and recovery. Compare an empty-scene control to identify host scheduling noise.
4. **Proposed release gates.** After first input, require zero resource-induced stalls over 50 ms in the first ten seconds following input on the cold route and fewer than 1% of intervals over twice the target frame budget. At steady state, verify the tier's minimum average presented cadence and the corresponding P95/P99 limits above, with fewer than 0.1% of intervals over twice the target frame budget. Report actual missed refresh opportunities as well. Sample render sizes throughout the route. A native run requires the full requested drawing buffer and, when present, a full-size main color target. The direct low path uses the default framebuffer.
5. Attach the tested commit, build fingerprint, route, hardware, before/after traces, images, test results and a rollback path to each performance change. Inspect fine text, silhouette, thin high-contrast lines, glass, nearby reflections, contact shadows and temporal flicker. Visual checks include native-size stills and a matched motion recording. Run the production build and relevant Playwright interactions before release.
6. Keep changes to the test contract here. Record the baseline, tested commit and measurement conditions with each published result. Keep local copies of raw traces, screenshots and run output in untracked storage.

## Engineering guardrails

Apply these rules to all future room, material, shader, asset, and interaction changes to avoid regressions:

### Assets and visual fidelity

- **No decimated room-model duplicates or stale 2D planar lightmaps:** Keep original hero geometry and real-time lighting/shadows across room and close-up views instead of maintaining parallel `*-room.glb` decimated swaps or static room lightmaps. Reserve lazy loading and visibility culling for genuinely unseen interiors (e.g., keyboard switches, chassis interiors, deep camera lens optics).
- **Mandatory GPU-compressed delivery:** Encode new standalone textures in `public/media/{materials,photography,panoramas}/` (and large 2D atlases) as sibling `.ktx2` files (`scripts/assets/encode-ktx2.mjs`: ETC1S for sRGB color/photos, UASTC+Zstd for normal/linear maps, with offline mipmaps and WebGL-correct orientation). Run `scripts/assets/optimize-glbs.mjs` (`KHR_mesh_quantization`, `EXT_meshopt_compression`, `KHR_texture_basisu`) on exported GLBs while respecting per-asset size gates.
- **Offline PMREM environment probes:** Bake studio and fixture environment probes offline into `.pmrem.gz` (PMR2 HalfFloat cubemaps) via `scripts/assets/bake-pmrem.mjs`. Never run synchronous `PMREMGenerator.fromEquirectangular()` on the startup critical path or during interactive switches (such as day/night or city changes).
- **Preserve art provenance:** Never modify `.blend` source masters in `felix-studio-art` for web workarounds; record art commits and export SHA-256 checksums for reviewed exports.

### Shaders and WebGL2 / ANGLE D3D11

- **Uniform-bounded non-shadowed light loops:** Keep non-shadowed `SpotLight` and `PointLight` loops bounded by uniforms (`uSpotCount`, `uPointCount`, `uCaseEmitterCount`) so Windows ANGLE/D3D11 FXC does not auto-unroll massive shaders and double cold compile time. Reserve `#pragma unroll_loop` strictly for shadowed light loops indexing `sampler2D` arrays.
- **No `RectAreaLight` LTC shading:** Keep `NUM_RECT_AREA_LIGHTS = 0`; approximate practical light bars and lamps with calibrated `SpotLight`/`PointLight` fixtures and emissive meshes.
- **Scope specialized shader patches:** Gate localized hooks (such as cabinet spotlights or case emitters) via explicit `material.userData` opt-in flags so unrelated room materials do not pay extra VGPR or compile overhead.
- **Stable program cache keys:** Every `onBeforeCompile` hook must define a deterministic `customProgramCacheKey()` so identical materials share compiled WebGL programs.
- **Material simplification hygiene:** When downgrading a `MeshPhysicalMaterial` to standard shading, delete `material.defines.PHYSICAL` in addition to clearing `isMeshPhysicalMaterial` so Three.js preserves dielectric Fresnel specular.
- **Demand-driven shadow updates:** Keep `renderer.shadowMap.autoUpdate = false` and per-light `light.shadow.autoUpdate = false`, triggering `requestShadowUpdate()` only when geometry moves or light/blind/weather state changes.

### Render pipeline, batching, and runtime hygiene

- **Avoid unnecessary 4K offscreen targets and copies:** Do not reintroduce default 4× MSAA `RGBA16F` offscreen targets or per-frame `GTAOPass` (which cause TBDR tile spills on Apple Silicon and heavy 4K bandwidth overhead). Prefer zero-copy CSS `filter` grading over fullscreen `FramebufferTexture` copies.
- **Instance and batch static geometry:** Use `InstancedMesh` for `>= 4` repeated same-material parts (DIMMs, pins, fins, light strips) and route rigid static subtrees through `batchRoomStaticGeometry()` with `matrixAutoUpdate = false`, explicitly excluding `room-lod.gz` meshes, interactive targets, and animated subtrees (blinds, ferry, doors, drawers). Ensure instanced geometry origin adjustments do not alter parent `localBounds()`.
- **Scissor coordinates:** Three.js `renderer.setScissor()` multiplies by DPR internally; always pass CSS-pixel dimensions from `renderer.getSize()`, never `getDrawingBufferSize()`.
- **Preload interactive transitions and keep startup lean:** Avoid high-iteration synchronous `Canvas2D` `fillRect` loops on startup; defer non-initial UI bundles (`Desktop`) and high-res book covers until ready/inspect; preload and GPU-upload interactive environment swaps (all city window panoramas, depth maps, and both day/night PMREM probes) so switching cities, weather, or day/night incurs zero shader compilation or upload hitches.
- **Sleep off-screen and hidden work:** Gate off-screen zone animations behind `zoneCuller.isZoneVisible()` and throttle or pause rendering when hidden or inside the full-screen computer UI.

### Regression budget ratchets

Treat exceeding these thresholds on the desk steady route or startup checks as a regression requiring investigation before merge:

- Active `RectAreaLight` count: `0`
- Active desk draw calls (4K steady, 4-zone culling): `<= 550`
- Active compiled shader programs (4K desk): `<= 100`
- Immediate 360° turn or city switch after load: `0` new shader compilations and `0` frames `> 50 ms`
- Warm repeat visit immutable media revalidations (`HTTP 304`): `0` (`0.00 MB` core asset transfer)
