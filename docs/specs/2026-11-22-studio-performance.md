# Studio performance development plan

The website code baseline is `5ce54d92feea442a2611f74c93cece7a5d59c80b` on `codex/studio-remake-checkpoint`, measured on 22 November 2026. The [performance standards](../performance-standards.md) define hardware targets, frame budgets and visual acceptance. Update the measurements and open experiments here as work lands.

The current project covers startup, resource scheduling, high-quality rendering and native low-quality rendering. Frame generation, upscaling and weak-network optimization are outside this project. Reuse the current assets first and seek approval for new GLBs, meshes or LODs before creating them.

The named hardware profiles keep their renderer checks for acceptance. The UHD 770 profile matches the full model name and excludes Arc A770. For another GPU, add `--current-adapter` to keep the profile's quality and dimensions while measuring the hardware renderer Chrome actually uses. On Windows the runner uses ANGLE D3D11. On other operating systems Chrome selects its own backend. Run 134 verified a 2560 × 1440 viewport and drawing buffer on Windows with the active RTX 4090. The macOS argument check verified the backend selection with a simulated platform value. Actual Mac browser behavior is awaiting hardware testing.

```sh
node scripts/performance/studio-benchmark.mjs 1440p 1 --current-adapter
```

## Hardware milestones

- **RTX 4090:** Validate native 3840 × 2160 at 144 FPS with all settings at highest quality. Use the full-quality desk route to check the effect of each rendering change.
- **Intel UHD 770:** Validate native 1920 × 1080 at 30 FPS on low quality first. Use a lightweight desk prototype to measure visual quality and frame pacing, then extend it to the required routes. Once native 30 FPS passes, evaluate native 60 FPS as a stretch target.

## Measured starting point

Ten independent cold visits used local production output on Windows, an i7-13700K, Chrome 157.0.8103.79 and hardware ANGLE/D3D11. Each run recorded about twelve seconds of desk rotation after full shading, with a clear-night weather fixture and the tab reporting visible. The table shows the median of the per-run averages and percentiles. FPS here counts room render submissions. The GPU adapter and render sizes were checked during each run.

| GPU and setting                                            | Actual 3D pixels | Runs |    FPS | Frame interval P95 / P99 |
| ---------------------------------------------------------- | ---------------- | ---: | -----: | ------------------------ |
| RTX 4090, high, 4× MSAA                                    | 3840 × 2160      |    3 |  64.44 | 27.6 / 41.7 ms           |
| RTX 4090, high, 4× MSAA                                    | 2560 × 1440      |    1 | 103.99 | 20.9 / 41.6 ms           |
| UHD 770, low, native-size diagnostic override              | 1920 × 1080      |    3 |  11.60 | 256.9 / 277.8 ms         |
| UHD 770, low, production adaptive path in a 1080p viewport | 960 × 540        |    3 |  30.34 | 41.8 / 104.5 ms          |

On every cold visit the loader had a gap near **one second** between available main-thread animation callbacks. The worst gap per run ranged from 980.1 to 1,074.1 ms, including the partial intervals at mount and removal. No page or request errors were recorded. Headless, loopback measurements establish a reproducible development case. Physical presentation at 144 Hz, weak-network startup and the other room views still need verification.

A separate 4K CPU profile located two startup stalls. Between 0.306 and 1.453 s, 646 of 940 sampled stacks included `buildStudio`. Geometry conversion, book-back typesetting, the cooler OLED texture and batching all appear there. Between 1.453 and 2.192 s, 506 of 510 stacks included the simplified first-picture draw. Uniform discovery accounted for 361 leaf samples and buffer creation for 83. These are sampled CPU stacks and can include waits inside a graphics call. GPU timing and presentation require separate instruments. The profiled run is excluded from the table.

## What already runs at this commit

| Area                      | Current behavior                                                                                                                                                                                                                                                                                                                                                                                             | First place to look                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Loading indicator         | Main-thread animation approaches 90% over 1.9 seconds and also follows reported progress. A second shader canvas can start after 2.2 seconds. The loader's existing test substitutes a room stub.                                                                                                                                                                                                            | `src/app/ui/LoadingScreen.tsx`, `src/app/App.tsx`, loader test in `tests/studio.spec.ts`                                    |
| First picture             | Room construction runs synchronously. A simplified shading pass draws the preview and signals readiness. Full shading later emits `studio-room-shaded`. Rear assets may still be pending then.                                                                                                                                                                                                               | `src/scene/StudioView.tsx`, `src/scene/room-first-frame.ts`, `src/scene/Finish.tsx`                                         |
| Warm-up and deferred work | Front shader batches contain up to 48 objects with parallel compile support. Background batches synchronously compile up to 40 objects. Front/background upload loops use 3/2 ms soft budgets between textures. Without the parallel compile extension this warm-up queue is skipped and programs can initialize on first use. An idle callback or an interaction starts the queued rear factories together. | `src/scene/room-warmup.ts`, `src/scene/studio.ts`, `prepareRear` in `StudioView.tsx`                                        |
| Device and render paths   | High quality uses a DPR range of 1–1.5. With float color targets it renders half-float beauty and composite buffers, up to 4× MSAA, and GTAO at half width and height. Low quality renders directly, and its adaptive scale may reach 0.5. It can swap in reduced index buffers for eligible meshes. The desktop scene throttles background room drawing while using the virtual computer.                   | `src/app/graphics-device.ts`, `src/scene/StudioView.tsx`, `src/scene/Finish.tsx`, `src/scene/room-detail.ts`                |
| Model delivery            | The build emits two shared part libraries and gzip payloads for independently loaded models and data. The browser caches part-library promises, decompresses as needed and reconstructs the part streams on the main thread. Meshopt decoding is already used.                                                                                                                                               | `scripts/build/studio-parts.ts`, `src/scene/blender-library.ts`, `src/scene/blender-parts.ts`, `src/scene/display-model.ts` |

The reference build has **54 files totaling 20,069,653 bytes** under `dist/media/models/`, including `room-parts.bpk` (4,065,963 bytes) and `workshop-tools.bpk` (268,017 bytes). Startup awaits the room library, scene module and a font-preparation gate that times out after 1.25 s in `src/main.tsx`. Obtain first-visit bytes from a cold network trace and record which requests finish before first interaction. Installed bytes, transfer bytes, decoded CPU buffers and GPU memory are separate quantities.

Two earlier experiments narrow the search. On the earlier build the median 4K GPU elapsed time for the main-color render was 5.67 ms, including any shadow work inside that call, versus about 1.44 ms for the five downstream passes combined. An isolated reconstruction of the shared part library took 16.8 ms at P95 on the main thread or 24.8 ms round trip in a JS Worker. Recheck main-color cost and UI-thread availability on the baseline build. The isolated experiment excluded decompression, scene construction and GPU upload.

## Development order and exit criteria

1. **Reduce the cost of reaching the first picture.** For the first stall, test deferring off-camera book-back typesetting and preparing only the geometry needed for the desk preview. For the second, separately test preparing a minimal set of preview shader variants and uploading a bounded set of visible buffers per frame. Confirm the desk outline, clock, labels and picking still work. Mark part fetch/inflate/unpack, room construction, first preview draw, first accepted input and full shading. Compare the worst intervals, first meaningful picture, input-to-paint and subsequent first turn against the unchanged baseline. Keep the variants independent so a compositing improvement cannot hide delayed interaction.
2. **Schedule existing inspection resources.** Prefetch the computer desk first, followed by the workbench, equipment wall and display cabinet. Use `p-queue` to bound concurrent speculative work and promote explicit interaction. At loader exit the user can turn, enter the computer and inspect objects with full detail. Keep the installed model visible until replacement geometry and materials are ready. Coalesce retries, discard obsolete completions, release orphaned resources and preserve picking and original transforms. Measure startup, decode, main-thread mesh installation and first upload.
3. **Reduce steady-state room cost.** Start with the desk main color pass. Earlier probes ranked it above the final full-screen passes. Repeat CPU submission and per-pass GPU timings on this commit before choosing a change. Count draw calls and triangles per pass, then test one zone with static same-material batching or instancing. Preserve culling granularity, transparency order, moving parts and individual hit targets. Separately A/B shadow invalidations, MSAA, GTAO and output bandwidth if those passes consume the remaining budget. Record bypass visuals and P95 improvement per experiment.
4. **Develop the native iGPU path.** Begin with one fixed 1080p desk view and a low-cost room representation that uses existing assets. Keep the room at low detail and promote the inspected item to full detail. Exercise fast turns, first and repeat inspection, put-back and cancellation. Expand by zone when the prototype meets the 30 FPS frame-pacing and visual checks. The existing 30.34 FPS sample used a 960 × 540 drawing buffer and serves as an adaptive comparison.
5. **Gate larger technology changes.** JS Workers target measured, separable CPU data work. Built-in decompression and existing Meshopt/WASM decoding each need independent timing. Consider new WASM only for a remaining hot kernel after transfer costs. Run a separate WebGPU spike only if submission or GPU scheduling remains a dominant cost after the WebGL changes. Use one representative room view, matched assets, effects and resolution, and the same timing and visual checks. Keep the working WebGL path available throughout.

## Reproduce the baseline

Use Node.js 24+ and installed Google Chrome. From the website checkout, run the production build, then the [benchmark](../../scripts/performance/studio-benchmark.mjs) on Windows with the specified GPU. It starts and closes its own loopback server. Run one GPU workload at a time.

```powershell
npm ci
npm run build
node scripts/performance/studio-benchmark.mjs 4k 1,2,3
node scripts/performance/studio-benchmark.mjs 4k 1 --startup --warm
node scripts/performance/studio-benchmark.mjs 4k 1 --loader-profile
node scripts/performance/studio-benchmark.mjs 1440p 1
node scripts/performance/studio-benchmark.mjs uhd-adaptive,uhd-native 1,2,3
```

The RTX and Intel profiles require their respective adapters. Check the recorded GPU string as Windows may reassign adapter identifiers after a reboot. The harness seeds settings, stubs weather, disables the HTTP cache by default and sends camera input. It records render intervals, loader callback gaps, CPU submission time and the build fingerprint. `--warm` primes the same origin in the browser context and reports cache hits and HTTP revalidations for the measured reload. The low native override pins the renderer's pixel ratio to 1. For physical-display release testing, follow the protocol in the standards.

The reference production chunk was `StudioView-DJH1_7OT.js`, SHA-256 `186cc88bd72aa5a9511a4fec31e89cc3a53b49a12330d9c5b1bc9acb0838fb83`. The baseline includes ten benchmark runs and the separate `loader-profile-4k-1` CPU profile.

Run `npm run test:ci` and the relevant WebGL interaction tests. For the first two tasks, run the loader test and inspect the first-drag, deferred cookware and cabinet-return cases in `tests/studio.spec.ts`. Run `npm test -- tests/blender-parts.spec.ts tests/blender-mesh.spec.ts` when changing the decoder. Compare the bookshelf route with `tests/bookshelf-view.spec.ts`. Pair fixed-angle native screenshots with a same-route motion capture. Inspect the OLED clock, desk Codex Micro, lower-shelf book spines, window and blind edges, hair, lights behind the case glass, statuette silhouettes and contact shadows. Attach before/after traces, raw measurements, images, branch/commit and a rollback switch or individually revertible change to each performance PR. Revert candidates that trade a visible defect for a timing gain.

The website owns loading, rendering, scheduling and measurements. The sibling `felix-studio-art` repository owns Blender scenes and export recipes. Changes to meshes or textures enter the website as reviewed exports. A website-only performance experiment builds without the art repository.

## First development milestone

Deliver the desk-preview construction experiment first. Attach the before/after startup timeline, visual comparison, first-input latency and worst loader gap. Test shader and buffer preparation separately. The rendering owner can reproduce the desk main-color cost on a different GPU or outside the startup test window. Arrange iGPU mesh exports after measuring a representative zone. Record the commit, effect on target metrics, visual differences and next decision for each experiment.

## First matched trials

The 22 November development runs used Chrome 157.0.8103.79 on Windows and checked hardware ANGLE/D3D11, viewport and actual drawing buffers. Startup tests sent a 96 CSS pixel desk drag after the loader cleared. Input time below runs from the pointer move's browser timestamp to the first room submission with a changed camera. The time between loader removal and event delivery is recorded separately. These are headless rendering and main-thread measurements. Physical display cadence remains a release check.

| Native 4K startup experiment                                | Loader worst gap | Loader removed | First input to changed submission | Decision                                                                                                                                 |
| ----------------------------------------------------------- | ---------------: | -------------: | --------------------------------: | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Same-build control, two visits                              |           985 ms |       1,890 ms |                            ~11 ms | Reference for books, shaders and part worker                                                                                             |
| Defer off-camera edition-back artwork, two visits           |           892 ms |       1,798 ms |                            ~11 ms | Build fell from 592 to 551 ms. The first-ten-second frame interval P95 rose from 201 to 229 ms. Keep for combined scheduling tests.      |
| Warm preview shaders, two visits                            |           993 ms |       2,460 ms |                             ~9 ms | The first picture arrived about 570 ms later. Keep the existing default.                                                                 |
| BPK worker, two visits                                      |         1,007 ms |       1,964 ms |                            ~11 ms | The room part fetch-to-install interval rose from 52–64 to 83–91 ms. Worker startup offset the saved main-thread decode time.            |
| Frame-sliced build plus books and priority queue, one visit |           756 ms |       2,089 ms |                             27 ms | Same-build control was 967 ms, 1,882 ms and 11 ms. The combined route exposed a 6.7 s long task after input, so it remains experimental. |

The independent visible-buffer upload trial delayed the first picture by 505 ms on its matched build. The independent Meshopt worker trial showed identical inspected geometry and a working fallback in browser tests. Its one cold-start comparison showed a longer worst gap and a worse post-input P95. The later comparison below led to removal of both worker paths.

The unchanged 4K GPU replay had 98 matched samples. Main color measured 5.43 / 6.61 ms at P50 / P95 and the five downstream passes measured 1.37 / 1.72 ms combined. The travel-board pin instancing trial reduced the end of the desk route from 1,188 to 1,165 draws at the same triangle count. Submission FPS was 126.29 versus 125.18 and P95 remained 13.9 ms. This size of change did not improve frame pacing in the test.

The high-quality path now applies denoised ambient occlusion in the final output shader. This removes two passes and one 3840 × 2160 RGBA16F attachment, saving about 63.3 MiB of color storage at 4K. A same-build RTX 4090 comparison at native 4K with 4× MSAA measured downstream P95 of 1.80 ms before and 1.58 ms after, and all timed passes at 7.75 ms before and 7.41 ms after. The matched desk stills showed no visible change in shadows, text, blinds or glass. The legacy path remains available through `--legacy-output`.

At native 1920 × 1080, turning off default-framebuffer antialiasing on UHD 770 improved submission FPS from 11.68 to 14.69 and P95 from 263.8 to 187.2 ms. The 30 FPS gate remains open. Keep the experiment opt-in while measuring the cheaper low-quality shading path and reviewing thin detail.

With antialiasing off in both runs of the same build, the simple low-quality shader increased native 1080p submission FPS from 14.70 to 46.16 on UHD 770. P95 improved from 194.4 to 28.0 ms and P99 from 229.2 to 69.4 ms. Fine desk-mat lettering, PC glass and contact shading visibly changed. The 35 ms P99 and visual checks remain open.

Sampling tied a 5.95 s long task on the sliced route to fresh waterfront and dust shader programs during the first turn. Reusing each effect's program across the preview and finished renderer removed both multi-second discoveries in the next instrumented run. The worst long task in the ten seconds after input fell to 488 ms. The first finished draw still contained long PBR shader or driver work of about 3.03 s.

