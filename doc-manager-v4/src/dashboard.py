import streamlit as st
import pandas as pd
import os
import sys
from dotenv import load_dotenv

# Ensure we can import modules
sys.path.append(os.path.dirname(__file__))
from database import Database
from l2_builder import L2Builder
from jobs import run_daily_job
from deleter import Deleter

# Load Envs
root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
local_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(root_env_path)
load_dotenv(local_env_path)

st.set_page_config(page_title="Doc Manager V4 Monitor", layout="wide")

@st.cache_resource
def get_db():
    return Database()

db = get_db()
conn = db.get_connection()

# Initialize Deleter with correct root path (Docker mount or local)
# Assuming run from /app (docker) or project root
VAULT_ROOT = os.path.abspath("obsidian_vault_v4")
deleter = Deleter(db, VAULT_ROOT)

st.title("🧠 Doc Manager V4: Monitoring")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Documents (L1)", "Reviews", "L2 Insights", "⚠️ Admin / Data"])

# --- TAB 1: OVERVIEW ---
with tab1:
    st.header("System Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with conn.cursor() as cur:
        # L0 Count
        cur.execute("SELECT COUNT(*) FROM documents")
        l0_count = cur.fetchone()[0]
        
        # L1 Count (Active)
        cur.execute("SELECT COUNT(*) FROM l1_versions WHERE status = 'ACTIVE'")
        l1_count = cur.fetchone()[0]
        
        # L1 Reviews Count
        cur.execute("SELECT COUNT(*) FROM l1_reviews")
        l1_review_limit = cur.fetchone()[0]

        # L2 Reviews Count
        cur.execute("SELECT COUNT(*) FROM l2_reviews")
        l2_review_count = cur.fetchone()[0]
        
        # L2 Count
        cur.execute("SELECT COUNT(*) FROM l2_versions")
        l2_count = cur.fetchone()[0]

    col1.metric("Source Docs (L0)", l0_count)
    col2.metric("Active Summaries (L1)", l1_count)
    col3.metric("Reviews", f"L1: {l1_review_limit} | L2: {l2_review_count}")
    col4.metric("L2 Insights", l2_count)

    st.subheader("Recent Activity")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 'L1 Generated' as type, created_at, source_uuid::text as id FROM l1_versions
            UNION ALL
            SELECT 'L2 Generated' as type, created_at, title as id FROM l2_versions
            UNION ALL
            SELECT 'L1 Review' as type, created_at, rating as id FROM l1_reviews
            UNION ALL
            SELECT 'L2 Review' as type, created_at, rating as id FROM l2_reviews
            ORDER BY created_at DESC LIMIT 10
        """)
        rows = cur.fetchall()
        if rows:
            df_log = pd.DataFrame(rows, columns=["Type", "Time", "Details"])
            st.dataframe(df_log, use_container_width=True)
        else:
            st.info("No activity yet.")

# --- TAB 2: DOCUMENTS ---
with tab2:
    st.header("Documents & Summaries")
    
    # List Docs
    query_docs = """
        SELECT 
            d.uuid, d.path, d.category, d.updated_at,
            l1.version as l1_ver, l1.model_id, l1.content as l1_content
        FROM documents d
        LEFT JOIN l1_versions l1 ON d.uuid = l1.source_uuid AND l1.status = 'ACTIVE'
        ORDER BY d.updated_at DESC
    """
    df_docs = pd.read_sql(query_docs, conn)
    
    if not df_docs.empty:
        selected_path = st.selectbox("Select Document", df_docs['path'])
        
        row = df_docs[df_docs['path'] == selected_path].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Original (L0)")
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM documents WHERE uuid = %s", (row['uuid'],))
                l0_content = cur.fetchone()[0]
            st.text_area("L0 Content", l0_content, height=400)
            
        with c2:
            st.subheader(f"Active L1 Summary (v{row['l1_ver']})")
            if row['l1_content']:
                st.info(f"Model: {row['model_id']}")
                st.markdown(row['l1_content'])
            else:
                st.warning("No Active L1 Summary found.")
    else:
        st.info("No documents found.")

# --- TAB 3: REVIEWS ---
with tab3:
    st.header("Review History")
    
    type_filter = st.radio("Review Type", ["L1 Reviews", "L2 Reviews"], horizontal=True)
    
    if type_filter == "L1 Reviews":
        query_reviews = """
            SELECT 
                r.rating, r.decision, r.notes, r.created_at,
                d.path as document
            FROM l1_reviews r
            JOIN l1_versions v ON r.l1_id = v.l1_id
            JOIN documents d ON v.source_uuid = d.uuid
            ORDER BY r.created_at DESC
        """
        df_reviews = pd.read_sql(query_reviews, conn)
        st.dataframe(df_reviews, use_container_width=True)
        
    else:
        query_l2_reviews = """
            SELECT 
                r.rating, r.decision, r.notes, r.created_at,
                v.title as insight_title
            FROM l2_reviews r
            JOIN l2_versions v ON r.l2_id = v.l2_id
            ORDER BY r.created_at DESC
        """
        df_reviews_l2 = pd.read_sql(query_l2_reviews, conn)
        st.dataframe(df_reviews_l2, use_container_width=True)

# --- TAB 4: L2 INSIGHTS ---
with tab4:
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.header("L2 Clustering Insights")
    with col_h2:
        if st.button("🚀 Run L2 Clustering Job"):
            with st.spinner("Processing..."):
                shadow_dir = os.path.join(VAULT_ROOT, "99_Shadow_Library")
                if not os.path.exists(shadow_dir):
                    os.makedirs(shadow_dir)
                
                builder = L2Builder(db, shadow_dir)
                run_daily_job(db, builder)
                st.success("Job Triggered!")
                st.rerun()

    query_l2 = "SELECT l2_id, title, content, created_at FROM l2_versions ORDER BY created_at DESC"
    df_l2 = pd.read_sql(query_l2, conn)
    
    if not df_l2.empty:
        for idx, row in df_l2.iterrows():
            with st.expander(f"{row['title']} ({row['created_at']})"):
                st.markdown(row['content'])
                
                st.divider()
                st.caption("Sources (L1 Members):")
                # Fetch members
                q_members = """
                    SELECT d.path 
                    FROM l2_members m
                    JOIN l1_versions v ON m.l1_id = v.l1_id
                    JOIN documents d ON v.source_uuid = d.uuid
                    WHERE m.l2_id = %s
                """
                with conn.cursor() as cur:
                    cur.execute(q_members, (row['l2_id'],))
                    members = [r[0] for r in cur.fetchall()]
                
                st.json(members)
    else:
        st.info("No L2 Insights generated yet.")

# --- TAB 5: ADMIN / DATA ---
with tab5:
    st.header("⚠️ Data Management (Hard Delete)")
    st.warning("Deleting data here is PERMANENT. It will delete DB records AND physical files.")
    
    del_type = st.selectbox("Select Data Type to Delete", ["L0 Source Document", "L1 Summary (Only)", "L2 Insight"])
    
    if del_type == "L0 Source Document":
        # Select L0
        q = "SELECT uuid, path FROM documents ORDER BY updated_at DESC"
        df_l0 = pd.read_sql(q, conn)
        if not df_l0.empty:
            sel_l0 = st.selectbox("Select Source Document", df_l0['path'])
            l0_uuid = df_l0[df_l0['path'] == sel_l0].iloc[0]['uuid']
            
            # Preview
            impact = deleter.preview_delete_l0(l0_uuid)
            
            st.error(f"Deleting '{sel_l0}' will REMOVE:")
            st.write(f"- Source Document (L0): {impact['l0']}")
            st.write(f"- Summaries (L1): {impact['l1']}")
            st.write(f"- Insights (L2): {impact['l2']}")
            st.write(f"- Reviews: {impact['reviews']}")
            with st.expander("Affected Files"):
                st.json(impact['files'])
                
            if st.button(f"🗑️ CONFIRM DELETE: {sel_l0}", type="primary"):
                deleter.delete_l0(l0_uuid)
                st.success(f"Deleted {sel_l0} and related data.")
                st.rerun()
        else:
            st.info("No documents.")

    elif del_type == "L1 Summary (Only)":
        # Select L1 (Show ALL versions for cleanup, not just ACTIVE)
        q = """
            SELECT l1.l1_id, d.path, l1.version, l1.status
            FROM l1_versions l1 
            JOIN documents d ON l1.source_uuid = d.uuid 
            ORDER BY d.updated_at DESC, l1.version DESC
        """
        df_l1 = pd.read_sql(q, conn)
        if not df_l1.empty:
            # Display name: path (v1) [SUPERSEDED]
            options = {}
            for i, r in df_l1.iterrows():
                status_tag = f" [{r['status']}]" if r['status'] != 'ACTIVE' else ""
                label = f"{r['path']} (v{r['version']}){status_tag}"
                options[label] = r['l1_id']
                
            sel_label = st.selectbox("Select L1 Summary", list(options.keys()))
            l1_id = options[sel_label]
            
            impact = deleter.preview_delete_l1(l1_id)
            
            st.error(f"Deleting L1 for '{sel_label}' will REMOVE:")
            st.write(f"- Summaries (L1): {impact['l1']}")
            st.write(f"- Insights (L2): {impact['l2']}")
            st.write(f"- Reviews: {impact['reviews']}")
            with st.expander("Affected Files"):
                st.json(impact['files'])
                
            if st.button(f"🗑️ CONFIRM DELETE: {sel_label}", type="primary"):
                deleter.delete_l1(l1_id)
                st.success(f"Deleted L1 {sel_label} and related data.")
                st.rerun()

    elif del_type == "L2 Insight":
        # Select L2
        q = "SELECT l2_id, title FROM l2_versions ORDER BY created_at DESC"
        df_l2 = pd.read_sql(q, conn)
        if not df_l2.empty:
            sel_l2 = st.selectbox("Select L2 Insight", df_l2['title'])
            l2_id = df_l2[df_l2['title'] == sel_l2].iloc[0]['l2_id']
            
            impact = deleter.preview_delete_l2(l2_id)
            
            st.error(f"Deleting L2 '{sel_l2}' will REMOVE:")
            st.write(f"- Insights (L2): {impact['l2']}")
            st.write(f"- Reviews: {impact['reviews']}")
            with st.expander("Affected Files"):
                st.json(impact['files'])
                
            if st.button(f"🗑️ CONFIRM DELETE: {sel_l2}", type="primary"):
                deleter.delete_l2(l2_id)
                st.success(f"Deleted L2 {sel_l2} and related data.")
                st.rerun()
