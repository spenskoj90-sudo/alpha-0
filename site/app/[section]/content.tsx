'use client';
import Link from 'next/link';
import profiles from '../components/game-profiles.json';
import { PublicHeader } from '../components/public-header';
import { PublicFooter } from '../components/public-footer';
import { useLocale } from '../components/locale-provider';
import { publicSections, type PublicSection } from '../components/public-sections';

type Pair = readonly [string, string];
const intro: Record<PublicSection, Pair> = {
  features: ['Context you understand. Decisions you control.', 'Понятный контекст. Решения под вашим контролем.'],
  games: ['Game profiles, with their limits visible.', 'Игровые профили с понятными ограничениями.'],
  modules: ['A focused module for each useful task.', 'Отдельный модуль для каждой полезной задачи.'],
  pricing: ['Clear access before you commit.', 'Понятный доступ до оформления подписки.'],
  help: ['Find your next step.', 'Найдите следующий шаг.'],
  access: ['Your account starts in the Control Plane.', 'Ваш аккаунт — в панели управления.'],
};
const lead: Record<PublicSection, Pair> = {
  features: ['SENTINEL brings account controls and game context together. The product is in pre-release testing; exact game and device acceptance remains pending.', 'SENTINEL объединяет управление аккаунтом и игровой контекст. Продукт проходит подготовку к релизу; проверка конкретных игр и устройств ещё не завершена.'],
  games: ['This is a development inventory, not verified game support. Each profile needs its own installed-version, permission and environment evidence.', 'Это направления разработки, а не подтверждённая поддержка игр. Каждый профиль требует проверки установленной версии, разрешений и игровой среды.'],
  modules: ['We start with one Android observer scenario. Broader player intelligence stays on the roadmap until sources, recognition and recommendations are verified.', 'Начинаем с одного сценария наблюдения на Android. Более широкая аналитика остаётся в планах до проверки источников, распознавания и рекомендаций.'],
  pricing: ['Prices are not published. Commercial terms and public availability require final approval. The staging account shows current server-provided test plans.', 'Цены пока не опубликованы. Коммерческие условия и публичная доступность требуют финального решения. В тестовом аккаунте доступны текущие тарифы, полученные от сервера.'],
  help: ['Use the account panel for sign-in, recovery and security status. Read the limits of this pre-release before testing.', 'В панели аккаунта доступны вход, восстановление и состояние безопасности. Перед тестированием ознакомьтесь с ограничениями версии до релиза.'],
  access: ['Sign-in and registration run in the authenticated Web Control Plane. This public site does not collect passwords. The link below opens staging.', 'Вход и регистрация выполняются в защищённой веб-панели. Публичный сайт не собирает пароли. Ссылка ниже открывает тестовую среду.'],
};
const cards: Partial<Record<PublicSection, readonly (readonly [Pair, Pair, string])[]>> = {
  features: [
    [['Account and security', 'Аккаунт и безопасность'], ['Review security state, sessions and devices with server-authoritative access.', 'Проверяйте безопасность, сессии и устройства с правами, определяемыми сервером.'], '/security/'],
    [['Player context', 'Игровой контекст'], ['Facts, inference and recommendations stay distinct. Unknown or stale data cannot authorize actions.', 'Факты, выводы и рекомендации разделены. Неизвестные или устаревшие данные не разрешают действия.'], '/modules/'],
    [['Phone, Web and Companion', 'Телефон, браузер и Companion'], ['Platform foundations are implemented. Physical Android and target Windows acceptance remain pending.', 'Основа платформ реализована. Приёмка на физическом Android и целевом Windows ещё впереди.'], '/status/'],
  ],
  modules: [
    [['Shattered Pixel Dungeon observer', 'Наблюдение за Shattered Pixel Dungeon'], ['Android pilot: per-session capture consent, local recognition and explicit Stop. Calibration and useful recommendation acceptance are pending.', 'Пилот на Android: согласие на захват экрана для каждой сессии, локальное распознавание и явная остановка. Калибровка и приёмка полезных рекомендаций ещё не завершены.'], '/games/'],
    [['Verified knowledge delivery', 'Доставка проверенных знаний'], ['Consumers check profile, digest, revision, expiry and revocation. Without a verified profile, recommendations stay unavailable.', 'Потребители проверяют профиль, digest, ревизию, срок действия и отзыв. Без проверенного профиля рекомендации недоступны.'], '/security/'],
    [['Future player intelligence', 'Будущая игровая аналитика'], ['Equipment, talents, PvP/PvE and session analysis are development directions. Economy, professions and travel remain later research.', 'Экипировка, таланты, PvP/PvE и разбор сессий — направления разработки. Экономика, профессии и путешествия — последующие исследования.'], '/status/'],
  ],
  pricing: [
    [['Test access', 'Тестовый доступ'], ['Use only server-provided staging plans. Test checkout is not a public paid subscription or a promise of game support.', 'Используйте только серверные тарифы тестовой среды. Тестовый checkout не является публичной подпиской и не обещает поддержку игр.'], '/access/'],
    [['Control your access', 'Управляйте доступом'], ['The server decides subscription state and expiry. Losing access does not modify or remove your original game.', 'Состояние и срок подписки определяет сервер. Прекращение доступа не изменяет и не удаляет оригинальную игру.'], '/security/'],
  ],
  help: [
    [['Sign in or create an account', 'Войти или создать аккаунт'], ['Open the account panel. Choose Create account for registration. Available providers are determined by the server.', 'Откройте панель аккаунта. Для регистрации выберите «Создать аккаунт». Доступные провайдеры входа определяет сервер.'], '/access/'],
    [['Recover access', 'Восстановить доступ'], ['Choose Forgot password in the account panel. Email delivery depends on staging configuration. Never share verification or recovery codes.', 'Выберите «Забыли пароль?» в панели аккаунта. Доставка писем зависит от тестовой конфигурации. Не передавайте коды подтверждения и восстановления.'], '/access/'],
    [['Before physical testing', 'Перед проверкой на устройстве'], ['Wait for an agreed exact candidate and verified update compatibility. Keep the installed app and its Keystore data.', 'Дождитесь согласованного кандидата и проверенной совместимости обновления. Сохраните установленное приложение и его данные Keystore.'], '/status/'],
    [['Privacy and diagnostics', 'Конфиденциальность и диагностика'], ['Use in-app diagnostics. Avoid publishing credentials or raw screen captures. Engineering principles do not replace the final legal notice.', 'Используйте диагностику приложения. Не публикуйте учётные данные и исходные снимки экрана. Инженерные принципы не заменяют юридическое уведомление.'], '/privacy/'],
  ],
};
export default function PublicSectionPage({ section }: { section: PublicSection }) {
  const { locale, t } = useLocale();
  const copy = (pair: Pair) => pair[locale === 'ru' ? 1 : 0];
  const entry = publicSections.find(item => item.path === section)!;
  const state = (status: string): Pair => status === 'observer_pilot'
    ? ['Observer pilot · Calibration pending', 'Пилот наблюдения · Калибровка ожидается']
    : status === 'adapter_foundation'
      ? ['Adapter foundation · Environment unverified', 'Основа адаптера · Среда не проверена']
      : ['Research only · Environment unverified', 'Только исследование · Среда не проверена'];
  return <>
    <a className="skip-link" href="#main-content">{t('Skip to main content')}</a>
    <PublicHeader />
    <main id="main-content" className="document-main"><div className="site-shell document-shell">
      <div className="eyebrow">{locale === 'ru' ? entry.ru : entry.en}</div>
      <h1>{copy(intro[section])}</h1><p className="document-lead">{copy(lead[section])}</p>
      {cards[section] && <div className="principle-grid">{cards[section]!.map(([title, body, href]) => <article className="feature-card" key={title[0]}>
        <h2>{copy(title)}</h2><p>{copy(body)}</p><Link className="text-link" href={href}>{copy(['Learn more →', 'Подробнее →'])}</Link>
      </article>)}</div>}
      {section === 'games' && <>
        <aside className="callout"><strong>{copy(['Game actions are disabled.', 'Игровые действия отключены.'])}</strong><p>{copy(['SENTINEL does not modify original game APKs or executables. Catalog membership does not grant capabilities or entitlements.', 'SENTINEL не изменяет оригинальные APK и исполняемые файлы игр. Наличие в каталоге не предоставляет возможности или права доступа.'])}</p></aside>
        <div className="principle-grid">{profiles.map(profile => <article className="feature-card" key={profile.id}>
          <h2>{profile.name}</h2><p>{profile.platform}{profile.patch ? ` · ${profile.patch}` : ''}</p><span className="status">{copy(state(profile.implementation_status))}</span>
        </article>)}</div>
      </>}
      {section === 'access' && <div className="hero-actions">
        <a className="button-primary" href="https://sentinel-web-staging-fxhn.onrender.com/#account">{copy(['Open staging account', 'Открыть тестовый аккаунт'])}</a>
        <Link className="button-secondary" href="/help/">{copy(['Account help', 'Помощь с аккаунтом'])}</Link>
      </div>}
      <div className="hero-actions"><Link className="text-link" href="/">{t('Return home')}</Link><Link className="text-link" href="/status/">{t('View release status')}</Link></div>
    </div></main><PublicFooter />
  </>;
}
