const productionBase = import.meta.env?.PROD ? import.meta.env.VITE_ASSET_BASE_URL : undefined;
const hostedAssetPath = /^\/?(?:(?:media|fonts)\/.+|assets\/.+\.woff2?)$/;

export function isHostedAssetPath(path: string) {
  return hostedAssetPath.test(path);
}

export function assetUrl(path: string, base: string | undefined = productionBase) {
  const origin = base?.trim().replace(/\/+$/, '');
  return origin && isHostedAssetPath(path) ? origin + '/' + path.replace(/^\//, '') : path;
}
