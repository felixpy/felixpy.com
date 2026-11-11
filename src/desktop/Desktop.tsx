import { CircleUserRound, Gamepad2, Music2, Settings2, Wifi, X } from 'lucide-react';
import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent,
} from 'react';
import type { Environment } from '../app/environment';
import { local } from '../app/locale';
import type { AppID } from '../scene/studio';
import { MusicPlayer } from './apps/music/MusicPlayer';
import type { StudioMusic } from './apps/music/useStudioMusic';
import Profile from './apps/Profile';
import LockScreen, { FlowWallpaper } from './LockScreen';
import Magnet from './react-bits/Magnet';
import { Select } from './ui/Select';
import { Tooltip } from './ui/Tooltip';

const Game = lazy(() => import('./apps/arcade/Game'));
const apps = {
  about: { en: 'About', zh: '关于', icon: CircleUserRound },
  music: { en: 'Music', zh: '音乐', icon: Music2 },
  game: { en: 'Orbital Patrol', zh: '近地航线', icon: Gamepad2 },
  settings: { en: 'Settings', zh: '系统设置', icon: Settings2 },
} satisfies Record<AppID, { en: string; zh: string; icon: typeof X }>;

type WindowState = {
  id: AppID;
  x: number;
  y: number;
  width: number;
  height: number;
  minimized: boolean;
  maximized: boolean;
  closing?: boolean;
};
type Props = {
  request: { id?: AppID; sequence: number };
  compact: boolean;
  visible?: boolean;
  music: StudioMusic;
  environment: Environment;
  setEnvironment: (patch: Partial<Environment>) => void;
  onExit?: () => void;
};

function Settings({
  environment: env,
  setEnvironment,
}: Pick<Props, 'environment' | 'setEnvironment'>) {
  const t = (en: string, zh: string) => local(env.locale, en, zh);
  return (
    <section className="os-content">
      <h1>{t('Studio settings', '工作室设置')}</h1>
      <div className="setting-group">
        <div className="setting-row">
          <span id="studio-language-label">{t('Language', '语言')}</span>
          <div className="setting-segments" role="group" aria-labelledby="studio-language-label">
            <button
              type="button"
              lang="en"
              aria-pressed={env.locale === 'en'}
              onClick={() => setEnvironment({ locale: 'en' })}
            >
              English
            </button>
            <button
              type="button"
              lang="zh-Hans"
              aria-pressed={env.locale === 'zh'}
              onClick={() => setEnvironment({ locale: 'zh' })}
            >
              简体中文
            </button>
          </div>
        </div>
        <label>
          <span>{t('Desk lamp', '台灯')}</span>
          <input
            type="checkbox"
            className="os-switch"
            checked={env.lamp}
            onChange={(event) => setEnvironment({ lamp: event.target.checked })}
          />
        </label>
        <label>
          <span>{t('Workbench lamp', '工作台灯')}</span>
          <input
            type="checkbox"
            className="os-switch"
            checked={env.benchLamp}
            onChange={(event) => setEnvironment({ benchLamp: event.target.checked })}
          />
        </label>
        <label>
          <span>{t('Ceiling light at night', '夜间顶灯亮度')}</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={env.ceiling}
            onChange={(event) => setEnvironment({ ceiling: Number(event.target.value) })}
          />
        </label>
        <label>
          <span>{t('Aura lighting', 'Aura 灯效')}</span>
          <input
            type="checkbox"
            className="os-switch"
            checked={env.aura}
            onChange={(event) => setEnvironment({ aura: event.target.checked })}
          />
        </label>
        <label>
          <span>{t('Rain ambience', '环境雨声')}</span>
          <input
            type="checkbox"
            className="os-switch"
            checked={env.rainAudio}
            onChange={(event) => setEnvironment({ rainAudio: event.target.checked })}
          />
        </label>
        <label>
          <span>{t('Arcade sound', '街机音效')}</span>
          <input
            type="checkbox"
            className="os-switch"
            checked={env.gameAudio}
            onChange={(event) => setEnvironment({ gameAudio: event.target.checked })}
          />
        </label>
      </div>
      <div className="setting-group">
        <div className="setting-row">
          <span id="studio-quality-label">{t('Render quality', '实时画质')}</span>
          <Select<Environment['quality']>
            labelId="studio-quality-label"
            value={env.quality}
            options={[
              { value: 'high', label: t('High', '高') },
              { value: 'low', label: t('Low power', '节能') },
            ]}
            onChange={(quality) => setEnvironment({ quality })}
          />
        </div>
        <label>
          <span>{t('Reduce motion', '减少动态效果')}</span>
          <input
            type="checkbox"
            className="os-switch"
            checked={env.reducedMotion}
            onChange={(event) => setEnvironment({ reducedMotion: event.target.checked })}
          />
        </label>
      </div>
    </section>
  );
}