On the inspection preload trial, the gate waited for the installed keyboard and switch GLB and the other front and rear assets. The 4K loopback visit reached input at 2.29 s and downloaded 27.80 MB before input. The earlier no-gate comparison reached input at 1.88 s with 16.45 MB transferred. Measure first and repeat inspections before promoting the gate. The existing bookshelf still loads the full cover print when inspecting a book.

The first warm-cache replay of the current default build recorded 113 HTTP 304 revalidations and 33.3 kB transferred before input. The loader ended at 1.34 s and its longest callback gap was 610 ms. This run verifies the reload procedure and does not replace the release repetition count.

The baseline bundle fingerprint is recorded above. The sliced-build and instancing comparisons used StudioView SHA-256 beginning `476f7581`. See `node scripts/performance/studio-benchmark.mjs --help` for the experiment switches.

## Compositor and native-lighting follow-up

The default loader animates the status cursor with CSS opacity and transforms. The numeric meter and segmented fill still follow the same progress curve, and polling stops at the plateau until reported progress changes. The default loader no longer opens a second WebGL context. `--legacy-loader` selects the previous title shader and stepped cursor for comparison.

Two matched native 4K startup traces used the same build (`3f298579` StudioView SHA-256), sliced construction, stable effects and inspection preload. The compositor captured 50 screenshots with the legacy loader and 158 with the CSS cursor. The capture-interval P95 fell from 198 to 39 ms. After dropping consecutive identical snapshots, P95 fell from 392 to 55 ms. Nine visual updates were captured during the first preview draw with the CSS cursor, compared with one using the legacy loader. The main-thread callback gap remained about 790 ms. These headless compositor screenshots show the loader can change while the main thread is busy. The original comparison used a 33.4 ms loader target. The current loading requirement is visible feedback at least once a second with prompt progress updates. First-input smoothness and time to readiness across the room are the primary startup measures. Use `--loader-trace` for the trace and screenshots, and the separate raw rAF series for main-thread stalls.

The native 1080p lighting trial with antialiasing disabled skips mathematically zero direct-light contributions in the low PBR shader. Two same-build UHD 770 visits improved mean submission FPS from 14.69–14.88 to 17.06–17.32 at unchanged draw and triangle counts. P99 fell from about 222 ms to 188–194 ms. Fixture pixels matched ordinary lighting, clearcoat, and out-of-range lamps. Time to full shading increased from 8.43–8.81 s to 11.36–13.91 s, so the variant stays opt-in. Reproduce it with `uhd-native --native-low --culled-lights`.

In two matched RTX 4090 startup pairs, prioritizing and reflecting programs for the live viewport removed the late PBR shader discoveries. The first complete high-quality frame fell from 3.04–4.42 s of work to 0.67–0.70 s. Completion of full shading improved from 27.26–30.19 s to 26.08–26.96 s. The first-ten-second frame interval tail was unstable and reached P95 around two seconds in both incremental visits. Keep this trial opt-in under `--incremental-warmup` while tracking driver waits and late asset arrivals.

Static batching now applies transforms in the merged buffer for compatible Float32 attributes. This avoids cloning every source attribute and preserves the original geometry. Two matched cold pairs measured batching at 108 ms before and 25–29 ms after. Total synchronous construction fell from 613–627 ms to 537–545 ms. Indices, positions, normals, UVs, tangents and movable targets matched the previous path in the regression fixture. Non-Float32 and interleaved attributes retain the existing path. Use `--transform-first` to replay the original batching order.

At the centered desk pose, the tower contributed roughly 789,000 of 1.71 million triangles and 284 draw submissions. Tightening frustum bounds and changing opaque ordering yielded no whole-frame gain on RTX 4090. A separate window-occlusion trial lowered isolated waterfront P95 from 0.15 to 0.09 ms, while total timed P95 rose about 0.33 ms in each matched sweep. The production window path retains its existing shader.

Indoor airborne dust was removed after visual review. In the earlier instrumented 4K first turn, program discovery for its draw accounted for 4.21 s of the 5.95 s long task. In a later comparison, the control's slow-draw log recorded a 135 ms dust draw. The new build eliminated the pass. Total input-window tails varied across both traces, and the first full-quality PBR transition still needs work. Window weather and cup steam use their separate effect paths.

## Room readiness and the first turn

The default loader updates its simulated progress approximately every 100 ms while it advances and applies reported progress immediately. The CSS cursor continues at the plateau. The rear-ready mark waits for deferred jobs to finish mounting, including jobs that do not call the loading manager. The benchmark reports front material preparation, rear readiness and the first fully shaded viewport separately. The summary uses the latest of those marks for the combined readiness time. Turning or inspecting can still reveal unprepared shader variants.

Native 4K cold startup on RTX 4090 with the same build (StudioView SHA-256 prefix 2cde869a), sliced construction, deferred book backs, stable effects and ordered rear loading yielded the following. The frame intervals cover the ten seconds after the first desk turn and measure render submissions.

| Shader warmup | Front ready | Rear ready | Initial shading | Frame P95 | Worst gap | Gaps over 50 ms |
| ------------- | ----------: | ---------: | --------------: | --------: | --------: | --------------: |
| Incremental   |      2.42 s |     6.02 s |         18.05 s |  180.6 ms | 1777.6 ms |              36 |
| Fixed pacing  |      2.44 s |     3.42 s |         56.82 s |   20.8 ms |   76.4 ms |               3 |
| Adaptive      |      2.46 s |     3.68 s |         40.09 s |   20.9 ms |   90.3 ms |               3 |

Fixed pacing took 39.96 s in a separate cold visit. The single matched pair does not establish that the adaptive control consistently shortens warmup. Both paced variants stay opt-in. The 58–63 ms upload of the high-resolution world atlas was observed inside a preview draw with a cached program in both paced visits.

A second build (StudioView SHA-256 prefix 22cc2cb8) held the first turn until three seconds after the loader disappeared. Automatic rear loading began after the loader and prioritized desk, workbench, gear, then cabinet. It moved rear readiness from 8.86 to 5.04 s, before the delayed input. Initial shading moved from 16.63 to 15.65 s. First-turn P95 fell from 76.3 to 62.5 ms and the worst gap fell from 1381.8 to 159.6 ms. The count of gaps over 50 ms was 30 versus 33. The longest interval between successive numeric progress updates or loader removal in the three runs was 711 ms. Keep automatic rear loading opt-in while repeating immediate input and inspection routes.

With automatic rear loading and a 20-second pause, initial shading was ready at 16.05 s. The first-turn P95 was 20.7 ms with one frame interval over 50 ms. The pointer-down dispatch still took 787 ms while main-thread tasks continued after initial shading. Repeating with book backs prepared during construction still produced a 1204 ms dispatch delay in one cold visit. Three-second native 4K route smokes recorded 144 FPS submissions at the rain window, 139.65 FPS inside the computer case and 144 FPS at the collection cabinet. P95 was 7.0 ms in each. These smoke runs check the benchmark routes and are shorter than the release sampling window.

Decoding the world atlas with ImageBitmap reduced its first upload from 85.5 to 34.5 ms in the automatic-loading comparison. The two smaller prints still took about 62 and 82 ms to upload. Initial shading remained near 15.5 s and the worst first-turn interval rose to 479 ms. The bitmap path remains experimental.

Use the startup benchmark with `--full-room` to wait for the rear-ready mark and `--input-delay-ms=3000` to reproduce the delayed turn. Runs 33 and 35–38 cover the paced warmup, delayed turn and route comparisons.

## First-pointer audio initialization

The 20-second delayed native 4K press still dispatched late with book backs prepared during construction. Run 39 reproduced a 950 ms dispatch delay and attributed approximately 942 ms of overlapping CPU samples to synchronous construction of the Web Audio context in the global gesture handler. The three seconds before the press were a separate render workload, dominated by Three.js renderer and program setup samples.

Automatic playback continues through the HTML media element. Lighting and spectrum analysis start when the Music app opens or an explicit playback action requests analysis. In the matched delayed, non-profiled visits, pointer-down dispatch fell from 1204 ms to 207 ms (runs 38 and 40). Initial shading was 16.72 and 16.19 s respectively. The immediate turn on the new build entered at 2.01 s and completed initial shading at 17.34 s, with a worst submitted-frame interval of 1.59 s. Shader and render preparation remain the limiting work for the immediate turn.

## Water motion scheduling

The room initially renders the photographed water through the existing depth projection, rain refraction and color grade. The startup shader omits the wave, wake and moving reflection code. After the first finished room render and rear asset readiness, the app schedules wave textures and the animated program during idle time. It switches when both are ready. Reduced motion defers activation and pauses the water clock. `--eager-water-motion` restores the original load order for comparisons. Record `studio-water-motion-start` and `studio-water-motion-ready` separately from room readiness.

The isolated SwiftShader test renders before and after animation preparation, checks shared uniforms and confirms reduced motion leaves wave assets deferred. A complete room review on the same software backend recorded first shaded output at 25.81 s, rear readiness at 27.07 s, motion preparation at 35.84 s and animation ready at 40.25 s. The ferry moved in window mode. The separate mouse-driven walkthrough stopped earlier at the camera FOV timeout under software rendering. These runs verify the new order and animation behavior without measuring native performance.

Before this change, the native 4K default run 41 first exposed the waterfront program in a 441.5 ms draw. The first finished room draw took 3.09 s, including three late workbench material programs with 2.62 s combined draw time and 256 ms at the first GTAO denoise. The measured shader-reuse toggle alone did not remove the first waterfront stalls.

In a matched eager-motion build (StudioView SHA-256 prefix 2f778feb), prewarming the existing waterfront recreated the same scene with no waterfront draw over 50 ms in its trace. The control recorded 432 ms. Pointer-down dispatch was 643 ms with reuse alone and 351 ms with early prewarming. Initial shading was 18.18 and 18.02 s respectively. The benchmark still recorded over 50 ms frame gaps elsewhere in both visits. Recheck native timing with deferred motion before drawing conclusions about its speed.

The same build compared fixed shader pacing with a flat compiler traversal. Initial shading was 40.27 and 40.01 s, with one gap over 50 ms in each visit. The flat variant was archived. A catch-up experiment now covers visible or changed models that the initial compile pass missed, along with the first GTAO passes. Keep it opt-in until tested on native hardware.

Prepared active light slots on UHD 770 shortened first full shading from 12.39 to 7.46 s against direct-light culling, while steady submissions fell from 17.22 to 15.38 submission FPS. That prototype was archived. The selective matte-shading candidate and shared local-reflection uniform are opt-in. Software rendering and source checks confirmed their expected branches. Native frame pacing and full-resolution visual comparisons remain open.

## Native startup and low-quality follow-up

With the same native 4K build (StudioView SHA-256 prefix 01dab121), the run 55 eager-to-deferred river comparison moved the first waterfront draw from 463.4 to 356.2 ms and pointer-down dispatch from 672.7 to 568.5 ms. Initial shading changed from 17.91 to 17.75 s. The deferred draw recorded 15 ms of texture upload inside its 356.2 ms CPU span. That span includes browser and driver waits.

Run 57 isolated early preparation of the reduced waterfront shader. The control recorded a 345.3 ms waterfront draw. The early-preparation run reported no waterfront draw above the 50 ms logging threshold. Pointer-down dispatch fell from 557.9 to 362.8 ms. The loader exit moved from 1.64 to 1.70 s and initial shading from 18.38 to 18.41 s. Default deferred water now starts this preparation during room construction when the parallel compile extension is available. A complete default run with StudioView SHA-256 prefix 03b7e45a reached the loader exit at 1.68 s and initial shading at 17.76 s. It recorded no waterfront draw over 50 ms, with 59 other post-input intervals over 50 ms. Use --cold-waterfront to switch the early preparation off.

In the same run 55 build, live-view catch-up moved the first finished draw from 2.97 s to 132 ms and initial shading from 17.75 to 15.63 s. The first-input P95 rose from 208 to 271 ms, so catch-up remains opt-in. A Node regression covers entering the frustum during preparation, late material changes, linked-program readiness and target restoration. Changing graphics quality now cancels pending catch-up work on the previous render target. Combining early waterfront preparation and catch-up yielded 15.45 s. The paired shared-reflection run reduced active programs from 103 to 89 and total initial shading to 14.86 s, with worse first-input pacing. OLED-only early preparation shortened the OLED draw from 260 to 191 ms in one comparison, and initial shading moved from 17.75 to 18.18 s. Those two shader variants remain opt-in.

A paired UHD 770 replay used native 1920 × 1080, no framebuffer MSAA and a repeated desk turn after water animation became ready (build prefix 1023100ae6df, run 54). Selective matte shading raised submission FPS from 16.96 to 20.49, with P95 from 159.2 to 56.1 ms and P99 from 194.4 to 152.8 ms. Primary submit P95 stayed at 10.5 ms. Stills show the typography and glass while the tabletop and plaster highlights are slightly flatter. Other work was active on the host's discrete GPU. The candidate remains opt-in. A separate window scissor candidate bounds the existing panorama draw to projected openings and passed CPU coverage for 216 camera poses. In the matched 1080p matte replay on StudioView build prefix 03b7e45a (run 59), the scissor increased warm submission FPS from 20.24 to 21.10. Both visits had 56.1 ms P95. Intervals over 50 ms fell from 51 to 22 in this pair. Retain the option for comparators while checking additional room views.

The mouse-driven window walkthrough now passes with the original endpoint and ferry-motion assertions after camera zoom uses actual elapsed time. The physics and room animations keep their existing timestep cap. The isolated deferred-water test and live-view catch-up regression also pass.

The Windows present tool in scripts/performance/studio-present.mjs can capture with the installed PresentMon and analyze an explicitly selected process/swap chain. It reports displayed swap-chain cadence and frame-time distributions. A release result also needs scene-frame correlation, display validation and the full playback protocol from the standards.

After the default waterfront preparation in run 58, the 354.6 ms press-dispatch interval overlapped eight measured texture uploads totaling 257.2 ms. The desk oak upload alone took 147.8 ms. The staged preview experiment submits the first preview immediately and schedules at most one original texture upload per subsequent preview frame. A CPU fixture confirms scheduling and texture identity. Individual uploads still need native timing. High-quality direct light culling is also selectable after source and finite-contribution checks. It needs an equivalent-image and frame-time comparison at native 4K.

Runs 53–58 captured native timings. The run 59 matte and scissor comparison recorded a 405 × 856 rectangle around the visible window and confirmed that the panorama draw restored the earlier GL scissor state. The corresponding desk stills showed no visible clipping. Rain and doorway routes remain open.

## Texture transfer and GPU timing

The matched native 4K run 60 cut the loader-exit-to-changed-submit interval from 693 to 167 ms with staged preview texture uploads. Pointer-down dispatch dropped from 343 to 24 ms. The same 1536 × 1536 oak upload took 140.3 ms in the default visit and 21.0 ms when staged. First-input P95 changed from 243.2 to 257.0 ms, so the staged path remains optional.

Run 62 isolated ImageBitmap decoding for the original oak. Pointer-down dispatch was 354.5 ms in the control and 350.6 ms with the bitmap. As the oak became ready later, the 151 ms oak call was replaced by a 143.5 ms linen upload. Observed uploads overlapping press dispatch totaled 259.7 and 257.2 ms respectively. Bitmap plus staged uploads reduced the loader-exit-to-changed-submit interval to 167.9 ms from 702.9 ms in the control. These results locate the slow region in the first upload batch. The WebGL upload spans include conversion, transfer and driver waits, without attributing each component separately.

