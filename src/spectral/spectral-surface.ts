type Surface = {
  canvas: HTMLCanvasElement;
  gl: WebGLRenderingContext;
};

let spare: Surface | undefined;

export function acquireSpectralSurface(): Surface | undefined {
  const surface = spare;
  spare = undefined;
  if (surface && !surface.gl.isContextLost()) return surface;
  const canvas = document.createElement('canvas');
  const gl = canvas.getContext('webgl', { alpha: false, antialias: false });
  return gl ? { canvas, gl } : undefined;
}

export function releaseSpectralSurface(canvas: HTMLCanvasElement, gl: WebGLRenderingContext) {
  canvas.remove();
  if (gl.isContextLost()) return;
  if (spare && !spare.gl.isContextLost()) {
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return;
  }
  canvas.width = 1;
  canvas.height = 1;
  spare = { canvas, gl };
}
