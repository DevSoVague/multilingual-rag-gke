import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "4"
## Only for mac backend

import re
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
import requests as http_requests

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextBox

from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

# ─────────────────────────────────────────────────────────────────────────────
# Gemini config
# ─────────────────────────────────────────────────────────────────────────────
# Set this in your shell 
# export GEMINI_API_KEY="..." (check the somecommands.txt file for what to input)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 3072

GEN_MODELS = {
    "gemini-2.0-flash": "gemini-2.0-flash",
    "gemini-2.5-pro": "gemini-2.5-pro-preview-05-06",
    "gemini-1.5-flash": "gemini-1.5-flash",
}
DEFAULT_GEN = "gemini-2.0-flash"

INDEX_TYPES = ["HNSW", "IVF_PQ", "DiskANN"] 

PAPER_TYPES = [
    "AI / ML",
    "Security",
    "Other",
]

# ─────────────────────────────────────────────────────────────────────────────
# Milvus config (set it for GKE deployment)
# ─────────────────────────────────────────────────────────────────────────────
MILVUS_URI = os.environ.get("MILVUS_URI", "http://localhost:19530")
MILVUS_TOKEN = os.environ.get("MILVUS_TOKEN", "")
MILVUS_ALIAS = "rag_conn"

# Default collection
DEFAULT_COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION", "papers_rag")


# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded output format — every answer must follow this structure exactly
# ─────────────────────────────────────────────────────────────────────────────
OUTPUT_FORMAT_INSTRUCTIONS = """
Your response MUST follow this exact structure — no deviations:

<Your answer here, 4-6 sentences, grounded only in the provided context.>

Recommended Research Papers:
• <Exact paper title 1>. URL: <url1>
• <Exact paper title 2>. URL: <url2>

Rules:
- Use bullet points (•) for the paper list, not dashes or numbers.
- The section header must be exactly: Recommended Research Papers:
- Only list papers from the provided allowed list. Do not invent papers.
- If a real URL is available from context, use it. Otherwise write: URL: Not available
- Do NOT include any text after the second paper bullet.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Translator config
# ─────────────────────────────────────────────────────────────────────────────
TRANSLATOR_URL = os.environ.get("TRANSLATOR_URL", "http://127.0.0.1:8080") #set this 


def _llm_translate(text: str, source_language: str, target_language: str) -> str:
    """Fallback: use Gemini to translate when the translator service is unavailable."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    prompt = (
        f"Translate the following text from {source_language} to {target_language}. "
        f"Return ONLY the translated text, no explanations or extra commentary.\n\n"
        f"{text}"
    )
    resp = llm.invoke(prompt)
    content = getattr(resp, "content", "")
    if isinstance(content, list):
        content = " ".join(str(x) for x in content)
    return str(content).strip()


