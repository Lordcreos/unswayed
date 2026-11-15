import React from 'react';
import type {CSSProperties, FC, ReactNode} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C, F, caps, linear, ramp} from './theme';

/* ---------- pictograms (same drawings as the demo console) ---------- */
const svg = (children: ReactNode, viewBox = '0 0 32 32') => (
  <svg viewBox={viewBox} width="1em" height="1em" style={{flex: 'none', display: 'block'}} aria-hidden>
    {children}
  </svg>
);
export const Icon = {
  tick: svg(
    <>
      <circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" strokeWidth="3" />
      <path d="m9.5 16.5 4.5 4.5 8.5-10" fill="none" stroke="currentColor" strokeWidth="3" />
    </>,
  ),
  block: svg(
    <>
      <path d="M11 3h10l8 8v10l-8 8H11l-8-8V11z" fill="none" stroke="currentColor" strokeWidth="3" />
      <path d="M9 16h14" stroke="currentColor" strokeWidth="3.4" />
    </>,
  ),
  weakens: svg(
    <>
      <circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" strokeWidth="3" />
      <path d="M16 8v15M9.5 16.5 16 23l6.5-6.5" fill="none" stroke="currentColor" strokeWidth="3" />
    </>,
  ),
  seal: svg(
    <>
      <rect x="4" y="10" width="16" height="11" rx="1.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" strokeWidth="2.2" />
    </>,
    '0 0 24 24',
  ),
  equal: svg(
    <>
      <path d="M6 12h20M6 20h20" fill="none" stroke="currentColor" strokeWidth="3.4" />
    </>,
  ),
  arrowRight: svg(<path d="M1 8h21M16 2l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2.6" />, '0 0 24 16'),
  arrowDown: svg(<path d="M6 1v9M2 6l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.8" />, '0 0 12 12'),
};

/* ---------- scene wrapper: fades content over the constant paper ground ---------- */
export const Scene: FC<{dur: number; fadeIn?: number; fadeOut?: number; children: ReactNode}> = ({
  dur,
  fadeIn = 10,
  fadeOut = 8,
  children,
}) => {
  const f = useCurrentFrame();
  const a = fadeIn ? linear(f, 0, fadeIn) : 1;
  const b = fadeOut ? 1 - linear(f, dur - fadeOut, fadeOut) : 1;
  return <AbsoluteFill style={{opacity: Math.min(a, b), color: C.ink}}>{children}</AbsoluteFill>;
};

/* ---------- inline code: `x` in recorded text becomes a code span, text is not changed ---------- */
export const Inline: FC<{text: string; codeStyle?: CSSProperties}> = ({text, codeStyle}) => {
  const parts = text.split(/`([^`]+)`/g);
  return (
    <>
      {parts.map((p, i) =>
        i % 2 ? (
          <code key={i} style={{fontFamily: F.code, fontSize: '.86em', ...codeStyle}}>
            {p}
          </code>
        ) : (
          <React.Fragment key={i}>{p}</React.Fragment>
        ),
      )}
    </>
  );
};

/* ---------- rubber stamp: word + pictogram, pressed by hand at -4deg ---------- */
export const Stamp: FC<{word: string; icon: ReactNode; size?: number; at: number; style?: CSSProperties}> = ({
  word,
  icon,
  size = 96,
  at,
  style,
}) => {
  const f = useCurrentFrame();
  const p = ramp(f, at, 15);
  return (
    <span
      style={{
        ...caps(size, 800, '.04em'),
        whiteSpace: 'nowrap',
        display: 'inline-flex',
        alignItems: 'center',
        gap: size * 0.2,
        padding: `${size * 0.2}px ${size * 0.34}px ${size * 0.18}px`,
        border: `${size * 0.107}px solid currentColor`,
        borderRadius: size * 0.143,
        outline: `${size * 0.043}px solid currentColor`,
        outlineOffset: -size * 0.222,
        transformOrigin: '30% 60%',
        transform: `rotate(${-13 + 9 * p}deg) scale(${1.7 - 0.7 * p})`,
        filter: p < 1 ? `blur(${(1 - p) * 8}px)` : undefined,
        opacity: f < at ? 0 : Math.min(1, p * 1.6),
        ...style,
      }}
    >
      <span style={{fontSize: size * 0.9, display: 'flex'}}>{icon}</span>
      {word}
    </span>
  );
};

/* ---------- blister pack: one cell per pull request, the denominator stays visible ---------- */
export const Cells: FC<{
  total: number;
  on: number;
  cols: number;
  size: number;
  gap?: number;
  color: string;
  at?: number;
  stagger?: number;
  outline?: string;
}> = ({total, on, cols, size, gap = 5, color, at = 0, stagger = 0.3, outline = C.ink}) => {
  const f = useCurrentFrame();
  const bw = Math.max(1.5, size * 0.055);
  return (
    <div style={{display: 'grid', gridTemplateColumns: `repeat(${cols}, ${size}px)`, gap, flex: 'none'}}>
      {Array.from({length: total}, (_, i) => {
        const p = i < on ? ramp(f, at + i * stagger, 10) : 0;
        return (
          <i
            key={i}
            style={{
              display: 'block',
              width: size,
              height: size,
              boxSizing: 'border-box',
              borderRadius: '28%',
              border: `${bw}px solid ${outline}`,
              position: 'relative',
            }}
          >
            {p > 0 ? (
              <b
                style={{
                  position: 'absolute',
                  inset: -bw,
                  borderRadius: '28%',
                  border: `${bw}px solid ${outline}`,
                  boxSizing: 'border-box',
                  background: color,
                  opacity: Math.min(1, p * 1.5),
                  transform: `scale(${0.2 + 0.8 * p})`,
                }}
              />
            ) : null}
          </i>
        );
      })}
    </div>
  );
};

/* ---------- heavy numeral with its "of N" ---------- */
export const Count: FC<{n: number; total: number; size: number; minDigits?: number; style?: CSSProperties}> = ({
  n,
  total,
  size,
  minDigits,
  style,
}) => (
  <p
    style={{
      margin: 0,
      display: 'flex',
      alignItems: 'baseline',
      gap: size * 0.14,
      whiteSpace: 'nowrap',
      fontFamily: F.display,
      fontWeight: 800,
      fontSize: size,
      lineHeight: 0.86,
      fontVariantNumeric: 'tabular-nums',
      ...style,
    }}
  >
    <span style={{minWidth: minDigits ? `${minDigits * 0.47}em` : undefined, textAlign: 'right'}}>{n}</span>
    <small style={{...caps(size * 0.34, 600, '.02em')}}>of {total}</small>
  </p>
);

/* ---------- caution-yellow label patch ---------- */
export const Flag: FC<{children: ReactNode; size?: number; style?: CSSProperties}> = ({children, size = 34, style}) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: size * 0.35,
      background: C.caution,
      color: C.ink,
      ...caps(size, 800, '.03em'),
      padding: `${size * 0.3}px ${size * 0.45}px ${size * 0.26}px`,
      ...style,
    }}
  >
    {children}
  </span>
);

/* ---------- scene headline ---------- */
export const Headline: FC<{children: ReactNode; size?: number; style?: CSSProperties}> = ({
  children,
  size = 80,
  style,
}) => <h2 style={{margin: 0, ...caps(size, 800, '.005em'), ...style}}>{children}</h2>;
