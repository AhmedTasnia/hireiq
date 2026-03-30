"""
HireIQ — AI-Powered CV Screening System
Phase 1: CV Scoring & Ranking
Run with: streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime
from io import BytesIO

from modules.pdf_converter import pdf_to_text
from modules.circular_parser import parse_circular
from modules.cv_extractor import extract_cv_info
from modules.scorer import score_cv, rank_candidates, DEFAULT_WEIGHTS
from database.models import init_db, get_session, Session_DB, Candidate

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HireIQ — CV Screening",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-title {
        font-size: 2rem; font-weight: 700; color: #1a1a2e;
        border-bottom: 3px solid #4f46e5; padding-bottom: 0.5rem; margin-bottom: 1rem;
    }
    .rank-card {
        border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px 16px;
        margin-bottom: 10px; background: white;
    }
    .rank-num {
        display: inline-flex; align-items: center; justify-content: center;
        background: #4f46e5; color: white; border-radius: 50%;
        width: 34px; height: 34px; font-weight: 700; font-size: 14px;
        flex-shrink: 0;
    }
    .score-pill { font-weight: 700; font-size: 22px; }
    .bar-bg { background: #e5e7eb; border-radius: 99px; height: 8px; }
    .bar-fill { height: 8px; border-radius: 99px; }
    .tag { display: inline-block; border-radius: 6px; padding: 1px 9px;
           font-size: 12px; margin: 2px; }
    .tag-req   { background:#ede9fe; color:#4338ca; }
    .tag-match { background:#dcfce7; color:#166534; }
    .tag-miss  { background:#fee2e2; color:#991b1b; }
</style>
""", unsafe_allow_html=True)

# ── init DB & session state ───────────────────────────────────────────────────
init_db()

