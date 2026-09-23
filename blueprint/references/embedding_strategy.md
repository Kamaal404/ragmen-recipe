# Embedding strategy

What gets vectorised is a design decision. It belongs in the blueprint, not in
Forge's implementation.

## Include the hierarchy path

Embedding a chunk's raw text loses the one thing that disambiguates it. `Article
12` means nothing on its own; `Code du travail > Titre II > Chapitre 2 > Article
12` is retrievable.

```yaml
targets:
  - name: chunk_verbatim
    of: Chunk
    text: "{path}\n\n{text}"
```

The validator warns when a Chunk target omits `{path}`.

## Entity cards

Chunk vectors answer "where is this discussed". Entity vectors answer "what is
this thing", which is a different question and often the one users ask.

An entity card is a short synthetic text built from the node and its
neighbourhood:

```yaml
  - name: entity_card
    of: [Procedure, Technique]
    text: "{name}. {description}. Used for: {purposes}. Avoid when: {avoid_when}"
```

Build cards for the types users name directly. Skip them for types that only
ever appear as attributes of something else.

## Multi-vector facets

One blended vector per node averages away the thing being searched for. On
structured domains a query usually targets one aspect: what it is, what it
contains, what it is for.

Separate facet vectors, searched independently and fused, consistently
outperform a single blended vector on such corpora. Set `multi_vector: true` and
give each target a `facet`. The cost is more vectors and more index maintenance,
so it is worth it when queries genuinely target different aspects and wasteful
when they do not.

## Hybrid is not optional

Keep fulltext alongside vectors, fused with reciprocal rank fusion. Users type
exact identifiers (`article 42`, a part number) and short rare terms, and vector
similarity is mediocre at both. This matters more than people expect on
structured corpora.

## Model and dimensions

Dimensions must match the model exactly. A mismatch does not raise; it makes
every search return nothing, which is a miserable thing to debug from the query
side. The validator checks known models against declared dimensions.

Local sentence-transformers models are free, offline, and good enough for most
corpora. They also remove a second API vendor from the dependency list, which
matters when the extraction model comes from a provider with no embeddings API.

Changing the model later means dropping and rebuilding the index and re-embedding
everything. Decide deliberately; this is one of the more expensive things to
change after the fact.

## Cache by content hash

Never re-embed identical text. On re-ingest, corrected editions, and incremental
source updates, the cache is most of the saving. `cache: content_hash` is the
default and there is rarely a reason to turn it off.
