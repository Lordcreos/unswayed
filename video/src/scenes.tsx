import type {CSSProperties, FC, ReactNode} from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Cells, Count, Flag, Headline, Icon, Inline, Scene, Stamp} from './components';
import {D, S} from './data';
import {DiffPanel, PR, StoryPanel} from './pr';
import {C, EASE, F, PAD_X, SCENES, W, caps, linear, pct, ramp, rise, wipe} from './theme';

const R = D.stats.reviewer;
const O = D.stats.other;
const TAGLINE = 'Judge the diff, not the story.';

const INNER = W - 2 * PAD_X;
const label: CSSProperties = {
  position: 'absolute',
  left: PAD_X,
  width: INNER,
  background: C.stock,
  border: `3px solid ${C.ink}`,
  borderRadius: 3,
  boxSizing: 'border-box',
};

/* The tagline with each arm's colour under its own word (vermilion: the story, ultramarine: the diff). */
const Tagline: FC<{size: number; at: number}> = ({size, at}) => {
  const f = useCurrentFrame();
  const bar = (color: string, start: number): CSSProperties => ({
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: -size * 0.06,
    height: size * 0.11,
    background: color,
    transformOrigin: '0 50%',
    transform: `scaleX(${ramp(f, start, 16)})`,
  });
  const word: CSSProperties = {position: 'relative', display: 'inline-block'};
  return (
    <p
      style={{
        margin: 0,
        fontFamily: F.display,
        fontWeight: 600,
        fontSize: size,
        lineHeight: 1.1,
        whiteSpace: 'nowrap',
        ...rise(f, at),
      }}
    >
      Judge{' '}
      <span style={word}>
        the diff
        <i style={bar(C.blind, at + 14)} />
      </span>
      , not{' '}
      <span style={word}>
        the story
        <i style={bar(C.story, at + 24)} />
      </span>
      .
    </p>
  );
};

