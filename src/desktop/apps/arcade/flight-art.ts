import { height, width, type Flight } from './flight';

const stars = Array.from({ length: 76 }, (_, i) => ({
  x: (i * 97 + i * i * 13) % width,
  y: (i * 53 + i * i * 7) % height,
  layer: i % 3,
}));
export const ship = [
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
export const attacker = [
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

export function sprite(
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

export function drawFlight(
  ctx: CanvasRenderingContext2D,
  flight: Flight,
  sector?: HTMLImageElement,
) {
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
