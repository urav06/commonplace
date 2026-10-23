"""Proofreading a page: a proofreader's operations on a machine draft, applied, assembled and checked.

A proof is one page's draft with the operations that make it a faithful Markdown copy of the page, saved
against the page's fingerprint. A program applies them, so the same proof always gives the same text.

Operations, each on numbered draft lines:
    {"op": "edit", "line": N, "find": "…", "replace": "…"}   fix a misreading; `find` occurs in line N
    {"op": "delete", "from": N, "to": M}                     running heads, page numbers, stamps
    {"op": "move", "from": N, "to": M, "after": K}           reading order; K = 0 puts it first
    {"op": "block", "from": N, "to": M, "markdown": "…"}     standalone Markdown in place of lines N to M
    {"op": "rewrite", "from": N, "to": M, "markdown": "…"}   running text in place of lines N to M
    {"op": "insert", "after": N, "markdown": "…"}             a page marker (an HTML comment), or an addition
    {"op": "heading", "line": N, "level": L}
    {"op": "para", "lines": [N, …]}                           lines that start a paragraph
    {"op": "join", "lines": [N, …]}                           lines the next line runs on from with no space
    {"op": "confirm", "words": "…"}                           words read off the image that no machine read
`keep_hyphen` is the name `join` had before; proofs saved with it apply as they did.
"""

import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Final

from shell import run

# fmt: off
COMMENT: Final  = re.compile(r"<!--.*?-->", re.DOTALL)
# What the librarian adds is no reading of the page, so the check leaves it out.
ADDED: Final    = re.compile(r"^> \[(?:Described by the librarian|Figure, described by the transcriber):.*?\]$",
                             re.MULTILINE | re.DOTALL)
# Words, numbers, and the symbols that carry meaning; punctuation and leftover markup are no reading's business.
TOKEN: Final    = re.compile(r"[^\W\d_]+|\d+(?:\.\d+)?|\.\d+|[^\w\s.,;:!?'\"“”‘’„«»()\[\]{}\-–—/^*#|`~_\\]")
# Superscripts mark notes and powers, which machines seldom read, so the check leaves them out.
SUPERSCRIPT: Final = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ]+")
# A stretch this long, missing as a word, still counts when a reading spells it across a space or a hyphen.
SPLIT_WORD: Final = 5
# fmt: on


@dataclass(frozen=True)
class Proof:
    page: int
    fingerprint: str
    draft: list[str]
    ops: list[dict]

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        for stale in folder.glob(f"p{self.page:04d}-*.json"):
            stale.unlink()
        path(folder, self.page, self.fingerprint).write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=1)
        )


def path(folder: Path, page: int, fingerprint: str) -> Path:
    return folder / f"p{page:04d}-{fingerprint}.json"


def load(folder: Path, page: int, fingerprint: str) -> Proof | None:
    """The page's proof, if one was saved for the page as it prints now."""
    if not (saved := path(folder, page, fingerprint)).exists():
        return None
    return Proof(**json.loads(saved.read_text()))


# --- applying ---------------------------------------------------------------


@dataclass
class Piece:
    """One item of a page in reading order: a line of running text, a standalone block, or a page marker."""

    text: str
    kind: str = "line"  # line | block | marker
    starts: bool = False  # a line that starts a paragraph
    joins: bool = False  # the next line runs on from this one with no space


@dataclass
class Page:
    """A draft page while operations apply to it: its lines by number, and what each operation said of them."""

    lines: dict[int, str]
    kinds: dict[int, str]  # line | block | gone
    starts: set[int] = field(default_factory=set)
    joins: set[int] = field(default_factory=set)
    inserts: dict[int, list[Piece]] = field(default_factory=dict)
    order: list[int] = field(default_factory=list)


