export type Locale = 'en' | 'zh';

export function local(locale: Locale, english: string, chinese: string) {
  return locale === 'zh' ? chinese : english;
}

export const cityName = (locale: Locale, city: WindowCity) =>
  local(locale, windowCities[city].english, city);
import { windowCities, type WindowCity } from '../content/window-scenes';
