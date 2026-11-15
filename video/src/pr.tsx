import type {CSSProperties, FC, ReactNode} from 'react';
import {S} from './data';
import {Icon, Inline} from './components';
import {C, F, PAD_X, caps} from './theme';

/* Shared geometry of the pull-request stage (scenes 2, 3 and 5). */
export const PR = {
  top: 136,
  tall: 904,
  compact: 420,
  bandTop: 576,
  bandH: 464,
  storyW: 868,
  diffW: 916,
  gap: 24,
  head: 62,
};

const frame: CSSProperties = {
  position: 'absolute',
  top: PR.top,
  background: C.stock,
  border: `3px solid ${C.ink}`,
  borderRadius: 3,
  overflow: 'hidden',
  boxSizing: 'border-box',
};

const PanelHead: FC<{title: string; note: ReactNode; bg: string; color: string}> = ({title, note, bg, color}) => (
  <div
    style={{
      height: PR.head,
      background: bg,
      color,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      flex: 'none',
    }}
  >
    <span style={caps(44, 800, '.01em')}>{title}</span>
    <span style={caps(25, 600, '.04em')}>{note}</span>
  </div>
);

/* ---------- THE STORY: the author's title and description, verbatim ---------- */

/* Cuts at a word boundary and marks the cut with an ellipsis; the recorded text is never reworded. */
export const truncate = (text: string, max: number): string => {
  if (text.length <= max) return text;
  let cut = text.slice(0, max);
  if (!/\s/.test(text.charAt(max))) cut = cut.slice(0, cut.lastIndexOf(' '));
  return cut.replace(/[\s,;:]+$/, '') + ' …';
};

type Block = {kind: 'h' | 'li' | 'p'; text: string};
const blocks = (body: string): Block[] =>
  body
    .split('\n')
    .filter((l) => l.trim())
    .map((line) =>
      /^#{1,4}\s+/.test(line)
        ? {kind: 'h', text: line.replace(/^#{1,4}\s+/, '')}
        : /^- /.test(line)
          ? {kind: 'li', text: line.slice(2)}
          : {kind: 'p', text: line},
    );

export const StoryPanel: FC<{
  height: number;
  maxChars: number;
  note?: ReactNode;
  more?: number; // opacity of the "continues" cue and the bottom fade
  children?: ReactNode; // overlay drawn over the body (the seal)
  style?: CSSProperties;
}> = ({height, maxChars, note = 'What the author wrote', more = 0, children, style}) => {
  const body = truncate(S.body, maxChars);
  const fade = more > 0 ? `linear-gradient(#000 calc(100% - ${90 * more}px), transparent)` : undefined;
  return (
    <section style={{...frame, left: PAD_X, width: PR.storyW, height, display: 'flex', flexDirection: 'column', ...style}}>
      <PanelHead title="The story" note={note} bg={C.story} color={C.ink} />
      <div style={{position: 'relative', flex: 1, minHeight: 0}}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            padding: '22px 30px 0',
            overflow: 'hidden',
            WebkitMaskImage: fade,
            maskImage: fade,
          }}
        >
          <h3
            style={{
              margin: '0 0 14px',
              fontFamily: F.display,
              fontWeight: 600,
              fontSize: 46,
              lineHeight: 1.12,
              letterSpacing: '.005em',
            }}
          >
            {S.title}
          </h3>
          {blocks(body).map((b, i) => (
            <p
              key={i}
              style={{
                margin: b.kind === 'h' ? '14px 0 4px' : '0 0 8px',
                fontFamily: F.text,
                fontWeight: b.kind === 'h' ? 600 : 400,
                fontSize: 29,
                lineHeight: 1.4,
                paddingLeft: b.kind === 'li' ? 34 : 0,
                position: 'relative',
                overflowWrap: 'anywhere',
              }}
            >
              {b.kind === 'li' ? (
                <i style={{position: 'absolute', left: 4, top: '0.66em', width: 16, height: 4, background: C.ink}} />
              ) : null}
              <Inline text={b.text} />
            </p>
          ))}
        </div>
        {more > 0 ? (
          <p
            style={{
              position: 'absolute',
              right: 14,
              bottom: 12,
              margin: 0,
              opacity: Math.max(0, (more - 0.6) / 0.4),
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: C.ink,
              color: C.stock,
              ...caps(22, 600, '.05em'),
              padding: '7px 12px 6px',
            }}
          >
            <span style={{fontSize: 18, display: 'flex'}}>{Icon.arrowDown}</span>Continues
          </p>
        ) : null}
        {children}
      </div>
    </section>
  );
};