def call_translator(text: str, source_language: str, target_language: str) -> str:
    """Call the external translator service. Falls back to LLM if service is unavailable."""
    if source_language == target_language:
        return text
    try:
        resp = http_requests.post(
            f"{TRANSLATOR_URL}/translate",
            json={
                "text": text,
                "source_language": source_language,
                "target_language": target_language,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["translated_text"]
    except Exception:
        # Translator service unavailable — fall back to LLM translation
        return _llm_translate(text, source_language, target_language)


# ─────────────────────────────────────────────────────────────────────────────
# Reflection / revision prompts  (from graph.py)
# ─────────────────────────────────────────────────────────────────────────────
_reflection_prompt = PromptTemplate.from_template(
"""#Role: You are a strict RAG answer reviewer.
#Task: Decide if the answer is grounded in the provided context and follows the required format.
#Format: Return EXACTLY:
#Issues:
- ...
#Fixes:
- ...
#Verdict: PASS or FAIL

#Rules:
- FAIL if the answer includes claims not supported by the provided Context.
- FAIL if the section header is not exactly: Recommended Research Papers:
- FAIL if the papers are not listed with bullet points (•), not dashes or numbers.
- FAIL if 'Recommended Research Papers' section is missing or includes papers not in the provided list.
- FAIL if the answer is unclear, contradictory, or ignores the user's question.
- FAIL if there are more than 2 recommended papers.
- FAIL if any URL is clearly wrong or unrelated to the paper title.
Question:
{question}

Context (snippets):
{context_block}

Allowed recommended papers (exact titles):
{papers_block}

Draft answer:
{answer}
"""
)

_revise_prompt = PromptTemplate.from_template(
"""#Role: You are a careful RAG answer rewriter.
#Task: Rewrite the answer to fix the issues while staying grounded in Context.
#Rules:
- Use ONLY the provided Context for factual claims.
- The section header must be exactly: Recommended Research Papers:
- List papers using bullet points (•), not dashes or numbers. Max 2 papers.
- List ONLY papers from the Allowed recommended papers list. Do NOT invent papers.
- Keep the answer concise (2-4 sentences) and directly responsive.
- If the original URL was not relevant to the paper title, remove it in the revision.
- After removing irrelevant URL, add a URL that is relevant to the paper title.
- If no URL is known, write: URL: Not available

Question:
{question}

Context (snippets):
{context_block}

Allowed recommended papers (exact titles):
{papers_block}

Reflection:
{reflection}

Previous answer:
{answer}
"""
)


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph state
# ─────────────────────────────────────────────────────────────────────────────
class RAGState(TypedDict):
    question: str
    top_k: int
    paper_filter: Optional[str]
    documents: List[Dict]
    answer: str
    # translation
    input_language: str
    translated_query: Optional[str]
    # reflection loop
    recommended_papers: Optional[List[str]]
    reflection: Optional[str]
    status: Optional[str]       # "PASS" or "FAIL"
    iteration: Optional[int]
    max_iterations: Optional[int]


# ─────────────────────────────────────────────────────────────────────────────
# PDFIndexer (Milvus backend)
# ─────────────────────────────────────────────────────────────────────────────
class PDFIndexer:
    """
    RAG indexer using Milvus (pymilvus) as the vector store backend.
    LangGraph is used for retrieve -> generate orchestration.

    Supports Milvus index types:
      - HNSW
      - IVF_PQ
      - DiskANN (if Milvus build/version supports it)
    """

    def __init__(
        self,
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        model: str = DEFAULT_GEN,
        index_type: str = "HNSW",
        collection_name: str = DEFAULT_COLLECTION_NAME,
        drop_old_collection: bool = False,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = model
        self.index_type = index_type
        self.embedding_dim = EMBED_DIM
        self.collection_name = collection_name

        self._collection: Optional[Collection] = None
        self._graph = None
        self._embedder = None
        self.output_language = "English"

        self._ensure_gemini()
        self._connect_milvus()
        self._init_collection(drop_old=drop_old_collection)

    # ═══════════════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════════════
    def _ensure_gemini(self):
        key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY not set.")

    @staticmethod
    def _safe_text(x: Any) -> str:
        if x is None:
            return ""
        return str(x)

    def _get_embedder(self) -> GoogleGenerativeAIEmbeddings:
        if self._embedder is None:
            self._embedder = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)
        return self._embedder

    def set_output_language(self, language: str = "English") -> None:
        self.output_language = language or "English"
        if self._collection is not None:
            self._build_graph()

    # ═══════════════════════════════════════════════════════════════════════════
    # Milvus connection + collection setup
    # ═══════════════════════════════════════════════════════════════════════════
    def _connect_milvus(self):
        # pymilvus can accept URI in newer versions
        conn_kwargs = {"alias": MILVUS_ALIAS, "uri": MILVUS_URI}
        if MILVUS_TOKEN:
            conn_kwargs["token"] = MILVUS_TOKEN
        connections.connect(**conn_kwargs)

    def _make_schema(self) -> CollectionSchema:
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=True,
            ),
            FieldSchema(
                name="chunk_id",
                dtype=DataType.INT64,
            ),
            FieldSchema(
                name="source",
                dtype=DataType.VARCHAR,
                max_length=512,
            ),
            FieldSchema(
                name="page",
                dtype=DataType.INT64,
            ),
            FieldSchema(
                name="paper_type",
                dtype=DataType.VARCHAR,
                max_length=128,
            ),
            FieldSchema(
                name="text",
                dtype=DataType.VARCHAR,
                max_length=65535,  # if your Milvus version complains, reduce to e.g. 16384
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=EMBED_DIM,
            ),
        ]
        return CollectionSchema(fields=fields, description="PDF RAG chunks")

    def _milvus_index_params(self) -> Dict:
        """
        Map UI index types to Milvus index params.
        NOTE:
        - DiskANN availability depends on Milvus version / deployment config.
        - Metric uses COSINE to match rubric.
        """
        itype = self.index_type

        if itype == "HNSW":
            return {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 32, "efConstruction": 200},
            }

        if itype == "IVF_PQ":
            # heuristic nlist (can tune based on corpus size)
            nlist = 128
            # m must divide dim
            m = 8 if EMBED_DIM % 8 == 0 else 16
            if EMBED_DIM % m != 0:
                raise ValueError(f"EMBED_DIM={EMBED_DIM} must be divisible by m={m} for IVF_PQ")
            return {
                "index_type": "IVF_PQ",
                "metric_type": "COSINE",
                "params": {"nlist": nlist, "m": m, "nbits": 8},
            }

        if itype == "DiskANN":
            # Depending on Milvus version, DiskANN may be "DISKANN"
            # If unsupported, create_index() will fail and app can catch/report.
            return {
                "index_type": "DISKANN",
                "metric_type": "COSINE",
                "params": {},  # some versions may support additional params
            }

        raise ValueError(f"Unknown index_type: {itype}")

    def _milvus_search_params(self) -> Dict:
        if self.index_type == "HNSW":
            return {"metric_type": "COSINE", "params": {"ef": 128}}
        if self.index_type == "IVF_PQ":
            return {"metric_type": "COSINE", "params": {"nprobe": 16}}
        if self.index_type == "DiskANN":
            # Param names can vary by version; empty params is safest fallback
            return {"metric_type": "COSINE", "params": {}}
        return {"metric_type": "COSINE", "params": {}}

    def _init_collection(self, drop_old: bool = False):
        if drop_old and utility.has_collection(self.collection_name, using=MILVUS_ALIAS):
            utility.drop_collection(self.collection_name, using=MILVUS_ALIAS)

        if not utility.has_collection(self.collection_name, using=MILVUS_ALIAS):
            schema = self._make_schema()
            self._collection = Collection(
                name=self.collection_name,
                schema=schema,
                using=MILVUS_ALIAS,
                shards_num=1,
            )
        else:
            self._collection = Collection(self.collection_name, using=MILVUS_ALIAS)

        # Build graph (retrieval can work once indexed)
        self._build_graph()

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. EXTRACTION — pdfminer.six
    # ═══════════════════════════════════════════════════════════════════════════
    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict]:
        pages = []
        pdf_name = Path(pdf_path).name

        for page_num, layout in enumerate(extract_pages(pdf_path), start=1):
            parts = []
            for el in layout:
                if isinstance(el, (LTTextContainer, LTTextBox)):
                    t = el.get_text()
                    if t and t.strip():
                        parts.append(t)

            text = self._clean(" ".join(parts))
            if text:
                pages.append({"page": page_num, "text": text, "source": pdf_name})

        return pages

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\x20-\x7E\n]", "", text)
        return text.strip()

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. CHUNKING
    # ═══════════════════════════════════════════════════════════════════════════
    def extract_and_chunk(self, pdf_path: str, paper_type: str = "Other") -> List[Dict]:
        pages = self.extract_text_from_pdf(pdf_path)
        chunks = []
        chunk_id = 0

        for page in pages:
            for text in self._chunk_text(page["text"]):
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "text": text,
                        "source": page["source"],
                        "page": page["page"],
                        "paper_type": paper_type,
                    }
                )
                chunk_id += 1

        return chunks

    def _chunk_text(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks, cur, cur_len = [], [], 0

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue

            wc = len(sent.split())
            if cur and (cur_len + wc > self.chunk_size):
                chunks.append(" ".join(cur))

                # overlap tail
                ov, ov_len = [], 0
                for s in reversed(cur):
                    sw = len(s.split())
                    if ov_len + sw <= self.chunk_overlap:
                        ov.insert(0, s)
                        ov_len += sw
                    else:
                        break
                cur, cur_len = ov, ov_len

            cur.append(sent)
            cur_len += wc

        if cur:
            chunks.append(" ".join(cur))

        return [c for c in chunks if c.strip()]

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. EMBEDDING
    # ═══════════════════════════════════════════════════════════════════════════
    def embed_one(self, text: str, task: str = "retrieval_document") -> List[float]:
        # task kept for compatibility with your app.py
        embedder = self._get_embedder()
        return embedder.embed_query(text)

    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        for chunk in chunks:
            chunk["embedding"] = self.embed_one(chunk["text"], "retrieval_document")
        return chunks

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. INDEX BUILDING + INGESTION (Milvus)
    # ═══════════════════════════════════════════════════════════════════════════
    def _drop_and_recreate_collection_for_index_type(self):
        """
        Recreate collection to ensure a clean index when switching algorithms.
        This avoids overlap/contamination between HNSW / IVF_PQ / DiskANN.
        """
        if utility.has_collection(self.collection_name, using=MILVUS_ALIAS):
            utility.drop_collection(self.collection_name, using=MILVUS_ALIAS)

        schema = self._make_schema()
        self._collection = Collection(
            name=self.collection_name,
            schema=schema,
            using=MILVUS_ALIAS,
            shards_num=1,
        )

    def build_index(self, embedded_chunks: List[Dict]) -> None:
        """
        Milvus version of build_index:
        - recreates collection (clean slate)
        - inserts all embedded chunks
        - creates Milvus ANN index on vector field
        - loads collection for search
        """
        if not embedded_chunks:
            raise ValueError("No embedded chunks provided.")
        if "embedding" not in embedded_chunks[0]:
            raise ValueError("Chunks must contain 'embedding' before build_index().")

        # Clean rebuild for fair comparisons
        self._drop_and_recreate_collection_for_index_type()

        # Insert rows
        chunk_ids = [int(c["chunk_id"]) for c in embedded_chunks]
        sources = [str(c["source"])[:512] for c in embedded_chunks]
        pages = [int(c["page"]) for c in embedded_chunks]
        paper_types = [str(c.get("paper_type", "Other"))[:128] for c in embedded_chunks]
        texts = [str(c["text"])[:65535] for c in embedded_chunks]  # truncate for field limit
        embeddings = [list(map(float, c["embedding"])) for c in embedded_chunks]

        data = [
            chunk_ids,
            sources,
            pages,
            paper_types,
            texts,
            embeddings,
        ]
        # Order matches schema excluding auto_id PK field
        # schema fields: id(auto), chunk_id, source, page, paper_type, text, embedding
        self._collection.insert(data)
        self._collection.flush()

        # Create vector index
        index_params = self._milvus_index_params()
        self._collection.create_index(field_name="embedding", index_params=index_params)

        # Load collection into memory for search
        self._collection.load()

        # Keep lightweight local metadata copy for app compatibility if needed
        self._chunks = [{k: v for k, v in c.items() if k != "embedding"} for c in embedded_chunks]

        self._build_graph()

    def add_to_index(self, embedded_chunks: List[Dict]) -> None:
        """
        Append new vectors to Milvus collection.
        NOTE: Depending on index type and benchmark fairness, you may prefer rebuilds.
        """
        if self._collection is None:
            self._init_collection(drop_old=False)

        if not embedded_chunks:
            return

        chunk_ids = [int(c["chunk_id"]) for c in embedded_chunks]
        sources = [str(c["source"])[:512] for c in embedded_chunks]
        pages = [int(c["page"]) for c in embedded_chunks]
        paper_types = [str(c.get("paper_type", "Other"))[:128] for c in embedded_chunks]
        texts = [str(c["text"])[:65535] for c in embedded_chunks]
        embeddings = [list(map(float, c["embedding"])) for c in embedded_chunks]

        data = [chunk_ids, sources, pages, paper_types, texts, embeddings]
        self._collection.insert(data)
        self._collection.flush()

        # Rebuild index not always required after insert, but load/refresh is good practice
        try:
            self._collection.load()
        except Exception:
            pass

        self._chunks.extend([{k: v for k, v in c.items() if k != "embedding"} for c in embedded_chunks])

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. SEARCH (Milvus)
    # ═══════════════════════════════════════════════════════════════════════════
    def _search(self, q_vec: List[float], top_k: int, paper_filter: Optional[str] = None) -> List[Dict]:
        if self._collection is None:
            return []

        expr = None
        if paper_filter:
            # safe whitelist behavior
            pf = paper_filter.replace('"', '\\"')
            expr = f'paper_type == "{pf}"'

        search_params = self._milvus_search_params()

        results = self._collection.search(
            data=[q_vec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["chunk_id", "source", "page", "paper_type", "text"],
            consistency_level="Strong",  # if your pymilvus version complains, remove this line
        )

        docs = []
        if results and len(results) > 0:
            for hit in results[0]:
                entity = hit.entity
                docs.append({
                    "chunk_id": entity.get("chunk_id"),
                    "source": entity.get("source"),
                    "page": entity.get("page"),
                    "paper_type": entity.get("paper_type"),
                    "text": entity.get("text"),
                    "score": float(hit.score),
                })
        return docs

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. LANGGRAPH PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_graph(self) -> None:
        indexer = self
        parser = StrOutputParser()

        # ── Node 1: translate user query → English ────────────────────────────
        def translate_query_node(state: RAGState) -> RAGState:
            input_language = state.get("input_language", "English")
            q = state["question"]
            translated = call_translator(
                text=q,
                source_language=input_language,
                target_language="English",
            )
            return {**state, "translated_query": translated}

        # ── Node 2: retrieve from Milvus ──────────────────────────────────────
        def retrieve_node(state: RAGState) -> RAGState:
            q = state.get("translated_query") or state["question"]
            top_k = state.get("top_k", 4)
            paper_filter = state.get("paper_filter")

            q_vec = indexer.embed_one(q, "retrieval_query")
            docs = indexer._search(q_vec=q_vec, top_k=top_k, paper_filter=paper_filter)

            # Derive top-2 unique paper titles from retrieved docs
            seen: set = set()
            recommended: List[str] = []
            for d in docs:
                title = d.get("source", "Unknown")
                if title not in seen:
                    seen.add(title)
                    recommended.append(title)

            return {**state, "documents": docs, "recommended_papers": recommended}

        # ── Node 3: generate answer (English, grounded) ───────────────────────
        def generate_node(state: RAGState) -> RAGState:
            docs = state.get("documents", [])
            recommended_papers = state.get("recommended_papers", [])

            if docs:
                context = "\n\n".join(
                    f"[{i}] {d['source']} (p{d['page']}, type={d.get('paper_type','?')}, score={d['score']:.3f})\n{d['text']}"
                    for i, d in enumerate(docs, 1)
                )
            else:
                context = "No relevant context found."

            top_2 = recommended_papers[:2]
            papers_block = "\n".join([f"- {t}" for t in top_2]) if top_2 else "(none)"

            q = state.get("translated_query") or state["question"]

            # Belt-and-suspenders: ask the LLM to reply in the user's language directly.
            # The translate_output_node will also run after the loop, but this ensures
            # the answer is in the right language even if translation fails mid-pipeline.
            input_language = state.get("input_language", "English")
            lang_instruction = (
                "" if input_language == "English"
                else f"Answer in {input_language}. "
            )

            prompt = (
                f"{lang_instruction}"
                f"{OUTPUT_FORMAT_INSTRUCTIONS}\n"
                "Answer using ONLY the provided context. Do NOT invent facts.\n\n"
                f"Context:\n{context}\n\n"
                f"Allowed papers to recommend (use ONLY these, exact titles):\n{papers_block}\n\n"
                f"Question: {q}"
            )

            model_name = GEN_MODELS.get(indexer.model, indexer.model)
            llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
            resp = llm.invoke(prompt)

            content = getattr(resp, "content", "")
            if isinstance(content, list):
                content = "\n".join(indexer._safe_text(x) for x in content)

            return {**state, "answer": indexer._safe_text(content)}

        # ── Node 4: reflect — check grounding & formatting ────────────────────
        def reflect_node(state: RAGState) -> RAGState:
            model_name = GEN_MODELS.get(indexer.model, indexer.model)
            llm_reflect = ChatGoogleGenerativeAI(model=model_name, temperature=0)

            question = state.get("translated_query") or state["question"]
            docs = state.get("documents", [])
            recommended_papers = state.get("recommended_papers", [])
            input_language = state.get("input_language", "English")

            context_block = "\n".join(
                f"- [{i}] {d['source']}: {d['text'][:300]}"
                for i, d in enumerate(docs, 1)
            ) if docs else "(no context retrieved)"
            top_2 = recommended_papers[:2]
            papers_block = "\n".join([f"- {t}" for t in top_2]) if top_2 else "(none)"

            # Append language note so the reflector judges the answer in context
            lang_note = (
                "" if input_language == "English"
                else f"\nNote: The answer should be in {input_language}. FAIL if it is not."
            )

            refl = (_reflection_prompt | llm_reflect | parser).invoke({
                "question": question + lang_note,
                "context_block": context_block,
                "papers_block": papers_block,
                "answer": state.get("answer", ""),
            })

            verdict_match = re.search(r"#Verdict:\s*(PASS|FAIL)", refl, re.IGNORECASE)
            status = verdict_match.group(1).upper() if verdict_match else "FAIL"
            return {**state, "reflection": refl, "status": status}

        # ── Node 5: revise — fix issues found in reflection ───────────────────
        def revise_node(state: RAGState) -> RAGState:
            model_name = GEN_MODELS.get(indexer.model, indexer.model)
            llm_revise = ChatGoogleGenerativeAI(model=model_name, temperature=0)

            question = state.get("translated_query") or state["question"]
            docs = state.get("documents", [])
            recommended_papers = state.get("recommended_papers", [])
            input_language = state.get("input_language", "English")

            context_block = "\n".join(
                f"- [{i}] {d['source']}: {d['text'][:300]}"
                for i, d in enumerate(docs, 1)
            ) if docs else "(no context retrieved)"
            top_2 = recommended_papers[:2]
            papers_block = "\n".join([f"- {t}" for t in top_2]) if top_2 else "(none)"

            # Inject language requirement into the revise prompt
            lang_rule = (
                "" if input_language == "English"
                else f"- Write the revised answer in {input_language}.\n"
            )

            revised = (_revise_prompt | llm_revise | parser).invoke({
                "question": question,
                "context_block": context_block,
                "papers_block": papers_block + (f"\n{lang_rule}" if lang_rule else ""),
                "reflection": state.get("reflection", ""),
                "answer": state.get("answer", ""),
            })

            return {**state, "answer": revised}

        # ── Node 6: bump iteration counter ────────────────────────────────────
        def iterate_node(state: RAGState) -> RAGState:
            return {**state, "iteration": int(state.get("iteration", 0)) + 1}

        # ── Node 7: translate final answer → user's language ─────────────────
        def translate_output_node(state: RAGState) -> RAGState:
            input_language = state.get("input_language", "English")
            english_answer = state.get("answer", "")
            translated_answer = call_translator(
                text=english_answer,
                source_language="English",
                target_language=input_language,
            )
            return {**state, "answer": translated_answer}

        # ── Conditional router ────────────────────────────────────────────────
        def should_continue(state: RAGState) -> str:
            if state.get("status") == "PASS":
                return "stop"
            if int(state.get("iteration", 0)) >= int(state.get("max_iterations", 2)):
                return "stop"
            return "continue"

        # ── Wire graph ────────────────────────────────────────────────────────
        builder = StateGraph(RAGState)
        builder.add_node("translate_query", translate_query_node)
        builder.add_node("retrieve", retrieve_node)
        builder.add_node("generate", generate_node)
        builder.add_node("reflect", reflect_node)
        builder.add_node("revise", revise_node)
        builder.add_node("iterate", iterate_node)
        builder.add_node("translate_output", translate_output_node)

        builder.set_entry_point("translate_query")
        builder.add_edge("translate_query", "retrieve")
        builder.add_edge("retrieve", "generate")
        builder.add_edge("generate", "reflect")
        builder.add_edge("reflect", "revise")
        builder.add_edge("revise", "iterate")
        builder.add_conditional_edges(
            "iterate",
            should_continue,
            {"continue": "reflect", "stop": "translate_output"},
        )
        builder.add_edge("translate_output", END)

        self._graph = builder.compile()

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. PUBLIC QUERY
    # ═══════════════════════════════════════════════════════════════════════════
    def query(
        self,
        question: str,
        top_k: int = 4,
        model: Optional[str] = None,
        paper_filter: Optional[str] = None,
        output_language: Optional[str] = None,
        max_iterations: int = 2,
    ) -> Tuple[str, List[Dict]]:
        if self._graph is None:
            self._build_graph()

        graph_needs_rebuild = False

        if model and model != self.model:
            self.model = model
            graph_needs_rebuild = True

        if output_language and output_language != self.output_language:
            self.output_language = output_language
            graph_needs_rebuild = True

        if graph_needs_rebuild:
            self._build_graph()

        init: RAGState = {
            "question": question,
            "top_k": top_k,
            "paper_filter": paper_filter,
            "documents": [],
            "answer": "",
            "input_language": output_language or "English",
            "translated_query": None,
            "recommended_papers": [],
            "reflection": None,
            "status": None,
            "iteration": 0,
            "max_iterations": max_iterations,
        }

        final = self._graph.invoke(init)
        return final["answer"], final["documents"]

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. PERSISTENCE / MANAGEMENT HELPERS (Milvus-style)
    # ═══════════════════════════════════════════════════════════════════════════
    def save_index(self, directory: str = "./rag_index") -> None:
        """
        Keeps compatibility with app benchmark helpers by writing lightweight metadata.
        """
        Path(directory).mkdir(parents=True, exist_ok=True)
        meta_path = Path(directory) / "milvus_index_meta.txt"
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(f"collection_name={self.collection_name}\n")
            f.write(f"index_type={self.index_type}\n")
            f.write(f"milvus_uri={MILVUS_URI}\n")

    def load_index(self, directory: str = "./rag_index") -> None:
        """
        For Milvus, load means reconnect + attach existing collection + load into memory.
        """
        self._connect_milvus()
        if not utility.has_collection(self.collection_name, using=MILVUS_ALIAS):
            raise FileNotFoundError(f"Milvus collection '{self.collection_name}' not found.")
        self._collection = Collection(self.collection_name, using=MILVUS_ALIAS)
        self._collection.load()
        self._build_graph()

    def clear_collection(self, drop: bool = False) -> None:
        """
        App helper to clear vector store contents.
        drop=True will drop the collection entirely.
        """
        if not utility.has_collection(self.collection_name, using=MILVUS_ALIAS):
            return

        if drop:
            utility.drop_collection(self.collection_name, using=MILVUS_ALIAS)
            self._collection = None
            return

        # Recreate empty collection with same schema
        self._drop_and_recreate_collection_for_index_type()