Run 63 tried a 512 × 512 lossless downsample of the existing oak color source with the original UVs, normals and roughness. Its estimated RGBA8 base storage is 1 MiB, down from 9 MiB. The small map was requested and did not appear among the logged uploads of at least 10 ms. The large delay appeared on the 137.4 ms linen call instead. Press dispatch changed from 329.1 to 355.7 ms.

The external image audit covers 135 WebP, PNG and JPEG assets, including seven at or above 2 million pixels. The default Shanghai-night run requested two of the seven, the desk oak and the 2880 × 1620 atlas. The atlas first uploaded during the turn at 57.5 ms. Shanghai day is 5120 × 2278, New York night is 3200 × 1014 and rain beads are 1792 × 1472. Those scene variants were absent in that visit. The other two are the 1536 × 1536 pine floor color and normal maps, also absent from the trace. A fresh GLB metadata scan found 152 embedded images in 48 model containers, including the two 2048 × 1280 teak maps and the 2124 × 1200 SELPHY postcard reverse. The desk mat artwork is 1974 × 875. An asset or model request alone does not establish its upload cost.

The optional main-color GPU query reported P95 of 7.30 ms for high-quality stock lighting and 6.31 ms with zero-contribution culling in the matched warmed 4K run 61 (61 samples each). Frame submissions were 129.11 and 129.00 FPS. Initial shading increased from 16.18 to 24.86 s. Keep both the high cull and the separate lean low-quality light kernel optional. The latter passed arithmetic equivalence checks and still needs native throughput and visual tests. The display-cadence witness also needs a headed calibration before physical results can be used for acceptance.

## Shanghai overcast panorama

Runs 64 and 65 used the same RTX 4090 build at native 3840 × 2160 high quality with the Shanghai window route and cold browser cache. The second build directory replaced only the overcast photograph with a same-aspect 2560 × 1139 WebP. The photos measured 733,118 and 224,050 bytes, with estimated base RGBA8 storage of 44.49 and 11.12 MiB before mipmaps. The depth map and render resolution were the same in both visits.

| Metric                                           | 5120 × 2278 | 2560 × 1139 |
| ------------------------------------------------ | ----------: | ----------: |
| First photograph `texSubImage2D` call            |    214.8 ms |    185.1 ms |
| Warm main-color GPU P95, 68 samples per visit    |     4.13 ms |     4.08 ms |
| Warm frame submission rate                       |  144.00 FPS |  144.00 FPS |
| Front and rear assets with initial shading ready |     16.89 s |     16.98 s |

Both upload calls started just after loader exit. Their CPU spans can include conversion, transfer and driver wait. Every sampled primary pass used a 3840 × 2160 default buffer and a 3840 × 2160 main color target. This pair shows lower asset bytes and estimated texture storage, a modest reduction in the observed upload call and comparable warm main-color work. Measure the integrated GPU separately before inferring a low-quality throughput benefit. The pixel-size window crop shows softer building facade detail on the smaller photo. A tiered color source can use the smaller photo for desk views and prepare the original asynchronously for close examination. Switch the color source within the same exposure after readiness, keeping normalized UVs, depth and projection calibration.

Replay with `--day --weather=overcast --route=window --seconds=8 --gpu-timing --texture-uploads --screenshot`.

## Native desk lighting and late ferry draw

Runs 66–67 replayed the same desk turn at native 1920 × 1080 on UHD 770 with framebuffer MSAA off, matte surfaces and window scissoring. The second visit added `--lean-lighting`. The renderer drew to the default framebuffer throughout. The two stills retain the desktop typography, timber shading, window alignment and PC glass. The moving screen, river and LEDs were captured at different times.

| Metric                                           | Matte and scissor | With lean lighting |
| ------------------------------------------------ | ----------------: | -----------------: |
| Warm frame submission rate                       |         21.04 FPS |          23.19 FPS |
| Warm submission P95 / P99 intervals              |   55.8 / 152.8 ms |    48.9 / 131.9 ms |
| Main-color GPU P95                               |          48.26 ms |           43.63 ms |
| Main-color GPU query samples                     |                15 |                 17 |
| Front and rear assets with initial shading ready |           13.05 s |            14.56 s |

The lean variant stays optional while the P99, startup cost and other room routes are checked. The measured GPU pass still exceeds the 33.33 ms frame budget. Run with `uhd-native --repeat-desk --native-low --matte-surfaces --window-scissor --gpu-timing --screenshot` and add `--lean-lighting` to the second visit.

Native 4K high-quality runs 68 and 69 used the same warmed desk replay for 15 seconds with and without slow-draw instrumentation. Submission rates were 124.59 and 131.59 FPS. The instrumented visit recorded a 590.5 ms draw for the river ferry's `Marine blue enamel` hull about 4.53 seconds into measured rotation, with no overlapping logged texture upload. The corresponding main-color submit took 595.8 ms. The uninstrumented visit reproduced a 583.3 ms frame interval. The hull entered the view after the room was shaded and water motion was active. Defer the ferry's first appearance until its scene-lighting program is prepared, and time preparation and first visible draw separately.

Runs 70 and 71 compared catch-up preparation with the same path limiting unchanged-view preview submissions to 30 FPS. Camera or scene changes still submitted immediately. In the immediate-drag native 4K replay, initial shading moved from 16.35 to 16.87 s and post-input submission interval P95 from 298.5 to 305.6 ms. Intentional idle gaps remained in the submission samples. The limited-preview experiment was removed.

Runs 72–73 used the same native 4K high-quality build with the slow-draw probe and a 12-second warmed desk replay. The optional `--warm-ferry` path compiles the existing vessel after deferred water motion starts, using the live scene lighting and main-color output configuration. The 585.3 ms hull draw disappeared from the slow-draw log. Worst warm interval fell from 590.4 to 20.9 ms and warm submissions rose from 118.57 to 127.91 FPS. Both visits reported 13.9 ms P95. In the first turn, a workbench switch-draw stall reached 390.1 ms on the variant after ferry warming finished. The wall-mount glare shield drew for 2.21 and 1.23 s respectively, before steady sampling. Keep ferry warming optional while reducing contention with first-turn workbench preparation. Physical present cadence and the 144 FPS gate remain open.

Runs 74–75 compared native UHD 770 lean, matte and scissor with the same options plus `--depth-prefill`. The depth pass writes a bounded subset of existing opaque, large room geometry into the native depth buffer. Color still uses the regular materials and ordering. Inspection views skip the extra pass. Warm submission FPS rose from 23.26 to 25.23. Submission P95 was 48.9 and 48.7 ms, with P99 of 132 and 125 ms. GPU P95 fell from 43.54 ms over 17 samples to 39.88 ms over 18 samples. The latter includes both depth and color draws, with the explicit clear before the depth pass outside its query. All 302 measured color frames in the variant had a depth prefill. Room readiness was 14.35 and 13.93 s. Keep the candidate optional until further native motion and inspection checks.

## First turn toward the workbench

Use `4k --startup --full-room --route=workbench --slow-draws --screenshot` to turn toward the workbench on the first drag after loader exit. The replay checks that the projected workbench center is inside the viewport. Without `--startup` the route clicks the workbench and samples seated camera movement. The first-drag route measures the full-shading cost of a different initial view from the desk.

| Run and startup options                         | Loader exit | Loader exit to changed submit | Full room readiness | First full draw | First ten seconds interval P95 |
| ----------------------------------------------- | ----------: | ----------------------------: | ------------------: | --------------: | -----------------------------: |
| 76, default, workbench turn                     |      1.67 s |                        706 ms |             25.99 s |         11.82 s |                         347 ms |
| 77, early rear, workbench turn                  |      1.65 s |                        710 ms |             25.37 s |         10.79 s |                         417 ms |
| 78, catch-up, workbench turn                    |      1.69 s |                        712 ms |             16.62 s |          133 ms |                         333 ms |
| 79, catch-up and staged uploads, workbench turn |      1.66 s |                        174 ms |             16.01 s |          133 ms |                         375 ms |
| 80, default, desk turn                          |      1.67 s |                        713 ms |             18.62 s |          3.13 s |                         229 ms |
| 81, catch-up and staged uploads, desk turn      |      1.83 s |                        183 ms |             16.33 s |          136 ms |                         382 ms |

The immediate workbench turn brought several cold programs into the first full render. Run 76 spent about 4.46 s on five H3C frame draws, 2.47 s on three Whale Girl print draws, 1.82 s on the two postcard faces, 1.00 s on the sampler acrylic, 0.83 s on the rocket plaque and 0.82 s on the wall lamp. Catch-up moves view-dependent preparation before the first full render. Staging reduced time to the first changed submission on both routes and the worst subsequent desk interval increased from 465 to 854 ms. Keep both switches available for further scheduling work while their mixed first-input intervals remain open.

The warmed workbench seat sustained 144 submissions per second over eight seconds at 4K in run 82. Main-color GPU P95 was 5.71 ms and submission interval P95 was 7.0 ms. `--draw-calls` confirmed native `WEBGL_multi_draw` availability on the test adapter and a median of 197 ordinary indexed draws for this route. The run used stock rendering.

Runs 83–84 compared the same build with and without `--warm-workbench` on the immediate turn. Scoped preparation uses the existing workbench lamp, sampler, postcard, H3C and rocket assemblies as soon as their rear materials settle. Whole-room readiness improved from 27.23 to 17.43 s and the first full render from 12.34 s to 433 ms. In the first ten seconds after input, submission interval P95 increased from 250 to 458 ms and the largest interval from 424 to 590 ms. Keep the workbench path optional. The visible-first, scoped-program tracking and render-target restoration cases are covered by `tests/room-warmup.spec.ts`.

Running the scoped and global catch-up preparers concurrently reached the 120-second full-shading timeout. Both variants now use the existing `studio-warmup` selector as separate comparison modes. Run 90 confirmed the final standalone mode at native 4K with 17.83 s room readiness and a 444 ms first full draw. The first ten seconds still had intervals up to 556 ms.

## Codex Micro multi-draw

Runs 85–86 on a matched native 4K desk build used `--warm-ferry --repeat-desk --draw-calls --gpu-timing`. The trial reduced up to 62 indexed Codex Micro surfaces to nine native multi-draw calls. Multi-draw was active on 974 of 1,583 sampled frames. Median indexed calls across the room fell from 1,044 to 1,023. Submission FPS moved from 133.41 to 131.84, both at 13.9 ms interval P95. Main-color GPU P95 increased from 6.74 to 7.00 ms. The trial's first-turn maximum reached 2.01 s and rear readiness moved from 18.30 to 22.58 s in this pair. The renderer trial was removed and the draw-call probe remains available.

## Native low rectangular-light field

Runs 87–88 used native 1080p UHD 770 with lean lighting, matte surfaces, window scissor and depth prefill. The trial used a Web Worker to tabulate diffuse form factors for two fixed rectangle lights and transferred a 1.27 MiB field. The worker completed at 3.29 s and the texture uploaded at the first full render. The matched 18-query GPU P95 values were 39.88 and 39.65 ms. Warm submissions were 25.23 and 25.38 FPS, at 124.9 and 125.0 ms interval P99. Rear readiness moved from 13.62 to 14.03 s. The trial was removed after the small measured difference. The worker asset, raw samples and native stills remain with the trial build.

## Long desk replay and physical display clock

Runs 91–92 used the same high-quality build, RTX 4090, cold startup, ferry prewarming and a prime turn followed by 60 seconds of motion. Both default and main-color targets used the requested native resolution with 4× MSAA on the main target. Draw and triangle counts matched at the sampled ending pose. These runs measure one route's room submissions and GPU work.

| RTX 4090 mode      | Warm submission rate | Submission P95 / P99 | Main-color GPU P95 | Initial room readiness |
| ------------------ | -------------------: | -------------------: | -----------------: | ---------------------: |
| Native 2560 × 1440 |           134.58 FPS |       13.9 / 13.9 ms |            7.75 ms |                18.52 s |
| Native 3840 × 2160 |           132.93 FPS |       13.9 / 13.9 ms |            6.81 ms |                18.57 s |

Both warmed visits had a 27.8 ms maximum interval. Their prime turns still had 521 and 486 ms maxima. One matched pair offers a development comparator and similar steady cadence at both resolutions. Physical presentation remains an acceptance requirement.

Run 139 profiled a 15-second warmed native 4K desk turn on RTX 4090. Revision `c76ac06` used the StudioView bundle with SHA-256 prefix `d0e162b6`, native main-color resolution and 4× MSAA. It submitted 136.20 FPS with 13.8 ms interval P95 and 7.9 ms primary CPU submission P95. V8 samples concentrated in Three's material program selection, uniform upload and draw submission. That profile includes possible graphics-driver waits. Repeat without the sampler for throughput and correlate with GPU timings before attributing missed refreshes to any one CPU operation.

Windows `QueryDisplayConfig` reported one active `DISPLAY1` on the RTX 4090 at 3840 × 2160 progressive. The target path and active signal both report 143999/1000 Hz. The installed PresentMon provides an absolute performance-counter clock. `studio-present.mjs capture --qpc-ms` records that mode and `analyze --qpc-ms` reads its millisecond `QPCTime` field. Use seconds on `--start`, matching the converted absolute clock. Model captures validated both parsers at 60 FPS with dropped rows retained. A headed session with a calibrated canvas witness is still required to identify distinct displayed scene frames.

`--present-witness` enables a canvas marker at top-left physical pixel (32, 32) in the fully graded room frame. Its 160 × 4 pixels contain a synchronization byte, 24-bit frame serial and CRC-8. The draw runs only when there is a completed render to the full default framebuffer. The marker module loads on demand and restores the prior clear state. Run 99 verified the exact black and white cells in a native 4K screenshot and decoded `D7 00 04 5C 68`, serial 1116 with a matching CRC. For a headed calibration, first confirm the fullscreen canvas maps to the selected display and the marker region has no overlay. Test rendered and frozen-canvas intervals before correlating the DXGI witness and PresentMon on their common QPC clock.

## Native low window motion

Runs 93–94 paired native UHD 770 1080p with lean lighting, matte surfaces, window scissor and depth prefill. `--window-only-water` keeps the static waterfront in ordinary low-quality room views and selects the already prepared animation on entry to a close window view. The water clock and ferry visibility follow that choice. The regression covers exit, reentry, reduced motion and quality changes.

Warm desk submissions changed from 25.09 to 25.75 FPS. Interval P95 stayed near 49 ms and P99 was 124.9 ms in both runs. The largest interval fell from 263.9 to 131.9 ms in this pair. Inclusive GPU P95 was 40.01 and 40.61 ms. Whole-room readiness was 13.79 and 14.76 s. The native low 30 FPS desk gate remains open. In a separate eight-second close-window smoke, run 95 submitted 39.76 FPS with GPU P95 of 24.42 ms.

Reversing the order in runs 100–101 reproduced the direction. The window-only visit submitted 25.77 FPS with a 125.1 ms maximum and GPU P95 of 40.23 ms. The control with water motion in the desk view submitted 25.17 FPS with a 270.9 ms maximum and GPU P95 of 39.69 ms. Keep this option for the worst-interval improvement on the measured desk route. Sustained GPU cost still exceeds the 30 FPS budget.

## First-drag texture priority

Runs 96–98 used the same native 4K build and stock shader warmup. `--input-priority-textures` keeps the initial preview, stages single texture uploads and holds them for 120 ms after the first frame. A viewport gesture extends the hold for 100 ms with a hard 350 ms cutoff from that frame. Cancellation clears the gesture extension.

| Texture strategy                                | Loader exit to changed submit | Pointer-down dispatch | First ten seconds P95 / max | Room readiness |
| ----------------------------------------------- | ----------------------------: | --------------------: | --------------------------: | -------------: |
| Default                                         |                        724 ms |                358 ms |                278 / 528 ms |        18.19 s |
| One staged upload per frame                     |                        177 ms |                 26 ms |                444 / 715 ms |        18.50 s |
| One staged upload per frame with input priority |                        175 ms |                 24 ms |                382 / 403 ms |        18.08 s |

