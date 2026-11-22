import * as T from 'three';
import { canvasTexture, group, mesh, random, type XYZ } from './geometry';
import type { Palette } from './materials';
import type { Locale } from '../app/locale';
import { printGreeting, travelPrints } from '../content/travel';
import { loadDisplayModel } from './display-model';
import { desk } from './layout';
import { blenderMesh } from './blender-mesh';

const paperSections = new Map<string, T.BufferGeometry>();

export function paperSection(
  card: T.Group,
  format: 'lab-print' | 'instant-film',
  section: string,
  material: T.Material,
) {
  const key = 'stationery/' + format + '-' + section;
  let geometry = paperSections.get(key);
  if (!geometry) {
    geometry = blenderMesh(key);
    paperSections.set(key, geometry);
  }
  const part = mesh(card, geometry, material);
  part.name = key;
  part.userData.printSurface = format + '-' + section;
  part.castShadow = section === 'back' || section === 'edge';
  return part;
}

export function photoEmulsion(image: T.Texture) {
  const ink = new T.MeshPhysicalMaterial({
    name: 'Photographic dyes under satin emulsion',
    map: image,
    roughness: 0.66,
    specularIntensity: 0.13,
  });
  ink.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <opaque_fragment>',
      `vec3 reflected = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
       vec3 inkReflectance = min(vec3(0.93), 1.25 * pow(material.diffuseColor, vec3(0.83)));
       outgoingLight = reflected * inkReflectance / max(material.diffuseColor, vec3(0.0001)) + totalSpecular;
       #include <opaque_fragment>`,
    );
  };
  return ink;
}

export function photoTile(atlas: T.Texture, index: number) {
  const tile = atlas.clone();
  tile.repeat.set(1 / 3, 1 / 2);
  tile.offset.set((index % 3) / 3, Math.floor(index / 3) === 0 ? 0.5 : 0);
  return tile;
}

export function photoPrinter(
  parent: T.Group,
  sample: T.Texture,
  position: XYZ,
  manager: T.LoadingManager,
  defer: (load: () => void) => void,
) {
  const printer = group(parent, 'Canon SELPHY CP1500', position);
  printer.rotation.y = -Math.PI / 2;
  const output = group(printer, 'Belém Tower postcard proof');
  defer(() => {
    void loadDisplayModel(printer, '/media/models/selphy-cp1500.glb', manager, {
      mesh(part) {
        const material = part.material;
        if (!(material instanceof T.MeshStandardMaterial)) return;
        if (material.name !== 'Selphy LCD thumbnail' && material.name !== 'Selphy postcard image')
          return;
        const uv = part.geometry.getAttribute('uv');
        for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
        material.map = sample;
        material.needsUpdate = true;
      },
      mounted(scene) {
        const sheet = scene.children.find((child) => child.userData.selphyProof);
        if (!sheet) return;
        output.position.copy(sheet.position);
        output.quaternion.copy(sheet.quaternion);
        sheet.position.set(0, 0, 0);
        sheet.quaternion.identity();
        output.add(sheet);
      },
    });
  });
  return output;
}

export function deskPhotoFrame(parent: T.Group, manager: T.LoadingManager, image: T.Texture) {
  const tilt = Math.atan(Math.tan((17 * Math.PI) / 180) / Math.SQRT2);
  const center = desk.top + 0.0791 * Math.cos(tilt) + 0.004 * Math.sin(tilt);
  const frame = group(parent, 'Desk portrait', [-0.821, center, 0.089]);
  frame.rotation.set(-tilt, 0.18, 0, 'YXZ');
  image.flipY = false;
  const ink = new T.MeshStandardMaterial({
    name: 'Matte photographic print',
    map: image,
    roughness: 0.96,
  });
  ink.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      '#include <opaque_fragment>',
      `vec3 paperLight = totalDiffuse / max(material.diffuseColor, vec3(0.0001));
       float exposure = dot(paperLight, vec3(0.2126, 0.7152, 0.0722));
       vec3 reflectedInk = material.diffuseColor * mix(vec3(exposure), paperLight, 0.62);
       outgoingLight = reflectedInk / (1.0 + exposure / 1.16)
         + min(totalSpecular, vec3(0.06)) * 0.05;
       #include <opaque_fragment>`,
    );
  };
  void loadDisplayModel(frame, '/media/models/desk-portrait-frame.glb', manager, {
    mesh(part) {
      const finish = part.material;
      if (!(finish instanceof T.MeshStandardMaterial)) return;
      if (finish.name === ink.name) {
        part.material = ink;
        part.castShadow = false;
        finish.dispose();
      } else if (finish.name === 'Cut cover glass') {
        finish.depthWrite = false;
        part.castShadow = false;
      }
    },
  });
  return frame;
}

