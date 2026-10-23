"""An EPUB's text, by pandoc: MathML as LaTeX, every table whole, and every word on its pages kept."""

import html
import re
import tempfile
import unicodedata
import urllib.parse
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Final
from xml.etree import ElementTree

from shell import run

# fmt: off
# Pandoc's own Markdown, with no raw HTML left over.
MARKDOWN: Final      = "markdown" + "".join(f"-{x}" for x in (
    "raw_html", "native_divs", "native_spans", "fenced_divs", "bracketed_spans", "header_attributes",
    "link_attributes", "inline_code_attributes", "raw_attribute", "smart"))
FILTER: Final        = Path(__file__).with_name("epub-to-markdown.lua")
# Pandoc drops a note nothing links to, a note link, and a title page, so an EPUB's pages lose those marks first.
DROPPED: Final       = re.compile(
    r'\s(?:epub:type|role)="[^"]*\b(?:doc-)?(?:footnotes?|endnotes?|rearnotes?|noteref|titlepage|halftitlepage)\b[^"]*"')
# The words a text must keep from its EPUB: inline tags join their letters, other tags part them.
INLINE_TAG: Final    = re.compile(r"</?(?:abbr|b|cite|code|dfn|em|i|kbd|mark|q|s|samp|small|span|strong|u|var)\b[^>]*>")
UNSPOKEN: Final      = re.compile(r"<(head|script|style|math)\b.*?</\1>", re.DOTALL)
WORD: Final          = re.compile(r"[^\W\d_]+")
URL: Final           = re.compile(r"https?://\S+")
# A text may miss this share of its EPUB's words, which the comparison itself miscounts, and no more.
LOSS_ALLOWED: Final  = 0.001
# fmt: on


def markdown(copy: Path) -> str:
    """The EPUB as Markdown by pandoc, from pages stripped of the marks that make pandoc drop words."""
    with tempfile.TemporaryDirectory() as tmp:
        cleaned = Path(tmp, "book.epub")
        with zipfile.ZipFile(copy) as book, zipfile.ZipFile(cleaned, "w", zipfile.ZIP_DEFLATED) as out:
            for item in book.infolist():
                data = book.read(item)
                if item.filename.endswith((".xhtml", ".html", ".htm")):
                    data = DROPPED.sub("", data.decode("utf-8", "replace")).encode("utf-8")
                out.writestr(item, data)  # the item keeps its own compression, so `mimetype` stays stored
        return run(
            "pandoc", str(cleaned), "--from=epub", f"--to={MARKDOWN}", "--wrap=none", f"--lua-filter={FILTER}"
        )


def problems(copy: Path, text: str) -> list[str]:
    """Why the EPUB's text falls short of its pages: words lost beyond what the count itself miscounts."""
    lost, printed = lost_words(copy, text)
    return (
        [f"lacks {lost} of the {printed} words on its copy's pages"] if lost > LOSS_ALLOWED * printed else []
    )


def reading_order(book: zipfile.ZipFile) -> list[str]:
    """The EPUB's pages in its reading order, leaving out pages it marks as outside that order."""
    container = ElementTree.fromstring(book.read("META-INF/container.xml"))
    opf = next(e.get("full-path", "") for e in container.iter() if e.tag.endswith("rootfile"))
    package = ElementTree.fromstring(book.read(opf))
    hrefs = {e.get("id"): e.get("href", "") for e in package.iter() if e.tag.endswith("}item")}
    folder = PurePosixPath(opf).parent
    return [
        str(folder / urllib.parse.unquote(hrefs[e.get("idref")]))
        for e in package.iter()
        if e.tag.endswith("itemref") and e.get("linear") != "no" and e.get("idref") in hrefs
    ]


def lost_words(copy: Path, text: str) -> tuple[int, int]:
    """How many of the words on the EPUB's pages its text lacks, out of how many. Equations are not counted."""
    with zipfile.ZipFile(copy) as book:
        pages = [book.read(name).decode("utf-8", "replace") for name in reading_order(book)]
    printed = Counter[str]()
    for page in pages:
        printed.update(
            words(html.unescape(re.sub(r"<[^>]+>", " ", INLINE_TAG.sub("", UNSPOKEN.sub(" ", page)))))
        )
    kept = Counter(words(run("pandoc", "--from=markdown", "--to=plain", "--wrap=none", input=text)))
    return (printed - kept).total(), printed.total()


def words(text: str) -> list[str]:
    """The words of a passage, as both sides of the count read them: web addresses are not prose."""
    return [w.lower() for w in WORD.findall(unicodedata.normalize("NFKC", URL.sub(" ", text)))]
