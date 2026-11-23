import type { Environment } from './environment';
import { releaseSpectralSurface } from '../spectral/spectral-surface';

export function graphicsDevice(): {
  available: boolean;
  quality: Environment['quality'];
  initialLowScale: number;
} {
  try {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('webgl2', {
      powerPreference: 'high-performance',
      alpha: false,
      antialias: false,
    });
    if (!context) return { available: false, quality: 'low', initialLowScale: 1 };
    const info = context.getExtension('WEBGL_debug_renderer_info');
    const renderer = info ? String(context.getParameter(info.UNMASKED_RENDERER_WEBGL)) : '';
    const software = /swiftshader|llvmpipe|microsoft basic render/i.test(renderer);
    const integrated =
      /\b(?:uhd|hd) graphics|iris(?:\(r\))? (?:xe|plus)|adreno[^\d]*[345]\d\d|mali-[gt][345]\d/i.test(
        renderer,
      );
    const limited = context.getParameter(context.MAX_TEXTURE_SIZE) < 8192;
    releaseSpectralSurface(canvas, context);
    return {
      available: true,
      quality: software || integrated || limited ? 'low' : 'high',
      initialLowScale: software ? 0.5 : 1,
    };
  } catch {
    return { available: false, quality: 'low', initialLowScale: 1 };
  }
}