The first response was earlier on both staged variants. The gesture hold improved the longest interval over plain staging in this pair and the remaining frame distribution kept the candidate optional. The first press overlapped 262 ms of logged texture upload in the control and about 15 ms on both variants. Compare using `4k --startup --full-room --texture-uploads`.

The first full-shading render without catch-up still took about 3.1 seconds in all three visits, after the first-input window. Report that span independently from the first ten seconds of interactive preview.

With catch-up enabled in both desk runs 102–103, adding the input hold changed the first response from 176 to 177 ms, whole-room readiness from 15.57 to 15.83 s and first-input P95 from 361 to 375 ms. The maximum interval moved from 521 to 438 ms. A separate run 104 turned directly toward the workbench with the combined options. It submitted the first changed view in 176 ms, reached whole-room readiness at 15.76 s and finished the first full draw in 130 ms. Its first-input maximum was 778 ms. Keep the combination experimental until the remaining preview stalls are reduced.

Run 104's 777.8 ms frame gap occurred during catch-up shading. The 777 ms main-thread task contained a 608.6 ms `texSubImage2D` call for `world-atlas.webp` at 2880 × 1620 and a 50.4 ms call for a 2048 × 1280 ImageBitmap. These wall times can include conversion, transfer and driver wait. A profiled repeat (run 105) had a 375 ms maximum instead. Report the attribution to the original observed outlier and use repeated trials to check a fix. Profile metadata now retains individual texture upload events as well as their count.

Runs 108–109 used the same native 4K workbench startup with catch-up and input-priority textures. `--atlas-detail-on-inspect` keeps the existing 960 × 540 room-scale map on the wall and requests the 2880 × 1620 atlas upon explicit inspection. In the ordinary route the option skipped the 880,194-byte atlas request and retained the 53,330-byte room asset. The control logged a 427 ms full-atlas upload and the candidate logged a 67 ms room-map upload. First-response time was 185 and 176 ms, room readiness 15.85 and 15.73 s, and the first-input maximum 639 and 472 ms. Interval P95 rose from 243 to 299 ms, so keep the mode optional. A native Chrome smoke verified zero ordinary-view requests, a single detail request, and cached detail application upon reopening.

The reversed pair 110–111 again skipped the full atlas request on the ordinary route. Its largest atlas upload calls were 11 ms for the room asset and 190 ms for the full asset respectively. The overall maximum interval was 507 ms with inspection-only detail and 410 ms with regular promotion. This pair leaves the maximum-frame-time improvement unconfirmed across visits.

## Startup spans and worker recheck

`--startup-spans` records long calls to renderer compile, texture initialization and render during loading and the first ten seconds after input. Times are CPU wall spans, including any blocking inside WebGL and driver calls. Run 112 used the existing atlas, first-input and catch-up options. The 590 ms workbench input gap overlapped a 401 ms preview-room render, a 126 ms compile on the native-size target and a 42 ms texture initialization. The texture call included a 512 × 640 ImageBitmap transfer of 41 ms. Image priority removed one recurring source of work. Render and shader preparation remain substantial in the same route.

The same-build runs 112–114 compared no worker flag, the BPK worker and the Meshopt worker independently. The worker marks confirm each selected path ran. First changed submit was 177, 179 and 176 ms, room readiness was 15.68, 16.67 and 16.43 s and post-input interval P95 was 278, 313 and 299 ms. BPK fetch-to-install was 55 ms in the control and 79 ms with its worker. This cold workbench comparison showed little first-response change with more time to full shading. Both worker implementations and their benchmark switches were removed.

## In-view preview texture order

`--in-view-preview-uploads` works with staged or input-priority preview textures. It selects the first pending map of a mesh in the current camera frustum and layers, respecting material groups and disabled frustum culling. It falls back to discovery order when no visible mesh has a pending map. The existing one-texture cap and gesture hold still apply. Runs 122–125 were cold native 4K RTX 4090 workbench turns on StudioView SHA-256 prefix `91a9a68a`, with input-priority textures, atlas detail on inspection and catch-up warmup.

| Run and order  | First change after loader | Room readiness | Post-input interval P95 / max |
| -------------- | ------------------------: | -------------: | ----------------------------: |
| 122, discovery |                  189.1 ms |        16.26 s |              305.5 / 465.3 ms |
| 123, in view   |                  177.6 ms |        16.32 s |              347.2 / 590.4 ms |
| 124, in view   |                  178.4 ms |        16.90 s |              361.2 / 624.9 ms |
| 125, discovery |                  196.0 ms |        16.62 s |              382.0 / 645.8 ms |

The in-view runs submitted the first change 11.5–17.6 ms earlier. Their ten-second tails had mixed results and readiness was slightly later in each neighboring comparison. Keep the option experimental. All four visits still had several long full-size preview calls and slow shader or texture preparation.

Build revision `4480221` with `npm run build`. Run the control and add `--in-view-preview-uploads` with a different run ID for the comparison.

```sh
node scripts/performance/studio-benchmark.mjs 4k 1 --startup --full-room --route=workbench --input-priority-textures --atlas-detail-on-inspect --catch-up-warmup --texture-uploads --startup-spans
```

The separate profiled run 121 recorded several long preview draws without a logged slow texture upload. During one 479 ms preview call, CPU samples landed at Three's framebuffer clear and uniform array serialization. The 528 ms gap in the same visit overlapped a separate 249 ms ImageBitmap upload and a 252 ms warmup compile. The profile also sampled garbage collection during the compile. The CPU sample attribution can include driver waits and scheduling. Record a matched shader or scheduling change independently from texture ordering.

## Shared preview uniforms

Runs 128–131 replayed the same 4K startup with in-view upload ordering. The trial placed the three preview lamp arrays and the grade curve into one 432-byte WebGL2 uniform block shared across preview materials. A WebGL fixture produced identical sample pixels for both shaders while changing lamp intensity and the room look. The tested StudioView SHA-256 began `acc89073`.

| Run and arrays  | First change after loader | Room readiness | Post-input interval P95 / max |
| --------------- | ------------------------: | -------------: | ----------------------------: |
| 128, standalone |                  174.3 ms |        15.56 s |              374.9 / 701.5 ms |
| 129, shared     |                  177.9 ms |        16.02 s |              319.4 / 479.2 ms |
| 130, shared     |                  183.3 ms |        16.18 s |              298.6 / 555.6 ms |
| 131, standalone |                  176.9 ms |        16.31 s |              243.0 / 381.9 ms |

The opposite-order pair reversed the frame-interval result. First change remained similar across all visits and full shading still took about 16 seconds. The shared block trial was removed.

## Isolated catch-up scheduling

`--isolated-catch-up` alternates interactive preview submissions with individual room-warmup steps. A warmup callback compiles a batch or one post-processing pass, reflects ready programs, or uploads one texture. The preview retains existing gesture-priority texture handling. Runs 132–133 and 135–136 compared the option against `--catch-up-warmup` on the same native 4K RTX 4090 workbench build with in-view uploads, gesture priority and detail on inspection. StudioView SHA-256 began `4bb38ba2`.

| Run and warmup | First change after loader | Room readiness | Post-input interval P95 / max |
| -------------- | ------------------------: | -------------: | ----------------------------: |
| 132, catch-up  |                  197.8 ms |        16.63 s |              326.4 / 500.1 ms |
| 133, isolated  |                  170.3 ms |        20.63 s |              201.3 / 548.5 ms |
| 135, isolated  |                  181.6 ms |        20.71 s |              166.7 / 451.3 ms |
| 136, catch-up  |                  183.3 ms |        16.32 s |              347.3 / 472.2 ms |

The isolated option lowered post-input P95 in both orders. Whole-room readiness took 4.0–4.4 seconds longer and the worst intervals remained over 450 ms. Native endpoint stills showed the same workbench, furnishings and lighting. Keep the option experimental while improving throughput when the view is idle.

### Shader and texture work during preparation

`--warmup-work` records program links and completion queries, renderer compile calls, texture initialization and GL texture-transfer calls. It separates phases at the existing startup marks and records the first draw that used each newly linked program during the first complete frame. The elapsed times are CPU wall spans and can include graphics-driver waits. Renderer compile and texture-initialization spans can contain the measured GL calls. A program's last completion observation is when the query observed readiness, so its elapsed time also includes polling and scheduling delay.

Runs 177–178 and 180–181 used one native 4K RTX 4090 build (StudioView SHA-256 prefix `55048674`) for the immediate workbench turn with isolated catch-up, gesture-priority textures, in-view upload order and atlas detail on inspection. `--resident-warmup-maps` skips versionless entries and ordinary 2D textures whose matching version is already resident in the renderer. It checks residency as the queue drains and preserves the order of pending uploads. Each isolated callback still starts at most one pending transfer. The reverse-order pair included startup spans and texture-upload logging in both visits.

| Run and isolated queue | Resident init calls | Other init calls | Room readiness | Move to changed submit | Post-input interval P95 / max |
| ---------------------- | ------------------: | ---------------: | -------------: | ---------------------: | ----------------------------: |
| 177, stock             |                 231 |              160 |        19.10 s |                63.7 ms |               76.5 / 194.6 ms |
| 178, skip resident     |                   4 |              160 |        16.43 s |                66.4 ms |               97.3 / 388.8 ms |
| 180, skip resident     |                   4 |              160 |        16.34 s |                60.6 ms |              104.2 / 493.0 ms |
| 181, stock             |                 231 |              160 |        19.23 s |                62.6 ms |               97.1 / 284.9 ms |

The counts cover the catch-up phase. The candidate eliminated 227 already-resident initialization calls in both orders and preserved 160 other calls. Whole-room readiness improved by 2.67–2.88 seconds. The first ten seconds had longer worst intervals in both comparisons. In run 180, the 493 ms interval contained a 17.5 ms room render and had no overlapping recorded long task. Keep the candidate opt-in while checking texture and preview scheduling under input.

Runs 247–248 repeated the cold native 4K workbench turn on build `ca18316f` with isolated catch-up, resident-map skipping, input-priority textures, in-view order and atlas detail on inspection. Immediate and 4.5-second delayed input reached whole-room readiness at 16.02 and 17.79 seconds, and submitted the changed view 62 and 167 ms after the pointer move. The respective first-input interval P95/max values were 83/444 and 76/1,111 ms. The catch-up phase took 13.46 and 15.49 seconds, with 159 and 171 nonresident initialization calls occupying 427 and 365 ms of combined CPU wall time. Initial full draws took 118 and 108 ms. The 1,111 ms interval contained a 20 ms preview render and no overlapping browser long task. Capture the independent animation callbacks to separate renderer scheduling from a delayed browser callback.

### Small texture groups during isolated preparation

`--small-warmup-maps` allows up to three small RGBA8 textures in one isolated preparation callback, with a 512 KiB estimate including mip levels and a 3 ms soft budget. Other transfers are submitted by themselves. The preview still alternates with preparation. Runs 251–254 used build `444c16a2` with the same settings above and measured the actual saved preparation slots from the batch marks.

| Run and input timing    | Whole room ready | Move to changed submit | First-input P95 / max | Prep slots saved |
| ----------------------- | ---------------: | ---------------------: | --------------------: | ---------------: |
| 251, immediate, control |          16.27 s |                  70 ms |           84 / 236 ms |                0 |
| 252, immediate, grouped |          16.42 s |                  59 ms |           83 / 201 ms |               14 |
| 253, delayed, grouped   |          16.81 s |                  56 ms |         49 / 1,173 ms |               21 |
| 254, delayed, control   |          17.65 s |                  35 ms |         69 / 1,153 ms |                0 |

The delayed grouped run shortened readiness by 846 ms and took 21 ms longer to submit the first changed frame. The immediate pair had similar pacing at a slightly later readiness. Leave the grouped option experimental while attributing the much larger interruption around rear assembly.

### Rear content timing during the workbench turn

`--startup-spans` records browser animation callback arrival times on a separate recorder after loader removal. In delayed runs 253–254, the longest scene intervals began 33–41 ms after rear readiness, with a single 18 ms recorded preview render and no overlapping browser long task in each interval. The independent callback gaps measured 1.15 and 1.13 seconds. The older delayed run 248 also had its 1.11-second scene gap begin 31 ms after rear readiness. This ties the blank section of the trace to missing browser callbacks around rear assembly, rather than to a renderer callback that chose to withhold a draw.

Runs 255–256 used the same `444c16a2` build with early rear loading and its existing changes to queue priority. The 4.5-second delayed run brought rear readiness from 7.42 to 3.64 seconds versus run 254, and the post-input maximum fell from 1,153 to 174 ms. Whole-room readiness improved from 17.65 to 16.93 seconds. On immediate input, with the camera already turned toward the workbench when rear content arrived, the maximum rose from 236 to 2,069 ms, and it again started 41 ms after rear readiness with no overlapping browser long task. This motivated an independent comparison of the early trigger with the existing queue priority.

Runs 257–259 compared the early idle trigger with original queue priority in build `290d818f`. In the delayed pair the trigger brought rear readiness from 7.40 to 2.56 seconds and whole-room readiness from 17.81 to 17.05 seconds. It changed the post-input P95/max from 49/2,069 to 42/153 ms, with move-to-submit changing from 65 to 93 ms. The immediate early-trigger run reached 16.19 seconds whole-room readiness and 76/229 ms post-input P95/max, close to the prior immediate control at 16.27 seconds and 84/236 ms. Neither early-trigger visit used the queue priority switch.

Runs 260–263 repeated the comparison on build `df199b52` with the usual high-quality startup schedule, without isolated preparation, staged textures or atlas changes. This version temporarily made the idle trigger the high-quality default. The explicit `--late-rear` comparison restored the ordinary later trigger.

| Run and input timing  | Rear ready | Whole room ready | Move to changed submit | First full draw | Newly linked programs in first full draw |
| --------------------- | ---------: | ---------------: | ---------------------: | --------------: | ---------------------------------------: |
| 260, delayed, late    |    11.15 s |          25.82 s |                  87 ms |         10.45 s |                                       21 |
| 261, delayed, early   |     3.75 s |          25.77 s |               5,558 ms |         10.37 s |                                       21 |
| 262, immediate, early |     3.44 s |          25.03 s |                   9 ms |         11.49 s |                                       22 |
| 263, immediate, late  |     3.45 s |          25.44 s |                  11 ms |         11.57 s |                                       22 |

In run 261, the move waited 5.21 seconds for event dispatch and 344 ms more for the changed submission after acceptance. The four visits' first full draws repeatedly linked 21–22 programs at the actual workbench view. Preserve the ordinary default and keep `--idle-rear` available for use alongside isolated preparation. Its favorable timing is conditional on the rest of the preparation schedule. The usual startup needs earlier preparation for the actual view before adopting the trigger.

### Progressive high-quality startup

The integrated path combines isolated view-dependent preparation, resident-map skipping, gesture-priority texture staging in view order and the idle rear trigger with original queue priority. It runs on high quality when parallel shader compilation and the floating-point beauty target are available. An explicitly selected shader warmup mode keeps its previous behavior. `--legacy-high-startup` selects the original startup schedule for comparison. `--progressive-high-startup` explicitly selects the integrated schedule.

Runs 264–265 first ran the equivalent switches individually on revision `8645257`, without the previous benchmark's atlas-on-inspection or ferry switches. Both loaded the ordinary 2880 × 1620 atlas and recorded its transfer. Immediate and delayed workbench turns reached whole-room readiness at 16.01 and 16.70 seconds with first full draws of 140 and 108 ms.

