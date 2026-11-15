// Typed view of src/data.json, which scripts/build-data.mjs generates from ../demo/data.js.
import raw from './data.json';

export type Counts = {
  total: number;
  approved_alone: number;
  approved_gated: number;
  approved_blind_only: number;
  flagged: number;
};
export type ReviewerStats = {name: string; malicious: Counts; benign: Counts};
export type Ordinary = {name: string; flagged: number; total: number};
export type Sample = {
  id: string;
  kind: string;
  vuln: string;
  cwe: string;
  repo: string;
  framing: string;
  title: string;
  body: string;
  diff: string;
  reviewer: {approved: boolean; passes: number; runs: number; reason: string};
  gate: {effect: string; votes: string[]; findings: string[]};
};
export type Data = {
  recorded: string;
  reviewer: string;
  benchmark: string;
  runs: number;
  stats: {reviewer: ReviewerStats; other: ReviewerStats; ordinary: Ordinary[]};
  sample: Sample;
};

export const D = raw as Data;
export const S = D.sample;
