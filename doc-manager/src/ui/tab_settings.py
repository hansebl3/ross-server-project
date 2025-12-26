import streamlit as st
import time

def render_settings_tab():
    st.header("System Settings")
    
    st.markdown("### 🛠 Embedding Model Migration")
    st.info(
        """
        **When to use this?**  
        If you change the `embedding_model` in `config.json`, the new model may produce vectors with different dimensions (e.g., 384 vs 768).  
        This tool will:
        1. Alter the database schema to match the new model's dimensions.
        2. Fetch all existing documents.
        3. Re-calculate embeddings using the currently loaded model.
        4. Save the new embeddings back to the database.
        """
    )
    
    # Check current status
    embedder = st.session_state.embedder
    try:
        current_dim = embedder.get_sentence_embedding_dimension()
        model_name = getattr(embedder, 'model_name_or_path', 'Unknown')
    except:
        current_dim = "Unknown"
        model_name = "Unknown"
        
    c1, c2 = st.columns(2)
    c1.metric("Current Model", str(model_name))
    c2.metric("Vector Dimension", str(current_dim))
    
    st.warning("⚠️ **Warning**: This process can take a long time for large datasets. Do not close this tab during migration.")
    
    if st.button("Start Re-indexing / Migration", type="primary"):
        progress_bar = st.progress(0, text="Initializing...")
        status_text = st.empty()
        
        def update_progress(current, total):
            pct = current / total
            progress_bar.progress(pct, text=f"Processing {current}/{total} documents...")

        with st.spinner("Migrating..."):
            success, msg = st.session_state.db.reindex_all_documents(
                embedder=st.session_state.embedder,
                progress_callback=update_progress
            )
            
        if success:
            progress_bar.progress(1.0, text="Completed!")
            st.success(f"✅ {msg}")
        else:
            st.error(f"❌ Migration Failed: {msg}")
