import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef, type RefObject } from 'react';
import { DepthTexture, HalfFloatType, WebGLRenderTarget } from 'three';
import type { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import type { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import type { RoomLook } from '../app/environment';
import { roomColorGrade } from './room-color-grade';
import { roomWarmup } from './room-warmup';
import { roomOcclusion } from './room-occlusion';
import { roomFirstFrame } from './room-first-frame';

export type FirstPicture = 'loading' | 'interactive' | 'preparing' | 'drawn';

export function Finish({
  enabled,
  look,
  roomVisible,
  screen,
  firstPicture,
  detailRevision,
  setLowScale,
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
  setLowScale: (scale: number) => void;
  onInteractive: () => void;
  night: boolean;
  firstFrame: ReturnType<typeof roomFirstFrame>;
}) {
  const { gl, scene, camera, size, viewport } = useThree();
  const grade = useMemo(roomColorGrade, []);
  useEffect(() => () => firstFrame.dispose(), [firstFrame]);
  useEffect(() => () => grade.dispose(), [grade]);
  const pipeline = useRef<{
    beauty: WebGLRenderTarget;
    composite: WebGLRenderTarget;
    occlusion: GTAOPass;
    output: OutputPass;
  } | null>(null);
  const lastRoomFrame = useRef(0);
  const shaders = useRef<'cold' | 'pending' | 'ready'>('cold');
  const preparation = useRef<ReturnType<typeof roomWarmup> | null>(null);
  const scannedRevision = useRef(-1);
  const sample = useRef({ frames: 0, slowFrames: 0, elapsed: 0, headroom: 0 });

  useEffect(() => {
    if (!enabled || !gl.extensions.has('EXT_color_buffer_float')) return;
    const depth = new DepthTexture(1, 1);
    const beauty = new WebGLRenderTarget(1, 1, {
      type: HalfFloatType,
      samples: Math.min(4, gl.capabilities.maxSamples),
      depthTexture: depth,
    });
    const composite = new WebGLRenderTarget(1, 1, { type: HalfFloatType, depthBuffer: false });
    const occlusion = roomOcclusion(scene, camera, depth);
    const output = grade.outputPass();
    pipeline.current = { beauty, composite, occlusion, output };
    return () => {
      pipeline.current = null;
      occlusion.dispose();
      occlusion.gtaoMaterial.dispose();
      occlusion.blendMaterial.dispose();
      output.dispose();
      beauty.dispose();
      composite.dispose();
    };
  }, [camera, enabled, gl, grade, scene]);

  useEffect(() => {
    const active = pipeline.current;
    if (!active) return;
    const width = Math.max(1, Math.floor(size.width * viewport.dpr));
    const height = Math.max(1, Math.floor(size.height * viewport.dpr));
    active.beauty.setSize(width, height);
    active.composite.setSize(width, height);
    active.occlusion.setSize(Math.ceil(width / 2), Math.ceil(height / 2));
  }, [camera, enabled, gl, scene, size.width, size.height, viewport.dpr]);

  useFrame(({ clock }, delta) => {
    if (firstPicture.current === 'interactive' && !roomVisible) return;
    if (firstPicture.current === 'loading' || firstPicture.current === 'interactive') {
      firstFrame.draw(gl, scene, camera, night, look);
      if (firstPicture.current === 'loading') onInteractive();
      firstPicture.current = 'interactive';
      return;
    }
    if (firstPicture.current === 'drawn' && !roomVisible) return;
    const now = clock.elapsedTime;
    const inComputer = screen.current?.dataset.interactive === 'true';
    if (inComputer && now - lastRoomFrame.current < 0.16) return;
    lastRoomFrame.current = now;
    if (!enabled && firstPicture.current === 'drawn' && !inComputer && !document.hidden) {
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
    const active = pipeline.current;
    if (preparation.current && firstPicture.current === 'drawn') {
      if (scannedRevision.current !== detailRevision.current) {
        preparation.current.scan();
        scannedRevision.current = detailRevision.current;
      }
      preparation.current.step(active?.beauty ?? null);
    }
    if (firstPicture.current === 'preparing') {
      const mapsReady = preparation.current?.uploadFront() ?? true;
      if (shaders.current === 'pending' || !mapsReady) {
        firstFrame.draw(gl, scene, camera, night, look);
        return;
      }
      if (shaders.current !== 'ready' && gl.extensions.has('KHR_parallel_shader_compile')) {
        shaders.current = 'pending';
        const pending = roomWarmup(gl, scene, camera);
        preparation.current = pending;
        scannedRevision.current = detailRevision.current;
        void pending.front(active?.beauty ?? null).then(
          () => {
            shaders.current = 'ready';
          },
          () => {
            shaders.current = 'ready';
          },
        );
        return;
      }
      shaders.current = 'ready';
    }
    grade.select(look);
    if (!active) {
      gl.render(scene, camera);
      grade.gradeScreen(gl);
    } else {
      const { beauty, composite, occlusion, output } = active;
      gl.setRenderTarget(beauty);
      gl.render(scene, camera);
      occlusion.render(gl, composite, beauty, delta, false);
      output.render(gl, beauty, composite, delta, false);
    }
    if (firstPicture.current === 'preparing') {
      firstPicture.current = 'drawn';
      firstFrame.dispose();
      performance.mark('studio-room-shaded');
    }
  }, 1);
  return null;
}
