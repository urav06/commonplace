#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["pyyaml>=6", "pypdf>=5", "pyobjc-framework-Vision>=12", "pyobjc-framework-Quartz>=12"]
# ///
"""commonplace: the deterministic half of a personal library.

Calibre holds every `source` and its `copy` files in `calibre/`. This tool measures
copies, keeps `texts/` and `shelf/` true to Calibre, and checks pages. It decides
nothing: judgment belongs to whoever reads its output.

    commonplace.py inspect FILE...       Facts about each copy, as JSON.
    commonplace.py covers ISBN DIR       Download every cover the web holds for an ISBN into DIR.
    commonplace.py identify ID K:V...    Set identifiers, such as isbn:… slug:… public:yes, keeping the
                                         rest. An empty value, such as public:, removes one.
    commonplace.py derive-from-calibre   Write each source's text into `texts/`, repair `shelf/`, and check
                                         every page.
    commonplace.py proofread SLUG        Lay out every page of the source not yet proofread, for proofreaders.
    commonplace.py proofread SLUG --accept
                                         Save each page whose proofreading checks out, list the flags of the
                                         rest, then derive.
    commonplace.py withdraw SLUG         Move a source and its copies into Calibre's trash, then derive.
    commonplace.py check-pages           Check every page on disk.
    commonplace.py check-pages --staged  Check the public pages as staged for the next commit.
    commonplace.py check-pages --pushed  Check the public pages in every commit a `git push` is about to publish.

Reads come straight from Calibre's database. Writes go through `calibredb`, which
reaches the library through the GUI's Content server whenever the GUI holds it.
"""

import json
import os
import re
import socket
import sqlite3
import sys
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from collections.abc import Iterator
from contextlib import closing, suppress
from dataclasses import dataclass
from functools import cache
from pathlib import Path, PurePosixPath
from typing import Final

import text
import yaml
from pypdf.errors import PyPdfError
from shell import run
from text import pdf

# fmt: off
REPO: Final          = Path(__file__).resolve().parent.parent
LIBRARY: Final       = REPO / "calibre"
DATABASE: Final      = LIBRARY / "metadata.db"
SHELF: Final         = REPO / "shelf"
TEXTS: Final         = REPO / "texts"
PUBLIC: Final        = "heads"    # git tracks it, and the public repo shows it
PRIVATE: Final       = "private"  # git ignores it
SERVER: Final        = ("127.0.0.1", 8080)
PREFS: Final         = Path(os.environ.get("CALIBRE_CONFIG_DIRECTORY", "~/Library/Preferences/calibre")).expanduser()
PROOFREADING: Final  = Path(tempfile.gettempdir()) / "commonplace-proofread"  # pages laid out for proofreaders

# A source's text derives from the first of these it holds.
READABLE: Final      = ("EPUB", "AZW3", "MOBI", "PDF", "DJVU")
SLUG: Final          = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
# A pandoc citation is a bracket holding one or more @slug keys, such as [see @blair-too-much-to-know, ch. 2].
CITATION: Final      = re.compile(r"\[[^\[\]]*\]")
CITEKEY: Final       = re.compile(rf"(?<![\w.@])@({SLUG.pattern})")
# A wikilink or markdown link into the private folder.
PRIVATE_LINK: Final  = re.compile(r"(?:\[\[|\]\()[./]*private/")
# calibredb splits identifier lists on commas. An empty value removes the identifier.
IDENTIFIER: Final    = re.compile(r"[^:,]+:[^,]*")
# Printed ISBNs are hyphenated or solid.
ISBN_LIKE: Final     = re.compile(r"(?<![\d-])(?:\d-?){9,12}[\dXx](?![\d-])")
ISBN10_DIGITS: Final = "0123456789X"
COVER_URLS: Final    = (
    "https://covers.openlibrary.org/b/isbn/{isbn13}-L.jpg?default=false",
    "https://images-na.ssl-images-amazon.com/images/P/{isbn10}.01._SCRMZZZZZZ_.jpg",
)
# fmt: on