Runs 266–269 used the same native 4K high-quality build `f60ca9fc` in legacy, progressive, progressive, legacy order. Both schedules used the regular assets, including the full world atlas and travel photographs. No shader, browser or resource issues were recorded.

| Run and mode               | Whole room ready | Move to changed submit | First full draw | First-input P95 / max | New programs in first full draw |
| -------------------------- | ---------------: | ---------------------: | --------------: | --------------------: | ------------------------------: |
| 266, immediate, legacy     |          23.73 s |                  11 ms |         10.14 s |          232 / 393 ms |                              21 |
| 267, immediate, integrated |          16.26 s |                  61 ms |          123 ms |           77 / 207 ms |                               7 |
| 268, delayed, integrated   |          16.50 s |                  62 ms |          128 ms |           40 / 138 ms |                               7 |
| 269, delayed, legacy       |          25.26 s |                  75 ms |         10.30 s |         31 / 5,068 ms |                              21 |

The integrated schedule made the first immediate changed submission 50 ms later and reduced the following interval tail. In the delayed pair it removed the measured five-second interval. The first complete draw still links six shadow-depth programs and one output program. The full atlas transfer in the integrated visits was 91–94 ms and occurred within preparation. Promote this schedule together, since moving rear work alone regressed an initial turn in the older preparation path.

Runs 270–272 used the promoted default build `619f7924`. The cold desk turn in run 270 reached 16.22 seconds whole-room readiness and a 135 ms first full draw. The ordinary atlas request carried the same 880,194-byte image. Run 272 recorded 92 compositor screenshots and 61 changes during loading. The longest interval between visible changes including both loader boundaries was 263 ms.

The warm delayed workbench turns in runs 271 and 274 each revalidated 136 responses and reached whole-room readiness at 4.60 and 4.58 seconds, before the turn. They still took 3.03 and 3.63 seconds from the move to the changed submission, mostly waiting for input dispatch. Water-motion preparation started shortly before the position, press and move commands ran into long scene submissions. The recorded draws were in several regular scene materials, so the overlap alone does not attribute the delay to the water effect.

Runs 275–277 compared legacy startup, the progressive path with water preparation delayed six seconds, and progressive startup with ordinary water timing on one build `da18bd20`. The measured move-to-submission times were 1.61, 3.46 and 2.96 seconds. In the delayed-water test, input dispatch took 2.4 ms and the first changed beauty render blocked for 3.45 seconds before water preparation began. The workbench pegboard draw accounted for 3.39 seconds. Legacy startup itself recorded a 1.57-second workbench lamp draw. The delayed-water option was removed because it left a multi-second first response. These runs separate preparation for the initial visible scene from first use of materials in an area entered after that scene is already shaded.

Run 278 used the promoted default at `b29f539` and revalidated 136 requests. Its `--warmup-work` probe ended the `postReady` interval at the first changed submission. The whole room was ready at 4.47 seconds. Of the 3.51 seconds from the pointer move to the changed submission, 3.34 seconds elapsed before pointer dispatch. The changed view then took 174 ms. The pegboard draw took 114 ms in this run. The post-ready probe recorded no long uniform or texture lookup in that interval. First-use material preparation remains a candidate for the render-blocked variant; the longer input dispatch stalls have a separate unresolved cause. The stage closes with the progressive high-quality default and the prior native-low checkpoint. The delayed warm first turn, steady-frame tails and physical-presentation audit remain open.

Run 280 isolated first and repeat turns within a single page on the same native 4K build `619f7924`. The warm reload revalidated 136 responses. After the 4.5-second delay, the first workbench turn took 2.32 seconds from pointer move to changed beauty submission, including 2.09 seconds before dispatch. Two repeated turns took 14.3 and 14.6 ms. The three turns used the same pointer displacement, WebGL context and settled start/end camera poses. This session reproduced the first-turn delay and fast revisits. Repeat timing after changes to lighting, inspection mode or renderer lifetime remains unmeasured.

Runs 281–282 replayed warm native 4K first turns on the same build, requesting delays of 12 and 4.5 seconds from loader removal. Both revalidated 136 responses. The pointer move actually arrived 9.51 and 2.91 seconds after whole-room readiness. The longer-wait turn submitted the changed view in 28.7 ms, including 8.8 ms before input dispatch, and had a 27.7 ms maximum interval over the following ten seconds. The shorter-wait turn took 4.00 seconds, including 3.74 seconds before dispatch. Its maximum interval after input was 1.49 seconds. Water preparation had completed before the longer-wait move and was still pending at the shorter-wait move. This pair shows a fast first turn after a longer wait on this build. It does not establish a fixed safe wait or attribute the delay to the water effect.

Runs 285–286 compared the source of the warm first move, using build `619f7924`, matched drag displacement, viewport and workbench projection, and a timer deadline 4.5 seconds after loader removal. Each had a real pointer press before the deadline. Run 285 issued the move through Playwright after the page timer returned. Its timer was armed 4 ms after the deadline and woke 164 ms late. Run 286 armed the timer 178 ms before the deadline and dispatched the move synchronously within its callback, 443 ms late. With direct page dispatch the view took 1.91 seconds after input acceptance to submit, with an independent animation callback gap of 1.92 seconds. Deadline-to-changed submission was 2.50 and 2.36 seconds, respectively. The in-page replay isolated the move round trip from the observed wait. The underlying browser or rendering wait and the latency of physical mouse input remain unverified.

Runs 287–288 replayed the first turn toward the collection cabinet and workbench, respectively, after warm reloads on RTX 4090 at native 4K. Both used build `a95214b5`, requested a 4.5-second pause after loader removal and observed 136 HTTP revalidations. Both reached room readiness before the turn. The cabinet turn took 3,032 ms from move to changed submission, including 359 ms before dispatch. A 2,407 ms main room render occurred after input acceptance. The workbench turn took 783 ms, including 579 ms before dispatch. The actual moves began 12.48 and 14.01 seconds after loader removal, so this pair shows the stall can occur in either direction and does not rank the routes. The cabinet turn verifies the lens mount came into view and leaves the camera in room mode.

Run 289 measured the first close-up click with the same build and cache policy. Use `--warm --route=cabinet --cabinet-entry-timing --seconds=3`. This route waits for full shading, turns toward the cabinet and clicks the lens mount. The pointer release occurred 16.86 seconds after loader removal. It took 28.2 ms to dispatch and 51.7 ms to submit a changed camera frame. The largest frame gap around the click and during the 1.28-second transition sample was 43.3 ms. The following three seconds submitted 135.65 FPS at native 4K with 4× MSAA. This sample covers a click after the initial turn and does not establish the latency of an earlier click during startup.

Runs 290–293 compared the default schedule with a trial that moved the post-shading scene scan and paced shader and texture preparation after the visible frame. All four visits used the same native 4K build `34fcf460`, revalidated 136 responses and accepted the page-timed move after room readiness. With `--page-timed-input --input-delay-ms=4500 --startup-spans`, the benchmark uses a real pointer press and arms the page timer for the first move more than four seconds ahead of its deadline. The rAF gap column includes gaps overlapping the interval from room readiness through ten seconds after the move, including a gap that ends beyond the interval.

| Run and route                  | Timer wake lateness | Deadline to changed submit | Longest overlapping rAF gap | Longest main room render |
| ------------------------------ | ------------------: | -------------------------: | --------------------------: | -----------------------: |
| 290, cabinet default           |              738 ms |                   6,306 ms |                    5,802 ms |                 5,563 ms |
| 291, cabinet paced afterward   |               12 ms |                     972 ms |                   19,373 ms |                19,371 ms |
| 292, workbench paced afterward |                5 ms |                      13 ms |                    4,152 ms |                 4,151 ms |
| 293, workbench default         |              172 ms |                     723 ms |                    5,100 ms |                 5,095 ms |

The cabinet trial submitted its first changed frame sooner and stalled on a later room render for 19.37 seconds. The workbench trial still had a 4.15-second render span after its quick first response. The trial and its switch were removed. First-response timing must be paired with the longest callback gap and render span along the rest of the turn. Attribute the long room draws before trying preparation scoped to the actual workbench and cabinet sight lines.

Run 294 restored the default build `a95214b5` and repeated the timed warm cabinet turn with `--slow-draws --warmup-work --check-shaders`. The first changed submission took 6,250 ms from the accepted move. One 6,242 ms room render contained a 6,218 ms draw of `v-water`, the alpha-blended water surface inside the window-side KINTO LUNA vase. The draw used the native 3840 × 2160 4× MSAA beauty target and the same physical shader program as the vase glass. From room readiness through that submission, the longest recorded uniform count query took less than 0.1 ms, the largest texture transfer took 7.2 ms and the largest renderer compile took 30.4 ms. Measure the calls inside this draw to distinguish shader use, geometry binding and draw submission before changing the vase material or its appearance. The following cabinet glass draw took 51 ms.

Run 295 used the same build, input and probes with stock production shader checks. The first changed submission followed input acceptance by 6,294 ms. The `v-water` draw took 6,255 ms, of which 6,254 ms was inside the WebGL active-uniform count query for its linked program. This isolates blocking first-use program reflection on the cabinet route. With explicit shader checks in run 294, the wait occurred before the count query. A targeted preparation trial must also check when program reflection completes and measure callback gaps between preview, input and subsequent frames.

Runs 296–297 used the same build `b34c121b` with the default schedule and an experiment that moved the vase water material into progressive preparation on the actual beauty target. The first turn began after readiness in both visits. The default took 6,171 ms from synthetic move to changed submission, including a 6,070 ms vase water draw. The trial changed the view in 83 ms and reduced readiness from 4.36 to 4.28 seconds. The longest callback gap between loader removal and readiness was 145 ms before and 138 ms after. The next newly visible cabinet glass draw still took 5,565 ms, so first response alone would overstate the improvement. The startup `--warmup-work` probe now records from both readiness marks through ten seconds after the move, including a timed call that starts within that window. This exposes later first-use costs in the same turn.

Runs 298–299 used the same build `5ed20902`. Preparing the vase and cabinet panes moved the first visible turn from 5,773 to 28 ms after the move. The later cabinet draw still took 5,535 ms, of which 5,535 ms was inside uniform-count discovery. The program cache key identified the mapped physical cabinet finish with spotlight shading; this was the cabinet woodwork, rather than the pane material selected by the trial. The next candidate selects the mapped cabinet finish directly.

Run 300 switched the default replay to the workbench on build `5ed20902`. The first changed frame took 172 ms, and the longest post-ready animation gap was 4,511 ms. Slow draws included the Artemide clamp extrusion at 1,111 ms, the H3C printer spool web at 3,965 ms and the printer smoke panel at 416 ms. The largest uniform-count query lasted 3,965 ms.

Run 301 on build `ee9a9dee` prioritized these materials, the vase water and the cabinet oak. The workbench first response improved to 92 ms and the longest post-ready callback gap was 4,422 ms, with the printer linen surface draw taking 3,865 ms. Run 302 on build `ce2fdb71` included all printer body materials. It reached room readiness at 6.67 seconds with a 4,441 ms post-ready callback gap. The longest attributed draws moved to three separate surfaces of the printed figure. The experiments and their switches were removed. The workbench replay requires preparation that covers the view along the actual turn, including asynchronously mounted model materials.

Runs 179 and 182 measured the default warmup in an immediate native 1080p UHD 770 desk turn on the same build. The shader phase took 9.25 and 8.50 seconds. The 14,890 and 12,999 completion queries occupied 25.8 and 115.3 ms of CPU wall time. In run 179 the last program link started 6.14 seconds into the phase and the last readiness observation was at 9.25 seconds. The query time alone offers little scope for a seconds-scale improvement.

The first full draw in run 182 took 1.58 seconds. Two newly linked programs explain most of the long render: the Astro Mondrian workbench lamp's graphite aluminium took 679 ms, and the SELPHY postcard image took 859 ms. The run logged three newly linked programs during that full draw. The lamp's bounding sphere is outside the initial warmup scan at the eased yaw reached when preparation begins. The 96-pixel input brings it into the frustum before the full draw.

Run 183 added the existing `--warm-workbench` and cut the first full draw to 634 ms. The lamp and postcard links were absent from that draw. The pegboard outside the scoped roots still took 586 ms on first use. Whole-room readiness moved from 13.45 to 13.26 seconds, and post-input interval P95 rose from 229.2 to 340.3 ms. Keep scoped preparation optional. Its shorter final draw tests the cause of the hitch, and moving that work into the existing queue still leaves long intervals during the first input.

### Reconciling the startup view

`--live-front-warmup` extends native low default warmup with the active camera frustum and detail revision. After the original front batches have been submitted, it checks for newly visible or changed geometry/material combinations while shader links are still in flight. It submits at most four candidates in one additional pending batch and checks the live view before the first complete draw. The original texture path, render target, light context and picking stay in use.

Runs 187–188 and 191–192 used one native 1080p UHD 770 build (StudioView SHA-256 prefix `97c23021`) for an immediate desk turn with lean lighting, matte finishes, window scissoring, window-only water and wide depth prefill. Each pair reversed the order of stock and live warmup.

| Run and front preparation | Whole room ready | First full draw | Newly linked PBR programs on that draw | First-input interval P95 / max |
| ------------------------- | ---------------: | --------------: | -------------------------------------: | -----------------------------: |
| 187, stock                |          20.24 s |        2,096 ms |                                      2 |               1,618 / 1,618 ms |
| 188, live                 |          18.90 s |          104 ms |                                      0 |               1,285 / 1,389 ms |
| 191, live                 |          18.34 s |          111 ms |                                      0 |               1,041 / 1,646 ms |
| 192, stock                |          20.23 s |        2,914 ms |                                      3 |               1,208 / 1,938 ms |

The lamp and postcard links left the first full draw in both orders. Whole-room readiness advanced 1.34–1.89 seconds. One separate full-screen grade program still linked at the transition. The first-input interval distributions contain only 18–22 samples and show long pauses on every visit. Keep live preparation optional until it passes the motion and cold/warm checks on further routes. The regression fixture exercises a camera change, a new mounted object and a material change while another batch is linking, and checks render-target restoration.

### Loader, first turn and lighting preparation

Runs 193–197 used the same native 1080p UHD 770 build (StudioView SHA-256 prefix `a032d999`) for desk input with wide prefill. The texture-order variant enabled gesture-priority preview uploads and in-view order on top of live-front warmup. Runs 196–197 used isolated catch-up with resident-map pruning and the same preview upload flags. The four-second delay applied to input after the existing loader removal.

| Run and preparation  | Input delay requested | Texture uploads overlapping press | Move to changed submit | Whole room ready | First-input interval P95 / max |
| -------------------- | --------------------: | --------------------------------: | ---------------------: | ---------------: | -----------------------------: |
| 193, live front      |                     0 |                          359.6 ms |                10.2 ms |          13.48 s |                 138.9 / 632 ms |
| 194, live and staged |                     0 |                           15.3 ms |                 464 ms |          12.74 s |               152.7 / 2,424 ms |
| 195, live and staged |                   4 s |                           23.7 ms |                89.7 ms |          12.68 s |                 243 / 2,222 ms |
| 196, isolated staged |                     0 |                           15.5 ms |               465.3 ms |          14.41 s |                97.4 / 270.8 ms |
| 197, isolated staged |                   4 s |                              0 ms |                  84 ms |          13.88 s |               145.8 / 708.4 ms |