@dataclass
class Applied:
    pieces: list[Piece] = field(default_factory=list)
    confirmed: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def apply(draft: list[str], ops: list[dict]) -> Applied:
    """The page's pieces in reading order, after every operation; problems name the operations that failed."""
    page = Page(lines=dict(enumerate(draft, 1)), kinds=dict.fromkeys(range(1, len(draft) + 1), "line"))
    page.order = list(page.lines)
    out = Applied()
    for op in ops:
        if problem := one(op, page, out.confirmed):
            out.problems.append(problem)
    for op in (op for op in ops if op.get("op") == "move"):
        page.order = moved(page.order, op)
    out.pieces += page.inserts.get(0, [])
    for n in page.order:
        if page.kinds[n] != "gone" and page.lines[n].strip():
            kind = "line" if page.kinds[n] == "line" else "block"
            out.pieces.append(Piece(page.lines[n].strip(), kind, n in page.starts, n in page.joins))
        out.pieces += page.inserts.get(n, [])
    return out


def one(op: dict, page: Page, confirmed: list[str]) -> str | None:
    """Apply one operation to the page, or say why it cannot be applied."""
    kind = op.get("op")
    if (missing := [n for n in numbers(op) if n not in page.lines]) and kind != "insert":
        return f"{kind} names lines {missing} that the draft lacks"
    match kind:
        case "edit" if op["find"] not in page.lines[op["line"]]:
            return f"edit on line {op['line']}: {op['find']!r} is not in {page.lines[op['line']]!r}"
        case "edit":
            page.lines[op["line"]] = page.lines[op["line"]].replace(op["find"], op["replace"], 1)
        case "delete" | "block" | "rewrite":
            page.kinds.update(dict.fromkeys(range(op["from"], op["to"] + 1), "gone"))
            if kind != "delete":  # a block stands alone; a rewrite runs on in its paragraph like any line
                page.kinds[op["from"]] = "block" if kind == "block" else "line"
                page.lines[op["from"]] = op["markdown"]
        case "insert":
            text = op["markdown"].strip()
            piece = Piece(text, "marker" if COMMENT.fullmatch(text) else "block")
            page.inserts.setdefault(op["after"], []).append(piece)
        case "heading":
            page.kinds[op["line"]] = "block"
            page.lines[op["line"]] = "#" * op["level"] + " " + page.lines[op["line"]].strip()
        case "para":
            page.starts.update(op["lines"])
        case "join" | "keep_hyphen":
            page.joins.update(op["lines"])
        case "confirm":
            confirmed.append(op["words"])
        case "move":
            pass  # applied once every other operation has
        case _:
            return f"unknown operation {op!r}"
    return None


def numbers(op: dict) -> list[int]:
    """The draft lines an operation names."""
    named = [op[k] for k in ("line", "from", "to", "after") if isinstance(op.get(k), int)]
    return named + list(op.get("lines", []))


def moved(order: list[int], op: dict) -> list[int]:
    span = [n for n in order if op["from"] <= n <= op["to"]]
    rest = [n for n in order if n not in span]
    at = 0 if op["after"] == 0 else rest.index(op["after"]) + 1 if op["after"] in rest else len(rest)
    return rest[:at] + span + rest[at:]


# --- assembling -------------------------------------------------------------


def assemble(pages: list[list[Piece]]) -> str:
    """The pages as one Markdown text.

    A paragraph runs on across lines and pages until a line starts a new one. A line marked to join runs into the
    next with no space. A line-end hyphen before a lowercase line is a word broken by the typesetter, so it goes.
    A page marker inside a running paragraph lands after the word that spans the page turn, so the word stays whole.
    """
    blocks, para, waiting, joins = [], "", [], False
    for piece in (p for page in pages for p in page):
        if piece.kind == "block":
            blocks, para = [*flushed(blocks, para, waiting), piece.text], ""
        elif piece.kind == "marker" and para:
            waiting.append(piece.text)
        elif piece.kind == "marker":
            blocks.append(piece.text)
        elif piece.starts or not para:
            blocks, para = flushed(blocks, para, waiting), piece.text
        else:
            para = joined(para, piece.text, waiting, joins=joins)
        if piece.kind == "line":
            joins = piece.joins
    return "\n\n".join(flushed(blocks, para, waiting)) + "\n"