/* ---------- THE DIFF: the recorded diff, verbatim; removal is caution yellow, never red/green ---------- */
type Row = {kind: 'file' | 'hunk' | 'rem' | 'add' | 'ctx'; text: string};
const rows: Row[] = [];
S.diff.split('\n').forEach((line) => {
  const m = /^diff --git a\/(\S+)/.exec(line);
  if (m) return void rows.push({kind: 'file', text: m[1]});
  if (/^(---|\+\+\+) /.test(line)) return;
  if (line.startsWith('@@')) return void rows.push({kind: 'hunk', text: line});
  const sign = line.charAt(0);
  rows.push({kind: sign === '-' ? 'rem' : sign === '+' ? 'add' : 'ctx', text: line.slice(1).replace(/\t/g, '  ')});
});
/* The first removed line that has content: the line the video points at. */
export const removedLine = (rows.find((r) => r.kind === 'rem' && r.text.trim()) || {text: ''}).text.trim();

const DIFF_FONT = 24;
const DIFF_LH = 34;

export const DiffPanel: FC<{
  height: number;
  hl: number; // 0..1 caution-yellow wipe over the removed lines
  callout?: number; // 0..1 the enlarged removed line (tall layout only)
  fields?: number; // 0..1 the kit-label fields at the foot (tall layout only)
  note?: ReactNode;
  style?: CSSProperties;
}> = ({height, hl, callout = 0, fields = 0, note = 'What the change does', style}) => (
  <section
    style={{
      ...frame,
      left: PAD_X + PR.storyW + PR.gap,
      width: PR.diffW,
      height,
      display: 'flex',
      flexDirection: 'column',
      ...style,
    }}
  >
    <PanelHead title="The diff" note={note} bg={C.ink} color={C.stock} />
    <div style={{padding: '18px 24px 0', flex: 'none'}}>
      <div style={{border: `2px solid ${C.rule}`, fontFamily: F.code, fontSize: DIFF_FONT, lineHeight: `${DIFF_LH}px`}}>
        {rows.map((r, i) =>
          r.kind === 'file' || r.kind === 'hunk' ? (
            <div
              key={i}
              style={{background: C.ink, color: C.stock, fontSize: 20, padding: '0 12px', whiteSpace: 'pre', height: DIFF_LH}}
            >
              {r.text}
            </div>
          ) : (
            <div
              key={i}
              style={{
                position: 'relative',
                height: DIFF_LH,
                padding: '0 12px 0 2.2em',
                whiteSpace: 'pre',
                fontWeight: r.kind === 'rem' ? 700 : 400,
                background: r.kind === 'add' ? C.added : undefined,
              }}
            >
              {r.kind === 'rem' ? (
                <i
                  style={{
                    position: 'absolute',
                    inset: 0,
                    background: C.caution,
                    transformOrigin: '0 50%',
                    transform: `scaleX(${hl})`,
                  }}
                />
              ) : null}
              <span style={{position: 'absolute', left: '.55em', fontWeight: 700, fontSize: '1.15em'}}>
                {r.kind === 'rem' ? '−' : r.kind === 'add' ? '+' : ''}
              </span>
              <span style={{position: 'relative'}}>{r.text || ' '}</span>
            </div>
          ),
        )}
      </div>
    </div>

    {/* Tall layout only: the removed line again, large enough for the back of the room. */}
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'flex-start',
        padding: '0 24px',
        opacity: callout,
        transform: `translateY(${(1 - callout) * 18}px)`,
      }}
    >
      <p style={{margin: '0 0 14px', ...caps(34, 800, '.03em')}}>Removed by this pull request</p>
      <p
        style={{
          margin: 0,
          background: C.caution,
          fontFamily: F.code,
          fontWeight: 700,
          fontSize: 58,
          lineHeight: 1,
          padding: '20px 26px 22px',
          whiteSpace: 'pre',
        }}
      >
        {removedLine}
      </p>
    </div>

    {/* Tall layout only: the specimen label fields, as on the console's kit header. */}
    <dl
      style={{
        margin: 0,
        flex: 'none',
        height: 104,
        display: 'grid',
        gridTemplateColumns: 'auto auto 1fr',
        borderTop: `3px solid ${C.ink}`,
        opacity: fields,
      }}
    >
      {[
        ['Source', S.repo],
        ['Class', S.cwe],
        ['Lot', S.vuln],
      ].map(([k, v], i) => (
        <div
          key={k}
          style={{
            borderLeft: i ? `3px solid ${C.ink}` : undefined,
            padding: '0 26px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <dt style={caps(24, 600, '.06em')}>{k}</dt>
          <dd style={{margin: 0, ...caps(42, 800, '.01em'), textTransform: 'none', whiteSpace: 'nowrap'}}>{v}</dd>
        </div>
      ))}
    </dl>
  </section>
);
