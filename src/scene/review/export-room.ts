import * as T from 'three';
import { frameGearWall, gearEye } from '../camera';
import type { StudioModel } from '../studio';
import { exportFinishGeometry, surfaceKey } from '../surface-finish';
import { editableBlindSlats } from '../window';
import { panoramaMeshName } from '../window-depth';

export async function exportRoom(
  model: StudioModel,
  camera: T.PerspectiveCamera,
  renderer: T.WebGLRenderer,
  objectName?: string,
  authoring = false,
) {
  if (authoring) await Promise.all([model.prepareRear(), model.prepareDrawerMedia()]);
  const { GLTFExporter } = await import('three/addons/exporters/GLTFExporter.js');
  const source = objectName ? model.root.getObjectByName(objectName) : model.root;
  if (!source) throw new Error('Unknown studio object: ' + objectName);
  if (authoring) await model.prepareBookExport(source);
  let studio = source.clone();
  const panorama = source.getObjectByName(panoramaMeshName);
  const baked =
    authoring && panorama instanceof T.Mesh
      ? (await import('./bake-waterfront')).bakeWaterfront(renderer, panorama)
      : undefined;
  if (authoring) {
    const geometries = new Map<T.BufferGeometry, T.BufferGeometry>();
    const portable = new Set(
      model.targets
        .filter(
          (t) =>
            t.type === 'inspect' || t.type === 'remote' || t.type === 'door' || t.type === 'drawer',
        )
        .map((t) => t.object),
    );
    const mark = (part: T.Object3D, copy: T.Object3D, cast: boolean) => {
      cast = cast && !portable.has(part) && part.visible;
      if (part instanceof T.Mesh) {
        const mats = Array.isArray(part.material) ? part.material : [part.material];
        copy.userData.studioOccluder =
          cast && part.castShadow && mats.every((material) => !material.transparent);
        if (copy instanceof T.Mesh && part.geometry.getAttribute('normal')) {
          copy.userData.studioSurface = surfaceKey(part.geometry);
          if (!geometries.has(part.geometry))
            geometries.set(part.geometry, exportFinishGeometry(part.geometry));
          copy.geometry = geometries.get(part.geometry)!;
        }
      }
      part.children.forEach((child, i) => mark(child, copy.children[i], cast));
    };
    mark(source, studio, true);
    if (source === model.root) {
      const rack = model.gearWall;
      const view = new T.PerspectiveCamera(gearEye.fov, camera.aspect, camera.near, camera.far);
      frameGearWall(rack, view.aspect, view.position);
      view.rotation.set(gearEye.pitch, gearEye.yaw, 0, 'YXZ');
      view.name = 'Equipment wall';
      studio.add(view);
    }
  }
  studio = editableBlindSlats(studio);
  if (objectName) studio.position.set(0, 0, 0);
  const tracks: T.KeyframeTrack[] = [];
  studio.traverse((child) => {
    if (
      (!authoring &&
        child instanceof T.InstancedMesh &&
        !child.userData.exportInstalledInstances) ||
      child instanceof T.Points ||
      child instanceof T.LineSegments
    )
      child.visible = false;
    if (authoring && child.name === 'Outside glazing surface' && child instanceof T.Mesh)
      child.material = new T.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
      });
    if (
      child.name === panoramaMeshName &&
      child instanceof T.Mesh &&
      child.material instanceof T.ShaderMaterial
    ) {
      if (baked) {
        child.geometry = baked.geometry;
        child.material = baked.material;
        child.userData.waterfrontCamera = baked.calibration;
        child.userData.studioOccluder = false;
      } else {
        child.material = new T.MeshBasicMaterial({
          map: child.material.uniforms.photoA.value,
          side: T.DoubleSide,
        });
      }
    }
    if (child.name !== 'Fan rotor') return;
    child.name = 'Fan rotor ' + (tracks.length + 1);
    const times = Array.from({ length: 61 }, (_, i) => i / 20);
    const quaternions = times.flatMap((time) =>
      new T.Quaternion()
        .setFromAxisAngle(new T.Vector3(0, 0, 1), time * 14 + child.rotation.z)
        .toArray(),
    );
    tracks.push(new T.QuaternionKeyframeTrack(child.name + '.quaternion', times, quaternions));
  });
  if (!objectName) {
    for (const child of [...studio.children])
      if (child instanceof T.Light || child instanceof T.Mesh) studio.remove(child);
  }
  const buffer = await new GLTFExporter()
    .parseAsync(studio, {
      binary: true,
      maxTextureSize: baked?.width ?? (authoring ? 2048 : 1024),
      onlyVisible: !authoring,
      animations: tracks.length ? [new T.AnimationClip('Fan rotors', 3, tracks)] : [],
    })
    .finally(() => {
      baked?.geometry.dispose();
      baked?.material.map?.dispose();
      baked?.material.dispose();
    });
  const url = URL.createObjectURL(new Blob([buffer as ArrayBuffer], { type: 'model/gltf-binary' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = objectName ? 'studio-object.glb' : 'felix-studio.glb';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
