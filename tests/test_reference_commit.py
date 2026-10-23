"""Exercise real commits in disposable repositories with the reference DOCX hook.

Run `uv run --no-project python -m unittest discover -s tests` from the template
repository. Each test installs the actual hook and commits real reference parts;
the user's repository, index, and Word documents are never modified.
"""

import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


SOURCE = Path(__file__).resolve().parent.parent


class ReferenceCommitTests(unittest.TestCase):
    """Check staged output, repeatability, and protection against data loss."""

    def setUp(self) -> None:
        """Create a disposable repository with the production hook enabled."""
        self.temporary = tempfile.TemporaryDirectory(prefix="reference-hook-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(SOURCE / "reference-doc", self.root / "reference-doc")
        shutil.copytree(SOURCE / ".githooks", self.root / ".githooks")
        shutil.copy2(SOURCE / "reference-doc.docx", self.root / "reference-doc.docx")
        (self.root / ".githooks/pre-commit").chmod(0o755)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Reference Hook Test")
        self.git("config", "user.email", "reference-hook@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "core.hooksPath", ".githooks")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial reference")

    def git(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run real Git operations and report complete diagnostics on failure."""
        result = subprocess.run(
            ["git", *arguments], cwd=self.root, capture_output=True,
        )
        if check and result.returncode:
            self.fail(result.stdout.decode(errors="replace") + result.stderr.decode(errors="replace"))
        return result

    def test_committed_package_uses_only_staged_parts(self) -> None:
        """Partial staging, added/deleted parts, and untracked files stay consistent."""
        styles = self.root / "reference-doc/word/styles.xml"
        staged = styles.read_bytes() + b"\n<!-- staged change -->\n"
        styles.write_bytes(staged)
        added = self.root / "reference-doc/word/new-part.xml"
        added.write_bytes(b"<new-part/>")
        self.git("add", "reference-doc/")
        self.git("rm", "reference-doc/word/webSettings.xml")
        unstaged = staged + b"<!-- unstaged change -->\n"
        styles.write_bytes(unstaged)
        (self.root / "reference-doc/untracked.xml").write_bytes(b"<untracked/>")
        self.git("commit", "--quiet", "-m", "Update staged reference")

        committed = self.git("show", "HEAD:reference-doc.docx").stdout
        with zipfile.ZipFile(io.BytesIO(committed)) as archive:
            self.assertEqual(archive.read("word/styles.xml"), staged)
            self.assertEqual(archive.read("word/new-part.xml"), b"<new-part/>")
            self.assertNotIn("word/webSettings.xml", archive.namelist())
            self.assertNotIn("untracked.xml", archive.namelist())
        self.assertEqual(styles.read_bytes(), unstaged)
        self.assertEqual(self.git("show", "HEAD:reference-doc/word/styles.xml").stdout, staged)
        before = committed
        (self.root / "notes.txt").write_text("Unrelated change", encoding="utf-8")
        self.git("add", "notes.txt")
        self.git("commit", "--quiet", "-m", "Unrelated change")
        self.assertEqual(self.git("show", "HEAD:reference-doc.docx").stdout, before)

    def test_unstaged_word_edits_stop_commit_without_data_loss(self) -> None:
        """A rebuild cannot overwrite a DOCX that the user has edited separately."""
        document = self.root / "reference-doc.docx"
        original_head = self.git("rev-parse", "HEAD").stdout
        edited = document.read_bytes() + b"unsaved Word changes"
        document.write_bytes(edited)
        styles = self.root / "reference-doc/word/styles.xml"
        styles.write_bytes(styles.read_bytes() + b"\n<!-- staged -->\n")
        self.git("add", "reference-doc/")
        result = self.git("commit", "--quiet", "-m", "Must fail", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Commit stopped", result.stderr)
        self.assertEqual(document.read_bytes(), edited)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, original_head)

    def test_missing_required_part_stops_commit(self) -> None:
        """An incomplete staged source tree cannot replace the valid package."""
        original = (self.root / "reference-doc.docx").read_bytes()
        original_head = self.git("rev-parse", "HEAD").stdout
        self.git("rm", "reference-doc/[Content_Types].xml")
        result = self.git("commit", "--quiet", "-m", "Must fail", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"Missing staged DOCX parts", result.stderr)
        self.assertEqual((self.root / "reference-doc.docx").read_bytes(), original)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, original_head)


if __name__ == "__main__":
    unittest.main()
