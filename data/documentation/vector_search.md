# Vector & Semantic Search in Craft ORM

Craft Engine natively supports **Vector / Semantic Search** directly within its Active Record query builder.

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
