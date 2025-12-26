import streamlit as st
import json

def render_prompt_tab():
    st.header("Prompt Lab")
    
    st.info("Design, test, and save prompts for reuse in Batch Processing.")
    
    # 0. Load Available Models
    models = st.session_state.llm.get_available_models()
    
    # 1. Test Configuration
    col_cfg1, col_cfg2 = st.columns([1, 3])
    with col_cfg1:
        test_model = st.selectbox("Test Model", models, key="prompt_test_model")
        
    st.divider()
    
    # 2. Workspace
    c_ws1, c_ws2 = st.columns(2)
    
    with c_ws1:
        st.subheader("Prompt")
        
        # Helper: Load saved prompt
        saved_prompts = st.session_state.db.get_prompts()
        
        with st.expander("📂 Load Saved Prompt", expanded=False):
            if saved_prompts:
                c_l1, c_l2 = st.columns([3, 1])
                with c_l1:
                    sel_p = st.selectbox("Select", saved_prompts, format_func=lambda x: x['alias'], label_visibility="collapsed")
                with c_l2:
                    if st.button("Load"):
                        st.session_state['lab_prompt_input'] = sel_p['prompt_text']
                        st.session_state['lab_save_alias'] = sel_p['alias'] # Pre-fill alias for easy update
                        st.rerun()
            else:
               st.info("No saved prompts yet.")

        # Load from Session State or Empty
        prompt_input = st.text_area("System/User Prompt", height=300, key="lab_prompt_input", placeholder="e.g. Summarize the text below in 3 bullet points.")
        
    with c_ws2:
        st.subheader("Content (Context)")
        content_input = st.text_area("Test Content", height=300, key="lab_content_input", placeholder="Paste document content here to test against...")

    # 3. Action
    if st.button("▶️ Run Test", type="primary", use_container_width=True):
        if not prompt_input or not content_input:
            st.warning("Please provide both Prompt and Content.")
        else:
            with st.spinner("Generating response..."):
                try:
                    # Reuse LLM Client
                    # We treat the input as a "Summary" style prompt where content is appended
                    result = st.session_state.llm.generate_content(content_input, test_model, prompt_input)
                    st.session_state['lab_result'] = result
                except Exception as e:
                    st.error(f"Error: {e}")

    # 4. Result Display
    if 'lab_result' in st.session_state:
        st.subheader("Result")
        st.success("Generation Complete")
        st.markdown(st.session_state['lab_result'])
        st.divider()

    # 5. Save / Manage Prompts
    st.header("Prompt Manager")
    
    c_save1, c_save2 = st.columns([3, 1])
    with c_save1:
        save_alias = st.text_input("Prompt Name (Alias)", placeholder="e.g. 3-Bullet-Summary", key="lab_save_alias")
    with c_save2:
        st.write("") # Spacer
        st.write("")
        if st.button("Save Current Prompt", use_container_width=True):
            if save_alias and prompt_input:
                if st.session_state.db.save_prompt(save_alias, prompt_input):
                    st.success(f"Saved: {save_alias}")
                    st.rerun()
                else:
                    st.error("Failed to save.")
            else:
                st.warning("Need Alias and Prompt text.")

    # 6. Saved Prompts List
    saved_prompts = st.session_state.db.get_prompts()
    if saved_prompts:
        st.subheader("Stored Prompts")
        for p in saved_prompts:
            with st.expander(f"📂 {p['alias']} ({p['created_at']})"):
                st.code(p['prompt_text'])
                c_act1, c_act2 = st.columns([1, 5])
                with c_act1:
                   if st.button("Load", key=f"load_{p['alias']}"):
                       # This requires session state manipulation hack or simple rerun
                       # Streamlit text_area widgets don't update easily from code unless using session state key
                       # We already set key='lab_prompt_input'
                       st.session_state['lab_prompt_input'] = p['prompt_text']
                       st.rerun()
                with c_act2:
                    if st.button("Delete", key=f"del_p_{p['alias']}"):
                        st.session_state.db.delete_prompt(p['alias'])
                        st.rerun()
