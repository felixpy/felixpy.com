export const profile = { name: 'Felix Yang', role: '软件工程师' } as const;
export const publicProfiles = {
  x: 'https://x.com/gofelixpy',
  github: 'https://github.com/felixpy/felixpy.com',
} as const;

export const biography = {
  hometown: '贵州铜仁',
  school: { years: '2010–2014', name: '北京航空航天大学', role: '求学并毕业' },
  first: {
    started: { year: 2014, month: 7 },
    years: '2014–2021',
    name: '流媒体视频公司',
    role: '离职前任技术经理',
  },
  second: { years: '2021–至今', name: '短视频公司', role: '高级软件工程师' },
} as const;

export const careerEditions = [
  {
    id: 'first',
    volume: '01',
    title: 'STREAMING VIDEO',
    ink: '#153645',
    accent: '#8cb7c2',
    jacket: '#234d69',
    years: [biography.first.years, biography.first.years],
    name: ['Streaming video company', biography.first.name],
    role: ['Technology Manager at departure', biography.first.role],
  },
  {
    id: 'second',
    volume: '02',
    title: 'SHORT-FORM VIDEO',
    ink: '#382b45',
    accent: '#b6a1c5',
    jacket: '#2d4167',
    years: ['2021–Present', biography.second.years],
    name: ['Short-form video company', biography.second.name],
    role: ['Senior Software Engineer', biography.second.role],
  },
] as const;

export const books = [
  ['代码大全', 'Code Complete', 'Steve McConnell', '#705047'],
  ['算法导论', 'Introduction to Algorithms', 'Cormen · Leiserson · Rivest · Stein', '#243b47'],
  [
    '深入理解计算机系统',
    'Computer Systems: A Programmer’s Perspective',
    'Bryant · O’Hallaron',
    '#836d46',
  ],
  ['设计数据密集型应用', 'Designing Data-Intensive Applications', 'Martin Kleppmann', '#524d3b'],
  [
    '计算机程序的构造和解释',
    'Structure and Interpretation of Computer Programs',
    'Abelson · Sussman · Sussman',
    '#534041',
  ],
  ['程序员修炼之道', 'The Pragmatic Programmer', 'Andrew Hunt · David Thomas', '#343e4a'],
  ['百年孤独', 'One Hundred Years of Solitude', 'Gabriel García Márquez', '#81644b'],
  ['局外人', 'The Stranger', 'Albert Camus', '#323f43'],
  ['喧哗与骚动', 'The Sound and the Fury', 'William Faulkner', '#743d35'],
  ['老人与海', 'The Old Man and the Sea', 'Ernest Hemingway', '#375058'],
  ['西方哲学史', 'A History of Western Philosophy', 'Bertrand Russell', '#836740'],
  ['西西弗神话', 'The Myth of Sisyphus', 'Albert Camus', '#6f443d'],
  ['存在与虚无', 'Being and Nothingness', 'Jean-Paul Sartre', '#4a4b42'],
] as const;
