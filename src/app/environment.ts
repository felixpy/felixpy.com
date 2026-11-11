import type { Locale } from './locale';

export interface Environment {
  locale: Locale;
  night: boolean;
  lamp: boolean;
  benchLamp: boolean;
  rainAudio: boolean;
  gameAudio: boolean;
  ceiling: number;
  aura: boolean;
  city: '上海' | '纽约';
  weather: '晴' | '阴' | '雨' | '雪';
  season: '春' | '夏' | '秋' | '冬';
  blinds: boolean;
  angle: 0 | 1 | 2;
  quality: 'high' | 'low';
  reducedMotion: boolean;
}

export const initialEnvironment: Environment = {
  locale: 'en',
  night: true,
  lamp: true,
  benchLamp: true,
  rainAudio: true,
  gameAudio: true,
  ceiling: 0.65,
  aura: true,
  city: '上海',
  weather: '雨',
  season: '秋',
  blinds: false,
  angle: 0,
  quality: 'high',
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

const cities = ['上海', '纽约'] as const;
const weather = ['晴', '阴', '雨', '雪'] as const;
const scenes = cities.flatMap((city) =>
  weather.flatMap((condition) =>
    [false, true].map((night) => ({ city, weather: condition, night })),
  ),
);

export function pressRemote(environment: Environment, key: number): Environment {
  switch (key) {
    case 0:
      return { ...environment, blinds: !environment.blinds };
    case 1:
      return environment.blinds
        ? { ...environment, angle: ((environment.angle + 1) % 3) as Environment['angle'] }
        : environment;
    case 2:
      return { ...environment, city: environment.city === '上海' ? '纽约' : '上海' };
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
      return { ...environment, ...alternatives[Math.floor(Math.random() * alternatives.length)] };
    }
    case 5:
      return { ...environment, night: !environment.night };
    default:
      return environment;
  }
}
