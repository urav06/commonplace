---
name: withdraw
description: Withdraw a source from the library. Use when the owner wants something shelved gone.
allowed-tools: Bash(bin/commonplace.py *) Bash(calibredb list *)
---

`bin/commonplace.py withdraw SLUG` moves one `source` and its copies into Calibre's trash, removes its `text` and its shelf links, and checks every page. You settle what the withdrawal leaves behind.

## Steps

1. **Name.** Match the owner's words to a slug with `calibredb list --fields title,authors,identifiers`. Done when you hold the exact slug of each `source` to withdraw, or have asked the owner which they meant.
2. **Trace.** Search `heads/` and `private/` for each slug. Done when you have listed every head that names it under `sources`, and every `citation` of it with the `page` it sits on.
3. **Withdraw.** Run `bin/commonplace.py withdraw SLUG` for each slug. Done when each run printed `withdrew`.
4. **Settle.** Work through the heads the last run reported.
   - When the owner wants a better `copy` of the `source`, move it from the head's `sources` to `wanted`, as author and title.
   - Otherwise, take it off the head.
   - Leave every `citation` as it is, for the report.

   Done when the run reports only citations.
5. **Report.** One message: each `source` withdrawn, by slug and title; each head changed; then each `citation` left for the owner, which `bin/commonplace.py check-pages` names until they decide. Say that Calibre's trash still holds the copies.
