import { ShaderChunk } from 'three';
import { desk, display, roomSize } from './layout';

export const deskProbe = { x: 0.37, y: 0.96, z: 0.21 };

const projection = `
vec3 reflectedRoomDirection(vec3 origin, vec3 ray, float roughness) {
  vec3 inverseRay = mix(vec3(-1.0), vec3(1.0), step(vec3(0.0), ray)) / max(abs(ray), vec3(0.0001));
  vec3 nearFace = vec3(${roomSize.west}, 0.0, ${roomSize.north});
  vec3 farFace = vec3(${roomSize.east}, ${roomSize.ceiling}, ${roomSize.south});
  vec3 distances = (mix(nearFace, farFace, step(vec3(0.0), ray)) - origin) * inverseRay;
  float t = min(distances.x, min(distances.y, distances.z));
  float table = (${desk.top} - origin.y) * inverseRay.y;
  vec2 onTable = origin.xz + table * ray.xz;
  if (ray.y < 0.0 && table > 0.006 && onTable.x > ${desk.left} && onTable.x < ${desk.right} &&
      onTable.y > ${desk.back} && onTable.y < ${desk.front}) t = min(t, table);
  float screenT = (${display.z + display.surface} - origin.z) * inverseRay.z;
  vec2 onScreen = abs(origin.xy + screenT * ray.xy - vec2(${display.x}, ${display.y}));
  if (ray.z < 0.0 && screenT > 0.006 && all(lessThan(onScreen, vec2(${display.outerWidth / 2}, ${display.outerHeight / 2}))))
    t = min(t, screenT);
  vec3 probe = vec3(${deskProbe.x}, ${deskProbe.y}, ${deskProbe.z});
  vec3 sampleDir = origin + max(t, 0.0) * ray - probe;
  float weight = (1.0 - smoothstep(0.50, 0.9, roughness)) *
    (1.0 - smoothstep(0.58, 1.48, origin.z)) * smoothstep(0.0, 0.02, t);
  return normalize(mix(ray, sampleDir / max(0.0001, length(sampleDir)), weight));
}
`;

export function projectRoomReflections(shader: { fragmentShader: string }) {
  const chunk = ShaderChunk.envmap_physical_pars_fragment;
  shader.fragmentShader = shader.fragmentShader.replace(
    '#include <envmap_physical_pars_fragment>',
    projection +
      chunk.replace(
        'envMapRotation * reflectVec,',
        'envMapRotation * reflectedRoomDirection(studioPosition, reflectVec, roughness),',
      ),
  );
}
