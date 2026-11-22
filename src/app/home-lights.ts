import { initialEnvironment, type Environment } from './environment';

export const homeLights = [
  { id: 'ceilingLamp', en: 'Ceiling light', zh: '顶灯' },
  { id: 'wallLamp', en: 'Track lights', zh: '轨道灯' },
  { id: 'floorLamp', en: 'Floor lamp', zh: '落地灯' },
  { id: 'pictureLamp', en: 'Picture light', zh: '画灯' },
  { id: 'lamp', en: 'Desk lamp', zh: '书桌灯' },
  { id: 'screenBar', en: 'Monitor light bar', zh: '屏幕挂灯' },
  { id: 'benchLamp', en: 'Workbench lamp', zh: '工作台灯' },
  { id: 'toolBoardLamp', en: 'Tool board light', zh: '工具板灯' },
] as const;

export type HomeLightId = (typeof homeLights)[number]['id'];

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
