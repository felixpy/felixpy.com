precision highp float;
/** @resolution */
uniform vec2 u_resolution;
/** @time */
uniform float u_time;

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  vec2 p = (gl_FragCoord.xy - u_resolution * vec2(0.275, 0.51)) / u_resolution.y;
  float r = length(p);
  float halo = exp(-r * r * 6.8);
  float edge = (r - 0.29) * 18.0;
  float rim = exp(-edge * edge);
  vec3 color = vec3(0.024, 0.043, 0.059);
  color += vec3(0.019, 0.050, 0.072) * halo;
  color += mix(vec3(0.035, 0.07, 0.08), vec3(0.08, 0.055, 0.025), smoothstep(-0.3, 0.3, p.x)) * rim * 0.48;
  float grain = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
  color += (grain - 0.5) * 0.012;
  gl_FragColor = vec4(color, 1.0);
}
