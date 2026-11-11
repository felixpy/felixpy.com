export const atlasPrint = { width: 2880, height: 1620, x: 84, y: 145, spanX: 2712, spanY: 1356 };

export function atlasPoint(longitude, latitude) {
  const { x, y, spanX, spanY } = atlasPrint;
  return [x + ((longitude + 180) / 360) * spanX, y + ((90 - latitude) / 180) * spanY];
}
