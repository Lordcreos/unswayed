# Data

Everything here comes from public sources and is kept so the numbers in the main README can be reproduced without network access.

| Folder | What it is | Source and licence |
| --- | --- | --- |
| `sevra/` | Pull request titles and descriptions of SEVRA-Bench | [RedAI4Code/SEVRA](https://huggingface.co/datasets/RedAI4Code/SEVRA), MIT. Its own README and licence are in the folder |
| `patches/` | The official fix commit of each vulnerability, as a diff | Fetched from each upstream project on GitHub by `experiments/fetch_patches.py`. Each diff remains under its project's licence |
| `ordinary/` | Ordinary commits from the same projects, used to count false alarms | Fetched by `experiments/fetch_ordinary.py`. Each diff remains under its project's licence |

The malicious pull requests of the benchmark are these fix commits applied in reverse: they reintroduce a known, already public vulnerability. Nothing here is a new exploit.