function Application({
  id,
  active,
  environment,
  setEnvironment,
  music,
}: Pick<Props, 'environment' | 'setEnvironment' | 'music'> & { id: AppID; active: boolean }) {
  const locale = environment.locale;
  const t = (en: string, zh: string) => local(locale, en, zh);
  switch (id) {
    case 'about':
      return (
        <Profile
          locale={locale}
          animate={active && !environment.reducedMotion && environment.quality !== 'low'}
        />
      );
    case 'music':
      return (
        <MusicPlayer
          locale={locale}
          music={music}
          active={active}
          reducedMotion={environment.reducedMotion}
        />
      );
    case 'game':
      return (
        <Suspense
          fallback={
            <p className="os-content">{t('Launching the flight program…', '正在启动飞行程序…')}</p>
          }
        >
          <Game locale={locale} active={active} sound={environment.gameAudio} />
        </Suspense>
      );
    case 'settings':
      return <Settings environment={environment} setEnvironment={setEnvironment} />;
  }
}

function newWindow(id: AppID): WindowState {
  const layout =
    id === 'about'
      ? { x: 4, y: 2, width: 91, height: 80.5 }
      : id === 'game'
        ? { x: 35, y: 0.6, width: 30, height: 81 }
        : id === 'music'
          ? { x: 9, y: 3, width: 82, height: 78 }
          : { x: 13, y: 6, width: 72, height: 68 };
  return { id, ...layout, minimized: false, maximized: false };
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function FelixMark() {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true">
      <path fill="currentColor" d="M2 2h12v2H4v3h7v2H4v5H2z M12 11h2v3h-2z" />
    </svg>
  );
}

