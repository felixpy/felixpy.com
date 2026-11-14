import { createRoot } from 'react-dom/client';
import Shader from '../spectral/Shader';
import profileShader from '../spectral/shaders/profile.glsl?raw';

export function mountLightField(element: Element) {
  createRoot(element).render(<Shader fragment={profileShader} animate maxDpr={1} />);
}
