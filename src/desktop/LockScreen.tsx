import { ArrowRight, LockKeyhole, X } from 'lucide-react';
import { lazy, Suspense, useEffect, useRef } from 'react';
import { local, type Locale } from '../app/locale';
import AnimatedContent from './react-bits/AnimatedContent';
import Magnet from './react-bits/Magnet';
import './lock-screen.css';

const Aurora = lazy(() => import('./react-bits/Aurora'));
const colors = ['#214a70', '#29849a', '#62c8ac', '#f3ca91', '#4b69a4'];

type Props = {
  locale: Locale;
  clock: Date;
  reducedMotion: boolean;
  lowPower: boolean;
  visible: boolean;
  leaving: boolean;
  onUnlock: (keyboard: boolean) => void;
  onLanguage: () => void;
  onExit?: () => void;
};

export function FlowWallpaper({
  active,
  reducedMotion,
  lowPower,
}: {
  active: boolean;
  reducedMotion: boolean;
  lowPower: boolean;
}) {
  return (
    <div className="flow-wallpaper" aria-hidden="true">
      {active && !reducedMotion && (
        <Suspense fallback={null}>
          <Aurora
            colorStops={colors}
            direction="bottom"
            speed={2.15}
            amplitude={2.25}
            blend={0.27}
            scale={1.72}
            height={0.59}
            glow={0.72}
            brightness={1.44}
            layers={lowPower ? 2 : 3}
            intro={false}
            dpr={lowPower ? 0.55 : 0.9}
          />
        </Suspense>
      )}
    </div>
  );
}

export default function LockScreen({
  locale,
  clock,
  reducedMotion,
  lowPower,
  visible,
  leaving,
  onUnlock,
  onLanguage,
  onExit,
}: Props) {
  const unlock = useRef<HTMLButtonElement>(null);
  const language = locale === 'en' ? 'en-GB' : 'zh-CN';
  const t = (en: string, zh: string) => local(locale, en, zh);
  const date = new Intl.DateTimeFormat(language, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(clock);
  const time = new Intl.DateTimeFormat(language, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(clock);

  useEffect(() => {
    if (visible && !leaving) unlock.current?.focus({ preventScroll: true });
  }, [leaving, visible]);

  const clockFace = (
    <div className="lock-clock">
      <div className="lock-status">
        <LockKeyhole aria-hidden="true" />
        {t('Studio locked', '工作室电脑已锁定')}
      </div>
      <p>{date}</p>
      <time dateTime={clock.toISOString()}>{time}</time>
    </div>
  );

  return (
    <section
      className={'lock-screen' + (leaving ? ' lock-screen-leaving' : '')}
      aria-label={t('Lock screen', '锁屏')}
      inert={leaving || !visible}
    >
      <div className="lock-top">
        <button
          type="button"
          onClick={onLanguage}
          aria-label={t('Switch to Chinese', '切换到英文')}
        >
          {locale === 'en' ? '中文' : 'EN'}
        </button>
        {onExit && (
          <button type="button" onClick={onExit} aria-label={t('Return to studio', '离开电脑')}>
            <X aria-hidden="true" />
          </button>
        )}
      </div>
      <div className="lock-main">
        {reducedMotion || !visible ? (
          clockFace
        ) : (
          <AnimatedContent trigger="mount" distance={8} duration={0.4} initialOpacity={0.5}>
            {clockFace}
          </AnimatedContent>
        )}
      </div>
      <div className="lock-access">
        <span className="lock-owner">Felix Studio</span>
        <Magnet
          padding={20}
          magnetStrength={8}
          maxOffset={4}
          disabled={reducedMotion || lowPower || !visible}
        >
          <button
            ref={unlock}
            className="lock-unlock"
            type="button"
            onClick={(event) => onUnlock(event.detail === 0)}
            data-lock-unlock
          >
            {t('Unlock', '解锁')} <ArrowRight aria-hidden="true" />
          </button>
        </Magnet>
      </div>
    </section>
  );
}
