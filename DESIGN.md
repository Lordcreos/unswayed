---
name: Unswayed
description: Judge the diff, not the story. A blinded-trial console for a description-blind security gate.
colors:
  story-vermilion: "#ff5a36"
  blind-ultramarine: "#1746e0"
  blind-deep: "#0c2a94"
  blind-tint: "#d9e3ff"
  caution-yellow: "#ffd400"
  ink-navy: "#0d1b2a"
  label-stock: "#ffffff"
  cool-paper: "#f3f6f9"
  added-line: "#e2e8f1"
  rule-hairline: "rgba(13, 27, 42, .22)"
typography:
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "4.5rem"
    fontWeight: 800
    lineHeight: 1.28
    letterSpacing: "-.01em"
  headline:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "2.9rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: ".005em"
  numeral:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "3.3rem"
    fontWeight: 800
    lineHeight: 1
  title:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "1.9rem"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: ".01em"
  label:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: ".03em"
  label-small:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: ".06em"
  body:
    fontFamily: "Barlow, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 400
    lineHeight: 1.42
  code:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "1.1rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  label: ".14rem"
  stamp: ".4rem"
  blister: "28%"
spacing:
  gutter: "1rem"
  panel: "1rem 1.3rem"
  section: "2rem"
  tight: ".5rem"
components:
  control-button:
    backgroundColor: "{colors.label-stock}"
    textColor: "{colors.ink-navy}"
    typography: "{typography.label-small}"
    rounded: "{rounded.label}"
    padding: ".25rem .8rem"
  control-button-hover:
    backgroundColor: "{colors.ink-navy}"
    textColor: "{colors.label-stock}"
  arm-story:
    backgroundColor: "{colors.story-vermilion}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.label}"
    padding: "{spacing.panel}"
  arm-blind:
    backgroundColor: "{colors.blind-ultramarine}"
    textColor: "{colors.label-stock}"
    rounded: "{rounded.label}"
    padding: "{spacing.panel}"
  specimen-panel:
    backgroundColor: "{colors.label-stock}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.label}"
    padding: "{spacing.panel}"
  caution-flag:
    backgroundColor: "{colors.caution-yellow}"
    textColor: "{colors.ink-navy}"
    padding: ".4rem .6rem"
  verdict-stamp:
    typography: "{typography.headline}"
    rounded: "{rounded.stamp}"
    padding: ".55rem .95rem .5rem"
  blister-cell:
    rounded: "{rounded.blister}"
---

# Design System: Unswayed

## Overview

**Creative North Star: "The Trial-Kit Label"**

Unswayed is drawn as the paperwork of a two-arm blinded trial, not as a security dashboard. Everything sits on cool white label stock framed in navy ink: a kit header with labelled fields, two arm panels in opposed solid fields, a specimen panel for the evidence between them, and a counted outcome strip of blister packs. The surface is printed matter. It is flat, dense, upper-case where it names things and sentence-case where it is read, and it is built to be legible from the back of a projected room.

The world has exactly two loud colours and they belong to the two arms of the trial: vermilion for the arm that reads the author's story, ultramarine for the arm that is blinded. Caution yellow is a label colour, applied in patches to whatever the room must look at. Verdicts arrive as rubber stamps, the withheld description as sealed bars, and the result as one cell per pull request so the count can be seen rather than trusted. The refused alternative is the dark SOC console of status chips and glowing badges.

The layout is a fixed 16:9 instrument: the root font size scales with the viewport so the whole console fits one projected screen without scrolling the page, and a presenter steps through it from the keyboard.

**Key Characteristics:**
- Cool white paper, white label stock, navy ink frames; no shadows.
- Two arm fields (vermilion, ultramarine) that carry meaning, never decoration.
- Caution yellow as small label patches: flags, the sealed tag, the removed line, focus.
- Barlow Condensed caps for structure, Barlow for reading, monospace for code.
- Rubber-stamp verdicts with word and pictogram; blister-pack unit grids for counts.
- Viewport-locked rem scale for projection; stacks and scrolls below 900px or in portrait.

## Colors

A cool, printed palette: two opposed saturated arm fields and one caution yellow on navy-and-white label stock.

### Primary
- **Story Vermilion** (story-vermilion): the field of Arm A, the reviewer that reads the title and description. Also the route bar "sent with the story" and the filled blister cells counting approvals of reintroduced CVEs. Navy ink sits on it.

### Secondary
- **Blinded Ultramarine** (blind-ultramarine): the field of Arm B, the gate that sees only the diff, and its route bar "sent sealed". White text sits on it.
- **Sealed Deep Ultramarine** (blind-deep): the sealed-description well inside Arm B and the code highlight inside its findings; the darker interior of the blinded field.
- **Ultramarine Tint** (blind-tint): the dashed perforation around the sealed well and secondary mono text (the raw gate output line) on ultramarine.