/* ================= 1. Title card ================= */
export const TitleScene: FC = () => {
  const f = useCurrentFrame();
  return (
    <Scene dur={SCENES.title.dur} fadeIn={8}>
      <div style={{...label, top: 150, height: 780, display: 'flex', flexDirection: 'column', ...wipe(f, 2, 22)}}>
        <div style={{flex: 1, padding: '0 72px', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
          <h1 style={{margin: '0 0 0 -8px', ...caps(340, 800, '-.01em'), lineHeight: 0.92, ...rise(f, 12, 20, 30)}}>
            Unswayed
          </h1>
          <div style={{marginTop: 26}}>
            <Tagline size={104} at={28} />
          </div>
        </div>
        <dl
          style={{
            margin: 0,
            height: 130,
            flex: 'none',
            borderTop: `3px solid ${C.ink}`,
            display: 'grid',
            gridTemplateColumns: 'auto 1fr max-content',
            ...rise(f, 46, 16, 0),
          }}
        >
          {[
            ['What it is', 'A description-blind security gate'],
            ['Where it sits', 'In front of an AI code reviewer'],
          ].map(([k, v], i) => (
            <div
              key={k}
              style={{
                borderLeft: i ? `3px solid ${C.ink}` : undefined,
                padding: '0 40px 0 ' + (i ? '40px' : '72px'),
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <dt style={caps(26, 600, '.06em')}>{k}</dt>
              <dd style={{margin: 0, ...caps(46, 800, '.01em'), whiteSpace: 'nowrap'}}>{v}</dd>
            </div>
          ))}
          <div
            style={{
              background: C.caution,
              borderLeft: `3px solid ${C.ink}`,
              padding: '0 44px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            <strong style={{...caps(40, 800, '.03em'), whiteSpace: 'nowrap'}}>Recorded runs</strong>
            <span style={{...caps(28, 600, '.03em'), whiteSpace: 'nowrap'}}>Real model output</span>
          </div>
        </dl>
      </div>
    </Scene>
  );
};

/* ================= 2 + 3. The pull request, then the AI reviewer ================= */
const HEAD_TOP = 36;
const headPos: CSSProperties = {position: 'absolute', left: PAD_X, top: HEAD_TOP, whiteSpace: 'nowrap'};

const Band: FC<{bg: string; color: string; at: number; children: ReactNode}> = ({bg, color, at, children}) => {
  const f = useCurrentFrame();
  const p = ramp(f, at, 20);
  return (
    <section
      style={{
        position: 'absolute',
        left: PAD_X,
        width: INNER,
        top: PR.bandTop,
        height: PR.bandH,
        boxSizing: 'border-box',
        background: bg,
        color,
        borderRadius: 3,
        padding: '22px 32px 26px',
        display: 'flex',
        flexDirection: 'column',
        opacity: p,
        transform: `translateY(${(1 - p) * 44}px)`,
      }}
    >
      {children}
    </section>
  );
};

const BandHead: FC<{title: ReactNode; sees: ReactNode}> = ({title, sees}) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      gap: 40,
      paddingBottom: 14,
      marginBottom: 20,
      borderBottom: '3px dashed currentColor',
      flex: 'none',
    }}
  >
    <h3 style={{margin: 0, ...caps(54, 800, '.005em'), whiteSpace: 'nowrap'}}>{title}</h3>
    <p style={{margin: 0, ...caps(29, 600, '.03em'), whiteSpace: 'nowrap'}}>{sees}</p>
  </div>
);

const asIs: CSSProperties = {textTransform: 'none'};

export const PRScene: FC = () => {
  const f = useCurrentFrame();
  const T3 = 270; // storyboard scene 3 starts here (13 s)
  const c = ramp(f, T3, 26);
  const h = PR.tall + (PR.compact - PR.tall) * c;
  const tallOnly = 1 - ramp(f, T3 - 6, 12);
  const r = S.reviewer;
  return (
    <Scene dur={SCENES.pr.dur}>
      <Headline style={{...headPos, ...rise(f, 4), opacity: ramp(f, 4, 16) * (1 - linear(f, T3 - 8, 8))}}>
        The second pair of eyes is now an AI.
      </Headline>
      <Headline style={{...headPos, ...rise(f, T3)}}>
        The AI reviewer reads both.
      </Headline>

      <StoryPanel height={h} maxChars={596} more={c} style={rise(f, 16, 18, 26)} />
      <DiffPanel
        height={h}
        hl={ramp(f, 84, 20)}
        callout={ramp(f, 104, 18) * tallOnly}
        fields={ramp(f, 40, 16) * tallOnly}
        style={rise(f, 28, 18, 26)}
      />

      <Band bg={C.story} color={C.ink} at={T3 + 12}>
        <BandHead
          title={
            <>
              AI reviewer: <span style={asIs}>{D.reviewer}</span>
            </>
          }
          sees="Receives the title, the description and the diff"
        />
        <div style={{display: 'grid', gridTemplateColumns: '650px 1fr', gap: 36, flex: 1, minHeight: 0}}>
          <div style={{paddingTop: 22, paddingLeft: 14}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 34}}>
              <Stamp word={r.approved ? 'Approved' : 'Rejected'} icon={r.approved ? Icon.tick : Icon.block} size={84} at={T3 + 62} />
            </div>
            <p style={{margin: '34px 0 0', ...caps(50, 800, '.02em'), ...rise(f, T3 + 72)}}>
              {r.passes} of {r.runs} runs
            </p>
            <div style={{marginTop: 16, ...rise(f, T3 + 150)}}>
              <Flag size={33}>
                Reverts the fix for <span style={asIs}>{S.vuln}</span>
              </Flag>
            </div>
          </div>
          <div
            style={{
              background: C.stock,
              borderRadius: 3,
              padding: '20px 30px 24px',
              alignSelf: 'start',
              ...rise(f, T3 + 86),
            }}
          >
            <p style={{margin: '0 0 10px', ...caps(26, 600, '.06em')}}>Its recorded reason</p>
            <p style={{margin: 0, fontFamily: F.text, fontSize: 36, lineHeight: 1.34}}>
              “<Inline text={r.reason} />”
            </p>
          </div>
        </div>
      </Band>
    </Scene>
  );
};

/* ================= 4. Big number ================= */
export const BigNumberScene: FC = () => {
  const f = useCurrentFrame();
  const m = R.malicious;
  return (
    <Scene dur={SCENES.bigNumber.dur}>
      <div style={{position: 'absolute', left: PAD_X, top: 196, width: INNER, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between'}}>
        <Count n={m.approved_alone} total={m.total} size={430} style={rise(f, 2)} />
        <div style={{paddingBottom: 14}}>
          <Cells total={m.total} on={m.approved_alone} cols={18} size={44} gap={8} color={C.story} at={8} stagger={0.8} />
        </div>
      </div>
      <Headline size={122} style={{position: 'absolute', left: PAD_X, top: 640, whiteSpace: 'nowrap', ...rise(f, 20)}}>
        malicious pull requests approved
      </Headline>
      <p style={{position: 'absolute', left: PAD_X, top: 800, margin: 0, fontFamily: F.text, fontSize: 48, lineHeight: 1.3, ...rise(f, 36)}}>
        {D.benchmark} subset, {D.reviewer} reviewer
      </p>
    </Scene>
  );
};

/* ================= 5. Unswayed steps in front ================= */
const sealLines = (S.title + '\n' + S.body).split('\n').filter((l) => l.trim());

export const GateScene: FC = () => {
  const f = useCurrentFrame();
  const g = S.gate;
  const votes = g.votes.filter((v) => v === g.effect).length;
  const weak = g.effect === 'WEAKENS';
  const seal = ramp(f, 20, 24);
  const tag = ramp(f, 50, 14);
  const FIND = [84, 108, 132];
  return (
    <Scene dur={SCENES.gate.dur}>
      <Headline style={{...headPos, ...rise(f, 4)}}>Unswayed steps in front.</Headline>

      <StoryPanel height={PR.compact} maxChars={596} more={1} note={f < 44 ? 'What the author wrote' : 'Sealed from the gate'}>
        {/* The sealed well: the description is covered before the gate runs. */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: C.blindDeep,
            clipPath: `inset(0 ${(1 - seal) * 100}% 0 0)`,
          }}
        >
          <div style={{position: 'absolute', inset: 10, border: `3px dashed ${C.blindTint}`}} />
          <div style={{position: 'absolute', inset: '34px 38px', display: 'grid', gap: 15, alignContent: 'start'}}>
            {sealLines.slice(0, 8).map((l, i) => (
              <i
                key={i}
                style={{
                  display: 'block',
                  height: 21,
                  background: C.sealedBar,
                  width: Math.max(22, Math.min(100, Math.round(l.length * 1.15))) + '%',
                  clipPath: `inset(0 ${(1 - ramp(f, 30 + i * 2, 18)) * 100}% 0 0)`,
                }}
              />
            ))}
          </div>
          <div style={{position: 'absolute', inset: 0, display: 'grid', placeItems: 'center'}}>
            <Flag
              size={76}
              style={{
                opacity: f < 50 ? 0 : Math.min(1, tag * 1.6),
                transform: `rotate(${-9 + 6 * tag}deg) scale(${1.6 - 0.6 * tag})`,
              }}
            >
              <span style={{fontSize: 66, display: 'flex'}}>{Icon.seal}</span>Never read
            </Flag>
          </div>
        </div>
      </StoryPanel>
      <DiffPanel height={PR.compact} hl={1} note="All the gate receives" />

      <Band bg={C.blind} color="#fff" at={56}>
        <BandHead title="Unswayed gate" sees="One question: does this change weaken an existing safeguard?" />
        <div style={{display: 'grid', gridTemplateColumns: '1fr 590px', gap: 44, flex: 1, minHeight: 0}}>
          <ul style={{listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 13, alignContent: 'start'}}>
            {g.findings.slice(0, 3).map((t, i) => (
              <li
                key={i}
                style={{
                  position: 'relative',
                  paddingLeft: 34,
                  fontFamily: F.text,
                  fontSize: 30,
                  lineHeight: 1.32,
                  ...rise(f, FIND[i]),
                }}
              >
                <i style={{position: 'absolute', left: 0, top: '0.6em', width: 18, height: 4, background: '#fff'}} />
                <Inline text={t} codeStyle={{background: C.blindDeep, padding: '0 .25em'}} />
              </li>
            ))}
          </ul>
          <div style={{paddingTop: 12}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 30, paddingLeft: 10}}>
              <Stamp word={g.effect} icon={weak ? Icon.weakens : Icon.tick} size={72} at={166} />
              <p style={{margin: 0, ...caps(40, 800, '.02em'), lineHeight: 1.05, ...rise(f, 176)}}>
                {votes} of {g.votes.length}
                <br />
                votes
              </p>
            </div>
            <div style={{marginTop: 34, ...rise(f, 196)}}>
              <Flag size={54}>
                <span style={{fontSize: 50, display: 'flex'}}>{Icon.block}</span>Blocked
              </Flag>
              <p style={{margin: '12px 0 0', fontFamily: F.text, fontWeight: 600, fontSize: 31, lineHeight: 1.3}}>
                until a person acknowledges it. The override is logged.
              </p>
            </div>
          </div>
        </div>
      </Band>
    </Scene>
  );
};

/* ================= 6. Before / after ================= */
const PackLabel: FC<{children: ReactNode; bg: string; color: string; size?: number}> = ({children, bg, color, size = 32}) => (
  <span
    style={{
      display: 'inline-block',
      background: bg,
      color,
      ...caps(size, 800, '.03em'),
      padding: `${size * 0.28}px ${size * 0.42}px ${size * 0.24}px`,
      whiteSpace: 'nowrap',
    }}
  >
    {children}
  </span>
);

export const BeforeAfterScene: FC = () => {
  const f = useCurrentFrame();
  const m = R.malicious;
  const b = R.benign;
  // The second pack starts as the reviewer's own cells and drains to the gated count.
  // Only the cells move: the numeral appears once, at its recorded value, so no frame shows an unreal number.
  const drain = interpolate(f, [62, 100], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE});
  const cellsNow = Math.round(m.approved_alone + (m.approved_gated - m.approved_alone) * drain);
  const secTitle: CSSProperties = {margin: '0 0 30px', ...caps(50, 800, '.01em'), whiteSpace: 'nowrap'};
  const arrow: CSSProperties = {fontSize: 84, display: 'flex', alignSelf: 'center', color: C.ink};
  return (
    <Scene dur={SCENES.beforeAfter.dur}>
      <Headline style={{...headPos, ...rise(f, 4)}}>Same reviewer, with Unswayed in front</Headline>

      <div style={{...label, top: 150, height: 640, display: 'grid', gridTemplateColumns: '1062px 1fr', ...rise(f, 10, 18, 26)}}>
        <section style={{padding: '34px 30px 0 36px'}}>
          <h3 style={secTitle}>Malicious pull requests approved</h3>
          <div style={{display: 'flex', justifyContent: 'space-between'}}>
            <div style={rise(f, 20)}>
              <PackLabel bg={C.story} color={C.ink} size={30}>Reviewer alone</PackLabel>
              <Count n={m.approved_alone} total={m.total} size={220} style={{margin: '40px 0 34px'}} />
              <Cells total={m.total} on={m.approved_alone} cols={18} size={20} gap={4} color={C.story} at={24} stagger={0.25} />
            </div>
            <span style={{...arrow, ...rise(f, 50, 14, 0)}}>{Icon.arrowRight}</span>
            <div style={rise(f, 54)}>
              <PackLabel bg={C.blind} color="#fff" size={30}>With Unswayed in front</PackLabel>
              <Count n={m.approved_gated} total={m.total} size={220} style={{margin: '40px 0 34px', ...rise(f, 98)}} />
              <Cells total={m.total} on={cellsNow} cols={18} size={20} gap={4} color={C.story} at={-100} stagger={0} />
            </div>
          </div>
        </section>
        <section style={{padding: '34px 36px 0 40px', borderLeft: `3px dashed ${C.ink}`, ...rise(f, 116, 16, 0)}}>
          <h3 style={secTitle}>Legitimate fixes approved</h3>
          <div style={{display: 'flex', justifyContent: 'space-between'}}>
            <div>
              <PackLabel bg={C.story} color={C.ink} size={30}>Reviewer alone</PackLabel>
              <Count n={b.approved_alone} total={b.total} size={150} style={{margin: '74px 0 34px'}} />
              <Cells total={b.total} on={b.approved_alone} cols={10} size={22} gap={4} color={C.ink} at={122} stagger={0.4} />
            </div>
            <span style={{...arrow, fontSize: 64}}>{Icon.arrowRight}</span>
            <div>
              <PackLabel bg={C.blind} color="#fff" size={30}>With Unswayed</PackLabel>
              <Count n={b.approved_gated} total={b.total} size={150} style={{margin: '74px 0 34px'}} />
              <Cells total={b.total} on={b.approved_gated} cols={10} size={22} gap={4} color={C.ink} at={132} stagger={0.4} />
            </div>
          </div>
          {b.approved_alone === b.approved_gated ? (
            <div style={{marginTop: 40, ...rise(f, 146)}}>
              <PackLabel bg={C.ink} color={C.stock} size={38}>
                <span style={{display: 'inline-flex', alignItems: 'center', gap: 14}}>
                  <span style={{fontSize: 34, display: 'flex'}}>{Icon.equal}</span>Unchanged
                </span>
              </PackLabel>
            </div>
          ) : null}
        </section>
      </div>

      <div
        style={{
          ...label,
          top: 812,
          height: 112,
          display: 'flex',
          alignItems: 'center',
          gap: 34,
          padding: '0 40px',
          ...rise(f, 160),
        }}
      >
        <p style={{margin: 0, ...caps(28, 600, '.05em'), lineHeight: 1.1}}>
          Second
          <br />
          reviewer
        </p>
        <p style={{margin: 0, ...caps(50, 800, '.01em'), ...asIs, whiteSpace: 'nowrap'}}>{O.name}</p>
        <i style={{width: 3, alignSelf: 'stretch', background: C.ink}} />
        <p style={{margin: 0, ...caps(42, 800, '.01em'), whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 16}}>
          Malicious approved {O.malicious.approved_alone}
          <span style={{fontSize: 40, display: 'flex'}}>{Icon.arrowRight}</span>
          {O.malicious.approved_gated} of {O.malicious.total}
        </p>
        <i style={{width: 3, alignSelf: 'stretch', background: C.ink}} />
        <p style={{margin: 0, ...caps(42, 800, '.01em'), whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 16}}>
          Legitimate {O.benign.approved_alone}
          <span style={{fontSize: 40, display: 'flex'}}>{Icon.arrowRight}</span>
          {O.benign.approved_gated} of {O.benign.total}
        </p>
      </div>

      <p style={{position: 'absolute', left: PAD_X, top: 952, margin: 0, fontFamily: F.text, fontSize: 32, ...rise(f, 170)}}>
        {D.benchmark} subset, {R.name} reviewer. Recorded real model runs, {D.recorded}.
      </p>
    </Scene>
  );
};

/* ================= 7. The cost ================= */
/* PRODUCT.md, Evidence on Hand: the Opus figure is a single pass. */
const ORDINARY_NOTE: Record<string, string> = {'Claude Opus 5.5': 'asks the gate question, single pass'};

export const CostScene: FC = () => {
  const f = useCurrentFrame();
  const o = D.stats.ordinary;
  return (
    <Scene dur={SCENES.cost.dur}>
      <Headline style={{...headPos, ...rise(f, 4)}}>The cost, stated next to the benefit</Headline>

      <div style={{...label, top: 150, padding: '28px 40px 14px', ...rise(f, 10, 18, 26)}}>
        <h3 style={{margin: '0 0 8px', ...caps(54, 800, '.01em'), whiteSpace: 'nowrap'}}>
          False alarms on {o[0].total} ordinary commits from the same repositories
        </h3>
        {o.map((x, i) => (
          <div
            key={x.name}
            style={{
              display: 'grid',
              gridTemplateColumns: '410px 320px 200px 1fr',
              alignItems: 'center',
              height: 164,
              borderTop: i ? `3px dashed ${C.ink}` : undefined,
              ...rise(f, 24 + i * 14),
            }}
          >
            <div>
              <p style={{margin: 0, ...caps(52, 800, '.01em'), ...asIs, whiteSpace: 'nowrap'}}>{x.name}</p>
              <p style={{margin: '8px 0 0', ...caps(25, 600, '.04em'), whiteSpace: 'nowrap'}}>
                {ORDINARY_NOTE[x.name] || 'asks the gate question'}
              </p>
            </div>
            <Count n={x.flagged} total={x.total} size={120} minDigits={2} />
            <div>
              <Flag size={84} style={{padding: '14px 22px 10px'}}>{pct(x.flagged, x.total)}%</Flag>
            </div>
            <div style={{justifySelf: 'end'}}>
              <Cells total={x.total} on={x.flagged} cols={40} size={15} gap={4} color={C.caution} at={30 + i * 14} stagger={0.5} />
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          position: 'absolute',
          left: PAD_X,
          width: INNER,
          top: 790,
          height: 180,
          boxSizing: 'border-box',
          border: `4px dashed ${C.ink}`,
          display: 'flex',
          alignItems: 'center',
          gap: 30,
          padding: '0 40px',
          ...rise(f, 96),
        }}
      >
        <PackLabel bg={C.ink} color={C.stock} size={50}>We attacked our own gate</PackLabel>
        <p style={{margin: 0, ...caps(84, 800, '.005em'), whiteSpace: 'nowrap'}}>best attack evades 8 of 24.</p>
      </div>
    </Scene>
  );
};

/* ================= 8. End card ================= */
export const EndScene: FC = () => {
  const f = useCurrentFrame();
  return (
    <Scene dur={SCENES.end.dur} fadeOut={0}>
      <div style={{...label, top: 110, height: 860, display: 'flex', flexDirection: 'column', ...rise(f, 2, 16, 0)}}>
        <div style={{padding: '50px 72px 44px', borderBottom: `3px solid ${C.ink}`, flex: 'none'}}>
          <p style={{margin: 0, ...caps(92, 800, '.005em'), whiteSpace: 'nowrap', ...rise(f, 8)}}>
            Runs as a pre-commit hook or CI check.
          </p>
          <p style={{margin: '18px 0 0', ...caps(92, 800, '.005em'), whiteSpace: 'nowrap', ...rise(f, 22)}}>
            Your models, your infrastructure.
          </p>
        </div>
        <div style={{flex: 1, padding: '0 72px', display: 'flex', flexDirection: 'column', justifyContent: 'center'}}>
          <h1 style={{margin: '0 0 0 -6px', ...caps(300, 800, '-.01em'), lineHeight: 0.92, ...rise(f, 48, 20, 26)}}>Unswayed</h1>
          <div style={{marginTop: 18}}>
            <Tagline size={84} at={60} />
          </div>
        </div>
        <p
          style={{
            margin: 0,
            flex: 'none',
            borderTop: `3px solid ${C.ink}`,
            padding: '16px 72px 18px',
            fontFamily: F.text,
            fontSize: 28,
            lineHeight: 1.2,
            ...rise(f, 76, 16, 0),
          }}
        >
          Recorded real model runs, {D.recorded}.
        </p>
      </div>
    </Scene>
  );
};

export {TAGLINE};
