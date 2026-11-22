import { useEffect, useRef, type Dispatch, type SetStateAction } from 'react';
import { switchDaylight, type Environment } from '../environment';
import { windowCities as places } from '../../content/window-scenes';
import { localConditions, weatherScene } from '../window-conditions';

type City = Environment['city'];
type WeatherResponse = {
  current?: { weather_code?: number; is_day?: number };
  daily?: { sunrise?: number[]; sunset?: number[] };
};

export function useWindowConditions(
  city: City,
  enabled: boolean,
  update: Dispatch<SetStateAction<Environment>>,
) {
  const manual = useRef({ city, weather: false, night: false });
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
              ...(manual.current.night ? current : switchDaylight(current, night)),
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
  return manual;
}
