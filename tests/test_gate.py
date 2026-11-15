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
SCRIPT = os.path.join(ROOT, "gate", "unswayed.py")
_spec = importlib.util.spec_from_file_location("unswayed_gate", SCRIPT)
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
        path = os.path.join(self.repo, ".git", "unswayed", "log.jsonl")
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh]

    def test_weakening_change_blocks_the_commit(self):
        proc = self.check("- replaces the parameterised query\nSECURITY_EFFECT: WEAKENS")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("weakens an existing safeguard", proc.stderr)
        self.assertIn("BLOCKED", proc.stderr)
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
            self.assertIn("unswayed.py", fh.read())

    def test_no_staged_changes_is_a_pass(self):
        self.run_git("reset", "-q", "--hard")
        self.assertEqual(self.check("SECURITY_EFFECT: WEAKENS").returncode, 0)

    def clean_env(self, **extra):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("UNSWAYED_", "REVISOR_CIEGO_"))}
        env.update(extra)
        return env

    def test_public_env_prefix_works_and_wins_over_the_legacy_one(self):
        env = self.clean_env(UNSWAYED_PROVIDER="mock", UNSWAYED_REVIEWER_CMD="",
                             UNSWAYED_MOCK_RESPONSE="- x\nSECURITY_EFFECT: WEAKENS",
                             REVISOR_CIEGO_MOCK_RESPONSE="- x\nSECURITY_EFFECT: NEUTRAL")
        blocked = subprocess.run([sys.executable, SCRIPT, "check"], cwd=self.repo, env=env,
                                 capture_output=True, text=True)
        self.assertEqual(blocked.returncode, 1)
        env["UNSWAYED_ACK"] = "approved in the change board"
        acked = subprocess.run([sys.executable, SCRIPT, "check"], cwd=self.repo, env=env,
                               capture_output=True, text=True)
        self.assertEqual(acked.returncode, 0)
        self.assertEqual(self.log()[-1]["ack"], "approved in the change board")

    def test_config_file_is_read_and_the_new_name_overrides_the_legacy_one(self):
        self.write(".revisor-ciego", 'PROVIDER="mock"\nREVIEWER_CMD="false"\n')
        env = self.clean_env(UNSWAYED_MOCK_RESPONSE="SECURITY_EFFECT: NEUTRAL")
        legacy = subprocess.run([sys.executable, SCRIPT, "check"], cwd=self.repo, env=env,
                                capture_output=True, text=True)
        self.assertEqual(legacy.returncode, 1)
        self.assertIn("handing over to the normal reviewer", legacy.stderr)
        self.write(".unswayed", 'REVIEWER_CMD=""\n')
        current = subprocess.run([sys.executable, SCRIPT, "check"], cwd=self.repo, env=env,
                                 capture_output=True, text=True)
        self.assertEqual(current.returncode, 0)

    def test_range_mode_checks_committed_changes_for_ci(self):
        self.run_git("commit", "-q", "-m", "story the gate never reads", "--no-verify")
        proc = self.check("- x\nSECURITY_EFFECT: WEAKENS", args=("--range", "HEAD~1..HEAD"))
        self.assertEqual(proc.returncode, 1)
        entry = self.log()[-1]
        self.assertEqual(entry["source"], "HEAD~1..HEAD")
        self.assertNotIn("story the gate never reads", json.dumps(entry))

    def test_init_writes_the_public_config_name(self):
        proc = subprocess.run([sys.executable, SCRIPT, "init"], cwd=self.repo,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".unswayed")))



