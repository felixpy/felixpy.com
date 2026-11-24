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
    '/media/models/hexcal-studio.glb',
    '/media/models/lg-oled-g6.glb',
    '/media/models/codex-micro.glb',
    '/media/models/mac-studio-m5-ultra-room.glb',
    '/media/models/prograde-pg05-5.glb',
    '/media/models/dji-mic-2.glb',
    '/media/models/strix-z890-a.glb',
    '/media/models/xpg-d50-fubuki.glb',
    '/media/models/rog-herculx-xh01.glb',
    '/media/models/gr701-lighting-board.glb',
    '/media/models/rog-azoth-extreme.glb',
    '/media/models/rog-harpe-extreme.glb',
    '/media/models/desk-portrait-frame.glb',
    '/media/models/kinto-clk-151.glb',
    '/media/models/mitsubishi-9850.glb',
    '/media/models/nikon-dk33.glb',
    '/media/models/nikon-z8-hardware.glb',
    '/media/models/nikkor-z24-70-sii.glb',
  ],
  north: [
    '/media/models/stationery/career-album.glb',
    '/media/models/window-cradle.glb',
    '/media/models/window-controller.glb',
  ],
  'east-workshop': [
    '/media/models/artek-stool-60.glb',
    '/media/models/bench-instruments.glb',
    '/media/models/selphy-cp1500.glb',
    '/media/models/cz5-y8-painted-shell.glb',
    '/media/models/whale-tail-girl.glb',
    '/media/models/astro-mondrian-600.glb',
  ],
  'south-rear': [
    '/media/models/camp-rack.glb',
    '/media/models/camp-cookware.glb',
    '/media/models/snow-peak-pitch-kit.glb',
    '/media/models/snow-peak-lantern-mugs.glb',
    '/media/models/talon-field-kit.glb',
    '/media/models/camp-field-equipment.glb',
    '/media/models/entry-bench.glb',
    '/media/models/snowminer-es-020.glb',
    '/media/models/parscan-minirail.glb',
    '/media/models/c1-mini-lc.glb',
    '/media/models/vitrine-inventory.glb',
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
