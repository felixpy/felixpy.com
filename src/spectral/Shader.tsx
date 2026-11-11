import { useEffect, useRef } from 'react';

const vertexSource = `attribute vec2 position;
  void main() { gl_Position = vec4(position, 0.0, 1.0); }`;

function compile(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
  gl.deleteShader(shader);
  return null;
}

export default function Shader({
  fragment,
  animate = false,
  progress = 0,
  maxDpr = 1.5,
  paintBackdrop,
}: {
  fragment: string;
  animate?: boolean;
  progress?: number;
  maxDpr?: number;
  paintBackdrop?: (context: CanvasRenderingContext2D, viewport: HTMLCanvasElement) => void;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const update = useRef<(() => void) | null>(null);
  const settings = useRef({ animate, progress });
  settings.current = { animate, progress };
  useEffect(() => {
    const canvas = ref.current!;
    const gl = canvas.getContext('webgl', { alpha: false, antialias: false });
    if (!gl) return;
    const vertex = compile(gl, gl.VERTEX_SHADER, vertexSource);
    const pixel = compile(gl, gl.FRAGMENT_SHADER, fragment);
    const program = gl.createProgram();
    if (program && vertex && pixel) {
      gl.attachShader(program, vertex);
      gl.attachShader(program, pixel);
      gl.linkProgram(program);
    }
    gl.deleteShader(vertex);
    gl.deleteShader(pixel);
    if (!program || !gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program);
      return;
    }
    const buffer = gl.createBuffer();
    gl.useProgram(program);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const resolution = gl.getUniformLocation(program, 'u_resolution');
    const mouse = gl.getUniformLocation(program, 'u_mouse');
    const time = gl.getUniformLocation(program, 'u_time');
    const motion = gl.getUniformLocation(program, 'u_motion');
    const progress = gl.getUniformLocation(program, 'u_progress');
    const backdrop = paintBackdrop ? document.createElement('canvas').getContext('2d') : null;
    const texture = backdrop ? gl.createTexture() : null;
    if (texture) {
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.uniform1i(gl.getUniformLocation(program, 'u_backdrop'), 0);
    }
    const pointer = { x: 0.5, y: 0.5 };
    let frame = 0,
      elapsed = 0,
      previous = 0;

    function render(now: number) {
      frame = 0;
      const width = canvas.width,
        height = canvas.height;
      if (settings.current.animate && previous) elapsed += Math.min(0.05, (now - previous) / 1000);
      previous = settings.current.animate ? now : 0;
      gl!.uniform2f(resolution, width, height);
      gl!.uniform2f(mouse, pointer.x * width, pointer.y * height);
      gl!.uniform1f(time, elapsed);
      gl!.uniform1f(motion, Number(settings.current.animate));
      gl!.uniform1f(progress, settings.current.progress);
      gl!.drawArrays(gl!.TRIANGLES, 0, 3);
      if (texture && !canvas.dataset.ready) canvas.dataset.ready = 'true';
      if (settings.current.animate && !document.hidden) frame = requestAnimationFrame(render);
    }
    function wake() {
      if (!frame && !document.hidden) frame = requestAnimationFrame(render);
    }
    function refreshBackdrop() {
      if (!backdrop || !texture || !paintBackdrop) return;
      backdrop.canvas.width = canvas.width;
      backdrop.canvas.height = canvas.height;
      paintBackdrop(backdrop, canvas);
      gl!.texImage2D(gl!.TEXTURE_2D, 0, gl!.RGBA, gl!.RGBA, gl!.UNSIGNED_BYTE, backdrop.canvas);
      wake();
    }
    function resize() {
      const ratio = Math.min(maxDpr, devicePixelRatio);
      canvas.width = Math.max(1, Math.round(canvas.clientWidth * ratio));
      canvas.height = Math.max(1, Math.round(canvas.clientHeight * ratio));
      gl!.viewport(0, 0, canvas.width, canvas.height);
      refreshBackdrop();
      wake();
    }
    function move(event: PointerEvent) {
      if (!settings.current.animate) return;
      const bounds = canvas.getBoundingClientRect();
      pointer.x = (event.clientX - bounds.left) / Math.max(1, bounds.width);
      pointer.y = 1 - (event.clientY - bounds.top) / Math.max(1, bounds.height);
    }
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    if (mouse) window.addEventListener('pointermove', move, { passive: true });
    document.addEventListener('visibilitychange', wake);
    update.current = wake;
    resize();
    let disposed = false;
    if (texture)
      void document.fonts.ready.then(() => {
        if (!disposed) refreshBackdrop();
      });
    return () => {
      disposed = true;
      observer.disconnect();
      window.removeEventListener('pointermove', move);
      document.removeEventListener('visibilitychange', wake);
      cancelAnimationFrame(frame);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteTexture(texture);
      delete canvas.dataset.ready;
      update.current = null;
    };
  }, [fragment, maxDpr, paintBackdrop]);
  useEffect(() => {
    update.current?.();
  }, [animate, progress]);
  return <canvas className="spectral-shader" ref={ref} aria-hidden="true" />;
}