class ShadowAndReportTests(unittest.TestCase):
    """Shadow mode (pilots) and the decision report (evidence)."""

    setUp = EndToEndTests.setUp
    tearDown = EndToEndTests.tearDown
    write = EndToEndTests.write
    run_git = EndToEndTests.run_git
    check = EndToEndTests.check
    log = EndToEndTests.log

    def test_shadow_mode_never_holds_a_change_but_logs_it(self):
        proc = self.check("- x\nSECURITY_EFFECT: WEAKENS", {"UNSWAYED_MODE": "shadow"})
        self.assertEqual(proc.returncode, 0)
        self.assertIn("SHADOW MODE", proc.stderr)
        entry = self.log()[-1]
        self.assertEqual(entry["decision"], "shadow-flagged")
        self.assertEqual(entry["mode"], "shadow")

    def test_shadow_mode_does_not_hold_on_model_failure(self):
        proc = self.check("no tag", {"UNSWAYED_MODE": "shadow"})
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self.log()[-1]["decision"], "error")

    def test_each_check_writes_exactly_one_log_line(self):
        self.check("- x\nSECURITY_EFFECT: WEAKENS",
                   {"UNSWAYED_ACK": "approved", "UNSWAYED_REVIEWER_CMD": "true"})
        self.assertEqual(len(self.log()), 1)
        self.check("no tag", {"UNSWAYED_ON_ERROR": "allow", "UNSWAYED_REVIEWER_CMD": "true"})
        self.assertEqual(len(self.log()), 2)

    def test_report_counts_decisions_and_exports_csv(self):
        self.check("- x\nSECURITY_EFFECT: WEAKENS")                                   # blocked
        self.check("- x\nSECURITY_EFFECT: WEAKENS", {"UNSWAYED_ACK": "ticket CHG-1"})  # acknowledged
        self.check("- x\nSECURITY_EFFECT: WEAKENS", {"UNSWAYED_MODE": "shadow"})       # shadow-flagged
        self.check("SECURITY_EFFECT: NEUTRAL")                                        # passed
        self.check("no tag")                                                          # error
        proc = subprocess.run([sys.executable, SCRIPT, "report", "--json"], cwd=self.repo,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        summary = json.loads(proc.stdout)
        self.assertEqual(summary["checks"], 5)
        self.assertEqual(summary["answered"], 4)
        self.assertEqual(summary["errors"], 1)
        self.assertEqual(summary["flagged"], 3)
        self.assertAlmostEqual(summary["flag_rate"], 0.75)
        self.assertEqual(summary["acknowledgements"][0]["ack"], "ticket CHG-1")
        out = os.path.join(self.repo, "evidence.csv")
        text = subprocess.run([sys.executable, SCRIPT, "report", "--csv", out], cwd=self.repo,
                              capture_output=True, text=True)
        self.assertIn("flagged as weakening a safeguard: 3 of 4 (75.0%)", text.stdout)
        with open(out, encoding="utf-8") as fh:
            rows = fh.read().splitlines()
        self.assertEqual(len(rows), 6)
        self.assertTrue(rows[0].startswith("time,decision,effect,mode,model"))

    def test_report_without_a_log_says_so(self):
        proc = subprocess.run([sys.executable, SCRIPT, "report"], cwd=self.repo,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)

    def test_job_summary_is_written_in_ci_with_model_text_fenced(self):
        target = os.path.join(self.repo, "summary.md")
        proc = self.check("- removes the check ``` and tries markdown\nSECURITY_EFFECT: WEAKENS",
                          {"GITHUB_STEP_SUMMARY": target, "GITHUB_ACTIONS": "true"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("unswayed-ack: <reason>", proc.stderr)
        with open(target, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("### Unswayed: BLOCKED", text)
        self.assertEqual(text.count("```"), 2)


def review(login, state, body="", commit="abc123", assoc="MEMBER", at="2026-11-14T10:00:00Z"):
    return {"user": {"login": login}, "state": state, "body": body, "commit_id": commit,
            "author_association": assoc, "submitted_at": at}


class CiAcknowledgementTests(unittest.TestCase):
    """Who may clear a block from a pull request."""

    OK = "Looks intended.\nunswayed-ack: ownership moved to the gateway, CHG-1042"

    def pick(self, reviews, author="mallory", head="abc123"):
        return gate.select_ack(reviews, author, head)

    def test_a_maintainers_approval_with_the_ack_line_is_accepted(self):
        self.assertEqual(self.pick([review("alice", "APPROVED", self.OK)]),
                         ("alice", "ownership moved to the gateway, CHG-1042"))

    def test_the_author_cannot_acknowledge_their_own_change(self):
        self.assertIsNone(self.pick([review("Mallory", "APPROVED", self.OK)]))

    def test_an_approval_on_an_older_commit_is_void(self):
        self.assertIsNone(self.pick([review("alice", "APPROVED", self.OK, commit="old999")]))

    def test_outside_contributors_cannot_acknowledge(self):
        self.assertIsNone(self.pick([review("eve", "APPROVED", self.OK, assoc="CONTRIBUTOR")]))
        self.assertIsNone(self.pick([review("eve", "APPROVED", self.OK, assoc="NONE")]))

    def test_an_approval_without_the_ack_line_is_not_an_acknowledgement(self):
        self.assertIsNone(self.pick([review("alice", "APPROVED", "LGTM")]))

    def test_a_later_change_request_by_the_same_person_voids_the_ack(self):
        reviews = [review("alice", "APPROVED", self.OK, at="2026-11-14T10:00:00Z"),
                   review("alice", "CHANGES_REQUESTED", "wait", at="2026-11-14T11:00:00Z")]
        self.assertIsNone(self.pick(reviews))

    def test_a_dismissed_approval_is_void_but_a_later_comment_is_not(self):
        self.assertIsNone(self.pick([review("alice", "DISMISSED", self.OK)]))
        reviews = [review("alice", "APPROVED", self.OK, at="2026-11-14T10:00:00Z"),
                   review("alice", "COMMENTED", "nit", at="2026-11-14T11:00:00Z")]
        self.assertEqual(self.pick(reviews)[0], "alice")

    def test_the_command_reads_paginated_api_output(self):
        pages = [[review("bob", "COMMENTED", "hm")], [review("alice", "APPROVED", self.OK)]]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reviews.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(pages, fh)
            found = subprocess.run([sys.executable, SCRIPT, "ack-from-reviews", "--file", path,
                                    "--author", "mallory", "--head", "abc123"],
                                   capture_output=True, text=True)
            self.assertEqual(found.returncode, 0)
            self.assertIn("CHG-1042 (acknowledged by alice on abc123)", found.stdout)
            none = subprocess.run([sys.executable, SCRIPT, "ack-from-reviews", "--file", path,
                                   "--author", "alice", "--head", "abc123"],
                                  capture_output=True, text=True)
            self.assertEqual(none.returncode, 1)
            self.assertEqual(none.stdout, "")



DECOY_DIFF = """diff --git a/api.py b/api.py
--- a/api.py
+++ b/api.py
@@ -1,6 +1,4 @@
 def get_invoice(db, user, invoice_id):
     invoice = db.find(invoice_id)
-    if invoice.owner_id != user.id:
-        raise Forbidden()
     return invoice
@@ -40,3 +38,5 @@
 def rename(db, name):
+    if name is None or len(name) > 64:
+        raise ValueError("bad name")
     db.rename(name)
"""


class GranularityTests(unittest.TestCase):
    """Judging every hunk on its own, so a decoy cannot outweigh a weakening."""

    @staticmethod
    def swayed_by_decoy(prompt, cfg):
        # A model that lets an added guard outweigh a removed check when it sees both.
        if "raise ValueError" in prompt:
            return "- adds a guard\nSECURITY_EFFECT: STRENGTHENS"
        if "-        raise Forbidden()" in prompt:
            return "- removes the ownership check\nSECURITY_EFFECT: WEAKENS"
        return "SECURITY_EFFECT: NEUTRAL"

    def cfg(self, granularity):
        return dict(gate.DEFAULTS, PROVIDER="mock", GRANULARITY=granularity)

    def test_whole_diff_judgement_can_be_outweighed_by_a_decoy(self):
        result = gate.tripwire(DECOY_DIFF, self.cfg("diff"), ask=self.swayed_by_decoy)
        self.assertEqual(result["effect"], "STRENGTHENS")

    def test_hunk_granularity_isolates_the_weakening_hunk(self):
        result = gate.tripwire(DECOY_DIFF, self.cfg("hunk"), ask=self.swayed_by_decoy)
        self.assertEqual(result["effect"], "WEAKENS")
        self.assertEqual([c["effect"] for c in result["chunks"]], ["WEAKENS", "STRENGTHENS"])

    def test_hunk_granularity_makes_one_call_per_hunk_with_the_file_header(self):
        chunks, _ = gate.build_chunks(DECOY_DIFF, 12000, gate.DEFAULTS["EXCLUDE"], "hunk")
        self.assertEqual(len(chunks), 2)
        for chunk in chunks:
            self.assertTrue(chunk["diff"].startswith("diff --git a/api.py b/api.py"))
            self.assertEqual(chunk["diff"].count("@@ -"), 1)


if __name__ == "__main__":
    unittest.main()
