import { expect, test } from '@playwright/test';

test('deferring shelf back text preserves the spine and restores the exact wrapper pixels', async ({
  page,
}) => {
  await page.goto('/robots.txt');
  const result = await page.evaluate(async () => {
    const tree = '/node_modules/three/build/three.module.js';
    const books = '/src/content/books.ts';
    const binding = '/src/scene/book-binding.ts';
    const library = '/src/scene/blender-library.ts';
    const { Group } = (await import(tree)) as typeof import('three');
    const { editions } = (await import(books)) as typeof import('../src/content/books');
    const { bindEdition, pageStocks } = (await import(
      binding
    )) as typeof import('../src/scene/book-binding');
    const { loadParts } = (await import(library)) as typeof import('../src/scene/blender-library');
    await loadParts('studio');
    const book = editions.find(({ key }) => key === 'taocp-2')!;
    const load = () => {};
    const stock = pageStocks();

    function wrapper(defer: boolean) {
      const model = new Group();
      const complete = bindEdition(model, book, { load }, stock, defer);
      const mesh = model.children.find(({ name }) => name.endsWith(' · wrapper'));
      if (!mesh || !('isMesh' in mesh)) throw new Error('Missing book wrapper');
      const { material } = mesh as import('three').Mesh<
        import('three').BufferGeometry,
        import('three').MeshStandardMaterial
      >;
      return {
        complete,
        get canvas() {
          return material.map!.image as HTMLCanvasElement;
        },
      };
    }

    function pixels(canvas: HTMLCanvasElement, x: number, width: number) {
      return canvas.getContext('2d')!.getImageData(x, 0, width, canvas.height).data;
    }

    function matches(left: Uint8ClampedArray, right: Uint8ClampedArray) {
      return left.every((value, index) => value === right[index]);
    }

    const eager = wrapper(false);
    const deferred = wrapper(true);
    const completed = wrapper(true);
    completed.complete?.();
    const sameSpine = matches(pixels(eager.canvas, 288, 96), pixels(deferred.canvas, 288, 96));
    const sameBack = matches(pixels(eager.canvas, 0, 288), pixels(deferred.canvas, 0, 288));
    const sameComplete = matches(pixels(eager.canvas, 0, 384), pixels(completed.canvas, 0, 384));
    return { sameSpine, sameBack, sameComplete };
  });
  expect(result).toEqual({ sameSpine: true, sameBack: false, sameComplete: true });
});
