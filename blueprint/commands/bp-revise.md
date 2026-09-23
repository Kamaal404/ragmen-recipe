---
description: Revise an existing blueprint against evidence from a build or a drift report
argument-hint: <blueprint path> [drift report or symptom]
allowed-tools: Read, Write, Edit, Bash, Grep
---

Revise: **$ARGUMENTS**

Revision needs evidence. Ask for the drift report, validation output, or failing
golden-set items before changing anything. Editing an ontology on a hunch is how
blueprints accumulate types nobody can justify.

Map the symptom to a cause:

- **hairball, or undeclared labels** → `closed` is not holding, or patterns are
  not exhaustive. Check the pattern list covers every relationship.
- **duplicate entities** → resolution strategy or a missing vocabulary, not the
  ontology.
- **high unmapped mention rate** → the corpus has real concepts the ontology
  lacks. This is the case where adding a type is justified.
- **hub nodes** → resolution failure, or a legitimately central concept that
  belongs in `drift.max_degree_exempt`. Check which before acting.
- **retrieval misses obvious answers** → usually the workload and the embedding
  targets, not the node types.
- **the graph loses to the vector baseline on lookup** → the traversal is
  over-expanding. That is Serve's problem, not the blueprint's.

Bump `blueprint_version` correctly: major for changes that require re-extraction,
minor for additive types, patch for descriptions and non-semantic edits. Re-hash.
Say explicitly which already-ingested types are invalidated, because Forge uses
the stamped hash to decide what to re-extract.
