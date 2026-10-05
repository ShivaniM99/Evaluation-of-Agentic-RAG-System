# Evaluation of an Agentic RAG System

This repository extends a team hackathon project (an agentic RAG system for technical-support lookup, built with teammates; see the team list in the original project README below). **My contribution is everything that measures, monitors and improves it:**

- **Evaluation layer** (`evals/`): a golden set with a dev/held-out split, retrieval metrics, claim-level groundedness, citation precision/recall/validity, correctness, abstention and agent-trajectory metrics, repeated runs with stability reporting, an independent-model-family judge, a verifier meta-eval and judge calibration.
- **Observability** (`observability/`): per-step tracing with latency, token and cost accounting, a SQLite trace store, structured logs and optional Langfuse export.
- **Online monitoring** (`monitoring/`, `pages/`): dashboard, sampled online evals, user feedback that feeds the golden set, and threshold alerts.
- **Fixes the evals found:** the Verifier was removing every citation; zero-evidence queries still produced invented answers; the analyzer was over-confident on off-subject evidence. See *Evaluation Findings* below.
- **Tests and a static results report** (`tests/`, `docs/`).

The pipeline itself (planner, retriever, analyzer, synthesizer, verifier, ingestion and UI) is the shared team codebase, which I modified where noted above.

---

# 🚀 HackVerse 2026 | ABC Technology ATLAS - Agentic Technical Lookup and Support

**Company Track:** ABC Technology <br>
**Team Name:** Hackify <br>
**Team Members:** Olan Pinto, Shivani Madan, Nikitha Lalam

---

## 1️⃣ Problem Statement

ABC Technology's technical support teams and customers interact daily with hundreds of pages of ABC Platform documentation — covering installation procedures, workflow configuration, step templates, inserter controllers, version-specific feature releases, and more. Finding accurate, specific answers to technical questions in this documentation requires navigating a large, hierarchically organised PDF knowledge base that is not keyword-searchable in a meaningful way.

**The end user** is a ABC Technology technical support engineer or an ABC Platform administrator who needs fast, accurate, source-verified answers to operational questions — without manually searching through hundreds of PDF pages.

**Why this matters:** Slow documentation lookup increases support ticket resolution time, increases the risk of misconfiguration, and creates a poor experience for customers who need help urgently. An intelligent retrieval system that reasons across documents, decomposes complex questions, and always cites its sources directly addresses this operational bottleneck.

---

## 2️⃣ Why We Chose This Problem

We selected the ABC Technology track because the problem is technically rich and practically impactful. The documentation corpus is non-trivial — it spans multiple document types (step-by-step procedures, long usage scenarios, release notes, and index pages), each requiring a different retrieval and chunking strategy. A naive RAG system would fail here because:

- Release-note documents need version-block awareness to answer "when was X introduced?"
- Scenario documents are multi-page walkthroughs that must be split by logical section, not token count
- Procedure documents are already atomic and should never be split
- Index/navigation pages should not be returned as answers at all

This forced us to build a genuinely intelligent ingestion pipeline rather than a generic one — and then pair it with a multi-step reasoning agent that can decompose ambiguous questions, iteratively refine retrieval, and verify every claim before answering. That combination of ingestion intelligence and agentic reasoning is what makes this problem compelling.

---

## 3️⃣ Solution Overview

ABC Technology ATLAS (Agentic Technical Lookup And Support) is a production-grade agentic RAG system built on top of 280MB of ABC Platform PDF documentation. A user submits a natural language question (by text or voice), and the system decomposes it, retrieves relevant documentation chunks using a hybrid FAISS + BM25 + entity-aware index, evaluates whether the evidence is sufficient, iteratively refines the retrieval if not, synthesises a grounded answer, and then verifies every claim against the source chunks before returning the final response — complete with structured citations. The system explicitly flags uncertainty and returns "insufficient evidence found" rather than hallucinating when the answer is not in the documentation.

---

## 4️⃣ Architecture & System Design

