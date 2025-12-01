"""
Streamlit app for the AU TA Chatbot.

This is the web UI that users interact with. It provides:
- Chat interface for asking questions
- Source display with citations
- PDF upload functionality
- Settings controls (top-k, threshold, etc.)
- Database statistics

Streamlit Basics:
- st.* functions render UI components
- st.session_state stores data between reruns (like a global dict)
- Any user interaction causes a full script rerun from top to bottom
- Use st.cache_resource or session_state to avoid re-initializing heavy objects
"""

import streamlit as st
from pathlib import Path
import shutil
from typing import List, Dict, Any
import sys

# Add src to path for imports
# This allows us to import from src/ when running from root directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.vectordb import get_vectordb
from src.retriever import get_retriever
from src.llm import get_llm
from src.rag_chain import create_rag_chain
from src.ingestion import ingest_document
from src.utils.logging_setup import setup_logging
from src.utils.citations import format_source_block, format_source_for_display

# Setup logging - do this once at module level
setup_logging(level=config.log_level)

# Page config
st.set_page_config(
    page_title="AU TA Chatbot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """
    Initialize session state variables.
    
    Streamlit's session_state persists data across reruns (user interactions).
    Think of it as a dictionary that survives page refreshes.
    
    We store:
    - messages: Chat history (list of dicts)
    - vectordb: Database connection (heavy, initialize once)
    - retriever: Retrieval engine (depends on vectordb)
    - llm: Language model (heavy, initialize once)
    - rag_chain: Orchestrator (combines retriever + llm)
    - show_scores: Debug toggle for showing similarity scores
    - stats: Session statistics (query counts, response times, etc.)
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []  # Chat history
    if "vectordb" not in st.session_state:
        st.session_state.vectordb = None  # Vector database connection
    if "retriever" not in st.session_state:
        st.session_state.retriever = None  # Retrieval engine
    if "llm" not in st.session_state:
        st.session_state.llm = None  # Language model
    if "rag_chain" not in st.session_state:
        st.session_state.rag_chain = None  # RAG orchestrator
    if "show_scores" not in st.session_state:
        st.session_state.show_scores = False  # Debug mode toggle
    if "stats" not in st.session_state:
        # Session statistics
        st.session_state.stats = {
            "total_queries": 0,
            "grounded": 0,
            "chitchat": 0,
            "fallback": 0,
            "total_response_time": 0.0,
            "total_confidence": 0.0,
            "confidence_count": 0
        }


def init_components():
    """
    Initialize RAG components (lazy initialization).
    
    Why lazy? These are heavy objects (loading models, connecting to DB).
    We only want to create them once and reuse across reruns.
    
    Streamlit reruns the entire script on every interaction, so we check
    if components already exist in session_state before creating them.
    
    Order matters: vectordb → llm → retriever → rag_chain
    (dependencies flow left to right)
    """
    # Initialize vector database connection (ChromaDB)
    if st.session_state.vectordb is None:
        with st.spinner("Initializing vector database..."):
            st.session_state.vectordb = get_vectordb()
    
    # Initialize LLM (Ollama, OpenAI, or transformers)
    if st.session_state.llm is None:
        with st.spinner("Loading LLM..."):
            # This might take a while for transformers fallback
            st.session_state.llm = get_llm()
    
    # Initialize retriever (uses vectordb, respects slider settings)
    if st.session_state.retriever is None:
        st.session_state.retriever = get_retriever(
            st.session_state.vectordb,
            # Get slider values from session_state, fallback to config defaults
            top_k=st.session_state.get("top_k_slider", config.top_k),
            score_threshold=st.session_state.get("threshold_slider", config.score_threshold)
        )
    
    # Initialize RAG chain (combines retriever + llm)
    if st.session_state.rag_chain is None:
        st.session_state.rag_chain = create_rag_chain(
            st.session_state.retriever,
            st.session_state.llm
        )


def render_sidebar():
    """Render the sidebar with controls and status."""
    with st.sidebar:
        st.title("🎓 AU TA Chatbot")
        st.markdown("*RAG-powered Teaching Assistant*")
        
        st.divider()
        
        # Database status
        st.subheader("📊 Database Status")
        if st.session_state.vectordb:
            stats = st.session_state.vectordb.get_stats()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Documents", stats["unique_documents"])
            with col2:
                st.metric("Chunks", stats["total_chunks"])
            
            if stats["sources"]:
                with st.expander("View Sources"):
                    for source in stats["sources"]:
                        st.text(f"• {Path(source).name}")
        else:
            st.info("Database not initialized")
        
        st.divider()
        
        # Model info
        st.subheader("🤖 Model Info")
        if st.session_state.llm:
            info = st.session_state.llm.get_backend_info()
            st.text(f"Backend: {info['backend']}")
            st.text(f"Model: {info['model']}")
            st.text(f"Temp: {info['temperature']}")
        
        st.divider()
        
        # Retrieval settings
        st.subheader("⚙️ Retrieval Settings")
        
        top_k = st.slider(
            "Top K Results",
            min_value=1,
            max_value=10,
            value=config.top_k,
            key="top_k_slider",
            help="Number of documents to retrieve"
        )
        
        threshold = st.slider(
            "Score Threshold",
            min_value=0.0,
            max_value=1.0,
            value=config.score_threshold,
            step=0.05,
            key="threshold_slider",
            help="Minimum similarity score"
        )
        
        # Update retriever if settings changed
        if (st.session_state.retriever and 
            (st.session_state.retriever.top_k != top_k or 
             st.session_state.retriever.score_threshold != threshold)):
            st.session_state.retriever.top_k = top_k
            st.session_state.retriever.score_threshold = threshold
        
        st.divider()
        
        # File upload
        st.subheader("📤 Upload Documents")
        uploaded_files = st.file_uploader(
            "Add documents",
            type=["pdf", "srt", "txt", "md"],
            accept_multiple_files=True,
            help="Upload documents (PDF, SRT, TXT, MD) to add to the knowledge base"
        )
        
        if uploaded_files and st.button("Process Uploads", type="primary"):
            process_uploaded_files(uploaded_files)
        
        st.divider()
        
        # Session Statistics Dashboard
        st.subheader("📊 Session Statistics")
        stats = st.session_state.stats
        
        if stats["total_queries"] > 0:
            # Total queries
            st.metric("Total Questions", stats["total_queries"])
            
            # Mode distribution
            col1, col2, col3 = st.columns(3)
            with col1:
                grounded_pct = (stats["grounded"] / stats["total_queries"] * 100) if stats["total_queries"] > 0 else 0
                st.metric("📚 Grounded", f"{stats['grounded']}", f"{grounded_pct:.0f}%")
            with col2:
                chitchat_pct = (stats["chitchat"] / stats["total_queries"] * 100) if stats["total_queries"] > 0 else 0
                st.metric("💬 Chitchat", f"{stats['chitchat']}", f"{chitchat_pct:.0f}%")
            with col3:
                fallback_pct = (stats["fallback"] / stats["total_queries"] * 100) if stats["total_queries"] > 0 else 0
                st.metric("⚠️ Fallback", f"{stats['fallback']}", f"{fallback_pct:.0f}%")
            
            # Average metrics
            avg_time = stats["total_response_time"] / stats["total_queries"] if stats["total_queries"] > 0 else 0
            avg_confidence = stats["total_confidence"] / stats["confidence_count"] if stats["confidence_count"] > 0 else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Response", f"{avg_time:.2f}s")
            with col2:
                if stats["confidence_count"] > 0:
                    st.metric("Avg Confidence", f"{avg_confidence*100:.0f}%")
        else:
            st.info("Ask a question to see statistics")
        
        st.divider()
        
        # Actions
        st.subheader("🔧 Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("New Chat"):
                st.session_state.messages = []
                # Reset stats
                st.session_state.stats = {
                    "total_queries": 0,
                    "grounded": 0,
                    "chitchat": 0,
                    "fallback": 0,
                    "total_response_time": 0.0,
                    "total_confidence": 0.0,
                    "confidence_count": 0
                }
                st.rerun()
        
        with col2:
            if st.button("Rebuild Index"):
                rebuild_index()
        
        # Debug toggle
        st.checkbox(
            "Show retrieval scores",
            key="show_scores",
            help="Display relevance scores for debugging"
        )


def process_uploaded_files(uploaded_files):
    """Process uploaded document files (any supported type)."""
    data_dir = Path("data/uploads")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_chunks = 0
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")
        
        # Save file
        file_path = data_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Ingest using generic document loader
        try:
            chunks_added = ingest_document(
                file_path,
                st.session_state.vectordb,
                force_reindex=True,
                data_root=data_dir
            )
            total_chunks += chunks_added
        except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.empty()
    progress_bar.empty()
    
    st.success(f"✅ Processed {len(uploaded_files)} files ({total_chunks} chunks added)")
    st.rerun()


def rebuild_index():
    """Rebuild the vector database index."""
    with st.spinner("Rebuilding index..."):
        try:
            st.session_state.vectordb.delete_collection()
            st.session_state.retriever = None
            st.session_state.rag_chain = None
            st.success("Index rebuilt! Please re-ingest your documents.")
        except Exception as e:
            st.error(f"Error rebuilding index: {e}")


def render_mode_indicator(mode: str, metadata: Dict[str, Any] = None):
    """Render a styled mode indicator badge."""
    if mode == "chitchat":
        st.markdown(
            """
            <div style="
                background-color: #E1BEE7;
                border-left: 4px solid #9C27B0;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            ">
                <strong>💬 CHITCHAT</strong> · Natural conversation - no retrieval performed
            </div>
            """,
            unsafe_allow_html=True
        )
    elif mode == "grounded":
        # Calculate confidence if metadata available
        avg_score = metadata.get("avg_score", 0.0) if metadata else 0.0
        num_sources = metadata.get("retrieved_chunks", 0) if metadata else 0
        
        confidence_bar = "█" * int(avg_score * 10) + "░" * (10 - int(avg_score * 10))
        
        st.markdown(
            f"""
            <div style="
                background-color: #C8E6C9;
                border-left: 4px solid #4CAF50;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            ">
                <strong>📚 GROUNDED</strong> · Answer based on {num_sources} course document{"s" if num_sources != 1 else ""}<br/>
                <span style="font-size: 0.9em;">Confidence: {confidence_bar} {avg_score*100:.0f}%</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif mode == "fallback":
        st.markdown(
            """
            <div style="
                background-color: #FFE0B2;
                border-left: 4px solid #FF9800;
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
            ">
                <strong>⚠️ FALLBACK</strong> · Answer based on general knowledge - no relevant documents found
            </div>
            """,
            unsafe_allow_html=True
        )


def render_timing_info(metadata: Dict[str, Any]):
    """Render response timing information."""
    if metadata and "timing" in metadata:
        timing = metadata["timing"]
        total = timing.get("total", 0.0)
        retrieval = timing.get("retrieval", 0.0)
        generation = timing.get("generation", 0.0)
        
        st.markdown(
            f"""
            <div style="
                font-size: 0.85em;
                color: #666;
                padding: 8px;
                background-color: #f5f5f5;
                border-radius: 5px;
                margin-top: 10px;
            ">
                ⏱️ <strong>Response time:</strong> {total:.2f}s 
                (Retrieval: {retrieval:.2f}s · Generation: {generation:.2f}s)
            </div>
            """,
            unsafe_allow_html=True
        )


def render_message(message: Dict[str, Any]):
    """Render a chat message."""
    role = message["role"]
    content = message["content"]
    mode = message.get("mode", "grounded")  # Default to grounded for backward compatibility
    metadata = message.get("metadata", {})
    
    with st.chat_message(role):
        # Show styled mode indicators for assistant messages
        if role == "assistant":
            render_mode_indicator(mode, metadata)
        
        st.markdown(content)
        
        # Show timing info for assistant messages
        if role == "assistant" and metadata:
            render_timing_info(metadata)
        
        # Show sources for assistant messages (only in grounded mode)
        if role == "assistant" and "sources" in message:
            sources = message["sources"]
            citations = message.get("citations", [])
            
            if sources and mode == "grounded":
                with st.expander(f"📚 Sources ({len(sources)})"):
                    for i, source in enumerate(sources, 1):
                        metadata = source.get("metadata", {})
                        score = source.get("score", 0.0)
                        
                        # Use file-type-aware formatting
                        display_info = format_source_for_display(metadata, score)
                        title = display_info["display_title"]
                        location = display_info["display_location"]
                        
                        st.markdown(f"**{i}. {title}** ({location})")
                        
                        if st.session_state.show_scores:
                            st.caption(f"Relevance: {score:.3f}")
                        
                        # Show snippet
                        snippet = source.get("text", "")[:300]
                        if len(source.get("text", "")) > 300:
                            snippet += "..."
                        st.markdown(f"> {snippet}")
                        
                        st.divider()
            
            # Show appropriate message for non-grounded modes
            elif mode == "fallback":
                st.info("📝 **No citations available** - Answer not based on course documents.")
            elif mode == "chitchat":
                # Don't show anything extra for chitchat (already have banner above)
                pass


def main():
    """Main app function."""
    # Initialize
    init_session_state()
    init_components()
    
    # Render sidebar
    render_sidebar()
    
    # Main content
    st.title("🎓 AU TA Chatbot")
    st.markdown("Ask questions about your course materials. Answers include citations and sources.")
    
    # Check if database has content
    if st.session_state.vectordb:
        stats = st.session_state.vectordb.get_stats()
        if stats["total_chunks"] == 0:
            st.warning("⚠️ No documents in the database. Add documents (PDF, SRT, TXT, MD) to data/ and run ingestion to get started.")
            st.code("python -m src.ingestion --data_dir data")
    
    # Chat history
    for message in st.session_state.messages:
        render_message(message)
    
    # ===== CHAT INPUT =====
    # The walrus operator := assigns and returns the value in one line
    # This runs when user presses Enter in the chat box
    if prompt := st.chat_input("Ask a question about your course materials..."):
        # Store user message in chat history
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Display user message immediately (with user avatar)
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # ===== GENERATE RESPONSE =====
        # Display in assistant bubble (with bot avatar)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):  # Show loading animation
                try:
                    # Call the RAG pipeline (retrieve → generate → cite)
                    result = st.session_state.rag_chain.query(prompt)
                    
                    # Unpack results
                    answer = result["answer"]
                    sources = result["sources"]
                    citations = result["citations"]
                    mode = result.get("mode", "grounded")  # Get the mode (grounded, fallback, or chitchat)
                    metadata = result.get("metadata", {})
                    
                    # Update session statistics
                    st.session_state.stats["total_queries"] += 1
                    if mode == "grounded":
                        st.session_state.stats["grounded"] += 1
                        if "avg_score" in metadata:
                            st.session_state.stats["total_confidence"] += metadata["avg_score"]
                            st.session_state.stats["confidence_count"] += 1
                    elif mode == "chitchat":
                        st.session_state.stats["chitchat"] += 1
                    elif mode == "fallback":
                        st.session_state.stats["fallback"] += 1
                    
                    if "timing" in metadata:
                        st.session_state.stats["total_response_time"] += metadata["timing"].get("total", 0.0)
                    
                    # Show styled mode indicator
                    render_mode_indicator(mode, metadata)
                    
                    # Display answer text
                    st.markdown(answer)
                    
                    # Show timing information
                    render_timing_info(metadata)
                    
                    # Save to history (for persistence across reruns)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "citations": citations,
                        "mode": mode,  # Save mode for rendering later
                        "metadata": metadata  # Save metadata for timing and confidence
                    })
                    
                    # ===== SHOW SOURCES =====
                    # Collapsible section with retrieved documents (only in grounded mode)
                    if sources and mode == "grounded":
                        with st.expander(f"📚 Sources ({len(sources)})"):
                            for i, source in enumerate(sources, 1):
                                # Extract metadata from source
                                metadata = source.get("metadata", {})
                                score = source.get("score", 0.0)  # Similarity score
                                
                                # Use file-type-aware formatting
                                display_info = format_source_for_display(metadata, score)
                                title = display_info["display_title"]
                                location = display_info["display_location"]
                                
                                # Display source header
                                st.markdown(f"**{i}. {title}** ({location})")
                                
                                # Show score if debug mode enabled
                                if st.session_state.show_scores:
                                    st.caption(f"Relevance: {score:.3f}")
                                
                                # Show snippet (first 300 chars)
                                snippet = source.get("text", "")[:300]
                                if len(source.get("text", "")) > 300:
                                    snippet += "..."
                                st.markdown(f"> {snippet}")
                                
                                st.divider()
                    
                    # Show appropriate message for non-grounded modes
                    elif mode == "fallback":
                        st.info("📝 **No citations available** - Answer not based on course documents.")
                    elif mode == "chitchat":
                        # No sources section needed for chitchat (already have banner)
                        pass
                
                except Exception as e:
                    # Handle errors gracefully
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    # Save error to history so it's visible on rerun
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })


if __name__ == "__main__":
    main()