### Tertiary
- **Caution Yellow** (caution-yellow): label patches only. The "recorded run" block in the kit header, the flag that names the reverted fix, the sealed tag, the removed lines in the diff, the "missed" contents field once revealed, the false-alarm blister cells, and the focus ring.

### Neutral
- **Navy Ink** (ink-navy): all text on light grounds, every frame and divider, the file and hunk bars of the diff, the "legitimate fix" contents field, and filled cells counting legitimate approvals.
- **Label Stock** (label-stock): the face of the kit header, the specimen panel, the description card in Arm A, the outcome strip and the controls.
- **Cool Paper** (cool-paper): the page ground showing in the gutters between labels.
- **Added Line Grey** (added-line): background of added lines in the diff; deliberately quiet so the removal reads first.
- **Rule Hairline** (rule-hairline): the thin frame around the diff and field dividers in the stacked layout.

### Named Rules
**The Two Arms Rule.** Vermilion means "read the story" and ultramarine means "blinded". Each appears only on its own arm, its route bar, and the counts that arm produced. Neither is ever used as a generic accent, link colour or status colour.

**The Caution Label Rule.** Yellow is a label, not a field. It is applied in patches small enough to read as stickers on the stock, and it marks what the room must look at: the harmful removed line, the reverted fix, the seal, the miss, the cost.

**The Removal Is The Danger Rule.** Diff lines are not coloured red and green. Removed lines take caution yellow with bold weight; added lines take a quiet grey; file and hunk headers are ink bars.

## Typography

**Display Font:** Barlow Condensed (with Arial Narrow, sans-serif)
**Body Font:** Barlow (with Helvetica Neue, Arial, sans-serif)
**Label/Mono Font:** system monospace (ui-monospace, SF Mono, Menlo, Consolas)

**Character:** Barlow Condensed in heavy caps is the voice of the printed label: dense, industrial, readable across a room. Barlow, its own humanist sibling, carries the sentences that are actually read: descriptions, model reasons and findings. Both are embedded so the console renders offline.

### Hierarchy
- **Display** (800, 4.5rem, 1.28, caps): the product name in the kit header only.
- **Headline** (800, 2.9rem, 1, caps): arm and specimen headings. Stamps use the same weight at 2.8rem with .04em tracking.
- **Numeral** (800, 3.3rem, 1): blister-pack counts, with a 600-weight caps "of N" suffix at 1.35rem; 2.3rem in compact rows.
- **Title** (800, 1.9rem, 1.05, caps): outcome section headings; kit field values at 1.95rem.
- **Label** (600, 1.3 to 1.45rem, .02 to .03em, caps): arm intake lines, route bars, pack labels, verdict run counts.
- **Label Small** (600, 1.05rem, .06em, caps): kit field names, the "continues" cue, control buttons (1.15rem).
- **Body** (400, 1.5rem, 1.42): description text, model reasons (1.4rem), gate findings. Sentence case.
- **Code** (400, 1.1rem default, 1.5): file paths and diffs. Diff size scales from 1rem up to 1.75rem as the diff gets shorter, so short diffs read from the back of the room.

