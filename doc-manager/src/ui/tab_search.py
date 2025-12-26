import streamlit as st
import pandas as pd
import json

def render_search_tab():
    st.header("Search Knowledge Base")
    col_s1, col_s2, col_s3, col_s4 = st.columns([2, 1, 1, 1])
    with col_s1:
        search_query = st.text_input("Text Search")
    with col_s2:
        search_cat = st.selectbox("Category Filter", ["ALL"] + st.session_state.categories)
    with col_s3:
        search_lvl = st.selectbox("Level Filter", ["ALL", "L0", "L1", "L2", "L3"])
    with col_s4:
        search_uuid = st.text_input("UUID Search")
    
    st.divider()
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        filter_no_task = st.checkbox("Show only documents WITHOUT an active task")
    with col_opt2:
        auto_expand_parent = st.checkbox("Automatically show parent content for summaries", value=True)
    
    cat_filter = None if search_cat == "ALL" else search_cat
    lvl_filter = None if search_lvl == "ALL" else search_lvl
    uuid_filter = search_uuid if search_uuid else None
    
    results = st.session_state.db.search_documents(query_text=search_query, category=cat_filter, level=lvl_filter, doc_id=uuid_filter)
    
    if results:
        # --- Performance Optimization: Pre-fetch all related data ---
        # 1. Get all tasks for task status check
        all_tasks = st.session_state.db.get_all_tasks()
        
        # 2. Collect all parent and child IDs for batch fetch
        doc_ids_to_fetch = set()
        for r in results:
            if r.get('summary_uuids'):
                doc_ids_to_fetch.update([str(s) for s in r['summary_uuids']])
            if r['level'] in ['L1', 'L2', 'L3']:
                # Collect parent IDs for pre-fetching
                parent_uuids = r.get('source_uuids') or []
                if not parent_uuids:
                    m_p_id = r['metadata'].get('parent_id') or r.get('metadata', {}).get('original_meta', {}).get('parent_id')
                    if m_p_id:
                        parent_uuids = [m_p_id]
                doc_ids_to_fetch.update([str(p) for p in parent_uuids])
        
        # 3. Batch fetch all related documents
        related_docs = st.session_state.db.get_documents_by_ids(list(doc_ids_to_fetch)) if doc_ids_to_fetch else {}

        if filter_no_task:
            results = [r for r in results if str(r['id']) not in all_tasks]

    if results:
        df = pd.DataFrame(results)
        display_df = df.drop(columns=['embedding']) if 'embedding' in df.columns else df
        st.dataframe(display_df, use_container_width=True)
        
        for idx, row in df.iterrows():
            doc_id_str = str(row['id'])
            is_summary = row['level'] in ['L1', 'L2', 'L3']
            
            # Use columns for indentation
            if is_summary:
                _, container = st.columns([1, 15])
            else:
                container = st.container()
            
            with container:
                display_name = row['title'] if row['title'] else doc_id_str
                with st.expander(f"[{row['category']} / {row['level']}] {display_name}"):
                    c_info, c_down = st.columns([4, 1])
                    with c_down:
                        st.download_button("Download MD", data=row['content'], file_name=f"{display_name}.md", mime="text/markdown", key=f"dl_{doc_id_str}")
                    
                    with c_info:
                        st.write(f"**Title:** {row['title']}")
                        st.write(f"**Metadata:** {json.dumps(row['metadata'], ensure_ascii=False)}")
                        st.write(f"**Content Snippet:** {row['content'][:500]}...")
                    
                    # Task Status (Using pre-fetched tasks)
                    task = all_tasks.get(doc_id_str)
                    if task:
                        st.info(f"**Task Status:** `{task['status']}`")
                    else:
                        st.warning("No Active Task in Queue")
                        if st.button("Add to Process Queue", key=f"re_q_{doc_id_str}"):
                            fname = row['metadata'].get('filename') or doc_id_str
                            st.session_state.db.enqueue_task(row['id'], config={"filename": fname})
                            st.success(f"Added to processing queue!")
                            st.rerun()

                    # Edit (Simplified for L0)
                    if row['category'] == 'L0':
                        with st.expander("Edit Content"):
                            new_content = st.text_area("Update Content", value=row['content'], height=200, key=f"edit_{doc_id_str}")
                            if st.button("Save & Reset Summaries", key=f"save_{doc_id_str}"):
                                new_emb = st.session_state.embedder.encode(new_content).tolist()
                                st.session_state.db.upsert_document(row['id'], row['category'], row['level'], row['metadata'], new_content, new_emb)
                                for sum_id in (row.get('summary_uuids') or []):
                                    st.session_state.db.delete_document(sum_id)
                                st.session_state.db.clear_summary_links(row['id'])
                                st.rerun()

                    if is_summary:
                        parent_uuids = row.get('source_uuids') or []
                        if not parent_uuids:
                            m_p_id = row['metadata'].get('parent_id') or row.get('metadata', {}).get('original_meta', {}).get('parent_id')
                            if m_p_id: parent_uuids = [m_p_id]
                        
                        for p_uuid in parent_uuids:
                            parent = related_docs.get(str(p_uuid))
                            if parent:
                                if auto_expand_parent:
                                    st.info(f"**Parent Context:**\n\n{parent['content']}")
                                elif st.button(f"Show Parent ({str(p_uuid)[:8]})", key=f"btn_{doc_id_str}_{p_uuid}"):
                                    st.info(f"**Parent Content:**\n{parent['content']}")
                    
                    if row.get('summary_uuids'):
                        st.write("**Related Summaries (L1):**")
                        for s_id in row['summary_uuids']:
                            s_doc = related_docs.get(str(s_id))
                            if s_doc: st.write(s_doc['content'])
                    
                    st.divider()
                    
                    # Delete
                    # Delete
                    del_key = f"confirm_del_{doc_id_str}"
                    if st.session_state.get(del_key, False):
                        # Fetch impact analysis
                        impacts = st.session_state.db.get_impact_analysis(row['id'])
                        
                        if impacts:
                            st.error(f"⚠️ WARNING: This document has {len(impacts)} dependent document(s)!")
                            st.write("Deleting this will **ALSO PERMANENTLY DELETE** the following:")
                            for imp in impacts:
                                st.write(f"- [{imp['level']}] {imp['title']} ({imp['category']})")
                            st.divider()

                        if st.button("🔴 Confirm DELETE", key=f"yes_{doc_id_str}", type="primary"):
                            st.session_state.db.delete_document(row['id'])
                            st.session_state[del_key] = False
                            st.rerun()
                        if st.button("Cancel", key=f"no_{doc_id_str}"):
                            st.session_state[del_key] = False
                            st.rerun()
                    else:
                        if st.button("Delete Document", key=f"req_del_{doc_id_str}"):
                            st.session_state[del_key] = True
                            st.rerun()
    else:
        st.info("No documents found.")
