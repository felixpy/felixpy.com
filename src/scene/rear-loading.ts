import type PQueue from 'p-queue';
import type { LoadingManager } from 'three';

const priorities = { desk: 4, bench: 3, gear: 2, cabinet: 1 };
type Area = keyof typeof priorities;
export type DeferRoomAsset = (load: () => Promise<unknown>) => void;
type Job = { id: string; area: Area; load: () => Promise<unknown> };

export function rearLoading(manager: LoadingManager, prioritized: boolean) {
  const token = 'deferred-room-detail';
  const jobs: Job[] = [];
  const waiting = new Set<Job>();
  let queue: PQueue | undefined;
  let preferred: Area | undefined;
  let started = false;
  manager.itemStart(token);
  const ready = new Promise<void>((resolve) => {
    manager.onLoad = resolve;
  });

  function priority(job: Job) {
    return job.area === preferred ? 5 : priorities[job.area];
  }

  function launchTogether() {
    for (const { load } of jobs.splice(0)) {
      try {
        void load().catch(() => {});
      } catch {
        manager.itemError(token);
      }
    }
  }

  async function launchPrioritized() {
    let scheduler: PQueue;
    try {
      const { default: Queue } = await import('p-queue');
      scheduler = new Queue({ concurrency: 3, autoStart: false });
    } catch {
      launchTogether();
      return;
    }
    queue = scheduler;
    for (const job of jobs.splice(0)) {
      waiting.add(job);
      void scheduler
        .add(
          () => {
            waiting.delete(job);
            return job.load();
          },
          { id: job.id, priority: priority(job) },
        )
        .catch(() => {});
    }
    try {
      scheduler.start();
      await scheduler.onIdle();
    } finally {
      waiting.clear();
      queue = undefined;
    }
  }

  return {
    ready,
    defer(area: Area): DeferRoomAsset {
      return (load) => jobs.push({ area, load, id: `${area}-${jobs.length}` });
    },
    prepare(area?: Area) {
      if (area && area !== preferred) {
        preferred = area;
        for (const job of waiting) queue?.setPriority(job.id, priority(job));
      }
      if (!started) {
        started = true;
        if (prioritized) {
          void launchPrioritized()
            .catch(() => manager.itemError(token))
            .finally(() => manager.itemEnd(token));
        } else {
          launchTogether();
          manager.itemEnd(token);
        }
      }
      return ready;
    },
  };
}
