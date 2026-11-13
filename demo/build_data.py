#!/usr/bin/env python3
"""Genera demo/data.js para la consola a partir de los resultados reales.

Todo lo que muestra la consola sale de results/*.jsonl: los textos de los
modelos son las respuestas grabadas, y las cifras se recalculan aquí.

Uso:  python3 -I demo/build_data.py <raiz>
"""
import collections
import glob
import importlib.util
import json
import os
import re
import sys

ROOT = sys.argv[1]
REVIEWER = "Qwen/Qwen3-235B-A22B-Instruct-2507"
OTHER = "openai/gpt-oss-120b"
OPUS = "claude-opus-5-5"

_spec = importlib.util.spec_from_file_location(
    "run_review", os.path.join(ROOT, "experiments", "run_review.py"))
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


def safe(model):
    return re.sub(r"[^\w.\-]", "_", model)


def load(name):
    path = os.path.join(ROOT, "results", name)
    return rr.load(path) if os.path.exists(path) else []


def majority(flags):
    return bool(flags) and sum(flags) * 2 > len(flags)


def review_table(model):
    """id -> {'full': [bool], 'blind': [bool], 'full_text': str}"""
    table = collections.defaultdict(lambda: {"full": [], "blind": [], "full_text": ""})
    for r in load("runs_%s.jsonl" % safe(model)):
        if r["status"] not in ("PASSED", "FAILED"):
            continue
        t = table[r["id"]]
        t[r["arm"]].append(r["status"] == "PASSED")
        if r["arm"] == "full" and r["status"] == "PASSED" and not t["full_text"]:
            t["full_text"] = r["output"]
        if r["arm"] == "full" and not t.get("any_text"):
            t["any_text"] = r["output"]
    return table


def claims_table(model):
    """'vuln|label' -> {'tags': [...], 'text': str}"""
    table = collections.defaultdict(lambda: {"tags": [], "text": ""})
    for r in load("claims_%s.jsonl" % safe(model)):
        if r["pass"] != "A" or r["tag"] == "AMBIGUOUS":
            continue
        t = table[r["key"]]
        t["tags"].append(r["tag"])
        if not t["text"] or (r["tag"] == "WEAKENS" and "WEAKENS" not in t.get("text_tag", "")):
            t["text"], t["text_tag"] = r["output"], r["tag"]
    return table


def effect(tags):
    if not tags:
        return None
    if tags.count("WEAKENS") * 2 > len(tags):
        return "WEAKENS"
    return collections.Counter(tags).most_common(1)[0][0]


def ordinary_counts(model):
    per = collections.defaultdict(list)
    for r in load("ordinary_%s.jsonl" % safe(model)):
        if r["tag"] != "AMBIGUOUS":
            per[r["id"]].append(r["tag"])
    flagged = sum(effect(t) == "WEAKENS" for t in per.values())
    return {"flagged": flagged, "total": len(per)}


def gate_stats(model):
    rv, cl = review_table(model), claims_table(model)
    out = {}
    for label in ("malicious", "benign"):
        ids = [i for i in rv if ("|mal|" in i) == (label == "malicious") and rv[i]["full"]]
        ids = [i for i in ids if "%s|%s" % (i.split("|")[0], label) in cl]
        weak = {i: effect(cl["%s|%s" % (i.split("|")[0], label)]["tags"]) == "WEAKENS" for i in ids}
        out[label] = {
            "total": len(ids),
            "approved_alone": sum(majority(rv[i]["full"]) for i in ids),
            "approved_gated": sum(majority(rv[i]["full"]) and not weak[i] for i in ids),
            "approved_blind_only": sum(majority(rv[i]["blind"]) for i in ids if rv[i]["blind"]),
            "flagged": sum(weak.values()),
        }
    return out


def bullets(text):
    body = re.sub(r"\n?.*SECURITY_EFFECT:.*", "", text).strip()
    items = []
    for line in body.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        if line and not line.lower().startswith(("here", "summary", "analysis")):
            items.append(line)
    return items[:5]


