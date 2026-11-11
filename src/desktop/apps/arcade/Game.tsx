import { useEffect, useRef, useState } from 'react';
import { local, type Locale } from '../../../app/locale';
import {
  advance,
  height,
  movement,
  newFlight,
  width,
  type Flight,
  type FlightState,
  type Point,
  type Supply,
} from './flight';
import { createArcadeAudio } from './audio';

const stars = Array.from({ length: 76 }, (_, i) => ({
  x: (i * 97 + i * i * 13) % width,
  y: (i * 53 + i * i * 7) % height,
  layer: i % 3,
}));
const ship = [
  '......##......',
  '......##......',
  '.....#@@#.....',
  '.....#@@#.....',
  '....#@@@@#....',
  '....#@@@@#....',
  '..###@@@@###..',
  '.###@####@###.',
  '###@@####@@###',
  '#####@@@@#####',
  '..###@==@###..',
  '...##@==@##...',
  '....#....#....',
];
const attacker = [
  '....#####....',
  '...#######...',
  '..###@@@###..',
  '.####@@@####.',
  '###@#####@###',
  '##@##...##@##',
  '.###.....###.',
];
const elite = [
  '........###........',
  '.......#@@@#.......',
  '..#....#@@@#....#..',
  '.###..##@@@##..###.',
  '.###.###===###.###.',
  '#######=====#######',
  '##@####=====####@##',
  '###@####===####@###',
  '.###@###@@@###@###.',
  '..#####..@..#####..',
  '...###.......###...',
  '....#.........#....',
];
const supplyArt = {
  power: {
    color: '#ffe0a0',
    art: ['...#...', '..###..', '.#####.', '##.#.##', '...#...', '...#...'],
  },
  shield: {
    color: '#9ceae0',
    art: ['.#####.', '#.....#', '#.....#', '.#...#.', '..#.#..', '...#...'],
  },
  repair: {
    color: '#f5a3b1',
    art: ['..###..', '..###..', '#######', '#######', '..###..', '..###..'],
  },
  missile: {
    color: '#f7b186',
    art: ['...#...', '..###..', '..#@#..', '..#@#..', '.#####.', '..@.@..'],
  },
};
const missileArt = ['..#..', '.#@#.', '.#@#.', '#####', '.@.@.'];
const lifeArt = ['...#...', '..###..', '.#####.', '###.###'];

function sprite(
  ctx: CanvasRenderingContext2D,
  art: string[],
  x: number,
  y: number,
  colors: string[],
) {
  const top = Math.round(y - art.length / 2),
    left = Math.round(x - art[0].length / 2);
  art.forEach((row, iy) => {
    for (let ix = 0; ix < row.length; ix++) {
      const color = '#@='.indexOf(row[ix]);
      if (color < 0) continue;
      ctx.fillStyle = colors[color];
      ctx.fillRect(left + ix, top + iy, 1, 1);
    }
  });
}

function draw(ctx: CanvasRenderingContext2D, flight: Flight, sector?: HTMLImageElement) {
  ctx.fillStyle = '#08091a';
  ctx.fillRect(0, 0, width, height);
  if (sector?.complete && sector.naturalWidth) {
    const scroll = Math.floor(flight.time * 5) % height;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(sector, 0, scroll, width, height);
    ctx.drawImage(sector, 0, scroll - height, width, height);
  }
  for (const star of stars) {
    ctx.fillStyle = ['#53627a', '#8c9bb2', '#e2c89b'][star.layer];
    ctx.fillRect(
      star.x,
      Math.floor((star.y + flight.time * (9 + star.layer * 11)) % height),
      star.layer === 2 ? 2 : 1,
      1,
    );
  }
  for (const shot of flight.shots) {
    if (shot.homing) {
      ctx.fillStyle = '#9a5a65';
      for (let i = 1; i < 4; i++) {
        ctx.fillRect(
          Math.round(shot.x - shot.vx * i * 0.018),
          Math.round(shot.y - shot.vy * i * 0.018),
          1,
          1,
        );
      }
      sprite(ctx, missileArt, shot.x, shot.y, ['#f6b579', '#fff2bd']);
      continue;
    }
    const x = Math.round(shot.x),
      y = Math.round(shot.y);
    ctx.fillStyle = shot.hostile ? '#ff7068' : '#b7e9d9';
    ctx.fillRect(x - 1, y - 3, shot.hostile ? 3 : 2, 6);
    if (shot.hostile) {
      ctx.fillStyle = '#ffe7af';
      ctx.fillRect(x, y - 1, 1, 3);
    }
  }
  for (const drone of flight.drones) {
    const armored = drone.kind === 'elite';
    const colors =
      drone.flash > 0
        ? ['#f7dfbc', '#ffffff', '#ff906e']
        : armored
          ? ['#a44c69', '#ff9b84', '#ffe1a6']
          : ['#746a9a', '#d99f9d'];
    sprite(ctx, armored ? elite : attacker, drone.x, drone.y, colors);
    const x = Math.round(drone.x),
      y = Math.round(drone.y);
    if (armored && drone.y > 14) {
      ctx.fillStyle = '#412d45';
      ctx.fillRect(x - 7, y + 9, 14, 2);
      ctx.fillStyle = '#f7ad87';
      ctx.fillRect(x - 7, y + 9, Math.ceil((14 * drone.hp) / drone.maxHp), 2);
    }
    if (drone.y > 42 && drone.y < height - 32 && drone.fireAt - drone.age < 0.26) {
      ctx.fillStyle = '#ffd893';
      ctx.fillRect(x - 1, y + 4, 3, 2);
    }
  }
  for (const pickup of flight.pickups) {
    const { color, art } = supplyArt[pickup.kind];
    const x = Math.round(pickup.x),
      y = Math.round(pickup.y);
    ctx.fillStyle = '#151c29';
    ctx.fillRect(x - 7, y - 6, 14, 12);
    ctx.strokeStyle = color;
    ctx.strokeRect(x - 6.5, y - 5.5, 13, 11);
    sprite(ctx, art, x, y, [color, '#fff1c7']);
  }
  for (const particle of flight.sparks) {
    ctx.fillStyle = particle.age < 0.15 ? '#ffe0a2' : '#d17469';
    ctx.fillRect(Math.round(particle.x), Math.round(particle.y), 2, 2);
  }
  const p = flight.pilot;
  if (flight.barrier) {
    ctx.strokeStyle = '#7ed6d3';
    ctx.beginPath();
    ctx.arc(Math.round(p.x), Math.round(p.y), 13.5, 0, Math.PI * 2);
    ctx.stroke();
  }
  if (p.grace === 0 || Math.floor(flight.time * 15) % 2 === 0) {
    sprite(ctx, ship, p.x, p.y, ['#d2e0e1', '#7394b6', '#d88557']);
    ctx.fillStyle = '#eeba75';
    ctx.fillRect(
      Math.round(p.x - 1),
      Math.round(p.y + 7),
      2,
      Math.floor(2 + ((flight.time * 37) % 4)),
    );
  }
  for (let i = 0; i < 3; i++) {
    sprite(ctx, lifeArt, 10 + i * 9, height - 8, [i < flight.shields ? '#ebd293' : '#586274']);
  }
  for (let i = 0; i < flight.power; i++) {
    ctx.fillStyle = '#80c8cb';
    ctx.fillRect(8 + i * 4, height - 17, 2, 2);
  }
}

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
