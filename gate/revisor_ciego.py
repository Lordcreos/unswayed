#!/usr/bin/env python3
"""revisor-ciego: compuerta a ciegas delante de un revisor de código con IA.

Antes de que el revisor normal (por ejemplo `gga run`) vea el cambio con todo
su contexto, un pase separado mira SOLO el diff y responde a una pregunta
estrecha: ¿este cambio debilita una salvaguarda existente? No ve mensajes de
commit, descripciones ni nombres de rama, así que el texto persuasivo no le
llega. Si la respuesta es WEAKENS, el commit se bloquea hasta que un humano
lo reconozca explícitamente.

Subcomandos:
  check      revisa el diff (staged por defecto) y, si pasa, llama al revisor
  init       escribe un .revisor-ciego con valores por defecto
  install    instala el hook pre-commit en el repositorio actual

Solo usa la biblioteca estándar de Python.
"""
import argparse
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

VERSION = "0.1.0"
CONFIG_NAME = ".revisor-ciego"

DEFAULTS = {
    "PROVIDER": "claude",            # claude | openai (cualquier API compatible: Nebius, Ollama...)
    "MODEL": "claude-opus-5-5",
    "BASE_URL": "https://api.tokenfactory.nebius.com/v1",
    "API_KEY_ENV": "NEBIUS_API_KEY",
    "SAMPLES": "1",                  # repeticiones del pase a ciegas; decide la mayoría
    "TIMEOUT": "180",
    "MAX_CHARS": "12000",            # tamaño máximo de diff por llamada
    "ON_ERROR": "block",             # block | allow, si el pase a ciegas no puede responder
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

def load_config(repo_root):
    cfg = dict(DEFAULTS)
    path = os.path.join(repo_root, CONFIG_NAME)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip().strip("'\"")
    for key in DEFAULTS:
        env = os.environ.get("REVISOR_CIEGO_" + key)
        if env is not None:
            cfg[key] = env
    return cfg


def git(args, cwd, check=True):
    proc = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise GateError("git %s falló: %s" % (" ".join(args), proc.stderr.strip()[:200]))
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


def build_chunks(diff_text, max_chars, exclude_re):
    """Agrupa archivos en llamadas de como mucho max_chars; excluye ruido."""
    exclude = re.compile(exclude_re) if exclude_re else None
    files, skipped = [], []
    for path, text in split_files(diff_text):
        if "GIT binary patch" in text or re.search(r"^Binary files ", text, re.M):
            skipped.append(path)
        elif exclude and exclude.search(path or ""):
            skipped.append(path)
        else:
            files.append((path, text))
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
    workdir = tempfile.mkdtemp(prefix="revisor-ciego-")  # carpeta vacía: sin CLAUDE.md ni memoria
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                              timeout=int(cfg["TIMEOUT"]), cwd=workdir)
    except FileNotFoundError:
        raise GateError("no se encontró la CLI `claude`")
    except subprocess.TimeoutExpired:
        raise GateError("el modelo no respondió en %s s" % cfg["TIMEOUT"])
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise GateError("claude devolvió error: %s" % (proc.stderr or proc.stdout).strip()[:200])
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
        raise GateError("la API devolvió HTTP %d" % exc.code)
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        raise GateError("fallo al llamar a la API: %s" % repr(exc)[:160])
    if not text.strip():
        raise GateError("la API devolvió una respuesta vacía")
    return text


