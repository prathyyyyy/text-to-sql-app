import os, sys
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from collections import OrderedDict, Counter
from dotenv import load_dotenv
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

load_dotenv()

# ---- your utilities (unchanged) ----
sys.path.append(os.path.abspath('src'))
from src.utils import (
    list_catalog_schema_tables, create_erd_diagram,
    process_llm_response_for_mermaid, quick_analysis,
    create_sql, load_data_from_query, process_llm_response_for_sql,
    get_enriched_database_schema, create_advanced_sql,
    validate_and_correct_sql, add_to_user_history, load_user_query_history
)

# -------------------------------------------------------
# Page
# -------------------------------------------------------
st.set_page_config(
    page_title="SQLGenPro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------
# Global styles (dark, structured, centered hero, glow CTAs)
# includes top padding so Deploy bar never overlaps header
# -------------------------------------------------------
PALETTE_CSS = """
<style>
:root{
  --navy:#2d3250;      /* background */
  --slate:#424769;     /* surfaces */
  --lav:#676f9d;       /* muted text */
  --accent:#f9b17a;    /* CTAs / glow */
  --ink:#ffffff;       /* primary text */
}

/* Push content down so the top bar doesn't overlap */
.block-container{
  padding-top: 3.6rem;
  padding-bottom: 2rem;
}
@media (max-width: 768px){
  .block-container{ padding-top: 4.6rem; }
}

/* Background with subtle radial glows */
.stApp{
  background:
    radial-gradient(1200px 700px at 15% 0%, rgba(103,111,157,.28), transparent 60%),
    radial-gradient(1000px 600px at 90% 10%, rgba(66,71,105,.35), transparent 70%),
    var(--navy);
}

/* Sidebar */
section[data-testid="stSidebar"] > div{
  background: var(--navy);
  border-right: 1px solid rgba(255,255,255,.06);
}
.sidebar-title{
  font-weight: 800; color: var(--ink); font-size: 1.05rem; margin: .25rem 0 .75rem 0;
}

/* Header card (centered) */
.header-card{
  margin-top: .5rem;
  background: rgba(66,71,105,.65);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,.25);
  backdrop-filter: blur(6px);
  text-align: center;
}
.header-title{ font-size: 1.7rem; font-weight: 800; color: var(--ink); margin: 0; }
.header-subtitle{ color: #e9ecff; margin-top: 8px; line-height: 1.5; }

/* Cards */
.card{
  background: rgba(66,71,105,.65);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 2px 18px rgba(0,0,0,.22);
  backdrop-filter: blur(5px);
}
.card h3{ margin: 0 0 6px 0; color: var(--ink); font-size: 1.1rem; font-weight: 800; }
.card p{ color: #dfe3ff; }

/* Inputs (dark) */
label, .stTextInput label, .stSelectbox label, .stMultiSelect label { color: var(--ink) !important; }
div[data-baseweb="base-input"] input,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] textarea{
  background: var(--navy) !important;
  border: 1px solid rgba(255,255,255,.12) !important;
  color: var(--ink) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{ gap: 8px; }
.stTabs [data-baseweb="tab"]{
  background: rgba(66,71,105,.55);
  border: 1px solid rgba(255,255,255,.10);
  border-radius: 12px;
  padding: 10px 14px;
  font-weight: 800;
  color: var(--lav);
}
.stTabs [aria-selected="true"]{
  background: rgba(249,177,122,.25);
  border-color: var(--accent);
  color: var(--ink);
}

/* Glow CTA buttons */
.stButton > button{
  background: var(--accent) !important;
  color: #2d3250 !important;
  border: 1px solid rgba(255,255,255,.25) !important;
  border-radius: 12px !important;
  padding: .6rem 1rem !important;
  font-weight: 900 !important;
  box-shadow: 0 0 0 rgba(249,177,122,0);
  transition: box-shadow .25s ease, transform .06s ease;
}
.stButton > button:hover{
  transform: translateY(-1px);
  box-shadow: 0 0 14px rgba(249,177,122,.75), 0 0 36px rgba(249,177,122,.45);
}
.stButton > button:focus{
  outline: 2px solid rgba(249,177,122,.65);
}

/* Expanders & alerts */
.streamlit-expanderHeader{ font-weight: 800; color: var(--ink); }
.stAlert{ border-radius: 12px; }
</style>
"""
st.markdown(PALETTE_CSS, unsafe_allow_html=True)

# -------------------------------------------------------
# Mermaid renderer with PNG download ONLY (default quality, white background)
# -------------------------------------------------------
def mermaid_png_white(mermaid_code: str, *, height: int = 640, padding: int = 16):
    """
    Render Mermaid ERD with a clean WHITE background and a single 'Download PNG' button.
    Default quality (no high-DPI scaling).
    """
    html = f"""
<div style="margin:10px auto; max-width:1200px;">
  <div id="mmd_wrap" style="
      overflow:auto;
      border:1px solid rgba(0,0,0,.08);
      border-radius:12px;
      padding:{padding}px;
      background:#ffffff;     /* white background for clarity */
  ">
    <div id="mmd" class="mermaid">
{mermaid_code}
    </div>
  </div>

  <div style="display:flex; gap:10px; flex-wrap:wrap; margin:12px 2px 0;">
    <button id="dlPng" class="btn">Download PNG</button>
    <a id="hiddenLink" style="display:none"></a>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
  // Initialize Mermaid with a WHITE diagram background for clarity
  mermaid.initialize({{
    startOnLoad: true,
    theme: "base",
    themeVariables: {{ background: "#ffffff" }}
  }});

  function triggerDownload(filename, url) {{
    const a = document.getElementById('hiddenLink');
    a.href = url; a.download = filename; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1200);
  }}

  function cloneAsStandaloneSvg(svg) {{
    const clone = svg.cloneNode(true);
    const bbox = svg.getBBox();
    clone.setAttribute('viewBox', [bbox.x, bbox.y, bbox.width, bbox.height].join(' '));
    clone.removeAttribute('height');
    clone.removeAttribute('width');
    return clone;
  }}

  document.getElementById('dlPng').onclick = () => {{
    const svg = document.querySelector('#mmd svg');
    if (!svg) return;

    const bbox = svg.getBBox();
    const pad = {padding};
    const SCALE = 1;        // default quality (no upscaling)
    const dpr = 1;          // ignore devicePixelRatio for "default" look

    const clone = cloneAsStandaloneSvg(svg);
    const xml = new XMLSerializer().serializeToString(clone);
    const svg64 = btoa(unescape(encodeURIComponent(xml)));
    const image64 = 'data:image/svg+xml;base64,' + svg64;

    const img = new Image();
    img.onload = function(){{
      const canvas = document.createElement('canvas');
      canvas.width  = Math.ceil((bbox.width  + pad*2) * SCALE);
      canvas.height = Math.ceil((bbox.height + pad*2) * SCALE);
      const ctx = canvas.getContext('2d');
      ctx.imageSmoothingEnabled = true;

      // Solid WHITE background for the exported PNG
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0,0,canvas.width,canvas.height);

      ctx.setTransform(SCALE, 0, 0, SCALE, 0, 0);
      ctx.drawImage(img, pad - bbox.x, pad - bbox.y);
      canvas.toBlob(function(blob){{
        const url = URL.createObjectURL(blob);
        triggerDownload('erd.png', url);
      }}, 'image/png');
    }};
    img.src = image64;
  }};
</script>

<style>
  .btn {{
    background: #f9b17a; color: #2d3250; border: 1px solid rgba(255,255,255,.25);
    border-radius: 12px; padding: 10px 14px; font-weight: 800; cursor: pointer;
    box-shadow: 0 0 0 rgba(249,177,122,0);
    transition: box-shadow .25s ease, transform .06s ease;
  }}
  .btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 0 14px rgba(249,177,122,.75), 0 0 36px rgba(249,177,122,.45);
  }}
</style>
"""
    components.html(html, height=height, scrolling=True)

# -------------------------------------------------------
# Header (centered hero)
# -------------------------------------------------------
st.markdown(
    """
    <div class="header-card">
      <p class="header-title">SQLGenPro 🚀</p>
      <p class="header-subtitle">
        Productivity improvement toolkit for Product Managers, Business stakeholders, and intermediate coders
        working with data in traditional SQL databases — powered by the latest, industry-grade
        <strong>GPT-5 Thinking (ChatGPT-5)</strong> model for advanced reasoning capabilities and accuracy.
      </p>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------------
# Auth
# -------------------------------------------------------
with open("authenticator.yml") as f:
    config = yaml.load(f, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"]
)
authenticator.login(location="main")

name = st.session_state.get("name")
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

# -------------------------------------------------------
# App flow
# -------------------------------------------------------
if authentication_status:
    c1, c2 = st.columns([0.75, 0.25])
    with c1:
        st.markdown(f"#### 👋 Welcome, **{name}**")
        st.caption("You are logged in to SQLGenPro.")
    with c2:
        authenticator.logout("Logout", "main")

    # Sidebar
    st.sidebar.markdown('<div class="sidebar-title">🧭 Navigation</div>', unsafe_allow_html=True)

    # Catalog / Schema / Tables
    try:
        result_tables = list_catalog_schema_tables()
        df_databricks = pd.DataFrame(result_tables).iloc[:, :4]
        df_databricks.columns = ["catalog", "schema", "table", "table_type"]

        catalog_schema_mapping_df = (
            df_databricks.groupby(["catalog"])
            .agg({"schema": lambda x: list(np.unique(x))})
            .reset_index()
        )
        schema_table_mapping_df = (
            df_databricks.groupby(["schema"])
            .agg({"table": lambda x: list(np.unique(x))})
            .reset_index()
        )

        catalog = st.sidebar.selectbox(
            "📁 Select Catalog",
            options=df_databricks["catalog"].unique().tolist(),
            key="sel_catalog"
        )

        schema_candidate_list = catalog_schema_mapping_df[
            catalog_schema_mapping_df["catalog"] == catalog
        ]["schema"].values[0]
        schema_candidate_list = [s for s in schema_candidate_list if s != "dev_tools"]
        schema = st.sidebar.selectbox("📂 Select Schema", options=schema_candidate_list, key="sel_schema")

        table_candidate_list = schema_table_mapping_df[
            schema_table_mapping_df["schema"] == schema
        ]["table"].values[0]

        table_list = st.sidebar.multiselect(
            "🗄️ Select Table(s)",
            options=["All"] + table_candidate_list,
            key="sel_tables"
        )
        if "All" in table_list:
            table_list = table_candidate_list

    except Exception as e:
        st.error(f"Could not load catalog/schema info. Details: {e}")
        st.stop()

    proceed = st.sidebar.checkbox("✅ Proceed", value=False, key="nav_proceed")

    if proceed:
        tabs = st.tabs(["🗺️ ERD Diagram", "⚡ Quick Analysis", "⭐ Favourites", "🔎 Deep Dive"])

        # ---------------- ERD (PNG only, white background) ----------------
        with tabs[0]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 🗺️ Entity Relationship Diagram")
            st.caption("Visualize your selection and download the diagram as a PNG.")

            regen = st.button("Regenerate ERD", key="btn_regen_erd")
            with st.spinner("Generating ERD…"):
                if regen:
                    create_erd_diagram.clear()
                response = create_erd_diagram(catalog, schema, table_list)
                mermaid_code = process_llm_response_for_mermaid(response)

            # Render + PNG download (default quality) on white background
            mermaid_png_white(mermaid_code, height=680, padding=16)

            st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Preload schema for other tabs ----------------
        with st.spinner("Loading table schema…"):
            table_schema = get_enriched_database_schema(catalog, schema, table_list)

        # ---------------- Quick Analysis ----------------
        with tabs[1]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### ⚡ Quick Analysis")
            st.caption("Pick a suggested question to instantly generate validated SQL, and preview sample results.")
            left, right = st.columns([0.28, 0.72])
            with left:
                if st.button("🔄 Need new ideas?", key="btn_qa_ideas"):
                    quick_analysis.clear()
                qa = quick_analysis(table_schema)
                questions = qa['text']['quick_analysis_questions']
                selected_question = st.selectbox("Suggested Questions", options=questions, key="sel_qa_question")
                analyze = st.checkbox("Analyze", key="chk_qa_analyze")
            with right:
                if analyze:
                    with st.spinner("Generating SQL…"):
                        sql_txt = create_sql(selected_question, table_schema)
                        sql_txt = process_llm_response_for_sql(sql_txt)
                        flag, sql_txt = validate_and_correct_sql(selected_question, sql_txt, table_schema)
                        while flag != 'Correct':
                            flag, sql_txt = validate_and_correct_sql(selected_question, sql_txt, table_schema)
                    st.code(sql_txt, language="sql")
                    a, b = st.columns(2)
                    with a:
                        if st.button("🔍 Query Sample Data", key="btn_qa_sample"):
                            try:
                                df = load_data_from_query(sql_txt)
                                st.dataframe(df, use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to run sample query: {e}")
                    with b:
                        if st.button("⭐ Save Query", key="btn_qa_save"):
                            add_to_user_history(name, selected_question, sql_txt, favourite_ind=True)
                            st.success("Added to favourites!")
            st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Favourites ----------------
        with tabs[2]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### ⭐ Your Favourites")
            st.caption("Revisit and run your saved queries.")
            try:
                fav_df = load_user_query_history(user_name=name)
                if fav_df.empty:
                    st.info("No favourites yet. Save your first query from **Quick Analysis** or **Deep Dive**.")
                else:
                    fq = st.selectbox("Saved Questions", options=fav_df['question'].unique().tolist(), key="sel_fav_q")
                    fsql = fav_df[fav_df['question'] == fq]['query'].values[0]
                    st.write(f"##### {fq}")
                    st.code(fsql, language="sql")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.checkbox("🔍 Query Sample Data", key="chk_fav_sample"):
                            try:
                                data = load_data_from_query(fsql)
                                st.dataframe(data, use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to run sample query: {e}")
            except Exception as e:
                st.error(f"Could not load favourites. Details: {e}")
            st.markdown('</div>', unsafe_allow_html=True)

        # ---------------- Deep Dive ----------------
        with tabs[3]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 🔎 Deep-Dive Analysis")
            st.caption("Ask any question for tailored SQL. Validate automatically, preview results, and build iteratively.")
            q1 = st.text_area(
                "Enter your question…", height=100, key="txt_dd_q1",
                placeholder="e.g., Compare weekly revenue growth by region for the last 8 weeks"
            )
            if st.checkbox("Generate SQL", key="chk_dd_generate"):
                with st.spinner("Generating SQL…"):
                    s1 = create_sql(q1, table_schema)
                    s1 = process_llm_response_for_sql(s1)
                    flag, s1 = validate_and_correct_sql(q1, s1, table_schema)
                    while flag != 'Correct':
                        flag, s1 = validate_and_correct_sql(q1, s1, table_schema)
                st.code(s1, language="sql")
                a, b = st.columns(2)
                with a:
                    if st.checkbox("🔍 Query Sample Data", key="chk_dd_sample1"):
                        try:
                            d1 = load_data_from_query(s1)
                            st.dataframe(d1, use_container_width=True)
                        except Exception as e:
                            st.error(f"Failed to run sample query: {e}")
                with b:
                    if st.button("⭐ Save Query", key="btn_dd_save1"):
                        add_to_user_history(name, q1, s1, favourite_ind=True)
                        st.success("Added to favourites!")

                st.divider()
                st.subheader("➕ Build on Top")
                q2 = st.text_area(
                    "How would you like to extend/refine the last result?",
                    height=100, key="txt_dd_q2",
                    placeholder="e.g., Break it down by product category and flag weeks with >10% WoW change"
                )
                if st.checkbox("Generate Advanced SQL", key="chk_dd_generate2"):
                    with st.spinner("Generating advanced SQL…"):
                        s2 = create_advanced_sql(q2, s1, table_schema)
                        s2 = process_llm_response_for_sql(s2)
                        flag, s2 = validate_and_correct_sql(q2, s2, table_schema)
                        while flag != 'Correct':
                            flag, s2 = validate_and_correct_sql(q2, s2, table_schema)
                    st.code(s2, language="sql")
                    x, y = st.columns(2)
                    with x:
                        if st.checkbox("🔍 Query Sample Data (advanced)", key="chk_dd_sample2"):
                            try:
                                d2 = load_data_from_query(s2)
                                st.dataframe(d2, use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to run sample query: {e}")
                    with y:
                        if st.button("⭐ Save Advanced Query", key="btn_dd_save2"):
                            add_to_user_history(name, q2, s2, favourite_ind=True)
                            st.success("Added to favourites!")
            st.markdown('</div>', unsafe_allow_html=True)

else:
    if authentication_status is False:
        st.error("❌ Username/password is incorrect.")
    else:
        st.warning("🔑 Please enter your username and password to continue.")
