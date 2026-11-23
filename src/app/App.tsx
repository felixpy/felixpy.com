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
import { pressRemote, type Environment } from './environment';
import { deterministicReview, loadEnvironment, saveEnvironment } from './environment-preferences';
import { graphicsDevice } from './graphics-device';
import { isMobileDevice } from './mobile-device';
import { lightForTarget, toggleHomeLight, type HomeLightId } from './home-lights';
import type { AppID, InspectionLink, Mode, StudioControls, Target } from '../scene/interaction';
import type { ComputerSession } from '../desktop/Desktop';
import Profile from '../desktop/apps/Profile';

const Desktop = lazy(() => import('../desktop/Desktop'));
import { useStudioMusic } from '../desktop/apps/music/useStudioMusic';
import LoadingScreen from './ui/LoadingScreen';
import FpsMeter from './ui/FpsMeter';
import { useRainAudio } from './hooks/useRainAudio';
import { useWindowConditions } from './hooks/useWindowConditions';
import { cityName, local } from './locale';
import './studio.css';
import { loadParts } from '../scene/blender-library';
import '../spectral/spectral.css';

async function loadStudio() {
  const [view] = await Promise.all([import('../scene/StudioView'), loadParts('studio')]);
  return view;
}
type StudioModule = Awaited<ReturnType<typeof loadStudio>>;

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

