import { useEffect, useRef } from 'react';

export function useRainAudio(raining: boolean, closeToWindow: boolean, blinds: boolean) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const settings = useRef({ raining, closeToWindow, blinds });
  settings.current = { raining, closeToWindow, blinds };
  const sync = useRef<(() => void) | null>(null);
  useEffect(() => {
    const player = new Audio('/media/audio/ambience/rain-window.ogg');
    player.preload = 'none';
    player.loop = true;
    audio.current = player;
    sync.current = () => {
      const { raining, closeToWindow, blinds } = settings.current;
      player.volume = (closeToWindow ? 0.24 : 0.11) * (blinds ? 0.55 : 1);
      if (raining && !document.hidden && player.paused) void player.play().catch(() => {});
      if ((!raining || document.hidden) && !player.paused) player.pause();
    };
    const update = () => sync.current?.();
    const check = () => {
      if (!settings.current.raining || document.hidden) player.pause();
    };
    window.addEventListener('pointerdown', update);
    window.addEventListener('keydown', update);
    document.addEventListener('visibilitychange', update);
    player.addEventListener('playing', check);
    update();
    return () => {
      window.removeEventListener('pointerdown', update);
      window.removeEventListener('keydown', update);
      document.removeEventListener('visibilitychange', update);
      player.removeEventListener('playing', check);
      player.pause();
      player.removeAttribute('src');
      player.load();
      audio.current = sync.current = null;
    };
  }, []);
  useEffect(() => {
    sync.current?.();
  }, [raining, closeToWindow, blinds]);
}
