import type { Environment } from './environment';
import { windowCities as places } from '../content/window-scenes';

type City = Environment['city'];
type LocalConditions = Pick<Environment, 'night' | 'season'>;

const clocks = Object.fromEntries(
  Object.entries(places).map(([city, { timezone }]) => [
    city,
    new Intl.DateTimeFormat('en-CA', {
      timeZone: timezone,
      month: 'numeric',
      hour: 'numeric',
      hourCycle: 'h23',
    }),
  ]),
) as Record<City, Intl.DateTimeFormat>;

export function localConditions(city: City, now = new Date()): LocalConditions {
  const fields = clocks[city].formatToParts(now);
  const month = Number(fields.find((field) => field.type === 'month')?.value);
  const hour = Number(fields.find((field) => field.type === 'hour')?.value);
  const season = month <= 2 || month === 12 ? '冬' : month <= 5 ? '春' : month <= 8 ? '夏' : '秋';
  return { season, night: hour < (season === '冬' ? 7 : 6) || hour >= (season === '夏' ? 20 : 18) };
}

export function weatherScene(code: number): Environment['weather'] {
  if ([71, 73, 75, 77, 85, 86].includes(code)) return '雪';
  if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99].includes(code)) return '雨';
  if ([2, 3, 45, 48].includes(code)) return '阴';
  return code === 0 || code === 1 ? '晴' : '雨';
}
