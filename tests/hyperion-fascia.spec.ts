import { expect, test } from '@playwright/test';

test('the Hyperion front admits air through both grilles and both side intakes', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const three = '/node_modules/three/build/three.module.js';
    const library = '/src/scene/blender-library.ts';
    const parts = '/src/scene/blender-mesh.ts';
    const T = (await import(three)) as typeof import('three');
    const { loadParts } = (await import(library)) as typeof import('../src/scene/blender-library');
    const { blenderMesh } = (await import(parts)) as typeof import('../src/scene/blender-mesh');
    await loadParts('studio');
    const material = new T.MeshBasicMaterial({ side: T.DoubleSide });
    const part = (finish: string) => new T.Mesh(blenderMesh('gr701-fascia-' + finish), material);
    const grille = part('plate'),
      filter = part('filter'),
      baffle = part('carrier'),
      vanes = part('vane'),
      wing = part('wing'),
      casting = part('cast');
    const ray = new T.Raycaster(new T.Vector3(), new T.Vector3(0, 0, -1));
    const solid = (mesh: typeof wing, x: number, y: number) => {
      ray.ray.origin.set(x / 1000, y / 1000, 0.6);
      return ray.intersectObject(mesh).length > 0;
    };
    const light = part('light');
    const seams = [
      [-24.2, 81.8],
      [-12.9, 79],
      [22.3, 83.7],
    ];
    const crestSeatedInPlate = seams.every(
      ([x, height]) => !solid(grille, x, 132 + height) && solid(light, x, 132 + height),
    );
    const longStamp = [
      [-7.7, 62.4],
      [-1.7, 47.3],
      [4.3, 33.1],
    ];
    const longSlotAndWeb = longStamp.every(
      ([x, height]) => !solid(grille, x, 132 + height) && solid(grille, x + 3, 132 + height),
    );
    const browVisible = [-43, 0, 43].every((x) => {
      ray.ray.origin.set(x / 1000, 0.2633, 0.6);
      return ray.intersectObjects([light, grille, baffle, casting])[0]?.object === light;
    });
    const fractionOpen = (mesh: typeof wing, sign: number, grille: boolean) => {
      let hits = 0,
        samples = 0;
      for (let y = 0; y < 25; y++)
        for (let x = 0; x < 41; x++) {
          const blocked = grille
            ? solid(mesh, x - 20, sign * (227 + y))
            : solid(mesh, sign * (28 + x), y - 12);
          if (!blocked) hits++;
          samples++;
        }
      return hits / samples;
    };
    const grilleSetback = (sign: number) => {
      let closest = Infinity;
      for (let x = 58; x <= 69; x++) {
        ray.ray.origin.set((sign * x) / 1000, 0, 0.6);
        const wingHit = ray.intersectObject(wing)[0];
        const meshHit = ray.intersectObject(filter)[0];
        if (wingHit && meshHit) closest = Math.min(closest, meshHit.distance - wingHit.distance);
      }
      return closest;
    };
    const straightSlots = [-1, 1].every((side) =>
      [25, 41, 57, 73, 89, 105].every((center) => {
        const y = Math.min(175, 51 + (center - 10) * 1.65);
        return [-y, 0, y].every(
          (level) =>
            solid(vanes, side * center, level) && !solid(vanes, side * (center + 6), level),
        );
      }),
    );
    const cheekSamples = [
      [-4, -106, 259],
      [-4, -98, 260],
      [0, -92, 259],
    ];
    const exposedInterior = [-1, 1].flatMap((side) =>
      cheekSamples.map(([x, y, z]) => {
        const eye = new T.Vector3(side * 0.212, 0.352, 0.686);
        const panel = new T.Vector3((-side * x) / 1000, y / 1000, z / 1000);
        ray.set(eye, panel.clone().sub(eye).normalize());
        const cover = ray.intersectObjects([casting, baffle, wing, grille])[0];
        return !cover || cover.point.z < 0.243;
      }),
    );
    ray.ray.direction.set(0, 0, -1);
    const printed = part('ink').geometry.boundingBox!;
    const screenBounds = filter.geometry.boundingBox!;
    const rotorFront = 0.225 + blenderMesh('strix-fan-opal').boundingBox!.max.z;
    const innerFrame = part('frame');
    const frameHit = (origin: number[], direction: number[]) => {
      ray.set(new T.Vector3().fromArray(origin), new T.Vector3().fromArray(direction).normalize());
      return ray.intersectObject(innerFrame)[0]?.distance ?? null;
    };
    const frontPorts = [-0.153, -0.013, 0.127].map((height) =>
      frameHit([0, height, 0.5], [0, 0, -1]),
    );
    const ductBorder = frameHit([0.078, 0.11, 0.5], [0, 0, -1]);
    const upperRail = frameHit([0.043, 0.258, 0.085], [1, 0, 0]);
    const frontHeader = frameHit([0.048, 0.221, 0.165], [0.05, 0.51, 0.86]);
    const roofRail = frameHit([0.081, 0.23, -0.05], [0, 1, 0]);
    const roofVent = frameHit([0, 0.23, -0.05], [0, 1, 0]);
    const castingLead = [-1, 1].flatMap((side) =>
      [
        [0.75284, 0.03453, -0.6573],
        [0.69917, -0.38418, -0.60297],
      ].map(([x, y, z]) => {
        ray.set(
          new T.Vector3(0.91393 * side, 0.20239, 0.92365),
          new T.Vector3(-side * x, y, z).normalize(),
        );
        const rail = ray.intersectObject(casting)[0];
        const steel = ray.intersectObject(innerFrame)[0];
        return rail && steel ? steel.distance - rail.distance : 0;
      }),
    );
    const jambSealed = [-1, 1].every((side) =>
      [-0.18, -0.09, 0, 0.09, 0.18].every((y) =>
        [0.28, 0.74].every((slope) => {
          const direction = new T.Vector3(-side, -0.07, -slope).normalize();
          const target = new T.Vector3(side * 0.1157, y, 0.195);
          ray.set(target.clone().addScaledVector(direction, -0.35), direction);
          const hit = ray.intersectObject(innerFrame)[0];
          return hit && Math.abs(hit.point.x - target.x) < 0.003;
        }),
      ),
    );
    ray.ray.direction.set(0, 0, -1);
    return {
      frontPorts,
      ductBorder,
      upperRail,
      frontHeader,
      roofRail,
      roofVent,
      castingLead,
      jambSealed,
      crestSeatedInPlate,
      longSlotAndWeb,
      browVisible,
      straightSlots,
      rotorGap: screenBounds.min.z - rotorFront,
      grilleClearance: grille.geometry.boundingBox!.min.z - screenBounds.max.z,
      exposedInterior,
      transferHeight: printed.max.y - printed.min.y,
      outermostTransfer: printed.min.x,
      panels: [1, -1].map((sign) => fractionOpen(grille, sign, true)),
      intakes: [1, -1].map((sign) => fractionOpen(filter, sign, false)),
      wingFaces: [1, -1].map((sign) => solid(wing, sign * 99, 0)),
      behindWings: [1, -1].map(grilleSetback),
      centralWeb: solid(casting, 0, 0),
    };
  });
  for (const open of result.panels) {
    expect(open).toBeGreaterThan(0.12);
    expect(open).toBeLessThan(0.68);
  }
  for (const open of result.intakes) {
    expect(open).toBeGreaterThan(0.3);
    expect(open).toBeLessThan(0.8);
  }
  expect(result.wingFaces).toEqual([true, true]);
  expect(result.straightSlots).toBe(true);
  expect(result.frontPorts).toEqual([null, null, null]);
  expect(result.ductBorder).toBeCloseTo(0.261, 2);
  expect(result.roofVent).toBeNull();
  expect(result.roofRail).toBeCloseTo(0.039, 2);
  expect(result.upperRail).toBeCloseTo(0.047, 2);
  expect(result.frontHeader).toBeGreaterThan(0.06);
  expect(result.frontHeader).toBeLessThan(0.095);
  expect(result.rotorGap).toBeGreaterThan(0.002);
  expect(result.rotorGap).toBeLessThan(0.004);
  expect(result.grilleClearance).toBeGreaterThan(0.004);
  for (const setback of result.behindWings) {
    expect(setback).toBeGreaterThan(0.025);
    expect(setback).toBeLessThan(0.05);
  }
  expect(result.centralWeb).toBe(true);
  expect(Math.min(...result.castingLead)).toBeGreaterThan(0.012);
  expect(result.jambSealed).toBe(true);
  expect(result.crestSeatedInPlate).toBe(true);
  expect(result.longSlotAndWeb).toBe(true);
  expect(result.browVisible).toBe(true);
  expect(result.exposedInterior).not.toContain(true);
  expect(result.transferHeight).toBeGreaterThan(0.165);
  expect(result.outermostTransfer).toBeLessThan(-0.115);
});
