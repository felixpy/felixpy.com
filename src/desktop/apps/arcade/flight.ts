export const width = 192;
export const height = 304;
export const movement = [
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'KeyW',
  'KeyS',
  'KeyA',
  'KeyD',
];
export type FlightState = 'ready' | 'playing' | 'paused' | 'lost';
export type Point = { x: number; y: number };
export type Supply = 'power' | 'shield' | 'repair' | 'missile';
type Shot = Point & { vx: number; vy: number; hostile: boolean; homing?: boolean };
type Drone = Point & {
  kind: 'scout' | 'elite';
  origin: number;
  age: number;
  speed: number;
  phase: number;
  hp: number;
  maxHp: number;
  flash: number;
  fireAt: number;
};
type Spark = Point & { vx: number; vy: number; age: number };
type Pickup = Point & { kind: Supply };
const loadouts = [
  [
    [-4, 0],
    [4, 0],
  ],
  [
    [-6, -17],
    [0, 0],
    [6, 17],
  ],
  [
    [-9, -34],
    [-3, -10],
    [3, 10],
    [9, 34],
  ],
  [
    [-10, -52],
    [-5, -27],
    [0, 0],
    [5, 27],
    [10, 52],
  ],
];
const supplies = ['power', 'missile', 'shield', 'power', 'repair'] as const;

export function newFlight(random = Math.random) {
  return {
    pilot: { x: width / 2, y: height * 0.76, cooldown: 0, grace: 0 },
    shots: [] as Shot[],
    drones: [] as Drone[],
    sparks: [] as Spark[],
    pickups: [] as Pickup[],
    time: 0,
    wave: 1,
    score: 0,
    shields: 3,
    barrier: false,
    power: 1,
    next: 0.9,
    spawned: 0,
    defeated: 0,
    missiles: 0,
    missileCooldown: 0,
    drops: 0,
    nextSupplyKill: 1,
    random,
    supply: null as { kind: Supply; time: number } | null,
  };
}

function hasEntered(drone: Drone) {
  return drone.y >= 15 && drone.age >= 0.36;
}
export type Flight = ReturnType<typeof newFlight>;

function close(a: Point, b: Point, horizontal: number, vertical: number) {
  return Math.abs(a.x - b.x) < horizontal && Math.abs(a.y - b.y) < vertical;
}

function hit(flight: Flight) {
  if (flight.barrier) flight.barrier = false;
  else flight.shields--;
  flight.pilot.grace = 1.25;
}

function collect(flight: Flight, kind: Supply) {
  if (kind === 'power') {
    if (flight.power < loadouts.length) flight.power++;
    else flight.score += 250;
  } else if (kind === 'missile') {
    if (flight.missiles < 3) flight.missiles++;
    else flight.score += 250;
  } else if (kind === 'shield') flight.barrier = true;
  else flight.shields = Math.min(3, flight.shields + 1);
  flight.supply = { kind, time: flight.time };
}

function guide(shot: Shot, drones: Drone[], delta: number) {
  let target: Drone | undefined;
  let nearest = 150 ** 2;
  for (const drone of drones) {
    if (drone.hp <= 0 || !hasEntered(drone) || drone.y > shot.y + 14) continue;
    const range = (drone.x - shot.x) ** 2 + (drone.y - shot.y) ** 2;
    if (range < nearest) {
      nearest = range;
      target = drone;
    }
  }
  if (!target) return;
  const direction = Math.atan2(shot.vy, shot.vx);
  const aim = Math.atan2(target.y - shot.y, target.x - shot.x);
  const angle = Math.atan2(Math.sin(aim - direction), Math.cos(aim - direction));
  const heading = direction + Math.max(-4.6 * delta, Math.min(4.6 * delta, angle));
  shot.vx = Math.cos(heading) * 150;
  shot.vy = Math.sin(heading) * 150;
}

function spawnFormation(f: Flight, difficulty: number, sectorSize: number) {
  const leader = f.spawned;
  const formationSize =
    difficulty >= 7 && leader % 7 === 0 ? 3 : difficulty >= 3 && leader % 4 === 0 ? 2 : 1;
  const count = Math.min(formationSize, sectorSize - leader);
  const spacing = 26;
  const margin = 21 + ((count - 1) * spacing) / 2;
  const center =
    f.wave === 1 && leader === 0
      ? width / 2
      : margin + ((leader * 53 + f.wave * 19) % (width - margin * 2));
  for (let slot = 0; slot < count; slot++) {
    const index = f.spawned++;
    const elite = difficulty >= 3 && (index + f.wave) % (difficulty >= 8 ? 5 : 7) === 0;
    // Scale with rounds per burst and homing damage, keeping the same health throughout the encounter.
    const hp = elite ? 3 + f.power * 3 + f.missiles * 2 + Math.floor(difficulty * 0.56) : 1;
    const origin = center + (slot - (count - 1) / 2) * spacing;
    f.drones.push({
      kind: elite ? 'elite' : 'scout',
      x: origin,
      y: -12 - slot * 11,
      origin,
      age: 0,
      speed: (36 + difficulty * 4.2) * (elite ? 0.7 : 1),
      phase: leader * 0.75,
      hp,
      maxHp: hp,
      flash: 0,
      fireAt: elite ? 1.65 : 1.65 - difficulty * 0.04,
    });
  }
  f.next = f.time + Math.max(0.33, 1.05 - difficulty * 0.064) + (count - 1) * 0.12;
}

