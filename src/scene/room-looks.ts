import type { RoomLook } from '../app/environment';

export const roomCurves = {
  cinematic: {
    red: [0, 0.105, 0.229, 0.379, 0.517, 0.655, 0.793, 0.902, 1],
    green: [0, 0.112, 0.23, 0.366, 0.504, 0.636, 0.764, 0.888, 1],
    blue: [0, 0.133, 0.247, 0.369, 0.492, 0.612, 0.737, 0.87, 1],
    saturation: 1.035,
  },
  'warm-film': {
    red: [0.014, 0.134, 0.274, 0.418, 0.557, 0.689, 0.808, 0.915, 1],
    green: [0.01, 0.121, 0.247, 0.385, 0.518, 0.647, 0.774, 0.893, 1],
    blue: [0.016, 0.118, 0.23, 0.351, 0.475, 0.609, 0.735, 0.864, 0.991],
    saturation: 0.93,
  },
  'cool-night': {
    red: [0, 0.095, 0.209, 0.335, 0.461, 0.59, 0.731, 0.876, 1],
    green: [0, 0.122, 0.246, 0.373, 0.503, 0.63, 0.761, 0.888, 1],
    blue: [0.005, 0.152, 0.281, 0.408, 0.544, 0.671, 0.795, 0.908, 1],
    saturation: 0.97,
  },
} satisfies Record<
  Exclude<RoomLook, 'neutral'>,
  { red: number[]; green: number[]; blue: number[]; saturation: number }
>;

export function roomLookFilter(look: RoomLook) {
  return look === 'neutral' ? 'none' : `url(#room-look-${look})`;
}
