import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';
import { renderAboutPages } from './scripts/build/about-pages';
import { studioParts } from './scripts/build/studio-parts';

function preloadStudioView(): Plugin {
  return {
    name: 'preload-studio-view',
    transformIndexHtml: {
      order: 'post',
      handler(_, context) {
        if (context.path !== '/index.html' || !context.bundle) return;
        const chunk = Object.values(context.bundle).find(
          (entry) =>
            entry.type === 'chunk' && entry.facadeModuleId?.endsWith('/scene/StudioView.tsx'),
        );
        if (!chunk) return;
        return [
          {
            tag: 'link',
            attrs: {
              rel: 'modulepreload',
              crossorigin: '',
              href: '/' + chunk.fileName,
              media: '(min-width: 701px) and (min-height: 421px)',
            },
            injectTo: 'head-prepend',
          },
        ];
      },
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), renderAboutPages(), studioParts(), preloadStudioView()],
  server: { watch: { ignored: ['**/.review/**', '**/.references/**', '**/.worktrees/**'] } },
  resolve: { tsconfigPaths: true },
  build: {
    rolldownOptions: { input: ['index.html', 'about.html'] },
  },
});
