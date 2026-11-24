import { expect, test } from '@playwright/test';
import { pcReadings } from '../src/scene/pc-telemetry';

test('the workstation OLEDs cover their operating ranges with gradual changes', () => {
  const samples = Array.from({ length: 10_800 }, (_, second) => pcReadings(second));
  const temperatures = samples.map((sample) => sample.celsius);
  const power = samples.map((sample) => sample.watts);
  expect([Math.min(...temperatures), Math.max(...temperatures)]).toEqual([35, 50]);
  expect([Math.min(...power), Math.max(...power)]).toEqual([150, 300]);
  expect(temperatures.slice(1).every((value, i) => Math.abs(value - temperatures[i]) <= 1)).toBe(
    true,
  );
  expect(power.slice(1).every((value, i) => Math.abs(value - power[i]) <= 8)).toBe(true);
});

test('the processor, memory, GPU support and power harness fit their workstation interfaces', async ({
  page,
}) => {
  await page.goto('/media/credits.txt');
  const fit = await page.evaluate(async () => {
    const scenePath = '/src/scene/';
    const threePath = '/node_modules/three/build/three.module.js';
    const [T, { tower }, { materials }, { loadParts }] = await Promise.all([
      import(threePath),
      import(scenePath + 'hardware.ts'),
      import(scenePath + 'materials.ts'),
      import(scenePath + 'blender-library.ts'),
    ]);
    await Promise.all([loadParts('studio'), loadParts('pc-hero')]);
    const manager = new T.LoadingManager();
    manager.setURLModifier((url: string) =>
      url.replace(/(strix-z890-a|xpg-d50-fubuki)\.glb\.gz$/, '$1.glb'),
    );
    const loaded = new Promise<void>((resolve) => {
      manager.onLoad = resolve;
    });
    const aura = Array.from({ length: 7 }, () => new T.MeshStandardMaterial());
    const pc = tower(new T.Group(), materials(new T.TextureLoader(manager)), aura, manager);
    pc.setComponentLights(false);
    pc.selectDetail(true);
    await loaded;
    const displayed = () => {
      const objects = new Set<import('three').Object3D>();
      pc.unit.traverseVisible((part: import('three').Object3D) => objects.add(part));
      return objects;
    };
    const closeView = displayed();
    pc.selectDetail(false);
    const roomView = displayed();
    const backplate = pc.unit.getObjectByName('Socket_steel_backplate_·_rear');
    const rearCapacitors = pc.unit.getObjectByName('CPU_underside_decoupling_capacitors');
    const throughGlass = pc.unit.getObjectByName('ROG Astral · close inspection');
    const seatedParts: import('three').Object3D[] = [];
    const guides: import('three').Object3D[] = [];
    pc.unit.traverse((part: import('three').Object3D) => {
      if (
        part.userData.installedHidden ||
        part.userData.model === 'Intel Core Ultra 9 285K' ||
        part.userData.name === '288 selectively plated connector fingers' ||
        part.userData.name === 'Under-spreader thermal interface pads' ||
        part.name === 'LGA1851 contact and 78 mm mount • copper' ||
        part.name === 'Keyed PCIe ×16 • gold'
      )
        seatedParts.push(part);
      if (part.userData.name === 'Continuous opaline light guide and pad printed XPG crown') {
        guides.push(part);
      }
    });
    const visibility = {
      seatedParts: seatedParts.length,
      guides: guides.length,
      concealed: seatedParts.every((part) => !closeView.has(part) && !roomView.has(part)),
      lit: guides.every((part) => closeView.has(part) && roomView.has(part)),
      inspection: closeView.has(throughGlass) && !roomView.has(throughGlass),
      serviceOpening:
        closeView.has(backplate) &&
        roomView.has(backplate) &&
        closeView.has(rearCapacitors) &&
        !roomView.has(rearCapacitors),
    };
    pc.unit.position.set(0, 0, 0);
    pc.unit.rotation.set(0, 0, 0);
    pc.unit.updateMatrixWorld(true);
    const processor = pc.unit.getObjectByName('Installed_Intel_Core_Ultra_9_285K');
    if (!processor) throw new Error('The installed Intel Core Ultra 9 285K is missing');
    const socket = pc.unit.getObjectByName('CPU_contact');
    const copper = pc.unit.getObjectByName('LGA1851 contact and 78 mm mount • copper');
    const outward = socket.getWorldDirection(new T.Vector3());
    const cpuContacts = [
      [0, 0],
      [-0.01, -0.012],
      [-0.01, 0.012],
      [0.01, -0.012],
      [0.01, 0.012],
    ].map(([u, v]) => {
      const contact = socket.localToWorld(new T.Vector3(u, v, 0));
      return [processor, copper].map((component, index) => {
        const direction = outward.clone().multiplyScalar(index === 0 ? -1 : 1);
        const origin = contact.clone().addScaledVector(direction, -0.012);
        const hit = new T.Raycaster(origin, direction, 0, 0.024).intersectObject(component)[0];
        return hit ? hit.point.distanceTo(contact) * 1000 : null;
      });
    });
    const holder = pc.unit.getObjectByName('ROG Herculx XH01');
    const card = pc.unit.getObjectByName('Diecast frame and thermal module');
    const deck = pc.unit.getObjectByName('Hyperion removable PSU shroud and accessory drawer');
    const shim = holder.getObjectByName('GR701_deck_leveling_shim');
    const rubber: import('three').Vector3[] = [];
    holder.traverse((part: import('three').Mesh) => {
      if (Array.isArray(part.material) || part.material?.name !== 'Herculx elastomer lands') return;
      const vertices = part.geometry.getAttribute('position');
      for (let i = 0; i < vertices.count; i++) {
        rubber.push(part.localToWorld(new T.Vector3().fromBufferAttribute(vertices, i)));
      }
    });
    const envelope = new T.Box3().setFromPoints(rubber);
    function landAt(planeY: number) {
      return new T.Box3().setFromPoints(rubber.filter((p) => Math.abs(p.y - planeY) < 0.00005));
    }
    function gap(
      land: import('three').Box3,
      planeY: number,
      direction: number,
      target: import('three').Object3D,
    ) {
      const center = land.getCenter(new T.Vector3());
      center.y = planeY - direction * 0.001;
      const hit = new T.Raycaster(center, new T.Vector3(0, direction, 0), 0, 0.008).intersectObject(
        target,
        true,
      )[0];
      return hit ? Math.abs(hit.point.y - planeY) * 1000 : null;
    }
    const emitters = new Map<string, import('three').MeshStandardMaterial>();
    pc.unit.traverse((obj: import('three').Mesh) => {
      const mat = obj.material;
      if (
        !Array.isArray(mat) &&
        ['D50 opal RGB', 'Herculx Aura etched lightguide'].includes(mat?.name)
      )
        emitters.set(mat.uuid, mat as import('three').MeshStandardMaterial);
    });
    const unlit = [...emitters.values()].map((m) => m.emissiveIntensity);
    pc.setComponentLights(true);
    const pad = landAt(envelope.max.y);
    const foot = landAt(envelope.min.y);
    const shimBounds = new T.Box3().setFromObject(shim, true);
    const firstFan = new T.Box3().setFromObject(card.getObjectByName('Axial-tech intake 1'), true);
    const lastFan = new T.Box3().setFromObject(card.getObjectByName('Axial-tech intake 3'), true);
    const cable = pc.unit.getObjectByName('Seated 12V-2x6 power and sense loom');
    const tray = pc.unit.getObjectByName('Motherboard tray with lower cable openings');
    const grommet = pc.unit.getObjectByName('24-pin tray grommet');
    const tongues = ['upper', 'centre', 'lower'].map((name) => {
      const piece = grommet.getObjectByName('Upper tray grommet · ' + name + ' tongue');
      const geometry = piece.geometry;
      const position = geometry.getAttribute('position');
      const vertexIds = new Map<string, number>();
      const index = Array.from({ length: position.count }, (_, i) => {
        const key = [position.getX(i), position.getY(i), position.getZ(i)].join(',');
        if (!vertexIds.has(key)) vertexIds.set(key, vertexIds.size);
        return vertexIds.get(key)!;
      });
      const sides = new Map<number, number>();
      const indices = geometry.index;
      for (let i = 0; i < indices.count; i += 3) {
        for (let j = 0; j < 3; j++) {
          const a = index[indices.getX(i + j)],
            b = index[indices.getX(i + ((j + 1) % 3))];
          const edge = Math.min(a, b) * vertexIds.size + Math.max(a, b);
          sides.set(edge, (sides.get(edge) ?? 0) + 1);
        }
      }
      geometry.computeBoundingBox();
      const bounds = geometry.boundingBox;
      const edges = [bounds.min.z, bounds.max.z].map((z) => {
        const heights = Array.from({ length: position.count }, (_, i) => i)
          .filter((i) => Math.abs(position.getZ(i) - z) < 0.00004)
          .map((i) => position.getY(i));
        return (Math.max(...heights) - Math.min(...heights)) * 1000;
      });
      return {
        edges,
        closed: [...sides.values()].every((count) => count === 2),
        euler: vertexIds.size - sides.size + indices.count / 3,
        relief: !!piece.material.normalMap,
      };
    });
    const fan = card.getObjectByName('Fourth pass-through fan');
    const direction = new T.Vector3(1, 0, 0);
    const heights: number[] = [];
    const crossings = [[], []] as import('three').Vector3[][];
    let fanClearance = Infinity;
    let cableShieldGap = Infinity;
    let prematureDrop = false;
    const harnessBounds = new T.Box3();
    const cableShield = pc.unit.getObjectByName('GR701 cable bay · smoke');
    const shieldRay = new T.Raycaster(undefined, direction, 0, 0.05);
    cable.traverse((piece: import('three').Mesh) => {
      if (!piece.isMesh) return;
      const positions = piece.geometry.getAttribute('position');
      const points = Array.from({ length: positions.count }, (_, index) =>
        piece.localToWorld(new T.Vector3().fromBufferAttribute(positions, index)),
      );
      for (const p of points) {
        harnessBounds.expandByPoint(p);
        if (p.x >= 0.082) {
          shieldRay.ray.origin.set(0.08, p.y, p.z);
          const shield = shieldRay.intersectObject(cableShield, false)[0];
          if (shield) cableShieldGap = Math.min(cableShieldGap, shield.point.x - p.x);
          continue;
        }
        if (p.y < 0 && p.y > -0.166) prematureDrop = true;
        if (p.y <= 0) continue;
        const local = fan.worldToLocal(p.clone());
        fanClearance = Math.min(fanClearance, Math.hypot(local.x, local.y) - 0.0544);
      }
      const indices = piece.geometry.index!;
      for (let i = 0; i < indices.count; i += 3) {
        for (let j = 0; j < 3; j++) {
          const a = points[indices.getX(i + j)];
          const b = points[indices.getX(i + ((j + 1) % 3))];
          for (const x of [0, 0.087]) {
            if (a.x < x === b.x < x) continue;
            const p = a.clone().lerp(b, (x - a.x) / (b.x - a.x));
            if (x === 0) heights.push(p.y * 1000);
            else crossings[p.y > 0 ? 0 : 1].push(p);
          }
        }
      }
    });
    const throughMetal = crossings
      .flat()
      .some(
        (p) =>
          new T.Raycaster(new T.Vector3(0.081, p.y, p.z), direction, 0, 0.011).intersectObjects(
            [tray, grommet],
            true,
          ).length > 0,
      );
    const atx = pc.unit.getObjectByName('24-pin ATX braided loom and retaining comb');
    const inletSize = new T.Box3().setFromObject(grommet, true).getSize(new T.Vector3());
    const seeThrough = [0, 0.42, -0.42].map((slope) => {
      const view = new T.Vector3(1, 0, slope).normalize();
      const ray = new T.Raycaster(undefined, view, 0, 0.24);
      let open = 0;
      let samples = 0;
      for (let z = -19; z < 10; z += 2) {
        const lower = 34 + z + 20;
        const upper = 176 - ((z + 20) * 29) / 30;
        for (let y = Math.ceil(lower) + 1; y < upper; y += 2) {
          ray.ray.origin.set(-0.125, y / 1000, z / 1000 - slope * 0.21);
          samples++;
          if (
            !ray.intersectObject(grommet, true).length &&
            !ray.intersectObjects([atx, cable], true).length
          )
            open++;
        }
      }
      return open / samples;
    });
    return {
      visibility,
      cpuContacts,
      height: (envelope.max.y - envelope.min.y) * 1000,
      outerClearance: lastFan.min.x - pad.max.x,
      closerToFreeEnd: pad.min.z > (firstFan.max.z + lastFan.min.z) / 2,
      padGap: gap(pad, envelope.max.y, 1, card),
      footGap: gap(foot, envelope.min.y, -1, shim),
      deckGap: gap(shimBounds, shimBounds.min.y, -1, deck),
      sockets: pc.unit
        .getObjectByName('XPG D50 Fubuki DDR5 memory bank')
        .children.filter((slot: import('three').Group) => slot.children.length)
        .map((slot: import('three').Group) => slot.userData.memorySocket),
      unlit,
      lit: [...emitters.values()].map((m) => m.emissiveIntensity),
      powerRoute: {
        samples: [heights.length, ...crossings.map((points) => points.length)],
        middle: [Math.min(...heights), Math.max(...heights)],
        throughMetal,
        inletDimensions: [inletSize.z * 1000, inletSize.y * 1000],
        tongues,
        seeThrough,
        prematureDrop,
        fanClearance: fanClearance * 1000,
        cableShieldGap: Number.isFinite(cableShieldGap) ? cableShieldGap * 1000 : null,
        leftGlassGap: (harnessBounds.min.x + 0.121) * 1000,
        rearGlassGap:
          (new T.Box3().setFromObject(
            pc.unit.getObjectByName('GR701 starboard tempered glass'),
            true,
          ).min.x -
            harnessBounds.max.x) *
          1000,
        tray: crossings
          .map((points) => new T.Box3().setFromPoints(points))
          .map((bounds) => [bounds.min.y * 1000, bounds.max.y * 1000]),
      },
    };
  });
  expect(fit.visibility).toEqual({
    seatedParts: 12,
    guides: 4,
    concealed: true,
    lit: true,
    inspection: true,
    serviceOpening: true,
  });
  for (const distance of fit.cpuContacts.flat()) {
    expect(
      distance,
      'Heat spreader and cold plate meet at the socket contact plane',
    ).not.toBeNull();
    expect(distance).toBeLessThan(0.1);
  }
  expect(fit.sockets).toEqual(['A1', 'A2', 'B1', 'B2']);
  expect(fit.height).toBeGreaterThanOrEqual(72);
  expect(fit.height).toBeLessThanOrEqual(128.01);
  expect(fit.outerClearance).toBeGreaterThan(0);
  expect(fit.closerToFreeEnd).toBe(true);
  for (const gap of [fit.footGap, fit.deckGap, fit.padGap]) {
    expect(gap).not.toBeNull();
    expect(gap).toBeLessThan(0.1);
  }
  expect(fit.unlit).toEqual([0, 0]);
  expect(fit.lit.every((level) => level > 0)).toBe(true);
  expect(fit.powerRoute.samples.every((count) => count > 0)).toBe(true);
  expect(fit.powerRoute.middle[0]).toBeGreaterThan(30);
  expect(fit.powerRoute.middle[1]).toBeLessThan(48);
  expect(fit.powerRoute.prematureDrop).toBe(false);
  expect(fit.powerRoute.throughMetal).toBe(false);
  expect(fit.powerRoute.inletDimensions[0]).toBeCloseTo(51.5, 1);
  expect(fit.powerRoute.inletDimensions[1]).toBeCloseTo(179, 1);
  for (const [i, tongue] of fit.powerRoute.tongues.entries()) {
    expect(tongue.closed && tongue.relief).toBe(true);
    expect(tongue.euler, 'Each tongue is a single unpierced skin').toBe(2);
    expect(tongue.edges[i === 1 ? 1 : 0]).toBeGreaterThan(60);
    expect(tongue.edges[i === 1 ? 0 : 1]).toBeLessThan(10);
  }
  for (const visible of fit.powerRoute.seeThrough) expect(visible).toBeLessThan(0.06);
  expect(fit.powerRoute.fanClearance).toBeGreaterThan(3);
  expect(fit.powerRoute.leftGlassGap).toBeGreaterThan(8);
  expect(fit.powerRoute.rearGlassGap).toBeGreaterThan(2);
  expect(fit.powerRoute.cableShieldGap).not.toBeNull();
  expect(fit.powerRoute.cableShieldGap).toBeGreaterThan(0);
  expect(fit.powerRoute.tray[0][0]).toBeGreaterThan(83);
  expect(fit.powerRoute.tray[0][1]).toBeLessThan(96);
  expect(fit.powerRoute.tray[1][0]).toBeGreaterThan(-255);
  expect(fit.powerRoute.tray[1][1]).toBeLessThan(-192);
});

