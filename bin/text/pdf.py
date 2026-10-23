"""A PDF's pages, and the machine readings of each: its own text layer, and Apple Vision's reading of its image.

A page's fingerprint hashes what the page prints, its content and images, and not the file around it, so
rewriting a PDF's metadata leaves every fingerprint, and every proofread page, as it was.
"""

import hashlib
import importlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from pypdf import PdfReader
from pypdf.generic import IndirectObject
from shell import run

# PyObjC builds Apple's frameworks into modules at run time, so no type checker can see what they hold.
Quartz: Any = importlib.import_module("Quartz")
Vision: Any = importlib.import_module("Vision")

# fmt: off
DPI: Final         = 200
# A page whose images cover this many pixels is a picture of its print: a scan.
SCAN_PIXELS: Final = 4_000_000
# Ligatures, the Alphabetic Presentation Forms of Latin, which a draft spells out letter by letter.
LIGATURES: Final   = range(0xFB00, 0xFB07)
# fmt: on


@dataclass(frozen=True)
class Page:
    number: int  # from 1
    fingerprint: str


@dataclass(frozen=True)
class Reading:
    """One page as the machines read it: a numbered draft to proofread, and both witnesses of its words.

    Neither reading knows the page's reading order or structure; the proofreader supplies both.
    """

    draft: list[str]
    layer: str  # the PDF's own text layer, as poppler reads it
    vision: str  # Apple Vision's reading of the page image, a line per line of print


def pages(copy: Path) -> list[Page]:
    """Every page of the PDF, with the fingerprint of what it prints."""
    return [Page(n, fingerprint(page)) for n, page in enumerate(PdfReader(copy).pages, 1)]


def images(page) -> list:
    """The images the page draws."""
    found = page.get("/Resources", {}).get("/XObject", {})
    return [
        (name, found[name].get_object() if isinstance(found[name], IndirectObject) else found[name])
        for name in sorted(found)
    ]


def fingerprint(page) -> str:
    """A hash of the page's content stream and every image it draws."""
    contents = page.get_contents()
    digest = hashlib.sha256(contents.get_data() if contents else b"")
    for name, image in images(page):
        digest.update(name.encode() + image._data)  # as stored: decoding a scan needs tools a hash does not
    return digest.hexdigest()[:16]


def is_scan(page) -> bool:
    """The page is a picture of its print, so any text layer it has is somebody's OCR."""
    return any(
        int(image.get("/Width", 0)) * int(image.get("/Height", 0)) > SCAN_PIXELS for _, image in images(page)
    )


def scanned_pages(copy: Path) -> int:
    return sum(map(is_scan, PdfReader(copy).pages))


def read(copy: Path, number: int, folder: Path) -> Reading:
    """Read one page both ways, leaving its image in `folder` as p0001.png for whoever proofreads it.

    A scan drafts from Vision, since its own text layer is somebody's old OCR; any other page from its text layer,
    whose characters are the typesetter's own.
    """
    image = render(copy, number, folder)
    layer = run("pdftotext", "-f", str(number), "-l", str(number), str(copy), "-")
    seen = vision(image)
    lines = seen if is_scan(PdfReader(copy).pages[number - 1]) else layer.splitlines()
    return Reading(draft=[spelled_out(line) for line in lines], layer=layer, vision="\n".join(seen))


def spelled_out(line: str) -> str:
    return "".join(unicodedata.normalize("NFKC", c) if ord(c) in LIGATURES else c for c in line)


def layer_by_page(copy: Path) -> list[str]:
    """The PDF's own text layer, a page at a time."""
    return run("pdftotext", str(copy), "-").split("\f")


def render(copy: Path, number: int, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stem = folder / f"p{number:04d}"
    page = ["-f", str(number), "-l", str(number)]
    run("pdftoppm", "-r", str(DPI), "-png", "-singlefile", *page, str(copy), str(stem))
    return stem.with_suffix(".png")


def vision(image: Path) -> list[str]:
    """The lines of print Apple Vision reads off the image, in its accurate mode, with the language detected."""
    url = Quartz.CFURLCreateFromFileSystemRepresentation(
        None, str(image).encode(), len(str(image).encode()), False
    )
    picture = Quartz.CGImageSourceCreateImageAtIndex(Quartz.CGImageSourceCreateWithURL(url, None), 0, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)
    request.setAutomaticallyDetectsLanguage_(True)
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(picture, None)
    succeeded, error = handler.performRequests_error_([request], None)
    if not succeeded:
        raise RuntimeError(f"Vision could not read {image.name}: {error}")
    return [line.topCandidates_(1)[0].string() for line in request.results() or []]
