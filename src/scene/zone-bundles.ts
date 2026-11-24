export const ZONE_ENTRY_PREFIX = '__zone_item__:';

export type ZoneBundleId = 'desk' | 'north' | 'east-workshop' | 'south-rear';

export const zoneBundleIds: readonly ZoneBundleId[] = [
  'desk',
  'north',
  'east-workshop',
  'south-rear',
];

export const zoneBundleModels: Record<ZoneBundleId, readonly string[]> = {
  desk: [
    '/media/models/scabbard-ii-xxl.glb',
    '/media/models/hexcal-studio-room.glb',
    '/media/models/lg-oled-g6-room.glb',
    '/media/models/codex-micro-room.glb',
    '/media/models/mac-studio-m5-ultra-room.glb',
    '/media/models/prograde-pg05-5.glb',
    '/media/models/dji-mic-2.glb',
    '/media/models/gr701-room.glb',
    '/media/models/gr701-lighting-board.glb',
    '/media/models/rog-azoth-extreme-room.glb',
    '/media/models/rog-harpe-extreme-room.glb',
    '/media/models/desk-portrait-frame.glb',
    '/media/models/kinto-clk-151.glb',
    '/media/models/mitsubishi-9850.glb',
    '/media/models/nikon-z8-room.glb',
  ],
  north: [
    '/media/models/stationery/career-album.glb',
    '/media/models/window-cradle.glb',
    '/media/models/window-controller.glb',
  ],
  'east-workshop': [
    '/media/models/artek-stool-60.glb',
    '/media/models/bench-instruments-room.glb',
    '/media/models/selphy-cp1500.glb',
    '/media/models/cz5-y8-painted-shell.glb',
    '/media/models/whale-tail-girl-room.glb',
    '/media/models/astro-mondrian-600.glb',
  ],
  'south-rear': [
    '/media/models/camp-rack-room.glb',
    '/media/models/camp-cookware-room.glb',
    '/media/models/snow-peak-pitch-kit-room.glb',
    '/media/models/snow-peak-lantern-mugs-room.glb',
    '/media/models/talon-field-kit-room.glb',
    '/media/models/camp-field-equipment-room.glb',
    '/media/models/entry-bench-room.glb',
    '/media/models/snowminer-es-020.glb',
    '/media/models/parscan-minirail.glb',
    '/media/models/c1-mini-lc.glb',
    '/media/models/vitrine-inventory-room.glb',
    '/media/models/film-archive.glb',
    '/media/models/skog-20303.glb',
    '/media/models/aeron-c7.glb',
  ],
};

const modelToZone = new Map<string, ZoneBundleId>();
for (const zone of zoneBundleIds) {
  for (const model of zoneBundleModels[zone]) {
    modelToZone.set(model, zone);
  }
}

export function zoneBundlePath(zone: ZoneBundleId) {
  return `/media/models/zone-${zone}.glb`;
}

export function zoneForModel(path: string): ZoneBundleId | undefined {
  return modelToZone.get(path);
}
