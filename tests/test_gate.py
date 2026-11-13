"""Pruebas de la compuerta sin llamar a ningún modelo.

Ejecutar:  python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "gate", "revisor_ciego.py")
_spec = importlib.util.spec_from_file_location("revisor_ciego", SCRIPT)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

DIFF_A = """diff --git a/db.py b/db.py
index 111..222 100644
--- a/db.py
+++ b/db.py
@@ -1,3 +1,3 @@
 def find(cur, name):
-    cur.execute("select * from t where name = ?", (name,))
+    cur.execute("select * from t where name = '%s'" % name)
     return cur.fetchall()
"""

DIFF_B = """diff --git a/util.py b/util.py
index 333..444 100644
--- a/util.py
+++ b/util.py
@@ -1,2 +1,2 @@
-def total(xs): return sum(xs)
+def total(values): return sum(values)
"""


def cfg(**over):
    c = dict(gate.DEFAULTS)
    c.update(PROVIDER="mock")
    c.update(over)
    return c


class ParseTests(unittest.TestCase):
    def test_takes_last_tag_of_the_answer(self):
        text = "- removes a check\nSECURITY_EFFECT: NEUTRAL\nactually\nSECURITY_EFFECT: WEAKENS"
        self.assertEqual(gate.parse_effect(text), "WEAKENS")

    def test_accepts_markdown_bold(self):
        self.assertEqual(gate.parse_effect("SECURITY_EFFECT: **STRENGTHENS**"), "STRENGTHENS")

    def test_missing_tag_is_none(self):
        self.assertIsNone(gate.parse_effect("I think this is fine."))

    def test_summary_drops_the_tag_line(self):
        self.assertEqual(gate.strip_effect_line("- a\n- b\nSECURITY_EFFECT: WEAKENS"), "- a\n- b")


class ChunkTests(unittest.TestCase):
    def test_index_lines_removed_and_files_split(self):
        files = gate.split_files(DIFF_A + DIFF_B)
        self.assertEqual([p for p, _ in files], ["db.py", "util.py"])
        self.assertNotIn("index 111", files[0][1])

    def test_small_diff_is_one_call(self):
        chunks, skipped = gate.build_chunks(DIFF_A + DIFF_B, 12000, gate.DEFAULTS["EXCLUDE"])
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["paths"], ["db.py", "util.py"])
        self.assertEqual(skipped, [])

    def test_large_diff_is_split_per_file(self):
        chunks, _ = gate.build_chunks(DIFF_A + DIFF_B, 250, gate.DEFAULTS["EXCLUDE"])
        self.assertEqual([c["paths"] for c in chunks], [["db.py"], ["util.py"]])

    def test_lockfiles_are_skipped(self):
        lock = DIFF_B.replace("util.py", "package-lock.json")
        chunks, skipped = gate.build_chunks(DIFF_A + lock, 12000, gate.DEFAULTS["EXCLUDE"])
        self.assertEqual(skipped, ["package-lock.json"])
        self.assertEqual(chunks[0]["paths"], ["db.py"])

    def test_big_file_is_split_by_hunks_keeping_header(self):
        hunks = "".join("@@ -%d,2 +%d,2 @@\n-old %d\n+new %d\n" % (i, i, i, i) for i in range(40))
        big = "diff --git a/big.py b/big.py\n--- a/big.py\n+++ b/big.py\n" + hunks
        chunks, _ = gate.build_chunks(big, 300, "")
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertTrue(c["diff"].startswith("diff --git a/big.py"))
        joined = "\n".join(c["diff"] for c in chunks)
        for i in range(40):
            self.assertIn("+new %d" % i, joined)


class TripwireTests(unittest.TestCase):
    def test_any_weakening_chunk_blocks_everything(self):
        def ask(prompt, _cfg):
            return "- x\nSECURITY_EFFECT: %s" % ("WEAKENS" if "db.py" in prompt else "NEUTRAL")
        result = gate.tripwire(DIFF_A + DIFF_B, cfg(MAX_CHARS="250"), ask)
        self.assertEqual(result["effect"], "WEAKENS")
        self.assertEqual([c["effect"] for c in result["chunks"]], ["WEAKENS", "NEUTRAL"])

    def test_majority_vote(self):
        answers = iter(["SECURITY_EFFECT: WEAKENS", "SECURITY_EFFECT: NEUTRAL", "SECURITY_EFFECT: NEUTRAL"])
        result = gate.tripwire(DIFF_A, cfg(SAMPLES="3"), lambda p, c: next(answers))
        self.assertEqual(result["effect"], "NEUTRAL")
        self.assertEqual(result["chunks"][0]["votes"], ["WEAKENS", "NEUTRAL", "NEUTRAL"])

    def test_unparseable_answer_raises(self):
        with self.assertRaises(gate.GateError):
            gate.tripwire(DIFF_A, cfg(), lambda p, c: "no tag here")

    def test_prompt_contains_only_the_diff(self):
        seen = []
        gate.tripwire(DIFF_A, cfg(), lambda p, c: seen.append(p) or "SECURITY_EFFECT: NEUTRAL")
        self.assertIn("cur.execute", seen[0])
        self.assertNotIn("index 111", seen[0])


class EndToEndTests(unittest.TestCase):
    """Repositorio git real, modelo simulado."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.run_git("init", "-q")
        self.run_git("config", "user.email", "test@example.com")
        self.run_git("config", "user.name", "Test")
        self.write("db.py", 'def find(cur, name):\n    cur.execute("select * from t where name = ?", (name,))\n')
        self.run_git("add", ".")
        self.run_git("commit", "-q", "-m", "base")
        self.write("db.py", "def find(cur, name):\n    cur.execute(\"select * from t where name = '%s'\" % name)\n")
        self.run_git("add", ".")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.repo, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def run_git(self, *args):
        subprocess.run(["git"] + list(args), cwd=self.repo, check=True, capture_output=True)

    def check(self, response, extra_env=None, args=()):
        env = dict(os.environ, REVISOR_CIEGO_PROVIDER="mock", REVISOR_CIEGO_MOCK_RESPONSE=response,
                   REVISOR_CIEGO_REVIEWER_CMD="")
        env.pop("REVISOR_CIEGO_ACK", None)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, SCRIPT, "check"] + list(args), cwd=self.repo, env=env,
                              capture_output=True, text=True)

    def log(self):
        path = os.path.join(self.repo, ".git", "revisor-ciego", "log.jsonl")
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh]

    def test_weakening_change_blocks_the_commit(self):
        proc = self.check("- replaces the parameterised query\nSECURITY_EFFECT: WEAKENS")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("debilita una salvaguarda", proc.stderr)
        self.assertIn("replaces the parameterised query", proc.stderr)
        self.assertEqual(self.log()[-1]["decision"], "blocked")

    def test_neutral_change_passes(self):
        proc = self.check("- renames a variable\nSECURITY_EFFECT: NEUTRAL")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.log()[-1]["decision"], "passed")

    def test_human_acknowledgement_lets_it_through_and_is_logged(self):
        proc = self.check("- x\nSECURITY_EFFECT: WEAKENS", {"REVISOR_CIEGO_ACK": "migración aprobada"})
        self.assertEqual(proc.returncode, 0)
        entry = self.log()[-1]
        self.assertEqual(entry["decision"], "acknowledged")
        self.assertEqual(entry["ack"], "migración aprobada")

    def test_reviewer_runs_only_after_passing_and_its_exit_code_wins(self):
        passed = self.check("SECURITY_EFFECT: NEUTRAL", {"REVISOR_CIEGO_REVIEWER_CMD": "sh -c 'exit 7'"})
        self.assertEqual(passed.returncode, 7)
        marker = os.path.join(self.repo, "reviewer-ran")
        blocked = self.check("SECURITY_EFFECT: WEAKENS",
                             {"REVISOR_CIEGO_REVIEWER_CMD": "touch %s" % marker})
        self.assertEqual(blocked.returncode, 1)
        self.assertFalse(os.path.exists(marker))

    def test_model_failure_blocks_by_default_and_allows_when_configured(self):
        self.assertEqual(self.check("no tag").returncode, 2)
        self.assertEqual(self.check("no tag", {"REVISOR_CIEGO_ON_ERROR": "allow"}).returncode, 0)

    def test_commit_message_never_reaches_the_gate(self):
        # El pase a ciegas solo lee `git diff --cached`; no hay forma de pasarle texto del autor.
        proc = self.check("SECURITY_EFFECT: NEUTRAL")
        self.assertEqual(proc.returncode, 0)
        chunks = self.log()[-1]["chunks"]
        self.assertEqual(chunks[0]["paths"], ["db.py"])

    def test_install_writes_an_executable_hook(self):
        proc = subprocess.run([sys.executable, SCRIPT, "install"], cwd=self.repo,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        hook = os.path.join(self.repo, ".git", "hooks", "pre-commit")
        self.assertTrue(os.access(hook, os.X_OK))
        with open(hook, encoding="utf-8") as fh:
            self.assertIn("revisor_ciego.py", fh.read())

    def test_no_staged_changes_is_a_pass(self):
        self.run_git("reset", "-q", "--hard")
        self.assertEqual(self.check("SECURITY_EFFECT: WEAKENS").returncode, 0)


if __name__ == "__main__":
    unittest.main()
