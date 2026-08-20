# Vector & Semantic Search in Craft ORM

Craft Engine natively supports **Vector / Semantic Search** directly within its Active Record query builder.

> **Where the arithmetic happens.** On PostgreSQL with the `vector` extension
> installed, these calls compile to pgvector's distance operators, so an HNSW
> index answers the query and the process never sees a row it did not ask for.
> Everywhere else the same calls fall back to scoring in Python, which reads the
> whole candidate set into the process — correct, and fine for development or a
> few thousand rows, but not a way to search a real corpus.
>
> Install the extension and index the column:
>
> ```python
> Schema.extension("vector")
> Schema.create_table("articles", lambda t: (
>     t.id(),
>     t.vector("embedding", 1536),
>     t.hnsw_index("embedding"),
> ))
> ```
>
> See [PostgreSQL](postgres.md#vectors).

## 🔎 Semantic Search with `where_vector_similar`

Filter database records by vector embedding similarity:

```python
from app.Models.Article import Article
from craft.facades import AI

# 1. Generate query embedding vector
query_vector = AI.embed("How to configure cloud database connections").vector

# 2. Query articles with minimum cosine similarity threshold
articles = Article.where_vector_similar("embedding", query_vector, min_similarity=0.75) \
    .where("published", True) \
    .limit(10) \
    .get()

for article in articles:
    print(article.title, article.similarity_score)
```

---

## 📈 Nearest Neighbor Ordering with `order_by_vector_similarity`

Sort results from most relevant to least relevant:

```python
results = Article.order_by_vector_similarity("embedding", query_vector).get()

top_match = results.first()
print(f"Top result: {top_match.title} (Score: {top_match.similarity_score})")
```
