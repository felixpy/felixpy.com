import * as T from 'three';
import { deferredDisplayModel, filterPrintedArtwork, loadDisplayModel } from './display-model';
import { group } from './geometry';

function ventFinish(material: T.Material | T.Material[]) {
  return (
    !Array.isArray(material) && ['Rear vent finish', 'Intake vent finish'].includes(material.name)
  );
}

function filterMacSurfaces(mesh: T.Mesh, inspection: boolean) {
  const material = mesh.material;
  if (!(material instanceof T.MeshStandardMaterial)) return;
  const vent = ventFinish(material);
  if (
    vent ||
    material.name === 'Bead blasted aluminum' ||
    material.name === 'Laser etched aluminum'
  ) {
    material.roughness = 0.76;
    if (material instanceof T.MeshPhysicalMaterial) material.clearcoat = 0;
  }
  if (!material.map) return;
  material.map.anisotropy = 8;
  if (!vent) return;
  if (inspection) {
    mesh.castShadow = false;
    material.side = T.FrontSide;
    material.depthWrite = false;
    material.transparent = true;
    material.polygonOffset = true;
    material.polygonOffsetFactor = -1;
    material.polygonOffsetUnits = -3;
  }
  material.customProgramCacheKey = () => (inspection ? 'mac-vent-coverage' : 'mac-vent');
  material.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <map_fragment>',
      `vec2 cellDx = dFdx(vMapUv), cellDy = dFdy(vMapUv);
       float cellsPerPixel = max(length(cellDx), length(cellDy));
       float footprint = mix(1.0, 2.7, smoothstep(0.15, 0.38, cellsPerPixel));
       diffuseColor *= textureGrad(map, vMapUv, cellDx * footprint, cellDy * footprint);
       ${
         inspection
           ? `float aperturePixels = 0.68 / max(cellsPerPixel, 0.0001);
       diffuseColor.a *= 1.0 - smoothstep(4.0, 9.0, aperturePixels);
       if (diffuseColor.a < 0.003) discard;`
           : ''
       }`,
    );
  };
}

export function macStudio(
  parent: T.Object3D,
  manager: T.LoadingManager,
  detailMounted: (scene: T.Group) => void,
) {
  const station = group(parent, 'Photo ingest workstation', [-1.09, 0.75, 0.299]);
  const mac = group(station, 'Mac Studio · M5 Ultra · 36-core CPU / 80-core GPU · 512 GB / 16 TB');
  const reader = group(
    station,
    'ProGrade Digital PG05.5 · CFexpress B / SD UHS-II',
    [0.17, 0, 0.041],
  );
  const authoring =
    import.meta.env.DEV && new URLSearchParams(location.search).get('review') === 'authoring';
  const base = '/media/models/mac-studio-m5-ultra';
  const room = group(mac, 'Mac Studio at desk distance');
  const close = group(mac, 'Mac Studio inspection detail');
  let requested = authoring;
  let ready = false;

  function sync() {
    close.visible = requested && ready;
    room.visible = !close.visible;
  }

  const prepareDetail = deferredDisplayModel(close, base + '.glb', {
    mesh: (mesh) => filterMacSurfaces(mesh, true),
    mounted(scene) {
      if (authoring) {
        const coverage: T.Mesh[] = [];
        scene.traverse((part) => {
          if (part instanceof T.Mesh && ventFinish(part.material)) coverage.push(part);
        });
        for (const part of coverage) part.removeFromParent();
      }
      ready = true;
      sync();
      detailMounted(scene);
    },
  });

  sync();
  if (authoring) void prepareDetail(manager);
  else
    loadDisplayModel(room, base + '-room.glb', manager, {
      mesh: (mesh) => filterMacSurfaces(mesh, false),
    });
  loadDisplayModel(reader, '/media/models/prograde-pg05-5.glb', manager, {
    mesh: filterPrintedArtwork,
  });
  return {
    mac,
    reader,
    prepareDetail,
    selectDetail(inspecting: boolean) {
      if (authoring || requested === inspecting) return;
      requested = inspecting;
      if (requested && !ready) void prepareDetail(new T.LoadingManager());
      sync();
    },
  };
}
