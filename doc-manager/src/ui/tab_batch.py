import streamlit as st
import os
import json

def render_batch_tab():
    st.header("Batch LLM Processing")
    
    # --- 0. Queue Dashboard (Top) ---
    c_dash1, c_dash2 = st.columns([3, 1])
    with c_dash1:
         st.subheader("Queue Dashboard")
    with c_dash2:
        if st.button("Refresh Status", key="refresh_top"):
            st.rerun()

    # Fetch all relevant statuses
    tasks_created = st.session_state.db.get_tasks_by_status('created')
    tasks_queued = st.session_state.db.get_tasks_by_status('queued')
    tasks_active = st.session_state.db.get_tasks_by_status('processing')

    # Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("1. Pending Config", len(tasks_created), help="Files uploaded but not yet configured for LLM.")
    m2.metric("2. Waiting in Queue", len(tasks_queued), help="Files queued and waiting for the background worker.")
    m3.metric("3. Processing Now", len(tasks_active), help="Files currently being processed by LLM.")

    st.divider()
    
    # Detailed Lists (Expanders)
    if tasks_created or tasks_queued or tasks_active:
        with st.expander("📂 Show Detailed Queue Lists", expanded=True):
            cols_list = st.columns(3)
            
            with cols_list[0]:
                st.markdown("**Pending Config**")
                if tasks_created:
                    for t in tasks_created:
                        fname = t['config'].get('filename', str(t['doc_id']))
                        st.caption(f"- {fname}")
                else:
                    st.caption("(Empty)")

            with cols_list[1]:
                st.markdown("**Waiting in Queue**")
                if tasks_queued:
                    for t in tasks_queued:
                        fname = t['config'].get('filename', str(t['doc_id']))
                        st.caption(f"- {fname}")
                else:
                    st.caption("(Empty)")
                    
            with cols_list[2]:
                st.markdown("**Processing**")
                if tasks_active:
                    for t in tasks_active:
                        fname = t['config'].get('filename', str(t['doc_id']))
                        st.text(f"▶ {fname}")
                else:
                    st.caption("(Idle)")
    
    st.divider()

    # --- 1. Configuration Section ---
    st.subheader("Batch Configuration")
    
    tasks_to_config = tasks_created # Alias for compatibility with logic below
    
    if not tasks_to_config:
        st.info("No new tasks to configure. Upload more files to add to the 'Pending Config' list.")
    else:
        st.write(f"Configuring **{len(tasks_to_config)}** pending files...")
        
        # Helper to load/save prefs
        PREFS_FILE = "user_prefs.json"
        def load_prefs():
            if os.path.exists(PREFS_FILE):
                try:
                     with open(PREFS_FILE, 'r') as f: return json.load(f)
                except: return {}
            return {}
        
        def save_prefs(key, value):
            p = load_prefs()
            p[key] = value
            with open(PREFS_FILE, 'w') as f: json.dump(p, f)
        
        prefs = load_prefs()

        col_sets, col_ctrl = st.columns([2, 1])
        
        with col_sets:
            # Fetch Saved Prompts
            saved_prompts_list = st.session_state.db.get_prompts()
            
            # Define System Defaults
            default_sum_obj = {
                "alias": "System Default: Concise Summary", 
                "prompt_text": "Summarize the following document concisely."
            }
            # Updated default to align with no-date logic
            default_meta_obj = {
                "alias": "System Default: Keywords & Title", 
                "prompt_text": "Extract key technical keywords and a short descriptive title (around 20 characters)."
            }
            
            # Build Options
            # We allow utilizing any prompt for any purpose, but defaults are top of list
            all_options = [default_sum_obj, default_meta_obj] + (saved_prompts_list if saved_prompts_list else [])
            
            # Deduplicate by alias just in case
            # (DB enforces PK on alias, so only defaults conflict if user named them same)
            
            # --- Summary Prompt Selection ---
            # Try to find index of last used alias
            last_sum_alias = prefs.get("summary_alias", default_sum_obj["alias"])
            try:
                # Find index
                sum_idx = next(i for i, v in enumerate(all_options) if v["alias"] == last_sum_alias)
            except StopIteration:
                sum_idx = 0
                
            selected_sum = st.selectbox("Summary Prompt", all_options, format_func=lambda x: x['alias'], index=sum_idx, key="sel_sum_prompt")
            
            # --- Metadata Prompt Selection ---
            last_meta_alias = prefs.get("meta_alias", default_meta_obj["alias"])
            try:
                meta_idx = next(i for i, v in enumerate(all_options) if v["alias"] == last_meta_alias)
            except StopIteration:
                meta_idx = 1 # Default to the meta obj (index 1)
                
            selected_meta = st.selectbox("Metadata Prompt", all_options, format_func=lambda x: x['alias'], index=meta_idx, key="sel_meta_prompt")

            # Save preferences (Alias only)
            if selected_sum["alias"] != prefs.get("summary_alias"): save_prefs("summary_alias", selected_sum["alias"])
            if selected_meta["alias"] != prefs.get("meta_alias"): save_prefs("meta_alias", selected_meta["alias"])

            # Preview
            with st.expander("Show Prompt Preview"):
                st.caption("**Selected Summary Prompt:**")
                st.info(selected_sum['prompt_text'])
                st.caption("**Selected Metadata Prompt:**")
                st.info(selected_meta['prompt_text'])

            # Set the variables for execution use
            prompt_summary = selected_sum['prompt_text']
            prompt_meta = selected_meta['prompt_text']

        with col_ctrl:
            models = st.session_state.llm.get_available_models()
            
            # Determine default indices based on prefs
            def get_index(model_list, pref_key, default_idx):
                if pref_key in prefs and prefs[pref_key] in model_list:
                    return model_list.index(prefs[pref_key])
                return default_idx

            idx_l = get_index(models, "model_l", 0)
            idx_r = get_index(models, "model_r", min(1, len(models)-1))

            model_l = st.selectbox("Left Model", models, index=idx_l, key="batch_model_l")
            model_r = st.selectbox("Right Model", models, index=idx_r, key="batch_model_r")
            
            # Save on change
            if model_l != prefs.get("model_l"): save_prefs("model_l", model_l)
            if model_r != prefs.get("model_r"): save_prefs("model_r", model_r)
            
            if st.button("Start Batch Execution", type="primary"):
                
                # Update all 'created' tasks to 'queued' with config
                count = 0
                for task in tasks_to_config:
                    new_config = task['config'] or {}
                    new_config.update({
                        "model_l": model_l,
                        "model_r": model_r,
                        "prompt_summary": prompt_summary,
                        "prompt_meta": prompt_meta
                    })
                    st.session_state.db.update_task(task['doc_id'], status='queued', config=new_config)
                    count += 1
                
                st.success(f"Queued {count} tasks! The background worker will pick them up.")
                st.rerun()
