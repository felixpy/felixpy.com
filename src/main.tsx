import { createRoot } from 'react-dom/client';
import '@fontsource/ibm-plex-sans/latin-400.css';
import '@fontsource/ibm-plex-sans/latin-500.css';
import '@fontsource/ibm-plex-sans/latin-600.css';
import '@fontsource/ibm-plex-sans/latin-700.css';
import '@fontsource/press-start-2p/latin-400.css';
import '@fontsource/space-grotesk/latin-400.css';
import '@fontsource/space-grotesk/latin-500.css';
import '@fontsource/space-grotesk/latin-600.css';
import '@fontsource/caveat/latin-500.css';
import { Analytics } from '@vercel/analytics/react';
import App from './app/App';
import { printGreeting, travelPrints } from './content/travel';

const root = createRoot(document.getElementById('root')!);
const handwriting = printGreeting.zh + travelPrints.map((photo) => photo.note.zh).join('');
const fonts = [
  document.fonts.load('600 20px "IBM Plex Sans"'),
  document.fonts.load('600 20px "Studio Han"', '工作室档案'),
  document.fonts.load('500 32px Caveat'),
  document.fonts.load('400 32px "Studio Script"', handwriting),
];
const fontsReady = Promise.race([
  Promise.allSettled(fonts),
  new Promise((resolve) => window.setTimeout(resolve, 1250)),
]);
root.render(
  <>
    <App fontsReady={fontsReady} />
    {window.location.hostname === 'felixpy.com' && <Analytics />}
  </>,
);
