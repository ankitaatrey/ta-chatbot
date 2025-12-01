"""
Streamlit comparison app: RAG vs Plain ChatGPT

This app shows side-by-side comparison of:
- Left: Plain ChatGPT (no course PDFs)
- Right: RAG-powered TA chatbot (with course PDFs)
"""

import streamlit as st
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.comparison import answer_with_rag, answer_with_chatgpt_only, EXAMPLE_QUESTIONS
from src.config import config
from src.utils.logging_setup import setup_logging
from src.utils.citations import format_citations_list, format_source_for_display

# Setup logging
setup_logging(level=config.log_level)

# Page config
st.set_page_config(
    page_title="RAG vs ChatGPT Comparison",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables."""
    if "comparison_history" not in st.session_state:
        st.session_state.comparison_history = []


def render_sidebar():
    """Render the sidebar with information and examples."""
    with st.sidebar:
        st.title("🔬 Comparison Mode")
        st.markdown("*RAG vs Plain ChatGPT*")
        
        st.divider()
        
        st.subheader("📖 About")
        st.markdown("""
        This page compares two approaches:
        
        **Left (ChatGPT):**
        - No course PDFs
        - General knowledge only
        - May hallucinate or give generic answers
        
        **Right (RAG TA Bot):**
        - Uses your course PDFs
        - Retrieves relevant context
        - Provides citations with page numbers
        """)
        
        st.divider()
        
        st.subheader("💡 Example Questions")
        st.markdown("Click to try:")
        
        for i, example in enumerate(EXAMPLE_QUESTIONS):
            if st.button(f"📝 {example[:50]}...", key=f"example_{i}"):
                st.session_state.selected_question = example
                st.rerun()
        
        st.divider()
        
        st.subheader("⚙️ Configuration")
        st.text(f"Model: {config.openai_model}")
        st.text(f"API Key: {'✓ Set' if config.openai_api_key else '✗ Missing'}")
        
        if not config.openai_api_key:
            st.warning("⚠️ Set OPENAI_API_KEY in .env")


def render_answer_panel(title: str, answer: str, is_rag: bool = False, sources=None, citations=None, mode: str = "grounded", metadata: dict = None):
    """
    Render an answer panel with optional sources.
    
    Args:
        title: Panel title
        answer: Answer text to display
        is_rag: Whether this is a RAG answer (shows sources)
        sources: Source documents (for RAG)
        citations: Citation objects (for RAG)
        mode: "grounded", "fallback", or "chitchat" (for RAG answers)
        metadata: Metadata dict with timing and scores
    """
    st.markdown(f"### {title}")
    
    # Show mode-specific styled badges
    if is_rag:
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
                    <strong>💬 CHITCHAT</strong> · Natural conversation
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
                    <strong>⚠️ FALLBACK</strong> · General knowledge - no relevant documents
                </div>
                """,
                unsafe_allow_html=True
            )
        elif mode == "grounded":
            # Show confidence score for grounded answers
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
                    <strong>📚 GROUNDED</strong> · {num_sources} source{"s" if num_sources != 1 else ""}<br/>
                    <span style="font-size: 0.9em;">Confidence: {confidence_bar} {avg_score*100:.0f}%</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Determine border color based on mode
    if is_rag:
        if mode == "chitchat":
            border_color = "#9C27B0"  # Purple for chitchat
            bg_color = "#F3E5F5"      # Light purple
        elif mode == "fallback":
            border_color = "#FFA726"  # Orange for fallback
            bg_color = "#FFF3E0"      # Light orange
        else:
            border_color = "#4CAF50"  # Green for grounded
            bg_color = "#f1f8f4"      # Light green
    else:
        border_color = "#2196F3"      # Blue for ChatGPT
        bg_color = "#e3f2fd"          # Light blue
    
    # Answer box with styling
    st.markdown(
        f"""
        <div style="
            padding: 20px;
            border: 2px solid {border_color};
            border-radius: 10px;
            background-color: {bg_color};
            min-height: 200px;
        ">
            {answer}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Show timing information if available
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
    
    # Show sources for RAG answer (only in grounded mode)
    if is_rag and sources and mode == "grounded":
        st.markdown("---")
        with st.expander(f"📚 Sources ({len(sources)})"):
            for i, source in enumerate(sources, 1):
                metadata = source.get("metadata", {})
                score = source.get("score", 0.0)
                
                # Use file-type-aware formatting
                display_info = format_source_for_display(metadata, score)
                title = display_info["display_title"]
                location = display_info["display_location"]
                file_type = display_info["file_type"]
                
                st.markdown(f"**{i}. {title}** ({location}) - Relevance: {score:.3f}")
                
                snippet = source.get("text", "")[:200]
                if len(source.get("text", "")) > 200:
                    snippet += "..."
                st.markdown(f"> {snippet}")
                
                if i < len(sources):
                    st.divider()
    
    # Show appropriate messages for non-grounded modes
    elif is_rag and mode == "fallback":
        st.markdown("---")
        st.info("📝 **No citations available** - This answer is not based on course documents.")
    elif is_rag and mode == "chitchat":
        # No sources section needed for chitchat (already have banner)
        pass


def main():
    """Main comparison app."""
    init_session_state()
    render_sidebar()
    
    # Header
    st.title("🔬 RAG vs ChatGPT Comparison")
    st.markdown(
        "Compare answers from **plain ChatGPT** (no course context) vs **RAG-powered TA chatbot** (with course PDFs)"
    )
    
    # Check for OpenAI API key
    if not config.openai_api_key:
        st.error("❌ OpenAI API key not configured. Set OPENAI_API_KEY in your .env file.")
        st.stop()
    
    # Question input
    st.divider()
    
    # Check if example was selected
    default_question = st.session_state.get("selected_question", "")
    if default_question:
        # Clear it after using
        st.session_state.selected_question = ""
    
    question = st.text_area(
        "Enter your question:",
        value=default_question,
        height=100,
        placeholder="Ask a question about your course materials..."
    )
    
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        submit_button = st.button("🚀 Compare Answers", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_button:
        st.rerun()
    
    # Generate comparison when button clicked
    if submit_button and question.strip():
        st.divider()
        st.markdown("## 📊 Comparison Results")
        
        # Create two columns for side-by-side comparison
        left_col, right_col = st.columns(2)
        
        # Left: Plain ChatGPT (no RAG)
        with left_col:
            with st.spinner("Asking ChatGPT (no PDFs)..."):
                chatgpt_answer = answer_with_chatgpt_only(question)
            render_answer_panel(
                "💬 ChatGPT (No Course PDFs)",
                chatgpt_answer,
                is_rag=False
            )
        
        # Right: RAG-powered TA
        with right_col:
            with st.spinner("Asking RAG TA Bot (with PDFs)..."):
                rag_result = answer_with_rag(question)
            
            rag_answer = rag_result.get("answer", "No answer generated")
            sources = rag_result.get("sources", [])
            citations = rag_result.get("citations", [])
            mode = rag_result.get("mode", "grounded")
            metadata = rag_result.get("metadata", {})
            
            render_answer_panel(
                "🎓 RAG TA Bot (With Course PDFs)",
                rag_answer,
                is_rag=True,
                sources=sources,
                citations=citations,
                mode=mode,
                metadata=metadata
            )
        
        # Analysis section
        st.divider()
        st.markdown("### 🔍 Key Differences")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "ChatGPT",
                "General Knowledge",
                delta="No citations",
                delta_color="off"
            )
        
        with col2:
            st.metric(
                "RAG TA Bot",
                f"{len(sources)} Sources",
                delta="Grounded in PDFs",
                delta_color="normal"
            )
        
        with col3:
            if sources:
                avg_score = sum(s.get("score", 0) for s in sources) / len(sources)
                st.metric(
                    "Avg Relevance",
                    f"{avg_score:.2f}",
                    delta="Similarity score",
                    delta_color="off"
                )
        
        # Show observations
        with st.expander("💡 What to Look For"):
            st.markdown("""
            **ChatGPT (left) might:**
            - Give generic, general advice
            - Make assumptions about course policies
            - Provide plausible but potentially incorrect details
            - Not mention specific page numbers or sources
            
            **RAG TA Bot (right) should:**
            - Reference specific course PDFs
            - Include citations with page numbers
            - Say "I don't know" if information isn't in the PDFs
            - Provide exact quotes from course materials
            """)
    
    elif submit_button:
        st.warning("⚠️ Please enter a question first.")
    
    # Instructions at bottom
    st.divider()
    st.markdown("""
    ### 📝 How to Use
    
    1. **Enter a question** about your course in the text box above
    2. **Click "Compare Answers"** to see both responses side-by-side
    3. **Observe the differences:**
       - ChatGPT gives general answers without course context
       - RAG TA Bot uses your actual course PDFs with citations
    
    **Tip:** Try the example questions in the sidebar!
    """)


if __name__ == "__main__":
    main()
