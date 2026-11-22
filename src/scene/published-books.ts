import * as T from 'three';
import { editions } from '../content/books';
import { bindEdition, enableClosePrint, pageStocks, type PaintCover } from './book-binding';
import { box, group, tube } from './geometry';
import type { Palette } from './materials';

export function publishedBooks(
  unit: T.Group,
  p: Palette,
  loader: T.TextureLoader,
  levels: number[],
  detailLoader: T.TextureLoader,
) {
  const stocks = pageStocks();
  const prints = new Map<string, { url: string; paint: PaintCover }>();
  const faceOut = new Set<string>();
  const rowEnds = new Set<string>();
  const neighbors = new Map<string, string[]>();
  const rearNeighbors = new Map<string, T.Group>();
  const fullSize = new Set<string>();
  const inFlight = new Map<string, Promise<void>>();
  const books = editions.map((edition) =>
    bindEdition(
      unit,
      edition,
      {
        load(url, paint) {
          prints.set(edition.key, { url, paint });
        },
      },
      stocks,
    ),
  );
  const inventory = new Map(
    editions.map((edition, i) => [edition.key, { object: books[i], size: edition.size }]),
  );
  function registerNeighbors(keys: string[]) {
    keys.forEach((key, i) => {
      neighbors.set(key, keys.slice(Math.max(0, i - 1), i + 2));
      if (i) rearNeighbors.set(key, inventory.get(keys[i - 1])!.object);
    });
  }
  function standing(level: number, keys: string[], lean: number, start = -0.269) {
    rowEnds.add(keys[0]);
    rowEnds.add(keys[keys.length - 1]);
    registerNeighbors(keys);
    const top = levels[level] + 0.014;
    let cursor = start,
      contactX = start;
    for (const [i, key] of keys.entries()) {
      const {
        object,
        size: [width, height, thick],
      } = inventory.get(key)!;
      const angle = i < keys.length - 3 ? 0 : lean;
      const cosine = Math.cos(angle),
        sine = Math.sin(angle);
      const base = cursor + (thick * cosine) / 2;
      object.rotation.set(0, Math.PI / 2, angle, 'ZXY');
      object.position.set(
        base - (height * sine) / 2,
        top + (height * cosine + thick * Math.abs(sine)) / 2,
        0.118 - width / 2 + 0.011 * Math.sin(i * 9.4 + level * 2.37),
      );
      cursor += thick / cosine + 0.0008;
      contactX = cursor - Math.min(height, 0.157) * Math.tan(angle);
    }
    const support = group(unit, 'Bent steel bookend', [contactX + 0.0011, top, 0.038]);
    box(support, [0.059, 0.0012, 0.116], [-0.029, 0.0006, -0.003], p.graphite, 0.00042);
    const side = box(support, [0.00155, 0.158, 0.108], [0, 0.0796, -0.005], p.graphite, 0.0006);
    side.rotation.x = -0.032;
    box(support, [0.0037, 0.008, 0.108], [0.0013, 0.156, -0.0076], p.graphite, 0.0009);
  }
  function display(key: string, level: number, x: number, yaw: number) {
    faceOut.add(key);
    const {
      object,
      size: [w, h, t],
    } = inventory.get(key)!;
    const top = levels[level] + 0.014,
      tilt = -0.14;
    const support = group(unit, 'Brass wire reading stand', [x, top, 0.041]);
    support.rotation.y = yaw;
    for (const side of [-1, 1]) {
      const x = side * w * 0.265;
      tube(support, [x, 0.0017, -0.059], [x, h * 0.53, -0.008], 0.00165, p.bronze);
      tube(support, [x, h * 0.53, -0.008], [x, 0.002, 0.038], 0.00165, p.bronze);
      tube(support, [x, 0.002, 0.038], [x, 0.0093, 0.04], 0.00145, p.bronze);
    }
    tube(support, [-w * 0.265, 0.002, -0.059], [w * 0.265, 0.002, -0.059], 0.00165, p.bronze);
    object.rotation.set(tilt, yaw, 0, 'YXZ');
    object.position.set(
      x,
      top + 0.002 + (h * Math.cos(tilt) + t * Math.abs(Math.sin(tilt))) / 2,
      0.072 - h * 0.5 * Math.sin(-tilt),
    );
  }
  standing(
    4,
    [
      'code-complete',
      'algorithms',
      'computer-systems',
      'data-intensive',
      'pragmatic',
      'patterns',
      'mythical',
      'c-language',
    ],
    -0.047,
  );
  display('sicp', 4, 0.156, -0.17);
  standing(
    3,
    [
      'moby',
      'own-room',
      'lighthouse',
      'darkness',
      'beloved',
      'butler',
      'frankenstein',
      'walden',
      'sound-and-fury',
      'dune',
      'neuromancer',
      'invisible-man',
    ],
    -0.105,
  );
  standing(
    2,
    ['machine', 'information', 'idea-factory', 'invention-nature', 'media', 'left-brain'],
    -0.083,
  );
  display('ways', 2, 0.008, -0.17);
  standing(
    1,
    [
      'mba',
      'grove',
      'thinking-systems',
      'fifth',
      'lean',
      'invisible-women',
      'code',
      'refactoring',
      'creative-act',
      'art-innovation',
    ],
    -0.075,
  );
  display('creativity', 1, 0.156, -0.12);
  standing(
    0,
    ['looking-photographs', 'weaving', 'buildings', 'photographer-eye', 'type', 'design-us'],
    0,
    0.004,
  );
  standing(5, ['taocp-1', 'taocp-2', 'taocp-3'], 0);
  display('color', 5, -0.025, -0.08);
  function loadFull(key: string, source: T.TextureLoader) {
    const current = inFlight.get(key);
    if (current) return current;
    const { url, paint } = prints.get(key)!;
    const reading = source
      .loadAsync(url)
      .then((texture) => {
        paint(texture);
        fullSize.add(key);
      })
      .finally(() => inFlight.delete(key));
    inFlight.set(key, reading);
    return reading;
  }

  const sortedKeys = [...prints.keys()].sort();
  void loader.loadAsync('/media/graphics/shelf-covers.webp').then(
    (atlas) => {
      const columns = Math.ceil(Math.sqrt(sortedKeys.length));
      const rows = Math.ceil(sortedKeys.length / columns);
      const width = atlas.image.width / columns;
      const height = atlas.image.height / rows;
      for (const [i, key] of sortedKeys.entries()) {
        if (!fullSize.has(key)) {
          prints.get(key)!.paint(atlas, {
            x: (i % columns) * width,
            y: Math.floor(i / columns) * height,
            width,
            height,
          });
        }
      }
      atlas.dispose();
    },
    () => {
      void Promise.allSettled(
        sortedKeys.filter((key) => !fullSize.has(key)).map((key) => loadFull(key, detailLoader)),
      );
    },
  );
  void Promise.allSettled([...faceOut].map((key) => loadFull(key, loader)));
  const eye = new T.Vector3(),
    front = new T.Vector3(),
    axis = new T.Vector3();
  for (const key of rowEnds) {
    const panel = inventory
      .get(key)!
      .object.children.find((child) => child.name.endsWith(' · front'))!;
    panel.onBeforeRender = (_renderer, _scene, camera) => {
      if (!(camera instanceof T.PerspectiveCamera)) return;
      eye.setFromMatrixPosition(camera.matrixWorld);
      axis.setFromMatrixColumn(panel.matrixWorld, 2);
      front.setFromMatrixPosition(panel.matrixWorld).addScaledVector(axis, 0.5);
      if (eye.sub(front).dot(axis) <= 0) return;
      panel.onBeforeRender = T.Object3D.prototype.onBeforeRender;
      if (!fullSize.has(key)) void loadFull(key, detailLoader).catch(() => {});
    };
  }
  books.forEach((unit, index) =>
    enableClosePrint(unit, editions[index], rearNeighbors.get(editions[index].key)),
  );
  function prepareBook(key: string) {
    const missing = (neighbors.get(key) ?? [key]).filter((book) => !fullSize.has(book));
    if (missing.length)
      return Promise.allSettled(missing.map((book) => loadFull(book, detailLoader))).then(() => {});
  }
  async function prepareBookExport(source: T.Object3D) {
    const included = new Set<T.Object3D>();
    source.traverse((child) => included.add(child));
    source.traverseAncestors((parent) => included.add(parent));
    await Promise.all(
      [...inventory]
        .filter(([key, { object }]) => included.has(object) && !fullSize.has(key))
        .map(([key]) => loadFull(key, detailLoader)),
    );
  }
  return { books, prepareBook, prepareBookExport };
}
