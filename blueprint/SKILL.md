---
name: blueprint
description: Design the knowledge-graph blueprint for a corpus before anything is ingested. Use this when someone wants to turn documents (laws, regulations, manuals, books, recipes, policies, standards, technical documentation) into a knowledge graph or GraphRAG system and there is no blueprint yet, or when an existing blueprint needs revising because extraction quality is poor, the graph came out as a hairball, entities are duplicated, or retrieval misses obvious answers. Covers corpus inspection, structure discovery, ontology design, embedding strategy, the query workload the graph must serve, and safety guardrails. Produces a spec-valid blueprint.yaml and stops for sign-off; it never ingests a corpus, writes to a database, or runs extraction at scale.
---

# Blueprint

Design time. You decide what the graph should be, write it down in a form a
machine can execute, and stop.

Two other components consume what you produce. **Forge** builds the graph from
it, unattended. **Serve** answers questions from it. Neither makes ontology
decisions. If either would have to decide what something *means*, the blueprint
is incomplete and that is your bug, not theirs.

## The one rule

**You never ingest a corpus, write to a database, or run extraction at scale.**

You read a sample, propose, and stop for sign-off. Extraction is where money is
spent and where a wrong ontology stays hidden for weeks. The sign-off gate is
not politeness; it is the only cheap moment to be wrong.

## What you produce

| File | What it is |
|---|---|
| `blueprints/<name>.yaml` | The contract. Must validate against `spec/blueprint.schema.json` |
| `blueprints/<name>.design-note.md` | Why each type exists |
| `vocab/<label>.csv` | Seed rows for controlled vocabularies, where the domain has one |
| `eval/<name>.jsonl` | The golden set, 30 to 50 labelled questions |

The design note is not paperwork. In six months someone will ask why two types
were not merged, and the answer will be gone. Write one line per type: what it
is, what question it answers, and what you considered merging it with.

## Sequence

Work in this order. Each step feeds the next, and skipping ahead to the ontology
is the single most common way to produce a blueprint that looks reasonable and
does not survive contact with the corpus.

### 1. Look at the actual text

```bash
python scripts/inspect_corpus.py --input <path> --show-sample
```

Never design from a filename, a title, or domain knowledge. Read real text. The
inspector reports heading families, proposes hierarchy regexes with matched
examples, flags front matter and indexes, strips page furniture, and lists
recurring noun phrases.

If it reports **NO TEXT LAYER**, stop. The document is scanned and needs OCR
first; everything downstream is worthless until that is fixed.

If it reports **NO HEADING STRUCTURE DETECTED**, read the sample yourself before
proposing anything. Continuous prose is a legitimate answer and changes the
chunking strategy entirely.

Treat the proposed regexes as candidates, not conclusions. Verify every
`example` line is real. See `references/structure_discovery.md` for what to do
when the obvious patterns do not fire.

### 2. Establish the workload before the ontology

This is the step people skip, and skipping it is why so many knowledge graphs
are elegant and useless.

Ask the user: **what questions must this answer?** Get 5 to 10 real ones, in
their words. Then sort them into shapes: lookup, multi-hop, aggregation,
negative, safety, comparison, temporal.

Two checks worth applying immediately:

- If none of the real questions need more than one hop, say so plainly. A vector
  store is cheaper, simpler and probably better. Recommending against building a
  graph is a legitimate and useful outcome of this skill.
- If every question is a lookup, the same applies.

The workload is what makes the ontology falsifiable. Without it, "is this a good
schema?" has no answer and the design conversation drifts into boxes and arrows.
See `references/workload_and_eval.md`.

### 3. Propose the ontology

Now, and not before. Derive types from the questions, then confirm they actually
appear in the corpus sample. The reverse order (types from frequency, questions
later) produces a graph that describes the text instead of serving the user.

Working ranges: 6 to 12 node types, 8 to 15 relationship types, an exhaustive
pattern list. For each node type, name the question it answers. A type that
cannot name one is a property.

Read `references/ontology_design.md` before this step. It covers node
granularity, the domain/range discipline that lets bad edges be dropped
mechanically, provenance, temporal validity, and worked examples.

### 4. Embedding strategy

What gets vectorised is a design decision, not an implementation detail.

Decide: which nodes get vectors, what text template builds each one, whether
facets get separate vectors, and which model. Include the hierarchy path in
chunk templates; `Article 12` without its breadcrumb is ambiguous.

See `references/embedding_strategy.md`.

### 5. Guardrails

Anything that must never leak (allergens, dietary flags, jurisdiction, in-force
dates, tenant visibility, safety warnings) is declared here and compiled into
Cypher by Serve. A prompt-level constraint can be talked around; a `WHERE` clause
cannot.

Also decide the conflict policy. Sources will disagree. `surface_both` with
attribution is the safe default; a safety corpus may want the stricter rule to
win. That is a domain decision and it belongs in the blueprint.

See `references/guardrails.md`.

### 6. Draft the golden set

30 to 50 questions with the chunk or node that should be retrieved. Cover every
declared shape, including at least one negative and, where relevant, one safety
question. Generating candidates from the corpus is fine and fast, but review
them: generated questions are biased toward what is easy to retrieve, which is
exactly the bias you are trying to measure.

### 7. Validate, then stop

```bash
python scripts/validate_blueprint.py blueprints/<name>.yaml --hash
```

Fix every error. Read every warning and either fix it or say why you are
accepting it. Then present to the user:

- the structure, with real matched examples
- each node and relationship type, with the question it answers
- the embedding plan
- the guardrails
- what you deliberately left out, and why
- an honest estimate of which workload shapes this will serve well and which it
  will not

**Then stop and ask for sign-off.** Do not proceed to Forge. Do not offer to
start ingestion in the same breath. Hand over the commands and let the user
decide when to spend.

## Judgment calls that come up every time

**"Should X be a node or a property?"** A node if it could be an answer unit and
it recurs across documents. Otherwise a property or an edge attribute. Quantity
is not a node. A date is not a node unless users ask what changed in 2019.

**"The corpus mentions Y a lot, shouldn't it be a type?"** Frequency shows what
the corpus talks about, not what users ask for. Check Y against the workload. If
no question needs it, it is background.

**"Can we add more types to be safe?"** No. Past roughly 15 node types the
extractor is choosing between near-synonymous labels and the choice becomes
arbitrary. More types is worse extraction, not richer data.

**"Two sources disagree."** That is data, not a problem to resolve at design
time. Set the conflict policy and let Forge record both with attribution.

**"The user wants to start now."** The inspector run costs nothing and takes a
minute. Do it. Designing from a description of the corpus rather than the corpus
is the most expensive shortcut available here.

## What you do not do

- Ingest, extract at scale, or write to any store. That is Forge.
- Write retrieval queries or tune traversal. That is Serve.
- Decide what a cheaper model would do to quality. That is a Forge measurement,
  made against the golden set you produced.
- Accept an open ontology. `closed: true` is not negotiable; an open schema is
  the single most common cause of a hairball graph.
