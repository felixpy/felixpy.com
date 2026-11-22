import { useEffect, useRef, useState } from 'react';
import { local, type Locale } from '../../../app/locale';
import {
  advance,
  height,
  movement,
  newFlight,
  width,
  type FlightState,
  type Point,
  type Supply,
} from './flight';
import { createArcadeAudio } from './audio';
import { drawFlight as draw } from './flight-art';

export default function Game({
  locale,
  active,
  sound,
}: {
  locale: Locale;
  active: boolean;
  sound: boolean;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const shell = useRef<HTMLDivElement>(null);
  const control = useRef(new Set<string>());
  const pointer = useRef<Point | undefined>(undefined);
  const live = useRef<FlightState>('ready');
  const flight = useRef(newFlight());
  const audio = useRef<ReturnType<typeof createArcadeAudio> | null>(null);
  const [state, setState] = useState<FlightState>('ready');
  const [supply, setSupply] = useState<Supply | null>(null);
  const [score, setScore] = useState(0);
  const t = (en: string, zh: string) => local(locale, en, zh);

  function set(value: FlightState) {
    live.current = value;
    setState(value);
    control.current.clear();
    pointer.current = undefined;
  }
  function start() {
    if (live.current !== 'paused') {
      flight.current = newFlight();
      setSupply(null);
      setScore(0);
    }
    set('playing');
    canvas.current?.focus();
    if (sound && window.AudioContext) {
      const player = (audio.current ??= createArcadeAudio());
      void player.start().then(() => {
        if (audio.current === player && live.current === 'playing') player.play('start');
      });
    }
  }
  useEffect(() => {
    if (!active && live.current === 'playing') set('paused');
  }, [active]);
  useEffect(() => {
    audio.current?.setEnabled(sound && active);
  }, [sound, active]);

  useEffect(() => {
    const ctx = canvas.current?.getContext('2d');
    if (!ctx) return;
    const sector = new Image();
    sector.onload = () => draw(ctx, flight.current, sector);
    sector.src = '/media/arcade/orbital-sector.webp';
    draw(ctx, flight.current);
    let frame = 0,
      last = performance.now();
    function tick(now: number) {
      const delta = Math.min(0.045, (now - last) / 1000);
      last = now;
      const f = flight.current;
      if (live.current === 'playing') {
        const before = f.supply;
        const scoreBefore = f.score;
        const pulseBefore = f.pilot.cooldown,
          missileBefore = f.missileCooldown,
          graceBefore = f.pilot.grace,
          defeatedBefore = f.defeated;
        const next = advance(f, control.current, delta, pointer.current);
        if (f.score !== scoreBefore) setScore(f.score);
        if (f.pilot.cooldown > pulseBefore) audio.current?.play('pulse');
        if (f.missileCooldown > missileBefore) audio.current?.play('missile');
        if (f.pilot.grace > graceBefore) audio.current?.play('hit');
        if (f.defeated > defeatedBefore) audio.current?.play('destroy');
        if (f.supply && f.time - f.supply.time > 1.75) f.supply = null;
        if (f.supply !== before) {
          setSupply(f.supply?.kind ?? null);
          if (f.supply) audio.current?.play('pickup');
        }
        if (next !== 'playing') {
          if (next === 'lost') audio.current?.play('lost');
          set(next);
        }
        draw(ctx!, f, sector);
      }
      frame = requestAnimationFrame(tick);
    }
    const release = (event: KeyboardEvent) => control.current.delete(event.code);
    const suspend = () => {
      if (live.current === 'playing') set('paused');
    };
    const visibility = () => {
      if (document.hidden) suspend();
    };
    frame = requestAnimationFrame(tick);
    window.addEventListener('keyup', release);
    window.addEventListener('blur', suspend);
    document.addEventListener('visibilitychange', visibility);
    return () => {
      cancelAnimationFrame(frame);
      sector.onload = null;
      audio.current?.dispose();
      audio.current = null;
      window.removeEventListener('keyup', release);
      window.removeEventListener('blur', suspend);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, []);

  const name =
    state === 'paused'
      ? t('Paused', '已暂停')
      : state === 'lost'
        ? t('Signal lost', '失去信号')
        : t('Orbital Patrol', '近地航线');
  const button =
    state === 'paused'
      ? t('Resume', '继续')
      : state === 'ready'
        ? t('Start', '开始')
        : t('Retry', '重开');
  const supplyNames = {
    power: t('Weapon upgraded', '武器升级'),
    shield: t('Shield equipped', '护盾已装备'),
    repair: t('Hull repaired', '机体已修复'),
    missile: t('Homing missiles equipped', '追踪导弹已装备'),
  };
  function aim(event: React.PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    pointer.current = {
      x: ((event.clientX - rect.left) / rect.width) * width,
      y: ((event.clientY - rect.top) / rect.height) * height - 10,
    };
  }

  return (
    <div className="game" ref={shell}>
      <div className="flight-view">
        <canvas
          ref={canvas}
          width={width}
          height={height}
          tabIndex={0}
          aria-label={t('Orbital Patrol playfield', '近地航线游戏画面')}
          onPointerDown={(event) => {
            if (live.current !== 'playing' || event.button !== 0) return;
            event.currentTarget.focus();
            event.currentTarget.setPointerCapture(event.pointerId);
            aim(event);
          }}
          onPointerMove={(event) => {
            if (pointer.current) aim(event);
          }}
          onLostPointerCapture={() => {
            pointer.current = undefined;
          }}
          onBlur={(event) => {
            control.current.clear();
            if (live.current === 'playing' && !shell.current?.contains(event.relatedTarget))
              set('paused');
          }}
          onKeyDown={(event) => {
            if (live.current !== 'playing') return;
            if (event.key === 'Escape' || event.code === 'KeyP') {
              event.preventDefault();
              event.stopPropagation();
              set('paused');
            } else if (movement.includes(event.code)) {
              event.preventDefault();
              event.stopPropagation();
              control.current.add(event.code);
            }
          }}
        />
        {state === 'playing' && (
          <>
            {supply && (
              <div className="flight-pickup" role="status">
                {supplyNames[supply]}
              </div>
            )}
            <output className="flight-score" aria-label={t('Score', '得分')} aria-live="off">
              {String(score).padStart(6, '0')}
            </output>
            <button
              type="button"
              className="flight-pause"
              aria-label={t('Pause', '暂停')}
              onClick={() => set('paused')}
            />
          </>
        )}
        {state !== 'playing' && (
          <div className="game-overlay">
            <h1>{name}</h1>
            <p>
              {state === 'ready'
                ? t(
                    'Endless patrol. Steer with the arrow keys, WASD or drag. Your ship fires automatically.',
                    '无尽巡航。用方向键、WASD 或拖动操纵，飞船自动开火。',
                  )
                : t('Sector', '扇区') +
                  ' ' +
                  flight.current.wave +
                  ' · ' +
                  t('Score', '得分') +
                  ' ' +
                  score}
            </p>
            <button type="button" className="flight-action" onClick={start}>
              {button}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
