import * as T from 'three';
import { loadDisplayModel } from './display-model';
import fixtures from './cabinet-light-layout.json';

export function cabinetSpots(unit: T.Group, manager: T.LoadingManager) {
  const centers = fixtures.map(() => new T.Vector3());
  const axes = centers.map(() => new T.Vector3());
  const optics = fixtures.map(({ beam, peak }) => {
    const halfPowerAngle = T.MathUtils.degToRad(beam / 2);
    const edge = Math.cos(halfPowerAngle * 1.22);
    return new T.Vector3(edge, 2 * Math.cos(halfPowerAngle) - edge, peak);
  });
  const power = { value: 0.55 };
  const visibilityFallback = new T.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
  visibilityFallback.needsUpdate = true;
  const visibility = { value: visibilityFallback as T.Texture };
  const visibilityReady = { value: 0 };
  const inverse = new T.Matrix4();
  const finishes = new WeakMap<T.Material, T.Material>();
  let diffuser: T.MeshStandardMaterial | undefined;

  function illuminate(obj: T.Object3D) {
    if (!(obj instanceof T.Mesh) || !(obj.material instanceof T.MeshStandardMaterial)) return;
    const source = obj.material;
    const existing = finishes.get(source);
    if (existing) {
      obj.material = existing;
      return;
    }
    const finish = source.clone();
    const receiver = obj.userData.caseShadowReceiver as 'floor' | 'back' | undefined;
    const receiverMode = receiver === 'floor' ? 1 : receiver === 'back' ? 2 : 0;
    const cacheKey = source.customProgramCacheKey();
    const compile = source.onBeforeCompile;
    finish.customProgramCacheKey = () => cacheKey + '-cabinet';
    finish.onBeforeCompile = (shader, renderer) => {
      compile.call(finish, shader, renderer);
      shader.uniforms.caseEmitters = { value: centers };
      shader.uniforms.caseAxes = { value: axes };
      shader.uniforms.caseOptics = { value: optics };
      shader.uniforms.caseDimmer = power;
      shader.uniforms.caseToWorld = { value: unit.matrixWorld };
      shader.uniforms.caseFromWorld = { value: inverse };
      shader.uniforms.caseVisibility = visibility;
      shader.uniforms.caseVisibilityReady = visibilityReady;
      shader.uniforms.caseReceiverMode = { value: receiverMode };
      shader.vertexShader =
        'uniform mat4 caseFromWorld; varying vec3 casePoint;\n' +
        shader.vertexShader.replace(
          '#include <project_vertex>',
          `#include <project_vertex>
          casePoint = (caseFromWorld * vec4(cameraPosition + transpose(mat3(viewMatrix)) * mvPosition.xyz, 1.)).xyz;`,
        );
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <aomap_fragment>',
        `#include <aomap_fragment>
        if (caseReceiverMode > 0.5 && caseReceiverMode < 1.5) {
          vec2 floorUV = vec2(casePoint.x / 1.145 + 0.5,
                            0.25 * clamp((casePoint.z - 0.0195) / 0.351, 0.001, 0.999));
          float contactVisibility = mix(1.0, texture2D(caseVisibility, floorUV).b, caseVisibilityReady);
          reflectedLight.indirectDiffuse *= contactVisibility;
          reflectedLight.indirectSpecular *= contactVisibility;
        }`,
      );
      shader.fragmentShader =
        `varying vec3 casePoint;
        uniform mat4 caseToWorld; uniform vec3 caseEmitters[5], caseAxes[5], caseOptics[5];
        uniform float caseDimmer;
        uniform sampler2D caseVisibility;
        uniform float caseVisibilityReady;
        uniform float caseReceiverMode;
        ` +
        shader.fragmentShader.replace(
          '#include <lights_fragment_begin>',
          `#include <lights_fragment_begin>
        #ifdef RE_Direct
        if (caseDimmer > 0.001 && casePoint.z > 0.019 && casePoint.z < 0.35 &&
            abs(casePoint.x) < 0.565 && casePoint.y > 0.5195 && casePoint.y < 1.2851) {
          bool upper = casePoint.y >= 0.965;
          vec3 visibleFromEmitter = vec3(1.0);
          if (caseReceiverMode > 0.5) {
            float atlasV = caseReceiverMode < 1.5
              ? 0.25 * clamp((casePoint.z - 0.0195) / 0.351, 0.001, 0.999)
              : (upper ? 0.625 + 0.375 * clamp((casePoint.y - 0.965) / 0.320, 0.001, 0.999)
                       : 0.25 + 0.375 * clamp((casePoint.y - 0.520) / 0.445, 0.001, 0.999));
            visibleFromEmitter = texture2D(caseVisibility, vec2(casePoint.x / 1.145 + 0.5, atlasV)).rgb;
          }
          for (int emitter = 0; emitter < 5; ++emitter) {
            if (upper != (emitter < 3)) continue;
            vec3 toPupil = caseEmitters[emitter] - casePoint;
            float r2 = max(dot(toPupil,toPupil), 0.00006);
            vec3 toward = toPupil * inversesqrt(r2);
            vec3 optic = caseOptics[emitter];
            float beam = smoothstep(optic.x,optic.y,dot(-toward,caseAxes[emitter]));
            IncidentLight displayLight;
            displayLight.direction = mat3(viewMatrix) * mat3(caseToWorld) * toward;
            displayLight.color = vec3(1.0,0.723,0.423) * (caseDimmer*optic.z*beam/r2);
            displayLight.color *= visibleFromEmitter[emitter < 3 ? emitter : emitter-3];
            displayLight.visible = true;
            RE_Direct(displayLight,geometryPosition,geometryNormal,geometryViewDir,geometryClearcoatNormal,material,reflectedLight);
          }
        }
        #endif`,
        );
    };
    finishes.set(source, finish);
    finishes.set(finish, finish);
    obj.material = finish;
  }

  function load() {
    unit.updateWorldMatrix(true, false);
    inverse.copy(unit.matrixWorld).invert();
    new T.TextureLoader(manager).load('/media/lighting/cabinet-spot-visibility.png', (loaded) => {
      visibilityFallback.dispose();
      visibility.value = loaded;
      visibilityReady.value = 1;
    });
    return loadDisplayModel(unit, '/media/models/c1-mini-lc.glb', manager, {
      mesh(part) {
        part.castShadow = false;
        if (
          part.material instanceof T.MeshStandardMaterial &&
          part.material.name.startsWith('C1-mini warm white collimator')
        )
          diffuser = part.material;
      },
      mounted(scene) {
        const rail = scene.getObjectByName('C1_magnetic_rail')!;
        const fixture = scene.getObjectByName('C1_magnetic_shoe')!;
        fixture.removeFromParent();
        rail.position.set(0, 1.285, 0.31);
        const lowerRail = rail.clone();
        lowerRail.position.y = 0.965;
        scene.add(lowerRail);
        for (const [index, { x, shelf, aim }] of fixtures.entries()) {
          const head = fixture.clone();
          head.position.set(x, shelf - 0.0073, 0.31);
          scene.add(head);
          const pan = head.getObjectByName('C1_pan')!;
          const tilt = head.getObjectByName('C1_tilt')!;
          const pupil = head.getObjectByName('C1_exit_pupil')!;
          const target = new T.Vector3().fromArray(aim);
          scene.updateWorldMatrix(true, true);
          const pivot = tilt.getWorldPosition(new T.Vector3()).applyMatrix4(inverse);
          const direction = target.clone().sub(pivot);
          const lateral = pupil.parent!.position.x;
          const yaw =
            Math.atan2(-direction.x, -direction.z) +
            Math.asin(lateral / Math.hypot(direction.x, direction.z));
          pan.rotation.y = yaw;
          direction.applyAxisAngle(new T.Vector3(0, 1, 0), -yaw);
          tilt.rotation.x = Math.atan2(-direction.z, -direction.y);
          scene.updateWorldMatrix(true, true);
          const origin = pupil.getWorldPosition(new T.Vector3()).applyMatrix4(inverse);
          const axis = target.clone().sub(origin).normalize();
          head.name = 'C1-mini-LC · ' + (index + 1);
          centers[index].copy(origin);
          axes[index].copy(axis);
        }
        if (diffuser) diffuser.emissiveIntensity = power.value * 3;
      },
    });
  }

  unit.traverse(illuminate);
  return {
    load,
    illuminate,
    centers: centers.slice(0, 3),
    axes: axes.slice(0, 3),
    power,
  };
}