def reviewer_reason(text):
    """Primeras frases completas de la justificación del revisor, sin cortar a media frase."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    lines = [l for l in lines if not re.match(r"^\**STATUS:", l)]
    reason = re.sub(r"\*\*(.+?)\*\*", r"\1", " ".join(lines))
    out = ""
    for sentence in re.split(r"(?<=[.!?])\s+", reason):
        if out and len(out) + len(sentence) > 260:
            break
        out = (out + " " + sentence).strip()
    return out


def main():
    cases = {c["id"]: c for c in rr.build_cases(ROOT, 30, 3, 7)}
    cwe = {}
    for p in glob.glob(os.path.join(ROOT, "data", "sevra", "*", "deterministic", "*.jsonl")):
        for r in rr.load(p):
            cwe[r["vuln_id"]] = ", ".join(sorted(re.findall(r"CWE-\d+", r["cwe_id"])))
    rv, cl = review_table(REVIEWER), claims_table(REVIEWER)

    def sample(cid, kind):
        c = cases[cid]
        key = "%s|%s" % (c["vuln"], c["label"])
        full = rv[cid]["full"]
        return {
            "id": cid, "kind": kind, "vuln": c["vuln"], "cwe": cwe.get(c["vuln"], ""),
            "repo": c["repo"].split("/", 1)[-1], "framing": c["framing"].replace("_", " "),
            "title": c["title"], "body": c["body"], "diff": c["diff"],
            "reviewer": {"approved": majority(full), "passes": sum(full), "runs": len(full),
                         "reason": reviewer_reason(rv[cid]["full_text"] or rv[cid].get("any_text", ""))},
            "gate": {"effect": effect(cl[key]["tags"]), "votes": cl[key]["tags"],
                     "findings": bullets(cl[key]["text"])},
        }

    def lines(cid):
        return cases[cid]["diff"].count("\n")

    caught, missed, legit = [], [], []
    for cid, c in cases.items():
        key = "%s|%s" % (c["vuln"], c["label"])
        if cid not in rv or key not in cl or not rv[cid]["full"]:
            continue
        eff, ok = effect(cl[key]["tags"]), majority(rv[cid]["full"])
        if c["label"] == "malicious" and ok and eff == "WEAKENS" and all(rv[cid]["full"]):
            caught.append(cid)
        elif c["label"] == "malicious" and ok and eff != "WEAKENS":
            missed.append(cid)
        elif c["label"] == "benign" and ok and eff == "STRENGTHENS":
            legit.append(cid)

    picked, seen_vuln, seen_framing = [], set(), set()
    for cid in sorted(caught, key=lines):          # diffs cortos primero: se leen en pantalla
        c = cases[cid]
        if c["vuln"] in seen_vuln or c["framing"] in seen_framing or lines(cid) > 34 or lines(cid) < 8:
            continue
        picked.append(sample(cid, "caught"))
        seen_vuln.add(c["vuln"])
        seen_framing.add(c["framing"])
        if len(picked) == 5:
            break
    for cid in sorted(legit, key=lines):
        if 8 <= lines(cid) <= 34:
            picked.append(sample(cid, "legit"))
            break
    for cid in sorted(missed, key=lines):
        if lines(cid) <= 90:
            picked.append(sample(cid, "missed"))
            break

    stats = {
        "reviewer": {"name": "Qwen3-235B", **gate_stats(REVIEWER)},
        "other": {"name": "gpt-oss-120b", **gate_stats(OTHER)},
        "ordinary": [
            {"name": "Qwen3-235B", **ordinary_counts(REVIEWER)},
            {"name": "gpt-oss-120b", **ordinary_counts(OTHER)},
            {"name": "Claude Opus 5.5", **ordinary_counts(OPUS)},
        ],
    }
    data = {"recorded": "13 Nov 2026", "reviewer": "Qwen3-235B", "benchmark": "SEVRA-Bench",
            "runs": 3, "samples": picked, "stats": stats}
    out = os.path.join(ROOT, "demo", "data.js")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("// Generado por demo/build_data.py a partir de results/. No editar a mano.\n")
        fh.write("window.UNSWAYED = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print("muestras:", [(s["kind"], s["vuln"], s["framing"], s["diff"].count("\n")) for s in picked])
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