def ask_mock(prompt, cfg):
    """Solo para pruebas: respuesta fija tomada del entorno."""
    return os.environ.get("REVISOR_CIEGO_MOCK_RESPONSE", "- nothing\nSECURITY_EFFECT: NEUTRAL")


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
        raise GateError("PROVIDER desconocido: %s" % cfg["PROVIDER"])
    chunks, skipped = build_chunks(diff_text, int(cfg["MAX_CHARS"]), cfg["EXCLUDE"])
    samples = max(1, int(cfg["SAMPLES"]))
    results = []
    for chunk in chunks:
        tags, summary = [], ""
        for _ in range(samples):
            text = ask(TRIPWIRE_PROMPT.format(diff=chunk["diff"]), cfg)
            tag = parse_effect(text)
            if tag is None:
                raise GateError("respuesta sin etiqueta SECURITY_EFFECT")
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
        log_dir = os.path.join(root, git_dir, "revisor-ciego") if not os.path.isabs(git_dir) \
            else os.path.join(git_dir, "revisor-ciego")
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
        say("revisor-ciego: %s" % exc)
        return 2
    cfg = load_config(root)

    if args.diff_file:
        with open(args.diff_file, encoding="utf-8", errors="replace") as fh:
            diff_text = fh.read()
        source = "archivo"
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
        say("revisor-ciego: no hay cambios que revisar.")
        return 0

    say("revisor-ciego: pase a ciegas (%s, solo el diff)..." % cfg["MODEL"])
    try:
        result = tripwire(diff_text, cfg)
    except GateError as exc:
        record.update(decision="error", error=str(exc))
        log_decision(root, record)
        if cfg["ON_ERROR"] == "allow":
            say("revisor-ciego: el pase a ciegas falló (%s); ON_ERROR=allow, continúo." % exc)
            result = None
        else:
            say("revisor-ciego: el pase a ciegas falló (%s). Commit bloqueado (ON_ERROR=block)." % exc)
            return 2

    if result is not None:
        record.update(effect=result["effect"], chunks=result["chunks"], skipped=result["skipped"])
        if result["effect"] == "WEAKENS":
            ack = os.environ.get("REVISOR_CIEGO_ACK", "").strip() or (args.ack or "").strip()
            say("")
            say("  ALERTA: este cambio debilita una salvaguarda existente.")
            for chunk in result["chunks"]:
                if chunk["effect"] != "WEAKENS":
                    continue
                say("  Archivos: %s" % ", ".join(chunk["paths"]))
                for line in chunk["summary"].splitlines():
                    say("    " + line)
            say("")
            if ack:
                record.update(decision="acknowledged", ack=ack)
                log_decision(root, record)
                say("  Reconocido por una persona (\"%s\"). Continúo con la revisión normal." % ack)
            else:
                record.update(decision="blocked")
                log_decision(root, record)
                say("  Commit bloqueado. Si el cambio es intencionado, repite con el motivo:")
                say("    REVISOR_CIEGO_ACK=\"motivo\" git commit ...")
                return 1
        else:
            record.update(decision="passed")
            say("revisor-ciego: sin salvaguardas debilitadas (%s)." % result["effect"])

    reviewer = "" if args.no_reviewer else resolve_reviewer(cfg)
    if reviewer:
        say("revisor-ciego: paso al revisor normal: %s" % reviewer)
        code = subprocess.run(shlex.split(reviewer), cwd=root).returncode
        record.update(reviewer=reviewer, reviewer_exit=code)
        log_decision(root, record)
        return code
    if "decision" in record and record["decision"] == "passed":
        log_decision(root, record)
    return 0


def cmd_init(args):
    root = repo_root(os.getcwd())
    path = os.path.join(root, CONFIG_NAME)
    if os.path.exists(path) and not args.force:
        say("%s ya existe (usa --force para sobrescribir)." % path)
        return 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Configuración de revisor-ciego (formato CLAVE=\"valor\", como .gga)\n")
        fh.write("# PROVIDER: claude (CLI de Claude Code) | openai (API compatible: Nebius, Ollama...)\n")
        for key, value in DEFAULTS.items():
            fh.write('%s="%s"\n' % (key, value))
    say("Creado %s" % path)
    return 0


HOOK = """#!/bin/sh
# Instalado por revisor-ciego {version}. Pase a ciegas y, si pasa, el revisor normal.
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
        if "revisor-ciego" not in existing:
            backup = target + ".antes-de-revisor-ciego"
            shutil.copy2(target, backup)
            say("Hook previo guardado en %s" % backup)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(HOOK.format(version=VERSION, script=os.path.abspath(__file__)))
    os.chmod(target, 0o755)
    say("Hook pre-commit instalado en %s" % target)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="revisor-ciego", description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="command", required=True)
    chk = sub.add_parser("check", help="revisa el diff y encadena con el revisor normal")
    chk.add_argument("--range", help="rango git a revisar (CI), p. ej. origin/main...HEAD")
    chk.add_argument("--diff-file", help="revisar un diff guardado en un archivo")
    chk.add_argument("--ack", help="motivo con el que una persona reconoce el cambio")
    chk.add_argument("--no-reviewer", action="store_true", help="no llamar al revisor normal")
    chk.set_defaults(func=cmd_check)
    ini = sub.add_parser("init", help="crea .revisor-ciego")
    ini.add_argument("--force", action="store_true")
    ini.set_defaults(func=cmd_init)
    ins = sub.add_parser("install", help="instala el hook pre-commit")
    ins.set_defaults(func=cmd_install)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
