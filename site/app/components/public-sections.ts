export const publicSections = [
  { path: 'features', en: 'Features', ru: 'Возможности' },
  { path: 'games', en: 'Games', ru: 'Игры' },
  { path: 'modules', en: 'Modules', ru: 'Модули' },
  { path: 'pricing', en: 'Plans', ru: 'Тарифы' },
  { path: 'help', en: 'Help', ru: 'Помощь' },
  { path: 'access', en: 'Sign in', ru: 'Вход' },
] as const;
export type PublicSection = typeof publicSections[number]['path'];