```
User Question (text or voice)
         │
         ▼
  ┌─────────────┐
  │   Planner   │  Decomposes question into intent + sub-questions
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │  Retriever  │  FAISS (semantic) + BM25 (keyword) + Entity Lookup
  └──────┬──────┘  → Reciprocal Rank Fusion → LLM Reranker
         │
         ▼
  ┌─────────────┐
  │  Analyzer   │  Scores evidence sufficiency (0–10)
  └──────┬──────┘
         │
    sufficient?──── No ──► Query Refiner ──► back to Retriever
         │                 (max 3 iterations)
        Yes
         │
         ▼
  ┌──────────────┐
  │  Synthesizer │  Drafts a grounded answer from retrieved chunks
  └──────┬───────┘
         │
         ▼
  ┌──────────────┐
  │   Verifier   │  Cross-checks every claim against source chunks
  └──────┬───────┘  Flags or removes unsupported claims
         │
         ▼
  Final Answer + Structured Citations + Uncertainty Flag
```


### Why this architecture?

The retriever → analyzer → refiner loop is the key design decision. A single retrieval pass is insufficient for complex questions that require evidence from multiple documents. The loop allows the system to identify what is missing and reformulate queries accordingly — up to 3 iterations before forcing a synthesis on whatever evidence exists.

**Trade-offs considered:**
- **Full knowledge graph vs. hierarchical indexing:** We chose hierarchical indexing (FAISS + BM25 + entity index) over a full knowledge graph. A knowledge graph would provide richer cross-document traversal but would require 3–4× the implementation time with marginal retrieval improvement for this corpus. The entity index captures ~80% of the cross-document linking benefit.
- **Single LLM call vs. multi-node pipeline:** A single prompt cannot simultaneously plan, retrieve, evaluate sufficiency, and verify. Separating these into distinct nodes with structured outputs at each stage makes the system auditable, debuggable, and more accurate.
- **LLM reranker vs. threshold-only filtering:** RRF scores can appear high even for irrelevant results due to surface-level keyword matching. The LLM reranker adds a second relevance gate that catches false positives the threshold alone misses.

---

## 5️⃣ Data Handling & Preprocessing

### Dataset
280MB of ABC Platform documentation exported as PDFs from the ABC Technology documentation portal. 280+ PDF files covering configuration, administration, troubleshooting, feature-specific procedures, usage scenarios, and release notes.

### Document Classification
Each PDF is automatically classified into one of four types using a rule-based fast path (covers ~80% of documents without an API call) and an OpenAI-backed LLM classifier with structured Pydantic output for ambiguous cases:

| Type | Description | Chunking Strategy |
|---|---|---|
| `procedure` | Single-task step-by-step instructions | 1 document = 1 chunk (never split) |
| `index` | Navigation/overview pages listing child topics | 1 chunk, flagged `is_navigational=True`, excluded from retrieval |
| `scenario` | Multi-page end-to-end usage walkthroughs | Split by section header patterns specific to ABC Technology's documentation style |
| `release-notes` | Changelog organised by version | Split by version block (`New functions and updates in Version X.Y.Z`) |

### Chunking
Type-aware chunking is the most critical preprocessing decision. Generic token-count chunking would destroy the semantic integrity of procedure documents (which are already atomic), waste context on navigation pages (which should never be retrieved as answers), and completely fail on release notes (where the version label is the most important retrieval signal).

The scenario chunker uses an allowlist of known ABC Technology section header patterns (`Setting up...`, `Preparing to...`, `Processing...`, etc.) rather than heuristic line detection — preventing overfitting to specific documents while generalising across the full corpus.

### Noise Removal
Each PDF page contains three lines of noise injected by the documentation export system: a timestamp, a page count, and a redundant section label. These are stripped before extraction using regex patterns. Breadcrumbs (e.g., `Configuring > Preparing to use workflows > Adding conditional processing`) are extracted and stored as metadata rather than included in chunk text.

### Output
- **`chunks/chunks.json`** — 766 total chunks (567 retrievable, 199 navigational)
- **`chunks/entity_index.json`** — 462 unique named entities mapped to chunk IDs

