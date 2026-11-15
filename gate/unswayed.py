#!/usr/bin/env python3
"""unswayed: a description-blind gate in front of an AI code reviewer.

Before the normal reviewer (for example `gga run`) sees a change with all its
context, a separate pass looks ONLY at the diff and answers one narrow
question: does this change weaken an existing safeguard? It never sees commit
messages, descriptions or branch names, so persuasive text cannot reach it.
If the answer is WEAKENS, the commit is blocked until a person acknowledges
it explicitly, and the decision is logged.

Subcommands:
  check             classify the diff (staged by default) and, if it passes, run the reviewer
  init              write a .unswayed config file with the defaults
  install           install the pre-commit hook in the current repository
  report            summarise the decision log; export it as CSV for an audit or a pilot
  ack-from-reviews  CI helper: find a maintainer's acknowledgement in pull request reviews

Python standard library only. The project started as "revisor-ciego"; the old
config file name and REVISOR_CIEGO_* environment variables keep working.
"""
import argparse
import csv
import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

VERSION = "0.2.0"
NAME = "unswayed"
CONFIG_NAME = ".unswayed"
LEGACY_CONFIG_NAME = ".revisor-ciego"
ENV_PREFIXES = ("UNSWAYED_", "REVISOR_CIEGO_")   # the first one set wins
LOG_DIR = "unswayed"

DEFAULTS = {
    "PROVIDER": "claude",            # claude | openai (cualquier API compatible: Nebius, Ollama...)
    "MODEL": "claude-opus-5-5",
    "BASE_URL": "https://api.tokenfactory.nebius.com/v1",
    "API_KEY_ENV": "NEBIUS_API_KEY",
    "SAMPLES": "1",                  # repeticiones del pase a ciegas; decide la mayoría
    "TIMEOUT": "180",
    "MAX_CHARS": "12000",            # tamaño máximo de diff por llamada
    "ON_ERROR": "block",             # block | allow, si el pase a ciegas no puede responder
    "MODE": "enforce",               # enforce | shadow (shadow: log the verdict, never hold a change)
    "GRANULARITY": "diff",           # diff | hunk (hunk: every hunk is judged on its own; more calls)
    "REVIEWER_CMD": "auto",          # auto = `gga run` si gga está instalado; "" = ninguno
    "EXCLUDE": r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|[\w.\-]*\.lock)$|\.min\.(js|css)$",
}

# Este texto es el que se midió en experiments/run_claims.py. Si se cambia,
# las cifras de detección y de falsas alarmas dejan de aplicar.
SYSTEM_PROMPT = (
    "You are an automated code reviewer acting as a merge gate in a CI pipeline. "
    "You only read the material you are given and answer with a verdict."
)

TRIPWIRE_PROMPT = """You are analysing a code change for a security team. You only see the diff: there is no description, and you must not guess the author's intent.

=== DIFF ===
{diff}
=== END DIFF ===

1. In 2-5 short bullet points, state factually what the change does to the program's behaviour. Mention any validation, escaping or encoding, authentication or authorization check, bounds or length check, query construction, sandboxing, or security-related test that is added, removed or altered.
2. Then finish with exactly one of these lines:
SECURITY_EFFECT: WEAKENS      (an existing safeguard is removed, bypassed or made less strict)
SECURITY_EFFECT: STRENGTHENS  (a safeguard is added or made stricter)
SECURITY_EFFECT: NEUTRAL      (no safeguard is affected)"""

EFFECTS = ("WEAKENS", "STRENGTHENS", "NEUTRAL")


class GateError(Exception):
    """El pase a ciegas no pudo dar una respuesta utilizable."""


# --------------------------------------------------------------------------- config

def env_get(key):
    """UNSWAYED_<KEY>, or the legacy REVISOR_CIEGO_<KEY>; None if neither is set."""
    for prefix in ENV_PREFIXES:
        value = os.environ.get(prefix + key)
        if value is not None:
            return value
    return None


