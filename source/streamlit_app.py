"""Streamlit frontend for Agentic RAG application."""
import streamlit as st
import requests
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"

# Cache TTL constants
HEALTH_CHECK_CACHE_TTL = 30  # seconds
REPO_CACHE_TTL = 60  # seconds

st.set_page_config(
    page_title="Agentic RAG Application",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with high contrast colors
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1565c0;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f77b4;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #0a3622;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #58151c;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        color: #000000;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
        color: #000000;
    }
    .user-message strong {
        color: #0d47a1;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4caf50;
        color: #000000;
    }
    .assistant-message strong {
        color: #1b5e20;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# API Functions with Caching
# ============================================================================

def check_api_health() -> bool:
    """Check if API is healthy with cached result to avoid unnecessary reruns."""
    current_time = time.time()

    # Initialize cache state if not exists
    if "api_health_cache" not in st.session_state:
        st.session_state.api_health_cache = {"is_healthy": None, "last_check": 0}

    cache = st.session_state.api_health_cache

    # Return cached result if still valid
    if current_time - cache["last_check"] < HEALTH_CHECK_CACHE_TTL:
        return cache["is_healthy"]

    # Perform actual health check
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        is_healthy = response.status_code == 200
    except:
        is_healthy = False

    # Update cache
    cache["is_healthy"] = is_healthy
    cache["last_check"] = current_time

    return is_healthy


@st.cache_data(ttl=REPO_CACHE_TTL)
def _list_repositories_cached() -> List[Dict[str, Any]]:
    """Cached version of list repositories (internal use)."""
    try:
        response = requests.get(f"{API_BASE_URL}/repositories")
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def list_repositories() -> List[Dict[str, Any]]:
    """List all repositories."""
    return _list_repositories_cached()


def clear_repositories_cache() -> None:
    """Clear the repositories cache. Call after creating/deleting repositories."""
    _list_repositories_cached.clear()


@st.cache_data(ttl=REPO_CACHE_TTL)
def _list_documents_cached(repository_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Cached version of list documents (internal use)."""
    try:
        params = {}
        if repository_id:
            params["repository_id"] = repository_id

        response = requests.get(f"{API_BASE_URL}/documents", params=params)
        response.raise_for_status()
        return response.json()
    except Exception:
        return []


def list_documents(repository_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List documents."""
    return _list_documents_cached(repository_id)


def clear_documents_cache() -> None:
    """Clear the documents cache. Call after uploading/deleting documents."""
    _list_documents_cached.clear()


def create_repository(name: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Create a new repository."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/repositories",
            json={"name": name, "description": description}
        )
        response.raise_for_status()
        # Clear cache after successful creation
        clear_repositories_cache()
        return response.json()
    except Exception as e:
        st.error(f"Error creating repository: {e}")
        return None


def delete_repository(repository_id: int) -> bool:
    """Delete a repository."""
    try:
        response = requests.delete(f"{API_BASE_URL}/repositories/{repository_id}")
        response.raise_for_status()
        # Clear cache after successful deletion
        clear_repositories_cache()
        return True
    except Exception as e:
        st.error(f"Error deleting repository: {e}")
        return False


def upload_document(file, repository_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Upload a single document."""
    try:
        files = {"file": (file.name, file, file.type)}
        params = {}
        if repository_id:
            params["repository_id"] = repository_id

        response = requests.post(
            f"{API_BASE_URL}/documents",
            files=files,
            params=params
        )
        response.raise_for_status()
        # Clear cache after successful upload
        clear_documents_cache()
        clear_repositories_cache()
        return response.json()
    except Exception as e:
        st.error(f"Error uploading document: {e}")
        return None


def upload_documents_bulk(files: List, repository_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Upload multiple documents at once using bulk upload endpoint.
    """
    try:
        # Prepare files for multipart upload
        files_data = []
        for file in files:
            files_data.append((
                "files",
                (file.name, file, file.type)
            ))

        params = {}
        if repository_id:
            params["repository_id"] = repository_id

        response = requests.post(
            f"{API_BASE_URL}/documents/bulk",
            files=files_data,
            params=params
        )
        response.raise_for_status()
        # Clear cache after successful upload
        clear_documents_cache()
        clear_repositories_cache()
        return response.json()
    except Exception as e:
        st.error(f"Error uploading documents: {e}")
        return None
    """Upload a document."""
    try:
        files = {"file": (file.name, file, file.type)}
        params = {}
        if repository_id:
            params["repository_id"] = repository_id

        response = requests.post(
            f"{API_BASE_URL}/documents",
            files=files,
            params=params
        )
        response.raise_for_status()
        # Clear cache after successful upload
        clear_documents_cache()
        clear_repositories_cache()
        return response.json()
    except Exception as e:
        st.error(f"Error uploading document: {e}")
        return None


def delete_document(document_id: int) -> bool:
    """Delete a document."""
    try:
        response = requests.delete(f"{API_BASE_URL}/documents/{document_id}")
        response.raise_for_status()
        # Clear cache after successful deletion
        clear_documents_cache()
        clear_repositories_cache()
        return True
    except Exception as e:
        st.error(f"Error deleting document: {e}")
        return False


def search_query(
    query: str,
    repository_id: int,
    conversation_id: Optional[str] = None,
    # DISABLED: source: str = "both",  # WEB SEARCH DISABLED
    top_k: int = 5,
    use_conversation_memory: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Perform search query - LLM inference only happens here on user action.
    SIMPLIFIED - No repository filtering, searches ALL documents.
    """
    try:
        payload = {
            "query": query,
            "source": "vector",
            # SIMPLIFIED: No repository filtering - searches all documents
            "repository_id": None,  # Optional, defaults to None (all documents)
            "top_k": top_k,
            "use_conversation_memory": use_conversation_memory
        }

        if conversation_id:
            payload["conversation_id"] = conversation_id

        response = requests.post(f"{API_BASE_URL}/search", json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error performing search: {e}")
        return None

    # ========================================================================
    # ORIGINAL CODE (commented out - web search disabled):
    # ========================================================================
    # def search_query(
    #     query: str,
    #     repository_id: Optional[int] = None,
    #     conversation_id: Optional[str] = None,
    #     source: str = "both",
    #     top_k: int = 5,
    #     use_conversation_memory: bool = True
    # ) -> Optional[Dict[str, Any]]:
    #     """Perform search query - LLM inference only happens here on user action."""
    #     try:
    #         payload = {
    #             "query": query,
    #             "source": source,
    #             "top_k": top_k,
    #             "use_conversation_memory": use_conversation_memory
    #         }
    #         if repository_id:
    #             payload["repository_id"] = repository_id
    #         if conversation_id:
    #             payload["conversation_id"] = conversation_id
    #         response = requests.post(f"{API_BASE_URL}/search", json=payload)
    #         response.raise_for_status()
    #         return response.json()
    #     except Exception as e:
    #         st.error(f"Error performing search: {e}")
    #         return None
    # ========================================================================


# ============================================================================
# UI Components
# ============================================================================

def main():
    """Main Streamlit application."""

    # Initialize session state for conversation
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Header
    st.markdown('<div class="main-header">🤖 Agentic RAG Application</div>', unsafe_allow_html=True)

    # Check API health (cached to avoid repeated calls)
    if not check_api_health():
        st.error("⚠️ API is not responding. Please ensure the FastAPI server is running.")
        st.stop()

    st.success("✅ API is healthy and ready")

    # Sidebar
    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "Select Operation",
            ["🔍 Search & Chat", "📁 Repositories", "📄 Documents"],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("### Settings")

        # SIMPLIFIED: No repository filter - searches all documents
        if page == "🔍 Search & Chat":
            st.info("💡 Searching across all documents in the system")

            top_k = st.slider(
                "Number of Results",
                min_value=1,
                max_value=10,
                value=5,
                help="Number of relevant chunks to retrieve"
            )

            use_memory = st.checkbox(
                "Use Conversation Memory",
                value=True,
                help="Remember conversation context during the chat"
            )

            if st.button("🔄 New Conversation"):
                st.session_state.conversation_id = None
                st.session_state.chat_history = []
                st.rerun()

    # Main content area
    if page == "🔍 Search & Chat":
        render_search_page(top_k, use_memory)
    elif page == "📁 Repositories":
        render_repositories_page()
    elif page == "📄 Documents":
        render_documents_page()


def render_search_page(top_k: int, use_memory: bool):
    """
    Render search and chat interface.
    LLM only called when user submits a query.
    SIMPLIFIED - No repository filtering, searches ALL documents.
    """
    st.markdown('<div class="sub-header">Search & Chat</div>', unsafe_allow_html=True)

    # Display chat history (no API calls here, just rendering)
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-message user-message"><strong>You:</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-message assistant-message"><strong>🕵️‍♂️</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True
            )

            # Show sources if available
            if "sources" in msg and msg["sources"]:
                with st.expander("📚 View Sources"):
                    for i, source in enumerate(msg["sources"][:5], 1):
                        st.markdown(f"**Source {i}** ({source.get('source', 'unknown')})")
                        st.text(source.get('content', '')[:300] + "...")
                        if source.get('url'):
                            st.markdown(f"[Link]({source['url']})")
                        st.markdown("---")

    # Chat input - LLM inference only triggered when user submits here
    query = st.chat_input("Ask a question about your documents...")

    if query:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": query
        })

        # Perform search - THIS IS WHERE LLM INFERENCE HAPPENS
        with st.spinner("🔍 Searching documents and generating answer..."):
            result = search_query(
                query=query,
                repository_id=None,  # SIMPLIFIED: No repository filtering
                conversation_id=st.session_state.conversation_id,
                top_k=top_k,
                use_conversation_memory=use_memory
            )

        if result:
            # Update conversation ID
            st.session_state.conversation_id = result.get("conversation_id")

            # Add assistant response to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result.get("answer", "No answer generated"),
                "sources": result.get("sources", [])
            })

            # Rerun to update display
            st.rerun()

    # ========================================================================
    # ORIGINAL CODE (commented out - web search disabled):
    # ========================================================================
    # def render_search_page(repository_id, search_source, top_k, use_memory):
    #     """Render search and chat interface. LLM only called when user submits a query."""
    #     st.markdown('<div class="sub-header">Search & Chat</div>', unsafe_allow_html=True)
    #
    #     # Display chat history (no API calls here, just rendering)
    #     for msg in st.session_state.chat_history:
    #         if msg["role"] == "user":
    #             st.markdown(
    #                 f'<div class="chat-message user-message"><strong>You:</strong><br>{msg["content"]}</div>',
    #                 unsafe_allow_html=True
    #             )
    #         else:
    #             st.markdown(
    #                 f'<div class="chat-message assistant-message"><strong>Assistant:</strong><br>{msg["content"]}</div>',
    #                 unsafe_allow_html=True
    #             )
    #
    #             # Show sources if available
    #             if "sources" in msg and msg["sources"]:
    #                 with st.expander("📚 View Sources"):
    #                     for i, source in enumerate(msg["sources"][:5], 1):
    #                         st.markdown(f"**Source {i}** ({source.get('source', 'unknown')})")
    #                         st.text(source.get('content', '')[:300] + "...")
    #                         if source.get('url'):
    #                             st.markdown(f"[Link]({source['url']})")
    #                         st.markdown("---")
    #
    #     # Chat input - LLM inference only triggered when user submits here
    #     query = st.chat_input("Ask a question...")
    #
    #     if query:
    #         # Add user message to history
    #         st.session_state.chat_history.append({
    #             "role": "user",
    #             "content": query
    #         })
    #
    #         # Perform search - THIS IS WHERE LLM INFERENCE HAPPENS
    #         with st.spinner("🔍 Searching and generating answer..."):
    #             result = search_query(
    #                 query=query,
    #                 repository_id=repository_id,
    #                 conversation_id=st.session_state.conversation_id,
    #                 source=search_source,
    #                 top_k=top_k,
    #                 use_conversation_memory=use_memory
    #             )
    #
    #         if result:
    #             # Update conversation ID
    #             st.session_state.conversation_id = result.get("conversation_id")
    #
    #             # Add assistant response to history
    #             st.session_state.chat_history.append({
    #                 "role": "assistant",
    #                 "content": result.get("answer", "No answer generated"),
    #                 "sources": result.get("sources", [])
    #             })
    #
    #             # Rerun to update display
    #             st.rerun()
    # ========================================================================


def render_repositories_page():
    """Render repositories management page."""
    st.markdown('<div class="sub-header">Repositories</div>', unsafe_allow_html=True)

    # Create new repository
    with st.expander("➕ Create New Repository", expanded=False):
        with st.form("create_repo_form"):
            repo_name = st.text_input("Repository Name", max_chars=255)
            repo_desc = st.text_area("Description (optional)", max_chars=1000)

            if st.form_submit_button("Create"):
                if repo_name:
                    repo = create_repository(repo_name, repo_desc)
                    if repo:
                        st.success(f"✅ Repository '{repo_name}' created successfully!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Repository name is required")

    # List repositories (uses cached data)
    st.markdown("### Existing Repositories")
    repos = list_repositories()

    if not repos:
        st.info("No repositories found. Create one to get started!")
    else:
        for repo in repos:
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{repo['name']}**")
                if repo.get('description'):
                    st.text(repo['description'][:100])
                st.caption(f"Documents: {repo.get('document_count', 0)} | Created: {repo['created_at'][:10]}")

            with col2:
                st.metric("ID", repo['id'])

            with col3:
                if st.button("🗑️ Delete", key=f"del_repo_{repo['id']}"):
                    if st.session_state.get(f"confirm_del_repo_{repo['id']}", False):
                        if delete_repository(repo['id']):
                            st.success("Repository deleted")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.session_state[f"confirm_del_repo_{repo['id']}"] = True
                        st.warning("Click again to confirm")

            st.markdown("---")


def render_documents_page():
    """Render documents management page - SIMPLIFIED without repositories."""
    st.markdown('<div class="sub-header">Documents</div>', unsafe_allow_html=True)

    # Upload documents (single or multiple)
    with st.expander("📤 Upload Documents", expanded=True):
        st.info("💡 Documents will be processed with Ali Cloud embeddings and added to the global search")

        # Accept multiple files at once
        uploaded_files = st.file_uploader(
            "Choose one or more files",
            type=['pdf', 'txt', 'md', 'docx', 'html'],
            help="Supported formats: PDF, TXT, MD, DOCX, HTML",
            accept_multiple_files=True
        )

        if uploaded_files and st.button("Upload All Documents"):
            if len(uploaded_files) == 1:
                # Single file upload
                with st.spinner(f"📤 Uploading '{uploaded_files[0].name}'..."):
                    doc = upload_document(uploaded_files[0], None)  # No repository

                if doc:
                    st.success(f"✅ Document '{uploaded_files[0].name}' uploaded successfully!")
                    time.sleep(1)
                    st.rerun()
            else:
                # Multiple files - use bulk upload endpoint
                with st.spinner(f"📤 Uploading {len(uploaded_files)} documents..."):
                    result = upload_documents_bulk(uploaded_files, None)  # No repository

                if result:
                    # Show upload summary
                    st.markdown("### Upload Summary")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Files", result.get("total_files", 0))
                    col2.metric("Successful", result.get("successful", 0), delta_color="normal")
                    col3.metric("Failed", result.get("failed", 0), delta_color="inverse")

                    # Show detailed results
                    with st.expander("📋 View Detailed Results", expanded=True):
                        for item in result.get("results", []):
                            if item.get("status") == "success":
                                st.success(f"✅ **{item['name']}** - Document ID: {item.get('document_id')}")
                            else:
                                st.error(f"❌ **{item['name']}** - Error: {item.get('error', 'Unknown error')}")

                    if result.get("failed", 0) == 0:
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

    # List ALL documents (no filtering)
    st.markdown("### Document List")
    docs = list_documents(None)  # None = all documents

    if not docs:
        st.info("No documents found. Upload one to get started!")
    else:
        st.info(f"📊 Total: {len(docs)} documents")
        for doc in docs:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{doc['name']}**")
                st.caption(f"Format: {doc['format']} | Chunks: {doc.get('chunk_count', 0)}")

            with col2:
                status = doc['status']
                color = {
                    'completed': '🟢',
                    'processing': '🟡',
                    'pending': '⚪',
                    'failed': '🔴'
                }.get(status, '⚪')
                st.markdown(f"{color} {status}")

            with col3:
                st.metric("ID", doc['id'])

            with col4:
                if st.button("🗑️", key=f"del_doc_{doc['id']}"):
                    if st.session_state.get(f"confirm_del_doc_{doc['id']}", False):
                        if delete_document(doc['id']):
                            st.success("Document deleted")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.session_state[f"confirm_del_doc_{doc['id']}"] = True
                        st.warning("Click again to confirm")

            st.markdown("---")


if __name__ == "__main__":
    main()
