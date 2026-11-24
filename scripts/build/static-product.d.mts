export type ProductSource = {
  doc: {
    scene?: number;
    scenes?: Array<{ nodes?: number[] }>;
    nodes?: Array<Record<string, unknown>>;
    [key: string]: unknown;
  };
  data: Buffer;
};

export function readProduct(bytes: Buffer): ProductSource;
export function assembleProducts(
  sources: ProductSource[],
  roots: Array<[ProductSource, number]>,
): Buffer;
