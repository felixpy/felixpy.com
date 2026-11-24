const productionBase = import.meta.env?.PROD ? import.meta.env.VITE_ASSET_BASE_URL : undefined;
const hostedAssetPath = /^\/?(?:(?:media|fonts)\/.+|assets\/.+\.woff2?)$/;
const hashedAssetPattern = /\.[a-f0-9]{10}\.[a-z0-9.]+$/i;
const viteAssetPattern = /^\/?assets\/.+\.[a-z0-9]+$/i;

// Replaced at Vite production build time with the generated content-hash manifest.
const defaultManifest: Record<string, string> = {};

export function isHostedAssetPath(path: string) {
  return hostedAssetPath.test(path);
}

export function isImmutableAssetPath(path: string) {
  const clean = path.split('?')[0].replace(/^\//, '');
  return (
    viteAssetPattern.test(clean) || (isHostedAssetPath(clean) && hashedAssetPattern.test(clean))
  );
}

export function insertContentHash(path: string, hash: string) {
  const compound = path.match(/(\.(?:glb|mesh|pmrem)\.gz)$/i);
  const extIndex = compound ? path.length - compound[1].length : path.lastIndexOf('.');
  if (extIndex <= 0) return `${path}.${hash}`;
  return `${path.slice(0, extIndex)}.${hash}${path.slice(extIndex)}`;
}

export function resolveMediaPath(path: string, manifest: Record<string, string> = defaultManifest) {
  const leadingSlash = path.startsWith('/');
  const normalized = leadingSlash ? path : '/' + path;
  const mapped = manifest[normalized];
  if (!mapped) return path;
  return leadingSlash ? mapped : mapped.slice(1);
}

export function assetUrl(
  path: string,
  base: string | undefined = productionBase,
  manifest: Record<string, string> = defaultManifest,
) {
  const resolved = resolveMediaPath(path, manifest);
  const origin = base?.trim().replace(/\/+$/, '');
  return origin && isHostedAssetPath(resolved)
    ? origin + '/' + resolved.replace(/^\//, '')
    : resolved;
}
