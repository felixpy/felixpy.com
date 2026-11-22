import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type HtmlTagDescriptor, type Plugin } from 'vite';
import { renderAboutPages } from './scripts/build/about-pages';
import { studioParts } from './scripts/build/studio-parts';
import { partLibraryPath } from './src/scene/blender-parts';

function preloadStudioView(): Plugin {
  return {
    name: 'preload-studio-view',
    transformIndexHtml: {
      order: 'post',
      handler(_, context) {
        if (context.path !== '/index.html') return;
        const media = '(min-width: 701px) and (min-height: 421px)';
        const tags: HtmlTagDescriptor[] = [
          {
            tag: 'link',
            attrs: {
              rel: 'preload',
              as: 'fetch',
              crossorigin: '',
              href: partLibraryPath('studio'),
              media,
            },
            injectTo: 'head-prepend',
          },
        ];
        const chunk = Object.values(context.bundle ?? {}).find(
          (entry) =>
            entry.type === 'chunk' && entry.facadeModuleId?.endsWith('/scene/StudioView.tsx'),
        );
        if (chunk)
          tags.push({
            tag: 'link',
            attrs: {
              rel: 'modulepreload',
              crossorigin: '',
              href: '/' + chunk.fileName,
              media,
            },
            injectTo: 'head-prepend',
          });
        return tags;
      },
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), renderAboutPages(), studioParts(), preloadStudioView()],
  server: { watch: { ignored: ['**/.review/**', '**/.references/**', '**/.worktrees/**'] } },
  resolve: { tsconfigPaths: true },
  build: {
    copyPublicDir: false,
    rolldownOptions: { input: ['index.html', 'about.html'] },
  },
});
