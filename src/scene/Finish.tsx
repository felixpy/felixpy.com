import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef, type RefObject } from 'react';
import { DepthTexture, HalfFloatType, WebGLRenderTarget, type Object3D } from 'three';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import type { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import type { RoomLook } from '../app/environment';
import { roomColorGrade } from './room-color-grade';
import { roomWarmup } from './room-warmup';
import { roomOcclusion } from './room-occlusion';
import { roomFirstFrame } from './room-first-frame';
import { roomDepthPrefill } from './room-depth-prefill';

export type FirstPicture = 'loading' | 'interactive' | 'preparing' | 'drawn';

function occlusionWarmup(occlusion?: GTAOPass) {
  return occlusion
    ? [
        { material: occlusion.gtaoMaterial, target: occlusion.gtaoRenderTarget },
        { material: occlusion.pdMaterial, target: occlusion.pdRenderTarget },
      ]
    : [];
}

export function Finish({
  enabled,
  look,
  roomVisible,
  screen,
  firstPicture,
  detailRevision,
  workbench,
  setLowScale,
  nativeLow,
  simpleLow,
  roomMode,
  onInteractive,
  night,
  firstFrame,
}: {
  enabled: boolean;
  look: RoomLook;
  roomVisible: boolean;
  screen: RefObject<HTMLDivElement | null>;
  firstPicture: RefObject<FirstPicture>;
  detailRevision: RefObject<number>;
  workbench: { roots: readonly Object3D[]; ready: Promise<void> };
  setLowScale: (scale: number) => void;
  nativeLow: boolean;
  simpleLow: boolean;
  roomMode: boolean;
  onInteractive: () => void;
  night: boolean;
  firstFrame: ReturnType<typeof roomFirstFrame>;
}) {
  const { gl, scene, camera, size, viewport } = useThree();
  const grade = useMemo(roomColorGrade, []);
  const prefill = useMemo(
    () =>
      nativeLow && new URLSearchParams(location.search).get('studio-depth-prefill') === 'coarse'
        ? roomDepthPrefill()
        : undefined,
    [nativeLow],
  );
  const warmup = useMemo(() => new URLSearchParams(location.search).get('studio-warmup'), []);
  const warmWorkbench = warmup === 'workbench';
  const pacing = warmup === 'paced' || warmup === 'adaptive' ? warmup : undefined;
  const catchUp = warmup === 'catch-up';
  useEffect(() => () => firstFrame.dispose(), [firstFrame]);
  useEffect(() => () => grade.dispose(), [grade]);
  useEffect(() => () => prefill?.dispose(), [prefill]);
  const pipeline = useRef<{
    beauty: WebGLRenderTarget;
    composite?: WebGLRenderTarget;
    occlusion: GTAOPass;
    output: OutputPass;
  } | null>(null);
  const lastRoomFrame = useRef(0);
  const frameMarker = useRef<ReturnType<
    typeof import('./room-frame-marker').roomFrameMarker
  > | null>(null);
  const shaders = useRef<'cold' | 'pending' | 'ready'>('cold');
  const preparation = useRef<ReturnType<typeof roomWarmup> | null>(null);
  const workbenchPreparation = useRef<ReturnType<typeof roomWarmup> | null>(null);
  const scannedRevision = useRef(-1);
  const sample = useRef({ frames: 0, slowFrames: 0, elapsed: 0, headroom: 0 });

  useEffect(() => {
    if (new URLSearchParams(location.search).get('studio-present-witness') !== 'roi') return;
    let active = true;
    void import('./room-frame-marker').then(({ roomFrameMarker }) => {
      if (active) frameMarker.current = roomFrameMarker();
    });
    return () => {
      active = false;
      frameMarker.current?.dispose();
      frameMarker.current = null;
    };
  }, []);

  useEffect(() => {
    if (!warmWorkbench || !gl.extensions.has('KHR_parallel_shader_compile')) return;
    const pending = roomWarmup(gl, scene, camera, [], undefined, workbench.roots);
    let disposed = false;
    void workbench.ready.then(() => {
      if (!disposed) workbenchPreparation.current = pending;
    });
    return () => {
      disposed = true;
      workbenchPreparation.current = null;
      pending.dispose();
    };
  }, [camera, enabled, gl, scene, warmWorkbench, workbench]);

  useEffect(() => {
    if (!catchUp) return;
    return () => {
      preparation.current?.dispose();
      preparation.current = null;
      shaders.current = 'cold';
    };
  }, [camera, catchUp, enabled, gl, grade, scene]);

  useEffect(() => {
    if (!enabled || !gl.extensions.has('EXT_color_buffer_float')) return;
    const fusedOutput = new URLSearchParams(location.search).get('studio-output') !== 'legacy';
    const depth = new DepthTexture(1, 1);
    const beauty = new WebGLRenderTarget(1, 1, {
      type: HalfFloatType,
      samples: Math.min(4, gl.capabilities.maxSamples),
      depthTexture: depth,
    });
    const composite = fusedOutput
      ? undefined
      : new WebGLRenderTarget(1, 1, { type: HalfFloatType, depthBuffer: false });
    const occlusion = roomOcclusion(scene, camera, depth);
    if (fusedOutput) occlusion.output = GTAOPass.OUTPUT.Off;
    const output = grade.outputPass(
      fusedOutput ? { map: occlusion.gtaoMap, intensity: occlusion.blendIntensity } : undefined,
    );
    pipeline.current = { beauty, composite, occlusion, output };
    return () => {
      pipeline.current = null;
      occlusion.dispose();
      occlusion.gtaoMaterial.dispose();
      occlusion.blendMaterial.dispose();
      output.dispose();
      beauty.dispose();
      composite?.dispose();
    };
  }, [camera, enabled, gl, grade, scene]);

  useEffect(() => {
    const active = pipeline.current;
    if (!active) return;
    const width = Math.max(1, Math.floor(size.width * viewport.dpr));
    const height = Math.max(1, Math.floor(size.height * viewport.dpr));
    active.beauty.setSize(width, height);
    active.composite?.setSize(width, height);
    active.occlusion.setSize(Math.ceil(width / 2), Math.ceil(height / 2));
  }, [camera, enabled, gl, scene, size.width, size.height, viewport.dpr]);

  useFrame(({ clock }, delta) => {
    if (firstPicture.current === 'interactive' && !roomVisible) return;
    if (firstPicture.current === 'loading' || firstPicture.current === 'interactive') {
      if (firstFrame.preparing(gl, scene, camera)) return;
      const initial = firstPicture.current === 'loading';
      if (initial) performance.mark('studio-room-preview-start');
      firstFrame.draw(gl, scene, camera, night, look);
      if (initial) {
        performance.mark('studio-room-preview-drawn');
        onInteractive();
      }
      firstPicture.current = 'interactive';
      return;
    }
    if (firstPicture.current === 'drawn' && !roomVisible) return;
    const now = clock.elapsedTime;
    const inComputer = screen.current?.dataset.interactive === 'true';
    if (inComputer && now - lastRoomFrame.current < 0.16) return;
    lastRoomFrame.current = now;
    if (
      !enabled &&
      !nativeLow &&
      firstPicture.current === 'drawn' &&
      !inComputer &&
      !document.hidden
    ) {
      const timing = sample.current;
      timing.elapsed += delta;
      if (delta > 1 / 42) timing.slowFrames++;
      if (++timing.frames >= 3 && timing.elapsed >= 0.75) {
        const average = timing.elapsed / timing.frames;
        if (average > 1 / 42 && timing.slowFrames * 2 >= timing.frames) {
          const next = Math.max(
            0.5,
            Math.floor(viewport.dpr * Math.sqrt(1 / 50 / average) * 8) / 8,
          );
          if (next < viewport.dpr) setLowScale(next);
          timing.headroom = 0;
        } else if (average < 1 / 55 && viewport.dpr < 1) {
          timing.headroom += timing.elapsed;
          if (timing.headroom >= 8) {
            setLowScale(Math.min(1, viewport.dpr + 0.125));
            timing.headroom = 0;
          }
        } else timing.headroom = 0;
        timing.frames = timing.slowFrames = timing.elapsed = 0;
      }
    } else {
      sample.current.frames =
        sample.current.slowFrames =
        sample.current.elapsed =
        sample.current.headroom =
          0;
    }
    if (simpleLow && !enabled) {
      firstFrame.draw(gl, scene, camera, night, look);
      if (firstPicture.current === 'preparing') {
        firstPicture.current = 'drawn';
        performance.mark('studio-room-shaded');
      }
      return;
    }
    const active = pipeline.current;
    const drawn = firstPicture.current === 'drawn';
    if (preparation.current && drawn) {
      if (scannedRevision.current !== detailRevision.current) {
        preparation.current.scan();
        scannedRevision.current = detailRevision.current;
      }
      if (!pacing) preparation.current.step(active?.beauty ?? null);
    }
    if (firstPicture.current === 'preparing') {
      const parallel = gl.extensions.has('KHR_parallel_shader_compile');
      const workbenchReady =
        workbenchPreparation.current?.prepareVisible(
          active?.beauty ?? null,
          detailRevision.current,
        ) ?? true;
      if ((warmup === 'incremental' || pacing) && parallel) {
        if (!preparation.current) {
          preparation.current = roomWarmup(
            gl,
            scene,
            camera,
            occlusionWarmup(active?.occlusion),
            pacing,
          );
          performance.mark('studio-room-shader-warm-start');
        }
        const preview = () => firstFrame.draw(gl, scene, camera, night, look);
        if (
          !preparation.current.prepareVisible(
            active?.beauty ?? null,
            detailRevision.current,
            pacing ? preview : undefined,
          )
        ) {
          if (warmup === 'incremental') preview();
          return;
        }
        performance.mark('studio-room-shader-warm-end');
      } else {
        const mapsReady = preparation.current?.uploadFront() ?? true;
        if (shaders.current === 'pending' || !mapsReady) {
          firstFrame.draw(gl, scene, camera, night, look);
          return;
        }
        if (shaders.current !== 'ready' && parallel) {
          shaders.current = 'pending';
          const pending = roomWarmup(
            gl,
            scene,
            camera,
            catchUp ? occlusionWarmup(active?.occlusion) : undefined,
            catchUp ? 'catch-up' : undefined,
          );
          preparation.current = pending;
          scannedRevision.current = catchUp ? -1 : detailRevision.current;
          performance.mark('studio-room-shader-warm-start');
          const finish = () => {
            if (preparation.current !== pending) return;
            shaders.current = 'ready';
            performance.mark(
              catchUp ? 'studio-room-shader-catch-up-start' : 'studio-room-shader-warm-end',
            );
          };
          void pending.front(active?.beauty ?? null).then(finish, finish);
          return;
        }
        if (catchUp && preparation.current) {
          if (!preparation.current.prepareVisible(active?.beauty ?? null, detailRevision.current)) {
            firstFrame.draw(gl, scene, camera, night, look);
            return;
          }
          performance.mark('studio-room-shader-warm-end');
        }
      }
      if (!workbenchReady) {
        firstFrame.draw(gl, scene, camera, night, look);
        return;
      }
      shaders.current = 'ready';
    }
    if (firstPicture.current === 'preparing') performance.mark('studio-room-full-draw-start');
    grade.select(look);
    if (!active) {
      if (prefill && !enabled && drawn && roomMode)
        prefill.render(gl, scene, camera, detailRevision.current);
      else gl.render(scene, camera);
      grade.gradeScreen(gl);
    } else {
      const { beauty, composite, occlusion, output } = active;
      const color = composite ?? beauty;
      gl.setRenderTarget(beauty);
      gl.render(scene, camera);
      occlusion.render(gl, color, beauty, delta, false);
      output.render(gl, beauty, color, delta, false);
    }
    if (frameMarker.current?.draw(gl) === 1) performance.mark('studio-present-marker-ready');
    if (drawn && pacing) preparation.current?.step(active?.beauty ?? null);
    if (firstPicture.current === 'preparing') {
      firstPicture.current = 'drawn';
      if (!simpleLow) firstFrame.dispose();
      performance.mark('studio-room-shaded');
    }
  }, 1);
  return null;
}
