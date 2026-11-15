import type {CSSProperties} from 'react';
import {Easing, interpolate} from 'remotion';

// Tokens from DESIGN.md ("The Trial-Kit Label").
export const C = {
  paper: '#f3f6f9',
  stock: '#ffffff',
  ink: '#0d1b2a',
  story: '#ff5a36',
  blind: '#1746e0',
  blindDeep: '#0c2a94',
  blindTint: '#d9e3ff',
  sealedBar: '#05103f',
  caution: '#ffd400',
  added: '#e2e8f1',
  rule: 'rgba(13, 27, 42, .22)',
};

export const F = {
  display: '"Barlow Condensed", "Arial Narrow", sans-serif',
  text: '"Barlow", "Helvetica Neue", Arial, sans-serif',
  code: 'Menlo, "SF Mono", Consolas, monospace',
};

export const FPS = 30;
export const W = 1920;
export const H = 1080;
export const PAD_X = 56;

// Scene boundaries in frames (30 fps). Total 1650 frames = 55 s.
export const SCENES = {
  title: {from: 0, dur: 120},
  pr: {from: 120, dur: 510}, // storyboard 2 (270 f) + 3 (240 f) share one continuous layout
  bigNumber: {from: 630, dur: 150},
  gate: {from: 780, dur: 300},
  beforeAfter: {from: 1080, dur: 240},
  cost: {from: 1320, dur: 180},
  end: {from: 1500, dur: 150},
};
export const TOTAL_FRAMES = 1650;

export const EASE = Easing.bezier(0.16, 1, 0.3, 1);

export const ramp = (frame: number, start: number, dur = 15): number =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE,
  });

export const linear = (frame: number, start: number, dur: number): number =>
  interpolate(frame, [start, start + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

export const rise = (frame: number, start: number, dur = 16, dist = 18): CSSProperties => {
  const p = ramp(frame, start, dur);
  return {opacity: p, transform: `translateY(${(1 - p) * dist}px)`};
};

export const wipe = (frame: number, start: number, dur = 18): CSSProperties => {
  const p = ramp(frame, start, dur);
  return {clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`};
};

export const pct = (a: number, b: number): number => Math.round((100 * a) / b);

export const caps = (size: number, weight: 600 | 800 = 800, tracking = '.01em'): CSSProperties => ({
  fontFamily: F.display,
  fontWeight: weight,
  fontSize: size,
  lineHeight: 1,
  letterSpacing: tracking,
  textTransform: 'uppercase',
});
