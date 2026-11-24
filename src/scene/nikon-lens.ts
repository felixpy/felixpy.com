import * as T from 'three';
import { blenderMesh } from './blender-mesh';
import { loadDisplayModel } from './display-model';
import { loadStudioTexture } from './ktx2-loader';
import { group, mesh, surface } from './geometry';
import { display, windowOpening } from './layout';
import { coatingLayers, coatingTints, nikkorCoating } from './nikkor-coating';
import { productDetail } from './product-detail';

const darkenedBaffles = new WeakSet<T.Material>();

function mountedOptics(part: T.Mesh) {
  const source = part.material;
  if (!(source instanceof T.MeshStandardMaterial)) return;
  if (
    /^(S II · anti-reflection baffles|S II · blackened spring-steel iris|Diaphragm shear edges)/.test(
      source.name,
    )
  ) {
    if (!darkenedBaffles.has(source)) {
      darkenedBaffles.add(source);
      source.customProgramCacheKey = () => 'nikkor-optical-baffle';
      source.onBeforeCompile = (shader) => {
        shader.uniforms.opticalDarken = { value: new T.Vector3(0.07, 0.08, 0.085) };
        shader.fragmentShader =
          'uniform vec3 opticalDarken;\n' +
          shader.fragmentShader.replace(
            '#include <opaque_fragment>',
            'outgoingLight *= opticalDarken;\n#include <opaque_fragment>',
          );
      };
    }
    return;
  }
  if (source.name.startsWith('Z24-70 entrance pupil')) {
    source.color.set('#111a20');
    source.roughness = 0.65;
    source.metalness = 0;
    source.envMapIntensity = 0.12;
    source.side = T.DoubleSide;
    part.castShadow = part.receiveShadow = false;
    return;
  }
  if (!source.name.startsWith('NIKKOR glass')) return;
  const layer = coatingLayers.findIndex((ending) => source.name.endsWith(ending));
  if (layer < 0) return;
  const finish = nikkorCoating(source.name, layer);
  finish.onBeforeCompile = (shader) => {
    shader.uniforms.coatingTint = { value: new T.Color(coatingTints[layer]) };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 glassWorld;')
      .replace(
        '#include <project_vertex>',
        '#include <project_vertex>\nglassWorld = (modelMatrix * vec4(transformed, 1.)).xyz;',
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform vec3 coatingTint; varying vec3 glassWorld;',
      )
      .replace(
        '#include <opaque_fragment>',
        `vec3 reflected = inverseTransformDirection(reflect(-normalize(vViewPosition), normal), viewMatrix);
        float gain = 0.022 + 0.18 * pow(1.0 - abs(dot(normal, normalize(vViewPosition))), 3.0);
        #ifdef ENVMAP_TYPE_CUBE_UV
        outgoingLight += coatingTint * gain * textureCubeUV(envMap, envMapRotation * reflected, 0.075).rgb * envMapIntensity;
        #endif
        float t = (${windowOpening.wall} - glassWorld.x) / min(-0.0001, reflected.x);
        vec2 glazing = (glassWorld + t * reflected).zy;
        vec2 opening = smoothstep(vec2(${windowOpening.z0}, ${windowOpening.y0}), vec2(${windowOpening.z0 + 0.065}, ${windowOpening.y0 + 0.065}), glazing)
          * (1.0 - smoothstep(vec2(${windowOpening.z1 - 0.065}, ${windowOpening.y1 - 0.065}), vec2(${windowOpening.z1}, ${windowOpening.y1}), glazing));
        float mullion = smoothstep(0.012, 0.022, abs(glazing.x - 0.85));
        float toDisplay = (${display.z + display.surface} - glassWorld.z) / min(-0.0001, reflected.z);
        vec2 screen = abs((glassWorld + reflected * toDisplay).xy - vec2(${display.x}, ${display.y}));
        vec2 panel = 1.0 - smoothstep(vec2(${display.width / 2 - 0.025}, ${display.height / 2 - 0.025}), vec2(${display.width / 2}, ${display.height / 2}), screen);
        outgoingLight += coatingTint * (vec3(0.050,0.078,0.113) * opening.x * opening.y * mullion * step(reflected.x,0.0) * step(0.0,t)
          + vec3(0.025,0.036,0.049) * panel.x * panel.y * step(reflected.z,0.0) * step(0.0,toDisplay));
        #include <opaque_fragment>`,
      );
  };
  finish.customProgramCacheKey = () => 'nikkor-mounted-coating';
  part.material = finish;
  part.renderOrder = layer + 1;
  part.castShadow = part.receiveShadow = false;
}

export function nikkorZoom(parent: T.Object3D, manager: T.LoadingManager) {
  const lens = group(parent, 'NIKKOR Z 24–70mm f/2.8 S II', [0.016, -0.003, 0.023]);
  const hood = group(lens, 'HB-117 bayonet petal hood');
  const shroud = surface('#262627', 0.66);
  const fittings = surface('#232425', 0.44, 0.04);
  const cover = surface('#29292a', 0.61);
  const printing = surface('#dededb', 0.69);
  printing.polygonOffset = true;
  printing.polygonOffsetFactor = -1;
  printing.polygonOffsetUnits = -1;
  const grain = loadStudioTexture(
    new T.TextureLoader(manager),
    '/media/materials/hb117-mold-normal.png',
    { srgb: false, wrap: T.RepeatWrapping, anisotropy: 4 },
  );
  for (const molded of [shroud, cover]) {
    molded.normalMap = grain;
    molded.normalScale.setScalar(0.63);
  }
  for (const [part, material] of Object.entries({
    shell: shroud,
    baffle: surface('#161719', 0.87),
    mount: fittings,
    guides: fittings,
    release: fittings,
    slide: cover,
    lever: cover,
    ink: printing,
  })) {
    mesh(hood, blenderMesh('handheld/hb117-' + part), material).name = 'HB-117 ' + part;
  }
  const barrel = group(lens, 'Z mount flange');
  barrel.rotation.set(-Math.PI / 2, 0, Math.PI);
  const detail = productDetail();
  return loadDisplayModel(barrel, '/media/models/nikkor-z24-70-sii.glb', manager, {
    mesh(part) {
      const finish = part.material instanceof T.Material ? part.material.name : '';
      if (
        finish === 'Z-mount contact · gold over nickel' ||
        finish === 'Z24-70 machined bayonet · nickel plating'
      ) {
        detail.enclosed(part);
      } else {
        mountedOptics(part);
      }
    },
  });
}
