import {
  Component,
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { initialEnvironment, pressRemote, type Environment } from './environment';
import type { AppID, Target } from '../scene/studio';
import type { Mode } from '../scene/StudioView';
import Desktop from '../desktop/Desktop';
import Profile from '../desktop/apps/Profile';
import { useStudioMusic } from '../desktop/apps/music/useStudioMusic';
import LoadingScreen from './ui/LoadingScreen';
import FpsMeter from './ui/FpsMeter';
import { useRainAudio } from './hooks/useRainAudio';
import { localConditions, useWindowConditions } from './hooks/useWindowConditions';
import { cityName, local } from './locale';
import './studio.css';
import '../spectral/spectral.css';

const StudioView = lazy(() => import('../scene/StudioView'));
const storageKey = 'felix-studio-v1';
const reviewMode = new URLSearchParams(location.search).get('review');
const deterministicReview =
  import.meta.env.DEV && reviewMode !== null && reviewMode !== 'live-weather';

function loadEnvironment(): Environment {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  try {
    const stored = JSON.parse(
      window.localStorage.getItem(storageKey) ?? '{}',
    ) as Partial<Environment>;
    const base = { ...initialEnvironment, reducedMotion, ...stored };
    return deterministicReview ? base : { ...base, ...localConditions(base.city), weather: '晴' };
  } catch {
    return {
      ...initialEnvironment,
      ...localConditions(initialEnvironment.city),
      weather: '晴',
      reducedMotion,
    };
  }
}

class RendererBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

function supported() {
  try {
    return Boolean(document.createElement('canvas').getContext('webgl2'));
  } catch {
    return false;
  }
}

export default function App({ fontsReady }: { fontsReady: Promise<unknown> }) {
  const [compact, setCompact] = useState(
    () => window.matchMedia('(max-width: 700px), (max-height: 420px)').matches,
  );
  const [webGL] = useState(supported);
  const [sceneReady, setSceneReady] = useState(false);
  const [loadingComplete, setLoadingComplete] = useState(false);
  const [fontsLoaded, setFontsLoaded] = useState(false);
  const [progress, setProgress] = useState(0);
  const [environment, setEnvironment] = useState(loadEnvironment);
  const windowConditions = useWindowConditions(
    environment.city,
    !deterministicReview && !compact && webGL,
    setEnvironment,
  );
  const resourcesReady = sceneReady && windowConditions.ready;
  const ready = resourcesReady && loadingComplete;
  const music = useStudioMusic(!compact);
  const t = (en: string, zh: string) => local(environment.locale, en, zh);
  const [mode, setMode] = useState<Mode>('room');
  useRainAudio(
    environment.weather === '雨' && environment.rainAudio && !compact && webGL && ready,
    mode === 'remote' || mode === 'window',
    environment.blinds,
  );
  const [hint, setHint] = useState('');
  const [inspectionLink, setInspectionLink] = useState<string>();
  const cue = useRef<HTMLDivElement>(null);
  const caption = useRef<HTMLDivElement>(null);
  const inspectionAnchor = useRef<HTMLAnchorElement>(null);
  const [request, setRequest] = useState<{ id?: AppID; sequence: number }>({ sequence: 0 });
  const screen = useRef<HTMLDivElement>(null);
  const controls = useRef<{ open: () => void }>(null);

  useEffect(() => {
    let active = true;
    void fontsReady.then(() => {
      if (active) setFontsLoaded(true);
    });
    return () => {
      active = false;
    };
  }, [fontsReady]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 700px), (max-height: 420px)');
    const update = () => {
      setCompact(media.matches);
      setMode('room');
      setSceneReady(false);
      setLoadingComplete(false);
      setProgress(0);
      if (screen.current) screen.current.dataset.visible = 'false';
    };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    const keepPageFocus = (event: KeyboardEvent) => {
      if (event.key === 'Tab' && !event.ctrlKey && !event.metaKey && !event.altKey)
        event.preventDefault();
    };
    window.addEventListener('keydown', keepPageFocus, true);
    return () => window.removeEventListener('keydown', keepPageFocus, true);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(environment));
    } catch {
      /* Browsing without local storage still works. */
    }
  }, [environment]);

  useEffect(() => {
    document.documentElement.lang = environment.locale === 'zh' ? 'zh-Hans' : 'en';
    document.title = environment.locale === 'zh' ? 'Felix Yang · 工作室' : 'Felix Yang — Studio';
    setHint('');
  }, [environment.locale]);

  const updateEnvironment = (patch: Partial<Environment>) =>
    setEnvironment((current) => ({ ...current, ...patch }));
  function handleMode(next: Mode, app?: AppID, link?: string) {
    setMode(next);
    setInspectionLink(link);
    if (next === 'computer' && app)
      setRequest((prev) => ({ id: app, sequence: prev.sequence + 1 }));
  }
  function handleHint(text: string, point?: { x: number; y: number }) {
    if (point && cue.current) {
      cue.current.style.setProperty(
        '--cue-x',
        Math.max(16, Math.min(window.innerWidth - 240, point.x + 17)) + 'px',
      );
      cue.current.style.setProperty(
        '--cue-y',
        Math.max(16, Math.min(window.innerHeight - 58, point.y + 18)) + 'px',
      );
    }
    setHint(text);
  }
  function handlePress(target: Target) {
    if (target.type === 'lamp') setEnvironment((current) => ({ ...current, lamp: !current.lamp }));
    if (target.type === 'bench-lamp')
      setEnvironment((current) => ({ ...current, benchLamp: !current.benchLamp }));
    if (target.type === 'aura') setEnvironment((current) => ({ ...current, aura: !current.aura }));
    if (target.type === 'key') {
      if (target.index === 1 && !environment.blinds)
        return t('Lower the blinds before tilting them', '先放下百叶再调节叶片');
      const next = pressRemote(environment, target.index);
      if (target.index === 2)
        windowConditions.manual.current = { city: next.city, weather: false, night: false };
      if (target.index === 3) windowConditions.manual.current.weather = true;
      if (target.index === 4)
        windowConditions.manual.current = { city: next.city, weather: true, night: true };
      if (target.index === 5) windowConditions.manual.current.night = true;
      setEnvironment(next);
      const city = cityName(environment.locale, next.city);
      const weather = t(
        { 晴: 'Clear', 阴: 'Overcast', 雨: 'Rain', 雪: 'Snow' }[next.weather],
        next.weather,
      );
      const daylight = next.night ? t('Night', '夜晚') : t('Day', '白天');
      return [
        next.blinds ? t('Blinds lowered', '百叶已放下') : t('Blinds raised', '百叶已收起'),
        (environment.locale === 'en'
          ? ['Slats open', 'Slats angled', 'Slats closed']
          : ['叶片全开', '叶片半开', '叶片闭合']
        )[next.angle],
        city,
        weather,
        [city, weather, daylight].join(' · '),
        daylight,
      ][target.index];
    }
  }

  const simple = (
    <main className="compact-studio">
      <Desktop
        compact
        request={request}
        environment={environment}
        setEnvironment={updateEnvironment}
        music={music}
      />
      <FpsMeter />
    </main>
  );
  if (compact)
    return (
      <main className="mobile-home">
        <Profile mobile locale={environment.locale} animate={!environment.reducedMotion} />
      </main>
    );
  if (!webGL) return simple;

  return (
    <RendererBoundary fallback={simple}>
      <main
        className="studio"
        aria-label={t('Felix Yang’s studio', 'Felix Yang 的工作室')}
        aria-describedby="studio-room-help"
        data-mode={mode}
      >
        <p id="studio-room-help" className="sr-only">
          {t(
            'Drag or use the arrow keys to look around. Scroll to zoom. Click an object to examine it or the workbench to move there. Escape puts the object back or returns to the desk.',
            '拖动或按方向键环顾，滚动鼠标滚轮缩放。点击物件检视，点击工作台切换视角。按 Esc 放回物件或回到电脑桌。',
          )}
        </p>
        {!ready && (
          <LoadingScreen
            progress={progress}
            ready={resourcesReady}
            reducedMotion={environment.reducedMotion}
            onComplete={() => setLoadingComplete(true)}
          />
        )}
        {ready && <FpsMeter />}
        <Suspense fallback={null}>
          {fontsLoaded && (
            <StudioView
              mode={mode}
              environment={environment}
              onMode={handleMode}
              onPress={handlePress}
              onHint={handleHint}
              onReady={() => setSceneReady(true)}
              onProgress={setProgress}
              musicLevels={music.levels}
              screen={screen}
              caption={caption}
              inspectionAnchor={inspectionAnchor}
              controls={controls}
              showMinimap={ready}
            />
          )}
        </Suspense>
        <button
          type="button"
          className="keyboard-entry"
          onClick={() => controls.current?.open()}
          disabled={!ready || (mode !== 'room' && mode !== 'bench')}
        >
          {mode === 'bench'
            ? t('Return to the computer desk', '回到电脑桌')
            : t('Open computer', '打开电脑')}
        </button>
        <div
          className="world-cue"
          ref={cue}
          aria-live="polite"
          style={{ '--cue-x': '50%', '--cue-y': '54%' } as CSSProperties}
        >
          {ready && ['room', 'bench', 'board', 'drawer', 'window'].includes(mode) && hint && (
            <>
              <kbd>E</kbd>
              <span>{hint}</span>
            </>
          )}
        </div>
        <div
          className="object-caption"
          ref={caption}
          data-window-view={mode === 'window'}
          hidden={
            !ready ||
            !['inspect', 'case', 'remote', 'map', 'board', 'drawer', 'window'].includes(mode)
          }
        >
          {hint && !['board', 'drawer', 'window'].includes(mode) && (
            <div className="interaction-caption" aria-live="polite">
              {hint}
            </div>
          )}
          <button
            className="inspection-exit"
            type="button"
            onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))}
          >
            <kbd>Esc</kbd>
            <span>
              {mode === 'drawer'
                ? t('Close drawer', '关闭抽屉')
                : ['case', 'map', 'board', 'window'].includes(mode)
                  ? t('Back', '返回')
                  : t('Put back', '放回')}
            </span>
          </button>
        </div>
        {mode === 'inspect' && inspectionLink && (
          <a
            ref={inspectionAnchor}
            className="inspection-link"
            href={inspectionLink}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t('Felix on X', 'Felix 的 X 主页')}
          />
        )}
        <div ref={screen} className="screen-anchor" data-visible="false" data-interactive="false">
          <Desktop
            request={request}
            compact={false}
            visible={mode === 'computer'}
            environment={environment}
            setEnvironment={updateEnvironment}
            music={music}
            onExit={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))}
          />
        </div>
      </main>
    </RendererBoundary>
  );
}
