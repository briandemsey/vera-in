"""
VERA-IN - Verification Engine for Results & Accountability
Streamlit Web Application for Indiana Education Data

Year Zero infrastructure for Indiana's GPS accountability system.
Verifies before grades carry consequences (2026-27).

Indiana GPS Framework: Graduate Prepared to Succeed
HEA 1498 (2025) established the framework.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sqlite3
import random

# =============================================================================
# Configuration
# =============================================================================

st.set_page_config(
    page_title="VERA-IN | Indiana Year Zero",
    page_icon="🌽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Indiana State Colors
CRIMSON = "#9D2235"
DARK_CRIMSON = "#6b1725"
GOLD = "#D4AF37"
WHITE = "#FFFFFF"
CREAM = "#F8F8F5"
NAVY = "#1B2A4A"

# Custom CSS
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&display=swap');

    .stApp {{
        background-color: {CREAM};
    }}

    section[data-testid="stSidebar"] {{
        background-color: {CRIMSON};
    }}
    section[data-testid="stSidebar"] .stMarkdown {{
        color: white;
    }}
    section[data-testid="stSidebar"] label {{
        color: white !important;
    }}
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio label span,
    section[data-testid="stSidebar"] .stRadio label p,
    section[data-testid="stSidebar"] .stRadio label div {{
        color: white !important;
    }}

    h1, h2, h3 {{
        font-family: 'Public Sans', sans-serif;
        color: {CRIMSON};
    }}
    h1 {{
        border-bottom: 4px solid {GOLD};
        padding-bottom: 16px;
    }}

    .stat-card {{
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-left: 4px solid {CRIMSON};
        min-width: 0;
    }}
    .stat-card .value {{
        font-size: 1.8rem;
        font-weight: 700;
        color: {CRIMSON};
        white-space: nowrap;
    }}
    .stat-card .label {{
        font-size: 0.85rem;
        color: #666;
    }}

    .year-zero-badge {{
        background: {GOLD};
        color: {NAVY};
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 16px;
    }}

    .milestone-card {{
        background: white;
        padding: 24px;
        border-radius: 8px;
        border-top: 4px solid {CRIMSON};
        margin-bottom: 16px;
    }}
    .milestone-card h4 {{
        color: {CRIMSON};
        font-size: 1.1rem;
        margin-bottom: 12px;
    }}

    .portrait-grid {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin: 20px 0;
    }}
    .portrait-item {{
        background: {CRIMSON};
        color: white;
        padding: 16px 8px;
        text-align: center;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Demo Data - Indiana Schools
# =============================================================================

@st.cache_data
def generate_demo_data():
    """Generate demo Indiana school data for Year Zero analysis."""

    # Indiana school corporations (districts)
    corporations = [
        ("Indianapolis Public Schools", "Marion", "Urban"),
        ("Fort Wayne Community Schools", "Allen", "Urban"),
        ("Evansville Vanderburgh School Corp", "Vanderburgh", "Urban"),
        ("South Bend Community School Corp", "St. Joseph", "Urban"),
        ("Carmel Clay Schools", "Hamilton", "Suburban"),
        ("Hamilton Southeastern Schools", "Hamilton", "Suburban"),
        ("Noblesville Schools", "Hamilton", "Suburban"),
        ("Fishers High School", "Hamilton", "Suburban"),
        ("Westfield Washington Schools", "Hamilton", "Suburban"),
        ("Zionsville Community Schools", "Boone", "Suburban"),
        ("Brownsburg Community School Corp", "Hendricks", "Suburban"),
        ("Avon Community School Corp", "Hendricks", "Suburban"),
        ("Plainfield Community School Corp", "Hendricks", "Suburban"),
        ("Center Grove Community School Corp", "Johnson", "Suburban"),
        ("Franklin Township Community School Corp", "Marion", "Suburban"),
        ("Perry Township Schools", "Marion", "Suburban"),
        ("Warren Township Schools", "Marion", "Urban"),
        ("Lawrence Township Schools", "Marion", "Suburban"),
        ("Washington Township Schools", "Marion", "Suburban"),
        ("Pike Township Schools", "Marion", "Suburban"),
        ("Bartholomew Consolidated School Corp", "Bartholomew", "Town"),
        ("Monroe County Community School Corp", "Monroe", "Town"),
        ("Tippecanoe School Corp", "Tippecanoe", "Town"),
        ("Vigo County School Corp", "Vigo", "Town"),
        ("Elkhart Community Schools", "Elkhart", "Town"),
    ]

    schools = []
    school_id = 1000

    for corp_name, county, locale in corporations:
        # Generate 3-8 schools per corporation
        num_schools = random.randint(3, 8)
        for i in range(num_schools):
            school_type = random.choice(["Elementary", "Middle", "High", "Elementary", "Elementary"])

            if school_type == "Elementary":
                grades = "K-5"
                enrollment = random.randint(300, 700)
            elif school_type == "Middle":
                grades = "6-8"
                enrollment = random.randint(500, 1000)
            else:
                grades = "9-12"
                enrollment = random.randint(800, 2500)

            # Demographics
            pct_frpl = random.randint(15, 75) if locale in ["Urban", "Town"] else random.randint(5, 35)
            pct_ell = random.randint(2, 25) if locale == "Urban" else random.randint(1, 10)
            pct_swd = random.randint(10, 18)

            # ILEARN proficiency (varies by demographics)
            base_ela = 55 - (pct_frpl * 0.3) + random.randint(-8, 8)
            base_math = 50 - (pct_frpl * 0.35) + random.randint(-8, 8)

            # Year Zero GPS Grade (informational only)
            gps_points = (base_ela + base_math) / 2 + random.randint(-5, 10)
            if gps_points >= 80:
                gps_grade = "A"
            elif gps_points >= 70:
                gps_grade = "B"
            elif gps_points >= 60:
                gps_grade = "C"
            elif gps_points >= 50:
                gps_grade = "D"
            else:
                gps_grade = "F"

            schools.append({
                "school_id": school_id,
                "school_name": f"{corp_name.split()[0]} {school_type} #{i+1}",
                "corporation": corp_name,
                "county": county,
                "locale": locale,
                "school_type": school_type,
                "grades_served": grades,
                "enrollment": enrollment,
                "pct_frpl": pct_frpl,
                "pct_ell": pct_ell,
                "pct_swd": pct_swd,
                "ilearn_ela": max(20, min(95, base_ela)),
                "ilearn_math": max(15, min(92, base_math)),
                "gps_grade": gps_grade,
                "gps_points": round(gps_points, 1),
                "attendance_rate": round(random.uniform(90, 97), 1),
                "graduation_rate": round(random.uniform(75, 98), 1) if school_type == "High" else None,
            })
            school_id += 1

    return pd.DataFrame(schools)


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <span style="font-size: 3rem;">🌽</span>
            <h2 style="color: white; margin: 10px 0;">VERA-IN</h2>
            <p style="color: {GOLD}; font-size: 0.9rem;">Verification Engine for Results & Accountability</p>
            <p style="color: rgba(255,255,255,0.6); font-size: 0.8rem;">Indiana • Year Zero</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["📊 Year Zero Dashboard", "📈 GPS Grade Distribution", "🎯 Portrait of a Graduate", "📋 Milestone Tracker", "ℹ️ About VERA-IN"],
        label_visibility="collapsed"
    )

    st.markdown(f"""
        <div style="
            height: 4px;
            background: linear-gradient(90deg, {GOLD}, #E8C547, {GOLD});
            margin: 30px 0 20px 0;
            border-radius: 2px;
        "></div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <p style="color: {GOLD}; font-size: 1.4rem; font-weight: 700; text-align: center; margin: 12px 0 6px 0;">
            Year Zero
        </p>
        <p style="color: white; font-size: 0.85rem; text-align: center; margin: 0 0 4px 0;">
            2025-26 School Year
        </p>
        <p style="color: rgba(255,255,255,0.7); font-size: 0.75rem; text-align: center; margin: 0 0 12px 0;">
            Grades calculated • No consequences
        </p>
        <p style="text-align: center;">
            <a href="https://indianagps.doe.in.gov" target="_blank" style="
                color: {GOLD};
                font-size: 0.9rem;
                font-weight: 600;
                text-decoration: none;
                border-bottom: 2px solid {GOLD};
            ">Indiana GPS Portal</a>
        </p>
    """, unsafe_allow_html=True)


# =============================================================================
# Load Data
# =============================================================================

schools_df = generate_demo_data()


# =============================================================================
# Page: Year Zero Dashboard
# =============================================================================

if page == "📊 Year Zero Dashboard":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("Indiana GPS Dashboard")
    st.caption("Demo data for verification testing • HEA 1498 Framework")

    st.markdown("""
    **Year Zero** means grades are calculated and published under the new GPS model,
    but carry no consequences. This is Indiana's window for verification — ensuring
    the system works before grades count in 2026-27.
    """)

    st.markdown("---")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        counties = ["All"] + sorted(schools_df["county"].unique().tolist())
        selected_county = st.selectbox("County", counties)
    with col2:
        corps = ["All"] + sorted(schools_df["corporation"].unique().tolist())
        selected_corp = st.selectbox("Corporation", corps)
    with col3:
        school_types = ["All", "Elementary", "Middle", "High"]
        selected_type = st.selectbox("School Type", school_types)

    # Filter data
    filtered = schools_df.copy()
    if selected_county != "All":
        filtered = filtered[filtered["county"] == selected_county]
    if selected_corp != "All":
        filtered = filtered[filtered["corporation"] == selected_corp]
    if selected_type != "All":
        filtered = filtered[filtered["school_type"] == selected_type]

    # Summary stats
    st.markdown("### Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="value">{len(filtered):,}</div>
                <div class="label">Schools</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        total_enrollment = filtered["enrollment"].sum()
        st.markdown(f"""
            <div class="stat-card">
                <div class="value">{int(total_enrollment):,}</div>
                <div class="label">Total Students</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        avg_ela = filtered["ilearn_ela"].mean()
        st.markdown(f"""
            <div class="stat-card">
                <div class="value">{avg_ela:.1f}%</div>
                <div class="label">Avg ILEARN ELA</div>
            </div>
        """, unsafe_allow_html=True)
    with c4:
        avg_math = filtered["ilearn_math"].mean()
        st.markdown(f"""
            <div class="stat-card">
                <div class="value">{avg_math:.1f}%</div>
                <div class="label">Avg ILEARN Math</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### GPS Grade Distribution (Year Zero)")
        grade_counts = filtered["gps_grade"].value_counts().reindex(["A", "B", "C", "D", "F"]).fillna(0)

        fig = px.bar(
            x=grade_counts.index,
            y=grade_counts.values,
            color=grade_counts.index,
            color_discrete_map={"A": "#1A5C38", "B": "#4CAF50", "C": "#FFC107", "D": "#FF9800", "F": CRIMSON},
            labels={"x": "GPS Grade", "y": "Number of Schools"}
        )
        fig.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("⚠️ Year Zero: These grades are informational only — no consequences attached.")

    with col_right:
        st.markdown("### ILEARN Proficiency by Locale")
        locale_prof = filtered.groupby("locale").agg({
            "ilearn_ela": "mean",
            "ilearn_math": "mean"
        }).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(name="ELA", x=locale_prof["locale"], y=locale_prof["ilearn_ela"], marker_color=CRIMSON))
        fig.add_trace(go.Bar(name="Math", x=locale_prof["locale"], y=locale_prof["ilearn_math"], marker_color=GOLD))
        fig.update_layout(barmode="group", height=350)
        fig.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50% Threshold")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Schools table
    st.markdown("### Schools")
    display_df = filtered[["school_name", "corporation", "county", "school_type", "enrollment",
                           "ilearn_ela", "ilearn_math", "gps_grade", "gps_points"]].copy()
    display_df.columns = ["School", "Corporation", "County", "Type", "Enrollment",
                          "ELA %", "Math %", "GPS Grade", "GPS Points"]

    st.dataframe(
        display_df.sort_values("GPS Points", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    csv = filtered.to_csv(index=False)
    st.download_button("Download CSV", csv, "vera_in_year_zero.csv", "text/csv")


# =============================================================================
# Page: GPS Grade Distribution
# =============================================================================

elif page == "📈 GPS Grade Distribution":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("GPS Grade Distribution Analysis")
    st.caption("Analyzing Year Zero grade calculations before they carry consequences")

    st.markdown("""
    The GPS (Graduate Prepared to Succeed) framework assigns A-F grades based on multiple measures
    including ILEARN proficiency, growth, graduation pathways, and attendance. Year Zero allows us
    to verify these calculations work correctly.
    """)

    st.markdown("---")

    # Statewide distribution
    st.markdown("### Statewide Grade Distribution")

    grade_counts = schools_df["gps_grade"].value_counts().reindex(["A", "B", "C", "D", "F"]).fillna(0)

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.pie(
            values=grade_counts.values,
            names=grade_counts.index,
            color=grade_counts.index,
            color_discrete_map={"A": "#1A5C38", "B": "#4CAF50", "C": "#FFC107", "D": "#FF9800", "F": CRIMSON},
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Grade Breakdown")
        for grade in ["A", "B", "C", "D", "F"]:
            count = int(grade_counts.get(grade, 0))
            pct = count / len(schools_df) * 100
            st.markdown(f"**{grade}:** {count} schools ({pct:.1f}%)")

        st.markdown("---")
        st.markdown(f"**Total:** {len(schools_df)} schools")

    st.markdown("---")

    # Grade by school type
    st.markdown("### GPS Grades by School Type")

    grade_by_type = schools_df.groupby(["school_type", "gps_grade"]).size().unstack(fill_value=0)
    grade_by_type = grade_by_type.reindex(columns=["A", "B", "C", "D", "F"], fill_value=0)

    fig = px.bar(
        grade_by_type.reset_index().melt(id_vars="school_type"),
        x="school_type",
        y="value",
        color="gps_grade",
        color_discrete_map={"A": "#1A5C38", "B": "#4CAF50", "C": "#FFC107", "D": "#FF9800", "F": CRIMSON},
        labels={"school_type": "School Type", "value": "Number of Schools", "gps_grade": "GPS Grade"},
        barmode="group"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Verification flags
    st.markdown("### Verification Flags")
    st.markdown("VERA identifies potential calculation anomalies that warrant review before grades count.")

    # Flag schools with potential issues
    high_poverty_high_grade = schools_df[(schools_df["pct_frpl"] > 60) & (schools_df["gps_grade"].isin(["A", "B"]))]
    low_poverty_low_grade = schools_df[(schools_df["pct_frpl"] < 25) & (schools_df["gps_grade"].isin(["D", "F"]))]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="milestone-card">
            <h4>🔍 High-Poverty Schools with High Grades</h4>
            <p>Schools with >60% FRPL and GPS Grade A or B</p>
            <p style="font-size: 2rem; font-weight: 700; color: {CRIMSON};">{len(high_poverty_high_grade)}</p>
            <p style="font-size: 0.85rem; color: #666;">May indicate strong intervention programs — verify for best practices</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="milestone-card">
            <h4>⚠️ Low-Poverty Schools with Low Grades</h4>
            <p>Schools with <25% FRPL and GPS Grade D or F</p>
            <p style="font-size: 2rem; font-weight: 700; color: {CRIMSON};">{len(low_poverty_low_grade)}</p>
            <p style="font-size: 0.85rem; color: #666;">May indicate calculation issues — verify data inputs</p>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# Page: Portrait of a Graduate
# =============================================================================

elif page == "🎯 Portrait of a Graduate":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("Portrait of a Graduate")
    st.caption("Indiana's five characteristics for graduate success")

    st.markdown("""
    HEA 1498 established Indiana's "Portrait of a Graduate" — five characteristics that
    define success beyond test scores. Year Zero tracks implementation fidelity across schools.
    """)

    # Portrait grid
    st.markdown("""
    <div class="portrait-grid">
        <div class="portrait-item">Academic<br>Mastery</div>
        <div class="portrait-item">Workforce<br>Skills</div>
        <div class="portrait-item">Communication</div>
        <div class="portrait-item">Collaboration</div>
        <div class="portrait-item">Work<br>Ethic</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Milestones
    st.markdown("### GPS Milestones by Grade Band")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="milestone-card">
            <h4>📚 K-3 Milestones</h4>
            <ul>
                <li>ILEARN test proficiency</li>
                <li>Attendance markers</li>
                <li>Literacy growth indicators</li>
                <li>ELL goal attainment</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="milestone-card">
            <h4>📖 Grades 4-8</h4>
            <ul>
                <li>Academic mastery across subjects</li>
                <li>Skills development tracking</li>
                <li>Additional achievement pathways</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="milestone-card">
            <h4>🎓 Grades 9-10</h4>
            <ul>
                <li>Career pathway exploration</li>
                <li>Work ethic and collaboration skills</li>
                <li>Academic advancement indicators</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="milestone-card">
            <h4>🏆 Grades 11-12</h4>
            <ul>
                <li>Workforce credentials earned</li>
                <li>Work-based learning experiences</li>
                <li>College/career coursework</li>
                <li>Regular attendance maintained</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Implementation tracking
    st.markdown("### Postsecondary Pathway Distribution")
    st.markdown("The 'Three E's' — Enrollment, Employment, Enlistment")

    # Generate sample pathway data
    pathways = {
        "College Enrollment": 45,
        "Workforce Employment": 38,
        "Military Enlistment": 8,
        "Other/Unknown": 9
    }

    fig = px.pie(
        values=list(pathways.values()),
        names=list(pathways.keys()),
        color_discrete_sequence=[CRIMSON, GOLD, "#1A5C38", "#888"]
    )
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Page: Milestone Tracker
# =============================================================================

elif page == "📋 Milestone Tracker":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("GPS Milestone Tracker")
    st.caption("Tracking progress toward GPS implementation goals")

    st.markdown("""
    Year Zero establishes baselines for GPS milestone achievement.
    This tracker monitors readiness before grades carry consequences.
    """)

    st.markdown("---")

    # Key metrics
    st.markdown("### Implementation Readiness")

    metrics = [
        ("3rd Grade Literacy", 62, "%", "Students meeting 3rd grade reading proficiency"),
        ("6th Grade Math Growth", 55, "%", "Students showing adequate growth"),
        ("Graduation Pathway Completion", 78, "%", "Seniors completing a pathway"),
        ("Credential Attainment", 34, "%", "Students earning workforce credentials"),
    ]

    cols = st.columns(4)
    for i, (name, value, unit, desc) in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{value}{unit}</div>
                    <div class="label">{name}</div>
                </div>
            """, unsafe_allow_html=True)
            st.caption(desc)

    st.markdown("---")

    # Progress chart
    st.markdown("### Year Zero Progress Timeline")

    timeline_data = pd.DataFrame({
        "Month": ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "Schools Reporting": [45, 68, 82, 88, 91, 94, 96, 98, 99, 100],
        "Data Quality Score": [72, 78, 82, 85, 87, 89, 91, 93, 95, 97]
    })

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timeline_data["Month"],
        y=timeline_data["Schools Reporting"],
        name="Schools Reporting (%)",
        line=dict(color=CRIMSON, width=3)
    ))
    fig.add_trace(go.Scatter(
        x=timeline_data["Month"],
        y=timeline_data["Data Quality Score"],
        name="Data Quality Score",
        line=dict(color=GOLD, width=3)
    ))
    fig.update_layout(height=350, yaxis_title="Percentage")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Ed-Fi integration status
    st.markdown("### Ed-Fi Data Integration Status")
    st.markdown("Indiana has adopted the Ed-Fi Data Standard for modern data exchange.")

    integration_status = [
        ("Student Information Systems", 92, "Connected"),
        ("Assessment Data", 88, "Connected"),
        ("Attendance Systems", 85, "Connected"),
        ("Credential Tracking", 67, "In Progress"),
        ("Work-Based Learning", 45, "Planned"),
    ]

    for system, pct, status in integration_status:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(pct / 100)
        with col2:
            color = "#1A5C38" if status == "Connected" else (GOLD if status == "In Progress" else "#888")
            st.markdown(f"**{system}**")
            st.markdown(f"<span style='color: {color}'>{status}</span> ({pct}%)", unsafe_allow_html=True)


# =============================================================================
# Page: About
# =============================================================================

elif page == "ℹ️ About VERA-IN":
    st.title("About VERA-IN")

    st.markdown(f"""
    ## Verification Engine for Results & Accountability

    **VERA-IN** provides Year Zero verification infrastructure for Indiana's GPS
    accountability system. It ensures calculations work correctly before grades
    carry consequences in 2026-27.

    ---

    ## The GPS Framework

    Indiana's **Graduate Prepared to Succeed (GPS)** framework was established by
    **HEA 1498** (2025). It measures success at critical K-12 milestones:

    - **K-3:** Literacy foundations
    - **4-8:** Academic mastery and skills development
    - **9-10:** Career pathway exploration
    - **11-12:** Postsecondary readiness (3 E's: Enrollment, Employment, Enlistment)

    ---

    ## Year Zero (2025-26)

    The current school year is **Year Zero** — grades are calculated and publicly
    released under the new GPS model, but carry no consequences. This provides:

    - Time to verify calculation accuracy
    - Baseline data for future comparisons
    - Opportunity to identify and fix data issues
    - Stakeholder familiarization with new metrics

    **In 2026-27**, grades will carry legal consequences for schools.

    ---

    ## What VERA Verifies

    | Area | Verification Focus |
    |------|-------------------|
    | **Grade Calculations** | Do A-F grades accurately reflect school performance? |
    | **Data Integration** | Is Ed-Fi data flowing correctly from all sources? |
    | **Milestone Tracking** | Are Portrait of a Graduate characteristics measured consistently? |
    | **Pathway Analytics** | Are postsecondary outcomes tracked accurately? |
    | **Equity Indicators** | Are achievement gaps identified and actionable? |

    ---

    ## Data Sources

    **Current:** Demo data for verification testing

    **Planned Integrations:**
    - [Indiana GPS Portal](https://indianagps.doe.in.gov) — Official school data
    - [IDOE EdData](https://eddata.doe.in.gov) — Enrollment and finance
    - Ed-Fi Data Exchange — Real-time SIS integration

    ---

    <p style="color: #666; font-size: 0.9rem;">
        VERA-IN v0.1 | Year Zero Edition | Built by <a href="https://hallucinations.cloud" style="color: {CRIMSON};">Hallucinations.cloud</a> |
        An <a href="https://h-edu.solutions" style="color: {CRIMSON};">H-EDU.Solutions</a> Initiative
    </p>
    """, unsafe_allow_html=True)
