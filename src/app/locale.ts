export type Locale = 'en' | 'zh';

export function local(locale: Locale, english: string, chinese: string) {
  return locale === 'zh' ? chinese : english;
}

export const cityName = (locale: Locale, city: '上海' | '纽约') =>
  local(locale, city === '上海' ? 'Shanghai' : 'New York', city);
