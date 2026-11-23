import * as T from 'three';
import { loadDisplayModel } from './display-model';
import { panoramaOrigin, riverLevel } from './window-depth';
import type { SailingRoute } from '../content/window-scenes';

const lighting: Record<string, readonly [string, number]> = {
  'Cabin glazing': ['#80949d', 0.11],
  'Saloon panorama glass': ['#c7aa82', 0.2],
  'Saloon with amber lamps': ['#eabf8a', 0.34],
  'Quiet saloon': ['#7996a3', 0.06],
  'Port red': ['#ff483b', 1.55],
  'Starboard green': ['#62e398', 1.6],
};

export type FerryWarmup = { warm: (ferry: T.Group) => Promise<void>; signal: AbortSignal };

export async function warmRiverFerry(
  gl: T.WebGLRenderer,
  ferry: T.Group,
  camera: T.Camera,
  scene: T.Scene,
  highQuality: () => boolean,
  signal: AbortSignal,
) {
  if (signal.aborted || !gl.extensions.has('KHR_parallel_shader_compile')) return;
  const context = gl.getContext();
  const floatColor = gl.extensions.has('EXT_color_buffer_float');
  if (context.isContextLost()) return;
  performance.mark('studio-ferry-warm-start');
  while (!signal.aborted && !context.isContextLost()) {
    const hdr = floatColor && highQuality();
    const environment = scene.environment;
    const target = hdr ? new T.WebGLRenderTarget(1, 1, { type: T.HalfFloatType }) : null;
    const previous = gl.getRenderTarget();
    const face = gl.getActiveCubeFace();
    const mip = gl.getActiveMipmapLevel();
    let linking: Promise<T.Object3D>;
    try {
      gl.setRenderTarget(target);
      linking = gl.compileAsync(ferry, camera, scene);
      context.flush();
    } finally {
      gl.setRenderTarget(previous, face, mip);
      target?.dispose();
    }
    await linking;
    if (signal.aborted || context.isContextLost()) return;
    if (hdr === (floatColor && highQuality()) && environment === scene.environment) {
      performance.mark('studio-ferry-warm-end');
      return;
    }
  }
}

export function riverFerry(
  parent: T.Group,
  manager: T.LoadingManager,
  warmup?: () => FerryWarmup | undefined,
) {
  const ferry = new T.Group();
  ferry.name = 'Passing river ferry';
  let ready = !warmup;
  ferry.visible = ready;
  let attempted: FerryWarmup | undefined;
  parent.add(ferry);
  const lamps: { surface: T.MeshStandardMaterial; power: number }[] = [];
  void loadDisplayModel(ferry, '/media/models/river-ferry.glb', manager, {
    mesh(child) {
      child.castShadow = child.receiveShadow = false;
      const surface = child.material;
      if (!(surface instanceof T.MeshStandardMaterial)) return;
      surface.envMapIntensity = 0.12;
      const lit = lighting[surface.name];
      if (lit) {
        surface.emissive.set(lit[0]);
        lamps.push({ surface, power: lit[1] });
      } else {
        surface.emissive.copy(surface.color);
        lamps.push({ surface, power: 0.05 });
      }
    },
  });
  const curves = new Map<SailingRoute, T.CatmullRomCurve3>();
  const point = new T.Vector3(),
    tangent = new T.Vector3();
  const track = new T.Vector4();
  return (
    route: SailingRoute | undefined,
    time: number,
    night: number,
    weather: string,
    visibility: number,
  ) => {
    if (!ready && ferry.children.length) {
      const request = warmup?.();
      if (request && request !== attempted && !request.signal.aborted) {
        attempted = request;
        const finish = () => {
          if (warmup?.() === request && !request.signal.aborted) ready = true;
        };
        void Promise.resolve()
          .then(() => (request.signal.aborted ? undefined : request.warm(ferry)))
          .then(finish, finish);
      }
    }
    ferry.visible = Boolean(ready && route && visibility > 0 && ferry.children.length);
    if (!route || !ferry.visible) return track.set(100000, 100000, 0, -1);
    let curve = curves.get(route);
    if (!curve) {
      curve = new T.CatmullRomCurve3(route.points.map(([x, z]) => new T.Vector3(x, 0, z)));
      curves.set(route, curve);
    }
    const u = (route.start + (time * route.speed) / curve.getLength()) % 1;
    curve.getPointAt(u, point);
    curve.getTangentAt(u, tangent);
    ferry.position.set(
      panoramaOrigin.x + point.x,
      riverLevel - 0.16 + 0.032 * Math.sin(time * 0.67),
      panoramaOrigin.z + point.z,
    );
    ferry.rotation.y = -Math.atan2(tangent.z, tangent.x);
    ferry.rotation.z = 0.002 * Math.sin(time * 0.52);
    ferry.rotation.x = 0.003 * Math.sin(time * 0.72);
    for (const { surface, power } of lamps)
      surface.emissiveIntensity = T.MathUtils.lerp(
        0.22,
        power * (weather === '雨' ? 0.94 : 1),
        night,
      );
    return track.set(ferry.position.x, ferry.position.z, tangent.x, tangent.z);
  };
}
