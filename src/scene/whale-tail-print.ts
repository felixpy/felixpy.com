import * as T from 'three';
import { assetUrl } from '../app/asset-url';
import { deferredDisplayModel, loadDisplayModel } from './display-model';

export function whaleTailPrint(
  bed: T.Group,
  manager: T.LoadingManager,
  options: { roomLod?: boolean; mounted?: (scene: T.Group) => void } = {},
) {
  const model = new T.Group();
  model.name = 'DeepSeek Whale Girl on PEI';
  bed.add(model);
  const authoring =
    import.meta.env.DEV &&
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('review') === 'authoring';
  const useRoomLod = Boolean(options.roomLod && !authoring);
  const roomGroup = useRoomLod ? new T.Group() : model;
  const heroGroup = useRoomLod ? new T.Group() : undefined;
  if (useRoomLod && heroGroup) {
    roomGroup.name = 'Whale Girl room LOD';
    heroGroup.name = 'Whale Girl hero detail';
    heroGroup.visible = false;
    model.add(roomGroup, heroGroup);
  }
  const tip = new T.Vector3();
  let travel = 0;
  let length = 0;
  let surface = 0;
  let crown: T.CatmullRomCurve3;
  let heroReady = false;
  let inspecting = false;

  const sync = () => {
    if (!useRoomLod || !heroGroup) return;
    heroGroup.visible = inspecting && heroReady;
    roomGroup.visible = !heroGroup.visible;
  };

  function update(delta: number) {
    if (length) {
      travel = (travel + delta * 0.045) % length;
      crown.getPointAt(travel / length, tip);
    }
    return { x: tip.x, z: tip.z, height: surface + 0.00048 };
  }

  function applyPlaFinish(part: T.Mesh) {
    const material = part.material as T.MeshStandardMaterial;
    material.onBeforeCompile = (shader) => {
      shader.vertexShader =
        'varying vec2 filamentSurface;\n' +
        shader.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nfilamentSurface=vec2(position.y, normal.y);',
        );
      shader.fragmentShader =
        'varying vec2 filamentSurface;\n' +
        shader.fragmentShader
          .replace(
            '#include <color_fragment>',
            `#include <color_fragment>
              float layerPhase = filamentSurface.x / .00024;
              diffuseColor.rgb *= .985 + .015*cos(layerPhase*6.283185)*(1.-smoothstep(.12,.5,fwidth(layerPhase)));`,
          )
          .replace(
            '#include <opaque_fragment>',
            'outgoingLight+=diffuseColor.rgb*(.19+.12*max(filamentSurface.y,0.));\n#include <opaque_fragment>',
          );
    };
    material.customProgramCacheKey = () => 'whale-pla-finish';
    part.castShadow = false;
  }

  const loadHero = heroGroup
    ? deferredDisplayModel(heroGroup, '/media/models/whale-tail-girl.glb', {
        mesh: applyPlaFinish,
        mounted(scene) {
          heroReady = true;
          sync();
          options.mounted?.(scene);
        },
      })
    : undefined;

  function load() {
    return loadDisplayModel(
      roomGroup,
      useRoomLod ? '/media/models/whale-tail-girl-room.glb' : '/media/models/whale-tail-girl.glb',
      manager,
      {
        mesh: applyPlaFinish,
        mounted(scene) {
          const figure = scene.children.find((child) => Array.isArray(child.userData.crownOutline));
          if (!figure) throw new Error('Missing whale crown outline');
          const outline = figure.userData.crownOutline as number[];
          surface = figure.userData.printHeight as number;
          const points = [];
          for (let i = 0; i < outline.length; i += 2)
            points.push(new T.Vector3(outline[i], 0, outline[i + 1]));
          crown = new T.CatmullRomCurve3(points, true, 'centripetal');
          length = crown.getLength();
          update(0);
        },
      },
    );
  }

  return {
    load,
    update,
    selectDetail(active: boolean) {
      inspecting = active;
      if (active && loadHero && !heroReady) {
        void loadHero(new T.LoadingManager().setURLModifier(assetUrl));
      }
      sync();
    },
    preloadHero() {
      if (loadHero && !heroReady) {
        void loadHero(new T.LoadingManager().setURLModifier(assetUrl));
      }
    },
  };
}
