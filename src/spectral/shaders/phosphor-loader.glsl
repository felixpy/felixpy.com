precision highp float;

uniform vec2 u_resolution;
uniform float u_time;
uniform float u_motion;
uniform sampler2D u_backdrop;

float hash(vec2 p) {
  vec3 q = fract(p.xyx * 0.1031);
  q += dot(q, q.yzx + 33.33);
  return fract((q.x + q.y) * q.z);
}

float ink(vec2 uv) {
  return texture2D(u_backdrop, uv).r;
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  vec2 p = uv * vec2(1600.0, 900.0);
  float row = floor(p.y / 3.5);
  float burst = hash(vec2(row, floor(u_time * 5.0)));
  float shift = (hash(vec2(row, floor(u_time * 7.0) + 9.0)) - 0.5) * (0.004 + 0.039 * pow(burst, 3.0));
  float bar = hash(vec2(floor(p.y / 13.0), floor(u_time * 3.0)));
  vec2 offset = vec2(shift * (0.45 + 0.55 * u_motion), 0.0);
  float core = ink(uv + offset);
  float smear = max(ink(uv + offset * 2.0), ink(uv - offset * 1.45));
  float halo = (ink(uv + vec2(0.0, 0.004)) + ink(uv - vec2(0.0, 0.004))) * 0.12;
  float scan = 0.56 + 0.44 * step(1.05, mod(p.y, 3.0));
  float signal = max(core, smear * (0.19 + 0.24 * bar)) * scan + halo;

  vec2 tile = floor(p / vec2(52.0 + 65.0 * hash(vec2(row, 3.0)), 16.0));
  float staticValue = step(0.94, hash(tile + floor(u_time * 1.5))) * 0.022;
  vec2 wire = floor(p / vec2(27.0, 3.0));
  float interference = step(0.995, hash(wire + floor(u_time * 2.0))) * 0.14;
  float mask = 1.0 - smoothstep(0.18, 0.67, length((uv - 0.5) * vec2(0.8, 1.0)));
  vec3 phosphor = vec3(0.557, 0.831, 0.388);
  vec3 color = phosphor * (signal + (staticValue + interference) * mask);
  gl_FragColor = vec4(color, 1.0);
}
