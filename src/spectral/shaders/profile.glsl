precision highp float;
/** @resolution */
uniform vec2 u_resolution;
/** @time */
uniform float u_time;
/** @mouse */
uniform vec2 u_mouse;

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  vec2 pointer = clamp(u_mouse / u_resolution - 0.5, -0.5, 0.5);
  vec2 p = (gl_FragCoord.xy - u_resolution * vec2(0.77, 0.53)) / u_resolution.y;
  p += pointer * 0.015;
  float t = u_time * 0.18;
  vec3 base = vec3(0.024, 0.043, 0.059);
  vec3 col = base;
  for (int i = 0; i < 54; i++) {
    float f = float(i) / 53.0;
    float y = (f - 0.5) * 0.47 + 0.16 * sin(p.x * 4.1 + f * 3.4 + t);
    y += 0.045 * cos(p.x * 9.0 - f * 4.0 - t);
    float d = abs(p.y - y);
    float stripe = exp(-d * 460.0) + exp(-d * 90.0) * 0.065;
    vec3 color = mix(vec3(0.30, 0.67, 0.86), vec3(0.97, 0.74, 0.49), smoothstep(0.4, 0.82, f));
    float specular = 0.24 + 0.7 * pow(abs(cos(p.x * 4.0 + f * 2.0 + t)), 6.0);
    col += stripe * color * specular;
  }
  float mask = smoothstep(0.35, 0.72, uv.x) * (1.0 - smoothstep(0.90, 1.0, uv.x));
  mask *= smoothstep(0.0, 0.27, uv.y) * (1.0 - smoothstep(0.87, 1.0, uv.y));
  col = mix(base, col, mask);
  float grain = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
  col += (grain - 0.5) * 0.015;
  gl_FragColor = vec4(col, 1.0);
}
