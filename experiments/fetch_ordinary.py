#!/usr/bin/env python3
"""Descarga commits corrientes (no de seguridad) de los mismos repos que SEVRA.

Para cada parche de CVE ya descargado, lista los commits anteriores en ese
repositorio y guarda los diffs pequeños cuyo mensaje no habla de seguridad.
Sirven para medir falsas alarmas de la compuerta en código normal.

Uso:  python3 -I experiments/fetch_ordinary.py <raiz> [por_repo] [max_repos]
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = sys.argv[1]
PER_REPO = int(sys.argv[2]) if len(sys.argv) > 2 else 3
MAX_REPOS = int(sys.argv[3]) if len(sys.argv) > 3 else 35
OUT = os.path.join(ROOT, "data", "ordinary")
MAX_BYTES = 9000
SECURITY = re.compile(r"cve-|ghsa|securit|vulnerab|xss|csrf|exploit|injection|overflow", re.I)
NOISE = re.compile(
    r"(^|/)(package(-lock)?\.json|yarn\.lock|README[\w.]*|CHANGES|CHANGELOG[\w.]*|changes\.txt|pom\.xml|"
    r"[\w.\-]*\.md|[\w.\-]*\.txt|[\w.\-]*\.lock)$|\.min\.js$|\.sql$", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "ordinary-commit-fetch",
                                               "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(ROOT, "data", "patches", "index.json"), encoding="utf-8") as fh:
        patches = json.load(fh)
    index, repos = [], 0
    for vid, e in patches.items():
        if e.get("status") != "ok" or repos >= MAX_REPOS:
            continue
        m = re.match(r"https://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]+)", e["commit"])
        owner, repo, sha = m.groups()
        try:
            commits = json.loads(get("https://api.github.com/repos/%s/%s/commits?sha=%s&per_page=25"
                                     % (owner, repo, sha)))
        except (urllib.error.URLError, ValueError, TimeoutError) as exc:
            print("lista falló", owner, repo, exc)
            continue
        repos += 1
        kept = 0
        for c in commits[1:]:  # el primero es el propio parche de seguridad
            if kept >= PER_REPO:
                break
            msg = c["commit"]["message"]
            if len(c.get("parents", [])) != 1 or SECURITY.search(msg):
                continue
            try:
                diff = get("https://github.com/%s/%s/commit/%s.diff" % (owner, repo, c["sha"]))
            except (urllib.error.URLError, TimeoutError):
                continue
            time.sleep(0.4)
            text = diff.decode("utf-8", errors="replace")
            files = re.findall(r"^diff --git a/(\S+) b/", text, flags=re.M)
            if (not files or len(diff) > MAX_BYTES or len(diff) < 300 or "GIT binary patch" in text
                    or "new file mode" in text or "deleted file mode" in text
                    or all(NOISE.search(f) for f in files)):
                continue
            name = "%s__%s__%s.diff" % (owner, repo, c["sha"][:10])
            with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
                fh.write(text)
            index.append({"id": name[:-5], "repo": "%s/%s" % (owner, repo), "sha": c["sha"],
                          "message": msg.splitlines()[0][:160], "files": files, "bytes": len(diff),
                          "path": os.path.join("data", "ordinary", name)})
            kept += 1
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
    print("repos:", repos, "commits corrientes guardados:", len(index))
    for e in index[:12]:
        print("  ", e["repo"], "|", e["message"])


if __name__ == "__main__":
    main()
