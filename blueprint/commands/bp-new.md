---
description: Design a new blueprint for a corpus, from inspection through sign-off
argument-hint: <path to corpus dir or file>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

Design a blueprint for: **$ARGUMENTS**

Follow the sequence in SKILL.md. Do not skip ahead to the ontology.

1. `python blueprint/scripts/inspect_corpus.py --input <path> --show-sample`
   Read the output and read real text. If there is no text layer, stop and say so.

2. Ask the user for 5 to 10 real questions the graph must answer, in their own
   words. If none need more than one hop, say plainly that a vector store is the
   better tool. That is a legitimate outcome.

3. Read `references/ontology_design.md`, then propose types derived from those
   questions, naming for each the question it answers.

4. Embedding strategy, then guardrails, then draft the golden set.

5. `python blueprint/scripts/validate_blueprint.py blueprints/<name>.yaml --hash`
   Fix every error. Address every warning or say why you accept it.

6. Present the design and **stop for sign-off**. Do not begin ingestion, and do
   not offer to in the same message. Hand over the Forge commands and let the
   user decide when to spend.
