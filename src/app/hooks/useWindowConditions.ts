import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react';
import type { Environment } from '../environment';

type City = Environment['city'];
type LocalConditions = Pick<Environment, 'night' | 'season'>;
type WeatherResponse = {
  current?: { weather_code?: number; is_day?: number };
  daily?: { sunrise?: number[]; sunset?: number[] };
};

const places: Record<City, { latitude: number; longitude: number; timezone: string }> = {
  上海: { latitude: 31.23, longitude: 121.47, timezone: 'Asia/Shanghai' },
  纽约: { latitude: 40.71, longitude: -74.01, timezone: 'America/New_York' },
};
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

export function useWindowConditions(
  city: City,
  enabled: boolean,
  update: Dispatch<SetStateAction<Environment>>,
) {
  const manual = useRef({ city, weather: false, night: false });
  const [resolved, setResolved] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    if (manual.current.city !== city) manual.current = { city, weather: false, night: false };
    let daylight: { sunrise: number; sunset: number } | undefined;
    let mostRecentIsDay: number | undefined;
    let alive = true;
    let controller: AbortController | undefined;

    function apply(weather?: Environment['weather']) {
      const now = new Date();
      const local = localConditions(city, now);
      const today = now.getTime() / 1000;
      const currentDaylight =
        daylight && Math.abs(daylight.sunset - today) < 18 * 3600 ? daylight : undefined;
      const night = currentDaylight
        ? today < currentDaylight.sunrise || today >= currentDaylight.sunset
        : mostRecentIsDay === undefined
          ? local.night
          : mostRecentIsDay === 0;
      update((current) =>
        current.city !== city
          ? current
          : {
              ...current,
              night: manual.current.night ? current.night : night,
              season: local.season,
              weather: manual.current.weather || !weather ? current.weather : weather,
            },
      );
    }

    async function refresh() {
      controller?.abort();
      const request = new AbortController();
      controller = request;
      const timeout = window.setTimeout(() => request.abort(), 5000);
      const place = places[city];
      const url = new URL('https://api.open-meteo.com/v1/forecast');
      url.search = new URLSearchParams({
        latitude: String(place.latitude),
        longitude: String(place.longitude),
        timezone: place.timezone,
        current: 'weather_code,is_day',
        daily: 'sunrise,sunset',
        forecast_days: '1',
        timeformat: 'unixtime',
      }).toString();
      try {
        const response = await fetch(url, { signal: request.signal });
        if (!response.ok) throw new Error('Weather response unavailable');
        const data: WeatherResponse = await response.json();
        if (!alive || controller !== request) return;
        const sunrise = data.daily?.sunrise?.[0],
          sunset = data.daily?.sunset?.[0];
        daylight =
          typeof sunrise === 'number' && typeof sunset === 'number'
            ? { sunrise, sunset }
            : undefined;
        mostRecentIsDay = data.current?.is_day;
        apply(weatherScene(data.current?.weather_code ?? -1));
      } catch {
        if (alive && controller === request) apply('雨');
      } finally {
        window.clearTimeout(timeout);
        if (alive && controller === request) setResolved(true);
      }
    }
    void refresh();
    const dateTimer = window.setInterval(() => apply(), 60_000);
    const weatherTimer = window.setInterval(refresh, 10 * 60_000);
    return () => {
      alive = false;
      controller?.abort();
      window.clearInterval(dateTimer);
      window.clearInterval(weatherTimer);
    };
  }, [city, enabled, update]);
  return { manual, ready: !enabled || resolved };
}