### Entity Index
A lightweight lookup table mapping named entities (step template names, job properties, software names, OS names, version numbers, file paths) to the chunk IDs that mention them. This enables entity-aware retrieval: if a query mentions `FusionPro` or `AssignJobValues`, the system immediately fetches all chunks that reference those entities before running semantic search.

### Limitations
- System requirements documents (RAM, hardware specs) were not present in the downloaded dataset — the system correctly returns "insufficient evidence" for those queries rather than hallucinating
- PDF extraction quality depends on pdfplumber; tables embedded in PDFs are extracted as plain text which may lose column alignment

---

## 6️⃣ Modeling & AI Strategy

### Models Used
| Component | Model | Reason |
|---|---|---|
| Document classification | `gpt-4o-mini` | Fast, cheap, structured output via Pydantic |
| Query embedding | `text-embedding-3-small` | Good semantic quality at low cost; 1536-dim vectors |
| Planner | `gpt-4o`  | Question decomposition requires strong reasoning |
| Analyzer | `gpt-4o`  | Evidence sufficiency scoring requires nuanced judgment |
| Query Refiner | `gpt-4o`  | Subquery reformulation from missing info description |
| Synthesizer | `gpt-4o`  | Grounded answer generation from multiple chunks |
| Reranker | `gpt-4o-mini` | Per-chunk relevance scoring (0.0–1.0); cheap at top-k=5 |
| Verifier | `gpt-4o`  | Claim-level fact checking against source chunks |
| Voice transcription | `whisper-1` | Speech-to-text for voice query input |

### Retrieval Strategy

**Stage 1 — Hybrid retrieval:**
- FAISS `IndexFlatIP` for cosine similarity semantic search (vectors L2-normalised)
- BM25Okapi for keyword/exact-match search
- Reciprocal Rank Fusion (RRF) combines both ranked lists: score = Σ 1/(rank + 1)
- Entity lookup: exact string match of known entities against query, boosted into results

**Stage 2 — LLM reranking:**
After RRF, a `gpt-4o-mini` call scores each candidate chunk 0.0–1.0 for true relevance to the query. Chunks below 0.3 are dropped. This catches false positives that RRF scores highly due to surface-level keyword overlap rather than semantic relevance.

**Relevance threshold:** A minimum RRF score of 0.75 is applied before reranking. If no chunks pass this threshold, the system returns an empty list and the agent outputs "insufficient evidence found."

### Prompt Structure

Each node uses structured output (Pydantic models parsed via `client.beta.chat.completions.parse`) to guarantee well-formed outputs with no string parsing fragility:

- **Planner** → `PlannerOutput(intent: str, subquestions: list[str])`
- **Analyzer** → `AnalyzerOutput(evidence_sufficient: bool, confidence_score: int, missing_info: str)`
- **Synthesizer** → `SynthesizerOutput(draft_answer: str)`
- **Verifier** → `VerifierOutput(verified_answer: str, uncertainty_flag: bool, flagged_claims: list[str])`
- **Classifier** → `DocumentClassification(doc_type: Literal[...], confidence: Literal[...], reasoning: str)`

The `reasoning` field in each structured output forces chain-of-thought before committing to a label, improving accuracy without a separate reasoning step.

### Alternatives Considered
- **Single-prompt RAG:** Rejected — cannot handle multi-document synthesis or iterative retrieval
- **Full knowledge graph:** Rejected — high implementation cost, marginal retrieval improvement for this corpus within a 12-hour constraint
- **Pinecone / Weaviate:** Rejected — FAISS is sufficient for 567 chunks and avoids external service dependencies during demo

---

## 7️⃣ Evaluation & Metrics

### Test Cases

| # | Question | Expected Source | Result |
|---|---|---|---|
| 1 | What property do I set if I want the printers to enable after a restart? | `aiw00p18.pdf` — Managing objects | ✅ `Remember enabled status of printers` property returned |
| 2 | What inserters does ABC Platform support? | `DefiningInserterControllers.pdf`, `UsingSuppliedInserterControllers.pdf` | ✅ Relevant inserter controller docs returned |
| 3 | Does ABC Platform work with FusionPro? | `aiwi_whatsnew.pdf` — Version 3.12.2 chunk | ✅ FusionPro Connect feature introduction returned |
| 4 | How do I create a workflow? | Procedure docs under Configuring > Workflows | ✅ Relevant procedure chunks returned |
| 5 | How much RAM does the primary server need for document-level processing? | System requirements doc (not in dataset) | ✅ Correctly returns "insufficient evidence" — no hallucination |

