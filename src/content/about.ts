import { biography } from './profile';

export const siteOrigin = 'https://felixpy.com';
export const shareImage = '/media/graphics/felix-studio-preview.jpg';

export const aboutPage = {
  path: '/about',
  title: 'Felix Yang | Senior Software Engineer',
  description:
    'Felix Yang (felixpy, gofelixpy) is a senior software engineer in short-form video and the creator of Felix Studio, an interactive 3D portfolio.',
  heading: 'Felix Yang.',
  subtitle: 'Full-stack engineer & AI maker',
  introduction: [
    'I’m a senior software engineer from China,',
    'with over a decade of experience in the tech industry.',
  ],
  practice: [
    'In my own projects, I explore how AI fits into building apps,',
    'making videos, and designing games.',
  ],
  career: 'The path so far',
  timeline: [
    [biography.school.years.replace('–', ' — '), 'Beihang University', 'Studied & graduated'],
    [biography.first.years.replace('–', ' — '), 'Streaming video', 'Engineering Manager'],
    ['2021 — NOW', 'Short-form video', 'Senior Software Engineer'],
  ],
  experience: 'Building. Learning. Repeating.',
  studio: 'Step inside Felix Studio.',
  studioDescription: 'An interactive 3D workspace. Look around, listen, and play.',
  explore: 'Explore the studio',
  motto: 'Taste Is All You Need.',
  github: 'Find me on GitHub',
  x: 'Follow on X',
  imageAlt: 'The interactive 3D workspace in Felix Studio',
} as const;

export function formatWorkYears(years: number) {
  return `${years} ${years === 1 ? 'year' : 'years'}`;
}