export function advance(
  f: Flight,
  keys: ReadonlySet<string>,
  delta: number,
  pointer?: Point,
): FlightState {
  f.time += delta;
  const p = f.pilot;
  const x =
    Number(keys.has('ArrowRight') || keys.has('KeyD')) -
    Number(keys.has('ArrowLeft') || keys.has('KeyA'));
  const y =
    Number(keys.has('ArrowDown') || keys.has('KeyS')) -
    Number(keys.has('ArrowUp') || keys.has('KeyW'));
  if (pointer && x === 0 && y === 0) {
    const dx = pointer.x - p.x,
      dy = pointer.y - p.y;
    const scale = Math.min(1, (delta * 176) / Math.max(1, Math.hypot(dx, dy)));
    p.x += dx * scale;
    p.y += dy * scale;
  } else {
    const step = (111 * delta) / Math.max(1, Math.hypot(x, y));
    p.x += x * step;
    p.y += y * step;
  }
  p.x = Math.max(9, Math.min(width - 9, p.x));
  p.y = Math.max(17, Math.min(height - 20, p.y));
  p.cooldown = Math.max(0, p.cooldown - delta);
  p.grace = Math.max(0, p.grace - delta);
  f.missileCooldown = Math.max(0, f.missileCooldown - delta);
  if (p.cooldown === 0) {
    p.cooldown = 0.24 - (f.power - 1) * 0.033;
    for (const [offset, spread] of loadouts[f.power - 1]) {
      f.shots.push({ x: p.x + offset, y: p.y - 10, vx: spread, vy: -220, hostile: false });
    }
  }
  if (
    f.missiles > 0 &&
    f.missileCooldown === 0 &&
    f.drones.some((drone) => drone.hp > 0 && hasEntered(drone) && drone.y < p.y)
  ) {
    f.missileCooldown = 1.22 - f.missiles * 0.13;
    for (let i = 0; i < f.missiles; i++) {
      const offset = i - (f.missiles - 1) / 2;
      f.shots.push({
        x: p.x + offset * 9,
        y: p.y - 6,
        vx: offset * 42,
        vy: -145,
        hostile: false,
        homing: true,
      });
    }
  }

  const difficulty = Math.min(f.wave, 16);
  const sectorSize = Math.min(46, 6 + 4 * f.wave);
  if (f.spawned < sectorSize && f.time >= f.next) {
    spawnFormation(f, difficulty, sectorSize);
  }

  for (const drone of f.drones) {
    const elite = drone.kind === 'elite';
    drone.age += delta;
    drone.flash = Math.max(0, drone.flash - delta);
    drone.x =
      drone.origin + Math.sin(drone.age * (elite ? 2.0 : 2.55) + drone.phase) * (elite ? 11 : 13);
    drone.y += drone.speed * delta;
    if (drone.y > 50 && drone.y < height - 32 && drone.age >= drone.fireAt) {
      drone.fireAt = elite ? drone.age + 1.84 : Infinity;
      const aim = Math.max(-45, Math.min(45, (p.x - drone.x) * 0.36));
      for (const spread of elite ? [-33, 0, 33] : [0]) {
        f.shots.push({
          x: drone.x,
          y: drone.y + 6,
          vx: aim + spread,
          vy: 87 + difficulty * 3.7,
          hostile: true,
        });
      }
    }
    if (p.grace === 0 && hasEntered(drone) && close(p, drone, elite ? 15 : 12, 10)) {
      hit(f);
      if (!elite) drone.hp = 0;
    }
  }

  for (const shot of f.shots) {
    if (shot.homing) guide(shot, f.drones, delta);
    shot.x += shot.vx * delta;
    shot.y += shot.vy * delta;
    if (shot.hostile) {
      if (p.grace === 0 && close(p, shot, 8, 9)) {
        hit(f);
        shot.y = height + 20;
      }
      continue;
    }
    const drone = f.drones.find(
      (item) =>
        item.hp > 0 && hasEntered(item) && close(shot, item, item.kind === 'elite' ? 12 : 8, 8),
    );
    if (!drone) continue;
    shot.y = -20;
    drone.hp -= shot.homing ? 2 : 1;
    drone.flash = 0.085;
    if (drone.hp > 0) continue;
    f.score += (drone.kind === 'elite' ? 300 : 100) + (f.wave - 1) * 10;
    if (++f.defeated === f.nextSupplyKill) {
      const kind = supplies[f.drops++ % supplies.length];
      f.pickups.push({ x: drone.x, y: drone.y, kind });
      f.nextSupplyKill += 4 + Math.floor(f.random() * 3);
    }
    for (let i = 0; i < 8; i++) {
      const angle = (i * Math.PI) / 4;
      f.sparks.push({
        x: drone.x,
        y: drone.y,
        vx: Math.sin(angle) * 34,
        vy: Math.cos(angle) * 34,
        age: 0,
      });
    }
  }
  f.shots = f.shots.filter(
    (shot) => shot.y > -10 && shot.y < height + 8 && shot.x > -8 && shot.x < width + 8,
  );
  f.drones = f.drones.filter((drone) => drone.hp > 0 && drone.y < height + 20);
  f.pickups = f.pickups.filter((pickup) => {
    pickup.y += delta * 54;
    if (close(p, pickup, 14, 13)) {
      collect(f, pickup.kind);
      return false;
    }
    return pickup.y < height + 10;
  });
  f.sparks = f.sparks.filter((particle) => {
    particle.x += particle.vx * delta;
    particle.y += particle.vy * delta;
    particle.age += delta;
    return particle.age < 0.36;
  });
  if (f.shields <= 0) return 'lost';
  if (f.spawned >= sectorSize && f.drones.length === 0) {
    f.wave++;
    f.spawned = 0;
    f.next = f.time + 2;
  }
  return 'playing';
}