On immediate staged runs 194 and 196 the move arrived during a 335–342 ms task with three draws to a 256 × 256 target. The two slowest draws were `PMREMEquirectangularToCubemap` and `PMREMGGXConvolution`, the initial reflection probe. The delayed routes avoided that first dispatch stall and still had later long intervals. Runs 198–200 replayed the live-front staged path at native 1080p in a single diagnostic build (StudioView SHA-256 prefix `0f3e19cc`) with shader checks enabled. The trial generated the same low-quality reflection probe while the loader was still attached. It moved the probe outside the first-input window. Loader removal moved from 2.51 to 2.66 seconds, the first changed view from 3.16 to 3.38 seconds, whole-room readiness from 13.23 to 13.37 seconds, and the longest first-input interval from 590 to 1,097 ms. Moving the whole synchronous probe to the loader offered no end-to-end gain in this pair. A separate opaque preview program discarded the unused cutoff check on eligible surfaces. With early reflection enabled in both runs, that variant showed a similar first response and a longer maximum interval (1,875 ms). Both trials were removed.

`--vitrine-timing` records fetch, unpack, GLTF parse, mesh setup, lighting and lens attachment for the rear collection cabinet. `body-end` uses the matching Resource Timing entry when available. Fetching and decompression can overlap, so `body-end` through `buffer-ready` measures the remaining work after network delivery. These spans target rear assembly tasks outside the render and texture instrumentation.

Run 203 verified these marks on native UHD 770 with staged preview and live-front preparation (StudioView SHA-256 prefix `b9d1f176`). Fetch start to response end was 255 ms, response end to unpacked buffer was 106 ms, parse spanned 818 ms, and mesh setup through mount took 3 ms after parse. The parse interval overlaps preview renders, shader preparation and browser long tasks. A CPU profile or scoped decode comparison is needed to distinguish GLTF/Meshopt/image work from the asynchronous waits before changing model scheduling.

The same-route CPU profile in run 204 sampled 294 stacks during the cabinet's 847 ms parse interval. Texture uploads, rendering and garbage collection appeared alongside Meshopt code. The longest separate first-input task lasted 1,873 ms. 541 of its 588 samples landed under Three's first-use uniform lookup at `getProgramParameter(ACTIVE_UNIFORMS)`. The containing room render took 1,746 ms. This is evidence of time inside the first-use WebGL call, including any driver wait. The cabinet parse had already completed.

Runs 205–207 used one native 1080p UHD 770 build (StudioView SHA-256 prefix `5983f424`) with live-front warming, input-priority staging and in-view uploads. The cabinet worker variant routed that model's Meshopt buffers through a worker, with the success mark confirming use. The preview depth variant applied a guarded non-color depth draw before 227 preview frames, excluding the initial picture. All three completed without browser or shader errors.

| Run and variant     | Cabinet parse wall time | Whole room ready | First-input interval P95 / max |
| ------------------- | ----------------------: | ---------------: | -----------------------------: |
| 205, control        |                1,078 ms |          12.53 s |               270.9 / 729.1 ms |
| 206, cabinet worker |                1,302 ms |          13.53 s |               173.6 / 826.4 ms |
| 207, preview depth  |                  826 ms |          13.35 s |               152.8 / 1,125 ms |

The variants improved interval P95 in this set while extending the worst interval and whole-room time. Both trials were removed. The CPU profile places the longest observed task at first-use GPU program reflection. Measure the draw and its program variant before considering more cabinet decode or preview fill-rate changes for the long tail.

### First-use program reflection

`--warmup-work` also times the uniform count and individual uniform lookups. Calls of at least 16 ms record the owning draw when one is active, including its object path and material type. Run 209 used the native 1080p `b9d1f176` build with live-front preparation and staged preview textures. The first tea vapor program spent 60 ms in its initial uniform count. A second tea program used during the shader-warm phase spent 827 ms in its first count. The first input window recorded a 917 ms maximum interval. Earlier runs 205–207 each attributed their longest preview render primarily to the tea vapor draw.

The vapor is an unlit `ShaderMaterial` and continues to render during the simplified preview. A scene warmup batch can select a second program with the full scene's light counts. The preview draw retains that program when the effect does not use lights, and its first uniform query can wait on the new link. Preserving the initialized program for this specific effect keeps the preview shader in use in the same direct native-low render context.

Runs 212–215 replayed the immediate native 1080p desk turn on the same `c76c8bbf` build in control, reuse, reuse, control order. Both control runs queried uniforms for a second tea program, taking 1,300 and 663 ms. The two reuse runs queried just the original tea program. All four visits completed without browser errors.

| Run and program handling | Whole room ready | First-input interval P95 / max |
| ------------------------ | ---------------: | -----------------------------: |
| 212, control             |          12.63 s |               277.8 / 1,438 ms |
| 213, reuse               |          12.46 s |                 194.3 / 375 ms |
| 214, reuse               |          12.96 s |                 201.5 / 340 ms |
| 215, control             |          12.74 s |               222.2 / 1,299 ms |

Native low now preserves the marked, initialized unlit effect program when the material version, tone mapping and output color space match the direct renderer. A new, stale or offscreen program still enters warmup. The vapor remains in the ordinary color render. `--legacy-tea-warmup` restores the earlier warmup behavior for comparison. Whole-room time stayed near 13 seconds, and several first-input intervals still exceeded the release budget.

The default native-low build `5aedcd90` completed the workbench startup in run 216 without browser or shader errors. Run 217 found one translucent tea vapor draw in each of three warmed desk inventory samples and submitted 28.80 FPS over six seconds. Both checks used native 1920 × 1080. They verify program preservation and continued drawing on the sampled routes.

Runs 218–220 tested a further idle-only tea vapor variant on build `1901a211`. This variant waited for initial shading, rear readiness and a quiet callback, then prepared the real direct-framebuffer tea program before revealing the vapor. The matched startup comparison with existing program reuse had 13.47/13.34 seconds room readiness and 361/1,549 ms maximum first-input intervals in control/trial order. The trial's longest interval occurred before the queued tea preparation started. In the separate warmed turn, preparation finished at 17.43 seconds and the vapor became visible at 32.20 seconds after the held turn ended. The trial was removed because the added scheduling did not produce a startup improvement in this comparison. Retain the measured program reuse and existing vapor rendering.

After the tea fix, the remaining long spans included warm preview geometry draws, the first reflection probe and texture transfers. The full atlas took 216 ms to upload in run 214 and 226 ms in run 218. Runs 221–222 replayed the same native UHD 770 build `5aedcd90` with staged textures and live-front preparation. The existing `--atlas-detail-on-inspect` removed the 880,194-byte ordinary-view atlas request and its 158 ms observed transfer. The 53,330-byte wall map remained. Whole-room readiness moved from 13.23 to 12.82 seconds. First-input interval P95/max moved from 153/340 to 222/354 ms, and the time from loader removal to the first changed view remained about 0.58 seconds. Keep on-inspection detail optional. This comparison removes the upload at issue and leaves other first-input spans to address.

Runs 210–211 used compositor screenshots of the loader on that same native 1080p build, with stock preview and `--warm-oled` respectively. Including the loader boundaries, the longest gaps between changed screenshots were 320 and 255 ms, while the main-thread callback gaps were 896 and 875 ms. Both visits had visible feedback within one second. Loader removal occurred at 2.37 and 2.23 seconds. OLED's first visible uniform query still took 367 and 281 ms, and the trial's OLED warm-end mark occurred just after loader removal. Repeat before changing the default OLED preparation order.

Runs 227–229 used the same native 1080p UHD 770 build, StudioView SHA-256 prefix `f22ffa9b`, with gesture-priority textures and in-view upload order. Each cold visit turned from the desk immediately after the loader. Live-front control reached whole-room readiness at 12.36 seconds, submitted a changed view 571 ms after the loader and recorded first-input interval P95/max of 243/521 ms. Separating original front shader batches from preview renders on alternating callbacks changed those measurements to 12.66 seconds, 610 ms and 118/465 ms. Intervals over 50 ms increased from 48 of 165 to 65 of 192. Texture preparation and other rendering still accumulated in the same intervals. The longest interval in the control included 372 ms of texture initialization and 131 ms of room rendering. The scheduling trial was removed.

Run 229 requested idle pre-linking for the reflection probe's equirectangular conversion. It recorded no pre-link activity marks, so its frame timings cannot establish an effect. The trial was removed. Resolve the early activation window before comparing an equivalent preparation path again.

### Front texture transfers and GPU backlog

The 372 ms initialization in run 227 was a 371.7 ms `texSubImage2D` for the 768 × 1024 Fanjingshan photo. It began one millisecond into its task, before the next preview render, consistent with the front material warmup's upload path. In runs 228 and 229 the same photo took 30.7 and 36.2 ms. The longest transfers shifted to a 448 × 1472 ImageBitmap used by a case light guide and a 414 × 558 ferry photo. The timing points to variable transfer or queue cost across textures.

Runs 238–240 used StudioView SHA-256 prefix `ea5945cf` for an immediate native UHD desk turn. The isolated trial ran a single nonresident front texture initialization between preview callbacks. The fenced trial used the same slots and checked a fence after the preceding preview with a zero timeout. If that preview had outstanding work, it waited for one more slot at most.

| Run and upload schedule | Whole room ready | Loader end to first changed submit | First-input P95 / max | Intervals over 50 ms |
| ----------------------- | ---------------: | ---------------------------------: | --------------------: | -------------------: |
| 238, control            |          12.29 s |                             587 ms |          243 / 792 ms |            40 of 167 |
| 239, isolated           |          12.03 s |                             578 ms |          208 / 493 ms |            53 of 173 |
| 240, fenced             |          12.25 s |                             574 ms |          167 / 396 ms |            54 of 179 |

The fenced trial recorded 3 ready polls, 62 deferred polls and 61 forced uploads after another timeout. It found the GPU still working after most previews. The isolated trials shortened the largest observed intervals in this set and increased the frequency of intervals over 50 ms. Both were removed. The results support testing the transfer itself and reducing preview work before imposing longer fence-based holds.

### Preview reflection conversion link

`--prelink-preview-reflections` submits Three.js's equirectangular conversion link through the native-low renderer's creation callback. It requires parallel compilation and a supported radiance target. It uses the generator that later performs the ordinary preview conversion, restores the render target and shadow settings, and does not issue the cubemap draws in advance. Runs 238 and 241–243 used build `ea5945cf` in control, prelink, prelink, control order. The `--slow-draws` probe records the first conversion and the submitted program identity.

| Run and link schedule | Initial conversion draw | Whole room ready | Loader end to first changed submit | First-input P95 / max |
| --------------------- | ----------------------: | ---------------: | ---------------------------------: | --------------------: |
| 238, control          |                233.4 ms |          12.29 s |                             587 ms |          243 / 792 ms |
| 241, prelink          |                  0.2 ms |          12.48 s |                             565 ms |          188 / 361 ms |
| 242, prelink          |                  0.3 ms |          12.43 s |                             557 ms |          146 / 396 ms |
| 243, control          |                238.4 ms |          12.27 s |                             583 ms |        250 / 1,764 ms |

Both trials submitted the matching program about 1.16 seconds before its first draw, with 1.4–1.5 ms from preparation start to submission. The first conversion no longer occupies hundreds of milliseconds. The full probe still includes GGX convolution, and other preview or transfer work still causes stalls. Whole-room readiness was 167–193 ms later in these pairs. Keep the prelink optional while evaluating the complete startup schedule.

## Idle-aware catch-up

`--idle-catch-up` keeps isolated preparation and permits up to three preparation frames before a quiet preview. It prioritizes the preview when 50 ms has elapsed since the preceding preview and restores alternating preparation and preview on input or visible movement. A single blocking render or warmup call can exceed that interval. Runs 140–143 used one native 4K RTX 4090 workbench build, StudioView SHA-256 prefix `ef5db8ab`. Each comparison used in-view uploads, gesture priority and detail on inspection.

| Run and warmup             | Move to changed submit | Room readiness | Post-input interval P95 / max |
| -------------------------- | ---------------------: | -------------: | ----------------------------: |
| 140, immediate isolated    |                62.1 ms |        19.29 s |              111.1 / 173.6 ms |
| 141, immediate idle        |                62.2 ms |        17.91 s |               83.4 / 187.5 ms |
| 142, 4.5 s delay, isolated |                92.3 ms |        20.92 s |              41.7 / 2076.3 ms |
| 143, 4.5 s delay, idle     |               125.5 ms |        18.81 s |              97.0 / 1041.5 ms |

The immediate moves arrived before shader preparation. The delayed moves arrived during it. Quiet preparation shortened readiness by 1.38 and 2.12 seconds, with slower delayed move response and a higher post-input P95 in the delayed pair.

Runs 150–151 reversed the delayed comparison on a second build, StudioView SHA-256 prefix `7ba66ee7`. The trial preserved one priority preview for the first actual camera, projection or scene-detail change after an unchanged press. The focused scheduler regression passed. Idle and fixed alternation finished at 21.50 and 21.87 seconds respectively. Move-to-changed submit was 98.9 and 92.1 ms, with interval P95 of 166.6 and 118.0 ms during the first ten seconds after input. Both moves arrived during preparation. The measured savings in readiness came with slower delayed input and worse pacing, so the idle scheduler was removed.

Runs 155–158 tested an opt-in native preview shader that skipped lighting for unlit materials and skipped desk-occlusion evaluation for zero-contribution spotlights. A WebGL fixture matched preview pixels with direct light, cloth, unlit materials and room grading. The RTX 4090 workbench trial used StudioView SHA-256 prefix `16f1bb5c` with isolated catch-up in both conditions. Immediate move-to-submit timings were 69.9 ms stock and 69.1 ms trial, with readiness at 26.75 and 27.25 seconds. With a 4.5-second input delay, move-to-submit was 147.7 ms stock and 539.3 ms trial, with readiness at 32.32 and 31.67 seconds. Both controls in this sweep took longer to reach readiness than earlier controls. The same-build comparison showed mixed readiness and a slower delayed response, so the trial was removed.

Runs 168–169 used a single native 4K workbench build (StudioView SHA-256 prefix `09a4a58c`) to compare the original Nikon grip samplers with one shared color texture. The two recorded 768 × 768 hardware-surface uploads of 21.8 and 20.8 ms became one upload of 20.3 ms. Room readiness was 19.53 and 19.50 seconds, move-to-submit was 58.6 and 71.8 ms, and post-input interval P95 was 83.3 and 83.4 ms. In this pair the removed upload did not translate into an overall readiness improvement. Sharing requires changing the thumb grip's wrap mode. The trial was removed.

## 4K post-processing attribution

`--gpu-downstream` adds a separate elapsed GPU query after each sampled high-quality main-color render and closes it after the final output draw. The sample includes ambient occlusion, denoise and output, while the main-color sample includes the render target resolve. Browser compositing and physical display need separate measurement.

Runs 146–147 compared the RGBA half-float ambient occlusion path with two single-channel half-float targets on the same native 4K RTX 4090 desk build and 4× MSAA. The trial reduced the two half-resolution color attachments from 31.64 MiB to 7.91 MiB of calculated storage. The WebGL fixture verified complete targets and matching pixel samples under matched denoise inputs. Downstream GPU P50/P95 was 1.27/1.58 ms in the reference (68 queries) and 1.26/1.66 ms in the trial (65 queries). Warm submission rates were 142.50 and 137.61 FPS over eight seconds. The measured benefit was confined to calculated attachment storage, so the shader trial was removed. The downstream benchmark remains available.

Run 152 sampled a 60-second warmed native 4K desk turn after a prime turn using `--warm-ferry --gpu-timing --gpu-downstream`. Revision `6cb5e1f` used StudioView SHA-256 prefix `9fe40ab2`, a 3840 × 2160 drawing buffer and a native-size 4× MSAA main target. The room submitted 134.82 FPS, interval P95/P99 of 13.9/13.9 ms and CPU main submission P95 of 7.8 ms. Main-color GPU P50/P95 was 5.82/6.75 ms and downstream GPU P50/P95 was 1.27/2.01 ms. The combined times for the 476 matching query pairs had P50/P95 of 7.18/8.26 ms. Actual presented cadence remains open.

