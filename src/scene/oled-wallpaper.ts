export const oledWallpaper = `
float oledTextCoverage(sampler2D atlas, vec2 uv) {
  vec2 pixel = vec2(uv.x, 1.0 - uv.y) * vec2(512.0, 288.0);
  vec2 size = vec2(240.0, 128.0);
  vec2 dx = dFdx(pixel) / size, dy = dFdy(pixel) / size;
  if (pixel.y >= 60.0 && pixel.y < 159.0) pixel.y -= 60.0;
  else if (pixel.y >= 218.0 && pixel.y < 246.0) pixel.y -= 118.0;
  else return 0.0;
  return textureGrad(atlas, (pixel - vec2(136.0, 0.0)) / size, dx, dy).r;
}
const vec3 oledInk = vec3(0.66539, 0.78354, 0.73791);
vec3 oledColour(vec2 uv, float time) {
float t = time * 0.49;
float wave = sin(uv.x * 7.1 + t) * 0.114 + sin(uv.x * 11.7 - t * 0.6) * 0.045;
float edge = 0.39 + wave + 0.18 * uv.x;
float curtain = 1.0 - smoothstep(edge - 0.24, edge + 0.09, uv.y);
float crest = exp(-pow(abs(uv.y - edge) * 12.0, 2.0));
vec3 ink = mix(vec3(0.026, 0.098, 0.17), vec3(0.09, 0.28, 0.27), smoothstep(0.07, 0.64, uv.x));
vec3 light = mix(ink, vec3(0.38, 0.27, 0.15), smoothstep(0.58, 0.87, uv.x) * (1.0 - smoothstep(0.92, 1.0, uv.x)));
return vec3(0.012, 0.026, 0.043) + light * (curtain * 0.91 + crest * 0.23);
}
`;
