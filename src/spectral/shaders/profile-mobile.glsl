precision highp float;

/** @resolution */
uniform vec2 u_resolution;
/** @time */
uniform float u_time;
/** @label Motion @default 1 @range 0, 1 */
uniform float u_motion;

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  // Recompose the desktop filaments for a portrait viewport, without a mouse.
  vec2 p = vec2((uv.x - 0.86) * 1.35, (uv.y - 0.57) * 1.5);
  float time = u_time * 0.14 * u_motion;
  vec3 base = vec3(0.024, 0.043, 0.059);
  vec3 light = vec3(0.0);

  for (int i = 0; i < 42; i++) {
    float f = float(i) / 41.0;
    float y = (f - 0.5) * 0.34 + 0.15 * sin(p.x * 4.1 + f * 3.4 + time);
    y += 0.04 * cos(p.x * 9.0 - f * 4.0 - time);
    float distanceToLine = abs(p.y - y);
    float filament = exp(-distanceToLine * 480.0) + exp(-distanceToLine * 100.0) * 0.055;
    vec3 color = mix(vec3(0.30, 0.67, 0.86), vec3(0.97, 0.74, 0.49), smoothstep(0.40, 0.82, f));
    float reflection = 0.20 + 0.60 * pow(abs(cos(p.x * 4.0 + f * 2.0 + time)), 6.0);
    light += filament * color * reflection;
  }

  // Keep the introduction readable and the career timeline visually quiet.
  float mask = smoothstep(0.24, 0.90, uv.x);
  mask *= smoothstep(0.30, 0.45, uv.y) * (1.0 - smoothstep(0.76, 0.88, uv.y));
  float copyBand = smoothstep(0.54, 0.60, uv.y) * (1.0 - smoothstep(0.72, 0.78, uv.y));
  mask *= 1.0 - copyBand * 0.62;
  gl_FragColor = vec4(base + light * mask * 0.88, 1.0);
}
