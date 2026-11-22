# Studio performance standards

Use these criteria when changing room rendering, asset loading, graphics defaults or inspection. The hardware targets are product goals. The percentile thresholds are proposed engineering acceptance gates. Record the decision and supporting measurements when changing them. The [development plan](specs/2026-11-22-studio-performance.md) records the measured baseline and experiments.

## Product targets

| Hardware and acceptance quality           | Required 3D drawing buffer | Release target | Stretch target at the same native resolution |
| ----------------------------------------- | -------------------------- | -------------- | -------------------------------------------- |
| RTX 4090, all settings at highest quality | 3840 × 2160 native         | 144 FPS        | —                                            |
| Desktop RTX 3060 12 GB, high quality      | 2560 × 1440 native         | 60 FPS         | 144 FPS                                      |
| Intel UHD 770, low quality                | 1920 × 1080 native         | 30 FPS         | 60 FPS                                       |

Use the release column for sign-off. After a tier passes, evaluate its stretch target separately and record the quality settings used. Count distinct rendered scene frames presented at native resolution for both targets.

| Target cadence | Frame budget | Suggested CPU / GPU P95 work budgets | Proposed presented-frame P95 / P99 limits |
| -------------- | ------------ | ------------------------------------ | ----------------------------------------- |
| 144 FPS        | 6.94 ms      | 4.5 / 5.8 ms                         | 7.2 / 7.5 ms                              |
| 60 FPS         | 16.67 ms     | 10 / 14 ms                           | 17.0 / 17.5 ms                            |
| 30 FPS         | 33.33 ms     | 20 / 28 ms                           | 34.0 / 35.0 ms                            |

The loading indicator has a separate 30 Hz target while animating, with a 33.33 ms update budget.

CPU and GPU work overlap. Record CSS viewport, device pixel ratio, drawing-buffer dimensions and the main render target separately. Report adaptive resolution in a separate row. A 4090 run at 1440p is a repeatable development comparator. Certification of the 3060 target requires matching hardware. Verify the monitor refresh mode and actual presented cadence on the target system.

## Measurement and release gates

1. Pin browser version, adapter/backend, power mode, foreground status, view, weather, day/night and quality. Record browser, OS/driver, refresh rate, monitor scaling, cache policy and actual render sizes with every result. For cold visits start a fresh browser profile with HTTP cache disabled. For warm visits enable caching in a separate context, prime the same origin once, then reload and measure. Avoid Playwright routing on the warm run because it disables the HTTP cache. Use a local weather fixture or targeted CDP interception and verify actual cache hits in the network trace. Software GPU emulation is useful for functional coverage only.
2. Separate loader rAF intervals, rendered room intervals, main-thread long tasks, asynchronous GPU timer queries and actually presented frames. Discard disjoint queries. A change in the progress percentage is a separate signal because a rounded label or an intentional plateau can remain unchanged across many animation frames. Capture the moving bar in the compositor trace or a display recording when verifying 30 Hz. Observe from first visible loader paint to removal, including the first/last partial interval.
3. For release, run five cold and five warm visits per target and sample 60 seconds per steady route. Include desk rotation, glass PC, bookcase, cabinet, equipment wall, printer, snow/rain at the window and first/repeat inspections. Hold weather, blinds, time, camera and exposure constant for comparisons. Run 10 minutes of repeated turns and inspections for memory growth, cache eviction and recovery. Compare an empty-scene control to identify host scheduling noise.
4. **Proposed release gates.** While the loader is moving, target a presented interval P95 ≤ 33.4 ms and zero app-attributed stalls over 50 ms, also reporting P99, worst gap and missed 33.33 ms deadlines. After first input, require zero resource-induced stalls over 50 ms in the first ten seconds following input on the cold route and fewer than 1% of intervals over twice the target frame budget. At steady state, verify the tier's presented FPS and the corresponding P95/P99 limits above, with fewer than 0.1% of intervals over twice the target frame budget. Report actual missed refresh opportunities as well. Sample render sizes throughout the route. A native run requires the full requested drawing buffer and, when present, a full-size main color target. The direct low path uses the default framebuffer.
5. Attach the tested commit, build fingerprint, route, hardware, before/after traces, images, test results and a rollback path to each performance change. Inspect fine text, silhouette, thin high-contrast lines, glass, nearby reflections, contact shadows and temporal flicker. Visual checks include native-size stills and a matched motion recording. Run the production build and relevant Playwright interactions before release.
6. Keep changes to the test contract here. Update the baseline and priorities in the development plan when the implementation changes. Store raw traces, screenshots and local run output in the ignored `.review/` directory. Record the tested commit and measurement conditions alongside each published result.