@dataclass(frozen=True)
class Source:
    """One source. Calibre calls it a book, and its copies formats."""

    id: int
    title: str
    folder: Path  # Calibre's folder for the book
    copies: dict[str, Path]  # by format
    identifiers: dict[str, str]

    @property
    def slug(self) -> str | None:
        return self.identifiers.get("slug")

    @property
    def public(self) -> bool:
        """The owner is content to have it named in public. Every source starts private."""
        return self.identifiers.get("public") == "yes"

    @property
    def readable(self) -> Path | None:
        return next(filter(None, map(self.copies.get, READABLE)), None)

    @property
    def text(self) -> Path:
        return TEXTS / f"{self.slug}.md"

    @property
    def proofs(self) -> Path:
        """Each proofread page, kept in Calibre's data folder for the book, so it moves and goes with it."""
        return self.folder / "data" / "proofs"


def sources() -> list[Source]:
    """Every source in the library."""
    if not DATABASE.exists():
        raise RuntimeError(f"no Calibre library in {LIBRARY}")
    with closing(sqlite3.connect(DATABASE.as_uri() + "?mode=ro", uri=True)) as db:
        formats: defaultdict[int, dict[str, str]] = defaultdict(dict)
        identifiers: defaultdict[int, dict[str, str]] = defaultdict(dict)
        for book, fmt, name in db.execute("SELECT book, format, name FROM data"):
            formats[book][fmt] = name
        for book, kind, value in db.execute("SELECT book, type, val FROM identifiers"):
            identifiers[book][kind] = value
        return [
            Source(
                id=id_,
                title=title,
                folder=LIBRARY / path,
                copies={f: LIBRARY / path / f"{name}.{f.lower()}" for f, name in formats[id_].items()},
                identifiers=identifiers[id_],
            )
            for id_, title, path in db.execute("SELECT id, title, path FROM books ORDER BY id")
        ]


def target() -> str:
    """Where `calibredb --with-library` points: the GUI's server while the GUI holds this library."""
    with socket.socket() as probe:
        server_up = probe.connect_ex(SERVER) == 0
    prefs = PREFS / "global.py.json"
    gui_library = json.loads(prefs.read_text()).get("library_path") if prefs.exists() else None
    if server_up and gui_library and Path(gui_library).resolve() == LIBRARY.resolve():
        # Naming the library makes a wrong server fail instead of answering.
        return f"http://{SERVER[0]}:{SERVER[1]}/#{LIBRARY.name}"
    return str(LIBRARY)


def calibredb(*args: str) -> str:
    return run("calibredb", "--with-library", target(), *args)


# --- ISBNs ------------------------------------------------------------------


def ean_sum(digits: str) -> int:
    return sum((3 if i % 2 else 1) * int(d) for i, d in enumerate(digits))


def isbn10_sum(digits: str) -> int:
    return sum((10 - i) * ISBN10_DIGITS.index(d) for i, d in enumerate(digits))


def isbn13(text: str) -> str | None:
    """The ISBN-13 written in `text`, accepting ISBN-10, or None when the check digit fails."""
    code = re.sub(r"[^\dX]", "", text.upper())
    if len(code) == 10 and code[:9].isdigit():
        stem = "978" + code[:9]
        return None if isbn10_sum(code) % 11 else stem + str(-ean_sum(stem) % 10)
    if len(code) == 13 and code.isdigit() and code.startswith(("978", "979")) and ean_sum(code) % 10 == 0:
        return code
    return None


def checked_isbn(text: str) -> str:
    """The ISBN-13 written in `text`, or an exit when its check digit fails."""
    if not (code := isbn13(text)):
        sys.exit(f"{text!r} fails its ISBN check digit")
    return code


def isbn10(code: str) -> str | None:
    """The ISBN-10 for an ISBN-13 that has one, which only the 978 range does."""
    if not code.startswith("978"):
        return None
    stem = code[3:12]
    return stem + ISBN10_DIGITS[-isbn10_sum(stem) % 11]


