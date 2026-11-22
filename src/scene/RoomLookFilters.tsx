import { roomCurves } from './room-looks';

export function RoomLookFilters() {
  return (
    <svg
      aria-hidden="true"
      width="0"
      height="0"
      style={{ position: 'absolute', pointerEvents: 'none' }}
    >
      <defs>
        {Object.entries(roomCurves).map(([look, curve]) => (
          <filter
            key={look}
            id={`room-look-${look}`}
            x="0"
            y="0"
            width="100%"
            height="100%"
            colorInterpolationFilters="sRGB"
          >
            <feComponentTransfer>
              <feFuncR type="table" tableValues={curve.red.join(' ')} />
              <feFuncG type="table" tableValues={curve.green.join(' ')} />
              <feFuncB type="table" tableValues={curve.blue.join(' ')} />
            </feComponentTransfer>
            <feColorMatrix type="saturate" values={String(curve.saturation)} />
          </filter>
        ))}
      </defs>
    </svg>
  );
}