def ss(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

ss("criteria", None)
ss("ranked", [])
ss("weights", DEFAULT_WEIGHTS.copy())
ss("selected_idx", 0)
ss("circular_text", "")
ss("cv_store", {})   # fname -> bytes, cached immediately on upload


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🎯 HireIQ")
    st.caption("AI CV Screening · Phase 1")
    st.divider()

    st.markdown("### ⚖️ Scoring Weights")
    st.caption("Controls how much each criterion matters (scaled to 100 automatically)")

    edu_w = st.slider("🎓 Education",   5, 50, st.session_state.weights["education"],  5)
    exp_w = st.slider("💼 Experience",  5, 50, st.session_state.weights["experience"], 5)
    sk_w  = st.slider("🛠️ Skills",      5, 40, st.session_state.weights["skills"],     5)
    age_w = st.slider("🎂 Age",         0, 30, st.session_state.weights["age"],        5)
    gen_w = st.slider("👤 Gender",      0, 20, st.session_state.weights["gender"],     5)

    total_w = edu_w + exp_w + sk_w + age_w + gen_w
    if total_w != 100:
        st.warning(f"Sum = {total_w} — will auto-scale to 100")
    else:
        st.success("✅ Weights sum to 100")

    st.session_state.weights = {
        "education": edu_w, "experience": exp_w,
        "skills": sk_w, "age": age_w, "gender": gen_w,
    }

    st.divider()
    if st.session_state.ranked:
        scores = [c["score"]["total"] for c in st.session_state.ranked]
        st.markdown("### 📊 Session Stats")
        st.metric("Candidates screened", len(scores))
        st.metric("Top score", f"{max(scores):.1f} / 100")
        st.metric("Average score", f"{sum(scores)/len(scores):.1f} / 100")

    st.divider()
    if st.button("🔄 Reset everything", use_container_width=True):
        st.session_state.criteria = None
        st.session_state.ranked = []
        st.session_state.selected_idx = 0
        st.session_state.circular_text = ""
        st.session_state.cv_store = {}
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">🎯 HireIQ — CV Screening System</div>', unsafe_allow_html=True)

ranked_count = len(st.session_state.ranked)
tab_upload, tab_results, tab_detail = st.tabs([
    "📋 Upload & Screen",
    f"🏆 Ranked Results ({ranked_count})" if ranked_count else "🏆 Ranked Results",
    "🔍 Candidate Detail",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — UPLOAD & SCREEN
# ══════════════════════════════════════════════════════════════════════════════
with tab_upload:

    # ── STEP 1: Circular ─────────────────────────────────────────────────────
    st.markdown("### Step 1 — Load Job Circular")

    use_sample = st.toggle("Use built-in sample circular (quick test)", value=False)

    if use_sample:
        sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "job_circular.txt")
        with open(sample_path, "r", encoding="utf-8") as f:
            st.session_state.circular_text = f.read()
        st.success("✅ Sample circular loaded")
    else:
        circ_file = st.file_uploader("Upload job circular (.txt)", type=["txt"], key="circ_up")
        if circ_file is not None:
            # Read & cache immediately — avoids stale pointer on rerun
            content = circ_file.read()
            st.session_state.circular_text = content.decode("utf-8", errors="ignore")
            st.success(f"✅ Loaded: {circ_file.name} ({len(st.session_state.circular_text)} chars)")

    if st.session_state.circular_text:
        with st.expander("👁️ Preview circular text"):
            st.text(st.session_state.circular_text[:1200])

    if st.session_state.circular_text:
        if st.button("🔍 Extract Job Criteria", type="primary"):
            with st.spinner("Parsing…"):
                st.session_state.criteria = parse_circular(st.session_state.circular_text)
            st.success("✅ Criteria extracted!")

    if st.session_state.criteria:
        c = st.session_state.criteria
        st.markdown("#### 📌 Extracted Criteria")
        cols = st.columns(3)
        with cols[0]:
            st.markdown(f"**Job Title:** {c.get('job_title','—')}")
            st.markdown(f"**Gender pref:** {c.get('gender','Not stated') or 'Not stated'}")
        with cols[1]:
            age = c.get("age", {})
            age_str = "Not stated"
            if age.get("max") and age.get("min"):
                age_str = f"{age['min']}–{age['max']} yrs"
            elif age.get("max"):
                age_str = f"Under {age['max']} yrs"
            elif age.get("min"):
                age_str = f"Over {age['min']} yrs"
            exp = c.get("experience", {})
            exp_str = f"Min {exp.get('min', 0)} yr(s)" if exp.get("min") else "Not stated"
            st.markdown(f"**Age:** {age_str}")
            st.markdown(f"**Experience:** {exp_str}")
        with cols[2]:
            edu = c.get("education", {})
            edu_str = (edu.get("level") or "—") + (f" in {edu['field']}" if edu.get("field") else "")
            skills = c.get("skills", [])
            st.markdown(f"**Education:** {edu_str}")
            st.markdown(f"**Skills ({len(skills)}):** {', '.join(skills[:6]) or '—'}")

    st.divider()

    # ── STEP 2: CVs ──────────────────────────────────────────────────────────
    st.markdown("### Step 2 — Upload CVs (PDF)")

    cv_files = st.file_uploader(
        "Upload one or more CV PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        key="cv_up",
    )

    # Cache bytes immediately when files land
    if cv_files:
        for f in cv_files:
            raw = f.read()
            if raw:  # only store if non-empty
                st.session_state.cv_store[f.name] = raw

    if st.session_state.cv_store:
        st.info(f"📂 {len(st.session_state.cv_store)} CV(s) ready: {', '.join(st.session_state.cv_store.keys())}")

    st.divider()

    # ── STEP 3: Screen ───────────────────────────────────────────────────────
    st.markdown("### Step 3 — Run Screening")

    ready = bool(st.session_state.criteria and st.session_state.cv_store)
    if not st.session_state.criteria:
        st.warning("↑ Complete Step 1 first (extract job criteria)")
    if not st.session_state.cv_store:
        st.warning("↑ Upload at least one PDF in Step 2")
    if ready:
        st.success(f"Ready: {len(st.session_state.cv_store)} CV(s) vs **{st.session_state.criteria.get('job_title','job')}**")

    if st.button("🚀 Screen All CVs Now", type="primary", disabled=not ready, use_container_width=True):

        # Scale weights if needed
        weights = st.session_state.weights.copy()
        total_w = sum(weights.values())
        if total_w != 100 and total_w > 0:
            factor = 100 / total_w
            weights = {k: round(v * factor, 2) for k, v in weights.items()}

        criteria = st.session_state.criteria
        candidates = []
        errors = []

        pbar = st.progress(0)
        status_txt = st.empty()

        cv_items = list(st.session_state.cv_store.items())

        for i, (fname, pdf_bytes) in enumerate(cv_items):
            status_txt.markdown(f"⚙️ Processing **{fname}** ({i+1}/{len(cv_items)})…")
            pbar.progress(i / len(cv_items))

            try:
                cv_text = pdf_to_text(pdf_bytes)

                if not cv_text or len(cv_text.strip()) < 20:
                    errors.append(
                        f"⚠️ **{fname}**: Very little text extracted "
                        f"(got {len(cv_text.strip())} chars). "
                        "PDF may be a scanned image — use a text-based PDF."
                    )
                    cv_info = extract_cv_info("")
                else:
                    cv_info = extract_cv_info(cv_text)

                score_result = score_cv(criteria, cv_info, weights)

                candidates.append({
                    "filename": fname,
                    "cv_text": cv_text,
                    "cv_info": cv_info,
                    "score": score_result,
                    "rank": 0,
                    "status": "pending",
                })

            except Exception as e:
                errors.append(f"❌ **{fname}**: {e}")

        pbar.progress(1.0)
        status_txt.markdown("🏁 Ranking…")

        if candidates:
            ranked = rank_candidates(candidates)
            st.session_state.ranked = ranked

            try:
                db = get_session()
                sess = Session_DB(
                    job_title=criteria.get("job_title", ""),
                    circular_text=criteria.get("raw_text", ""),
                    extracted_criteria=json.dumps(
                        {k: v for k, v in criteria.items() if k != "raw_text"}
                    ),
                    created_at=datetime.utcnow(),
                )
                db.add(sess)
                db.flush()
                for cand in ranked:
                    db.add(Candidate(
                        session_id=sess.id,
                        name=cand["cv_info"].get("name", ""),
                        email=cand["cv_info"].get("email", ""),
                        phone=cand["cv_info"].get("phone", ""),
                        cv_path=cand["filename"],
                        cv_text=cand["cv_text"],
                        total_score=cand["score"]["total"],
                        score_breakdown=json.dumps(cand["score"]["breakdown"]),
                        rank=cand["rank"],
                        status="pending",
                    ))
                db.commit()
                db.close()
            except Exception as db_err:
                st.warning(f"DB save skipped: {db_err}")

        pbar.empty()
        status_txt.empty()

        for e in errors:
            st.warning(e)

        if candidates:
            st.success(f"✅ Done! {len(candidates)} candidate(s) ranked. Go to the **🏆 Ranked Results** tab.")
            st.balloons()
        else:
            st.error("No candidates could be processed. Are the PDFs text-based (not scanned images)?")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — RANKED RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_results:
    if not st.session_state.ranked:
        st.info("Run the screening in the Upload & Screen tab — results will appear here.")
    else:
        ranked = st.session_state.ranked
        scores = [c["score"]["total"] for c in ranked]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Candidates", len(ranked))
        m2.metric("Top Score", f"{max(scores):.1f} / 100")
        m3.metric("Average", f"{sum(scores)/len(scores):.1f} / 100")
        m4.metric("Strong matches (≥75)", sum(1 for s in scores if s >= 75))

        st.divider()

        col_list, col_chart = st.columns([1.1, 1], gap="large")

        with col_list:
            st.markdown("### 🏆 Ranked Candidates")

            for c in ranked:
                score = c["score"]["total"]
                info = c["cv_info"]
                rank = c["rank"]
                bd = c["score"]["breakdown"]

                if score >= 75:
                    bar_color = "#22c55e"; left_border = "#22c55e"
                elif score >= 50:
                    bar_color = "#f59e0b"; left_border = "#f59e0b"
                else:
                    bar_color = "#ef4444"; left_border = "#ef4444"

                st.markdown(f"""
                <div class="rank-card" style="border-left: 5px solid {left_border};">
                  <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                    <div class="rank-num">#{rank}</div>
                    <div style="flex:1; min-width:0;">
                      <div style="font-weight:700; font-size:15px;">{info.get('name','Unknown')}</div>
                      <div style="font-size:11px; color:#6b7280;">{c['filename']}</div>
                    </div>
                    <div style="text-align:right; flex-shrink:0;">
                      <span class="score-pill" style="color:{bar_color};">{score:.1f}</span>
                      <span style="font-size:13px; color:#9ca3af;">/100</span>
                    </div>
                  </div>
                  <div class="bar-bg" style="margin-bottom:8px;">
                    <div class="bar-fill" style="width:{min(score,100):.1f}%; background:{bar_color};"></div>
                  </div>
                  <div style="display:flex; gap:16px; font-size:12px; color:#6b7280; flex-wrap:wrap; margin-bottom:6px;">
                    <span>🎓 {info.get('education',{}).get('level') or '—'}</span>
                    <span>💼 {info.get('experience_years',0)} yrs</span>
                    <span>🎂 {info.get('age') or '—'}</span>
                    <span>👤 {(info.get('gender') or '—').title()}</span>
                    <span>📧 {info.get('email') or '—'}</span>
                  </div>
                  <div style="font-size:11px; color:#374151; display:flex; gap:8px; flex-wrap:wrap;">
                    <span>Edu <b>{bd['education']['score']:.0f}/{bd['education']['max']}</b></span>·
                    <span>Exp <b>{bd['experience']['score']:.0f}/{bd['experience']['max']}</b></span>·
                    <span>Skills <b>{bd['skills']['score']:.0f}/{bd['skills']['max']}</b></span>·
                    <span>Age <b>{bd['age']['score']:.0f}/{bd['age']['max']}</b></span>·
                    <span>Gender <b>{bd['gender']['score']:.0f}/{bd['gender']['max']}</b></span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"🔍 Full detail — #{rank}", key=f"det_{rank}"):
                    st.session_state.selected_idx = rank - 1
                    st.success("➡️ Switch to the **Candidate Detail** tab above")

        with col_chart:
            st.markdown("### 📊 Visual Analysis")

            names = [c["cv_info"].get("name") or c["filename"][:18] for c in ranked]

            # Horizontal bar chart
            fig_bar = go.Figure(go.Bar(
                x=scores, y=names, orientation="h",
                marker=dict(
                    color=scores,
                    colorscale=[[0,"#ef4444"],[0.5,"#f59e0b"],[1,"#22c55e"]],
                    cmin=0, cmax=100, line=dict(width=0),
                ),
                text=[f"{s:.1f}" for s in scores], textposition="outside",
            ))
            fig_bar.update_layout(
                title="Overall Match Scores",
                xaxis=dict(range=[0,115], title="Score / 100"),
                yaxis=dict(autorange="reversed"),
                height=max(220, len(ranked)*46),
                margin=dict(l=10,r=30,t=40,b=30),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12), showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            # Stacked breakdown
            cats = ["education","experience","skills","age","gender"]
            colors = ["#4f46e5","#06b6d4","#10b981","#f59e0b","#ec4899"]
            fig_stack = go.Figure()
            for cat, col in zip(cats, colors):
                fig_stack.add_trace(go.Bar(
                    name=cat.title(), x=names,
                    y=[c["score"]["breakdown"][cat]["score"] for c in ranked],
                    marker_color=col,
                ))
            fig_stack.update_layout(
                barmode="stack", title="Score Breakdown by Criterion",
                height=280, margin=dict(l=10,r=10,t=40,b=60),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11), legend=dict(orientation="h",y=-0.35),
                xaxis=dict(tickangle=-30),
            )
            st.plotly_chart(fig_stack, use_container_width=True)

            # Radar for #1 candidate
            top = ranked[0]
            bd = top["score"]["breakdown"]
            rcats = [k.title() for k in bd]
            rvals = [bd[k]["score"]/bd[k]["max"]*100 if bd[k]["max"]>0 else 0 for k in bd]
            fig_radar = go.Figure(go.Scatterpolar(
                r=rvals+[rvals[0]], theta=rcats+[rcats[0]],
                fill="toself", fillcolor="rgba(79,70,229,0.18)",
                line=dict(color="#4f46e5", width=2),
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(range=[0,100], tickfont=dict(size=9))),
                showlegend=False,
                title=f"Top Candidate — {top['cv_info'].get('name','#1')}",
                height=260, margin=dict(l=30,r=30,t=45,b=10),
                paper_bgcolor="rgba(0,0,0,0)", font=dict(size=11),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # Export
        st.divider()
        st.markdown("### 📥 Export Results")
        rows = []
        for c in ranked:
            info = c["cv_info"]
            bd = c["score"]["breakdown"]
            rows.append({
                "Rank": c["rank"], "Name": info.get("name",""),
                "Email": info.get("email",""), "Phone": info.get("phone",""),
                "Gender": info.get("gender",""), "Age": info.get("age",""),
                "Experience (yrs)": info.get("experience_years",0),
                "Education": info.get("education",{}).get("level",""),
                "Field": info.get("education",{}).get("field",""),
                "Total Score": c["score"]["total"],
                "Education Score": bd["education"]["score"],
                "Experience Score": bd["experience"]["score"],
                "Skills Score": bd["skills"]["score"],
                "Age Score": bd["age"]["score"],
                "Gender Score": bd["gender"]["score"],
                "Skills Found": ", ".join(info.get("skills",[])),
                "File": c["filename"],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download CSV", df.to_csv(index=False),
            file_name=f"hireiq_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — CANDIDATE DETAIL
# ══════════════════════════════════════════════════════════════════════════════
with tab_detail:
    if not st.session_state.ranked:
        st.info("Run the screening first — candidate details will appear here.")
    else:
        ranked = st.session_state.ranked

        names_for_sel = [
            f"#{c['rank']} — {c['cv_info'].get('name') or c['filename']} ({c['score']['total']:.1f} pts)"
            for c in ranked
        ]
        chosen = st.selectbox("Select candidate:", names_for_sel, index=st.session_state.selected_idx)
        idx = names_for_sel.index(chosen)
        st.session_state.selected_idx = idx
        cand = ranked[idx]

        info = cand["cv_info"]
        score = cand["score"]
        bd = score["breakdown"]
        req_skills = set(st.session_state.criteria.get("skills", []) if st.session_state.criteria else [])

        st.divider()
        st.markdown(f"## #{cand['rank']} &nbsp; {info.get('name','Unknown')}")

        hc1, hc2, hc3, hc4, hc5 = st.columns(5)
        hc1.metric("Total Score", f"{score['total']:.1f} / 100")
        hc2.metric("Experience", f"{info.get('experience_years',0)} yrs")
        hc3.metric("Education", info.get("education",{}).get("level") or "—")
        hc4.metric("Age", str(info.get("age") or "—"))
        hc5.metric("Gender", (info.get("gender") or "—").title())

        st.divider()

        dcol1, dcol2 = st.columns([1,1], gap="large")

        with dcol1:
            st.markdown("#### 📇 Contact Details")
            st.markdown(f"- **Email:** {info.get('email') or '—'}")
            st.markdown(f"- **Phone:** {info.get('phone') or '—'}")
            st.markdown(f"- **File:** {cand['filename']}")
            st.markdown(f"- **Status:** `{cand.get('status','pending')}`")

            st.markdown("#### 🛠️ Skills")
            cv_skills = info.get("skills", [])
            if cv_skills:
                tags = []
                for sk in cv_skills:
                    cls = "tag tag-match" if sk.lower() in req_skills else "tag tag-req"
                    tags.append(f'<span class="{cls}">{sk}</span>')
                st.markdown("".join(tags), unsafe_allow_html=True)
                missing = [s for s in req_skills if s not in cv_skills]
                if missing:
                    st.markdown("**Missing required skills:**")
                    st.markdown("".join(f'<span class="tag tag-miss">{s}</span>' for s in missing), unsafe_allow_html=True)
            else:
                st.caption("No skills detected in CV")

            with st.expander("📄 Raw extracted CV text"):
                raw = cand.get("cv_text","")
                if raw and raw.strip():
                    st.text(raw[:3000] + ("…" if len(raw)>3000 else ""))
                else:
                    st.warning("⚠️ No text extracted. PDF may be a scanned image — use a text-based PDF.")

        with dcol2:
            st.markdown("#### 📊 Criterion Breakdown")

            crit_colors = {
                "education":"#4f46e5","experience":"#06b6d4",
                "skills":"#10b981","age":"#f59e0b","gender":"#ec4899",
            }
            for crit, data in bd.items():
                s, m, note = data["score"], data["max"], data["note"]
                pct = (s/m*100) if m>0 else 0
                col = crit_colors.get(crit, "#6b7280")
                if "✅" in note:   bg="#f0fdf4"; bc="#22c55e"
                elif "⚠️" in note: bg="#fffbeb"; bc="#f59e0b"
                else:              bg="#fef2f2"; bc="#ef4444"

                st.markdown(f"""
                <div style="border:1px solid {bc}; border-left:4px solid {col};
                            border-radius:10px; padding:12px 14px; margin-bottom:10px; background:{bg};">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-weight:600; font-size:14px; text-transform:capitalize;">{crit}</span>
                    <span style="font-weight:700; font-size:17px; color:{col};">{s:.1f}
                      <span style="font-size:11px;color:#9ca3af;"> / {m}</span></span>
                  </div>
                  <div class="bar-bg" style="margin-bottom:6px;">
                    <div class="bar-fill" style="width:{min(pct,100):.1f}%;background:{col};"></div>
                  </div>
                  <div style="font-size:12px;color:#374151;">{note}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        nav1, nav2, nav3 = st.columns(3)
        with nav1:
            if idx > 0:
                if st.button("⬅️ Previous", use_container_width=True):
                    st.session_state.selected_idx = idx-1
                    st.rerun()
        with nav2:
            opts = ["pending","selected","rejected","hold"]
            cur = cand.get("status","pending")
            new_s = st.selectbox("Status", opts, index=opts.index(cur), key="status_sel")
            if new_s != cur:
                st.session_state.ranked[idx]["status"] = new_s
                st.success(f"Status → **{new_s}**")
        with nav3:
            if idx < len(ranked)-1:
                if st.button("Next ➡️", use_container_width=True):
                    st.session_state.selected_idx = idx+1
                    st.rerun()

st.divider()
st.caption("HireIQ · Phase 1 · AI CV Screening · 2025")
