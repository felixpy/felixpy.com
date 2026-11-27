import type { Object3D } from 'three';

export type AppID = 'about' | 'music' | 'game' | 'settings';
export type InspectionLink = {
  url: string;
  region?: { left: number; right: number; top: number; bottom: number; z: number };
};
export type HardwareOrbit = {
  closeFov?: number;
  rearClearance?: number;
  center: [number, number, number];
  azimuth: [number, number, number];
  elevation: [number, number, number];
  distance: [number, number, number];
};

export type Target = {
  id: string;
  label: string;
  english: string;
  object: Object3D;
  prepare?: () => Promise<void> | undefined;
} & (
  | {
      type: 'inspect';
      size: number;
      onInspect?: (held: boolean, reducedMotion: boolean) => void;
      pose?: [number, number, number];
      viewDistance?: number;
      caption?: { en: string; zh: string };
      link?: InspectionLink;
    }
  | {
      type:
        | 'remote'
        | 'window'
        | 'lamp'
        | 'screen-bar'
        | 'bench-lamp'
        | 'tool-board-lamp'
        | 'equipment-track'
        | 'picture-lamp'
        | 'floor-lamp'
        | 'workbench'
        | 'gear'
        | 'bookshelf'
        | 'map'
        | 'map-pin'
        | 'board'
        | 'door';
    }
  | {
      type: 'case';
      orbit?: HardwareOrbit;
      onInspect?: (active: boolean, reducedMotion: boolean) => void;
      caption?: { en: string; zh: string };
    }
  | { type: 'computer'; app?: AppID }
  | { type: 'drawer' | 'key' | 'cabinet'; index: number }
);

export type StudioControls = {
  open(): void;
  exit(): void;
};

export type Station = 'room' | 'bench';
export type WallView = 'board' | 'map' | 'gear' | 'bookshelf';
export type Mode =
  | Station
  | WallView
  | 'inspect'
  | 'case'
  | 'window'
  | 'remote'
  | 'computer'
  | 'drawer'
  | 'returning';
export const isStation = (mode: Mode): mode is Station => mode === 'room' || mode === 'bench';
export const canLookAround = (mode: Mode): mode is Station | 'gear' =>
  isStation(mode) || mode === 'gear';
export const atWindow = (mode: Mode) => mode === 'window' || mode === 'remote';
export const isWallView = (mode: string): mode is WallView =>
  mode === 'board' || mode === 'map' || mode === 'gear' || mode === 'bookshelf';
export const canPick = (mode: Mode) => mode !== 'returning';

const viewTypes = new Set<Target['type']>([
  'window',
  'map',
  'board',
  'gear',
  'bookshelf',
  'case',
  'computer',
  'workbench',
  'drawer',
]);
export const opensStudioView = (target: Target) => viewTypes.has(target.type);
