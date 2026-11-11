import * as T from 'three';
import { box, cable, canvasTexture, group, mesh, print, surface, tube } from './geometry';
import type { Palette } from './materials';

export function rocketModel(parent: T.Group, p: Palette) {
  const model = group(parent, 'Standing launch vehicle scale model', [-0.733, 0.878, 0.028]);
  model.rotation.y = -0.16;
  const satinWhite = p.plaster.clone();
  satinWhite.color.set('#e5e0d7');
  satinWhite.roughness = 0.46;
  satinWhite.normalScale.set(0.42, 0.42);
  const missionBlue = satinWhite.clone();
  missionBlue.color.set('#315774');
  const collar = surface('#424d55', 0.38, 0.45);
  box(model, [0.104, 0.016, 0.079], [0, -0.12, 0.003], p.woodDark, 0.003);
  box(model, [0.096, 0.002, 0.07], [0, -0.111, 0.003], collar, 0.001);
  tube(model, [0, -0.111, -0.007], [0, -0.068, -0.007], 0.0017, p.steel);
  tube(model, [0, -0.111, -0.007], [0, -0.107, -0.007], 0.0032, collar);

  const airframe = group(model, 'Airframe and stage interfaces', [0, 0.015, 0]);
  const coreRadius = 0.0157;
  const profile = [
    [0, -0.092],
    [0.0138, -0.092],
    [coreRadius, -0.082],
    [coreRadius, 0.087],
    [0.019, 0.1],
    [0.019, 0.137],
    [0.0186, 0.143],
    [0.016, 0.152],
    [0.011, 0.163],
    [0.0054, 0.173],
    [0.0014, 0.177],
    [0, 0.178],
  ];
  mesh(
    airframe,
    new T.LatheGeometry(
      profile.map(([r, y]) => new T.Vector2(r, y)),
      64,
    ),
    satinWhite,
  );
  mesh(
    airframe,
    new T.CylinderGeometry(0.01915, 0.01915, 0.0036, 64, 1, true),
    missionBlue,
    [0, 0.107, 0],
  );
  for (const [y, r] of [
    [-0.076, 0.01586],
    [0.037, 0.01584],
    [0.086, 0.01586],
    [0.101, 0.01915],
  ]) {
    mesh(airframe, new T.CylinderGeometry(r, r, 0.0011, 64), collar, [0, y, 0]);
  }
  const inscription = canvasTexture(256, 768, (ctx) => {
    ctx.fillStyle = '#224f79';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.font = '700 132px "Studio Han", "Microsoft YaHei", sans-serif';
    Array.from('中国航天').forEach((character, i) => ctx.fillText(character, 128, 117 + i * 178));
  });
  const lettering = mesh(
    airframe,
    new T.CylinderGeometry(0.01585, 0.01585, 0.046, 48, 1, true, -0.47, 0.94),
    new T.MeshStandardMaterial({ map: inscription, alphaTest: 0.4, roughness: 0.51 }),
    [0, 0.058, 0],
  );
  lettering.name = '中国航天 · painted on the core stage';
  lettering.castShadow = lettering.receiveShadow = false;

  const engines = group(
    model,
    'First-stage thrust frame and four gimballed engines',
    [0, 0.015, 0],
  );
  engines.scale.set(0.68, 1, 0.68);
  const titanium = surface('#6f7478', 0.36, 0.63);
  const liner = surface('#333538', 0.72, 0.36);
  const bolts = surface('#7b7267', 0.48, 0.56);
  tube(engines, [0, -0.0942, 0], [0, -0.0913, 0], 0.0206, liner);
  mesh(engines, new T.TorusGeometry(0.0188, 0.00065, 7, 56), titanium, [0, -0.0946, 0]).rotation.x =
    Math.PI / 2;
  for (let i = 0; i < 12; i++) {
    const angle = (i * Math.PI) / 6;
    const x = 0.019 * Math.cos(angle),
      z = 0.019 * Math.sin(angle);
    tube(engines, [x, -0.0952, z], [x, -0.0942, z], 0.00066, bolts);
  }
  const nozzleProfile = [
    [0.0031, -0.0065],
    [0.0036, -0.0092],
    [0.0047, -0.0118],
    [0.0065, -0.0149],
    [0.0071, -0.0162],
    [0.0069, -0.0167],
    [0.0063, -0.0167],
    [0.0059, -0.0154],
    [0.0043, -0.0123],
    [0.0032, -0.0094],
    [0.00265, -0.0074],
    [0.0031, -0.0065],
  ];
  const nozzle = new T.LatheGeometry(
    nozzleProfile.reverse().map(([radius, y]) => new T.Vector2(radius, y)),
    48,
  );
  for (const x of [-0.009, 0.009])
    for (const z of [-0.009, 0.009]) {
      const engine = group(engines, 'Gimbal, feed pipe and open nozzle', [x, -0.0913, z]);
      tube(engine, [0, -0.0032, 0], [0, 0, 0], 0.004, collar);
      const joint = mesh(engine, new T.SphereGeometry(0.0034, 20, 12), titanium, [0, -0.0039, 0]);
      joint.scale.y = 0.7;
      tube(engine, [0, -0.0071, 0], [0, -0.0052, 0], 0.0032, collar);
      mesh(engine, nozzle, titanium);
      const throat = mesh(engine, new T.CircleGeometry(0.00265, 24), liner, [0, -0.0075, 0]);
      throat.rotation.x = Math.PI / 2;
      const radial = Math.sign(x);
      cable(
        engine,
        [
          [radial * 0.0032, -0.0015, 0.002],
          [radial * 0.0046, -0.0037, 0.002],
          [radial * 0.0045, -0.0062, 0.001],
          [radial * 0.0029, -0.0064, 0.0005],
        ],
        0.00059,
        bolts,
      );
      tube(
        engine,
        [-radial * 0.0041, -0.0008, 0],
        [-radial * 0.003, -0.0053, 0],
        0.00069,
        titanium,
      );
    }
  const boosterProfile = [
    [0, -0.085],
    [0.0059, -0.085],
    [0.0079, -0.079],
    [0.008, 0.003],
    [0.0077, 0.012],
    [0.0054, 0.022],
    [0.0021, 0.031],
    [0, 0.034],
  ];
  const boosterShell = new T.LatheGeometry(
    boosterProfile.map(([r, y]) => new T.Vector2(r, y)),
    48,
  );
  for (let i = 0; i < 4; i++) {
    const angle = Math.PI / 4 + (i * Math.PI) / 2;
    const mount = group(airframe, 'Booster attachment struts');
    mount.rotation.y = angle;
    for (const y of [-0.055, 0.0])
      box(mount, [0.0048, 0.0042, 0.007], [0, y, 0.017], collar, 0.0006);
    const booster = group(mount, 'Strap-on booster', [0, 0, 0.0242]);
    mesh(booster, boosterShell, satinWhite);
    mesh(
      booster,
      new T.CylinderGeometry(0.00808, 0.00808, 0.0025, 36, 1, true),
      missionBlue,
      [0, -0.006, 0],
    );
    mesh(booster, nozzle, titanium, [0, -0.081, 0]).scale.set(0.63, 0.88, 0.63);
  }
  const plaque = canvasTexture(512, 96, (ctx) => {
    ctx.fillStyle = '#43494c';
    ctx.fillRect(0, 0, 512, 96);
    ctx.fillStyle = '#e2ddd0';
    ctx.font = '500 36px "IBM Plex Sans", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('FLIGHT STUDY   /   LV–01', 256, 61);
  });
  print(model, 0.078, 0.009, [0, -0.12, 0.043], plaque).castShadow = false;
  return model;
}
