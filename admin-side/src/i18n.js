import { createI18n } from 'vue-i18n';
import en from './locales/en.json';
import it from './locales/it.json';

const messages = {
  en,
  it
};

// Get saved locale from localStorage or default to 'en'
const savedLocale = localStorage.getItem('user-locale') || 'en';

const i18n = createI18n({
  legacy: false, // Set to false for Composition API mode
  locale: savedLocale,
  fallbackLocale: 'en',
  messages,
});

export default i18n;
