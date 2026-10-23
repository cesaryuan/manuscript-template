"""Generate and stage reference-doc.docx before a manuscript-template commit.

Run via the pre-commit hook (or `uv run --no-project --script
.githooks/build_reference_doc.py`) from this repository. The ZIP is assembled
from Git's index, so partially staged XML and untracked files cannot leak into
the commit. Unstaged DOCX edits stop the hook before any file is overwritten.
No Word or Pandoc process is started. Unchanged package contents retain the
existing DOCX bytes; changed packages use fixed timestamps and sorted entries.
"""

import io
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


LOGGER = logging.getLogger("reference-doc")
ROOT = Path(__file__).resolve().parent.parent
DOCUMENT = "reference-doc.docx"


def git(*arguments: str) -> bytes:
    """Run Git in the template repository, preserving a commit's temporary index."""
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def staged_sources() -> dict[str, bytes]:
    """Read source blobs from the index, rejecting unresolved or symlink entries."""
    sources = {}
    for record in git("ls-files", "--stage", "-z", "--", "reference-doc/").split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, object_id, stage = metadata.split()
        if stage != b"0" or mode not in (b"100644", b"100755"):
            raise RuntimeError("Resolve conflicts and use regular files in reference-doc/ first")
        name = raw_path.decode("utf-8").removeprefix("reference-doc/")
        sources[name] = git("cat-file", "blob", object_id.decode("ascii"))
    required = {"[Content_Types].xml", "_rels/.rels", "word/document.xml", "word/styles.xml"}
    if missing := required.difference(sources):
        raise RuntimeError(f"Missing staged DOCX parts: {', '.join(sorted(missing))}")
    return sources


def package_matches(package: bytes, sources: dict[str, bytes]) -> bool:
    """Compare package parts rather than ZIP metadata to avoid binary-only churn."""
    try:
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            names = archive.namelist()
            return (
                len(names) == len(sources)
                and set(names) == sources.keys()
                and all(archive.read(name) == content for name, content in sources.items())
            )
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
        return False


def build_package(sources: dict[str, bytes]) -> bytes:
    """Create a reproducible DOCX with uncompressed, already-compressed media."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for name, content in sorted(sources.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = (
                zipfile.ZIP_STORED if name.startswith("word/media/") else zipfile.ZIP_DEFLATED
            )
            archive.writestr(entry, content)
    return output.getvalue()


def main() -> None:
    """Synchronize the staged package while protecting unsaved worktree changes."""
    sources = staged_sources()
    indexed = bool(git("ls-files", "--", DOCUMENT))
    if indexed and package_matches(git("show", f":{DOCUMENT}"), sources):
        LOGGER.info("Staged reference-doc.docx already matches reference-doc/")
        return

    destination = ROOT / DOCUMENT
    # A DOCX edited in Word may contain work absent from the extracted XML.
    # Refuse to replace it until those edits have been imported or saved elsewhere.
    if indexed:
        if git("diff", "--name-only", "--", DOCUMENT):
            raise RuntimeError("reference-doc.docx has unstaged changes")
    elif destination.exists():
        raise RuntimeError("Move the untracked reference-doc.docx aside before committing")

    package = build_package(sources)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=ROOT, suffix=".docx", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(package)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    git("add", "--", DOCUMENT)
    LOGGER.info("Generated and staged reference-doc.docx from staged reference-doc/ files")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        LOGGER.error(
            "Commit stopped: %s\nPreserve any DOCX edits (apply-reference-doc-edits.ps1 "
            "imports them), stage the intended reference-doc/ files, then retry",
            error or "reference-doc.docx has unstaged changes",
        )
        raise SystemExit(1)
