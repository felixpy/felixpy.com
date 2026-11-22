import { Component, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import {
  applyDaylightLighting,
  initialEnvironment,
  isRoomLook,
  pressRemote,
  type Environment,
} from './environment';
import { savedPreferences, toggleHomeLight } from './home-lights';
import type { AppID, InspectionLink, Target } from '../scene/studio';
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
import { loadParts } from '../scene/blender-library';
import '../spectral/spectral.css';
import { releaseSpectralSurface } from '../spectral/spectral-surface';

async function loadStudio() {
  const [view] = await Promise.all([import('../scene/StudioView'), loadParts('studio')]);
  return view;
}
type StudioModule = Awaited<ReturnType<typeof loadStudio>>;
const storageKey = 'felix-studio-v1';
const reviewMode = new URLSearchParams(location.search).get('review');
const deterministicReview =
  import.meta.env.DEV && reviewMode !== null && reviewMode !== 'live-weather';
const windowReview = deterministicReview && reviewMode === 'window';

function loadEnvironment(suggested: Environment['quality']): Environment {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  try {
    const stored = JSON.parse(
      window.localStorage.getItem(storageKey) ?? '{}',
    ) as Partial<Environment>;
    const automaticQuality = stored.automaticQuality ?? !stored.quality;
    const base = {
      ...initialEnvironment,
      reducedMotion,
      ...stored,
      roomLook: isRoomLook(stored.roomLook) ? stored.roomLook : initialEnvironment.roomLook,
      automaticQuality,
      quality: automaticQuality ? suggested : (stored.quality ?? suggested),
    };
    if (windowReview)
      return applyDaylightLighting({
        ...base,
        city: '上海',
        night: new URLSearchParams(location.search).get('time') !== 'day',
        weather: '晴',
        blinds: false,
      });
    return applyDaylightLighting(
      deterministicReview ? base : { ...base, ...localConditions(base.city), weather: '晴' },
    );
  } catch {
    return applyDaylightLighting({
      ...initialEnvironment,
      quality: suggested,
      ...localConditions(initialEnvironment.city),
      weather: '晴',
      reducedMotion,
    });
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

function graphicsDevice(): {
  available: boolean;
  quality: Environment['quality'];
  initialLowScale: number;
} {
  try {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('webgl2', {
      powerPreference: 'high-performance',
      alpha: false,
      antialias: false,
    });
    if (!context) return { available: false, quality: 'low', initialLowScale: 1 };
    const info = context.getExtension('WEBGL_debug_renderer_info');
    const renderer = info ? String(context.getParameter(info.UNMASKED_RENDERER_WEBGL)) : '';
    const software = /swiftshader|llvmpipe|microsoft basic render/i.test(renderer);
    const integrated =
      /\b(?:uhd|hd) graphics|iris(?:\(r\))? (?:xe|plus)|adreno[^\d]*[345]\d\d|mali-[gt][345]\d/i.test(
        renderer,
      );
    const limited = context.getParameter(context.MAX_TEXTURE_SIZE) < 8192;
    releaseSpectralSurface(canvas, context);
    return {
      available: true,
      quality: software || integrated || limited ? 'low' : 'high',
      initialLowScale: software ? 0.5 : 1,
    };
  } catch {
    return { available: false, quality: 'low', initialLowScale: 1 };
  }
}

export default function App({ prepareFonts }: { prepareFonts: () => Promise<unknown> }) {
  const [compact, setCompact] = useState(
    () => window.matchMedia('(max-width: 700px), (max-height: 420px)').matches,
  );
  const [graphics, setGraphics] = useState(() => (compact ? null : graphicsDevice()));
  const webGL = graphics?.available === true;
  const [ready, setReady] = useState(false);
  const [studio, setStudio] = useState<StudioModule | null>(null);
  const [studioUnavailable, setStudioUnavailable] = useState(false);
  const StudioView = studio?.default;
  const [progress, setProgress] = useState(0);
  const [environment, setEnvironment] = useState(() => loadEnvironment(graphics?.quality ?? 'low'));
  const manualConditions = useWindowConditions(
    environment.city,
    !deterministicReview && !compact && webGL,
    setEnvironment,
  );
  const music = useStudioMusic(!compact);
  const t = (en: string, zh: string) => local(environment.locale, en, zh);
  const [mode, setMode] = useState<Mode>('room');
  useRainAudio(
    environment.weather === '雨' && environment.rainAudio && !compact && webGL && ready,
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
  const screen = useRef<HTMLDivElement>(null);
  const controls = useRef<{ open: () => void }>(null);

  useEffect(() => {
    if (compact || !webGL) return;
    let active = true;
    void Promise.all([loadStudio(), prepareFonts()]).then(
      ([module]) => {
        if (active) setStudio(module);
      },
      () => {
        if (active) setStudioUnavailable(true);
      },
    );
    return () => {
      active = false;
    };
  }, [webGL, compact, prepareFonts]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 700px), (max-height: 420px)');
    const update = () => {
      if (!media.matches && !graphics) {
        const device = graphicsDevice();
        setGraphics(device);
        setEnvironment((current) =>
          current.automaticQuality ? { ...current, quality: device.quality } : current,
        );
      }
      setCompact(media.matches);
      setMode('room');
      setReady(false);
      setProgress(0);
      if (screen.current) screen.current.dataset.visible = 'false';
    };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [graphics]);

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
    if (windowReview) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(savedPreferences(environment)));
    } catch {
      /* Browsing without local storage still works. */
    }
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
  function handlePress(target: Target) {
    if (target.type === 'picture-lamp')
      setEnvironment((current) => ({
        ...current,
        pictureLamp: !(current.pictureLamp ?? current.night),
      }));
    if (target.type === 'equipment-track' || target.type === 'floor-lamp') {
      const key = target.type === 'equipment-track' ? 'wallLamp' : 'floorLamp';
      setEnvironment((current) => ({ ...current, [key]: !(current[key] ?? current.night) }));
    }
    if (target.type === 'screen-bar')
      setEnvironment((current) => ({ ...current, screenBar: !current.screenBar }));
    if (target.type === 'lamp') setEnvironment((current) => ({ ...current, lamp: !current.lamp }));
    if (target.type === 'bench-lamp')
      setEnvironment((current) => ({ ...current, benchLamp: !current.benchLamp }));
    if (target.type === 'tool-board-lamp')
      setEnvironment((current) => ({ ...current, toolBoardLamp: !current.toolBoardLamp }));
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
            'Drag or use the arrow keys to look around. Scroll to zoom. Click an object to examine it, or click the workbench or gear rack to move closer. Press Escape to put an object back or leave a view. After switching directly between views, Escape returns to the computer desk.',
            '拖动或按方向键环顾，滚动鼠标滚轮缩放。点击物件检视，点击工作台或装备架走近查看。按 Esc 放回物件或离开当前视角。切换视角后，按 Esc 回到电脑桌。',
          )}
        </p>
        {!ready && <LoadingScreen progress={progress} reducedMotion={environment.reducedMotion} />}
        {ready && <FpsMeter />}
        {StudioView && (
          <StudioView
            initialLowScale={graphics?.initialLowScale ?? 1}
            mode={mode}
            environment={environment}
            onMode={handleMode}
            onPress={handlePress}
            onToggleHomeLight={(id) => setEnvironment((current) => toggleHomeLight(current, id))}
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
            onClick={() => window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))}
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
