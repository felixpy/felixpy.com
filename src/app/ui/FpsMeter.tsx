import { useEffect, useRef } from 'react';

export default function FpsMeter() {
  const value = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let request = 0;
    let started = 0;
    let frames = 0;
    function measure(now: number) {
      if (!started) started = now;
      frames++;
      if (now - started >= 800) {
        if (value.current)
          value.current.textContent = String(Math.round(((frames - 1) * 1000) / (now - started)));
        started = now;
        frames = 1;
      }
      request = requestAnimationFrame(measure);
    }
    function visibility() {
      cancelAnimationFrame(request);
      started = 0;
      frames = 0;
      if (!document.hidden) request = requestAnimationFrame(measure);
    }
    visibility();
    document.addEventListener('visibilitychange', visibility);
    return () => {
      cancelAnimationFrame(request);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, []);

  return (
    <div className="fps-meter" aria-label="Frames per second">
      <span ref={value}>—</span> FPS
    </div>
  );
}