### Evaluation Metric: Retrieval Relevance + Grounding Rate

**Retrieval relevance** is measured by whether the correct source document appears in the top-5 results for each test question. Across our 5 validated test questions, 4/5 (80%) return the correct source document in top-5.

The 5th question (RAM requirements) correctly returns empty — which is the right behaviour, not a failure. The system does not hallucinate an answer.

**Grounding rate** is the percentage of claims in the final answer that are directly traceable to a cited source chunk. The Verifier node enforces this by removing any claim not supported by the retrieved chunks and setting `uncertainty_flag=True` if any claims were removed.

### Limitations of this metric
Retrieval relevance at top-5 does not measure answer quality — a chunk can be retrieved correctly but the synthesiser could still misinterpret it. Full end-to-end answer quality evaluation would require a labelled ground truth answer set, which was not available within the hackathon timeframe.

---

## 8️⃣ Business Impact & Actionability

**For ABC Technology technical support teams:**
- Reduces average documentation lookup time from minutes (manual PDF search) to seconds
- Every answer includes structured citations with document name, section, breadcrumb, and page range — engineers can verify and audit any claim instantly
- The uncertainty flag prevents engineers from acting on hallucinated information — a critical safety property in a technical support context

**For ABC Platform administrators:**
- Natural language access to 280MB of documentation without needing to know file names or documentation hierarchy
- Voice input support means hands-free lookup during active system administration

**Real-world usability:**
The system is deployable as a Streamlit web application accessible from any browser. The ingestion pipeline is reusable — new documentation can be added by dropping PDFs into the `data/pdfs/` folder and rerunning `main_ingest.py`. The FAISS and BM25 indexes are rebuilt automatically.

**Limitations:**
- Answers are bounded by what is in the documentation — the system cannot answer questions about undocumented behaviour or edge cases
- The LLM reranker adds ~1–2 seconds of latency per query (one API call per retrieved chunk)
- Voice transcription requires a microphone and adds ~2 seconds of Whisper processing time

---

## 9️⃣ Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **Agent Framework** | LangGraph (StateGraph with conditional edges) |
| **LLM** | OpenAI GPT-4o / GPT-4o-mini, Whisper-1 |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Vector Store** | FAISS (IndexFlatIP, cosine similarity) |
| **Keyword Search** | BM25Okapi (rank-bm25) |
| **PDF Extraction** | pdfplumber |
| **Structured Outputs** | Pydantic v2 + OpenAI `.parse()` |
| **UI** | Streamlit |
| **Other Libraries** | numpy, tiktoken, tqdm, python-dotenv |

---

## 🔟 How to Run the Project

### Prerequisites
- Python 3.10+
- OpenAI API key
- PDFs downloaded from the ABC Technology documentation Drive folder into `data/`

### 1. Clone the repository
```bash
git clone https://github.com/ShivaniM99/Evaluation-of-Agentic-RAG-System.git
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your-key-here
```

### 4. Run ingestion pipeline (your part)
```bash
python main_ingest.py
```
This produces `chunks/chunks.json` and `chunks/entity_index.json`.

### 5. Build the search indexes (teammate's part)
```bash
python index.py
```
This produces `indexes/faiss_index/index.bin`, `indexes/bm25/bm25_model.pkl`, and `indexes/faiss_index/chunks_metadata.json`.

> **Note:** Steps 4 and 5 only need to be run once. The indexes are saved to disk and loaded at app startup.

### 6. Launch the app
```bash
streamlit run app.py
```

---

## 1️⃣1️⃣ Repository Structure

