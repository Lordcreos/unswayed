import {loadFont} from '@remotion/fonts';
import {continueRender, delayRender, staticFile} from 'remotion';

// Local copies of demo/fonts/*.ttf (SIL OFL, see public/fonts/OFL.txt). No network fonts.
const faces: Array<{family: string; file: string; weight: string}> = [
  {family: 'Barlow', file: 'Barlow-Regular.ttf', weight: '400'},
  {family: 'Barlow', file: 'Barlow-SemiBold.ttf', weight: '600'},
  {family: 'Barlow Condensed', file: 'BarlowCondensed-SemiBold.ttf', weight: '600'},
  {family: 'Barlow Condensed', file: 'BarlowCondensed-ExtraBold.ttf', weight: '800'},
];

const handle = delayRender('Loading Barlow fonts');
Promise.all(
  faces.map((f) =>
    loadFont({family: f.family, url: staticFile('fonts/' + f.file), weight: f.weight, style: 'normal'}),
  ),
)
  .then(() => continueRender(handle))
  .catch((err) => {
    throw err;
  });
