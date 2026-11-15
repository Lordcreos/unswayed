import type {FC} from 'react';
import {AbsoluteFill, Composition, Sequence} from 'remotion';
import './fonts';
import {BeforeAfterScene, BigNumberScene, CostScene, EndScene, GateScene, PRScene, TitleScene} from './scenes';
import {C, F, FPS, H, SCENES, TOTAL_FRAMES, W} from './theme';

const Demo: FC = () => (
  <AbsoluteFill style={{background: C.paper, color: C.ink, fontFamily: F.text}}>
    <Sequence from={SCENES.title.from} durationInFrames={SCENES.title.dur} name="1 Title">
      <TitleScene />
    </Sequence>
    <Sequence from={SCENES.pr.from} durationInFrames={SCENES.pr.dur} name="2-3 Pull request and reviewer">
      <PRScene />
    </Sequence>
    <Sequence from={SCENES.bigNumber.from} durationInFrames={SCENES.bigNumber.dur} name="4 Big number">
      <BigNumberScene />
    </Sequence>
    <Sequence from={SCENES.gate.from} durationInFrames={SCENES.gate.dur} name="5 Gate">
      <GateScene />
    </Sequence>
    <Sequence from={SCENES.beforeAfter.from} durationInFrames={SCENES.beforeAfter.dur} name="6 Before and after">
      <BeforeAfterScene />
    </Sequence>
    <Sequence from={SCENES.cost.from} durationInFrames={SCENES.cost.dur} name="7 Cost">
      <CostScene />
    </Sequence>
    <Sequence from={SCENES.end.from} durationInFrames={SCENES.end.dur} name="8 End card">
      <EndScene />
    </Sequence>
  </AbsoluteFill>
);

export const Root: FC = () => (
  <Composition id="UnswayedDemo" component={Demo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={W} height={H} />
);
