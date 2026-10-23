---
name: shelve
description: Shelve copies into the library. Use when copies wait in inbox/, or when a shelved source needs a better copy, a clean description, or a slug.
allowed-tools: Bash(bin/commonplace.py *) Bash(calibredb *) Bash(fetch-ebook-metadata *) Bash(ebook-convert *) Bash(ebook-meta *) Bash(sips *) Bash(unzip *) Bash(rm inbox/*) WebFetch(domain:api.openalex.org) WebFetch(domain:api.crossref.org) WebFetch(domain:standardebooks.org) WebFetch(domain:www.gutenberg.org)
hooks:
  Stop:
    - hooks:
        - type: command
          command: '"$CLAUDE_PROJECT_DIR"/bin/commonplace.py derive-from-calibre'
          once: true
---

`bin/commonplace.py` measures and writes. You judge, and you run from start to finish. A `copy` you do not shelve stays in the inbox for the report.

## Steps

1. **Measure.** Run `bin/commonplace.py inspect inbox/*`, and pass its `library` value as `--with-library` to every `calibredb` call. Unpack an archive and inspect what it held. Done when every `copy` has facts.
2. **Judge.** For each `copy`, name its `source`, judge how `lossy` and how `structured` it is, and whether it is `dirty`, from the facts and from reading `opening` and `middle`. Done when every `copy` has a `source` and those judgments.
3. **Hunt.** Find the best `copy` of each `source` that exists, so the verdict weighs this `copy` against it and the owner never has to research it. A paper: its DOI at `https://api.openalex.org/works/doi:DOI` lists every open copy with its version and licence, and only the published version is the same `source`. A public-domain book: Standard Ebooks, then Project Gutenberg. A book in copyright: `fetch-ebook-metadata -v` lists its editions, and the ebook ones by ISBN. Done when every `copy` has a verdict from the rules below, and every verdict that sends the owner hunting names the `copy` to fetch, where it is, and whether it is free.
4. **Clean.** Treat every description as a witness that can be wrong, the copy's own included. `fetch-ebook-metadata -v` writes every candidate from every catalogue to stderr before its single merge. Query by ISBN with `--cover DIR/calibre.jpg`, then by title and author. Keep refining, or narrow to one catalogue with `-p`, until the candidates agree with the `source` itself. Calibre also fills the title sort and author sort from the copy's own description, so check those too. Done when every field has a value you can trace.
5. **Name.** Give the `source` a slug: the first author's surname and the shortest unambiguous title, such as `blair-too-much-to-know`. A revised edition or a translation is its own `source`, so add what tells it apart, such as `carruthers-book-of-memory-2008`. Done when the slug is unique in the library.
6. **Cover.** In the same fresh folder per `copy`, add `bin/commonplace.py covers ISBN DIR` and `ebook-meta FILE --get-cover=DIR/own.jpg`. Look at each candidate and measure it with `sips -g pixelWidth -g pixelHeight`. Done when you have chosen the largest that shows this source's bare cover art, edge to edge.
7. **Shelve.** Write the `copy` into Calibre and describe it.
   - A new `source` goes in with `calibredb add FILE`, and a better `copy` of a shelved one with `calibredb add_format ID FILE`. Then remove the file from the inbox.
   - Write each field with `calibredb set_metadata ID --field name:value`, and the cover with `--field cover:FILE`.
   - Write identifiers with `bin/commonplace.py identify ID isbn:… slug:…`, which keeps the existing set. Every `source` stays private. Add `public:yes` only when the owner says the source may be named in public.
   - Record each copy's `origin` as one line per format, such as `EPUB: libgen.li`, with `calibredb set_custom origin ID "…"`. Replace the line for that format and keep the others. Take it from the owner's message or the filename, or write unknown and ask in the report.
   - When a head lists the `source` under `wanted`, move it to that head's `sources` by slug. A head in `heads/` is public, so there, move it only if the `source` is `public`, and otherwise ask in the report.
   - Finish with `calibredb embed_metadata ID`.

   Done when `calibredb list -s id:ID --fields title,authors,identifiers,cover,*origin` shows what you cleaned.
8. **Derive.** Run `bin/commonplace.py derive-from-calibre`. Done when nothing it reports concerns these copies, apart from pages not yet proofread.
9. **Proofread.** Every `source` whose `text` records pages not proofread gets proofread now, so its `text` is ready for close reading. See [PROOFREADING.md](PROOFREADING.md). Done when each such `text` records no page left, or the report names the page and why.
10. **Report.** One message: each `copy` shelved, with its slug, the fields the catalogues supplied, and how its `text` was made; then each `copy` left in the inbox, with its verdict and the `copy` to fetch instead, by ISBN or DOI, where it is and whether it is free.

## Verdicts

Judge the gap between this `copy` and the best `copy` likely to exist for its `source`. A born-digital book or a recent paper almost always has a `structured`, `lossless` one somewhere. Shelving makes derived copies, and each is only as good as this one.

- A small gap: shelve.
- A large gap, and a better `copy` is likely out there: leave it, and ask the owner to hunt for that copy, naming what to look for.
- A large gap, but nothing better is likely to exist, such as the only scan of an out-of-print book: shelve, and say so.
- A different `source` from the one the owner asked for, such as a translation of the book they named: leave it, and name the `source` to look for.
- `error` is present: leave it. No reader can open it, often because of DRM.
- Already shelved: shelve only a better `copy`, meaning more `lossless`, then more `structured`.

## Facts

- For a PDF, `words` counts its own text layer. `words` near zero, or `words_per_page` under about 50, means the `copy` is `flat`.
- `scanned_pages` counts pages that are pictures of their print. To judge how well a PDF reads, look at a page or two yourself: render one with `pdftoppm` and compare it with `pdftotext` for the same page. Proofreading repairs the `text` either way, so how a PDF reads weighs on how `lossy` and `structured` the `copy` is, never on whether it can be shelved.
- `toc_entries` and `internal_links` at 0 mean a weakly `structured` copy.
- `isbns_in_text` are candidates. Confirm each against the copyright page in `opening`, and use the ISBN of the `source` you hold.
- `already_shelved` matches by ISBN only. When it is empty, also search by title with `calibredb list -s 'title:"…"'`.
- The title page, which `opening` shows, decides the title, its casing, and the author's name as printed.
- Calibre's Tags field stays empty. Grouping lives in heads.
