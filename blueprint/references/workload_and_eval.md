# Workload and evaluation

The workload section is what turns ontology design from taste into engineering.

## Why it comes before the ontology

Without declared questions, "is this a good schema?" has no answer, and the
design conversation drifts into boxes and arrows that look reasonable and serve
nobody. With them, every later change is measurable.

Ask the user for 5 to 10 real questions in their own words. Not categories, not
"things about safety". Actual sentences someone would type.

## The shapes, and what each one proves

| Kind | Proves | Expectation |
|---|---|---|
| `lookup` | The graph did not make simple things worse | Plain vector RAG should match or beat it. If the graph loses badly, the traversal is over-expanding. |
| `multi_hop` | The graph is worth building at all | This is where it must clearly win |
| `aggregation` | Counting and filtering work | Needs a text-to-Cypher path, not traversal |
| `negative` | Exclusions hold | Any failure is a bug, not a tuning issue |
| `safety` | Warnings surface with methods | Release blocker where relevant |
| `comparison` | Parallel retrieval across entities | Often reveals missing symmetry in the ontology |
| `temporal` | Superseded content stays out | Only if the corpus is amended over time |

**Declare at least one `lookup` and one `multi_hop`.** The validator errors
without a `multi_hop` shape, and the reason is blunt: if no real question needs
more than one hop, a vector store is cheaper, simpler and probably better. Saying
so is a legitimate outcome of the design process.

## The honest baseline

Always measure plain vector RAG on the same corpus. GraphRAG costs meaningfully
more to build and run. If it does not beat the baseline on the declared shapes,
the schema is wrong, and more graph will not fix it.

Skipping the baseline is how projects spend six months proving something they
never tested.

## The golden set

30 to 50 items is enough to steer decisions. Format, one JSON object per line:

```json
{"id": "mh-004", "shape": "multi_hop", "q": "what do I burn for a cooking fire in wet conditions",
 "gold_chunks": ["c_8fa21b"], "gold_nodes": ["FireLay:log cabin"],
 "must_include": ["dry inner bark"], "must_not_include": []}
```

`must_not_include` is the field people leave empty and should not. For a safety
or exclusion question, what must *not* appear is the actual test.

## Generating candidates is fine, reviewing them is mandatory

Generating questions from chunks is fast and produces reasonable coverage. It is
also biased toward what is easy to retrieve, which is precisely the bias the
golden set exists to detect.

Review every generated item. Delete the ones that are answerable by copying one
sentence, unless they are the declared `lookup` shape.

## Measure retrieval separately from generation

Recall@k on the gold chunk tells you whether a bad answer was a retrieval miss or
a generation failure. Conflating them wastes days, and it is the most common
reason teams cannot say why their RAG got worse.
