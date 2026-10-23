"""The text module, through its interface: every word kept, every proofreading slip caught.

Run: uv run --python 3.14 --with pytest --with pypdf --with pyobjc-framework-Vision --with pyobjc-framework-Quartz pytest tests
"""

import sys
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bin"))

import text
from text import epub, pdf, proof

# --- an EPUB with everything pandoc would drop, unaided --------------------------------------------------------

CONTAINER = """<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>"""

OPF = """<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">x</dc:identifier>
<dc:title>Fixture</dc:title><dc:language>en</dc:language></metadata>
<manifest><item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>
<item id="body" href="body.xhtml" media-type="application/xhtml+xml"/>
<item id="pop" href="pop.xhtml" media-type="application/xhtml+xml"/>
<item id="img" href="fig.png" media-type="image/png"/></manifest>
<spine><itemref idref="title"/><itemref idref="body"/><itemref idref="pop" linear="no"/></spine></package>"""


def page(body: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"
xmlns:epub="http://www.idpf.org/2007/ops"><head><title>x</title></head><body>{body}</body></html>"""


TITLE = page('<section epub:type="titlepage"><h1>Fixture</h1><p>Translated by Quillon Marsh.</p></section>')
BODY = page("""<h2>Chapter one</h2>
<p>The orchard keeper counted <i>thirteen</i> pears.<a epub:type="noteref" href="#n1">1</a></p>
<p>The rule is <math xmlns="http://www.w3.org/1998/Math/MathML"><mi>x</mi><mo>=</mo><mn>2</mn></math> exactly.</p>
<figure><a href="pop.xhtml"><img src="fig.png" alt=""/></a><figcaption>Fig. 1. A ladder against the wall.</figcaption></figure>
<table><tbody>
<tr><td epub:type="z3998:persona">Socrates</td><td><p>Whence come you, my friend?</p></td></tr>
<tr><td epub:type="z3998:persona">Phaedrus</td><td><p>From the river.</p><p>And the plane tree.</p></td></tr>
</tbody></table>
<aside epub:type="footnote" id="n1"><p>Counted twice at dusk.</p></aside>
<div role="doc-footnote"><p>Unlinked author note about lanterns.</p></div>""")
POP = page("<p>A duplicate pop-up page outside the reading order.</p>")


@pytest.fixture
def book(tmp_path: Path) -> Path:
    path = tmp_path / "fixture.epub"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", CONTAINER)
        z.writestr("OEBPS/book.opf", OPF)
        z.writestr("OEBPS/title.xhtml", TITLE)
        z.writestr("OEBPS/body.xhtml", BODY)
        z.writestr("OEBPS/pop.xhtml", POP)
        z.writestr("OEBPS/fig.png", b"\x89PNG\r\n\x1a\n")
    return path


def test_epub_keeps_every_word(book: Path, tmp_path: Path) -> None:
    made = text.make(book, tmp_path / "no-proofs")
    for words in (
        "Translated by Quillon Marsh",
        "Counted twice at dusk",
        "Unlinked author note about lanterns",
        "A ladder against the wall",
        "**Socrates:** Whence come you",
        "And the plane tree",
    ):
        assert words in made.markdown
    assert "$x = 2$" in made.markdown
    assert made.problems == []
    assert made.method == "pandoc"


def test_epub_loss_is_reported(book: Path) -> None:
    assert epub.problems(book, "Chapter one only") != []


def test_stamp_is_current_until_the_copy_changes(book: Path, tmp_path: Path) -> None:
    proofs, written = tmp_path / "proofs", tmp_path / "fixture.md"
    made = text.made_from(book, proofs)
    written.write_text(text.stamped(text.make(book, proofs), made))
    assert text.current(written, made)
    book.write_bytes(book.read_bytes() + b"\0")
    assert not text.current(written, text.made_from(book, proofs))


def test_problems_survive_in_the_written_text(tmp_path: Path) -> None:
    written = tmp_path / "x.md"
    written.write_text(
        text.stamped(text.Text("words", "machine", ["has 2 of its 3 pages not proofread: 1-2"]), "f")
    )
    assert text.problems(written) == ["has 2 of its 3 pages not proofread: 1-2"]


# --- proofreading -----------------------------------------------------------------------------------------------

DRAFT = [
    "JOURNAL OF ORCHARDS 251",  # running head
    "Results",
    "The test was repeated, F(1, 117) 5 36.39, Zp 2 5 .24, which indi-",
    "cated a long-",
    "term effect.",
    "A new paragraph starts here and runs on to the next page with theorem-",
]


def test_operations_make_the_page() -> None:
    ops = [
        {"op": "insert", "after": 0, "markdown": "<!-- page 251 -->"},
        {"op": "delete", "from": 1, "to": 1},
        {"op": "heading", "line": 2, "level": 2},
        {
            "op": "edit",
            "line": 3,
            "find": "F(1, 117) 5 36.39, Zp 2 5 .24",
            "replace": "$F(1, 117) = 36.39$, $\\eta_p^2 = .24$",
        },
        {"op": "join", "lines": [4]},
        {"op": "para", "lines": [3, 6]},
    ]
    applied = proof.apply(DRAFT, ops)
    markdown = proof.assemble([applied.pieces])
    assert applied.problems == []
    assert "## Results" in markdown
    assert "JOURNAL" not in markdown
    assert "$F(1, 117) = 36.39$, $\\eta_p^2 = .24$, which indicated a long-term effect." in markdown


def test_proofs_saved_with_keep_hyphen_still_apply() -> None:
    applied = proof.apply(["a long-", "term effect"], [{"op": "keep_hyphen", "lines": [1]}])
    assert proof.assemble([applied.pieces]).strip() == "a long-term effect"


def test_a_failed_edit_or_unknown_operation_is_a_problem_not_a_silent_skip() -> None:
    applied = proof.apply(
        DRAFT, [{"op": "edit", "line": 3, "find": "not there", "replace": "x"}, {"op": "x"}]
    )
    assert len(applied.problems) == 2 and "not there" in applied.problems[0]


def test_a_paragraph_runs_across_the_page_turn() -> None:
    first = proof.apply(["ends with theorem-"], [{"op": "para", "lines": [1]}, {"op": "join", "lines": [1]}])
    second = proof.apply(["proving machines."], [{"op": "insert", "after": 0, "markdown": "<!-- page 5 -->"}])
    assert (
        proof.assemble([first.pieces, second.pieces]).strip()
        == "ends with theorem-proving <!-- page 5 --> machines."
    )


def test_a_word_broken_across_the_page_turn_is_rejoined() -> None:
    first = proof.apply(["the infor-"], [{"op": "para", "lines": [1]}])
    second = proof.apply(["mation given."], [{"op": "insert", "after": 0, "markdown": "<!-- page 5 -->"}])
    assert proof.assemble([first.pieces, second.pieces]).strip() == "the information <!-- page 5 --> given."


def test_a_wrapped_web_address_joins_when_marked() -> None:
    applied = proof.apply(
        ["See https://doi.org/10.1016/j.", "lindif.2014.05.002 for data."], [{"op": "join", "lines": [1]}]
    )
    assert "https://doi.org/10.1016/j.lindif.2014.05.002 for data." in proof.assemble([applied.pieces])


def test_a_rewrite_runs_on_in_its_paragraph_where_a_block_stands_alone() -> None:
    draft = ["Men will fill in the gaps, ei-", "garbled", "noise", "when the computer has no mode."]
    rewrite = {
        "op": "rewrite",
        "from": 2,
        "to": 3,
        "markdown": "ther in the problem solution or in the program,",
    }
    assert proof.assemble([proof.apply(draft, [rewrite]).pieces]).strip() == (
        "Men will fill in the gaps, either in the problem solution or in the program, when the computer has no mode."
    )
    block = {**rewrite, "op": "block", "markdown": "| a | b |"}
    assert proof.assemble([proof.apply(draft, [block]).pieces]).count("\n\n") == 2


def test_moves_put_columns_in_order() -> None:
    ops = [{"op": "move", "from": 2, "to": 2, "after": 0}, {"op": "para", "lines": [1, 2]}]
    markdown = proof.assemble([proof.apply(["right column", "left column"], ops).pieces])
    assert markdown.index("left") < markdown.index("right")


def test_check_flags_what_no_machine_read_until_confirmed() -> None:
    draft = ["F(1, 117) 5 36.39, Zp 2 5 .24"]
    ops = [
        {"op": "insert", "after": 0, "markdown": "<!-- page 1 -->"},
        {
            "op": "edit",
            "line": 1,
            "find": "F(1, 117) 5 36.39, Zp 2 5 .24",
            "replace": "$F(1, 117) = 36.39$, $\\eta_p^2 = .24$",
        },
    ]
    witnesses = ["F(1, 117) = 36.39, n,2 = 24", "F(1, 117) 5 36.39, Zp 2 5 .24"]
    flags = proof.check(proof.Proof(1, "f", draft, ops), witnesses)
    assert any("η" in f for f in flags)
    confirmed = [*ops, {"op": "confirm", "words": "η p"}]
    assert proof.check(proof.Proof(1, "f", draft, confirmed), witnesses) == []


def test_check_demands_a_page_marker() -> None:
    assert any("page marker" in f for f in proof.check(proof.Proof(1, "f", ["words"], []), ["words"]))


def test_proofs_are_found_only_for_the_page_as_it_prints(tmp_path: Path) -> None:
    proof.Proof(3, "abc", ["x"], []).save(tmp_path)
    assert proof.load(tmp_path, 3, "abc") is not None
    assert proof.load(tmp_path, 3, "changed") is None


def test_the_check_reads_the_page_as_a_reader_sees_it() -> None:
    page = (
        "<!-- page 3 -->\n\n> **Box 1** Offloading memory^2^ works, $\\beta_1 Condition_{ij}$, p &lt; 0.001."
        "\n\n> [Described by the librarian: a chart of nothing anyone printed]"
    )
    witnesses = [
        "Box 1 Offloading memory works, β1 Conditionij, p < 0.001.",
        "Box 1 Offloading memory works, p < 0.001.",
    ]
    assert proof.unsupported(proof.plain(page), witnesses, []) == []


def test_a_long_word_split_by_a_reading_still_counts() -> None:
    assert proof.unsupported("the information given", ["the infor\nmation given"], []) == []


# --- PDFs -------------------------------------------------------------------------------------------------------


def test_fingerprints_ignore_metadata(tmp_path: Path) -> None:
    first, second = tmp_path / "a.pdf", tmp_path / "b.pdf"
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    writer.write(first)
    writer.add_metadata({"/Title": "Rewritten by Calibre"})
    writer.write(second)
    assert [p.fingerprint for p in pdf.pages(first)] == [p.fingerprint for p in pdf.pages(second)]
