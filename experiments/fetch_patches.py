#!/usr/bin/env python3
"""Descarga los parches oficiales (fix commits) de las vulnerabilidades de SEVRA.

SEVRA no incluye el código: cada PR malicioso es `git apply -R` del parche
oficial, y cada PR benigno es el parche aplicado tal cual. Aquí resolvemos el
commit de corrección vía OSV y bajamos su diff de GitHub.

Uso:  python3 -I experiments/fetch_patches.py <raiz_proyecto> [max_vulns]
"""
import collections
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = sys.argv[1]
MAX_VULNS = int(sys.argv[2]) if len(sys.argv) > 2 else 70
SEVRA = os.path.join(ROOT, "data", "sevra")
OUT = os.path.join(ROOT, "data", "patches")
MAX_BYTES = 9000
COMMIT_RE = re.compile(r"https://github\.com/([\w.\-]+)/([\w.\-]+)/commit/([0-9a-f]{7,40})")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "sevra-patch-fetch"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    mal, ben = [], []
    for p in glob.glob(os.path.join(SEVRA, "*", "deterministic", "*.jsonl")):
        mal += load(p)
    for p in glob.glob(os.path.join(SEVRA, "*", "benign", "gpt5.2_v2", "*.jsonl")):
        ben += load(p)
    by_vuln = collections.defaultdict(list)
    for r in mal:
        by_vuln[r["vuln_id"]].append(r)
    benign_ids = {r["vuln_id"] for r in ben}

    # Candidatas: en ambos conjuntos, pocos archivos; primero las que engañaron a Haiku.
    cands = [v for v, rs in by_vuln.items() if v in benign_ids and len(rs[0]["files_changed"]) <= 2]
    cands.sort(key=lambda v: -sum(any("haiku" in m for m in r["failed_by"]) for r in by_vuln[v]))
    cands = cands[:MAX_VULNS]

    index = {}
    for vid in cands:
        dest = os.path.join(OUT, re.sub(r"[^\w.\-]", "_", vid) + ".diff")
        entry = {"vuln_id": vid, "status": "?", "files_expected": by_vuln[vid][0]["files_changed"]}
        index[vid] = entry
        try:
            osv = json.loads(get("https://api.osv.dev/v1/vulns/" + vid))
        except (urllib.error.URLError, ValueError, TimeoutError) as exc:
            entry["status"] = "osv_error: %s" % exc
            continue
        commits = []
        for ref in osv.get("references", []):
            m = COMMIT_RE.search(ref.get("url", ""))
            if m and m.group(0) not in commits:
                commits.append(m.group(0))
        if len(commits) != 1:
            entry["status"] = "commits=%d" % len(commits)
            continue
        try:
            diff = get(commits[0] + ".diff")
        except (urllib.error.URLError, TimeoutError) as exc:
            entry["status"] = "diff_error: %s" % exc
            continue
        time.sleep(0.4)
        text = diff.decode("utf-8", errors="replace")
        files = re.findall(r"^diff --git a/(\S+) b/", text, flags=re.M)
        entry.update(commit=commits[0], bytes=len(diff), files=files)
        if len(diff) > MAX_BYTES:
            entry["status"] = "too_big"
            continue
        if "new file mode" in text or "deleted file mode" in text or "GIT binary patch" in text:
            entry["status"] = "adds_or_deletes_files"
            continue
        if set(files) != set(entry["files_expected"]):
            entry["status"] = "files_mismatch"
            continue
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        entry["status"] = "ok"
        entry["path"] = os.path.relpath(dest, ROOT)

    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
    counts = collections.Counter(e["status"].split(":")[0] for e in index.values())
    print(dict(counts))
    for vid, e in index.items():
        if e["status"] == "ok":
            print("ok", vid, e["bytes"], e["files"])


if __name__ == "__main__":
    main()
