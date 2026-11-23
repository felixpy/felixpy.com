import * as T from 'three';
import type { DeferRoomAsset } from './rear-loading';
import { cabinetSpots } from './cabinet-spots';
import { loadDisplayModel } from './display-model';
import { coatingLayers, coatingTints, nikkorCoating } from './nikkor-coating';
import { box, canvasTexture, group, print, surface, type XYZ } from './geometry';
import type { Palette } from './materials';
import { display, windowOpening } from './layout';
import { productDetail } from './product-detail';

export function collectionVitrine(
  wall: T.Group,
  p: Palette,
  manager: T.LoadingManager,
  deferRoomDetail: DeferRoomAsset,
) {
  const unit = group(wall, 'Low-iron glass collection cabinet', [0.599, 0, 0]);
  const lenses = [
    { variant: 0, model: 'NIKKOR Z 14–24mm f/2.8 S' },
    { variant: 5, model: 'NIKKOR Z 100–400mm f/4.5–5.6 VR S' },
    { variant: 2, model: 'NIKKOR Z 70–200mm f/2.8 VR S II' },
    { variant: 3, model: 'NIKKOR Z 135mm f/1.8 S Plena' },
    { variant: 4, model: 'NIKKOR Z 58mm f/0.95 S Noct' },
  ].map(({ variant, model }) => ({ variant, object: group(unit, model + ' · cabinet mount') }));
  const oak = p.wood.clone(),
    stiles = p.woodVertical.clone();
  oak.color.set('#bf9874');
  stiles.color.copy(oak.color);
  const dark = surface('#343d39', 0.79),
    rails = surface('#554c3f', 0.37, 0.66);
  const w = 1.145,
    d = 0.351;
  for (const x of [-0.502, 0.502])
    for (const z of [0.083, 0.306]) box(unit, [0.047, 0.146, 0.046], [x, 0.073, z], stiles, 0.003);
  box(unit, [w, 0.382, d], [0, 0.328, 0.195], oak, 0.005);
  for (const s of [-1, 1]) {
    box(unit, [0.552, 0.342, 0.018], [s * 0.278, 0.328, 0.374], stiles, 0.003);
    box(unit, [0.066, 0.008, 0.014], [s * 0.079, 0.459, 0.388], rails, 0.002);
  }
  const plinth = box(unit, [w, 0.024, d], [0, 0.508, 0.195], oak.clone(), 0.003);
  plinth.userData.caseShadowReceiver = 'floor';
  box(unit, [w, 0.025, d], [0, 1.2975, 0.195], oak, 0.003);
  box(unit, [w - 0.02, 0.775, 0.009], [0, 0.903, 0.025], dark);
  const backing = canvasTexture(128, 384, (ctx) => {
    const c = ctx.createLinearGradient(0, 0, 0, 384);
    c.addColorStop(0, '#c6b799');
    c.addColorStop(0.13, '#b6a890');
    c.addColorStop(0.45, '#a59e8b');
    c.addColorStop(1, '#888b7e');
    ctx.fillStyle = c;
    ctx.fillRect(0, 0, 128, 384);
    for (let y = 1; y < 384; y += 3) {
      ctx.fillStyle = y % 2 ? '#292c2920' : '#eff0d319';
      ctx.fillRect(0, y, 128, 0.6);
    }
  });
  const back = print(unit, w - 0.03, 0.765, [0, 0.901, 0.0305], backing);
  back.castShadow = false;
  back.userData.caseShadowReceiver = 'back';
  const glass = new T.MeshStandardMaterial({
    color: '#dff2eb',
    transparent: true,
    opacity: 0.026,
    roughness: 0.16,
    metalness: 0,
    envMapIntensity: 0.5,
    depthWrite: false,
  });
  glass.customProgramCacheKey = () => 'vitrine-glass';
  glass.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <opaque_fragment>',
      `float grazing = 1.0 - abs(dot(normal, normalize(vViewPosition)));
       diffuseColor.a = 0.009 + 0.080 * pow(grazing, 3.0);
       outgoingLight = min(outgoingLight, vec3(0.86));
       #include <opaque_fragment>`,
    );
  };
  const edge = surface('#6f9188', 0.21, 0.25);
  function pane(size: XYZ, point: XYZ) {
    const panel = box(unit, size, point, glass);
    panel.castShadow = panel.receiveShadow = false;
    return panel;
  }
  for (const x of [-w / 2 + 0.008, w / 2 - 0.008]) {
    pane([0.005, 0.771, d - 0.008], [x, 0.903, 0.193]);
    for (const z of [0.032, 0.358]) box(unit, [0.011, 0.772, 0.012], [x, 0.903, z], rails, 0.0015);
  }
  pane([w - 0.027, 0.006, d - 0.061], [0, 0.968, 0.185]);
  box(unit, [w - 0.034, 0.004, 0.002], [0, 0.967, 0.331], edge, 0.0004);
  for (const x of [-0.544, 0.544])
    for (const z of [0.069, 0.303]) box(unit, [0.035, 0.008, 0.025], [x, 0.962, z], rails, 0.001);
  for (const [i, s] of [-1, 1].entries()) {
    const z = 0.35 + i * 0.009;
    pane([w / 2 + 0.006, 0.749, 0.004], [s * w * 0.245, 0.903, z]);
    box(unit, [0.002, 0.745, 0.003], [-s * 0.012, 0.903, z], edge, 0.0004);
    box(unit, [0.009, 0.051, 0.009], [s * 0.523, 0.87, z + 0.005], rails, 0.002);
  }
  for (const y of [0.526, 1.28]) {
    box(unit, [w - 0.016, 0.009, 0.022], [0, y, 0.355], rails, 0.0015);
    box(unit, [w - 0.019, 0.002, 0.002], [0, y + 0.004, 0.353], p.black);
  }
  const spots = cabinetSpots(unit, manager);
  deferRoomDetail(spots.load);
  const finishes = new Map<T.Material, T.Material>();
  const assembledLens = productDetail();
  const behindRearCap = new Set([
    'Z14-24 · plated CPU contacts',
    'Telephoto Z mount · plated contacts',
    '100-400 S · gold contact pads',
  ]);
  const cabinetInverse = unit.matrixWorld.clone();
  const mark =
    typeof location !== 'undefined' &&
    new URLSearchParams(location.search).get('studio-vitrine-timing') === 'on'
      ? (phase: string, startTime?: number) =>
          performance.mark(`studio-vitrine-${phase}`, { startTime })
      : undefined;
  deferRoomDetail(() =>
    loadDisplayModel(unit, '/media/models/vitrine-inventory.glb', manager, {
      mark,
      mounted(scene) {
        scene.traverse(spots.illuminate);
        mark?.('lights-end');
        const parts = [...scene.children];
        scene.updateWorldMatrix(true, true);
        mark?.('lens-attach-start');
        for (const lens of parts) {
          const target = lenses.find((item) => item.variant === lens.userData.opticalVariant);
          if (!target) continue;
          const cap = parts.find(
            (part) => part.name.startsWith('LF-N1') && part.position.equals(lens.position),
          );
          const bounds = new T.Box3().setFromObject(lens);
          if (cap) bounds.expandByObject(cap);
          const holder = target.object;
          holder.position.copy(unit.worldToLocal(bounds.getCenter(new T.Vector3())));
          holder.quaternion.copy(lens.quaternion);
          holder.attach(lens);
          if (cap) {
            holder.attach(cap);
            lens.traverse((part) => {
              if (
                part instanceof T.Mesh &&
                part.material instanceof T.Material &&
                behindRearCap.has(part.material.name)
              )
                assembledLens.enclosed(part);
            });
          }
        }
        mark?.('lens-attach-end');
      },
      mesh(part) {
        const source = part.material;
        const pupil =
          source instanceof T.MeshStandardMaterial &&
          /^Z(\d+)(?:-\d+)? entrance pupil/.exec(source.name);
        if (pupil) {
          source.side = T.DoubleSide;
          source.customProgramCacheKey = () => 'nikkor-entrance-pupil';
          source.onBeforeCompile = (shader) => {
            shader.uniforms.pupilFocalLength = { value: Number(pupil[1]) / 1000 };
            const telephoto = /^Z(?:70-200|100-400) /.test(source.name);
            shader.uniforms.pupilRoughness = { value: telephoto ? 0.08 : 0.24 };
            shader.uniforms.pupilGain = { value: telephoto ? 0.41 : 1 };
            shader.vertexShader = shader.vertexShader
              .replace(
                '#include <common>',
                '#include <common>\nvarying vec3 pupilOffset; varying vec3 pupilWorld;',
              )
              .replace(
                '#include <project_vertex>',
                '#include <project_vertex>\npupilOffset = mat3(modelMatrix) * vec3(position.x, 0., position.z); pupilWorld = (modelMatrix * vec4(position, 1.)).xyz;',
              );
            shader.fragmentShader = shader.fragmentShader
              .replace(
                '#include <common>',
                '#include <common>\nuniform float pupilFocalLength, pupilRoughness, pupilGain; varying vec3 pupilOffset; varying vec3 pupilWorld;',
              )
              .replace(
                '#include <opaque_fragment>',
                `vec3 ray = normalize(pupilWorld - cameraPosition);
                vec3 chief = normalize(ray - pupilOffset / pupilFocalLength);
                #ifdef ENVMAP_TYPE_CUBE_UV
                  outgoingLight = textureCubeUV(envMap, envMapRotation * chief, pupilRoughness).rgb * envMapIntensity * pupilGain * vec3(0.73,0.76,0.71);
                #else
                  outgoingLight = vec3(0.017,0.020,0.019);
                #endif
                #include <opaque_fragment>`,
              );
          };
          part.castShadow = part.receiveShadow = false;
          return;
        }
        if (
          source instanceof T.Material &&
          (source.name.startsWith('Optical flock') ||
            source.name === 'Plena · antireflection velvet')
        ) {
          const stop = finishes.get(source) ?? new T.MeshBasicMaterial({ color: '#090d0e' });
          if (source.name.startsWith('Plena') || /Noct bore|70-200 S II bore/.test(source.name)) {
            stop.side = T.DoubleSide;
          }
          finishes.set(source, stop);
          part.material = stop;
          part.castShadow = false;
          return;
        }
        if (
          source instanceof T.MeshStandardMaterial &&
          /^(Optical cell|Graphite diaphragm|Diaphragm shear|Plena · anodized optical cell)/.test(
            source.name,
          )
        ) {
          if (!finishes.has(source)) {
            source.customProgramCacheKey = () => 'nikkor-optical-baffle';
            source.onBeforeCompile = (shader) => {
              shader.uniforms.opticalDarken = { value: new T.Vector3(0.037, 0.05, 0.056) };
              shader.fragmentShader =
                'uniform vec3 opticalDarken;\n' +
                shader.fragmentShader.replace(
                  '#include <opaque_fragment>',
                  'outgoingLight *= opticalDarken;\n#include <opaque_fragment>',
                );
            };
            finishes.set(source, source);
          }
          return;
        }
        if (Array.isArray(source) || !source.name.startsWith('NIKKOR glass')) return;
        const layer = coatingLayers.findIndex((name) => source.name.endsWith(name));
        if (layer < 0) return;
        const calibratedGlass = /100-400 S|70-200 S II|14-24 S|135 Plena|58 f0.95 Noct/.test(
          source.name,
        );
        let finish = finishes.get(source);
        if (!finish) {
          unit.updateWorldMatrix(true, false);
          cabinetInverse.copy(unit.matrixWorld).invert();
          finish = nikkorCoating(source.name, layer);
          finish.onBeforeCompile = (shader) => {
            shader.uniforms.cabinetInverse = { value: cabinetInverse };
            shader.uniforms.caseSpotCenters = { value: spots.centers };
            shader.uniforms.caseSpotAxes = { value: spots.axes };
            shader.uniforms.casePower = spots.power;
            const tints = source.name.includes('58 f0.95 Noct')
              ? ['#b0c2ac', '#cfb295', '#9eb6bb', '#c3a9b5']
              : coatingTints;
            shader.uniforms.coatingTint = { value: new T.Color(tints[layer]) };
            shader.uniforms.coatingCalibrated = { value: calibratedGlass ? 1 : 0 };
            shader.vertexShader = shader.vertexShader
              .replace(
                '#include <common>',
                '#include <common>\nuniform mat4 cabinetInverse; varying vec3 cellPosition; varying vec3 glassWorld;',
              )
              .replace(
                '#include <project_vertex>',
                '#include <project_vertex>\nglassWorld=(modelMatrix*vec4(transformed,1.)).xyz; cellPosition=(cabinetInverse*vec4(glassWorld,1.)).xyz;',
              );
            shader.fragmentShader = shader.fragmentShader
              .replace(
                '#include <common>',
                '#include <common>\nuniform mat4 cabinetInverse; uniform vec3 coatingTint; uniform float coatingCalibrated; uniform vec3 caseSpotCenters[3]; uniform vec3 caseSpotAxes[3]; uniform float casePower; varying vec3 cellPosition; varying vec3 glassWorld;',
              )
              .replace(
                '#include <opaque_fragment>',
                `vec3 bounce = inverseTransformDirection(reflect(-normalize(vViewPosition), normal), viewMatrix);
                vec3 cabinetRay = mat3(cabinetInverse) * bounce;
                float caseReflection = 0.0;
                for (int spot = 0; spot < 3; ++spot) {
                  vec3 axis = caseSpotAxes[spot];
                  float facing = -dot(cabinetRay, axis);
                  float t = dot(cellPosition-caseSpotCenters[spot], axis) / max(facing, 0.001);
                  float radius = distance(cellPosition + t*cabinetRay, caseSpotCenters[spot]);
                  caseReflection += (1.0-smoothstep(0.003,0.006,radius))*smoothstep(0.62,0.90,facing)*step(0.0,t);
                }
                float toWindow = (${windowOpening.wall} - glassWorld.x) / min(-0.0001,bounce.x);
                vec2 glazing = (glassWorld + bounce * toWindow).zy;
                vec2 opening = smoothstep(vec2(${windowOpening.z0}, ${windowOpening.y0}),
                  vec2(${windowOpening.z0 + 0.06}, ${windowOpening.y0 + 0.06}),glazing)
                  * (1.0-smoothstep(vec2(${windowOpening.z1 - 0.06}, ${windowOpening.y1 - 0.06}),
                    vec2(${windowOpening.z1}, ${windowOpening.y1}),glazing));
                float mullion = smoothstep(0.012,0.022,abs(glazing.x-0.85));
                float toScreen = (${display.z + display.surface} - glassWorld.z) / min(-0.0001,bounce.z);
                vec2 screen = abs((glassWorld + bounce * toScreen).xy-vec2(${display.x},${display.y}));
                vec2 oled = 1.0-smoothstep(vec2(${display.width / 2 - 0.03},${display.height / 2 - 0.03}),
                  vec2(${display.width / 2},${display.height / 2}),screen);
                if (coatingCalibrated > 0.5) {
                  float gain = 0.022 + 0.18 * pow(1.0-abs(dot(normal,normalize(vViewPosition))), 3.0);
                  #ifdef ENVMAP_TYPE_CUBE_UV
                    vec3 coat = textureCubeUV(envMap, envMapRotation * bounce, 0.075).rgb * envMapIntensity;
                    outgoingLight += coatingTint * coat * gain;
                  #endif
                  float toOak = (0.0305-cellPosition.z) / min(-0.0001,cabinetRay.z);
                  vec2 oak = abs((cellPosition + toOak*cabinetRay).xy - vec2(0.,1.126));
                  float backing = (1.0-smoothstep(0.52,0.59,oak.x)) * (1.0-smoothstep(0.13,0.18,oak.y));
                  outgoingLight += coatingTint * vec3(0.15,0.115,0.085) * gain * backing * step(cabinetRay.z,0.0);
                }
                outgoingLight += coatingTint * (caseReflection * casePower * 0.95 + vec3(0.064,0.092,0.12) *
                  opening.x*opening.y*mullion*step(bounce.x,0.0) + vec3(.036,.050,.058)*oled.x*oled.y*step(bounce.z,0.0));
                #include <opaque_fragment>`,
              );
          };
          finish.customProgramCacheKey = () => 'nikkor-vitrine-coating';
          finishes.set(source, finish);
        }
        part.material = finish;
        part.renderOrder = layer + 1;
        part.receiveShadow = part.castShadow = false;
      },
    }),
  );
  const archive = group(unit, 'Photographic film and mounted transparencies', [0.275, 0.52, 0.17]);
  deferRoomDetail(() =>
    loadDisplayModel(archive, '/media/models/film-archive.glb', manager, {
      mounted: (scene) => scene.traverse(spots.illuminate),
    }),
  );
  return { unit, lightPower: spots.power };
}
