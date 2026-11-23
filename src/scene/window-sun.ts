import { windowOpening } from './layout';

const { wall, z0, z1, y0, y1 } = windowOpening;

export const windowSunGLSL = `
  float sunThroughWindowOpening(vec3 p, vec3 beam) {
    float depth = p.x - (${wall - 0.154});
    if (depth <= 0.0 || beam.x < 0.01) return 1.0;
    vec3 hit = p - beam * (depth / beam.x);
    float edge = min(min(hit.z - (${z0 + 0.037}), ${z1 - 0.037} - hit.z),
                     min(hit.y - ${y0 + 0.038}, ${y1 - 0.035} - hit.y));
    float penumbra = 0.003 + depth * 0.0047;
    float frame = min(abs(hit.z - ${z0 + 0.037 + (z1 - z0 - 0.074) * 0.62}) - 0.018,
                      abs(hit.y - ${y1 - 0.235}) - 0.013);
    return smoothstep(-penumbra, penumbra, min(edge, frame));
  }
  float transmittedSun(vec3 p, vec3 beam, vec2 slats) {
    float depth = p.x - (${wall - 0.154});
    if (depth <= 0.0 || beam.x < 0.01) return 1.0;
    float opening = sunThroughWindowOpening(p, beam);
    float penumbra = 0.003 + depth * 0.0047;
    float blindDepth = p.x - (${wall - 0.026});
    float belowRail = ${y1 - 0.083} - (p.y - beam.y * blindDepth / beam.x);
    float pitch = max(slats.x, 0.0038);
    float blade = clamp(floor(belowRail / pitch + 0.5), 1.0, 33.0) * pitch;
    float halfBlade = 0.001 + 0.026 * abs(sin(slats.y) - beam.y / beam.x * cos(slats.y));
    return opening * smoothstep(halfBlade - penumbra, halfBlade + penumbra, abs(belowRail - blade));
  }
`;
