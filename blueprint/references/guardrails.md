# Guardrails

What must never leak, decided at design time and compiled into Cypher at query
time.

## Why not in the prompt

A prompt-level constraint is advisory. It can be talked around, and it degrades
silently under paraphrase, role-play, or a long conversation. A `WHERE` clause
cannot be talked around.

Anything used as a hard filter belongs as a graph property, queryable in Cypher:
allergens, dietary flags, jurisdiction, in-force dates, tenant visibility,
security classification, licence scope.

## The three modes

**`exclude`** removes matching results. Allergens, forbidden ingredients,
out-of-scope jurisdictions.

**`restrict`** limits to what the caller may see. Tenant and visibility scoping.
Declare this even for a single-user system if user-uploaded sources are on the
roadmap; retrofitting tenant isolation into a graph is a rewrite.

**`force_include`** pulls specified labels into every result regardless of
similarity. Hazards and safety rules. For a corpus where a method can hurt
someone, returning the method without the warning is worse than returning
nothing.

```yaml
guardrails:
  hard_filters:
    - name: allergen_exclusion
      mode: exclude
      params: [exclude_allergens]
      cypher: |
        NOT EXISTS {
          MATCH (r)-[:USES_INGREDIENT]->(:Ingredient)-[:CONTAINS_ALLERGEN]->(a:Allergen)
          WHERE a.name IN $exclude_allergens
        }
      rationale: Allergen exposure is a safety issue, not a preference.
    - name: hazards_always
      mode: force_include
      labels: [Hazard, SafetyRule]
      rationale: A method without its warning is worse than no answer.
```

Record a `rationale` for every filter. Six months later someone will want to
relax one for performance, and the rationale is what stops that being a casual
decision.

## Reachability constrains the ontology

A hard filter must be a cheap, obviously correct query. That is a real constraint
on the ontology, not an afterthought: if allergens are four hops from a recipe,
the filter is slow and easy to get subtly wrong.

Design the exclusion path to be one or two hops. When a guardrail is awkward to
express, the ontology is usually wrong.

## Release blockers

A safety filter with no automated leak suite is an intention, not a guarantee.
Name the suite in `release_blockers` and treat a failure as blocking.

The suite is adversarial by design: for every exclusion, a question that would
return the excluded thing if the filter were removed. That is the only way to
know the filter is doing anything.

## Conflict policy

Sources disagree. Two manuals give different ratios; two regulations conflict;
an older edition contradicts a newer one.

- `surface_both` (default): return both with attribution and let the reader judge.
  Right for most corpora, and the honest choice.
- `prefer_strictest`: for safety corpora where the cautious answer should win.
- `prefer_newest`: where recency is authority, with temporal validity enabled.
- `prefer_source_rank`: where sources have an explicit hierarchy.

This is a domain decision and it belongs here, not in Serve. Forge records
`asserted_by` on every edge regardless, so the policy can change without
re-ingesting.

## Answer policy

`refuse_outside_corpus: true` by default. For a corpus someone deliberately built
a graph from, falling back to general knowledge defeats the point and hides
retrieval failures behind fluent text.

`require_citation: true` by default. An uncited answer from a cited corpus is a
regression.
