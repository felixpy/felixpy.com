import type { Environment } from './environment';
import { releaseSpectralSurface } from '../spectral/spectral-surface';

export type GraphicsTier = 'ultra' | 'high' | 'balanced';

export function graphicsDevice(): {
  available: boolean;
  quality: Environment['quality'];
  tier: GraphicsTier;
  initialLowScale: number;
} {
  try {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('webgl2', {
      powerPreference: 'high-performance',
      alpha: false,
      antialias: false,
    });
    if (!context) return { available: false, quality: 'low', tier: 'balanced', initialLowScale: 1 };
    const info = context.getExtension('WEBGL_debug_renderer_info');
    const renderer = info ? String(context.getParameter(info.UNMASKED_RENDERER_WEBGL)) : '';
    const software = /swiftshader|llvmpipe|microsoft basic render/i.test(renderer);
    const appleSilicon = /\bapple\s*(?:gpu|m\d)/i.test(renderer);
    const discrete = /\b(?:rtx|gtx|radeon rx|arc\s*a\d)/i.test(renderer);
    const integrated =
      /\b(?:uhd|hd) graphics|iris(?:\(r\))? (?:xe|plus)|adreno[^\d]*[345]\d\d|mali-[gt][345]\d|radeon\(tm\)\s*graphics/i.test(
        renderer,
      );
    const limited = context.getParameter(context.MAX_TEXTURE_SIZE) < 8192;
    releaseSpectralSurface(canvas, context);
    const low = software || integrated || limited;
    const tier: GraphicsTier = low ? 'balanced' : discrete && !appleSilicon ? 'ultra' : 'high';
    return {
      available: true,
      quality: low ? 'low' : 'high',
      tier,
      initialLowScale: software ? 0.5 : 1,
    };
  } catch {
    return { available: false, quality: 'low', tier: 'balanced', initialLowScale: 1 };
  }
}