`--sky-clear` uses the visible constant-color sky dome as the high-quality beauty clear color when the perspective camera and viewport satisfy the dome coverage and depth constraints. It restores the original scene state before the downstream passes. The WebGL comparison preserved color and packed depth with 4× MSAA. The native activation mark confirms the guarded path ran in run 160.

Runs 159–160 used the same native 4K desk build (StudioView SHA-256 prefix `16f1bb5c`) for eight seconds per warmed visit. Main-color GPU P95 was 19.58 ms stock and 15.89 ms with sky clear, CPU submission P95 was 19.3 and 17.1 ms, and warm submissions were 68.49 and 72.12 FPS. Run 163 replayed the unchanged production bundle from run 152 (StudioView SHA-256 prefix `9fe40ab2`) and also measured 70.43 FPS with CPU submission P95 of 19.8 ms. The slowdown reproduced on the older build. The cause remains open. Preserve the option for a rerun at the earlier cadence before using the result to estimate a 144 FPS benefit.

Run 164 made a 20-second warmed visit using that same older bundle and sampled NVIDIA telemetry at 500 ms intervals. The room submitted 70.55 FPS, CPU main submission P95 was 18.6 ms, main-color GPU P95 was 16.61 ms and downstream GPU P95 was 1.92 ms. The 39 telemetry rows in the measured time window report P0, 2,745 MHz graphics clock, 49–56 °C, 238–325 W under a 450 W power limit and 44–73% sampled GPU utilization. The GPU sustained its reported clock during the slowdown. These observations leave submission stalls and contention open for investigation.

`--wddm-luid=<high,low>` samples the selected Windows adapter during the steady route. Use the current boot's adapter LUID. The report records UTC time, dedicated adapter bytes and one utilization pair per 3D engine for the private Chrome GPU process and all other processes combined. Browser frame timestamps can be aligned using `timeOriginUnixMs`. The report also records collection errors or absent Chrome counters.

Run 176 replayed the same `9fe40ab2` bundle for 20 seconds with WDDM sampling, a native 3840 × 2160 drawing buffer and a native 4× MSAA main target. It submitted 141.20 FPS with interval P95/P99 of 7.0/13.9 ms. CPU submission P95 was 7.2 ms, main-color GPU P95 was 6.36 ms, and downstream GPU P95 was 1.48 ms. The 19 WDDM rows within the measured interval found one active 3D engine, with Chrome utilization of 71.8–99.8% (median 93.4%) and 0.3–2.6% from other processes. Dedicated adapter use was 5.28–5.33 GiB. The fast replay shows the earlier slowdown is intermittent. This visit did not capture WDDM during a slowdown. The 141.20 FPS figure counts browser submissions, and physical cadence still requires calibration.

Pairing same-frame query results by submission ordinal in run 176 gives 6.81/7.54 ms GPU P50/P95 across main and downstream draws. Views from center toward the tower accounted for 63 of the 67 paired samples above 6.94 ms and 55 of the 56 submission intervals above 10 ms. The view bands use replayed pointer motion, so the eased camera lags the commanded heading. Compare these bands on the next native 4K render change and measure physical presentation separately.

Room readiness on run 176 was 17.27 seconds. The room shader warm-up marks bracketed 13.13 seconds before the first full draw. The interval includes preparation and waiting between submitted work. Measure program link and readiness-poll counts before attributing its duration to repeated compilation or to actual compiler latency.

### Pose-matched 4K comparisons

GPU timing captures the primary frame index with every valid elapsed query and the actual camera yaw for every primary frame. `node scripts/performance/studio-view-timing.mjs BASELINE.json CANDIDATE.json` checks comparable native High desk runs, pairs main and downstream queries by index, and reports overall metrics and six fixed yaw bands. Negative yaw turns right toward the tower. The paired sums cover the measured passes, separate from browser composition and presentation.

Runs 184–186 used the same native 4K 4× MSAA build (StudioView SHA-256 prefix `6643401a`), a prime desk turn with ferry warmup and 14 seconds of measured motion. They ran stock, sky clear and stock in that order. Sky clear activated and the equivalent ending pose dropped from 519 to 518 draws. The three visits all ran in the slower regime.

| Run and draw mode | Warm submissions | CPU submission P95 | Paired GPU P50 / P95 | Paired GPU P95, yaw below −0.42 rad | Browser interval P95 / P99 |
| ----------------- | ---------------: | -----------------: | -------------------: | ----------------------------------: | -------------------------: |
| 184, stock        |        72.29 FPS |            17.8 ms |     13.67 / 17.96 ms |                            17.96 ms |             20.9 / 27.6 ms |
| 185, sky clear    |        71.96 FPS |            16.9 ms |     14.60 / 16.80 ms |                            18.01 ms |             21.0 / 27.6 ms |
| 186, stock        |        71.36 FPS |            17.2 ms |     14.87 / 17.67 ms |                            18.01 ms |             20.9 / 27.7 ms |

The paired sample counts were 60, 60 and 59 overall and 14, 14 and 15 in the far-right band. Sky clear lowered overall paired P95 in these visits while the far-right GPU tail and browser intervals stayed similar. Leave the comparison optional. Across the three visits, thirteen WDDM samples per measured route found Chrome 3D utilization medians of 37.2–39.5% and peaks for the combined other processes below 0.3%. This visit reproduced the slow regime with little competing work on the observed 3D engine. It leaves CPU submission, driver scheduling, other engines and compositor timing open.

Runs 201–202 made an adjacent same-host regression check at native 4K with 4× MSAA, ferry prewarm, one prime desk turn and ten seconds of measured motion. The older `9fe40ab2` and build `a032d999` from revision `9fde900` submitted 137.69 and 141.10 FPS respectively. The interval P95 was 7.1 and 7.0 ms, with P99 of 13.9 ms in both. This pair reproduced fast behavior on both bundles. Runs 164 and 176 already reproduced both speed regimes on `9fe40ab2` alone. A stable 144 FPS result and the reason for the intermittent slow regime remain open.

`--cpu-telemetry` adds Windows logical CPU parking, utility, performance and system queue length from browser launch onward. The report identifies processors by Windows group and index. Align its UTC timestamps with the browser time origin before comparing startup and steady windows. The counters describe host state and cannot identify the cores that ran Chrome threads.

Run 208 collected 51 complete CPU rows with all 24 logical processors on the native 4K `b9d1f176` build. The ten-second warmed turn submitted 141.10 FPS with 13.9 ms interval P99. The ten CPU rows within the measured route found 14–19 parked logical processors and a median system queue of zero. Nine aligned WDDM rows had a median Chrome 3D utilization of 92.5%. The fast visit verifies the collection path and shows that substantial parking can coexist with fast rendering. Capture the same counters during a slow replay before drawing a scheduling conclusion.

`--raf-control` closes the scene page after the recorded workload and timing queries finish. It then samples animation callbacks on a separate page in the same Chrome process for three seconds. The page animates a 4 × 4 CSS element without WebGL. This control measures the available browser animation cadence and keeps physical presentation as a separate measurement.

On the 143.999 Hz test output, run 223's completed blank-page control reported 144.00 callbacks per second and a 7.1 ms interval P99. The native 4K highest-quality scene on the same run submitted 140.90 FPS with interval P99 of 13.9 ms. This reproduces a browser cadence near the display refresh rate and occasional doubled intervals under scene load. Capture the control during a slow-regime visit as a further check on the intermittent 70–72 FPS results.

Runs 223–224 used the same native 4K 4× MSAA build `f0f6becd` for ten seconds of desk motion and GLSL checks. The trial skipped depth and normal work in neutral Poisson denoise neighborhoods. Downstream GPU P95 changed from 1.64 to 1.56 ms, while same-frame main-plus-downstream P95 moved from 7.66 to 7.72 ms across 83 and 82 pairs. In the far-right band its P95 moved from 7.57 to 7.81 ms. Warm submissions were 140.90 and 139.10 FPS. Both browser interval P99 values were 13.9 ms. Both blank-page controls retained 7.1 ms P99. The denoise trial was removed given the unchanged whole-frame result.

Run 233 repeated the desk route for 60 seconds after a prime turn, using production revision `f99d348` (StudioView SHA-256 prefix `71f63e04`). All 8,289 recorded main renders used 3840 × 2160 and a 4× MSAA main target. The room submitted 138.13 FPS, or 136.8–139.8 FPS in each ten-second segment. Submission interval P95/P99 was 7.1/13.9 ms. Of 8,288 intervals, 351 exceeded 10 ms and one exceeded 17 ms. CPU submission P95 was 7.7 ms. Main-color and downstream GPU P95 values were 6.56 and 1.71 ms in 488 pairs. The blank-page control submitted 144.00 animation callbacks per second with a 7.1 ms P99. The 58 aligned WDDM samples placed Chrome utilization at a 93.1% median with other processes peaking at 2.9% on the observed 3D engine. This replay cleared the tolerated average submission cadence and did not capture the earlier slow regime. Physical presentation and the remaining release routes still need measurement.

The same run recorded 348 of its 351 intervals over 10 ms between the desk center and right or near the center, at camera yaw below 0.21 radians. Paired GPU P95 reached 8.12–8.58 ms in those four bands and 6.81–7.10 ms in the two leftmost bands. This localizes the steady fast regime's remaining missed intervals while leaving the intermittent slowdown open.

Runs 249–250 compared the stock and zero-radiance directional shadow branch on build `1ba17e52` in 12-second warmed native 4K desk turns. The trial bypassed window-aperture evaluation, directional PCF and direct shading when the shadowed directional light's color was zero. The compiled material kept the same vertex code, resources and nonzero-light calculation. The visits completed without browser or shader errors.

| Run and mode | Warm submissions | Intervals over 10 ms | Main GPU P95 | Paired main + downstream GPU P95 | Paired P95, yaw below 0.21 rad |
| ------------ | ---------------: | -------------------: | -----------: | -------------------------------: | -----------------------------: |
| 249, stock   |       138.75 FPS |          62 of 1,664 |      6.46 ms |                          7.91 ms |                        7.99 ms |
| 250, branch  |       134.91 FPS |         104 of 1,617 |      7.12 ms |                          8.54 ms |                        8.49 ms |

The branch had 96 valid same-frame GPU pairs and the control had 98. Both had 67 pairs in the center and right bands. The trial was removed after its slower timings in this comparison.

### Native high beauty and resolve attribution

On the high path, `--gpu-color-passes` alternates inclusive GPU timing with three separate queries on the actual native-size 4× MSAA beauty target. The split starts at the first opaque color draw, transitions at the first blended or transmissive draw, and ends with the matching full-target color and depth resolve. The benchmark records unsupported targets, off-target or late draws, missing or multiple explicit resolves and disjoint queries. A missing explicit resolve produces no resolve timing.

Run 273 sampled a 20-second warmed native 4K desk turn on the promoted default build `619f7924`. All 75 split frames and explicit resolves passed the instrument's boundary checks. The separate timing distributions were as follows.

| Stage                  | GPU P50 | GPU P95 |
| ---------------------- | ------: | ------: |
| Inclusive main color   | 5.83 ms | 6.33 ms |
| Opaque color           | 5.37 ms | 5.91 ms |
| Translucent color      | 0.16 ms | 0.73 ms |
| 4× MSAA beauty resolve | 0.22 ms | 0.23 ms |
| Downstream AO/output   | 1.37 ms | 1.43 ms |

The run submitted 127.25 FPS. The same browser's unloaded control reached 128.30 callbacks per second. Preserve the native targets and separate the browser cadence from actual display timing before comparing this submission rate to the 144 Hz release target. The split measurements put most of the main GPU time in opaque color drawing.

### Native 4K rainy window

Run 284 measured 60 seconds of steady camera motion after entering the close-window view on the promoted default build `619f7924`. The cold visit used the night rain fixture and confirmed both the rain setting and window mode. The stock pane-center click timed out in run 283. In the measured run, the replay used the existing window interaction test's glass point, 0.166 m outside the west wall at height 1.42 m and room depth 0.85 m, and verified the window interaction cue before clicking. The initial view turned by 241 CSS pixels toward the window. The timing window began after close-window entry and the steady replay's two-second lead-in.

All 8,641 recorded main-color frames used a 3840 × 2160 drawing buffer and 4× MSAA beauty target. The 8,640 intervals yielded 144.00 submissions per second, P95/P99 of 7.0/7.1 ms and a 7.2 ms maximum. The same-process blank-page control measured 142.72 animation callbacks per second, with a 7.1 ms P99. Inclusive main-color GPU P95 was 3.91 ms and downstream P95 was 1.63 ms across 255 samples. The 254 valid split samples measured opaque, translucent and resolve P95 at 2.09, 1.06 and 0.80 ms respectively. No browser or shader errors were recorded. This covers a steady close-window rain route at native size. Physical presentation, entry latency and the broader release matrix are separate checks.

## UHD 770 desk GPU attribution

Runs 106–107 used native 1920 × 1080 with matte and lean lighting, scissor, window-only water and depth prefill. `--gpu-panorama` alternates whole main-color queries with queries around the panorama draw on separate frames. On the stock opaque order, GPU P95 was 39.64 ms inclusive and 0.98 ms for the panorama alone, with 14 samples each. The panorama query covers that single draw and its result is a sampled cost ceiling for savings on the photographed exterior, with other scene work still in the inclusive measurement. Near-first opaque sorting moved inclusive P95 to 40.74 ms and did not close the 30 FPS frame budget gap. It remains a benchmark diagnostic.

An architectural lighting trial approximated diffuse light from small or distant rectangular emitters on plaster and floor surfaces. It blended near or significant contributions back to the existing matte calculation. Run 116 used a malformed shader directive and rendered the plaster black. Exclude its timings from evaluation. After correcting the directive, runs 119–120 compared the trial and matte under native 1080p on UHD 770 with lean lighting, window scissor, window-only water and depth prefill. The ending view used 1,139 draws and 1,544,136 triangles in each run. The trial restored plaster lighting in the native screenshot and passed a WebGL fixture comparing pixels under a distant rectangular light.

| Room lighting | Warm submission rate | Submission P95 / P99 | Main-color GPU P95 | Room readiness |
| ------------- | -------------------: | -------------------: | -----------------: | -------------: |
| Matte         |            26.05 FPS |        48.6 / 125 ms |           40.29 ms |        13.45 s |
| Architecture  |            26.13 FPS |        42 / 124.9 ms |           39.69 ms |        13.48 s |

The GPU difference was 0.60 ms with 16 timer samples per run. Near-identical submission rates and P99 intervals leave the 30 FPS goal open. The trial was removed from the scene code.

Runs 126–127 compared stock transparent lighting with exact direct-light culling on the window pane and two outer PC glass materials. Both used the same UHD 770 native 1080p build and matched lean, matte, scissor, depth-prefill and window-only water settings. The candidate kept the authored glass shading and preserved the window and PC in the endpoint screenshots. Both poses showed 1,139 draws and 1,544,136 triangles. Warm submissions changed from 25.96 to 26.37 FPS and main-color GPU P50/P95 from 36.38/40.58 to 36.55/39.68 ms (16 timer samples each). Room readiness increased from 13.36 to 14.67 s and interval P99 from 118 to 125 ms. The trial was removed given the small steady difference and slower readiness in this pair.

