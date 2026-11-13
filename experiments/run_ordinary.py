#!/usr/bin/env python3
"""Mide falsas alarmas de la pregunta a ciegas (pase A) en commits corrientes.

Uso:
  python3 -I experiments/run_ordinary.py <raiz> --model openai/gpt-oss-120b [--provider nebius]
"""
import argparse
import collections
import concurrent.futures
import importlib.util
import json
import os
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rr = _load("run_review")
rc = _load("run_claims")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--model", required=True)
    ap.add_argument("--provider", choices=("claude", "nebius"), default="nebius")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()

    with open(os.path.join(args.root, "data", "ordinary", "index.json"), encoding="utf-8") as fh:
        index = json.load(fh)
    if args.limit:
        index = index[:args.limit]
    out_path = os.path.join(args.root, "results", "ordinary_%s.jsonl" % rc.safe(args.model))
    done = {}
    if os.path.exists(out_path):
        for r in rr.load(out_path):
            if r["tag"] != "AMBIGUOUS":
                done[(r["id"], r["sample"])] = r

    if not args.analyze:
        if args.provider == "claude":
            workdir = tempfile.mkdtemp(prefix="ordinary-")
            ask = lambda p: rr.call_reviewer(p, args.model, workdir)
        else:
            key = rr.nebius_key(args.root)
            ask = lambda p: rr.call_nebius(p, args.model, key)[0]
        lock = threading.Lock()
        jobs = [(e, s) for e in index for s in range(args.samples) if (e["id"], s) not in done]
        print("llamadas:", len(jobs), flush=True)

        def work(job):
            e, s = job
            with open(os.path.join(args.root, e["path"]), encoding="utf-8") as fh:
                diff = rr.strip_index(fh.read())
            text = ask(rc.PROMPT_A.format(diff=diff))
            rec = {"id": e["id"], "sample": s, "message": e["message"],
                   "tag": rc.last_tag(text, "SECURITY_EFFECT", ("WEAKENS", "STRENGTHENS", "NEUTRAL")),
                   "output": text[:1200]}
            with lock:
                with open(out_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                done[(e["id"], s)] = rec

        with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
            list(pool.map(work, jobs))

    per = collections.defaultdict(list)
    msg = {}
    for (cid, _), r in done.items():
        per[cid].append(r["tag"])
        msg[cid] = r["message"]
    verdict = {}
    for cid, tags in per.items():
        verdict[cid] = collections.Counter(tags).most_common(1)[0][0]
    counts = collections.Counter(verdict.values())
    n = len(verdict)
    print("\nmodelo: %s   commits corrientes: %d" % (args.model, n))
    for tag in ("NEUTRAL", "STRENGTHENS", "WEAKENS"):
        print("  %-11s %3d  (%.0f%%)" % (tag, counts[tag], 100 * counts[tag] / max(1, n)))
    print("\nMarcados como WEAKENS (falsas alarmas a revisar a mano):")
    for cid, v in sorted(verdict.items()):
        if v == "WEAKENS":
            print("  %s | %s" % (cid.split("__")[1], msg[cid]))


if __name__ == "__main__":
    main()
