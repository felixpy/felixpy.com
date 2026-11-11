import { useEffect, useRef } from 'react';
import type { StudioMusic } from './useStudioMusic';

export default function Spectrum({
  read,
  animate,
}: {
  read: StudioMusic['spectrum'];
  animate: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const source = useRef(read);
  source.current = read;
  useEffect(() => {
    const node = canvas.current!;
    const context = node.getContext('2d');
    if (!context) return;
    const values = new Float32Array(76);
    const smooth = new Float32Array(values.length);
    let frame = 0;
    function draw() {
      const { width, height } = node;
      if (animate) source.current(values);
      context!.clearRect(0, 0, width, height);
      const gradient = context!.createLinearGradient(0, 0, width, 0);
      gradient.addColorStop(0, '#7397af');
      gradient.addColorStop(0.72, '#99cfdf');
      gradient.addColorStop(1, '#ca9a69');
      context!.fillStyle = gradient;
      const step = width / values.length;
      for (let i = 0; i < values.length; i++) {
        const rest = 0.1 + 0.06 * Math.sin(i * 2.3) ** 2;
        smooth[i] += (Math.max(rest, values[i]) - smooth[i]) * 0.32;
        const length = Math.max(2, smooth[i] * height * (0.78 + 0.2 * Math.sin(i * 1.53)));
        context!.fillRect(
          Math.round(i * step),
          (height - length) / 2,
          Math.max(1, Math.floor(step * 0.46)),
          length,
        );
      }
      if (animate && !document.hidden) frame = requestAnimationFrame(draw);
    }
    function resize() {
      node.width = Math.max(1, Math.round(node.clientWidth * Math.min(2, devicePixelRatio)));
      node.height = Math.max(1, Math.round(node.clientHeight * Math.min(2, devicePixelRatio)));
      if (!animate) draw();
    }
    function visibility() {
      cancelAnimationFrame(frame);
      if (animate && !document.hidden) frame = requestAnimationFrame(draw);
    }
    const observer = new ResizeObserver(resize);
    observer.observe(node);
    document.addEventListener('visibilitychange', visibility);
    resize();
    if (animate) visibility();
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [animate]);
  return <canvas className="spectral-spectrum" ref={canvas} aria-hidden="true" />;
}
