# Ontology design

Read before proposing any node or relationship type.

## What earns a node

Both must be true:
1. It could be the answer unit to a real question in the declared workload.
2. It recurs across documents.

Everything else is a property on a node or an attribute on an edge. This single
rule prevents most schema bloat. Quantity does not become a `Quantity` node; it
becomes `amount` and `unit` on the edge. A date does not become a `Date` node
unless users ask "what changed in 2019".

**6 to 12 node types.** Past about 15, extraction quality drops measurably
because the model is choosing between near-synonymous labels and the choice
becomes arbitrary. If a domain seems to need 25, most of them are properties.

**8 to 15 relationship types.** Prefer a smaller set with typed properties over
near-duplicates. One `APPLIES_TO` with a `scope` property beats
`APPLIES_TO_PERSON`, `APPLIES_TO_ORG`, `APPLIES_TO_SECTOR`.

## Derive from questions, not from frequency

Types come from the workload. Then check they appear in the corpus. The reverse
order produces a graph that describes the text instead of serving the user, and
it is seductive because the inspector's noun-phrase list looks like an answer.

For each type, write the question it answers. If you cannot, it is a property.

## Domain and range discipline

Every relationship declares which source and target types are legal, as
`[Source, RELATION, Target]` triples in `ontology.patterns`.

This is the highest-leverage validation available. An edge that violates its type
signature can be dropped without a human reading it, which mechanically removes a
large share of extraction noise at zero cost.

Write the list exhaustively. A relationship with no declared pattern is
unconstrained, and the validator treats that as an error.

## Polarity deserves its own edge type

When a corpus says both "use X when Y" and "never use X when Z", resist encoding
that as one relationship with a `positive: false` property.

`SUITED_FOR` and `UNSUITED_FOR` as separate types means a query cannot forget to
check the sign. A negative recommendation is usually the thing you most need
retrieval to surface, and a boolean property is exactly the kind of thing a
traversal silently ignores.

## Provenance

Every extracted node and edge carries `source_id`, `chunk_id`, `char_start`,
`char_end`, and a verbatim `quote`.

For legal, regulatory, medical, safety and financial corpora this is the
difference between a system someone can rely on and one nobody is allowed to
deploy. "Where does it say that" must return a citation, not a paraphrase.

Set `provenance.require_page: true` for paginated sources. A page number is what
makes an answer checkable by someone holding the book.

## Temporal validity

Any corpus amended over time (law, policy, standards, terms of service) needs
`in_force_from` and `in_force_to` on the affected types, declared in
`ontology.temporal`.

Without it, repealed content answers queries and nobody notices until it matters.
Model amendments as edges between versions (`AMENDS`, `REPEALS`) rather than by
mutating the amended node; the history is the valuable part.

## Controlled vocabularies

For any type with a recurring entity appearing in many surface forms
(ingredients, drug names, part numbers, legal actor types), build the vocabulary
before ingesting anything.

Four tiers, first hit wins: exact, fuzzy, embedding, then an LLM fallback
**constrained to a shortlist**. Tier 4 must be closed-list; an open-ended "what
is this?" call reintroduces exactly the variance the vocabulary exists to remove.

Entities resolve against the list, never pairwise against each other. Pairwise
resolution drifts as the corpus grows; anchoring to a fixed list does not.

Seed from an authoritative external source where one exists. Hand-curating from
scratch is slow and leaves gaps you find in production.

## Descriptions are a cost

Every node and relationship description is sent to the extractor on every chunk.
On a real corpus the ontology block is often 40% or more of input tokens.

Write generous descriptions for the first run, because they steer extraction when
nothing has been tuned. Then trim them once the profile is proven. Flag this to
the user as a follow-up rather than optimising prematurely.

## Worked example: statutes

The atomic node is the **clause**, not the document and not the article.
Articles are frequently multi-part with independent obligations, and retrieving a
whole article to answer a question about one paragraph dilutes the context.

Types: `Act, Clause, Definition, Actor, Obligation, Condition, Sanction,
Authority, Jurisdiction`.

`CONTAINS`, `PARENT_OF`, `REFERS_TO`, `AMENDS`, `REPEALS` all come from the
deterministic parser. Only the obligation and condition structure needs a model.

## Worked example: practical manuals

The central node is the thing being built or done, with the materials, tools and
conditions hanging off it, plus an explicit hazard and mitigation pair.

Types: `Procedure, Technique, Material, Tool, Purpose, Condition, Hazard,
SafetyRule`. Quantities and stages go on edges.

Reachability matters here: hazard and mitigation must be one hop from the
procedure so a retrieval query can force-include them cheaply.

## Common failures

**A type that never connects.** If a node type appears in no pattern, nothing
will ever link to it and it will sit empty. The validator warns on this.

**A relationship that means two things.** `RELATED_TO` is not a relationship
type. If you cannot say what the edge asserts in one sentence, split it.

**Types that mirror document structure.** `Chapter` and `Section` are the
lexical graph, which Forge builds automatically. Do not declare them as ontology
types.

**Deterministic relations also asked of the model.** Anything in
`structure.xref_patterns` must appear in `ontology.deterministic_relations`, or
the extractor produces lower-precision duplicates of edges you already trust.
