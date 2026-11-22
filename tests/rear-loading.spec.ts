import { expect, test } from '@playwright/test';
import { LoadingManager } from 'three';
import { rearLoading } from '../src/scene/rear-loading';

test('rear loading starts three jobs, boosts a requested area, and waits for real completion', async () => {
  const rear = rearLoading(new LoadingManager(), true);
  const started: string[] = [];
  function job(area: Parameters<typeof rear.defer>[0], name: string) {
    const gate = Promise.withResolvers<void>();
    rear.defer(area)(() => {
      started.push(name);
      return gate.promise;
    });
    return gate;
  }

  const cabinet = job('cabinet', 'cabinet');
  const bench = job('bench', 'bench');
  const gear = job('gear', 'gear');
  const desk = [job('desk', 'first'), job('desk', 'second'), job('desk', 'third')];
  const ready = rear.prepare();
  let loaded = false;
  void ready.then(() => (loaded = true));
  await expect.poll(() => started).toEqual(['first', 'second', 'third']);
  expect(rear.prepare('gear')).toBe(ready);
  desk[0].resolve();
  await expect.poll(() => started).toEqual(['first', 'second', 'third', 'gear']);
  desk[1].reject(new Error('Test request failed'));
  await expect.poll(() => started).toEqual(['first', 'second', 'third', 'gear', 'bench']);
  desk[2].resolve();
  await expect
    .poll(() => started)
    .toEqual(['first', 'second', 'third', 'gear', 'bench', 'cabinet']);
  expect(loaded).toBe(false);
  cabinet.resolve();
  bench.resolve();
  gear.resolve();
  await ready;
  expect(loaded).toBe(true);
});

test('a throwing deferred factory leaves the remaining room loads usable', async () => {
  const manager = new LoadingManager();
  const rear = rearLoading(manager, false);
  const errors: string[] = [];
  manager.onError = (url) => errors.push(url);
  rear.defer('desk')(() => {
    throw new Error('Test factory failed before starting a request');
  });
  let mounted = false;
  rear.defer('bench')(async () => {
    manager.itemStart('bench');
    await Promise.resolve();
    mounted = true;
    manager.itemEnd('bench');
  });
  await rear.prepare();
  expect(errors).toHaveLength(1);
  expect(mounted).toBe(true);
});
