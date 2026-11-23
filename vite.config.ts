import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv, type HtmlTagDescriptor, type Plugin } from 'vite';
import { renderAboutPages } from './scripts/build/about-pages';
import { studioParts } from './scripts/build/studio-parts';
import { assetUrl } from './src/app/asset-url';
import { isMobileDevice } from './src/app/mobile-device';
import { shareImage, siteOrigin } from './src/content/about';
import { partLibraryPath } from './src/scene/blender-parts';

function preloadStudioView(assetBase: string): Plugin {
  return {
    name: 'preload-studio-view',
    transformIndexHtml: {
      order: 'post',
      handler(_, context) {
        if (context.path !== '/index.html') return;
        const tags: HtmlTagDescriptor[] = [
          {
            tag: 'link',
            attrs: {
              rel: 'preload',
              as: 'fetch',
              crossorigin: '',
              href: assetUrl(partLibraryPath('studio'), assetBase),
            },
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
            },
          });
        return [
          {
            tag: 'template',
            attrs: { id: 'studio-preloads' },
            children: tags,
            injectTo: 'head-prepend',
          },
          {
            tag: 'script',
            children: `if (!(${isMobileDevice.toString()})(navigator)) {
  document.currentScript.before(document.getElementById('studio-preloads').content);
}`,
            injectTo: 'head-prepend',
          },
        ];
      },
    },
  };
}

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
      studioParts(),
      preloadStudioView(assetBase),
      Boolean(assetBase) && {
        name: 'studio-share-image',
        transformIndexHtml(html, { path }) {
          if (path === '/index.html') {
            return html.replace(siteOrigin + shareImage, assetUrl(shareImage, assetBase));
          }
        },
      },
    ],
    server: { watch: { ignored: ['**/.review/**', '**/.references/**', '**/.worktrees/**'] } },
    resolve: { tsconfigPaths: true },
    build: {
      copyPublicDir: false,
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
