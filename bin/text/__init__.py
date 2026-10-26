"""The `text` of a source: the Markdown made from its best copy, so the librarian can read and search it.

    markdown(copy) -> str             the copy as Markdown, as a machine reads it unaided
    made_from(copy, proofs) -> str    a fingerprint of the copy and its proofs, as a text records it
    make(copy, proofs) -> Text        the text, and every way it falls short of its copy
    stamped(text, made) -> str        the text as written to `texts/`, headed by what it was made from
    current(path, made) -> bool       the text at `path` was made from what `made` fingerprints
    problems(path) -> list[str]       the shortfalls a written text records
    prepare(copy, proofs, work) -> list[int]               lay out the pages a proofreader must read
    accept(copy, proofs, work) -> dict[int, list[str]]     keep each page that checks out; flags for the rest

Every copy but a PDF becomes Markdown by pandoc, from an EPUB, which Calibre makes first for any other format,
and its text is checked word for word against the EPUB's pages. A PDF's text is assembled from its proofread
pages; a page not yet proofread contributes its own text layer, and the text says so.
"""

import hashlib
import json
import re
import tempfile
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from shell import run

from . import epub, pdf, proof

# Raise it whenever the way texts are made changes, so every text is made again.
VERSION: Final = 4
STAMP: Final = re.compile(r"<!-- commonplace text (\d+) of ([0-9a-f]+) by (\w+) -->")
PROBLEM: Final = re.compile(r"^<!-- problem: (.*) -->$")


@dataclass(frozen=True)
class Text:
    markdown: str
    method: str  # pandoc, proofread or machine
    problems: list[str]


def markdown(copy: Path) -> str:
    """The copy as Markdown, as a machine reads it unaided: a PDF's own text layer, anything else by pandoc."""
    if copy.suffix.lower() == ".pdf":
        return run("pdftotext", str(copy), "-")
    with as_epub(copy) as book:
        return epub.markdown(book)


def make(copy: Path, proofs: Path) -> Text:
    if copy.suffix.lower() == ".pdf":
        return pdf_text(copy, proofs)
    with as_epub(copy) as book:
        text = epub.markdown(book)
        return Text(text, "pandoc", epub.problems(book, text) or empty(text))


@contextmanager
def as_epub(copy: Path) -> Generator[Path]:
    """The copy as an EPUB: the copy itself, or one Calibre converts it into, for as long as it is needed."""
    if copy.suffix.lower() == ".epub":
        yield copy
        return
    with tempfile.TemporaryDirectory() as tmp:
        book = Path(tmp, "book.epub")
        run("ebook-convert", str(copy), str(book))
        yield book


def empty(markdown: str) -> list[str]:
    return (
        [] if markdown.split() else ["is empty, so its copy is flat: it needs proofreading or a better copy"]
    )


def unproofread(copy: Path, proofs: Path) -> Iterator[tuple[pdf.Page, proof.Proof | None]]:
    """Every page of the PDF, with the proof that fits it as it prints now, if one was saved."""
    for page in pdf.pages(copy):
        yield page, proof.load(proofs, page.number, page.fingerprint)


def pdf_text(copy: Path, proofs: Path) -> Text:
    """Every page proofread where a proof fits it as it prints now, its own text layer where none does."""
    layer = pdf.layer_by_page(copy)
    pieces, raw = [], []
    for page, saved in unproofread(copy, proofs):
        if saved:
            pieces.append(proof.apply(saved.draft, saved.ops).pieces)
        else:
            raw.append(page.number)
            marker = proof.Piece(f"<!-- pdf page {page.number}, not proofread -->", "marker")
            lines = layer[page.number - 1].splitlines() if page.number <= len(layer) else []
            pieces.append([marker] + [proof.Piece(line.strip()) for line in lines if line.strip()])
    text = proof.assemble(pieces)
    problems = [f"has {len(raw)} of its {len(pieces)} pages not proofread: {spans(raw)}"] if raw else []
    return Text(text, "machine" if raw else "proofread", problems + empty(text))


def spans(numbers: list[int]) -> str:
    """Page numbers as runs, such as 1-4, 7."""
    out: list[list[int]] = []
    for n in numbers:
        if out and n == out[-1][-1] + 1:
            out[-1].append(n)
        else:
            out.append([n])
    return ", ".join(f"{r[0]}-{r[-1]}" if len(r) > 1 else str(r[0]) for r in out)


def made_from(copy: Path, proofs: Path) -> str:
    """A fingerprint of everything a text is made from: the copy's bytes and every saved proof."""
    with copy.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    for saved in sorted(proofs.glob("*.json")) if proofs.is_dir() else []:
        digest.update(saved.name.encode() + saved.read_bytes())
    return digest.hexdigest()[:16]


def stamped(text: Text, made: str) -> str:
    head = [f"<!-- commonplace text {VERSION} of {made} by {text.method} -->"]
    head += [f"<!-- problem: {p} -->" for p in text.problems]
    return "\n".join(head) + "\n\n" + text.markdown


def current(path: Path, made: str) -> bool:
    if not path.exists():
        return False
    with path.open() as f:
        stamp = STAMP.match(f.readline())
    return bool(stamp) and int(stamp[1]) == VERSION and stamp[2] == made


def problems(path: Path) -> list[str]:
    """The shortfalls a written text records, from its head, without reading the rest."""
    found = []
    with path.open() as f:
        for line in f:
            if not line.startswith("<!-- "):
                break
            if match := PROBLEM.match(line.rstrip("\n")):
                found.append(match[1])
    return found


# --- proofreading -------------------------------------------------------------
# For each page `work` holds p0001.png (the page), p0001.draft.txt (numbered lines to proofread), and the
# two machine readings the result is checked against. A proofreader writes p0001.ops.json beside them.


def prepare(copy: Path, proofs: Path, work: Path) -> list[int]:
    """Lay out every page with no proof that fits it, and name them."""
    if copy.suffix.lower() != ".pdf":
        return []
    work.mkdir(parents=True, exist_ok=True)
    waiting = []
    for page, saved in unproofread(copy, proofs):
        if saved:
            continue
        reading = pdf.read(copy, page.number, work)
        stem = work / f"p{page.number:04d}"
        draft = "".join(f"{i:04d}\t{line}\n" for i, line in enumerate(reading.draft, 1))
        Path(f"{stem}.draft.txt").write_text(draft)
        Path(f"{stem}.layer.txt").write_text(reading.layer)
        Path(f"{stem}.vision.txt").write_text(reading.vision)
        waiting.append(page.number)
    return waiting


def accept(copy: Path, proofs: Path, work: Path) -> dict[int, list[str]]:
    """Check each page's operations; keep the proof of every page that passes, and return the flags of the rest."""
    flags = {}
    for page in pdf.pages(copy):
        stem = work / f"p{page.number:04d}"
        if not (ops := Path(f"{stem}.ops.json")).exists():
            continue
        draft = [row.split("\t", 1)[1] for row in Path(f"{stem}.draft.txt").read_text().splitlines()]
        candidate = proof.Proof(page.number, page.fingerprint, draft, json.loads(ops.read_text()))
        witnesses = [Path(f"{stem}.layer.txt").read_text(), Path(f"{stem}.vision.txt").read_text()]
        flagged = Path(f"{stem}.flags.json")
        if found := proof.check(candidate, witnesses):
            flags[page.number] = found
            flagged.write_text(json.dumps(found, indent=1, ensure_ascii=False))
        else:
            candidate.save(proofs)
            ops.rename(ops.with_suffix(".accepted"))
            flagged.unlink(missing_ok=True)
    return flags
