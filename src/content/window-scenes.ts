export interface SailingRoute {
  points: [number, number][];
  speed: number;
  start: number;
}

export interface RiverExposure {
  kind: 'river';
  asset: string;
  depth: string;
  aspect: number;
  focal: number;
  center: number;
  clearSkyFrom: number;
  range: [number, number];
  shoreline: number[];
  flow: [number, number];
  waveScale: number;
  route?: SailingRoute;
}

export interface LandExposure {
  kind: 'land';
  asset: string;
  yaw: number;
}

export type WindowExposure = RiverExposure | LandExposure;
type CityWindow = {
  english: string;
  latitude: number;
  longitude: number;
  timezone: string;
  clear: WindowExposure;
  overcast: WindowExposure;
  night: WindowExposure;
};

const huangpu: SailingRoute = {
  points: [
    [-238, 1150],
    [-280, 480],
    [-322, 104],
    [-346, -140],
    [-306, -430],
    [-240, -1180],
  ],
  speed: 4.8,
  start: 0.47,
};
const hudson: SailingRoute = {
  points: [
    [-252, -1350],
    [-280, -630],
    [-286, -230],
    [-304, 0],
    [-362, 250],
    [-396, 530],
    [-419, 1450],
  ],
  speed: 6.2,
  start: 0.49,
};

const bund: Omit<RiverExposure, 'asset' | 'shoreline'> = {
  kind: 'river',
  depth: 'shanghai-depth',
  aspect: 2.25,
  focal: 0.406,
  center: 0.423,
  clearSkyFrom: 0.947,
  range: [130, 980],
  flow: [-0.12, -0.92],
  waveScale: 0.88,
  route: huangpu,
};
const weehawken: Omit<RiverExposure, 'asset' | 'shoreline'> = {
  kind: 'river',
  depth: 'new-york-depth',
  aspect: 3200 / 1014,
  focal: 0.395,
  center: 0.435,
  clearSkyFrom: 0.74,
  range: [150, 1100],
  flow: [0.16, 0.72],
  waveScale: 1.17,
  route: hudson,
};

export const windowCities = {
  上海: {
    english: 'Shanghai',
    latitude: 31.23,
    longitude: 121.47,
    timezone: 'Asia/Shanghai',
    clear: {
      ...bund,
      asset: 'shanghai-clear',
      shoreline: [0.116, 0.103, 0.1, 0.104, 0.102, 0.101, 0.099, 0.1, 0.101],
    },
    overcast: {
      ...bund,
      asset: 'shanghai-day',
      shoreline: [0.12, 0.104, 0.101, 0.104, 0.102, 0.101, 0.1, 0.1, 0.103],
    },
    night: {
      ...bund,
      asset: 'shanghai-night',
      shoreline: [0.12, 0.106, 0.103, 0.105, 0.105, 0.104, 0.101, 0.103, 0.102],
    },
  },
  纽约: {
    english: 'New York',
    latitude: 40.71,
    longitude: -74.01,
    timezone: 'America/New_York',
    clear: {
      ...weehawken,
      asset: 'new-york-day',
      shoreline: [0.141, 0.142, 0.138, 0.141, 0.142, 0.142, 0.141, 0.139, 0.14],
    },
    overcast: {
      ...weehawken,
      asset: 'new-york-overcast',
      shoreline: [0.143, 0.142, 0.139, 0.142, 0.144, 0.144, 0.142, 0.14, 0.141],
    },
    night: {
      ...weehawken,
      asset: 'new-york-night',
      shoreline: [0.144, 0.142, 0.141, 0.143, 0.144, 0.144, 0.143, 0.141, 0.142],
    },
  },
} satisfies Record<string, CityWindow>;

export type WindowCity = keyof typeof windowCities;
export const cityOrder = Object.keys(windowCities) as WindowCity[];

export function windowExposure(city: WindowCity, night: boolean, clear: boolean): WindowExposure {
  const views = windowCities[city];
  return night ? views.night : clear ? views.clear : views.overcast;
}
