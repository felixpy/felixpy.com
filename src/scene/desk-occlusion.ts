import { desk } from './layout';

export const deskOcclusionGLSL = `
float deskVisibility(vec3 receiver, vec3 emitter) {
  const float surface = ${desk.top};
  if (receiver.y >= surface - 0.001 || emitter.y <= surface) return 1.;
  vec2 crossing = mix(receiver.xz, emitter.xz, (surface-receiver.y)/(emitter.y-receiver.y));
  vec2 clearance = min(crossing-vec2(${desk.left},${desk.back}), vec2(${desk.right},${desk.front})-crossing);
  float edge = min(clearance.x,clearance.y);
  return 1.-smoothstep(-0.005,0.005,edge);
}
`;