# --- sensors ----------------------------------------------------------------


def epub_facts(path: Path) -> dict[str, int]:
    with zipfile.ZipFile(path) as z:
        docs = [
            z.read(n).decode("utf-8", "replace")
            for n in z.namelist()
            if n.endswith((".xhtml", ".html", ".htm", ".ncx"))
        ]
    navs = [m for t in docs for m in re.findall(r'<nav[^>]*epub:type="toc".*?</nav>', t, re.DOTALL)]
    return {
        "toc_entries": sum(t.count("<navPoint") for t in docs) or sum(n.count("<a ") for n in navs),
        "internal_links": sum(len(re.findall(r'<a\s[^>]*href="(?!https?:|mailto:)', t)) for t in docs),
    }


def pdf_facts(path: Path) -> dict:
    pages = re.search(r"^Pages:\s+(\d+)", run("pdfinfo", str(path)), re.MULTILINE)
    outline = run("pdftohtml", "-xml", "-i", "-stdout", "-q", "-l", "1", str(path))
    return {
        "pages": int(pages[1]) if pages else 0,
        "toc_entries": outline.count("<item"),
    } | {"scanned_pages": pdf.scanned_pages(path)}


def inspect(path: Path, library: list[Source]) -> dict:
    facts: dict = {"file": str(path)}
    try:
        facts["format"] = kind = run("file", "-b", str(path)).strip()
        if kind.startswith("EPUB"):
            facts |= epub_facts(path)
        elif kind.startswith("PDF"):
            facts |= pdf_facts(path)
        facts["embedded"] = run("ebook-meta", str(path)).strip()
        reading = text.markdown(path)
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        return facts | {"error": str(error)}
    words = reading.split()
    facts["words"] = len(words)
    if facts.get("pages"):
        facts["words_per_page"] = round(len(words) / facts["pages"])
    # Front and back matter, where copyright pages live.
    facts["isbns_in_text"] = found = list(
        dict.fromkeys(c for m in ISBN_LIKE.findall(reading[:40_000] + reading[-20_000:]) if (c := isbn13(m)))
    )
    facts["already_shelved"] = [
        {"id": v.id, "slug": v.slug, "title": v.title, "copies": sorted(v.copies)}
        for v in library
        if isbn13(v.identifiers.get("isbn", "")) in found
    ]
    facts["opening"] = " ".join(words[:300])
    facts["middle"] = " ".join(words[len(words) // 2 : len(words) // 2 + 300])
    return facts


def fetch(url: str) -> bytes:
    """The body at `url`, or nothing when the request fails."""
    with suppress(OSError), urllib.request.urlopen(url, timeout=30) as reply:
        return reply.read()
    return b""


def covers(isbn: str, folder: Path) -> list[str]:
    """Every cover the web holds for the ISBN, saved into `folder`. Sites send tiny placeholders for none."""
    code = checked_isbn(isbn)
    ten = isbn10(code)
    urls = [url.format(isbn13=code, isbn10=ten) for url in COVER_URLS if ten or "{isbn10}" not in url]
    images = {folder / f"web-{i}.jpg": image for i, url in enumerate(urls) if len(image := fetch(url)) > 1000}
    folder.mkdir(parents=True, exist_ok=True)
    for cover, image in images.items():
        cover.write_bytes(image)
    return [str(cover) for cover in images]


# --- actuators --------------------------------------------------------------


def identify(source_id: int, pairs: list[str], library: list[Source]) -> None:
    """Merge identifiers into a source's set. A slug is checked, unique and permanent; an ISBN becomes ISBN-13."""
    if not (source := next((s for s in library if s.id == source_id), None)):
        sys.exit(f"no source with id {source_id}")
    if bad := [p for p in pairs if not IDENTIFIER.fullmatch(p)]:
        sys.exit(f"identifiers look like kind:value with no commas, not {bad[0]!r}")
    updates = {k.strip().lower(): v.strip() for k, v in (p.split(":", 1) for p in pairs)}
    if updates.get("isbn"):
        updates["isbn"] = checked_isbn(updates["isbn"])
    if updates.get("public", "yes") not in ("yes", ""):
        sys.exit("public is `public:yes`, or `public:` to make the source private again")
    if "slug" in updates and (problem := slug_problem(source, updates["slug"], library)):
        sys.exit(problem)
    # calibredb replaces the whole set, so send all of it.
    merged = ",".join(f"{k}:{v}" for k, v in (source.identifiers | updates).items() if v)
    calibredb("set_metadata", str(source_id), "--field", f"identifiers:{merged}")
    print(merged.replace(",", "\n"))


def slug_problem(source: Source, slug: str, library: list[Source]) -> str | None:
    """Why `slug` cannot name this source, if it cannot."""
    if not SLUG.fullmatch(slug):
        return f"{slug!r} is not a slug: lowercase words joined by hyphens"
    if source.slug and source.slug != slug:
        return f"source {source.id} is already {source.slug!r}, and slugs never change"
    if taken := next((s for s in library if s.slug == slug and s.id != source.id), None):
        return f"{slug!r} already belongs to source {taken.id}, {taken.title}"
    return None


def shelved_as(slug: str, library: list[Source]) -> Source:
    if not (source := next((s for s in library if s.slug == slug), None)):
        sys.exit(f"no source is shelved as {slug!r}")
    return source


def proofreading(slug: str, library: list[Source]) -> tuple[Path, Path, Path]:
    """The source's readable copy, where its proofs are kept, and where its pages are laid out for proofreaders."""
    source = shelved_as(slug, library)
    if not source.readable:
        sys.exit(f"{slug} has no readable copy")
    return source.readable, source.proofs, PROOFREADING / slug


def proofread(slug: str, library: list[Source]) -> dict:
    """Lay out every page of the source's readable copy that no proof fits, for proofreaders."""
    copy, proofs, work = proofreading(slug, library)
    return {"copy": str(copy), "work": str(work), "pages": text.prepare(copy, proofs, work)}


def accept(slug: str, library: list[Source]) -> dict[int, list[str]]:
    """Keep each page whose proofreading checks out; the flags of every page that does not."""
    return text.accept(*proofreading(slug, library))


def withdraw(slug: str, library: list[Source]) -> None:
    """Take a source out of Calibre, into Calibre's trash."""
    source = shelved_as(slug, library)
    calibredb("remove", str(source.id))
    print(f"withdrew {slug}: {source.title}")


def repair_shelf(shelved: list[Source]) -> list[str]:
    """`shelf/` is the owner's to arrange, flat or in folders. Each copy has a link there named `<slug>.<ext>`.

    Repair touches only the library's links: those named for a copy or pointing into `calibre/`. It re-points
    them, removes those whose copy is gone, and puts a missing one at the top. Returns what it had to leave.
    """
    copies = {f"{s.slug}.{fmt.lower()}": file for s in shelved for fmt, file in s.copies.items()}
    SHELF.mkdir(exist_ok=True)
    links = [path for path in SHELF.rglob("*") if path.is_symlink()]
    for link in links:
        points_to, wanted = link.readlink(), copies.get(link.name)
        if (wanted or points_to.is_relative_to(LIBRARY)) and points_to != wanted:
            link.unlink()
            if wanted:
                link.symlink_to(wanted)
    left = []
    for name in sorted(copies.keys() - {link.name for link in links}):
        try:
            (SHELF / name).symlink_to(copies[name])
        except FileExistsError:
            left.append(f"shelf/{name} is taken by something that is not a link, so {name} has no link")
    return left


def refresh_text(source: Source, copy: Path) -> list[str]:
    """Write the source's text unless it was made from this copy and its proofs as they stand. Returns every way
    the text falls short, as the text itself records them."""
    try:
        made = text.made_from(copy, source.proofs)
        if not text.current(source.text, made):
            source.text.write_text(text.stamped(text.make(copy, source.proofs), made))
    except (OSError, RuntimeError, zipfile.BadZipFile, PyPdfError) as error:
        return [f"{source.slug} has no text: {error}"]
    return [f"{source.slug}'s text {problem}" for problem in text.problems(source.text)]


# --- pages ------------------------------------------------------------------

type Pages = dict[PurePosixPath, str]  # each page's text, by its path in the repo


def pages_on_disk() -> Pages:
    """Every page in the working tree, public and private."""
    files = (file for folder in (PUBLIC, PRIVATE) for file in (REPO / folder).rglob("*.md"))
    return {PurePosixPath(file.relative_to(REPO).as_posix()): file.read_text() for file in files}


def git(*args: str) -> str:
    return run("git", "-C", str(REPO), *args)


@cache
def blob(sha: str) -> str:
    """A page's text by its git blob id. A push reads each distinct page once, however many commits hold it."""
    return git("cat-file", "blob", sha)


def pages_in_git(rev: str) -> Pages:
    """Every public page in a git commit or tree. Nothing private is ever in git. An unknown rev fails."""
    tree = git("rev-parse", "--verify", f"{rev}^{{tree}}").strip()
    entries = (
        entry.split("\t", 1) for entry in git("ls-tree", "-r", "-z", tree, "--", PUBLIC).split("\0") if entry
    )
    return {PurePosixPath(path): blob(meta.split()[2]) for meta, path in entries if path.endswith(".md")}


def pushed() -> list[str]:
    """The commits a `git push` is about to publish, from the lines git hands its pre-push hook on stdin."""
    tips = [fields[1] for line in sys.stdin if len(fields := line.split()) == 4 and fields[1].strip("0")]
    return git("rev-list", "--abbrev-commit", *tips, "--not", "--remotes").split() if tips else []


def frontmatter(text: str) -> dict | None:
    """The YAML block at the top of a page, or None when it is missing or unreadable."""
    if match := re.match(r"---\n(.*?)\n---\n", text, re.DOTALL):
        with suppress(yaml.YAMLError):
            meta = yaml.safe_load(match[1]) or {}
            return meta if isinstance(meta, dict) else None
    return None


def cited(text: str) -> list[str]:
    """The slugs a page cites, in order of first citation."""
    return list(dict.fromkeys(key for group in CITATION.findall(text) for key in CITEKEY.findall(group)))


def naming(where: str, slugs: list, named: set[str], allowed: set[str]) -> Iterator[str]:
    """Each slug that is not in the library, or not allowed where it appears."""
    for slug in slugs:
        if slug not in named:
            yield f"{where} {slug!r}, which is not in the library"
        elif slug not in allowed:
            yield f"{where} {slug!r}, which is not public"


def check_head(readme: PurePosixPath, text: str | None, named: set[str], allowed: set[str]) -> Iterator[str]:
    """A head's README holds a question, its sources by slug, and wanted sources in free text."""
    if text is None:
        yield f"{readme.parent} is a head with no README.md"
    elif (meta := frontmatter(text)) is None:
        yield f"{readme} has no readable frontmatter"
    else:
        if not isinstance(meta.get("question"), str):
            yield f"{readme} needs a `question:`"
        if not all(isinstance(meta.get(key) or [], list) for key in ("sources", "wanted")):
            yield f"{readme} needs `sources:` and `wanted:` as lists"
        elif sources := meta.get("sources"):
            yield from naming(f"{readme} lists under `sources:`", sources, named, allowed)


def place(page: PurePosixPath) -> tuple[str, PurePosixPath | None]:
    """The side a page is on, public or private, and the head it belongs to: its first folder there, if any."""
    side, *inside = page.parts
    return side, PurePosixPath(side, inside[0]) if len(inside) > 1 else None


def check_page(page: PurePosixPath, text: str, named: set[str], allowed: set[str]) -> Iterator[str]:
    """Every source a page cites is in the library and allowed. A public page sits in a head and keeps private/ out."""
    side, head = place(page)
    if side == PUBLIC and head is None:
        yield f"{page} is a public page outside any head; move it into a head, or into {PRIVATE}/"
    if side == PUBLIC and PRIVATE_LINK.search(text):
        yield f"{page} links into {PRIVATE}/"
    yield from naming(f"{page} cites", cited(text), named, allowed)


def problems_in(pages: Pages, library: list[Source]) -> Iterator[str]:
    """Every head and page in the set. A public one may name only public sources, a private one any shelved one."""
    named = {slug for s in library if (slug := s.slug)}
    public = {slug for s in library if (slug := s.slug) and s.public}
    allowed = {PUBLIC: public, PRIVATE: named}
    for side, head in sorted({(side, head) for side, head in map(place, pages) if head}):
        readme = head / "README.md"
        yield from check_head(readme, pages.get(readme), named, allowed[side])
    for page, body in sorted(pages.items()):
        yield from check_page(page, body, named, allowed[place(page)[0]])


# --- sync ---------------------------------------------------------------------


def shelving_problem(source: Source, library: list[Source]) -> str | None:
    """Why a source cannot go on the shelf yet, if it cannot."""
    if not source.slug:
        return f"source {source.id} has no slug yet"
    if not source.readable:
        return f"{source.slug} has no readable copy"
    return slug_problem(source, source.slug, library)


def derive() -> list[str]:
    library = sources()
    checked = [(s, shelving_problem(s, library)) for s in library]
    shelved = [(s, copy) for s, problem in checked if not problem and (copy := s.readable)]
    TEXTS.mkdir(exist_ok=True)
    unreadable = [p for s, copy in shelved for p in refresh_text(s, copy)]
    unshelved = repair_shelf([s for s, _ in shelved])
    for orphan in set(TEXTS.glob("*.md")) - {s.text for s, _ in shelved}:
        orphan.unlink()
    return [*(p for _, p in checked if p), *unreadable, *unshelved, *problems_in(pages_on_disk(), library)]


def check_pages(snapshots: list[tuple[str, Pages]]) -> int:
    """Check each snapshot of the pages. A snapshot's label, such as its commit, starts each of its problems."""
    try:
        library = sources()
    except RuntimeError:
        # A clone without the owner's library has nothing to check citations against.
        print("no Calibre library, so no pages checked", file=sys.stderr)
        return 0
    return report(
        [f"{label}{problem}" for label, pages in snapshots for problem in problems_in(pages, library)]
    )


def report(problems: list[str]) -> int:
    print("\n".join(problems) or "no problems", file=sys.stderr)
    return 1 if problems else 0


def main() -> int:
    try:
        match sys.argv[1:]:
            case ["inspect", *files] if files:
                library = sources()
                print(
                    json.dumps(
                        {"library": target(), "files": [inspect(Path(f), library) for f in files]},
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            case ["covers", isbn, folder]:
                print("\n".join(covers(isbn, Path(folder))))
            case ["identify", source_id, *pairs] if pairs and source_id.isdigit():
                identify(int(source_id), pairs, sources())
            case ["proofread", slug]:
                print(json.dumps(proofread(slug, sources()), indent=2))
            case ["proofread", slug, "--accept"]:
                print(json.dumps(accept(slug, sources()), indent=2, ensure_ascii=False))
                return report(derive())
            case ["withdraw", slug]:
                withdraw(slug, sources())
                report(derive())
            case ["derive-from-calibre"]:
                return report(derive())
            case ["check-pages"]:
                return check_pages([("", pages_on_disk())])
            case ["check-pages", "--staged"]:
                return check_pages([("", pages_in_git(git("write-tree").strip()))])
            case ["check-pages", "--pushed"]:
                return check_pages([(f"{rev} ", pages_in_git(rev)) for rev in pushed()])
            case _:
                sys.exit(__doc__)
    except (RuntimeError, OSError, sqlite3.Error) as error:
        sys.exit(str(error))
    return 0


if __name__ == "__main__":
    sys.exit(main())
