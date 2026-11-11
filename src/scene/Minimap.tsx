import type { RefObject } from 'react';
import { desk, roomSize, windowOpening, workshopLayout } from './furniture';
import { eye } from './camera';

export function Minimap({
  marker,
  label,
}: {
  marker: RefObject<SVGGElement | null>;
  label: string;
}) {
  const { west, east, north, south } = roomSize;
  const doorLeft = 1.409,
    doorRight = 2.251;
  const wallInset = 0.017;
  const cabinetDepth = 0.36;
  const benchStart = north + wallInset + cabinetDepth;
  const benchLeft = workshopLayout.x - 0.31;
  return (
    <aside className="studio-minimap" aria-label={label}>
      <svg
        viewBox={`${west - 0.16} ${north - 0.16} ${east - west + 0.32} ${south - north + 0.32}`}
        aria-hidden="true"
      >
        <rect
          x={west}
          y={north}
          width={east - west}
          height={south - north}
          rx=".035"
          className="minimap-floor"
        />
        <path
          d={`M ${doorLeft} ${south} H ${west} V ${north} H ${east} V ${south} H ${doorRight}`}
          className="minimap-walls"
        />
        <path
          d={`M ${west} ${windowOpening.z0} V ${windowOpening.z1} M ${doorLeft} ${south} H ${doorRight}`}
          className="minimap-openings"
        />
        <g className="minimap-furniture">
          <rect
            x={desk.left + wallInset}
            y={desk.back + wallInset}
            width={desk.right - desk.left - wallInset}
            height={desk.front - desk.back - wallInset}
            rx=".035"
          />
          <rect
            x={desk.right}
            y={north + wallInset}
            width={east - desk.right - wallInset}
            height={cabinetDepth}
            rx=".025"
          />
          <rect
            x={benchLeft}
            y={benchStart}
            width={east - benchLeft - wallInset}
            height={workshopLayout.z + workshopLayout.length / 2 - benchStart}
            rx=".035"
          />
          <rect x="-1.12" y="2.74" width="1.16" height=".3" rx=".06" />
        </g>
        <g ref={marker} transform={`translate(${eye.x} ${eye.defaultZ})`}>
          <path className="minimap-view" d="M0 0 -.42 -.66 A .79 .79 0 0 1 .42 -.66 Z" />
          <path className="minimap-player" d="M0 -.18 .13 .13 0 .08 -.13 .13 Z" />
        </g>
      </svg>
    </aside>
  );
}
