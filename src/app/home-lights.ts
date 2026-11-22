import { initialEnvironment, type Environment } from './environment';
import type { Target } from '../scene/interaction';

export const homeLights = [
  { id: 'ceilingLamp', target: null, en: 'Ceiling light', zh: '顶灯' },
  { id: 'wallLamp', target: 'equipment-track', en: 'Track lights', zh: '轨道灯' },
  { id: 'floorLamp', target: 'floor-lamp', en: 'Floor lamp', zh: '落地灯' },
  { id: 'pictureLamp', target: 'picture-lamp', en: 'Picture light', zh: '画灯' },
  { id: 'lamp', target: 'lamp', en: 'Desk lamp', zh: '书桌灯' },
  { id: 'screenBar', target: 'screen-bar', en: 'Monitor light bar', zh: '屏幕挂灯' },
  { id: 'benchLamp', target: 'bench-lamp', en: 'Workbench lamp', zh: '工作台灯' },
  { id: 'toolBoardLamp', target: 'tool-board-lamp', en: 'Tool board light', zh: '工具板灯' },
] as const satisfies ReadonlyArray<{
  id: keyof Environment;
  target: Target['type'] | null;
  en: string;
  zh: string;
}>;

export type HomeLightId = (typeof homeLights)[number]['id'];

export function lightForTarget(type: Target['type']) {
  return homeLights.find((light) => light.target === type)?.id;
}

export function savedPreferences(environment: Environment) {
  const preferences: Partial<Environment> = { ...environment };
  for (const { id } of homeLights) delete preferences[id];
  return preferences;
}

export function isHomeLightOn(env: Environment, id: HomeLightId) {
  const enabled = env[id] ?? env.night;
  return id === 'ceilingLamp' ? enabled && env.ceiling > 0 : enabled;
}

export function ceilingLightLevel(env: Environment) {
  return isHomeLightOn(env, 'ceilingLamp') ? env.ceiling : 0;
}

export function toggleHomeLight(env: Environment, id: HomeLightId): Environment {
  const enabled = !isHomeLightOn(env, id);
  if (id === 'ceilingLamp' && enabled && env.ceiling === 0) {
    return { ...env, ceilingLamp: true, ceiling: initialEnvironment.ceiling };
  }
  return { ...env, [id]: enabled };
}
