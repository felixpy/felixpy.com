import { useCallback, useEffect, useRef, useState } from 'react';
import Shader from '../../spectral/Shader';
import phosphor from '../../spectral/shaders/phosphor-loader.glsl?raw';
import '@fontsource/ibm-plex-mono/latin-500.css';

const approachProgress = 0.9;
const progressIntervalMs = 100;

export default function LoadingScreen({
  progress,
  reducedMotion,
}: {
  progress: number;
  reducedMotion: boolean;
}) {
  const track = useRef<HTMLDivElement>(null);
  const meter = useRef<HTMLProgressElement>(null);
  const percent = useRef<HTMLSpanElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const start = useRef<number | null>(null);
  const displayed = useRef(0);
  const [legacy] = useState(
    () => new URLSearchParams(location.search).get('studio-loader') === 'legacy',
  );
  const [phosphorReady, setPhosphorReady] = useState(false);
  useEffect(() => {
    if (!legacy) return;
    const timer = window.setTimeout(() => setPhosphorReady(true), 2200);
    return () => window.clearTimeout(timer);
  }, [legacy]);
  const paintTitle = useCallback(
    (context: CanvasRenderingContext2D, viewport: HTMLCanvasElement) => {
      const heading = title.current;
      if (!heading || !viewport.clientWidth) return;
      const ratio = viewport.width / viewport.clientWidth;
      const bounds = heading.getBoundingClientRect();
      const area = viewport.getBoundingClientRect();
      const style = getComputedStyle(heading);
      context.fillStyle = '#fff';
      context.font = `${style.fontWeight} ${parseFloat(style.fontSize) * ratio}px ${style.fontFamily}`;
      context.letterSpacing = `${parseFloat(style.letterSpacing) * ratio}px`;
      context.textAlign = 'center';
      context.textBaseline = 'middle';
      context.fillText(
        heading.textContent ?? '',
        (bounds.left - area.left + bounds.width / 2) * ratio,
        (bounds.top - area.top + bounds.height / 2) * ratio,
      );
    },
    [],
  );
  useEffect(() => {
    const started = (start.current ??= performance.now());
    let frame = 0;
    let timer = 0;
    function update(now: number) {
      const elapsed = Math.max(0, now - started);
      const waiting = Math.min(1, elapsed / 1900);
      const next = Math.max(
        displayed.current,
        approachProgress * (1 - (1 - waiting) ** 2.4),
        progress * 0.95,
      );
      if (next !== displayed.current) {
        displayed.current = next;
        track.current?.style.setProperty('--progress', (next * 100).toFixed(2) + '%');
        if (meter.current) meter.current.value = next;
        const label = `${Math.floor(next * 100)}%`;
        if (percent.current && percent.current.textContent !== label)
          percent.current.textContent = label;
      }
      if (waiting >= 1 || next >= approachProgress) return;
      if (legacy) frame = requestAnimationFrame(update);
      else timer = window.setTimeout(() => update(performance.now()), progressIntervalMs);
    }
    if (legacy) frame = requestAnimationFrame(update);
    else update(performance.now());
    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(timer);
    };
  }, [legacy, progress]);

  return (
    <section
      className="studio-loading phosphor-loader"
      lang="en"
      aria-labelledby="loading-title"
      data-reduced-motion={reducedMotion}
      data-loader-animation={legacy ? 'legacy' : 'composited'}
    >
      <h1 id="loading-title" ref={title}>
        FELIX.PY
      </h1>
      {phosphorReady && (
        <Shader
          fragment={phosphor}
          animate={!reducedMotion}
          maxDpr={0.8}
          paintBackdrop={paintTitle}
        />
      )}
      <p>Taste Is All You Need</p>
      <div className="phosphor-progress">
        <div className="phosphor-track" ref={track}>
          <progress ref={meter} className="sr-only" max={1} aria-label="Room loading progress" />
          <span className="phosphor-fill" aria-hidden="true" />
          <span className="phosphor-cursor" aria-hidden="true">
            <span />
          </span>
        </div>
        <span className="phosphor-percent" ref={percent} aria-hidden="true">
          0%
        </span>
      </div>
    </section>
  );
}