```
AgentSupport-ABC Technology/
│
├── data/
│   └── pdfs/                        # Raw PDF documentation files
│
├── chunks/
│   ├── chunks.json                  # 766 processed chunks with metadata
│   └── entity_index.json            # 462 entity → chunk_id mappings
│
├── indexes/
│   ├── faiss_index/
│   │   ├── index.bin                # FAISS vector index
│   │   └── chunks_metadata.json     # Chunk metadata aligned to FAISS positions
│   └── bm25/
│       └── bm25_model.pkl           # Serialised BM25 model
│
├── ingestion/
│   ├── extractor.py                 # PDF text extraction + noise removal
│   ├── classifier.py                # LLM-based document type classifier
│   ├── chunker.py                   # Type-aware chunking (4 strategies)
│   └── metadata.py                  # Entity extraction + entity index builder
│
├── nodes/
│   ├── planner.py                   # LangGraph node: query decomposition
│   ├── retriever.py                 # LangGraph node: hybrid search
│   ├── analyzer.py                  # LangGraph node: evidence sufficiency scoring
│   ├── query_refiner.py             # LangGraph node: subquery reformulation
│   └── synthesizer.py              # LangGraph node: answer generation
│
├── agent_graph.py                   # LangGraph StateGraph definition
├── pipeline.py                      # Streaming pipeline runner for UI
├── verifier.py                      # Claim verification against source chunks
├── index.py                         # HybridSearchModel + index builder
├── index_loader.py                  # Loads pre-built indexes from disk
├── main_ingest.py                   # Ingestion pipeline entry point
├── app.py                           # Streamlit UI
├── styles.py                        # Modular CSS for Streamlit app
├── config.py                        # API keys, model names, constants
├── requirements.txt
└── README.md
```

---

## 1️⃣2️⃣ Alignment with HackVerse Rubric

| Criterion | How We Address It |
|---|---|
| **Problem Understanding** | Deep analysis of ABC Technology's documentation corpus structure led to 4 distinct document types and type-specific processing strategies — not a generic RAG approach |
| **Data & System Design** | Type-aware ingestion pipeline with noise removal, breadcrumb extraction, entity indexing, and navigational page filtering — all grounded in actual document analysis |
| **Technical Depth** | Multi-stage agentic loop (Planner → Retriever → Analyzer → Refiner → Synthesizer → Verifier), hybrid FAISS+BM25+entity retrieval, LLM reranker, structured Pydantic outputs at every node |
| **Modeling Strategy** | Retrieval strategy documented and justified (why RRF, why cosine similarity, why reranker, why relevance threshold, why iterative loop up to 3 iterations) |
| **Evaluation** | 5 documented test cases with expected sources, actual results, and explicit handling of the "answer not in dataset" case without hallucination |
| **Business Actionability** | Structured citations on every answer make outputs auditable; uncertainty flag prevents engineers from acting on unsupported claims; voice input for hands-free use |
| **Visualization** | Streamlit UI with live agent reasoning trace showing each node's decision, confidence score, retrieved chunk count, and iteration number in real time |
| **Innovation** | Four-way document type classification driving type-specific chunking strategies; entity-aware retrieval index built during ingestion; two-stage retrieval (RRF + LLM reranker) with honest "no evidence" output |

---

## 📜 Compliance Statement

We confirm that this project was developed during HackVerse 2026. We used only permitted datasets and tools. No private code sharing occurred between teams. All work is original.

---

## 📊 Future Improvements

- **Missing documents:** A system requirements document covering hardware/RAM specifications was not present in the downloaded dataset. Downloading and ingesting it would enable the system to answer hardware planning questions.
- **Streaming answer generation:** Currently the synthesizer produces a complete answer before it is displayed. Token-level streaming would improve perceived responsiveness.
- **Feedback loop:** A thumbs up/down mechanism on answers could log low-confidence responses for human review and future fine-tuning.
- **Re-ingestion on document update:** The pipeline currently requires a full re-run to incorporate new documents. An incremental ingestion mode that detects and processes only new/changed PDFs would reduce maintenance overhead.
- **Cross-document citation linking:** When a scenario document references a step template by name, the entity index identifies the relevant procedure chunk — but the synthesiser does not currently auto-fetch and include it. A graph traversal step after retrieval would enable richer cross-document synthesis.

