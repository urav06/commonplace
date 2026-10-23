# commonplace

A personal library of curated reading, and the knowledge kept from it. `GLOSSARY.md` defines its terms.

The owner reads and asks. The librarian, a Claude Code session in this repo, keeps the library and writes pages when asked. `CLAUDE.md` gives the librarian its role.

## How it fits together

Calibre holds every source and its copies in `calibre/`. Two skills change it: `shelve` puts a copy in, and `withdraw` takes a source out. Each one then runs `bin/commonplace.py derive-from-calibre`, which writes the text of each source into `texts/` for the librarian to read, and repairs `shelf/`. Calibre itself is for reading. A change made there by hand reaches the rest at the next shelving.

A text is made by a program: pandoc for an EPUB, or any other format once Calibre has converted it to one. A PDF's text is proofread page by page while it is shelved: `proofreader` subagents correct the machine's reading against the page images, and the program checks every word they add against two machine readings of the page. Each proofread page is kept in the book's `data/` folder in Calibre, so a text can be remade from them without proofreading again.

`digest` reads a head's sources and writes its map: the head's question sharpened, the distinctions its sources take sides on, verdicts on its hard questions, and when to open each source. A reader who did not write it critiques it before it is done. The map serves the owner's own study, and an agent working elsewhere that needs the head's knowledge.

`shelf/` holds one link to each copy, named by slug, for opening in any reader. The owner can arrange the links into any folders, and keep anything else there too. Repairs touch only the library's own links, so keep their names.

Everything written lives in pages, and everything is private until the owner publishes it:

- `private/` holds private heads, one folder each, and loose pages. Git ignores it.
- `heads/` holds published heads. Publishing a head means moving its folder from `private/` to `heads/` and committing.

A head's `README.md` holds its `question`, the slugs of its `sources`, and `wanted`, the sources still wanted, in free text. Pages cite sources as `[@slug, place]`.

Every source is private too, until the owner marks it public with `bin/commonplace.py identify ID public:yes`. Before each commit, `bin/commonplace.py check-pages --staged` fails if a published page, as staged, cites a source the library lacks, names a source that is not public, or links into `private/`. Before each push it checks every commit about to be published, so a commit made with `--no-verify` cannot slip through. No copy or text ever enters this repo.

## Setup

Requires macOS with [Homebrew](https://brew.sh).

```
brew install --cask calibre
brew install uv poppler pandoc lefthook gitleaks ruff ty
```

uv fetches Python on first run.

Point Calibre at `calibre/` as its library. Under Preferences, Sharing over the net, Advanced, set the listening interface to `127.0.0.1` and allow unauthenticated local connections to make changes. Then start the Content server. Once, with Calibre closed, add the origin column:

```
calibredb --with-library calibre add_custom_column origin Origin comments
```

Run `lefthook install` once per clone.

Open the repo folder as an [Obsidian](https://obsidian.md) vault. `.obsidian/app.json` hides `calibre/`, `shelf/` and `texts/`, and writes links as paths from the vault root, so the commit check can see a link into `private/`.

## Licensing

Code and configuration are MIT. Everything else is CC BY-SA 4.0. Quoted passages belong to their authors and fall under neither license. See `REUSE.toml`.
