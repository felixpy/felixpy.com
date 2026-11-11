import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 70_000,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    channel: 'chrome',
    launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] },
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
  },
});
