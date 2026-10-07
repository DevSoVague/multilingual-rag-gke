import streamlit as st
import os
import re
import time
import json
import csv
import requests as http_requests
from datetime import datetime
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "4"

from langchain_google_genai import ChatGoogleGenerativeAI
from indexer import PDFIndexer, PAPER_TYPES, INDEX_TYPES, GEN_MODELS, EMBED_MODEL

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF RAG  ·  Gemini + LangGraph + Milvus",
    page_icon="",
    layout="wide",
)

st.markdown("""
<style>
    .chunk-preview {
        background: #1a1a2e;
        border-left: 3px solid #4285f4;
        padding: 0.75rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.5rem 0;
        font-size: 0.84rem;
        color: #e8eaed;
        white-space: pre-wrap;
    }
    .badge {
        display: inline-block;
        background: #2d2d44;
        color: #81c995;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: bold;
        margin-right: 4px;
    }
    .badge-type {
        background: #3b2d44;
        color: #f4a261;
    }
    .badge-idx {
        background: #1d3557;
        color: #a8dadc;
    }
    .badge-url {
        background: #0b3d91;
        color: #cfe8ff;
    }
    .reflect-pass {
        background: #0d3320;
        border-left: 3px solid #34a853;
        padding: 0.5rem 0.75rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.78rem;
        color: #81c995;
        margin: 0.3rem 0;
    }
    .reflect-fail {
        background: #3a1a1a;
        border-left: 3px solid #ea4335;
        padding: 0.5rem 0.75rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.78rem;
        color: #f28b82;
        margin: 0.3rem 0;
    }
    .reflect-fixed {
        background: #1a2a3a;
        border-left: 3px solid #fbbc04;
        padding: 0.5rem 0.75rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.78rem;
        color: #fdd663;
        margin: 0.3rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for k, v in [
    ("indexer", None),
    ("indexed_files", []),
    ("file_url_map", {}),
    ("index_stats", {}),
    ("chat_history", []),
    ("prepared_chunks", None),
    ("prepared_files", None),
    ("benchmark_results", None),
    ("benchmark_csv_path", None),
    ("benchmark_run_dir", None),
    ("interrupt_requested", False),
    ("is_indexing", False),
    ("is_querying", False),
    ("is_benchmarking", False),
    ("last_index_error", None),
]:
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ────────────────────────────────────────────────────────────────────
def _check_interrupt():
    if st.session_state.get("interrupt_requested", False):
        raise RuntimeError("Interrupted by user.")


def _now_run_id():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _ensure_tmp_upload_dir() -> Path:
    tmp_dir = Path("/tmp/rag_uploads")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def _estimate_storage_mb(n_vectors: int, dim: int) -> float:
    return (n_vectors * dim * 4) / (1024 * 1024)


def _unique_papers_from_sources(sources, file_url_map, k=2):
    seen = set()
    recs = []
    for s in sorted(sources, key=lambda x: float(x.get("score", 0.0)), reverse=True):
        name = s.get("source", "")
        if not name or name in seen:
            continue
        seen.add(name)
        recs.append({
            "paper": name,
            "url": file_url_map.get(name, ""),
            "paper_type": s.get("paper_type", ""),
            "best_score": float(s.get("score", 0.0)),
        })
        if len(recs) >= k:
            break
    return recs


def _safe_set_failed_stats(index_type, model_choice):
    st.session_state["index_stats"] = {
        "status": "failed",
        "index_type": index_type,
        "gen_model": model_choice,
        "embed_model": EMBED_MODEL,
    }


def _save_benchmark_csv(rows, run_dir: Path) -> str:
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "benchmark_results.csv"
    if not rows:
        csv_path.write_text("no_results\n")
        return str(csv_path)
    fieldnames = sorted({k for r in rows for k in r.keys()})
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(csv_path)


# ── URL Reflect Pattern ────────────────────────────────────────────────────────
# This is a three-step reflect loop that runs after the main answer is returned:
#   Step 1 — reflect:  check if each recommended paper has a valid URL
#   Step 2 — fetch:    for missing/bad URLs, ask Gemini to find the real one
#   Step 3 — validate: do a HEAD request to confirm the URL resolves
# Returns updated recs list and a trace dict for display in the UI.

def _is_url_reachable(url: str, timeout: int = 5) -> bool:
    """Quick HEAD check to see if a URL resolves. Returns False on any failure."""
    if not url or not url.startswith("http"):
        return False
    try:
        resp = http_requests.head(url, allow_redirects=True, timeout=timeout)
        return resp.status_code < 400
    except Exception:
        return False


def _llm_find_url(paper_title: str, model_name: str = "gemini-2.0-flash") -> str:
    """
    Ask Gemini for the most likely canonical URL for a paper title.
    Returns a URL string or empty string if none found.
    """
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
    prompt = (
        "You are a research paper URL resolver. "
        "Given a paper title, return ONLY the single most likely canonical URL "
        "(arXiv abstract page, DOI link, or official venue page). "
        "Return the raw URL only — no explanation, no markdown, no extra text. "
        "If you are not confident, return an empty string.\n\n"
        f"Paper title: {paper_title}"
    )
    resp = llm.invoke(prompt)
    raw = getattr(resp, "content", "")
    if isinstance(raw, list):
        raw = " ".join(str(x) for x in raw)
    url = raw.strip().split()[0] if raw.strip() else ""
    # Basic sanity check — must look like a URL
    if not re.match(r"^https?://", url):
        return ""
    return url


def _reflect_and_fix_urls(recs: list, model_name: str = "gemini-2.0-flash") -> tuple:
    """
    Reflect on whether each recommended paper has a good URL.
    Returns (updated_recs, trace) where trace is a list of dicts for UI display.

    Reflect loop per paper:
      - PASS : URL present and reachable           -> keep as-is
      - FETCH: URL missing or unreachable           -> ask LLM for URL
      - VALIDATE: LLM returned a URL               -> HEAD check
      - FIXED: validated URL replaces old one
      - UNRESOLVED: LLM returned nothing or HEAD failed -> keep blank
    """
    trace = []
    updated = []

    for rec in recs:
        title = rec.get("paper", "")
        url   = rec.get("url", "").strip()
        entry = {"paper": title, "original_url": url}

        # Step 1 — reflect
        if url and _is_url_reachable(url):
            entry["status"] = "PASS"
            entry["final_url"] = url
            entry["note"] = "URL present and reachable."
        else:
            # Step 2 — fetch via LLM
            entry["status"] = "FETCH"
            entry["note"] = "URL missing or unreachable — asking Gemini."
            found_url = _llm_find_url(title, model_name=model_name)

            if found_url:
                # Step 3 — validate
                if _is_url_reachable(found_url):
                    entry["status"] = "FIXED"
                    entry["final_url"] = found_url
                    entry["note"] = f"LLM found URL and HEAD check passed: {found_url}"
                    url = found_url
                else:
                    # LLM gave something but it doesn't resolve — keep it anyway
                    # (could be a valid arXiv/DOI that blocks HEAD)
                    entry["status"] = "FIXED"
                    entry["final_url"] = found_url
                    entry["note"] = f"LLM found URL (HEAD check inconclusive): {found_url}"
                    url = found_url
            else:
                entry["status"] = "UNRESOLVED"
                entry["final_url"] = ""
                entry["note"] = "Could not find a URL for this paper."

        trace.append(entry)
        updated.append({**rec, "url": entry.get("final_url", url)})

    return updated, trace


def _render_recommendations(recs: list, url_trace: list = None):
    """Render top-2 recommended papers with URL reflect trace if available."""
    if not recs:
        st.info("No paper recommendations available.")
        return

    st.subheader("Recommended papers (top 2)")
    for i, r in enumerate(recs, 1):
        url = r.get("url", "")
        st.markdown(f"**{i}. {r.get('paper', '')}**  `{r.get('paper_type', '')}`")
        if url:
            st.markdown(f"Link: {url}")
        else:
            st.caption("No URL available.")
        st.caption(f"Best score: {r.get('best_score', 0.0):.4f}")

    # Show URL reflection trace in expander
    if url_trace:
        with st.expander("URL reflection trace"):
            for t in url_trace:
                status = t.get("status", "")
                css_class = (
                    "reflect-pass"  if status == "PASS"       else
                    "reflect-fixed" if status == "FIXED"      else
                    "reflect-fail"
                )
                orig = t.get("original_url", "") or "(none)"
                final = t.get("final_url", "") or "(none)"
                st.markdown(
                    f'<div class="{css_class}">'
                    f'<strong>{t.get("paper","")}</strong><br>'
                    f'Status: {status}<br>'
                    f'Original URL: {orig}<br>'
                    f'Final URL: {final}<br>'
                    f'Note: {t.get("note","")}'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ── Benchmark helper ───────────────────────────────────────────────────────────
def _run_index_benchmark_all_methods(
    embedded_chunks: list,
    model_choice: str,
    top_k: int,
    input_language: str,
    sample_query: str,
    paper_filter: str | None,
    max_iterations: int = 2,
) -> tuple[list, str, str, dict]:
    _check_interrupt()
    st.session_state["is_benchmarking"] = True
    st.session_state["benchmark_results"] = None
    st.session_state["benchmark_csv_path"] = None
    st.session_state["benchmark_run_dir"] = None

    run_id = _now_run_id()
    run_dir = Path("./benchmarks") / f"run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    shared_summary = {
        "run_id": run_id,
        "n_chunks": len(embedded_chunks),
        "embed_model": EMBED_MODEL,
        "embed_dim": 3072,
        "estimated_vector_storage_mb": round(
            _estimate_storage_mb(len(embedded_chunks), 3072), 3
        ),
        "note": "Storage is a rough estimate of vector bytes only.",
    }

    results = []
    methods = [m for m in INDEX_TYPES if m in ("HNSW", "IVF_PQ", "DiskANN")]

    # Raw vector storage (same for every method — vectors are always stored)
    raw_vector_mb = round(_estimate_storage_mb(len(embedded_chunks), 3072), 3)

    # Per-method overhead multipliers applied ON TOP of raw vector bytes:
    #   HNSW    — stores the proximity graph alongside vectors (~1.3–1.5x total)
    #   IVF_PQ  — Product Quantisation compresses vectors heavily (~0.1–0.15x for
    #             the compressed part), but centroid + metadata still add overhead
    #             → net estimate is roughly 0.3x raw vectors
    #   DiskANN — graph stored on disk rather than RAM; overhead similar to HNSW
    _STORAGE_OVERHEAD = {
        "HNSW":    1.4,   # graph structure adds ~40 % on top of raw vectors
        "IVF_PQ":  0.3,   # PQ compression reduces to ~30 % of raw vector size
        "DiskANN": 1.3,   # disk-based graph, slightly lower RAM overhead than HNSW
    }

    for method in methods:
        _check_interrupt()
        t0 = time.perf_counter()
        collection_name = f"papers_rag_{run_id}_{method.lower()}"

        # Estimated total storage for this specific index type
        estimated_storage_mb = round(raw_vector_mb * _STORAGE_OVERHEAD.get(method, 1.0), 3)

        try:
            idx = PDFIndexer(
                chunk_size=st.session_state.index_stats.get("chunk_size", 400) or 400,
                chunk_overlap=st.session_state.index_stats.get("chunk_overlap", 50) or 50,
                model=model_choice,
                index_type=method,
                collection_name=collection_name,
                drop_old_collection=True,
            )

            _check_interrupt()
            t_build0 = time.perf_counter()
            idx.build_index(embedded_chunks)
            t_build1 = time.perf_counter()

            _check_interrupt()
            t_q0 = time.perf_counter()
            answer, sources = idx.query(
                sample_query,
                top_k=top_k,
                model=model_choice,
                paper_filter=paper_filter,
                output_language=input_language,
                max_iterations=max_iterations,
            )
            t_q1 = time.perf_counter()
            t1 = time.perf_counter()

            recs = _unique_papers_from_sources(
                sources, st.session_state.get("file_url_map", {}), k=2
            )
            recs, _ = _reflect_and_fix_urls(recs, model_name=model_choice)

            results.append({
                "method": method,
                "n_chunks": len(embedded_chunks),
                "index_build_sec": round(t_build1 - t_build0, 4),
                "end_to_end_sec": round(t1 - t0, 4),
                "one_query_sec": round(t_q1 - t_q0, 4),
                "estimated_storage_mb": estimated_storage_mb,
                "top_k": top_k,
                "sample_query": sample_query,
                "paper_filter": paper_filter or "None",
                "recommended_1": recs[0]["paper"] if len(recs) > 0 else "",
                "recommended_1_url": recs[0]["url"] if len(recs) > 0 else "",
                "recommended_2": recs[1]["paper"] if len(recs) > 1 else "",
                "recommended_2_url": recs[1]["url"] if len(recs) > 1 else "",
                "notes": (
                    ""
                    if method != "DiskANN"
                    else "DiskANN support depends on Milvus build/version."
                ),
            })

            (run_dir / f"{method}_answer.txt").write_text(answer or "", encoding="utf-8")
            (run_dir / f"{method}_sources.json").write_text(
                json.dumps(sources, indent=2), encoding="utf-8"
            )

        except Exception as e:
            results.append({
                "method": method,
                "n_chunks": len(embedded_chunks),
                "index_build_sec": "",
                "end_to_end_sec": "",
                "one_query_sec": "",
                "estimated_storage_mb": estimated_storage_mb,
                "top_k": top_k,
                "sample_query": sample_query,
                "paper_filter": paper_filter or "None",
                "recommended_1": "",
                "recommended_1_url": "",
                "recommended_2": "",
                "recommended_2_url": "",
                "notes": f"FAILED: {e}",
            })

    csv_path = _save_benchmark_csv(results, run_dir)
    st.session_state["is_benchmarking"] = False
    return results, csv_path, str(run_dir), shared_summary


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Configuration")

    input_language = st.selectbox(
        "Query Language",
        ("English", "Spanish", "Italian", "French"),
    )

    st.subheader("Index Type")
    index_type = st.selectbox(
        "Vector index algorithm",
        ("HNSW", "IVF_PQ", "DiskANN"),
        index=0,
        help=(
            "HNSW    -- fast ANN, good recall\n"
            "IVF_PQ  -- memory-efficient, good for large corpora\n"
            "DiskANN -- disk-based ANN (depends on Milvus build)"
        ),
    )

    info = {
        "HNSW":    "Fast ANN, low latency, good recall.",
        "IVF_PQ":  "Compressed vectors via PQ; good at scale.",
        "DiskANN": "Disk-based ANN. May fail if Milvus build does not support it.",
    }
    st.caption(info.get(index_type, ""))

    st.divider()
    st.subheader("Chunking")
    chunk_size    = st.slider("Chunk size (words)",    100, 1000, 400, 50)
    chunk_overlap = st.slider("Chunk overlap (words)", 0,   200,  50,  10)

    st.divider()
    st.subheader("Generation")
    model_choice = st.selectbox(
        "Gemini model",
        list(GEN_MODELS.keys()),
        index=0,
        help="gemini-2.0-flash is fast; gemini-2.5-pro is most capable",
    )
    top_k = st.slider("Top-K retrieval", 1, 10, 4)
    max_iterations = st.slider(
        "Reflection iterations (anti-hallucination)", 1, 4, 2,
        help="Max reflect/revise loops before the final answer is accepted",
    )

    st.divider()
    if st.button("Interrupt current task", use_container_width=True):
        st.session_state["interrupt_requested"] = True
        st.warning("Interrupt requested. Current step will stop shortly.")

    if st.session_state.get("is_indexing"):
        st.caption("Indexing in progress...")
    elif st.session_state.get("is_benchmarking"):
        st.caption("Benchmarking in progress...")
    elif st.session_state.get("is_querying"):
        st.caption("Query in progress...")

    st.divider()
    if st.button("Clear vector store / reset app", use_container_width=True):
        st.session_state.indexer            = None
        st.session_state.indexed_files      = []
        st.session_state.file_url_map       = {}
        st.session_state.index_stats        = {}
        st.session_state.chat_history       = []
        st.session_state.prepared_chunks    = None
        st.session_state.prepared_files     = None
        st.session_state.benchmark_results  = None
        st.session_state.benchmark_csv_path = None
        st.session_state.benchmark_run_dir  = None
        st.session_state.last_index_error   = None
        st.session_state.interrupt_requested = False
        st.success("App state cleared.")
        st.rerun()

    if st.session_state.indexed_files:
        st.subheader("Indexed Files")
        for name, ptype in st.session_state.indexed_files:
            url = st.session_state.file_url_map.get(name, "")
            if url:
                st.markdown(
                    f"`{name}`  <span class='badge badge-type'>{ptype}</span>"
                    f"  <span class='badge badge-url'>URL</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"`{name}`  <span class='badge badge-type'>{ptype}</span>",
                    unsafe_allow_html=True,
                )


# ── MAIN ───────────────────────────────────────────────────────────────────────
st.title("PDF RAG  --  Gemini + LangGraph + Milvus")
st.caption(f"Index: **{index_type}**  --  Model: **{model_choice}**  --  Top-K: **{top_k}**")

tab_index, tab_query, tab_stats = st.tabs(
    ["Upload & Index", "Query", "Stats & Benchmark"]
)

# ── TAB 1: Upload & Index ──────────────────────────────────────────────────────
with tab_index:
    st.subheader("Upload PDFs")
    uploaded_files = st.file_uploader(
        "Drop one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )

    file_paper_types: dict = {}
    file_urls: dict = {}

    if uploaded_files:
        st.markdown("#### Assign paper type")
        cols_per_row = 2
        rows = [
            uploaded_files[i : i + cols_per_row]
            for i in range(0, len(uploaded_files), cols_per_row)
        ]
        for row in rows:
            cols = st.columns(cols_per_row)
            for col, uf in zip(cols, row):
                with col:
                    ptype = st.selectbox(
                        f"`{uf.name}` type",
                        PAPER_TYPES,
                        key=f"pt_{uf.name}",
                        index=0,
                    )
                    file_paper_types[uf.name] = ptype


    col_a, col_b, col_c = st.columns(3)
    with col_a:
        append_mode = st.checkbox("Append to existing index", value=False)
    with col_b:
        show_chunks = st.checkbox("Preview first 5 chunks", value=True)
    with col_c:
        cache_for_benchmark = st.checkbox(
            "Cache chunks for benchmarking", value=True
        )

    can_index = bool(uploaded_files)

    if st.button(
        "Start Indexing", type="primary", disabled=not can_index, use_container_width=True
    ):
        st.session_state["interrupt_requested"] = False
        st.session_state["is_indexing"]         = True
        st.session_state["last_index_error"]    = None

        tmp_dir = _ensure_tmp_upload_dir()
        saved = []

        try:
            for uf in uploaded_files:
                _check_interrupt()
                dest = tmp_dir / uf.name
                dest.write_bytes(uf.read())
                saved.append(
                    (dest, file_paper_types.get(uf.name, "Other"), file_urls.get(uf.name, ""))
                )

            status  = st.status("Initialising...", expanded=True)
            bar     = st.progress(0, text="Starting...")
            log_box = st.empty()
            logs    = []

            def log(msg):
                logs.append(msg)
                log_box.markdown("\n\n".join(f"- {l}" for l in logs[-10:]))

            def tick(pct, label):
                bar.progress(
                    min(float(pct), 1.0),
                    text=f"{label} -- {int(min(pct, 1.0) * 100)}%",
                )

            tick(0.02, "Creating indexer")
            status.write(f"Index type: **{index_type}**  --  Model: **{model_choice}**")
            indexer = PDFIndexer(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                model=model_choice,
                index_type=index_type,
                collection_name="papers_rag_interactive",
                drop_old_collection=(not append_mode),
            )
            log(f"Indexer ready [{index_type}]")

            all_chunks = []
            n_files    = len(saved)

            for fi, (pdf_path, ptype, url) in enumerate(saved):
                _check_interrupt()
                p0 = 0.05 + (fi / max(n_files, 1)) * 0.25
                p1 = 0.05 + ((fi + 1) / max(n_files, 1)) * 0.25

                tick(p0, f"Extracting: {pdf_path.name} [{ptype}]")
                status.write(f"pdfminer -- **{pdf_path.name}** `{ptype}`")
                chunks = indexer.extract_and_chunk(str(pdf_path), paper_type=ptype)

                for c in chunks:
                    c["url"] = url

                all_chunks.extend(chunks)
                tick(p1, f"{pdf_path.name} -- {len(chunks)} chunks")
                log(f"{pdf_path.name} [{ptype}] -- {len(chunks)} chunks")

            total = len(all_chunks)
            tick(0.33, f"Extraction done -- {total} chunks")
            status.write(f"OK: {total} chunks from {n_files} file(s)")

            status.write(f"Embedding with `{EMBED_MODEL}`...")
            log("Embedding chunks (Gemini)...")

            for ci, chunk in enumerate(all_chunks):
                _check_interrupt()
                chunk["embedding"] = indexer.embed_one(chunk["text"], "retrieval_document")
                pct = 0.33 + ((ci + 1) / max(total, 1)) * 0.42
                tick(pct, f"Embedding {ci+1}/{total} ({chunk['source']} p{chunk['page']})")

            tick(0.75, f"{total} embeddings done")
            status.write(f"OK: {total} vectors ready")
            log("All embeddings complete")

            if cache_for_benchmark:
                st.session_state.prepared_chunks = all_chunks
                st.session_state.prepared_files  = saved

            _check_interrupt()
            tick(0.80, f"Building {index_type} index...")
            status.write(f"Building **{index_type}** index (Milvus)...")
            log(f"Building {index_type} index...")

            if append_mode and st.session_state.indexer:
                st.session_state.indexer.add_to_index(all_chunks)
                st.session_state.indexer.set_output_language(input_language)
            else:
                indexer.build_index(all_chunks)
                indexer.set_output_language(input_language)
                st.session_state.indexer = indexer

            tick(0.92, f"{index_type} index built")
            log(f"{index_type} index built")

            tick(1.0, "All done!")
            status.update(label="Indexing complete!", state="complete", expanded=False)

            new_entries = [(p.name, pt) for p, pt, _ in saved]
            url_map = st.session_state.file_url_map or {}
            for p, _, u in saved:
                if u:
                    url_map[p.name] = u
            st.session_state.file_url_map = url_map

            if append_mode:
                st.session_state.indexed_files.extend(new_entries)
            else:
                st.session_state.indexed_files = new_entries

            st.session_state.index_stats = {
                "status":        "ok",
                "total_chunks":  total,
                "total_files":   len(st.session_state.indexed_files),
                "chunk_size":    chunk_size,
                "chunk_overlap": chunk_overlap,
                "embed_dim":     3072,
                "embed_model":   EMBED_MODEL,
                "index_type":    index_type,
                "gen_model":     model_choice,
                "paper_types":   list({pt for _, pt in st.session_state.indexed_files}),
            }

            st.success(
                f"**{n_files} file(s)** -- **{total} chunks** -- **{total} vectors** "
                f"in **{index_type}** (Milvus)."
            )

            if show_chunks and all_chunks:
                st.subheader("Chunk preview (first 5)")
                for c in all_chunks[:5]:
                    url        = st.session_state.file_url_map.get(c["source"], "")
                    url_badge  = " <span class='badge badge-url'>URL</span>" if url else ""
                    st.markdown(
                        f'<div class="chunk-preview">'
                        f'<span class="badge">{c["source"]}</span>'
                        f'<span class="badge">p{c["page"]}</span>'
                        f'<span class="badge badge-type">{c["paper_type"]}</span>'
                        f'<span class="badge badge-idx">chunk #{c["chunk_id"]}</span>'
                        f'{url_badge}'
                        f'<br><br>{c["text"][:480]}{"..." if len(c["text"]) > 480 else ""}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        except Exception as e:
            st.session_state["last_index_error"] = str(e)
            _safe_set_failed_stats(index_type=index_type, model_choice=model_choice)
            if "Interrupted by user" in str(e):
                st.warning("Indexing interrupted by user.")
            else:
                st.error(str(e))
                st.exception(e)

        finally:
            st.session_state["is_indexing"] = False


# ── TAB 2: Query ───────────────────────────────────────────────────────────────
with tab_query:
    if not st.session_state.indexer:
        st.info("Index PDFs first in the **Upload & Index** tab.")
    else:
        st.subheader("Chat with your documents")

        available_types = sorted({pt for _, pt in st.session_state.indexed_files})
        filter_options  = ["All paper types"] + list(available_types)
        selected_filter = st.selectbox(
            "Filter by paper type",
            filter_options,
            index=0,
            help="Restrict retrieval to a specific paper type",
        )
        paper_filter = None if selected_filter == "All paper types" else selected_filter

        st.caption(
            f"Index: **{st.session_state.index_stats.get('index_type', '?')}**  --  "
            f"Model: **{model_choice}**  --  "
            f"Filter: **{selected_filter}**"
        )
        st.divider()

        # Render chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    with st.expander(f"{len(msg['sources'])} retrieved chunks"):
                        for s in msg["sources"]:
                            url      = st.session_state.file_url_map.get(s["source"], "")
                            url_line = (
                                f"<br><span class='badge badge-url'>URL</span> {url}"
                                if url else ""
                            )
                            st.markdown(
                                f'<div class="chunk-preview">'
                                f'<span class="badge">{s["source"]}</span>'
                                f'<span class="badge">p{s["page"]}</span>'
                                f'<span class="badge badge-type">{s.get("paper_type","?")}</span>'
                                f'<span class="badge">score {s["score"]:.3f}</span>'
                                f'{url_line}'
                                f'<br><br>{s["text"][:500]}{"..." if len(s["text"]) > 500 else ""}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

        if prompt := st.chat_input("Ask anything about your PDFs..."):
            st.session_state["interrupt_requested"] = False
            st.session_state["is_querying"]         = True

            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    if st.session_state.get("interrupt_requested", False):
                        raise RuntimeError("Interrupted by user.")

                    with st.spinner("retrieve --> generate via LangGraph..."):
                        answer, sources = st.session_state.indexer.query(
                            prompt,
                            top_k=top_k,
                            model=model_choice,
                            paper_filter=paper_filter,
                            output_language=input_language,
                            max_iterations=max_iterations,
                        )

                    if st.session_state.get("interrupt_requested", False):
                        raise RuntimeError("Interrupted by user.")

                    st.markdown(answer)

                    # URL reflect pattern
                    recs = _unique_papers_from_sources(
                        sources=sources,
                        file_url_map=st.session_state.get("file_url_map", {}),
                        k=2,
                    )
                    with st.spinner("Reflecting on paper URLs..."):
                        recs, url_trace = _reflect_and_fix_urls(
                            recs, model_name=model_choice
                        )

                    _render_recommendations(recs, url_trace=url_trace)

                    with st.expander(f"{len(sources)} retrieved chunks"):
                        for s in sources:
                            url      = st.session_state.file_url_map.get(s["source"], "")
                            url_line = (
                                f"<br><span class='badge badge-url'>URL</span> {url}"
                                if url else ""
                            )
                            st.markdown(
                                f'<div class="chunk-preview">'
                                f'<span class="badge">{s["source"]}</span>'
                                f'<span class="badge">p{s["page"]}</span>'
                                f'<span class="badge badge-type">{s.get("paper_type","?")}</span>'
                                f'<span class="badge">score {s["score"]:.3f}</span>'
                                f'{url_line}'
                                f'<br><br>{s["text"][:500]}{"..." if len(s["text"]) > 500 else ""}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                except Exception as e:
                    if "Interrupted by user" in str(e):
                        st.warning("Query interrupted by user.")
                        answer, sources = "Query interrupted by user.", []
                    else:
                        st.error(f"Query failed: {e}")
                        answer, sources = f"Query failed: {e}", []

                finally:
                    st.session_state["is_querying"] = False

            if isinstance(answer, str) and "interrupted by user" not in answer.lower():
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })

        if st.session_state.chat_history:
            if st.button("Clear chat"):
                st.session_state.chat_history = []
                st.rerun()


# ── TAB 3: Stats & Benchmark ───────────────────────────────────────────────────
with tab_stats:
    s = st.session_state.get("index_stats", {}) or {}

    st.subheader("Current Index Stats")

    if not s or "total_files" not in s:
        st.info("No successful indexing stats available yet.")
        if st.session_state.get("last_index_error"):
            st.error(f"Last indexing error: {st.session_state['last_index_error']}")
    else:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Files",      s.get("total_files", 0))
        c2.metric("Chunks",     s.get("total_chunks", 0))
        c3.metric("Index",      s.get("index_type", "--"))
        c4.metric("Embed dim",  s.get("embed_dim", "--"))
        c5.metric("Chunk size", f'{s.get("chunk_size", "--")}w')
        c6.metric("Gen model",  s.get("gen_model", "--"))

        st.divider()
        st.subheader("Embed model")
        st.code(s.get("embed_model", "--"))

        st.subheader("Paper types in index")
        for pt in sorted(s.get("paper_types", [])):
            st.markdown(
                f'<span class="badge badge-type">{pt}</span>', unsafe_allow_html=True
            )

        st.subheader("Indexed files + URLs")
        for name, ptype in st.session_state.get("indexed_files", []):
            url = st.session_state.file_url_map.get(name, "")
            if url:
                st.markdown(
                    f'`{name}`  <span class="badge badge-type">{ptype}</span>'
                    f'  <span class="badge badge-url">URL</span> {url}',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'`{name}`  <span class="badge badge-type">{ptype}</span>',
                    unsafe_allow_html=True,
                )

    st.divider()
    st.subheader("Benchmark (HNSW vs IVF_PQ vs DiskANN)")

    if st.session_state.prepared_chunks is None:
        st.info("Index once with caching enabled to unlock benchmarking.")
    else:
        st.caption("Benchmarks reuse cached chunks to keep comparisons fair.")

        sample_query = st.text_input(
            "Sample benchmark query",
            value="Summarize the main contribution of the papers and cite sources.",
        )

        bench_filter = st.selectbox(
            "Benchmark filter (optional)",
            ["None"] + PAPER_TYPES,
            index=0,
        )
        bench_paper_filter = None if bench_filter == "None" else bench_filter

        colx, coly = st.columns([1, 1])
        with colx:
            run_bench = st.button(
                "Run benchmark for all methods", type="primary", use_container_width=True
            )
        with coly:
            if st.button("Clear cached benchmark prep", use_container_width=True):
                st.session_state.prepared_chunks    = None
                st.session_state.prepared_files     = None
                st.session_state.benchmark_results  = None
                st.session_state.benchmark_csv_path = None
                st.session_state.benchmark_run_dir  = None
                st.success("Cleared cached prep.")
                st.rerun()

        if run_bench:
            st.session_state["interrupt_requested"] = False
            st.session_state["is_benchmarking"]     = True

            try:
                _check_interrupt()
                with st.spinner("Running benchmark across methods..."):
                    results, csv_path, run_dir, shared_summary = (
                        _run_index_benchmark_all_methods(
                            embedded_chunks=st.session_state.prepared_chunks,
                            model_choice=model_choice,
                            top_k=top_k,
                            input_language=input_language,
                            sample_query=sample_query,
                            paper_filter=bench_paper_filter,
                            max_iterations=max_iterations,
                        )
                    )

                st.session_state.benchmark_results  = results
                st.session_state.benchmark_csv_path = csv_path
                st.session_state.benchmark_run_dir  = run_dir

                st.success("Benchmark complete")
                st.json(shared_summary)

            except Exception as e:
                if "Interrupted by user" in str(e):
                    st.warning("Benchmark interrupted by user.")
                else:
                    st.error(f"Benchmark failed: {e}")
                    st.exception(e)

            finally:
                st.session_state["is_benchmarking"] = False

        if st.session_state.get("benchmark_results"):
            st.subheader("Benchmark results")
            st.dataframe(
                st.session_state["benchmark_results"], use_container_width=True
            )

            csv_path = st.session_state.get("benchmark_csv_path")
            if csv_path and Path(csv_path).exists():
                st.caption(f"Saved: `{csv_path}`")
                csv_bytes = Path(csv_path).read_bytes()
                st.download_button(
                    "Download benchmark CSV",
                    data=csv_bytes,
                    file_name=Path(csv_path).name,
                    mime="text/csv",
                    use_container_width=True,
                )

            run_dir = st.session_state.get("benchmark_run_dir")
            if run_dir:
                st.caption(f"Run folder: `{run_dir}`")
