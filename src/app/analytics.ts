import { inject } from '@vercel/analytics';

if (window.location.hostname === 'felixpy.com') {
  inject();

  const google = window as Window & { dataLayer?: unknown[] };
  const dataLayer = (google.dataLayer ??= []);
  function gtag(..._command: unknown[]) {
    dataLayer.push(arguments);
  }
  gtag('js', new Date());

  const container = document.createElement('script');
  container.async = true;
  container.src = 'https://www.googletagmanager.com/gtm.js?id=GTM-KFP4MGQN';
  document.head.append(container);
}