### Named Rules
**The Caps Name, Sentences Read Rule.** Anything that names, labels, counts or rules is Barlow Condensed caps. Anything the audience reads as an argument (the author's description, the reviewer's reason, the gate's finding) is Barlow in sentence case. The pull request title is the one condensed line in sentence case (600, 1.95rem) because it is the author's own words.

**The Room Scale Rule.** Type is sized in rem on a root of `clamp(9px, min(.833vw, 1.48vh), 24px)`; nothing on the projected surface is sized in fixed pixels.

## Layout

A four-row viewport grid locked to the screen: kit header (6rem), the trial (remaining height), the outcome strip (14.4rem), the footer (2.4rem), with a 1rem gap and 1.2rem by 1.6rem page padding. The page itself never scrolls at 16:9; long descriptions and diffs scroll inside their panels with a fade mask and an ink "continues" cue that appears only while content remains below.

The trial row is three columns in proportion 33 / 35 / 32: Arm A on the left, the specimen in the centre, Arm B on the right, separated by the 1rem gutter. The route bars inside the specimen bleed outward across the gutters into both arms, physically connecting the one change to the two arms it was sent to. The outcome strip is three sections in proportion 43 / 27 / 30, divided by dashed ink perforations with 2rem of space on each side.

Panels use 1rem by 1.3rem internal padding; stacked items inside them sit .5 to .85rem apart. Below 900px wide, or in any portrait aspect, the root drops to 12px, the page scrolls, every grid collapses to one column, panel scrollers take a fixed 26rem height, and the outcome perforations turn horizontal.

## Elevation & Depth

Flat. There are no shadows anywhere. Depth is conveyed the way printed labels convey it: ink frames (.16rem) around stock panels, solid colour fields for the arms, a darker inset well for the sealed description, and ink bars inside the diff. The only element that leaves the flat plane is the verdict stamp, which is rotated by -4deg as if pressed by hand.

### Named Rules
**The Printed Matter Rule.** Separation comes from ink frames, solid fields and dashed perforations, never from shadows, glows or blur at rest.

## Shapes

Near-square corners (.14rem) on every label, panel and button, so they read as die-cut stock. The stamp is the softer exception (.4rem) with a doubled border: a .3rem outer border plus an inset .12rem outline, the classic rubber-stamp ring. Blister cells are squares with 28% corner rounding and a thin ink outline. Dashed lines mean perforation or division: under the arm intake line, around the sealed well, between outcome sections, and around pending verdict slots. The arm codes "A" and "B" sit in square ink-bordered boxes the height of the headline.

## Components

### Buttons
Quiet label-stock keys; the presenter uses the keyboard and the buttons are the fallback.
- **Shape:** near-square corners (.14rem) with a .14rem ink border.
- **Primary:** stock face, ink text, Label Small caps at 1.15rem, padding .25rem .8rem; the key binding follows in monospace.
- **Hover / Focus:** hover inverts to ink face with stock text; focus is a .22rem caution-yellow outline offset .15rem (global).
- **Disabled:** 35% opacity, no hover inversion.

### Kit Header
The trial-kit label. A stock strip in a .16rem ink frame: the product name and tagline, then a row of labelled fields (Sample, Contents, Lot, Class, Source) separated by ink rules, each with a small caps field name over a heavy caps value, and a caution-yellow "recorded run" block at the end. The Contents field turns ink for a legitimate fix and caution yellow for a revealed miss.

### Arm Panels
Solid colour fields, one per arm. Headline with the boxed arm code, a caps intake line stating exactly what that arm receives, a dashed rule, then the arm's evidence and its verdict slot. Arm A holds a stock description card; Arm B holds the sealed well and the findings list, whose bullets are short white dashes.

### Specimen Panel
Stock with an ink frame: the change between the arms. Mono file paths, the two route bars (vermilion pointing left, ultramarine pointing right, each with an SVG arrow), then the diff in a hairline frame.

### Verdict Stamp (signature)
The verdict is a rubber stamp in the arm's ink colour: heavy caps word plus an SVG pictogram (circle tick for approved, octagon bar for blocked, arrow for passed on, circle exclamation for not flagged), rotated -4deg with a double ring. Beside it, a caps line with the run count; below, the model's reason or the consequence. Before the verdict lands, the slot shows a dashed "awaiting" frame of the same height so the layout does not jump. It lands with a scale-down from 1.7x, -13deg and a blur, over .5s on cubic-bezier(.16, 1, .3, 1).

### Sealed Bars (signature)
The withheld description, drawn as solid deep bars whose widths follow the real line lengths, inside a deep-ultramarine well with a dashed tint perforation, tagged by a caution-yellow seal label with a padlock pictogram stating how many characters were never shown. The bars draw left to right in a 38ms stagger.

### Blister Packs (signature)
One cell per pull request or commit, filled for the ones counted, empty and outlined for the rest, so the denominator is always visible. Fill colour says whose count it is: vermilion for malicious changes approved, ink for legitimate fixes approved, caution yellow for false alarms. Counts appear as a heavy numeral with "of N"; cells pop in with a 9ms stagger once the outcome is counted.

### Caution Flag
A caution-yellow patch with heavy caps ink text (1.25rem, padding .4rem .6rem), used to name the consequence the reviewer missed, for example the fix it reverts.

## Do's and Don'ts

### Do:
- **Do** give every verdict a word and a pictogram on the stamp; colour alone never carries a verdict.
- **Do** show every count as a blister pack with its total, and put the cost (legitimate approvals, false alarms) in the same strip as the benefit.
- **Do** keep vermilion and ultramarine bound to their arms and to the counts each arm produced.
- **Do** frame stock panels with a .16rem navy ink border and near-square .14rem corners.
- **Do** use dashed ink or tint lines for perforations and divisions, and solid ink for frames.
- **Do** size everything in rem on the viewport-locked root so the console fits one 16:9 projected screen.
- **Do** wrap motion in `prefers-reduced-motion: no-preference`, and reserve a pending frame of the final size before content lands.

### Don't:
- **Don't** build a dark SOC dashboard of status chips, glowing badges or traffic-light pills.
- **Don't** use shadows, glows or blur at rest; this is printed label stock.
- **Don't** colour diffs red and green; removal is caution yellow, addition is quiet grey.
- **Don't** spread caution yellow into a full field or background; it stays a label patch.
- **Don't** introduce a third saturated hue or use either arm colour as a generic accent.
- **Don't** set reading text (descriptions, reasons, findings) in condensed caps.
