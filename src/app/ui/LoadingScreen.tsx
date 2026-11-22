import { useCallback, useEffect, useRef, useState } from 'react';
import Shader from '../../spectral/Shader';
import phosphor from '../../spectral/shaders/phosphor-loader.glsl?raw';
import '@fontsource/ibm-plex-mono/latin-500.css';

const approachProgress = 0.9;

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
  const [phosphorReady, setPhosphorReady] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setPhosphorReady(true), 2200);
    return () => window.clearTimeout(timer);
  }, []);
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
  const status = useRef(progress);
  status.current = progress;
  useEffect(() => {
    const start = performance.now();
    let displayed = 0,
      frame = 0;
    function update(now: number) {
      const elapsed = Math.max(0, now - start);
      const waiting = Math.min(1, elapsed / 1900);
      displayed = Math.max(
        displayed,
        approachProgress * (1 - (1 - waiting) ** 2.4),
        status.current * 0.95,
      );
      track.current?.style.setProperty('--progress', (displayed * 100).toFixed(2) + '%');
      if (meter.current) meter.current.value = displayed;
      if (percent.current) {
        const label = `${Math.floor(displayed * 100)}%`;
        if (percent.current.textContent !== label) percent.current.textContent = label;
      }
      frame = requestAnimationFrame(update);
    }
    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <section
      className="studio-loading phosphor-loader"
      lang="en"
      aria-labelledby="loading-title"
      data-reduced-motion={reducedMotion}
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
