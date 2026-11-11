# Repository guide

- Use Node.js 24 or later and `npm ci`. Run `npm run build` and the relevant Playwright tests before handing off changes.
- Put biography and travel copy in `src/content/`, browser behavior and preferences in `src/app/`, computer apps in `src/desktop/apps/`, and Three.js scene work in `src/scene/`.
- Use PascalCase for React component files, `useName` for React hooks, and lowercase kebab-case for multiword utility, shader, and media filenames. Keep scene measurements in meters and use the existing placement and camera helpers.
- Keep `README.md` and `README.zh-CN.md` in sync. Update corresponding sections, instructions, badges, links, and screenshots in the same change. Reuse the same image files and translate the alt text. Write other repository documentation in English.
- Pair English and Simplified Chinese site copy. English is the initial locale. Rebuild the subset fonts when new text requires additional glyphs.
- Keep settings compatible with the existing `felix-studio-v1` storage entry. Preserve the static-site build and the compact layout when changing desktop-only behavior.
- Group production media by purpose under `public/media/`. Record third-party sources and terms in [Media](docs/media.md) and update `public/media/credits.txt` as needed. Use `uv` for Python asset scripts and keep Python dependencies out of the global environment.
- Keep local screenshots, recordings, authoring exports, and review material under the ignored `.review/` directory. Keep tests and maintained documentation in their own tracked directories.
- `npm ci` installs the Husky hooks. Use `npm run hooks:install` to reinstall them. Oxfmt checks staged files before committing. Use Conventional Commit subjects for commits and pull request titles.