export function landmarkPrint(
  parent: T.Object3D,
  p: Palette,
  image: T.Texture,
  index: number,
  pos: XYZ,
) {
  const place = travelPrints[index];
  const card = group(parent, place.zh, pos);
  const stock = p.paper.clone();
  stock.color.set('#f5f2eb');
  stock.normalScale.set(0.035, 0.035);
  paperSection(card, 'lab-print', 'face', stock);
  paperSection(card, 'lab-print', 'edge', stock);
  paperSection(card, 'lab-print', 'image', photoEmulsion(image));
  function writeIndex(ctx: CanvasRenderingContext2D, locale: Locale) {
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, 480, 60);
    ctx.fillStyle = '#625a4e';
    ctx.font = '500 26px "IBM Plex Sans", "Studio Han", sans-serif';
    ctx.fillText(
      String(index + 1).padStart(2, '0') + '   /   ' + place[locale].split(' · ')[0],
      8,
      39,
      464,
    );
  }
  const indexMark = canvasTexture(480, 60, (ctx) => writeIndex(ctx, 'en'));
  const indexInk = stock.clone();
  indexInk.map = indexMark;
  paperSection(card, 'lab-print', 'index', indexInk);
  function writeNote(ctx: CanvasRenderingContext2D, locale: Locale) {
    ctx.fillStyle = '#dcd0b6';
    ctx.fillRect(0, 0, 576, 768);
    const rng = random(921 + index);
    for (let i = 0; i < 4200; i++) {
      ctx.fillStyle = i % 2 ? '#efe7d317' : '#9a815b0d';
      ctx.fillRect(rng() * 576, rng() * 768, 0.8, 1.1);
    }
    const age = ctx.createLinearGradient(0, 767, 520, 270);
    age.addColorStop(0, '#9c7c5028');
    age.addColorStop(0.46, '#9c7c5000');
    ctx.fillStyle = age;
    ctx.fillRect(0, 0, 576, 768);
    ctx.fillStyle = '#3d494c';
    ctx.font =
      locale === 'zh' ? '400 36px "Studio Script", KaiTi, serif' : '500 43px Caveat, cursive';
    ctx.save();
    ctx.translate(40, 236);
    ctx.rotate(-0.029);
    ctx.fillText(printGreeting[locale], 0, 0, 496);
    place.note[locale]
      .split('\n')
      .forEach((line, row) => ctx.fillText(line, row * 4, 105 + row * 65, 496));
    ctx.restore();
    ctx.font = '500 36px Caveat, cursive';
    ctx.fillText('— Felix', 390, 507);
  }
  const note = canvasTexture(576, 768, (ctx) => writeNote(ctx, 'en'));
  paperSection(
    card,
    'lab-print',
    'back',
    new T.MeshStandardMaterial({ map: note, roughness: 0.87 }),
  );
  return {
    card,
    setLocale(locale: Locale) {
      writeIndex(indexMark.image.getContext('2d')!, locale);
      writeNote(note.image.getContext('2d')!, locale);
      indexMark.needsUpdate = note.needsUpdate = true;
    },
  };
}
