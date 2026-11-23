import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
import { renderAboutPages } from './scripts/build/about-pages';
import { assetUrl } from './src/app/asset-url';
import { shareImage, siteOrigin } from './src/content/about';

export default defineConfig(({ command, mode }) => {
  const assetBase =
    command === 'build'
      ? (loadEnv(mode, process.cwd(), 'VITE_').VITE_ASSET_BASE_URL?.trim() ?? '')
      : '';

  return {
    plugins: [
      react(),
      tailwindcss(),
      renderAboutPages(assetBase),
      Boolean(assetBase) && {
        name: 'studio-share-image',
        transformIndexHtml(html, { path }) {
          if (path === '/index.html') {
            return html.replace(siteOrigin + shareImage, assetUrl(shareImage, assetBase));
          }
        },
      },
    ],
    resolve: { tsconfigPaths: true },
    build: {
      rolldownOptions: { input: ['index.html', 'about.html'] },
    },
    experimental: assetBase
      ? {
          renderBuiltUrl(filename) {
            const path = '/' + filename;
            const url = assetUrl(path, assetBase);
            if (url !== path) return url;
          },
        }
      : undefined,
  };
});