def load_config(repo_root):
    cfg = dict(DEFAULTS)
    for name in (LEGACY_CONFIG_NAME, CONFIG_NAME):   # .unswayed overrides the legacy file
        path = os.path.join(repo_root, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip().strip("'\"")
    for key in DEFAULTS:
        env = env_get(key)
        if env is not None:
            cfg[key] = env
    return cfg


def git(args, cwd, check=True):
    proc = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise GateError("git %s failed: %s" % (" ".join(args), proc.stderr.strip()[:200]))
    return proc.stdout


def repo_root(cwd):
    return git(["rev-parse", "--show-toplevel"], cwd).strip()


# --------------------------------------------------------------------------- diff

def split_files(diff_text):
    """Devuelve [(ruta, texto_del_diff_de_ese_archivo)]."""
    parts, current, path = [], [], None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current:
                parts.append((path, "\n".join(current)))
            current = [line]
            m = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            path = m.group(2) if m else "?"
        elif current:
            if line.startswith("index "):
                continue  # los hashes no aportan y no se midieron
            current.append(line)
    if current:
        parts.append((path, "\n".join(current)))
    return parts


def split_hunks(file_diff, max_chars):
    """Trocea el diff de un archivo grande por hunks, repitiendo la cabecera."""
    lines = file_diff.splitlines()
    first_hunk = next((i for i, l in enumerate(lines) if l.startswith("@@")), len(lines))
    header, body = lines[:first_hunk], lines[first_hunk:]
    hunks, cur = [], []
    for line in body:
        if line.startswith("@@") and cur:
            hunks.append(cur)
            cur = []
        cur.append(line)
    if cur:
        hunks.append(cur)
    chunks, acc, size = [], [], 0
    for hunk in hunks:
        text = "\n".join(hunk)
        if acc and size + len(text) > max_chars:
            chunks.append("\n".join(header + acc))
            acc, size = [], 0
        acc.extend(hunk)
        size += len(text)
    if acc:
        chunks.append("\n".join(header + acc))
    return chunks or [file_diff]


def build_chunks(diff_text, max_chars, exclude_re, granularity="diff"):
    """Agrupa archivos en llamadas de como mucho max_chars; excluye ruido.

    With granularity="hunk" every hunk becomes its own call, so a weakening hunk
    cannot be outweighed by benign or hardening hunks placed around it.
    """
    exclude = re.compile(exclude_re) if exclude_re else None
    files, skipped = [], []
    for path, text in split_files(diff_text):
        if "GIT binary patch" in text or re.search(r"^Binary files ", text, re.M):
            skipped.append(path)
        elif exclude and exclude.search(path or ""):
            skipped.append(path)
        else:
            files.append((path, text))
    if granularity == "hunk":
        return [{"paths": [path], "diff": piece}
                for path, text in files for piece in split_hunks(text, 0)], skipped
    chunks, acc, acc_paths, size = [], [], [], 0
    for path, text in files:
        pieces = [text] if len(text) <= max_chars else split_hunks(text, max_chars)
        for piece in pieces:
            if acc and size + len(piece) > max_chars:
                chunks.append({"paths": acc_paths, "diff": "\n".join(acc)})
                acc, acc_paths, size = [], [], 0
            acc.append(piece)
            if path not in acc_paths:
                acc_paths = acc_paths + [path]
            size += len(piece)
    if acc:
        chunks.append({"paths": acc_paths, "diff": "\n".join(acc)})
    return chunks, skipped


# --------------------------------------------------------------------------- modelos

def ask_claude(prompt, cfg):
    cmd = ["claude", "--print", "--model", cfg["MODEL"], "--tools", "",
           "--system-prompt", SYSTEM_PROMPT, "--strict-mcp-config", "--no-session-persistence"]
    workdir = tempfile.mkdtemp(prefix="unswayed-")  # carpeta vacía: sin CLAUDE.md ni memoria
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=int(cfg["TIMEOUT"]), cwd=workdir)
    except FileNotFoundError:
        raise GateError("the `claude` CLI was not found")
    except subprocess.TimeoutExpired:
        raise GateError("the model did not answer within %s s" % cfg["TIMEOUT"])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GateError("claude returned an error: %s" % (proc.stderr or proc.stdout).strip()[:200])
    return proc.stdout


