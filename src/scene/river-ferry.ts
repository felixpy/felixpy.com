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

export function riverFerry(parent: T.Group, manager: T.LoadingManager) {
  const ferry = new T.Group();
  ferry.name = 'Passing river ferry';
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
    ferry.visible = Boolean(route && visibility > 0 && ferry.children.length);
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
