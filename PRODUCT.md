# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS, one file that opens from disk with no server and no network (confirmed by the user). The gate itself is a Python standard-library CLI.

## Users

- **Engineering teams that let an AI reviewer approve code**, often code written by another AI, as a pre-commit hook or CI gate. They install the gate in a repository and meet it when a commit is blocked.
- **Security leaders evaluating it** (the first audience is a hackathon jury of CISOs and security researchers in Berlin, 14 Nov 2026). They see it projected for three minutes and judge novelty, impact and enterprise relevance.

## Product Purpose

Unswayed is a security gate that sits in front of an AI code reviewer. Before the normal reviewer reads a change with its description, a separate pass sees only the diff and answers one narrow question: does this change weaken an existing safeguard? If yes, the merge is blocked until a person acknowledges it with a reason, which is logged. Success means a persuasive description can no longer talk an AI reviewer into approving a reintroduced vulnerability, without making the reviewer reject legitimate work.

## Positioning

The four-eyes control fails when the second pair of eyes is an AI that reads the author's story. Unswayed keeps the full-context reviewer for the verdict and adds a description-blind check that is never asked to approve or reject, only to classify the direction of the change. Reviewing everything blind (the published defence) costs legitimate approvals; the narrow question does not.

## Operating Context

- Runs as a git pre-commit hook or in CI, chained before Gentleman Guardian Angel (`gga`) or any other reviewer command.
- Works with a Claude Code session or any OpenAI-compatible endpoint (Nebius, a local Ollama model).
- Demo setting: a laptop projected to a room; the presenter drives it; the console replays recorded real model runs and the live block is shown separately in a terminal with the git hook.

## Capabilities and Constraints

- Blocks on `WEAKENS`; passes `NEUTRAL` and `STRENGTHENS` to the normal reviewer; human acknowledgement via `UNSWAYED_ACK`; decisions logged to `.git/unswayed/log.jsonl`.
- Does not see commit messages, PR descriptions or branch names by construction.
- Shadow mode (`MODE=shadow`) logs verdicts and never holds a change; `unswayed report` summarises the log and exports CSV.
- As a pull request check (`examples/github-actions.yml`, `pull_request_target`): the gate and workflow come from the base branch, and only a maintainer who is not the author can clear a block, with `unswayed-ack: <reason>` in an approval of the exact commit. Ran on GitHub-hosted runners with a scripted model answer on 14 Nov 2026; the acknowledgement path is unit-tested only.
- Adaptive attacker, measured 14 Nov 2026 on 24 stable cases (Qwen3-235B, one sample per attack): in the default mode the best attack, a decoy hardening change elsewhere in the diff, evades 8 of 24; all six attacks evade 28 of 144. With `GRANULARITY=hunk` the same attacks evade 4 of 144, at a cost: ordinary commits flagged go from 18 to 33 of 118 and legitimate fixes flagged from 2 to 6 of 30, with 2.4 times the model calls. Not measured: an attacker adapted to hunk mode.
- The public name is Unswayed and so is the CLI (`bin/unswayed`, config `.unswayed`, `UNSWAYED_*` variables). The project folder and the module file keep the original name `revisor-ciego`; the old config file and `REVISOR_CIEGO_*` variables still work.

## Brand Commitments

- Name: **Unswayed**. Tagline: **"Judge the diff, not the story."**
- Interface language for the jury: English.
- Do not claim that regulation requires code review, and do not say open models are weak.

## Evidence on Hand

Measured on SEVRA-Bench (malicious PRs that revert real CVE fixes, wrapped in persuasive descriptions) with reconstructed diffs; raw runs in `results/`.

- Qwen3-235B as reviewer: approves 53 of 90 malicious PRs with the description, about 1% when it sees the diff alone. With the gate: 6 of 90. Legitimate security fixes approved: 24 of 30 before and after.
- gpt-oss-120b as reviewer: 19 of 90 malicious approved, 5 of 90 with the gate; legitimate 23 of 30 before and after.
- Reviewing everything blind drops legitimate approvals from 24 of 30 to 12 of 30 pull requests by majority vote (79% to 37% of individual runs), Qwen3-235B.
- Gate question answered by Claude Opus 5.5: flags 30 of 30 malicious (sample), 1 of 10 legitimate fixes.
- False alarms on 118 ordinary commits from the same repositories: 16% (gpt-oss-120b), 15% (Qwen3-235B), 4% (Opus 5.5, single pass).
- Negative result: the difference between the full and blind verdicts does not work as a detector (AUROC 0.55 to 0.59).
- No customers or deployments exist; none may be shown. Pricing exists only as a proposal (Community free, Team per active developer, Enterprise self-hosted) and must be labelled as not validated with any customer whenever it is shown.

## Product Principles

1. The check that guards against persuasion must never read the persuasion.
2. Ask the narrowest question that still catches the harm; leave the verdict to the reviewer that has context.
3. State the cost next to the benefit: every number shown comes with its false-alarm rate.
4. A person can always override, and the override is recorded.

## Accessibility & Inclusion

Must be legible when projected: readable from the back of a room, and verdicts must not depend on colour alone.
