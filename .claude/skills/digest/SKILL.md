---
name: digest
description: Digest a head's sources into its map.
disable-model-invocation: true
allowed-tools: Bash(bin/commonplace.py check-pages) Bash(grep *) Bash(python3 -I *)
---

To digest is Seneca's and Carruthers's word for making what one reads one's own: the bee does not carry flowers home, it makes honey. Here the librarian digests a head's `source`s into one `page`, the head's **map**, at `private/<head>/map.md`, or in place in `heads/<head>/` for a published head.

The map serves two readers with one representation:

- **The owner**, learning the head's question: what the sources fight over, where each stands, what is settled.
- **An agent in another repository**, reading the map first to gain a working intuition for the topic, and to know which source to open, where, and when its own problem calls for it.

Both need the same thing: the head's question made sharp, the lines the sources take sides on, the verdicts the evidence allows, and the way back to the texts. Every claim traces to a source, because the map is the one page other pages may build on (see `CLAUDE.md`). Its format, and the principles for choosing its forms, are in [MAP.md](MAP.md); read it before you write.

## What goes wrong, and why the steps are shaped as they are

A digest is itself a machine reading alongside a reader, so it fails the way the head on that subject found such readings fail:

- **Qualifications drop out, and they drop out one way.** A sentence that says "arguable", "not in all circumstances", or "we did not test this" fits no slot, so it falls away, and the losses lean toward whatever answer the frame expected. Carry every hedge a source puts on a claim it makes into the map with the claim, where [MAP.md](MAP.md) places it.
- **The frame smuggles in the conclusion.** A master axis chosen before reading counts the sources that disagree with it as dissenters. Let the distinctions come out of the reading, and check whether the question itself is ambiguous before answering it.
- **Voices blur.** Historians quote, editors gloss, dialogues stage views their authors reject. A claim belongs to whoever makes it: name the voice when it is not the author's.
- **A bridge word equivocates.** The claim that old argument and new measurement agree usually rests on one word, such as "memory" or "learning", that means one thing to a historian's sources and another to an experiment's measure. Before writing that two kinds of source converge, check what each one actually counts as the thing.
- **Novelty is claimed too easily.** "This is new" is the claim an agent will repeat. Check it against the head's historians before writing it.
- **The polish feels like truth.** A map reads as more certain than its sources. Standing marks and a critique by a reader who did not write it are what keep it honest.

## Steps

1. **Gather.** Read the head's `README.md` and confirm each slug under `sources` has its `text` at `texts/<slug>.md`. Note how each text marks places (printed pages, or only headings), since citations follow it. Done when you hold every slug, its length in words, and its kind of place; a slug with no text goes in the report and out of the digest.

2. **Read.** Read every source for the head's question, keeping notes outside the library, in your scratchpad: what each source claims, the distinctions it draws and which side it takes, the hedges it puts on itself, whose voice each passage is, and its place. Quote verbatim, with the text's line number, so the quote can be checked.
   - Read short sources whole yourself. You write the map, and nothing replaces having read its sources.
   - Hand long sources to `close-reader` subagents, a few sources each, grouped so each reader can compare like with like (the ancients together, the historians together), all in parallel. Your context cannot hold four long books and still write well, and readers starting cold bring the independence a seed vocabulary would otherwise steal. Give each the question, its slugs, and a notes path; never a list of expected terms.
   - Done when every source has notes that say what was read and what was skipped, and why.

3. **Find the lines.** From the notes, find where the sources part: each distinction they take sides on, which side each source takes, and how settled it is. Before that, ask whether the question itself splits, a key word in it meaning one thing to some sources and another to others; an ambiguity in the question often explains most of the disagreements, and the sharpened question leads the map. Under each disagreement, look for a test the opposed sides share and apply differently; it is often the most portable thing the map can say. Then choose the hard questions an agent or the owner would bring to this head, and the verdict the evidence allows on each. Done when every distinction names at least two sources on different sides, or says why one side stands alone, and every hard question has a verdict, a confidence, and the citations behind it.

4. **Ask, when a gap blocks.** When a verdict the head needs cannot be reached because the head lacks a kind of evidence, and a few named sources would supply it, ask the owner for them, saying what each would settle. Ask for the smallest set that would change a verdict; a gap that changes nothing goes in the map's open questions instead. Add what the owner agrees to under `wanted` in the README. Done when each blocking gap is either asked about or recorded as open.

5. **Write.** Write `map.md` to the format in [MAP.md](MAP.md). Then check it mechanically, with short `python3 -I` scripts, since a misquote or a wrong place is cheap to catch by program and costly to catch by eye:
   - each quotation beside a citation is found verbatim in that slug's text, after normalising quote marks, whitespace, emphasis, note markers and page markers;
   - each quotation cited to a section heading sits under that heading in the text, and each cited to a page sits after that page's marker.

   Done when the map is whole and both checks pass, or each miss is a script's artefact you have confirmed by hand.

6. **Compare, when the head already has pages.** A map from an earlier digest, or pages the head held before, are a second reading of the same sources. Read them only now, after your draft, so they cannot steer it. Then list what each got right that the other missed: a source's hedge, a distinction, a place, a use an agent would need. Carry over what holds, checking each claim against its text, not against the earlier page. Done when every difference is either merged or deliberately left out.

7. **Critique.** Dispatch one `critic` subagent, fresh, with the map's path and the head. It checks the map against the texts and reports; it never edits. A reader who did not write the map is the only one who will see what the writer's frame hid. Weigh each finding against the text yourself, fix what holds, and keep a line for each finding you reject and why. Fix an error where it lies: correct the claim rather than append a qualification to it, and put new support in the fold, since fixes that only add words make a map long without making it truer. Done when every finding is fixed or answered.

8. **Check.** Run `bin/commonplace.py check-pages`, and fix what it names. Done when it prints `no problems`.

9. **Report.** One message: where the map is; its question as sharpened; how long it runs, visible and folded; the critique's findings, with what you fixed and what you rejected and why; any sources you asked for; and the questions only the owner can answer.

## Learning, when the owner asks

The owner may ask to be quizzed on a head. Question them from the map's distinctions and verdicts, have them answer before you say anything, then send them to the cited passage that settles it. Ask in different forms, and come back later to what they missed: retrieval is what keeps, rereading is what feels like keeping. The owner's own notes are theirs to write; offer to check them against the texts when they have.
