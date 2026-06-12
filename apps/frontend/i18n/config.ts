/**
 * Internationalization configuration
 */

export const locales = ['tr', 'en', 'es', 'zh', 'ja', 'pt'] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = 'tr';

export const localeNames: Record<Locale, string> = {
  tr: 'Türkçe',
  en: 'English',
  es: 'Español',
  zh: '中文',
  ja: '日本語',
  pt: 'Português',
};

export const localeFlags: Record<Locale, string> = {
  tr: '🇹🇷',
  en: '🇺🇸',
  es: '🇪🇸',
  zh: '🇨🇳',
  ja: '🇯🇵',
  pt: '🇧🇷',
};