test('room-LOD workstation startup defers pc-hero.bpk until case inspection', async ({ page }) => {
  await page.goto('/media/credits.txt');
  const result = await page.evaluate(async () => {
    const scenePath = '/src/scene/';
    const threePath = '/node_modules/three/build/three.module.js';
    const [T, { tower }, { materials }, { hasParts, loadParts }] = await Promise.all([
      import(threePath),
      import(scenePath + 'hardware.ts'),
      import(scenePath + 'materials.ts'),
      import(scenePath + 'blender-library.ts'),
    ]);
    await loadParts('studio');
    const manager = new T.LoadingManager();
    const roomLoaded = new Promise<void>((resolve) => {
      manager.onLoad = resolve;
    });
    const aura = Array.from({ length: 7 }, () => new T.MeshStandardMaterial());
    let heroMountedCalls = 0;
    const pc = tower(new T.Group(), materials(new T.TextureLoader(manager)), aura, manager, {
      roomLod: true,
      mounted() {
        heroMountedCalls++;
      },
    });
    await roomLoaded;
    const roomRotors: string[] = [];
    pc.unit.traverse((node: import('three').Object3D) => {
      if (node.name === 'Fan rotor') roomRotors.push(node.parent?.name ?? '');
    });
    const beforeInspect = {
      pcHeroLoaded: hasParts('pc-hero'),
      hasGpuHero: Boolean(pc.unit.getObjectByName('Diecast frame and thermal module')),
      hasAtxHero: Boolean(pc.unit.getObjectByName('24-pin ATX braided loom and retaining comb')),
      hasCableBaySmoke: Boolean(pc.unit.getObjectByName('GR701 cable bay · smoke')),
      hasFasciaLight: Boolean(pc.unit.getObjectByName('GR701 front assembly · light')),
      hasThorAura: Boolean(pc.unit.getObjectByName('Thor 1600W Titanium III • aura')),
      hasThorOled: Boolean(pc.unit.getObjectByName('Thor OLED power draw')),
      roomLodVisible: Boolean(pc.unit.getObjectByName('GR701 room LOD')?.visible),
      roomRotorCount: roomRotors.length,
    };
    pc.selectDetail(true);
    const deadline = performance.now() + 10_000;
    while (
      (!hasParts('pc-hero') || !pc.unit.getObjectByName('Diecast frame and thermal module')) &&
      performance.now() < deadline
    ) {
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    const afterInspect = {
      pcHeroLoaded: hasParts('pc-hero'),
      hasGpuHero: Boolean(pc.unit.getObjectByName('Diecast frame and thermal module')),
      hasAtxHero: Boolean(pc.unit.getObjectByName('24-pin ATX braided loom and retaining comb')),
      hasCableBaySmoke: Boolean(pc.unit.getObjectByName('GR701 cable bay · smoke')),
      roomLodVisible: Boolean(pc.unit.getObjectByName('GR701 room LOD')?.visible),
      roomGpuRotorsVisible: Boolean(pc.unit.getObjectByName('ROG Astral room fan rotors')?.visible),
      heroMountedCalls,
    };
    pc.selectDetail(false);
    const afterReturn = {
      roomLodVisible: Boolean(pc.unit.getObjectByName('GR701 room LOD')?.visible),
      roomGpuRotorsVisible: Boolean(pc.unit.getObjectByName('ROG Astral room fan rotors')?.visible),
    };
    return { beforeInspect, afterInspect, afterReturn };
  });
  expect(result.beforeInspect).toEqual({
    pcHeroLoaded: false,
    hasGpuHero: false,
    hasAtxHero: false,
    hasCableBaySmoke: false,
    hasFasciaLight: true,
    hasThorAura: true,
    hasThorOled: true,
    roomLodVisible: true,
    roomRotorCount: 11,
  });
  expect(result.afterInspect.pcHeroLoaded).toBe(true);
  expect(result.afterInspect.hasGpuHero).toBe(true);
  expect(result.afterInspect.hasAtxHero).toBe(true);
  expect(result.afterInspect.hasCableBaySmoke).toBe(true);
  expect(result.afterInspect.roomLodVisible).toBe(false);
  expect(result.afterInspect.roomGpuRotorsVisible).toBe(false);
  expect(result.afterInspect.heroMountedCalls).toBeGreaterThanOrEqual(2);
  expect(result.afterReturn).toEqual({
    roomLodVisible: true,
    roomGpuRotorsVisible: true,
  });
});
