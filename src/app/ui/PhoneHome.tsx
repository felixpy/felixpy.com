import { useEffect, useState, type RefObject } from 'react';
import {
  BatteryFull,
  Frame,
  Lamp,
  LampCeiling,
  LampDesk,
  LampFloor,
  Lightbulb,
  Monitor,
  PanelsTopLeft,
  Signal,
  Spotlight,
  Wifi,
} from 'lucide-react';
import type { Environment } from '../environment';
import { homeLights, isHomeLightOn, type HomeLightId } from '../home-lights';
import { local } from '../locale';
import './phone-home.css';

const icons = {
  ceilingLamp: LampCeiling,
  wallLamp: Spotlight,
  floorLamp: LampFloor,
  pictureLamp: Frame,
  lamp: Lamp,
  screenBar: Monitor,
  benchLamp: LampDesk,
  toolBoardLamp: PanelsTopLeft,
};

type Props = {
  panelRef: RefObject<HTMLDivElement | null>;
  environment: Environment;
  onToggle: (id: HomeLightId) => void;
};

export default function PhoneHome({ panelRef, environment, onToggle }: Props) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 15000);
    return () => window.clearInterval(interval);
  }, []);
  const { locale } = environment;
  const active = homeLights.filter((light) => isHomeLightOn(environment, light.id)).length;
  const time = now.getHours() + ':' + String(now.getMinutes()).padStart(2, '0');
  const count =
    active > 0
      ? local(locale, active + ' on', active + ' 盏已开启')
      : local(locale, 'All off', '全部关闭');
  return (
    <div
      ref={panelRef}
      className="phone-home"
      data-phone-home=""
      role="region"
      aria-label={local(locale, 'Apple Home', 'Apple 家庭')}
      tabIndex={-1}
    >
      <div className="phone-home-status" aria-hidden="true">
        <time>{time}</time>
        <i className="phone-home-island" />
        <span>
          <Signal size={17} />
          <Wifi size={15} />
          <BatteryFull size={21} />
        </span>
      </div>
      <div className="phone-home-content">
        <h1>{local(locale, 'My Home', '我的家庭')}</h1>
        <div className="phone-home-summary" aria-live="polite">
          <Lightbulb aria-hidden="true" size={27} />
          <span>
            {local(locale, 'Lighting', '照明')}
            <small>{count}</small>
          </span>
        </div>
        <h2>{local(locale, 'Studio', '工作室')}</h2>
        <div className="phone-home-accessories">
          {homeLights.map(({ id, en, zh }) => {
            const Icon = icons[id];
            const enabled = isHomeLightOn(environment, id);
            const label = local(locale, en, zh);
            return (
              <button
                key={id}
                type="button"
                role="switch"
                aria-label={label}
                aria-checked={enabled}
                data-home-light={id}
                onClick={() => onToggle(id)}
              >
                <span className="phone-home-glyph">
                  <Icon aria-hidden="true" size={26} strokeWidth={1.8} />
                </span>
                <span className="phone-home-device">{label}</span>
                <span className="phone-home-state">
                  {enabled ? local(locale, 'On', '已开启') : local(locale, 'Off', '已关闭')}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="phone-home-indicator" aria-hidden="true" />
    </div>
  );
}