def flushed(blocks: list[str], para: str, waiting: list[str]) -> list[str]:
    """The blocks with the paragraph closed, and any page marker still waiting set after it."""
    out = [*blocks, para] if para.strip() else list(blocks)
    out += waiting
    waiting.clear()
    return out


def joined(para: str, line: str, waiting: list[str], *, joins: bool) -> str:
    """The paragraph with the next line joined on; page markers waiting at the join go after its first word."""
    if waiting:
        first, _, rest = line.partition(" ")
        line = " ".join([first, *waiting, rest]).rstrip()
        waiting.clear()
    if joins:
        return para + line
    if re.search(r"\w-$", para) and line[:1].islower():
        return para[:-1] + line
    return para + " " + line


# --- checking ---------------------------------------------------------------


def plain(markdown: str) -> str:
    """The proofread page as a reader sees it: the librarian's additions out, the markup gone, maths in Unicode."""
    return run("pandoc", "--from=markdown", "--to=plain", "--wrap=none", input=ADDED.sub(" ", markdown))


def tokens(text: str) -> list[str]:
    """The words, numbers and symbols a reader would compare."""
    text = SUPERSCRIPT.sub(" ", COMMENT.sub(" ", text).replace("[illegible]", " ").replace("[?]", " "))
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("‘", "'")
    return [t.lower() for t in TOKEN.findall(text)]


def unsupported(page_text: str, witnesses: list[str], confirmed: list[str]) -> list[str]:
    """Each stretch of the page's plain text holding words no machine reading has anywhere on the page.

    A word is supported while some reading holds it as often, anywhere: the readings know no reading order, and
    settling it is the proofreader's work. A word also counts when it, or it run into a neighbour, makes a long
    enough stretch that some reading spells with its spaces and hyphens squeezed out, as readings split words at
    line ends and glue subscripts on. What is left was read off the image alone: a fix to confirm, or an error.
    """
    mine = tokens(page_text)
    held = Counter[str]()
    for reading in witnesses:
        held |= Counter(tokens(reading))
    squeezed = " ".join(re.sub(r"[\s\-‐-]+", "", w.lower()) for w in witnesses)
    vouched = {t for words in confirmed for t in tokens(words)}
    missing = []
    for i, token in enumerate(mine):
        if held[token] > 0:
            held[token] -= 1
        elif token not in vouched and not spelled(mine, i, squeezed):
            missing.append(i)
    return list(stretches(mine, missing))


def spelled(mine: list[str], i: int, squeezed: str) -> bool:
    """Some reading spells the word, alone or run into a neighbour, once its spaces and hyphens are squeezed out."""
    before = mine[i - 1] + mine[i] if i > 0 else ""
    after = mine[i] + mine[i + 1] if i + 1 < len(mine) else ""
    return any(len(s) >= SPLIT_WORD and s in squeezed for s in (mine[i], before, after))


def stretches(mine: list[str], missing: list[int]) -> Iterator[str]:
    """Missing words grouped where they run together, each group shown in brackets with a word either side."""
    groups: list[list[int]] = []
    for i in missing:
        if groups and i - groups[-1][-1] <= 2:
            groups[-1].append(i)
        else:
            groups.append([i])
    for group in groups:
        start, end = group[0], group[-1] + 1
        yield " ".join(
            [*mine[max(start - 2, 0) : start], f"[{' '.join(mine[start:end])}]", *mine[end : end + 2]]
        )


def check(proof: Proof, witnesses: list[str]) -> list[str]:
    """Everything about a page's proof that the proofreader must look at on the page image before it is kept."""
    applied = apply(proof.draft, proof.ops)
    flags = list(applied.problems)
    flags += [
        f"no machine read the bracketed words in {s!r}; confirm them on the image or fix them"
        for s in unsupported(plain(assemble([applied.pieces])), witnesses, applied.confirmed)
    ]
    if not any(p.kind == "marker" for p in applied.pieces):
        flags.append("no page marker: insert the printed page number first, as <!-- page N -->")
    return flags
