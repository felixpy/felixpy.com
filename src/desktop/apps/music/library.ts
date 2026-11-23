export const tracks = [
  {
    name: 'Moonlit Skyline',
    artist: 'Nihilore',
    file: 'moonlit-skyline',
    length: 292,
    mood: ['Downtempo', '慢拍'],
  },
  {
    name: 'A Mundane Conclusion',
    artist: 'Nihilore',
    file: 'a-mundane-conclusion',
    length: 417,
    mood: ['Chillhop', '舒缓嘻哈'],
  },
  {
    name: 'The Murky Deep',
    artist: 'Nihilore',
    file: 'the-murky-deep',
    length: 320,
    mood: ['Slow jazz', '慢爵士'],
  },
  {
    name: 'Kadupul',
    artist: 'Nihilore',
    file: 'kadupul',
    length: 221,
    mood: ['Electronic beats', '电子节拍'],
  },
  {
    name: 'Lore',
    artist: 'Nihilore',
    file: 'lore',
    length: 287,
    mood: ['Trip-hop', '迷幻节拍'],
  },
] as const;
export const timestamp = (value: number) =>
  Math.floor(value / 60) + ':' + String(Math.floor(value) % 60).padStart(2, '0');
export const collectionLength = tracks.reduce((total, track) => total + track.length, 0);
