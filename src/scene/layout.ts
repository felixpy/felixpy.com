export const roomSize = { west: -1.26, east: 2.52, north: -0.56, south: 3.19, ceiling: 2.71 };
export const windowOpening = {
  wall: roomSize.west,
  z0: -0.22,
  z1: 1.39,
  y0: 0.947,
  y1: 2.3,
  thickness: 0.25,
};
export const desk = {
  left: roomSize.west,
  right: 1.22,
  back: roomSize.north,
  front: 0.43,
  top: 0.75,
};
export const workshopLayout = { x: 2.207, z: 0.69, length: 1.42 };
export const printerStand = { x: 2.111, z: 1.914, width: 0.658, depth: 0.644, yaw: -Math.PI / 2 };

const diagonal = 48 * 0.0254;
const height = (diagonal * 9) / Math.hypot(16, 9);
const width = (height * 16) / 9;
export const display = {
  x: -0.135,
  y: 1.216,
  z: -0.246,
  width,
  height,
  outerWidth: 1.071,
  outerHeight: 0.62,
  surface: 0.003,
};
export const deskSetup = {
  speakerSpacing: (1.2 + 0.2) / 2 + 0.05,
  speakerZ: -0.304,
  mat: { x: display.x, z: 0.226, width: 0.9, depth: 0.4, top: 0.753 },
  inputZ: 0.237,
  codexMicro: { x: -0.668, z: 0.06, yaw: 0.09 },
  lightController: { x: 0.378, z: 0.13 },
};