export default function Desktop({
  request,
  compact,
  visible = true,
  environment,
  setEnvironment,
  music,
  onExit,
}: Props) {
  const locale = environment.locale;
  const t = (en: string, zh: string) => local(locale, en, zh);
  const [appWindow, setAppWindow] = useState<WindowState | null>(null);
  const [systemMenuOpen, setSystemMenuOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [clock, setClock] = useState(() => new Date());
  const [session, setSession] = useState<'locked' | 'unlocking' | 'unlocked'>('locked');
  const surface = useRef<HTMLDivElement>(null);
  const systemButton = useRef<HTMLButtonElement>(null);
  const restoreKeyboardFocus = useRef(false);
  const sequence = useRef(-1);
  const pendingApp = useRef<AppID | undefined>(undefined);
  const hasUnlocked = useRef(false);
  const drag = useRef<{
    origin: WindowState;
    x: number;
    y: number;
    action: 'move' | 'resize';
  } | null>(null);
  const reducedMotion =
    environment.reducedMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const lowPower = environment.quality === 'low';
  const clockText = new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-GB', {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(clock);
  const desktopVisible = session !== 'locked';

  function open(id: AppID) {
    drag.current = null;
    setAppWindow((current) =>
      current?.id === id ? { ...current, minimized: false, closing: false } : newWindow(id),
    );
    setSystemMenuOpen(false);
    setAboutOpen(false);
  }

  useEffect(() => {
    if (sequence.current === request.sequence) return;
    sequence.current = request.sequence;
    if (session === 'locked') pendingApp.current = request.id;
    else if (request.id) open(request.id);
  }, [request, session]);

  useEffect(() => {
    if (!visible || session === 'locked') return;
    setAppWindow((current) => (current && !current.closing ? current : newWindow('about')));
  }, [visible, session]);

  useEffect(() => {
    if (!visible) return;
    setClock(new Date());
    const timer = window.setInterval(() => setClock(new Date()), 1000 * 10);
    return () => window.clearInterval(timer);
  }, [visible]);

  useEffect(() => {
    if (session !== 'unlocking') return;
    const timer = window.setTimeout(() => setSession('unlocked'), 270);
    return () => window.clearTimeout(timer);
  }, [session]);

  useEffect(() => {
    if (session === 'unlocked' && restoreKeyboardFocus.current)
      systemButton.current?.focus({ preventScroll: true });
  }, [session]);

  function unlock(keyboard: boolean) {
    hasUnlocked.current = true;
    restoreKeyboardFocus.current = keyboard;
    const requested = pendingApp.current;
    pendingApp.current = undefined;
    if (requested) open(requested);
    setSession(reducedMotion ? 'unlocked' : 'unlocking');
  }

  function lock() {
    setSystemMenuOpen(false);
    setAboutOpen(false);
    setAppWindow((current) => (current?.closing ? null : current));
    setSession('locked');
  }

  function switchLanguage() {
    setEnvironment({ locale: locale === 'en' ? 'zh' : 'en' });
  }

  function closeAbout() {
    setAboutOpen(false);
    requestAnimationFrame(() => systemButton.current?.focus({ preventScroll: true }));
  }

  function close(item: WindowState) {
    if (reducedMotion) setAppWindow((current) => (current?.id === item.id ? null : current));
    else patch(item.id, { closing: true });
  }

  function patch(id: AppID, change: Partial<WindowState>) {
    setAppWindow((current) => (current?.id === id ? { ...current, ...change } : current));
  }

  function dragStart(
    event: PointerEvent<HTMLElement>,
    item: WindowState,
    action: 'move' | 'resize',
  ) {
    if (
      compact ||
      item.maximized ||
      event.button !== 0 ||
      (action === 'move' && (event.target as HTMLElement).closest('button'))
    )
      return;
    drag.current = { origin: item, x: event.clientX, y: event.clientY, action };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function dragMove(event: PointerEvent<HTMLElement>) {
    const active = drag.current,
      rect = surface.current?.getBoundingClientRect();
    if (!active || !rect) return;
    const x = ((event.clientX - active.x) / rect.width) * 100;
    const y = ((event.clientY - active.y) / rect.height) * 100;
    const w = active.origin;
    patch(
      w.id,
      active.action === 'move'
        ? {
            x: clamp(w.x + x, 1, 99 - w.width),
            y: clamp(w.y + y, 1, 84 - w.height),
          }
        : {
            width: clamp(w.width + x, w.id === 'game' ? 24 : 46, 99 - w.x),
            height: clamp(w.height + y, 38, 84 - w.y),
          },
    );
  }
  const stopDrag = () => {
    drag.current = null;
  };

  const ids = Object.keys(apps) as AppID[];
  const openWindow = appWindow && !appWindow.closing ? appWindow : null;
  const active = openWindow && !openWindow.minimized ? openWindow : null;
  const title = appWindow ? apps[appWindow.id][locale] : '';
  const systemMenuLabel = t('System menu', '系统菜单');
  const switchLanguageLabel = t('Switch to Chinese', '切换到英文');
  return (
    <div
      className="desktop"
      ref={surface}
      data-reduced-motion={reducedMotion}
      onPointerDown={(event) => {
        if (!(event.target as HTMLElement).closest('.menu-bar')) setSystemMenuOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && (aboutOpen || systemMenuOpen)) {
          event.preventDefault();
          event.stopPropagation();
          if (systemMenuOpen) setSystemMenuOpen(false);
          else closeAbout();
        }
      }}
    >
      <FlowWallpaper active={visible} reducedMotion={reducedMotion} lowPower={lowPower} />
      {hasUnlocked.current && (
        <div className="desktop-session" hidden={!desktopVisible} inert={session !== 'unlocked'}>
          <div className="menu-bar">
            <Tooltip text={systemMenuLabel} placement="bottom-start">
              <button
                ref={systemButton}
                className="system-menu-button"
                type="button"
                aria-label={systemMenuLabel}
                aria-expanded={systemMenuOpen}
                onClick={() => setSystemMenuOpen(!systemMenuOpen)}
              >
                <FelixMark />
              </button>
            </Tooltip>
            <strong>{active ? apps[active.id][locale] : 'Felix Studio'}</strong>
            <span className="menu-clock">
              <Wifi aria-hidden="true" />
              <span>{clockText}</span>
            </span>
            <Tooltip text={switchLanguageLabel} placement="bottom-end">
              <button
                type="button"
                className="menu-language"
                aria-label={switchLanguageLabel}
                onClick={switchLanguage}
              >
                <span>{locale === 'en' ? '中文' : 'EN'}</span>
              </button>
            </Tooltip>
            {onExit && (
              <Tooltip text={t('Return to studio (Esc)', '离开电脑（Esc）')} placement="bottom-end">
                <button
                  type="button"
                  aria-label={t('Return to studio', '离开电脑')}
                  onClick={onExit}
                >
                  <X />
                </button>
              </Tooltip>
            )}
            {systemMenuOpen && (
              <div className="menu-dropdown">
                <button
                  type="button"
                  aria-haspopup="dialog"
                  onClick={() => {
                    setSystemMenuOpen(false);
                    setAboutOpen(true);
                  }}
                >
                  {t('About Felix OS', '关于 Felix OS')}
                </button>
                <button type="button" onClick={() => open('settings')}>
                  {t('System Settings…', '系统设置…')}
                </button>
                <button type="button" onClick={lock}>
                  {t('Lock screen', '锁定屏幕')}
                </button>
                {onExit && (
                  <button type="button" onClick={onExit}>
                    {t('Return to studio', '返回工作室')}
                  </button>
                )}
              </div>
            )}
          </div>
          {appWindow && (
            <section
              key={appWindow.id}
              className={
                'os-window os-window-' +
                appWindow.id +
                (appWindow.maximized ? ' is-maximized' : '') +
                (active ? ' is-active' : '') +
                (appWindow.closing ? ' is-closing' : '')
              }
              aria-label={locale === 'en' ? title + ' window' : title + '窗口'}
              hidden={appWindow.minimized}
              inert={appWindow.closing}
              style={
                {
                  '--window-x': appWindow.x + '%',
                  '--window-y': appWindow.y + '%',
                  '--window-w': appWindow.width + 'cqw',
                  '--window-h': appWindow.height + '%',
                  '--game-height': appWindow.height + 'cqh',
                } as CSSProperties
              }
              onAnimationEnd={(event) => {
                if (
                  event.target === event.currentTarget &&
                  event.animationName === 'window-dismiss'
                ) {
                  setAppWindow((current) =>
                    current?.id === appWindow.id && current.closing ? null : current,
                  );
                }
              }}
            >
              <div
                className="title-bar"
                onPointerDown={(event) => dragStart(event, appWindow, 'move')}
                onPointerMove={dragMove}
                onPointerUp={stopDrag}
                onPointerCancel={stopDrag}
                onDoubleClick={(event) => {
                  if (!(event.target as HTMLElement).closest('button'))
                    patch(appWindow.id, { maximized: !appWindow.maximized });
                }}
              >
                <div className="traffic">
                  <button
                    type="button"
                    className="close"
                    aria-label={t('Close ' + title, '关闭' + title)}
                    onClick={() => close(appWindow)}
                  />
                  <button
                    type="button"
                    className="minimize"
                    aria-label={t('Minimize ' + title, '最小化' + title)}
                    onClick={() => patch(appWindow.id, { minimized: true })}
                  />
                  <button
                    type="button"
                    className="zoom"
                    aria-label={
                      appWindow.maximized
                        ? t('Restore ' + title, '还原' + title)
                        : t('Maximize ' + title, '放大' + title)
                    }
                    onClick={() => patch(appWindow.id, { maximized: !appWindow.maximized })}
                  />
                </div>
                <span>{title}</span>
              </div>
              <div className="window-body">
                <Application
                  id={appWindow.id}
                  active={Boolean(active && visible && session === 'unlocked')}
                  environment={environment}
                  setEnvironment={setEnvironment}
                  music={music}
                />
              </div>
              {!compact && !appWindow.maximized && (
                <div
                  className="window-resize"
                  aria-hidden="true"
                  onPointerDown={(event) => dragStart(event, appWindow, 'resize')}
                  onPointerMove={dragMove}
                  onPointerUp={stopDrag}
                  onPointerCancel={stopDrag}
                />
              )}
            </section>
          )}
          <nav className="dock" aria-label={t('Applications', '应用程序')}>
            {ids.map((id) => {
              const { icon: Icon } = apps[id];
              const title = apps[id][locale];
              return (
                <Magnet
                  key={id}
                  padding={10}
                  magnetStrength={7}
                  maxOffset={4}
                  scale={1.025}
                  disabled={reducedMotion || lowPower || !visible}
                >
                  <Tooltip text={title}>
                    <button
                      type="button"
                      className="dock-button"
                      aria-label={title}
                      onClick={() => open(id)}
                    >
                      <span className="dock-label" aria-hidden="true">
                        {title}
                      </span>
                      <span className={'app-icon app-' + id}>
                        <Icon aria-hidden="true" />
                      </span>
                      <i className={openWindow?.id === id ? 'running' : ''} />
                    </button>
                  </Tooltip>
                </Magnet>
              );
            })}
          </nav>
          {aboutOpen && (
            <section
              className="os-about-dialog"
              role="dialog"
              aria-labelledby="os-about-name"
              aria-describedby="os-about-version"
            >
              <button
                className="os-about-close"
                type="button"
                autoFocus
                aria-label={t('Close', '关闭')}
                onClick={closeAbout}
              >
                <X aria-hidden="true" />
              </button>
              <div className="os-about-mark" aria-hidden="true">
                <FelixMark />
              </div>
              <h2 id="os-about-name">Felix OS</h2>
              <p id="os-about-version">26.11</p>
            </section>
          )}
        </div>
      )}
      {session !== 'unlocked' && (
        <LockScreen
          locale={locale}
          clock={clock}
          reducedMotion={reducedMotion}
          lowPower={lowPower}
          visible={visible}
          leaving={session === 'unlocking'}
          onUnlock={unlock}
          onLanguage={switchLanguage}
          onExit={onExit}
        />
      )}
    </div>
  );
}
