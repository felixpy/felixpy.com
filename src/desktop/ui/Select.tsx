import { Check, ChevronDown } from 'lucide-react';
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';

export function Select<Value extends string>({
  labelId,
  value,
  options,
  onChange,
}: {
  labelId: string;
  value: Value;
  options: readonly { value: Value; label: string }[];
  onChange: (value: Value) => void;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const listbox = useRef<HTMLDivElement>(null);
  const listboxId = useId();
  const valueId = useId();
  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    if (!open) return;
    const option = listbox.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]');
    option?.focus({ preventScroll: true });

    function dismissOutside(event: PointerEvent) {
      if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false);
    }

    document.addEventListener('pointerdown', dismissOutside, true);
    return () => document.removeEventListener('pointerdown', dismissOutside, true);
  }, [open]);

  function close() {
    setOpen(false);
    trigger.current?.focus({ preventScroll: true });
  }

  function navigate(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' && open) {
      event.preventDefault();
      event.stopPropagation();
      close();
      return;
    }
    const step = event.key === 'ArrowDown' ? 1 : event.key === 'ArrowUp' ? -1 : 0;
    if (!open && step) {
      event.preventDefault();
      event.stopPropagation();
      setOpen(true);
      return;
    }
    if (!open || (!step && event.key !== 'Home' && event.key !== 'End')) return;

    event.preventDefault();
    event.stopPropagation();
    const buttons = Array.from(listbox.current?.querySelectorAll('button') ?? []);
    const current = buttons.indexOf(document.activeElement as HTMLButtonElement);
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? buttons.length - 1
          : Math.max(0, Math.min(buttons.length - 1, current + step));
    buttons[next]?.focus({ preventScroll: true });
  }

  return (
    <div
      className="os-select"
      ref={root}
      onKeyDown={navigate}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        className="os-select-trigger"
        type="button"
        ref={trigger}
        aria-labelledby={`${labelId} ${valueId}`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        onClick={() => setOpen(!open)}
      >
        <span id={valueId}>{selected?.label}</span>
        <ChevronDown aria-hidden="true" />
      </button>
      {open && (
        <div
          className="os-select-options"
          id={listboxId}
          ref={listbox}
          role="listbox"
          aria-labelledby={labelId}
        >
          {options.map((option) => (
            <button
              type="button"
              key={option.value}
              role="option"
              tabIndex={-1}
              aria-selected={option.value === value}
              onClick={() => {
                onChange(option.value);
                close();
              }}
            >
              {option.label}
              {option.value === value && <Check aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
