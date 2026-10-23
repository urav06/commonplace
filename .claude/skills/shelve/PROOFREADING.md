# Proofreading a PDF's text

A PDF's `text` starts as a machine draft. `proofreader` subagents read each page against its image and return operations; `bin/commonplace.py` applies them, checks every word against both machine readings of the page, and keeps each page that passes in Calibre's data folder for the book. A page proofread once stays proofread until the page itself changes, so a PDF is proofread once, at shelving.

1. **Lay out.** `bin/commonplace.py proofread SLUG` prints the work folder and the pages still to proofread, each laid out there as `p0001.png` and `p0001.draft.txt`. Done when you hold the list; an empty list means nothing is left.
2. **Dispatch.** One `proofreader` per source, given the work folder and its pages; a source past about fifteen pages gets one per run of about fifteen, all in parallel. Each run keeps its pages in context for the flags that follow, and a run much longer than that pays to re-read its growing context on every step. Done when every page has its `p0001.ops.json`. A proofreader stopped by the API's content filter gets its pages dispatched again in smaller runs; a page that fails twice goes in the report.
3. **Accept.** `bin/commonplace.py proofread SLUG --accept` keeps every page that passes, writes each other page's flags to `p0001.flags.json`, prints them, and re-derives. Done when it prints `{}`.
4. **Settle.** Send each run's flags back to the proofreader that read those pages, with SendMessage, so it judges them with the pages still in mind; then accept again. A proofreader that has ended gets a fresh one for its flagged pages. Done when accept prints `{}`, or a page keeps a flag through two rounds, which goes in the report.

The report names, per source, the pages proofread, the readings proofreaders confirmed off the image alone, and anything they chose that the brief did not foresee.
