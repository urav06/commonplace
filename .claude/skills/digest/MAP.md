# The map's format

The map is read two ways: skimmed for its shape, then read closely where the reader's problem lands. So its visible text carries the reasoning in the librarian's words, and the evidence sits folded beneath each claim, one click away in Obsidian and plain blockquotes to an agent reading the raw file. A reader should be able to take in the visible map in one sitting and trust that every line of it opens onto a source.

## Shape

In this order, because each part leans on the one before:

```markdown
---
head: <head folder name>
built-from: [<every slug the map cites>]
digested: <date>, critiqued
---

# <The head's question, as a title>

<Summary: a few sentences that would serve a reader who reads nothing else.>

> [!note]- How to read this map
> <The standing marks, the citation form, where the texts are: `texts/<slug>.md` in the library.>

## The question
<The README's question, then the question as the sources sharpened it: the ambiguity it hid, the
sub-questions it splits into, what the owner must decide that the sources cannot.>

## Distinctions
<An at-a-glance view of them all, then one section each.>

## Hard questions
<One section each: the question, the verdict in bold, a confidence, the case.>

## Sources
<What each source is good for, when to open it, and where in it to look.>

## Open
<What the head's sources cannot answer, and what kind of source would.>
```

### The question

Sharpen, don't restate. A sharpened question names the ambiguity the sources exposed and says which reading each section serves. It says what only the owner can settle, such as what they read this head *for*.

### Distinctions

A distinction is a line the sources take sides on: what it asks, the sides, where each source stands, and how settled it is. They are the map's core, because they are what travels: an agent that holds the distinctions can reason about a problem the sources never saw.

For each:

- **What it asks**, as one question, then the sides in a sentence each.
- **Where each source stands.** A source that does not speak to it is left out, not marked neutral.
- **How settled**, with a standing mark and a line saying why.
- **What it means in use**: the test it gives someone with a problem in hand.
- **Evidence**, folded.

Lead the section with a table of every distinction, its sides and its standing, so the whole fight is visible before any part of it.

### Hard questions

The questions a reader brings to the head, answered. End with the practice that follows: what the owner would do differently, and what an agent or a tool acting on the topic should do, since an agent elsewhere reads the map to act, not only to understand. Each opens with a bold **verdict** and a **confidence** (high, medium, low) with its reason, then the case. Where the librarian reasons beyond what any source says, write "the librarian's inference" there; an agent elsewhere will otherwise take inference for finding.

### Sources

One entry per source: what it is (author, year, kind, and for a study its design, who, how many, how long, so the map stands alone where the text cannot be opened), what it is good for in this head, and when to open it, with the places that repay opening. This is how an agent elsewhere finds its way back to the texts.

## Length

A map should be as short as its head allows, because every line costs both readers: the owner's attention, and the context of an agent that loads the map before its own work. A long map also hides its load-bearing lines among the rest. No one length suits every head. Sources that fight on many lines need more words than sources that mostly agree, so judge a map by what each part carries, never by its size.

Words are earned by each distinct idea a reader needs, each place the sources disagree, and each qualification that changes what a claim licenses. They are not earned by restatement, by a distinction that is really a facet of another, or by evidence in the visible text that could sit in its fold. The visible text says what the evidence adds up to; a paragraph that lists sources, or restates a quotation above its callout, is evidence in the wrong place.

A hedge belongs in the visible claim when it changes what the claim means, such as its scope, its sample, or a missing control; its support, the quotation and the numbers, goes in the fold. Never cut a hedge outright. The summary at the top is the line most often repeated, so it must carry the limits of what it summarises.

## Standing marks

How settled a claim is, readable at a glance:

- ● **settled**: the sources that speak to it agree, and the strongest evidence the question admits (an experiment, a proof, a primary record) supports it.
- ◐ **leaning**: the weight falls one way, but the evidence is thin, indirect, narrow in scope, or some source dissents.
- ○ **open**: the sources split, or none decides it.

Mark the standing of the claim, never the importance of the topic. Reserve ● for what the evidence itself shows; agreement across eras without that evidence is ◐. Confidence on a verdict is the librarian's judgment of the answer; standing on a distinction is the state of the sources. Keep both.

## Choosing forms

Choose each form by the shape of what it shows, never by habit or for decoration:

- **Prose** carries reasoning: why, because, unless. Most of the map is prose.
- **A list** for items that are parallel and independent.
- **A table** when several items share the same attributes and the reader will compare across them: distinctions by side and standing, sources by what each is good for, studies by design and result. If a row would need a paragraph, it is not table-shaped.
- **A Mermaid diagram** only when the ideas are graph-shaped: relations that cross, branch or loop, so prose would make the reader rebuild a picture in their head, such as distinctions that depend on one another, a lineage of sources answering sources, or a causal chain with branches. A diagram that a sentence or a table could carry costs more to read than it gives; a line of boxes is a list. Each edge in a diagram is a claim, so show its standing: draw measured edges solid and argued or inferred ones dotted, and cite each edge in the evidence.
- **Callouts** for what most readers skip on most visits: evidence, method notes, the guide to reading the map.

## Evidence

Every claim carries a citation, `[@slug, place]`. The place is what a reader can find: a printed page where the text has page markers, otherwise the chapter and the section heading as the text prints it, or the letter, the dialogue, the section number.

Quote only where the exact words matter: a definition, a hedge, a striking formulation, a number, a claim someone might dispute. Otherwise paraphrase, with the citation. Name the voice when the words are not the author's own: a historian quoting an earlier writer, an editor's gloss, a speaker in a dialogue testing a view the author drops.

Fold evidence under the claim it supports:

```markdown
**Standing: ◐ leaning.** Two eras agree; no study here measures it.

> [!quote]- Evidence
> - <Author>: "<the words that matter>" [@<slug>, ch. 3, "<section heading>"].
> - <Author>, summarising <someone else>, <paraphrase> [@<slug>, p. 41].
```

A claim the visible text makes plainly still keeps its citation in the visible text when it is the kind an agent will repeat: a number, a verdict, a definition.
