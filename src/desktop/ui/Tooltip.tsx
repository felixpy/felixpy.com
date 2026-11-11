import type { ReactElement } from 'react';

export function Tooltip({
  children,
  text,
  placement = 'top',
}: {
  children: ReactElement;
  text: string;
  placement?: 'top' | 'bottom-start' | 'bottom-end';
}) {
  return (
    <span className="tooltip-anchor" data-placement={placement}>
      {children}
      <span className="tooltip-label" aria-hidden="true">
        {text}
      </span>
    </span>
  );
}
