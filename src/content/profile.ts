export const profile = { name: 'Felix Yang', role: '软件工程师' } as const;
export const publicProfiles = {
  githubProfile: 'https://github.com/felixpy',
  x: 'https://x.com/gofelixpy',
  github: 'https://github.com/felixpy/felixpy.com',
} as const;

export function getWorkYears(today = new Date()) {
  const { year, month } = biography.first.started;
  const months = (today.getFullYear() - year) * 12 + today.getMonth() + 1 - month;
  return Math.max(0, Math.floor(months / 12));
}

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
