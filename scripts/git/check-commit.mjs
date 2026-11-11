import { readFileSync } from 'node:fs';

const [argument, value] = process.argv.slice(2);
if (!argument || (argument === '--message' && !value)) {
  console.error('Usage: npm run check:commit -- <message-file> | --message "<subject>"');
  process.exit(2);
}

const message = argument === '--message' ? value : readFileSync(argument, 'utf8');
const subject =
  message
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line && !line.startsWith('#')) ?? '';
const conventional =
  /^(?:fixup! |squash! |amend! )?(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\([\w./-]+\))?!?: \S/;
const generated = /^(?:Merge (?:branch|branches|remote-tracking branch|tag|commit) |Revert ".+"$)/;

if (!conventional.test(subject) && (argument === '--message' || !generated.test(subject))) {
  console.error(
    'Use a Conventional Commit subject, for example: fix(scene): align the window projection',
  );
  process.exit(1);
}