---

## 🔬 Evaluation, Observability & Monitoring

### Setup
```bash
# put OPENAI_API_KEY (and optionally ANTHROPIC_API_KEY) in a local .env file; config.py reads it
export EVAL_JUDGE_MODEL=gpt-4o      # judge model (keep it different from OPENAI_CHAT_MODEL)
```

### 1. Offline evals (`evals/`)
| Command | What it does |
|---|---|
| `python -m evals.run --suite smoke` | 8 stratified questions, end-to-end, all metrics → `evals/results/<run>.{json,md}` |
| `python -m evals.run --suite full --run-id v2` | whole golden set (`--with-draft` adds the pre-verifier groundedness for verifier lift) |
| `python -m evals.run --retrieval-only` | retriever ablation: semantic vs BM25 vs hybrid(RRF) vs hybrid+LLM-rerank |
| `python -m evals.dataset.build_golden --n 80` then `python -m evals.dataset.review` | generate + human-review golden items |
| `python -m evals.verifier_eval --n 20` | injects unsupported claims, reports the Verifier's catch rate and false-removal rate |
| `python -m evals.calibrate export --run evals/results/<run>.json` / `score` | judge-vs-human agreement (Cohen's κ) |

**Metrics:** Recall@k, Precision@k, MRR, nDCG, context precision · claim-level **groundedness** · **citation precision / recall / validity** (does the cited chunk support the claim; does the citation point at a really-retrieved chunk) · **correctness** + key-fact coverage vs reference · relevance · **abstention correctness** (unanswerable → must abstain) · agent trajectory (refiner iterations, refiner recall gain, analyzer decision accuracy, loop exhaustion) · latency/tokens/cost per node.

The golden set lives in `evals/dataset/golden.jsonl` (5 seed items from the original test cases; grow it with the builder/review tools).

### 2. Observability (`observability/`)
Every query is traced: one span per agent node with latency, LLM calls, tokens and cost (`usage.py` wraps the OpenAI SDK, so rerank and embedding calls are attributed to the node that made them). Traces, spans, feedback and online scores live in SQLite (`observability/atlas.db`, override with `ATLAS_DB_PATH`). Structured JSON logs carry a `request_id`. Set `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` (and `LANGFUSE_HOST`) to also export traces to Langfuse.

### 3. Online monitoring (`monitoring/`)
- Dashboard: `streamlit run app.py` → **Monitoring** page (or `streamlit run monitoring/dashboard.py`).
- `python -m monitoring.online_eval --rate 0.25` scores a deterministic sample of live traces with the same judges (reference-free).
- 👍 / 👎 / "Wrong citation" buttons under every answer; `python -m monitoring.feedback` turns flagged answers into golden-set candidates.
- Threshold alerts (override via `ATLAS_ALERT_<METRIC>`) are shown on the dashboard.

### Tests
`python -m pytest tests` (no API key needed; OpenAI calls are mocked at the HTTP layer).

### Comparing models
Generator models are set per node (default `OPENAI_CHAT_MODEL`); override with `ATLAS_MODEL_<NODE>` (planner, analyzer, refiner, synthesizer, verifier). The judge is separate: `EVAL_JUDGE_MODEL=gpt-4o`, or `anthropic:<model>` to use a different provider family (needs `pip install anthropic` and `ANTHROPIC_API_KEY`).
```bash
python -m evals.run --suite full --run-id baseline-mini
ATLAS_MODEL_SYNTHESIZER=gpt-4o ATLAS_MODEL_VERIFIER=gpt-4o python -m evals.run --suite full --run-id strong-synth
```
Compare the two `evals/results/*.md` tables (groundedness, citation precision, correctness, cost).

---

## 📈 Evaluation Findings

All numbers come from `python -m evals.run` on the **dev split** of the golden set (30 questions × 2 repeats, Claude Sonnet 5.5 as an independent judge; generator is `gpt-4o-mini`). Ranges are 95% bootstrap intervals; with 30 questions they are wide, so only large differences are meaningful. The held-out split (20 questions) has **not** been scored yet.

**About the golden set:** 82 questions generated from the corpus by GPT-4o, then validated by a second model family (Claude) against the source chunk; 7 of 84 candidates were rejected. It is synthetic and auto-validated, with a small spot-check by the author, not fully human-labelled. Most questions are "How do I…" style, and each has a single gold chunk, so retrieval recall is likely understated.

| Metric | Baseline | + abstain-on-no-evidence & stricter analyzer (`gpt-4o`) |
|---|---|---|
| Groundedness (claims supported by retrieved text) | 93.6% | 94.6% |
| Citation precision / recall | 79% / 71% | 76% / 66% |
| Fabricated citations | none (validity 99%) | none |
| Hallucinated answers on unanswerable questions | 6.7% | 0% (2 distinct questions fixed; n is small) |
| False abstains on answerable questions | 6.7% | 5% |
| Pipeline cost per query | $0.001 | $0.010 |

### What the evals found (and what was done)
1. **The Verifier was stripping every citation** from final answers, so the "auditable citations" promise did not hold. Fixed in the verifier prompt; citation validity went from no citations to 99% valid.
2. **A zero-evidence query still produced an invented answer** (a made-up licensing model). The UI hid it, but the pipeline did not. It now abstains without calling the LLM.
3. **The analyzer was over-confident on topically related but off-subject evidence** (e.g. the product's own tuning settings for a "third-party OS tuning" question). A stronger analyzer model plus a rule to abstain when refinement ends off-subject removed these hallucinations in the dev set, at roughly 10× pipeline cost per query.
4. **Run-to-run variance matters.** The retrieved chunk set differed between repeats for 30–43% of questions, which is why comparisons use repeats and intervals.
5. **The refiner rarely helped** (on 4 questions it was exercised, it improved recall once).

### Known limitations / future work
- Score the held-out split once (not yet done) and grow the golden set with more varied phrasings (keyword queries, error codes, yes/no).
- Cut the cost of fix 3: keep the cheap analyzer in the loop and add one strong scope check before answering.
- Investigate retrieval misses: e.g. `gen-073` (a release-notes question about license key installation) retrieves zero chunks and fails identically in every run, so it is a retrieval gap, not an effect of the analyzer change.
- Make retrieval more stable (the LLM reranker and the planner are non-deterministic) and review the refiner's value.
- Calibrate the judge against human labels (`python -m evals.calibrate`); not done yet.
- Safety/guardrails, CI quality gate, and containerization (Layers 4–7).

Reports for each run are in `evals/results/*.md`.

### Reproducing the findings table
```bash
# baseline settings (all nodes gpt-4o-mini), judge = Claude Sonnet 5.5
EVAL_JUDGE_MODEL=anthropic:claude-sonnet-5-5 python -m evals.run --suite smoke --split dev --limit 30 --repeats 2 --workers 4
# "stricter analyzer" column additionally sets:
ATLAS_MODEL_ANALYZER=gpt-4o
```
A 30 × 2 run costs roughly $1 with the Sonnet judge (the report prints the pipeline and judge cost separately).

## 🚀 Deployment notes
- Set `OPENAI_API_KEY` as a secret / environment variable on the host (Streamlit Community Cloud: *App settings → Secrets*). Never commit `.env`.
- The monitoring database (`observability/atlas.db`) is a local SQLite file; on hosts with ephemeral disks it resets on restart. Point `ATLAS_DB_PATH` at persistent storage if you want history to survive.
- The default pipeline uses `gpt-4o-mini` for every node. Set `ATLAS_MODEL_ANALYZER=gpt-4o` to enable the stricter (and ~10× costlier per query) analyzer measured above.

## 🌐 Static evaluation report
`docs/index.html` is a self-contained page (results chart, confidence intervals, replayable case studies) built from the saved runs by `python docs/build_report.py`. It makes no API calls, so it can be hosted anywhere (for example GitHub Pages: Settings → Pages → deploy from `/docs`) without exposing a key.
