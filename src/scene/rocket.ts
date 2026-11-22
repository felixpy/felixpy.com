import * as T from 'three';
import { deferredDisplayModel, filterPrintedArtwork } from './display-model';
import { benchEye } from './camera';
import { box, cable, group, mesh, surface, tube } from './geometry';
import type { Palette } from './materials';

export function rocketModel(parent: T.Group, p: Palette, mounted: (model: T.Group) => void) {
  const model = group(parent, 'Standing launch vehicle scale model', [0.232, 0.878, 0.345]);
  const viewer = parent.worldToLocal(new T.Vector3(benchEye.x, benchEye.y, benchEye.z));
  model.rotation.y = Math.atan2(viewer.x - model.position.x, viewer.z - model.position.z);
  const collar = surface('#424d55', 0.38, 0.45);
  box(model, [0.1, 0.002, 0.075], [0, -0.127, 0.003], p.cloth, 0.0009);
  box(model, [0.104, 0.014, 0.079], [0, -0.119, 0.003], p.wood, 0.0018);
  box(model, [0.085, 0.002, 0.06], [0, -0.111, 0.003], p.bronze, 0.0008);
  for (const x of [-0.01, 0.01]) {
    tube(model, [x, -0.11, -0.014], [x, -0.062, -0.014], 0.0017, p.steel);
    tube(model, [x, -0.11, -0.014], [x, -0.107, -0.014], 0.0032, collar);
  }

  const airframe = group(model, 'Airframe and stage interfaces', [0, 0.015, 0]);
  const prepare = deferredDisplayModel(airframe, '/media/models/cz5-y8-painted-shell.glb', {
    mesh: filterPrintedArtwork,
    mounted,
  });

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
  return { model, prepare };
}