export default function App({ prepareFonts }: { prepareFonts: () => Promise<unknown> }) {
  const [mobile] = useState(() => isMobileDevice(navigator));
  const [graphics] = useState(() => (mobile ? null : graphicsDevice()));
  const webGL = graphics?.available === true;
  const [ready, setReady] = useState(false);
  const [studio, setStudio] = useState<StudioModule | null>(null);
  const [studioUnavailable, setStudioUnavailable] = useState(false);
  const StudioView = studio?.default;
  const [progress, setProgress] = useState(0);
  const [environment, setEnvironment] = useState(() => loadEnvironment(graphics?.quality ?? 'low'));
  const manualConditions = useWindowConditions(
    environment.city,
    !deterministicReview && webGL,
    setEnvironment,
  );
  const music = useStudioMusic(!mobile);
  const t = (en: string, zh: string) => local(environment.locale, en, zh);
  const [mode, setMode] = useState<Mode>('room');
  useRainAudio(
    environment.weather === '雨' && environment.rainAudio && webGL && ready,
    mode === 'remote' || mode === 'window',
    environment.blinds,
  );
  const [hint, setHint] = useState('');
  const [hoverHint, setHoverHint] = useState('');
  const [inspectionLink, setInspectionLink] = useState<InspectionLink>();
  const cue = useRef<HTMLDivElement>(null);
  const inspectionAnchor = useRef<HTMLAnchorElement>(null);
  const objectCaption = useRef<HTMLDivElement>(null);
  const [request, setRequest] = useState<{ id?: AppID; sequence: number }>({ sequence: 0 });
  const [computerSession, setComputerSession] = useState<ComputerSession>('unlocked');
  const screen = useRef<HTMLDivElement>(null);
  const controls = useRef<StudioControls>(null);

  useEffect(() => {
    if (computerSession !== 'unlocking') return;
    const timer = window.setTimeout(() => setComputerSession('unlocked'), 270);
    return () => window.clearTimeout(timer);
  }, [computerSession]);

  useEffect(() => {
    if (!webGL) return;
    let active = true;
    void prepareFonts();
    void loadStudio().then(
      (module) => {
        if (active) setStudio(module);
      },
      () => {
        if (active) setStudioUnavailable(true);
      },
    );
    return () => {
      active = false;
    };
  }, [webGL, prepareFonts]);

  useEffect(() => {
    const keepPageFocus = (event: KeyboardEvent) => {
      if (
        event.key === 'Tab' &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey &&
        !(event.target instanceof Element && event.target.closest('[data-phone-home]'))
      )
        event.preventDefault();
    };
    window.addEventListener('keydown', keepPageFocus, true);
    return () => window.removeEventListener('keydown', keepPageFocus, true);
  }, []);

  useEffect(() => {
    saveEnvironment(environment);
  }, [environment]);

  useEffect(() => {
    document.documentElement.lang = environment.locale === 'zh' ? 'zh-Hans' : 'en';
    document.title = environment.locale === 'zh' ? 'Felix Yang · 工作室' : 'Felix Yang — Studio';
    setHint('');
    setHoverHint('');
  }, [environment.locale]);

  const updateEnvironment = (patch: Partial<Environment>) =>
    setEnvironment((current) => ({
      ...current,
      ...patch,
      ...(patch.automaticQuality && graphics ? { quality: graphics.quality } : {}),
    }));
  function handleMode(next: Mode, app?: AppID, link?: InspectionLink) {
    setMode(next);
    setHoverHint('');
    setInspectionLink(link);
    if (next === 'computer' && app)
      setRequest((prev) => ({ id: app, sequence: prev.sequence + 1 }));
  }
  function handleHover(text: string, point?: { x: number; y: number }) {
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
    setHoverHint(text);
  }
  function toggleLight(id: HomeLightId) {
    setEnvironment((current) => toggleHomeLight(current, id));
  }
  function handlePress(target: Target) {
    const light = lightForTarget(target.type);
    if (light) return toggleLight(light);
    if (target.type === 'key') {
      if (target.index === 1 && !environment.blinds)
        return t('Lower the blinds before tilting them', '先放下百叶再调节叶片');
      const next = pressRemote(environment, target.index);
      if (target.index === 2)
        manualConditions.current = { city: next.city, weather: false, night: false };
      if (target.index === 3) manualConditions.current.weather = true;
      if (target.index === 4)
        manualConditions.current = { city: next.city, weather: true, night: true };
      if (target.index === 5) manualConditions.current.night = true;
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
      <Suspense fallback={null}>
        <Desktop
          compact
          request={request}
          session={computerSession}
          setSession={setComputerSession}
          environment={environment}
          setEnvironment={updateEnvironment}
          music={music}
        />
      </Suspense>
      <FpsMeter />
    </main>
  );
  if (mobile)
    return (
      <main className="mobile-home">
        <Profile mobile locale={environment.locale} animate={!environment.reducedMotion} />
      </main>
    );
  if (!webGL || studioUnavailable) return simple;

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
            'Drag or use the arrow keys to look around. Scroll to zoom. Click an object to examine it, or click the workbench or gear rack to move closer. Press Escape to put an object back or leave the current view.',
            '拖动或按方向键环顾，滚动鼠标滚轮缩放。点击物件检视，点击工作台或装备架走近查看。按 Esc 放回物件或离开当前视角。',
          )}
        </p>
        {!ready && <LoadingScreen progress={progress} reducedMotion={environment.reducedMotion} />}
        {ready && <FpsMeter />}
        {StudioView && (
          <StudioView
            initialLowScale={graphics?.initialLowScale ?? 1}
            computerLocked={computerSession === 'locked'}
            mode={mode}
            environment={environment}
            onMode={handleMode}
            onPress={handlePress}
            onToggleHomeLight={toggleLight}
            onHint={setHint}
            onHover={handleHover}
            onReady={() => setReady(true)}
            onProgress={setProgress}
            musicLevels={music.levels}
            musicPlaying={music.playing}
            screen={screen}
            inspectionAnchor={inspectionAnchor}
            objectCaption={objectCaption}
            controls={controls}
            roomVisible={ready}
          />
        )}
        <button
          type="button"
          className="keyboard-entry"
          onClick={() => controls.current?.open()}
          disabled={!ready || mode !== 'room'}
        >
          {t('Open computer', '打开电脑')}
        </button>
        {ready && mode === 'bench' && (
          <div className="workbench-exit-hint">
            <kbd>Esc</kbd> {t('Return to the computer desk', '回到电脑桌')}
          </div>
        )}
        <div
          className="world-cue"
          ref={cue}
          aria-live="polite"
          style={{ '--cue-x': '50%', '--cue-y': '54%' } as CSSProperties}
        >
          {ready && hoverHint && (
            <>
              <kbd>E</kbd>
              <span>{hoverHint}</span>
            </>
          )}
        </div>
        <div
          className="object-caption"
          ref={objectCaption}
          hidden={
            !ready ||
            ![
              'inspect',
              'case',
              'remote',
              'map',
              'board',
              'gear',
              'bookshelf',
              'drawer',
              'window',
            ].includes(mode)
          }
        >
          {hint && !['board', 'gear', 'drawer', 'window'].includes(mode) && (
            <div className="interaction-caption" aria-live="polite">
              {hint}
            </div>
          )}
          <button
            className="inspection-exit"
            type="button"
            onClick={() => controls.current?.exit()}
          >
            <kbd>Esc</kbd>
            <span>
              {mode === 'drawer'
                ? t('Close drawer', '关闭抽屉')
                : ['case', 'map', 'board', 'gear', 'bookshelf', 'window'].includes(mode)
                  ? t('Back', '返回')
                  : t('Put back', '放回')}
            </span>
          </button>
        </div>
        {mode === 'inspect' && inspectionLink?.region && (
          <a
            ref={inspectionAnchor}
            className="inspection-link"
            href={inspectionLink.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={t('Felix on X', 'Felix 的 X 主页')}
          />
        )}
        <div ref={screen} className="screen-anchor" data-visible="false" data-interactive="false">
          {(mode === 'computer' || request.sequence > 0) && (
            <Suspense fallback={null}>
              <Desktop
                request={request}
                session={computerSession}
                setSession={setComputerSession}
                compact={false}
                visible={mode === 'computer'}
                environment={environment}
                setEnvironment={updateEnvironment}
                music={music}
                onExit={() => controls.current?.exit()}
              />
            </Suspense>
          )}
        </div>
      </main>
    </RendererBoundary>
  );
}
