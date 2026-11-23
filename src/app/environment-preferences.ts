import {
  applyDaylightLighting,
  initialEnvironment,
  isRoomLook,
  type Environment,
} from './environment';
import { savedPreferences } from './home-lights';
import { localConditions } from './window-conditions';

const storageKey = 'felix-studio-v1';
const reviewMode = new URLSearchParams(location.search).get('review');
export const deterministicReview =
  import.meta.env.DEV && reviewMode !== null && reviewMode !== 'live-weather';
const windowReview = deterministicReview && reviewMode === 'window';

export function loadEnvironment(suggested: Environment['quality']): Environment {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  try {
    const stored = JSON.parse(
      window.localStorage.getItem(storageKey) ?? '{}',
    ) as Partial<Environment>;
    const automaticQuality = stored.automaticQuality ?? !stored.quality;
    const base = {
      ...initialEnvironment,
      reducedMotion,
      ...stored,
      roomLook: isRoomLook(stored.roomLook) ? stored.roomLook : initialEnvironment.roomLook,
      automaticQuality,
      quality: automaticQuality ? suggested : (stored.quality ?? suggested),
    };
    if (windowReview)
      return applyDaylightLighting({
        ...base,
        city: '上海',
        night: new URLSearchParams(location.search).get('time') !== 'day',
        weather: '晴',
        blinds: false,
      });
    return applyDaylightLighting(
      deterministicReview ? base : { ...base, ...localConditions(base.city), weather: '晴' },
    );
  } catch {
    return applyDaylightLighting({
      ...initialEnvironment,
      quality: suggested,
      ...localConditions(initialEnvironment.city),
      weather: '晴',
      reducedMotion,
    });
  }
}

export function saveEnvironment(environment: Environment) {
  if (windowReview) return;
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(savedPreferences(environment)));
  } catch {
    return;
  }
}
