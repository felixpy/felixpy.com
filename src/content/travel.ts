import type { Locale } from '../app/locale';

export const journeys = {
  europe: [
    { id: 'netherlands', en: 'Netherlands', zh: '荷兰', lon: 5.31, lat: 52.15 },
    { id: 'france', en: 'France', zh: '法国', lon: 2.35, lat: 46.71 },
    { id: 'portugal', en: 'Portugal', zh: '葡萄牙', lon: -8.08, lat: 39.55 },
    { id: 'germany', en: 'Germany', zh: '德国', lon: 10.38, lat: 51.12 },
  ],
  china: [
    { id: 'guizhou', en: 'Guizhou', zh: '贵州', lon: 109.18, lat: 27.72 },
    { id: 'beijing', en: 'Beijing', zh: '北京', lon: 116.4, lat: 39.9 },
  ],
} as const;

export const printGreeting = {
  en: 'To whoever found this,',
  zh: '给偶然翻到这张照片的你',
} as const;

export const travelPrints = [
  {
    en: 'Rijksmuseum · Netherlands',
    zh: '国立博物馆 · 荷兰',
    caption: {
      en: 'Soft morning light picks out the museum’s red brick and tall windows.',
      zh: '清晨的柔光照亮了博物馆的红砖和高窗。',
    },
    note: {
      en: 'I hope you notice one small thing today\nthat you would usually walk past.',
      zh: '愿你今天留意到一样\n平时会匆匆走过的小东西。',
    },
  },
  {
    en: 'Eiffel Tower · France',
    zh: '埃菲尔铁塔 · 法国',
    caption: {
      en: 'The tower’s ironwork stands out against a pale Paris sky.',
      zh: '巴黎淡淡的天光衬出了铁塔的细密轮廓。',
    },
    note: {
      en: 'If today has been crowded,\nI hope you find a little room to breathe.',
      zh: '如果今天挤得有点喘不过气，\n愿你还能留一点空给自己。',
    },
  },
  {
    en: 'Belém Tower · Portugal',
    zh: '贝伦塔 · 葡萄牙',
    caption: {
      en: 'The last warm light falls across the tower beside the Tagus.',
      zh: '最后一点暖光落在塔霍河边的贝伦塔上。',
    },
    note: {
      en: 'If you are waiting on something,\nI hope the light is good where you are.',
      zh: '如果你也正在等什么，\n愿此刻照在你身上的光是暖的。',
    },
  },
  {
    en: 'Brandenburg Gate · Germany',
    zh: '勃兰登堡门 · 德国',
    caption: {
      en: 'Even light makes the columns and the silhouette above them easy to read.',
      zh: '均匀的天光下，石柱和顶部轮廓格外清楚。',
    },
    note: {
      en: 'Take the long way if you have time.\nI hope it gives you a good story.',
      zh: '如果来得及，不妨绕一点路。\n愿你遇见一件以后想讲起的事。',
    },
  },
  {
    en: 'Temple of Heaven · Beijing',
    zh: '天坛祈年殿 · 北京',
    caption: {
      en: 'The blue roof sits quietly above the pale stone terraces.',
      zh: '蓝瓦屋顶立在浅色石台上，线条很安静。',
    },
    note: {
      en: 'Whatever brought you here,\nI hope you leave with something worth keeping.',
      zh: '不管你是怎么走到这里的，\n愿你带走一点值得留下的东西。',
    },
  },
  {
    en: 'Oriental Pearl Tower · Shanghai',
    zh: '东方明珠 · 上海',
    caption: {
      en: 'The spheres of the tower catch the last light across the river.',
      zh: '隔着江，塔上的球体还接得住一点天光。',
    },
    note: {
      en: 'On your way home, look back once.\nThe same place can surprise you twice.',
      zh: '回去的路上，记得回头看一眼。\n同一个地方也会给人两次惊喜。',
    },
  },
  {
    en: 'Fanjingshan · Tongren',
    zh: '梵净山红云金顶 · 铜仁',
    caption: {
      en: 'Two small temples meet above the cloud line, joined by a footbridge.',
      zh: '云线之上，一座小桥把两边的殿宇连在一起。',
    },
    note: {
      en: 'I hope there is somewhere in the world\nyou can return to and feel at home.',
      zh: '愿这个世界上有个地方，\n你一回去，就知道自己到家了。',
    },
  },
] as const;

export function travelCaption(index: number, locale: Locale) {
  return travelPrints[index].caption[locale];
}
