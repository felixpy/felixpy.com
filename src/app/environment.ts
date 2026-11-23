import type { Locale } from './locale';
import { cityOrder, type WindowCity } from '../content/window-scenes';

export const roomLooks = ['cinematic', 'neutral', 'warm-film', 'cool-night'] as const;
export type RoomLook = (typeof roomLooks)[number];
export function isRoomLook(value: unknown): value is RoomLook {
  return roomLooks.some((look) => look === value);
}

export interface Environment {
  locale: Locale;
  roomLook: RoomLook;
  night: boolean;
  lamp: boolean;
  screenBar: boolean;
  benchLamp: boolean;
  toolBoardLamp: boolean;
  wallLamp: boolean | null;
  pictureLamp: boolean | null;
  floorLamp: boolean | null;
  rainAudio: boolean;
  gameAudio: boolean;
  ceiling: number;
  ceilingLamp: boolean | null;
  aura: boolean;
  city: WindowCity;
  weather: '晴' | '阴' | '雨' | '雪';
  season: '春' | '夏' | '秋' | '冬';
  blinds: boolean;
  angle: 0 | 1 | 2;
  quality: 'high' | 'low';
  automaticQuality: boolean;
  reducedMotion: boolean;
}

export const initialEnvironment: Environment = {
  locale: 'en',
  roomLook: 'cinematic',
  night: true,
  lamp: true,
  screenBar: true,
  benchLamp: true,
  toolBoardLamp: true,
  wallLamp: null,
  pictureLamp: null,
  floorLamp: null,
  rainAudio: true,
  gameAudio: true,
  ceiling: 1,
  ceilingLamp: null,
  aura: true,
  city: '上海',
  weather: '雨',
  season: '秋',
  blinds: true,
  angle: 0,
  quality: 'high',
  automaticQuality: true,
  reducedMotion: false,
};

export const remoteKeys = [
  '百叶升降',
  '叶片倾角',
  '切换城市',
  '切换天气',
  '随机窗景',
  '昼夜切换',
] as const;

const weather = ['晴', '阴', '雨', '雪'] as const;
const scenes = cityOrder.flatMap((city) =>
  weather.flatMap((condition) =>
    [false, true].map((night) => ({ city, weather: condition, night })),
  ),
);

export function applyDaylightLighting(
  environment: Environment,
  night = environment.night,
): Environment {
  return {
    ...environment,
    night,
    lamp: night,
    screenBar: night,
    benchLamp: night,
    toolBoardLamp: night,
    wallLamp: night,
    pictureLamp: night,
    floorLamp: night,
    ceilingLamp: night,
    ceiling: night && environment.ceiling === 0 ? initialEnvironment.ceiling : environment.ceiling,
  };
}

export function switchDaylight(environment: Environment, night: boolean) {
  return night === environment.night ? environment : applyDaylightLighting(environment, night);
}

export function pressRemote(environment: Environment, key: number): Environment {
  switch (key) {
    case 0:
      return { ...environment, blinds: !environment.blinds };
    case 1:
      return environment.blinds
        ? { ...environment, angle: ((environment.angle + 1) % 3) as Environment['angle'] }
        : environment;
    case 2:
      return {
        ...environment,
        city: cityOrder[(cityOrder.indexOf(environment.city) + 1) % cityOrder.length],
      };
    case 3:
      return {
        ...environment,
        weather: environment.weather === '晴' ? '雨' : environment.weather === '雨' ? '雪' : '晴',
      };
    case 4: {
      const alternatives = scenes.filter(
        (scene) =>
          scene.city !== environment.city ||
          scene.weather !== environment.weather ||
          scene.night !== environment.night,
      );
      const scene = alternatives[Math.floor(Math.random() * alternatives.length)];
      return { ...switchDaylight(environment, scene.night), ...scene };
    }
    case 5:
      return applyDaylightLighting(environment, !environment.night);
    default:
      return environment;
  }
}