def ask_openai(prompt, cfg):
    key = os.environ.get(cfg["API_KEY_ENV"], "") if cfg["API_KEY_ENV"] else ""
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    payload = {"model": cfg["MODEL"], "max_tokens": 1500,
               "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}]}
    req = urllib.request.Request(cfg["BASE_URL"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=int(cfg["TIMEOUT"])) as resp:
            body = json.loads(resp.read())
        text = body["choices"][0]["message"].get("content") or ""
    except urllib.error.HTTPError as exc:
        raise GateError("the API returned HTTP %d" % exc.code)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        raise GateError("the API call failed: %s" % repr(exc)[:160])
    if not text.strip():
        raise GateError("the API returned an empty response")
    return text


def ask_mock(prompt, cfg):
    """Solo para pruebas: respuesta fija tomada del entorno."""
    response = env_get("MOCK_RESPONSE")
    return response if response is not None else "- nothing\nSECURITY_EFFECT: NEUTRAL"


PROVIDERS = {"claude": ask_claude, "openai": ask_openai, "mock": ask_mock}


# --------------------------------------------------------------------------- pase a ciegas

def parse_effect(text):
    """Última etiqueta SECURITY_EFFECT de la RESPUESTA del modelo (nunca del diff)."""
    found = re.findall(r"SECURITY_EFFECT:\s*\**\s*(%s)" % "|".join(EFFECTS), text)
    return found[-1] if found else None


def strip_effect_line(text):
    return re.sub(r"\n?.*SECURITY_EFFECT:.*", "", text).strip()


def tripwire(diff_text, cfg, ask=None):
    """Clasifica el diff. Devuelve dict con effect global y detalle por trozo."""
    ask = ask or PROVIDERS.get(cfg["PROVIDER"])
    if ask is None:
        raise GateError("unknown PROVIDER: %s" % cfg["PROVIDER"])
    chunks, skipped = build_chunks(diff_text, int(cfg["MAX_CHARS"]), cfg["EXCLUDE"],
                                   cfg.get("GRANULARITY", "diff").strip().lower())
    samples = max(1, int(cfg["SAMPLES"]))
    results = []
    for chunk in chunks:
        tags, summary = [], ""
        for _ in range(samples):
            text = ask(TRIPWIRE_PROMPT.format(diff=chunk["diff"]), cfg)
            tag = parse_effect(text)
            if tag is None:
                raise GateError("the model response has no SECURITY_EFFECT tag")
            tags.append(tag)
            if tag == "WEAKENS" or not summary:
                summary = strip_effect_line(text)
        weak = tags.count("WEAKENS") * 2 > len(tags)
        effect = "WEAKENS" if weak else max(set(tags), key=tags.count)
        results.append({"paths": chunk["paths"], "effect": effect, "votes": tags, "summary": summary})
    if any(r["effect"] == "WEAKENS" for r in results):
        overall = "WEAKENS"
    elif any(r["effect"] == "STRENGTHENS" for r in results):
        overall = "STRENGTHENS"
    else:
        overall = "NEUTRAL"
    return {"effect": overall, "chunks": results, "skipped": skipped}


# --------------------------------------------------------------------------- registro y salida

def log_decision(root, record):
    try:
        git_dir = git(["rev-parse", "--git-dir"], root).strip()
        log_dir = os.path.join(root, git_dir, LOG_DIR) if not os.path.isabs(git_dir) \
            else os.path.join(git_dir, LOG_DIR)
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "log.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except (GateError, OSError):
        pass  # el registro nunca debe impedir un commit


def say(text=""):
    sys.stderr.write(text + "\n")


def resolve_reviewer(cfg):
    cmd = cfg["REVIEWER_CMD"]
    if cmd == "auto":
        return "gga run" if shutil.which("gga") else ""
    return cmd


def cmd_check(args):
    cwd = os.getcwd()
    try:
        root = repo_root(cwd)
    except GateError as exc:
        say("unswayed: %s" % exc)
        return 2
    cfg = load_config(root)

    if args.diff_file:
        with open(args.diff_file, encoding="utf-8", errors="replace") as fh:
            diff_text = fh.read()
        source = "file"
    elif args.range:
        diff_text = git(["diff", "--no-color", "-U3", args.range], root)
        source = args.range
    else:
        diff_text = git(["diff", "--cached", "--no-color", "-U3", "--diff-filter=ACMR"], root)
        source = "staged"

    record = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "version": VERSION, "source": source, "provider": cfg["PROVIDER"], "model": cfg["MODEL"],
              "branch": git(["rev-parse", "--abbrev-ref", "HEAD"], root, check=False).strip()}

    if not diff_text.strip():
        say("unswayed: no changes to check.")
        return 0

    shadow = cfg["MODE"].strip().lower() == "shadow"
    record["mode"] = "shadow" if shadow else "enforce"
    say("unswayed: blind pass (%s, diff only%s)..." % (cfg["MODEL"], ", shadow mode" if shadow else ""))
    result = None
    try:
        result = tripwire(diff_text, cfg)
    except GateError as exc:
        record.update(decision="error", error=str(exc))
        if shadow or cfg["ON_ERROR"] == "allow":
            say("unswayed: the blind pass failed (%s); %s, continuing."
                % (exc, "shadow mode" if shadow else "ON_ERROR=allow"))
        else:
            log_decision(root, record)
            write_step_summary(record)
            say("unswayed: the blind pass failed (%s). Blocked (ON_ERROR=block)." % exc)
            return 2

    if result is not None:
        record.update(effect=result["effect"], chunks=result["chunks"], skipped=result["skipped"])
        if result["effect"] == "WEAKENS":
            ack = (env_get("ACK") or "").strip() or (args.ack or "").strip()
            say("")
            say("  WEAKENS: this change weakens an existing safeguard.")
            for chunk in result["chunks"]:
                if chunk["effect"] != "WEAKENS":
                    continue
                say("  Files: %s" % ", ".join(chunk["paths"]))
                for line in chunk["summary"].splitlines():
                    say("    " + line)
            say("")
            if ack:
                record.update(decision="acknowledged", ack=ack)
                say("  Acknowledged by a person (\"%s\") and logged. Continuing with the normal review." % ack)
            elif shadow:
                record.update(decision="shadow-flagged")
                say("  SHADOW MODE: this would have been held. Logged; nothing is blocked.")
            else:
                record.update(decision="blocked")
                log_decision(root, record)
                write_step_summary(record)
                if os.environ.get("GITHUB_ACTIONS"):
                    say("  BLOCKED. If the change is intended, a maintainer other than the author")
                    say("  approves the pull request with a line:  unswayed-ack: <reason>")
                else:
                    say("  BLOCKED. If the change is intended, repeat it with the reason:")
                    say("    UNSWAYED_ACK=\"reason\" git commit ...")
                return 1
        else:
            record.update(decision="passed")
            say("unswayed: no safeguard weakened (%s)." % result["effect"])

    code = 0
    reviewer = "" if args.no_reviewer else resolve_reviewer(cfg)
    if reviewer:
        say("unswayed: handing over to the normal reviewer: %s" % reviewer)
        code = subprocess.run(shlex.split(reviewer), cwd=root).returncode
        record.update(reviewer=reviewer, reviewer_exit=code)
    log_decision(root, record)   # exactly one log line per check
    write_step_summary(record)
    return code


def write_step_summary(record):
    """In GitHub Actions, add the verdict to the job summary. Model text goes in a code block."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["### Unswayed: %s" % record.get("decision", "unknown").upper(), "",
             "Blind pass on the diff only, model `%s`, mode `%s`. Effect: **%s**."
             % (record.get("model"), record.get("mode"), record.get("effect", "no answer")), ""]
    if record.get("ack"):
        lines += ["Acknowledged: %s" % record["ack"].replace("`", "'"), ""]
    for chunk in record.get("chunks", []):
        if chunk.get("effect") != "WEAKENS":
            continue
        lines += ["Files: %s" % ", ".join("`%s`" % p for p in chunk.get("paths", [])), "",
                  "```text", chunk.get("summary", "").replace("```", "'" * 3), "```", ""]
    if record.get("error"):
        lines += ["Error: %s" % record["error"].replace("`", "'"), ""]
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        pass


# --------------------------------------------------------------------------- report

def read_log(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def record_files(row):
    files = []
    for chunk in row.get("chunks", []):
        for p in chunk.get("paths", []):
            if p not in files:
                files.append(p)
    return files


def summarize(rows):
    """Counts for a pilot or an audit. The flag rate is over checks the model answered."""
    by_decision = {}
    for row in rows:
        key = row.get("decision", "unknown")
        by_decision[key] = by_decision.get(key, 0) + 1
    answered = [r for r in rows if r.get("decision") != "error"]
    flagged = [r for r in answered if r.get("effect") == "WEAKENS"]
    times = sorted(r["time"] for r in rows if r.get("time"))
    return {
        "checks": len(rows),
        "answered": len(answered),
        "errors": len(rows) - len(answered),
        "flagged": len(flagged),
        "flag_rate": (len(flagged) / len(answered)) if answered else None,
        "by_decision": by_decision,
        "first": times[0] if times else None,
        "last": times[-1] if times else None,
        "acknowledgements": [{"time": r.get("time"), "files": record_files(r), "ack": r.get("ack")}
                             for r in rows if r.get("decision") == "acknowledged"],
    }


CSV_COLUMNS = ["time", "decision", "effect", "mode", "model", "provider", "source", "files", "ack",
               "reviewer", "reviewer_exit", "error", "summary"]


def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            summary = " | ".join(c.get("summary", "").replace("\n", " ") for c in row.get("chunks", [])
                                 if c.get("effect") == "WEAKENS")
            flat = dict(row, files="; ".join(record_files(row)), summary=summary)
            writer.writerow([flat.get(col, "") if flat.get(col) is not None else "" for col in CSV_COLUMNS])


def cmd_report(args):
    path = args.log
    if not path:
        try:
            root = repo_root(os.getcwd())
            git_dir = git(["rev-parse", "--git-dir"], root).strip()
        except GateError as exc:
            say("unswayed: %s" % exc)
            return 2
        base = git_dir if os.path.isabs(git_dir) else os.path.join(root, git_dir)
        path = os.path.join(base, LOG_DIR, "log.jsonl")
    if not os.path.exists(path):
        say("unswayed: no decision log at %s" % path)
        return 1
    rows = read_log(path)
    summary = summarize(rows)
    if args.csv:
        write_csv(rows, args.csv)
        say("unswayed: wrote %d rows to %s" % (len(rows), args.csv))
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    d = summary["by_decision"]
    rate = "n/a" if summary["flag_rate"] is None else "%.1f%%" % (100 * summary["flag_rate"])
    print("Unswayed decision report")
    print("  log:      %s" % path)
    print("  period:   %s to %s" % (summary["first"], summary["last"]))
    print("  checks:   %d (model answered %d, model errors %d)"
          % (summary["checks"], summary["answered"], summary["errors"]))
    print("  flagged as weakening a safeguard: %d of %d (%s)"
          % (summary["flagged"], summary["answered"], rate))
    print("    held (blocked):               %d" % d.get("blocked", 0))
    print("    acknowledged by a person:     %d" % d.get("acknowledged", 0))
    print("    shadow mode, would have held: %d" % d.get("shadow-flagged", 0))
    print("  passed:   %d" % d.get("passed", 0))
    if summary["acknowledgements"]:
        print("Acknowledgements")
        for item in summary["acknowledgements"]:
            print("  %s  %s  \"%s\"" % (item["time"], ", ".join(item["files"]) or "-", item["ack"]))
    return 0


# --------------------------------------------------------------------------- CI acknowledgement

ACK_LINE = re.compile(r"^\s*unswayed-ack:\s*(\S.*?)\s*$", re.I | re.M)
TRUSTED_ASSOCIATIONS = ("OWNER", "MEMBER", "COLLABORATOR")


def select_ack(reviews, author, head_sha, allowed=TRUSTED_ASSOCIATIONS):
    """Find a valid acknowledgement among pull request reviews (GitHub API objects).

    Valid means: the reviewer's LATEST review is an approval, it was made on the
    commit being checked (a later push voids it), the reviewer is not the author
    of the pull request, has a trusted association with the repository, and the
    review body has a line `unswayed-ack: <reason>`. Returns (login, reason) or None.
    """
    latest = {}
    for review in reviews:
        if not isinstance(review, dict) or review.get("state") in (None, "COMMENTED", "PENDING"):
            continue
        login = ((review.get("user") or {}).get("login") or "").lower()
        if not login:
            continue
        stamp = review.get("submitted_at") or ""
        if login not in latest or stamp >= (latest[login].get("submitted_at") or ""):
            latest[login] = review
    valid = []
    for login, review in latest.items():
        if login == (author or "").lower():
            continue
        if review.get("state") != "APPROVED" or review.get("commit_id") != head_sha:
            continue
        if review.get("author_association") not in allowed:
            continue
        found = ACK_LINE.search(review.get("body") or "")
        if found:
            valid.append((review.get("submitted_at") or "", (review.get("user") or {}).get("login"), found.group(1)))
    if not valid:
        return None
    valid.sort()
    return valid[-1][1], valid[-1][2]


def cmd_ack_from_reviews(args):
    raw = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    try:
        data = json.loads(raw) if raw.strip() else []
    except ValueError:
        say("unswayed: the reviews file is not valid JSON")
        return 2
    if data and all(isinstance(item, list) for item in data):   # `gh api --paginate --slurp`
        data = [review for page in data for review in page]
    allowed = tuple(a.strip().upper() for a in args.associations.split(",") if a.strip())
    found = select_ack(data, args.author, args.head, allowed)
    if not found:
        return 1
    print("%s (acknowledged by %s on %s)" % (found[1], found[0], args.head[:12]))
    return 0


def cmd_init(args):
    root = repo_root(os.getcwd())
    path = os.path.join(root, CONFIG_NAME)
    if os.path.exists(path) and not args.force:
        say("%s already exists (use --force to overwrite)." % path)
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Unswayed configuration (KEY=\"value\", same format as .gga)\n")
        fh.write("# PROVIDER: claude (Claude Code CLI) | openai (any compatible API: Nebius, Ollama...)\n")
        for key, value in DEFAULTS.items():
            fh.write('%s="%s"\n' % (key, value))
    say("Created %s" % path)
    return 0


HOOK = """#!/bin/sh
# Installed by unswayed {version}. Blind pass first; if it passes, the normal reviewer.
exec python3 "{script}" check
"""


def cmd_install(args):
    root = repo_root(os.getcwd())
    hooks = git(["rev-parse", "--git-path", "hooks"], root).strip()
    hooks = hooks if os.path.isabs(hooks) else os.path.join(root, hooks)
    os.makedirs(hooks, exist_ok=True)
    target = os.path.join(hooks, "pre-commit")
    if os.path.exists(target):
        with open(target, encoding="utf-8", errors="replace") as fh:
            existing = fh.read()
        if "unswayed" not in existing and "revisor-ciego" not in existing:
            backup = target + ".before-unswayed"
            shutil.copy2(target, backup)
            say("Previous hook saved to %s" % backup)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(HOOK.format(version=VERSION, script=os.path.abspath(__file__)))
    os.chmod(target, 0o755)
    say("pre-commit hook installed at %s" % target)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog=NAME, description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="command", required=True)
    chk = sub.add_parser("check", help="classify the diff and chain into the normal reviewer")
    chk.add_argument("--range", help="git range to check (CI), e.g. origin/main...HEAD")
    chk.add_argument("--diff-file", help="check a diff saved in a file")
    chk.add_argument("--ack", help="reason with which a person acknowledges the change")
    chk.add_argument("--no-reviewer", action="store_true", help="do not run the normal reviewer")
    chk.set_defaults(func=cmd_check)
    ini = sub.add_parser("init", help="create .unswayed")
    ini.add_argument("--force", action="store_true")
    ini.set_defaults(func=cmd_init)
    ins = sub.add_parser("install", help="install the pre-commit hook")
    ins.set_defaults(func=cmd_install)
    rep = sub.add_parser("report", help="summarise the decision log; --csv exports it")
    rep.add_argument("--log", help="path to a log.jsonl (default: this repository's)")
    rep.add_argument("--csv", help="write every decision to this CSV file")
    rep.add_argument("--json", action="store_true", help="print the summary as JSON")
    rep.set_defaults(func=cmd_report)
    ack = sub.add_parser("ack-from-reviews",
                         help="CI: print a maintainer's acknowledgement found in PR reviews")
    ack.add_argument("--file", required=True, help="JSON from the pull request reviews API, or - for stdin")
    ack.add_argument("--author", required=True, help="login of the pull request author (never accepted)")
    ack.add_argument("--head", required=True, help="commit SHA being checked; older approvals are void")
    ack.add_argument("--associations", default=",".join(TRUSTED_ASSOCIATIONS),
                     help="author_association values allowed to acknowledge")
    ack.set_defaults(func=cmd_ack_from_reviews)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
