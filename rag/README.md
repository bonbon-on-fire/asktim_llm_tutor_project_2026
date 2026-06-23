# rag

Retrieval-Augmented Generation over course materials (Phase 11 — see root
[PLANNING.md](../PLANNING.md)).

Instead of dumping every lecture transcript into every tutor call (~125k tokens,
~17× cost/message for `cities_and_climate_change`), the tutor retrieves only the
handful of chunks relevant to the current student turn.

## What is and isn't ingested

- **Ingested (retrievable):** course description (`course.txt`), syllabus
  (`syllabus.txt`), lectures (`lectures/*.txt`), and OCW pages — pulled from the
  local files, the course's OCW site (`online_link.txt`), or both.
- **Never ingested:** the **exercise** (`exercises/exercise_XX.txt`, kept local
  and always in context verbatim) and **figures** (handled by the multimodal
  pipeline).

## Build an index

```powershell
# from the repo root
python -m rag.ingest --course cities_and_climate_change --source local
python -m rag.ingest --course mathematics_for_cs        --source ocw
python -m rag.ingest --course <course>                  --source both
```

`--source` is a toggle: `local` (curriculum files), `ocw` (crawl the course's
`online_link.txt`), or `both`. OCW needs `beautifulsoup4`. Output lands in
`curriculum/<course>/rag_index/` (`vectors.npy` + `chunks.jsonl` +
`manifest.json`) and is meant to be committed so deploys don't re-embed.

## Retrieve (used by the tutor)

```python
from rag import retrieve, format_context, has_index

if has_index(course):
    chunks = retrieve(course, student_message, k=6)
    block = format_context(chunks)   # injected on the latest student turn
```

## Layout

| File | Role |
| ---- | ---- |
| `chunking.py` | sentence-aware splitter → `Chunk(text, source, course, index)` |
| `embeddings.py` | OpenAI `text-embedding-3-small` batch embedder |
| `store.py` | numpy cosine store (`vectors.npy` + `chunks.jsonl` + `manifest.json`) |
| `sources.py` | local reader: `course.txt` / `syllabus.txt` / `lectures/*.txt` |
| `ocw.py` | OCW crawler (reads `online_link.txt`; needs `beautifulsoup4`) |
| `ingest.py` | CLI: gather → chunk → embed → save |
| `retrieve.py` | query-time `retrieve()` + `format_context()` |

## Config (env)

- `OPENAI_API_KEY` — required for embedding (ingest + query).
- `EMBEDDING_MODEL` — defaults to `text-embedding-3-small`.

## Notes

- Vector store is brute-force numpy cosine (instant at a few hundred chunks/course,
  no FAISS dependency); `pgvector` on the production Postgres is the eventual swap.
- Re-run `rag.ingest` when course materials change (the manifest records source
  hashes so staleness is detectable).
