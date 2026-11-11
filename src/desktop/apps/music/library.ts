export const tracks = [
  { name: 'Galactic Rap', file: 'galactic-rap', length: 142, mood: ['Downtempo', '慢拍'] },
  { name: 'Space Jazz', file: 'space-jazz', length: 370, mood: ['Jazz', '爵士'] },
  {
    name: 'Equatorial Complex',
    file: 'equatorial-complex',
    length: 240,
    mood: ['Ambient', '氛围'],
  },
] as const;
export const artist = 'Kevin MacLeod';
export const timestamp = (value: number) =>
  Math.floor(value / 60) + ':' + String(Math.floor(value) % 60).padStart(2, '0');
export const collectionLength = tracks.reduce((total, track) => total + track.length, 0);
