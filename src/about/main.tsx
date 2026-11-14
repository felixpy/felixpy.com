import '@fontsource/space-grotesk/latin-400.css';
import '@fontsource/space-grotesk/latin-500.css';
import '@fontsource/space-grotesk/latin-600.css';
import '../app/analytics';
import { formatWorkYears } from '../content/about';
import { getWorkYears } from '../content/profile';
import './about.css';

const tenure = document.getElementById('about-years');
if (tenure) {
  tenure.textContent = formatWorkYears(getWorkYears());
}

const light = document.querySelector('.about-light');
if (light && !window.matchMedia('(prefers-reduced-motion: reduce), (max-width: 640px)').matches) {
  void import('./light-field').then(({ mountLightField }) => mountLightField(light));
}
