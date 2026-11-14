import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { Connect, HtmlTagDescriptor, Plugin } from 'vite';
import AboutPage from '../../src/about/AboutPage';
import { aboutPage as page, shareImage, siteOrigin } from '../../src/content/about';
import { profile, publicProfiles } from '../../src/content/profile';

function serveCleanAboutUrls(req: Connect.IncomingMessage, _: unknown, next: Connect.NextFunction) {
  const [pathname, query] = (req.url ?? '').split('?');
  if (pathname === page.path) {
    req.url = `${pathname}.html${query ? `?${query}` : ''}`;
  }
  next();
}

export function renderAboutPages(): Plugin {
  return {
    name: 'render-about-pages',
    configureServer(server) {
      server.middlewares.use(serveCleanAboutUrls);
    },
    configurePreviewServer(server) {
      server.middlewares.use(serveCleanAboutUrls);
    },
    transformIndexHtml(html, { path }) {
      if (path !== `${page.path}.html`) return;

      const canonical = siteOrigin + page.path;
      const image = siteOrigin + shareImage;
      const person = {
        '@context': 'https://schema.org',
        '@type': 'ProfilePage',
        url: canonical,
        inLanguage: 'en',
        mainEntity: {
          '@type': 'Person',
          '@id': `${siteOrigin}/about#felix-yang`,
          name: profile.name,
          alternateName: ['felixpy', 'gofelixpy'],
          description: page.description,
          url: `${siteOrigin}/about`,
          sameAs: [publicProfiles.githubProfile, publicProfiles.x],
        },
      };
      const tags: HtmlTagDescriptor[] = [
        { tag: 'title', children: page.title },
        { tag: 'meta', attrs: { name: 'description', content: page.description } },
        { tag: 'meta', attrs: { name: 'theme-color', content: '#060b0f' } },
        { tag: 'link', attrs: { rel: 'canonical', href: canonical } },
        ...Object.entries({
          'og:type': 'profile',
          'og:site_name': 'Felix Studio',
          'og:title': page.title,
          'og:description': page.description,
          'og:url': canonical,
          'og:locale': 'en_US',
          'og:image': image,
          'og:image:alt': page.imageAlt,
        }).map(([property, content]) => ({ tag: 'meta', attrs: { property, content } })),
        { tag: 'meta', attrs: { name: 'twitter:card', content: 'summary_large_image' } },
        { tag: 'meta', attrs: { name: 'twitter:creator', content: '@gofelixpy' } },
        {
          tag: 'script',
          attrs: { type: 'application/ld+json' },
          children: JSON.stringify(person).replace(/</g, '\\u003c'),
        },
      ];

      return {
        html: html.replace('<!-- about content -->', () =>
          renderToStaticMarkup(createElement(AboutPage)),
        ),
        tags: tags.map((tag) => ({ ...tag, injectTo: 'head' })),
      };
    },
  };
}
