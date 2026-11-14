import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { renderAboutPages } from './scripts/build/about-pages';

export default defineConfig({
  plugins: [react(), tailwindcss(), renderAboutPages()],
  resolve: { tsconfigPaths: true },
  build: {
    rolldownOptions: { input: ['index.html', 'about.html'] },
  },
});
