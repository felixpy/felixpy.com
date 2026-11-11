# Contributing to Felix Studio

[Code of conduct](CODE_OF_CONDUCT.md)

## Report a bug or suggest a change

Search [existing issues](https://github.com/felixpy/felixpy.com/issues) first. Use the [issue forms](https://github.com/felixpy/felixpy.com/issues/new/choose) for a new report or proposal. English and Simplified Chinese are both welcome.

For bugs, include the page or view, steps to reproduce, expected and actual behavior, and your browser and operating system. For rendering or layout problems, include a screenshot and the viewport size if known. For larger changes to the studio or its controls, describe the proposed behavior in an issue before opening a pull request.

## Set up your checkout

Use Node.js 24 or later. From the repository root, run the following commands.

```sh
npm ci
npm run dev
```

`npm ci` installs the repository’s Husky hooks. Run `npm run hooks:install` to reinstall them. Before a commit, lint-staged runs Oxfmt on the staged files and reports files that need formatting. Run `npm run format -- <path>` to format a file and stage it again. To check the whole repository, use `npm run format:check`.

The `commit-msg` hook checks [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) subjects. Use the same format for pull request titles, such as `fix(scene): align the window projection`.

## Make and verify changes

- Follow the [Oxfmt settings](.oxfmtrc.json) and [.editorconfig](.editorconfig). See [AGENTS.md](AGENTS.md) for file naming, code placement, and scene conventions.
- Update English and Simplified Chinese site copy together. Keep the README in both languages and write other repository documentation in English.
- Record the source and usage terms for new third-party assets in the [media documentation](docs/media.md) and [runtime credits](public/media/credits.txt).
- Run `npm run build` and the relevant Playwright tests. Install Chrome for Playwright with `npx playwright install chrome`, then run `npm test`. For a focused run, pass a test name pattern with `npm test -- --grep "pattern"`.
- For visible changes, include before-and-after screenshots or a recording in the pull request. Note the browser and viewport if the result depends on them. Keep local review files in `.review/`.

## Open a pull request

Explain what changed, why it changed, and how you verified it. Link related issues and call out anything reviewers should check manually. [GitHub Actions](.github/workflows/ci.yml) runs the build and browser suite, and validates pull request titles.
