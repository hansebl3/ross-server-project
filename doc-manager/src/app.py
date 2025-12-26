import streamlit as st
import subprocess
from db_manager import DBManager
from llm_client import LLMClient
from sentence_transformers import SentenceTransformer
from utils.config_loader import load_config

# Import Tabs
from ui.tab_upload import render_upload_tab
from ui.tab_batch import render_batch_tab
from ui.tab_review import render_review_tab
from ui.tab_search import render_search_tab
from ui.tab_prompt import render_prompt_tab
from ui.tab_settings import render_settings_tab

# Page Config
st.set_page_config(page_title="Documentation Manager", layout="wide")

# Load Config
CONF = load_config()

# --- Shared Resource Initialization (Cached) ---
@st.cache_resource
def get_db():
    return DBManager()

@st.cache_resource
def get_llm():
    return LLMClient()

@st.cache_resource
def get_embedder():
    """
    Initializes and caches the SentenceTransformer model.
    
    CRITICAL CONFIGURATION NOTE:
    The `cache_folder` is explicitly set to "/app/embed".
    This path corresponds to a directory inside the Docker container.
    
    1. Docker Mount: The host machine's `./embed` directory is mounted to `/app/embed`.
       (See `docker-compose.yml` services: doc-manager: volumes)
    2. Shared Storage: This ensures that downloaded models are stored persistently 
       on the host (not inside the container's ephemeral file system) and can be 
       shared across different projects (e.g., RAG) by mounting the same host directory.
    3. User Transparency: Users don't need to configure this path in config.json 
       as it is an internal structural decision for the Docker environment.
    """
    return SentenceTransformer(
        CONF.get("embedding_model", 'paraphrase-multilingual-MiniLM-L12-v2'),
        cache_folder="/app/embed"
    )

# Initialize Session State using Cached Resources
# We re-assign these on every run to ensure that if the class definition changed (e.g. during development),
# the session state gets the latest cached instance.
st.session_state.db = get_db()
st.session_state.llm = get_llm()
st.session_state.embedder = get_embedder()
if "categories" not in st.session_state:
    st.session_state.categories = st.session_state.db.get_categories()

# Sidebar - Settings & Prompt History
st.sidebar.title("Settings")
llm_url = st.sidebar.text_input("LLM Base URL", value=CONF.get("llm_base_url", "http://192.168.1.238:8080/v1"))
st.session_state.llm.base_url = llm_url



# Tabs
tab_upload, tab_process, tab_review, tab_search, tab_prompt, tab_system = st.tabs(["1. Upload", "2. Batch Processing", "3. Review & Save", "4. Search & View", "5. Prompt Lab", "6. System"])

# --- Tab 1: Upload & Check ---
with tab_upload:
    render_upload_tab()

# --- Tab 2: Batch Processing ---
with tab_process:
    render_batch_tab()

# --- Tab 3: Review & Save ---
with tab_review:
    render_review_tab()

# --- Tab 4: Search & View ---
with tab_search:
    render_search_tab()

# --- Tab 5: Prompt Lab ---
with tab_prompt:
    render_prompt_tab()

# --- Tab 6: System Settings ---
with tab_system:
    render_settings_tab()
