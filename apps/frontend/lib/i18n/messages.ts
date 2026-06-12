import type { Locale } from '@/i18n/config';

import tr from '@/messages/tr.json';
import en from '@/messages/en.json';
import es from '@/messages/es.json';
import zh from '@/messages/zh.json';
import ja from '@/messages/ja.json';
import pt from '@/messages/pt-BR.json';

export type Messages = typeof en;

const allMessages: Record<Locale, Messages> = {
  tr: tr as Messages,
  en,
  es: es as Messages,
  zh: zh as Messages,
  ja: ja as Messages,
  pt: pt as Messages,
};

export function getMessages(locale: Locale): Messages {
  return allMessages[locale] || allMessages.en;
}