Runs 137–138 tested matte lighting and more compact diffuse light loops on selected rough walls, millwork and backings. The trial kept the regular renderer, authored textures, weather and occlusion. Desktop, floor, text, transparent panes and authored material hooks used the prior path. The two native 1080p UHD 770 replays had 1,139 draws and 1,544,136 triangles at the ending pose. Warm submissions moved from 26.16 to 26.52 FPS, GPU P50/P95 from 37.46/40.38 to 35.05/38.90 ms, and room readiness from 13.92 to 14.10 seconds. Each run had 16 GPU samples. The two desk stills show similar lighting on the visible walls and preserved main props. The small cadence gain leaves the 30 FPS goal open. The trial was removed.

## Wide depth prefill

`--wide-depth-prefill` expands depth-only coverage using existing opaque geometry whose material hooks preserve vertex positions. It ranks selected meshes by their clipped camera footprint and geometry cost. The pass restores layers and ordering before regular color rendering. Transparency, authored vertex positioning, overlays, and near-plane intersections are excluded. The mode uses the same native low room path as `--depth-prefill`.

| Pair and mode     | Warm submissions | Inclusive GPU P95 | Valid queries | Submission P95 / P99 | Room readiness |
| ----------------- | ---------------: | ----------------: | ------------: | -------------------: | -------------: |
| 144, coarse, 8 s  |        26.87 FPS |          39.93 ms |            13 |      42.1 / 118.1 ms |        13.05 s |
| 145, wide, 8 s    |        28.73 FPS |          34.68 ms |            14 |      41.9 / 111.1 ms |        13.03 s |
| 148, wide, 20 s   |        28.28 FPS |          34.67 ms |            34 |      41.9 / 111.0 ms |        14.17 s |
| 149, coarse, 20 s |        26.05 FPS |          40.05 ms |            31 |      48.7 / 124.9 ms |        14.51 s |

Runs 144–145 used StudioView SHA-256 prefix `ef5db8ab`. Reversed runs 148–149 used prefix `7ba66ee7`. Both pairs used native 1920 × 1080, matte and lean lighting, window scissor and window-only water. The desk stills preserve the principal surfaces, screen and PC glass. The timed query includes depth and main color draws. The 20-second runs recorded a median of 96 prefill draws and 69,896 triangles for wide, and 18 draws and 9,878 triangles for coarse. Keep wide available while measuring depth-only cost and extending visual and motion coverage. Submission pacing and physical presentation remain open for the native 30 FPS gate.

`--gpu-depth-prepass` alternates each inclusive GPU sample with separate sequential measurements of the depth draw and the following color render. Timers start inside the renderer after the depth pass's explicit clear. Runs 153–154 used one native 1080p desk build (StudioView SHA-256 prefix `032af0d4`) for 20 seconds per warmed visit. The trial changed the depth order to near-to-far after selecting the same meshes. Both modes used a median of 96 prefill draws and 69,896 triangles.

| Mode        | Depth-only P50 / P95 | Color after depth P50 / P95 | Inclusive P50 / P95 | Warm submissions | Submission P95 / P99 |
| ----------- | -------------------: | --------------------------: | ------------------: | ---------------: | -------------------: |
| Wide        |       0.28 / 0.40 ms |            32.70 / 41.07 ms |    34.02 / 35.40 ms |        28.15 FPS |      55.1 / 111.1 ms |
| Near-to-far |       0.26 / 0.33 ms |            33.08 / 35.24 ms |    33.83 / 34.73 ms |        28.34 FPS |      62.1 / 111.0 ms |

The depth draw accounts for less than half a millisecond at P95 in both visits. The near-to-far trial was removed given the small cadence change and higher interval P95. The split timer remains available for testing additional coverage and identifying the cost of the following color pass. Stage percentiles use separate sample distributions.

Runs 161–162 increased the wide draw limit from 96 to 160 while keeping the 96,000 triangle budget and candidate order. The same native 1080p build, StudioView SHA-256 prefix `72ed4024`, used 12 seconds per warmed desk visit. The median prefill grew from 96 draws and 69,435 triangles to 149 draws and 95,897 triangles. Depth GPU P50 rose from 0.28 to 0.34 ms, color-after-depth GPU P50 stayed at about 32.25 ms, and warm submission rate rose from 27.85 to 27.93 FPS. CPU submission P95 was 30.2 and 34.5 ms, above the earlier controls in both visits. The higher limit was removed. Concentrate on reducing visible color work and submission latency.

### Opaque and translucent draws

`--gpu-color-passes` alternates inclusive GPU timings with separate elapsed queries for opaque and translucent default-framebuffer render calls after depth prefill. The opaque query begins at the first color draw. The translucent query begins at the first blended or transmissive material and ends with the room render. The benchmark records sampled offscreen or late opaque draws to validate the boundary.

Run 165 used the production bundle from `ced4278` (StudioView SHA-256 prefix `6d1c7816`) for a 12-second warmed native UHD 770 desk turn with wide depth prefill. The ten split frames had zero offscreen or late opaque draws, a median of 1,069 opaque color draws and 58 translucent color draws. GPU P50 was 31.89 ms for opaque and 1.17 ms for translucent. Inclusive GPU P50/P95 was 34.21/34.74 ms from ten alternating samples. The room submitted 28.20 FPS. The measured cost supports prioritizing opaque shading and lowering the number of draws before tuning glass or depth further.

Runs 225–226 used the same native 1080p UHD 770 low build, StudioView SHA-256 prefix `5aedcd90`, with matte and lean lighting, window scissor, window-only water and wide depth prefill. The repeated desk turn lasted 60 seconds and the workbench route lasted 15 seconds. Both visits checked shader compilation and completed without browser errors.

| Route                    | Warm submissions | Submission P95 / P99 | Opaque GPU P50 | Main-color GPU P95 | Intervals over 66.67 ms |
| ------------------------ | ---------------: | -------------------: | -------------: | -----------------: | ----------------------: |
| 225, 60-second desk      |        28.34 FPS |      62.5 / 111.1 ms |       31.10 ms |           34.92 ms |             78 of 1,700 |
| 226, 15-second workbench |        33.78 FPS |       35.3 / 62.5 ms |       25.35 ms |           31.25 ms |                1 of 505 |

The desk is 0.16 FPS below the tolerated average cadence even at the browser submission layer. The main-color samples placed 1,065 median opaque draws at the desk and 217 at the workbench. The desk visit had 42 submission gaps of at least 90 ms. Their clustering at roughly one-second intervals suggests a separate periodic cost alongside the sustained opaque pass. The blank-page control after the desk run reached 143.73 callbacks per second.

### PC display updates

Runs 230–232 repeated the native 1080p desk turn for 20 seconds each on the same build, StudioView SHA-256 prefix `56e6735f`, in control, frozen, control order. `--static-pc-telemetry` keeps the initial readings and suppresses later canvas changes for the PC power and cooler displays on the direct native-low path. The activation mark confirms the freeze in run 231. The three visits completed without browser errors.

| Run and display mode | Warm submissions | Submission P95 / P99 | Intervals at least 90 ms | Intervals over 66.67 ms |
| -------------------- | ---------------: | -------------------: | -----------------------: | ----------------------: |
| 230, control         |        28.46 FPS |      62.5 / 111.1 ms |                       15 |               23 of 568 |
| 231, frozen          |        28.63 FPS |       42.0 / 76.4 ms |                        0 |               11 of 572 |
| 232, control         |        28.40 FPS |      62.3 / 111.1 ms |                       14 |               24 of 565 |

The intervention isolated a contributor to the longest intervals and left opaque GPU P50 at 31.26–31.65 ms across the visits. The synchronous texture probe recorded no canvas transfer of at least 10 ms. It does not measure asynchronous driver work or mipmap generation. Keep the freeze as a diagnostic.

Runs 234–237 compared the original CanvasTexture transfer and a typed RGBA8 transfer on the same StudioView build `46d6744a`. The typed path reads the existing two canvases only when their power or temperature reading changes. It reuses the typed backing buffer and keeps the same sRGB interpretation, alpha, filtering and generated mipmaps. The updates follow the same integer-second clock.

| Run and display mode | Warm submissions | Submission P95 / P99 | Intervals at least 90 ms | Intervals over 66.67 ms |
| -------------------- | ---------------: | -------------------: | -----------------------: | ----------------------: |
| 234, canvas, 20 s    |        28.39 FPS |      62.5 / 111.1 ms |                       13 |               26 of 567 |
| 235, typed, 20 s     |        28.61 FPS |       42.1 / 69.6 ms |                        0 |               12 of 571 |
| 236, typed, 60 s     |        28.58 FPS |       42.2 / 76.4 ms |                        1 |             34 of 1,714 |
| 237, canvas, 20 s    |        28.47 FPS |      42.9 / 111.1 ms |                       15 |               23 of 568 |

All visits used native 1080p on UHD 770 with the same desk turn, lighting and depth options. The typed visits retained live readings, removed the observed clustering at one-second intervals and completed shader checks without errors. Run 236 submitted at 28.5–28.7 FPS in each ten-second segment. Its remaining 1.98% of intervals over twice the nominal frame budget still exceed the proposed steady-state limit. Use `--canvas-pc-telemetry` to replay the original upload path against the native-low default.

Run 244 exercised the case inspection in the final build `ca18316f` with typed uploads enabled by the native-low default. It entered case mode with no browser or shader errors and rendered at native 1920 × 1080. The 15-second route submitted 23.06 FPS, with a 48.9/49.2 ms P95/P99 and no intervals over 50 ms. This route remains below the mean target. The WebGL pixel fixture covers the two source dimensions, full and minified samples, orientation, alpha and an updated reading on the same typed texture.

The same build's 12-second case attribution in run 245 measured main-color GPU P50 of 42.47 ms and split opaque/translucent GPU P50 of 38.30/3.47 ms. Run 246 submitted 22.86 FPS with 7.6 ms CPU submission P95. Native-low work is paused at this checkpoint. Current development prioritizes whole-room startup, first input and native 4K frame pacing.

### Opaque shader experiments

An opt-in opaque shader trial shared receiver-side LTC setup across multiple rectangle lights. Run 167 used a shader with a scalar clearcoat argument passed to a vector parameter. Its missing screen and other missing clearcoat surfaces invalidate the timing result. The corrected shader passed an offscreen WebGL pixel comparison using the stock rectangle-light lookup tables. Native run 170 verified the paths with `--check-shaders`, which enables compilation diagnostics in production builds, and its screenshot showed the restored screen and clearcoat objects.

Runs 170–171 compared the corrected trial and stock on the same native 1080p wide-prefill desk build (StudioView SHA-256 prefix `01b032c5`) for 20 seconds per warmed visit. Opaque GPU P50 was 31.49 and 31.40 ms, inclusive GPU P95 was 36.19 and 34.81 ms, and warm submissions were 28.56 and 28.43 FPS respectively. Both measured submission interval P95/P99 of 62.5/111.1 ms. Each visit had 17 valid inclusive samples. The trial was removed. Keep the pass attribution and compilation diagnostics for the next changes to visible opaque workload.

### Main-color draw inventory

`--draw-inventory` records object names, material identity, submissions and triangles from up to three main-color frames during the measured route. The capture excludes the depth prefill and other render targets. Use GPU timing separately because collecting the inventory adds CPU work to the captured frames.

Run 172 sampled a warmed, native 1920 × 1080 UHD 770 desk turn on the wide-prefill build (StudioView SHA-256 prefix `6d1c7816`). The three poses contained 1,069–1,113 opaque and 58–70 translucent draws. The tower contributed 272 opaque draws and 727,871 triangles in all three poses. The motherboard alone contributed 58 draws and 77,126 triangles in the middle sample. The bookcase submitted 196 opaque draws throughout, and the travel photos submitted 142–154. At the middle pose, the tower contributed about half of the 1.47 million opaque triangles. These counts locate the geometry and submission work. The opaque GPU timings also include pixel shading, and draw counts alone cannot rank individual objects by GPU time.

Runs 173–175 compared stock wide prefill with two trials on a single build (StudioView SHA-256 prefix `6966607d`). Each measured a 12-second warmed native 1080p desk turn with GLSL diagnostics and ten inclusive GPU samples. The secondary shader omitted direct specular on selected rough finishes at ordinary room distance and added five compiled variants. The motherboard batching trial reused the same materials and current low-room indices. It merged 35 eligible surfaces into nine proxies while preserving the original meshes for picking and inspection.

| Run and mode      | Median opaque draws | Opaque GPU P50 | Inclusive GPU P95 | Warm submissions | Submission P95 / P99 | Room readiness |
| ----------------- | ------------------: | -------------: | ----------------: | ---------------: | -------------------: | -------------: |
| 173, stock        |               1,070 |       32.05 ms |          34.66 ms |        28.07 FPS |      62.5 / 111.1 ms |        13.24 s |
| 174, diffuse trim |               1,069 |       31.51 ms |          34.31 ms |        28.28 FPS |      62.4 / 104.2 ms |        14.15 s |
| 175, merged board |               1,043 |       31.57 ms |          35.43 ms |        28.11 FPS |      62.5 / 110.6 ms |        13.31 s |

All three visits completed without browser or shader errors. The changes had little effect on cadence or its long intervals. Room readiness was later in the diffuse trial, concurrent with the additional shader variants. Both trials were removed. A larger reduction in visible color work or a reduction in first-use program work remains an open direction.

### Low-quality screen grade

`--gpu-low-grade` adds an elapsed GPU query for the non-neutral low path's native framebuffer copy and full-screen grade quad on the same sampled frames as the main-color query. It uses the copied texture to identify the grade draw. Runs 189–190 compared the existing curve calculation with evaluating only the active segment for each color channel. Both used the same native 1080p UHD 770 wide-prefill build (StudioView SHA-256 prefix `97c23021`), a prime desk turn and 20 pairs of valid GPU queries. Both ran without shader compile errors.

Grade GPU P50/P95 went from 1.21/1.28 to 1.04/1.13 ms. Main-color GPU P95 was 34.90 and 35.01 ms. Warm submission rates were 27.92 and 28.08 FPS, with browser interval P95 of 69.5 and 70.0 ms. The small isolated savings left the room cadence effectively unchanged. The segment trial was removed, and the timer remains available for wider changes to the low output path.

`scripts/performance/studio-witness.mjs` validates a completed `studio-dxgi-roi-v1` file offline. It checks QPC order and marker CRC and distinguishes repeated serials, skipped serials and missed acquisitions. Synthetic covered-window tests passed. A two-second PresentMon preflight targeting the invoking process exited with code 1 before producing a CSV under the current user token. A headed GPU process and joint PresentMon and desktop witness capture are still required for physical calibration.

## Physical display calibration runner

Build the DXGI witness from an MSVC x64 Developer Prompt and pass the resulting executable to the calibration driver. Use an existing writable output directory for the generated files.

```bat
cl /nologo /std:c++17 /utf-8 /W4 /WX /EHsc scripts\performance\studio-dxgi-witness.cpp /Fo"<output-directory>\studio-dxgi-witness.obj" /Fe"<output-directory>\studio-dxgi-witness.exe" /link d3d11.lib dxgi.lib
```

Build the website with `npm run build`. The dry run checks the witness, PresentMon, built hold hook and selected native display without opening Chrome. The explicit capture mode opens a private foreground Chrome kiosk and requires a clear display. It scopes PresentMon to Chrome's GPU process and saves only the witness marker metadata from the 160 × 4 pixel region. A moving, held, and resumed sequence checks whether the canvas serial stays fixed while the same output is redrawn. ETW chain attribution and actual presented cadence remain separate checks.

```powershell
node scripts/performance/studio-physical.mjs --dry-run --display='\\.\DISPLAY1' --witness='<output-directory>\studio-dxgi-witness.exe'
```

The MSVC build and witness CPU self-test passed. The runner dry run confirmed native 3840 × 2160 at 143999/1000 Hz and found the test build's hold hook. No foreground capture results are available yet.
