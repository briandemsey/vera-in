"""
VERA-IN - Verification Engine for Results & Accountability
Streamlit Web Application for Indiana Education Data

Year Zero infrastructure for Indiana's GPS accountability system.
Verifies before grades carry consequences (2026-27).

Data sourced from Indiana DHS GIS (gis.dhs.in.gov) with IDOE school data.
Indiana GPS Framework: Graduate Prepared to Succeed
HEA 1498 (2025) established the framework.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
# Data Functions - Indiana DHS ArcGIS API (IDOE School Data)
# =============================================================================

# Indiana DHS GIS Schools endpoint (direct from IDOE)
INDIANA_SCHOOLS_ENDPOINT = "https://gis.dhs.in.gov/arcgis/rest/services/Open/SchoolsOpen/FeatureServer/0/query"


@st.cache_data(ttl=3600)
def fetch_indiana_schools():
    """Fetch all Indiana schools from DHS ArcGIS endpoint."""
    all_schools = []
    offset = 0
    batch_size = 1000

    while True:
        try:
            response = requests.get(
                INDIANA_SCHOOLS_ENDPOINT,
                params={
                    "where": "1=1",
                    "outFields": "OBJECTID,IDOE_SCHOOL_ID,SCHOOL_NAME,CORPORATION_NAME,COUNTY_NAME,ADDRESS,CITY,ZIP,LOW_GRADE,HIGH_GRADE,Type,Enrollment",
                    "f": "json",
                    "resultRecordCount": batch_size,
                    "resultOffset": offset
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])
            if not features:
                break

            for feature in features:
                attrs = feature.get("attributes", {})
                all_schools.append(attrs)

            if len(features) < batch_size:
                break
            offset += batch_size

        except Exception as e:
            st.error(f"Error fetching school data: {e}")
            break

    return all_schools


def process_schools_data(raw_data):
    """Process raw API data into a clean DataFrame."""
    if not raw_data:
        return pd.DataFrame()

    df = pd.DataFrame(raw_data)

    # Rename columns for clarity
    df = df.rename(columns={
        "SCHOOL_NAME": "school_name",
        "CORPORATION_NAME": "corporation",
        "COUNTY_NAME": "county",
        "IDOE_SCHOOL_ID": "school_id",
        "LOW_GRADE": "low_grade",
        "HIGH_GRADE": "high_grade",
        "Type": "school_type",
        "Enrollment": "enrollment",
        "ADDRESS": "address",
        "CITY": "city",
        "ZIP": "zip"
    })

    # Clean enrollment data
    df["enrollment"] = pd.to_numeric(df["enrollment"], errors="coerce").fillna(0).astype(int)

    # Filter out schools with no name or zero enrollment
    df = df[df["school_name"].notna()]
    df = df[df["enrollment"] > 0]

    # Determine school level from grades
    def get_school_level(row):
        low = str(row.get("low_grade", "")).upper()
        high = str(row.get("high_grade", "")).upper()

        if low in ["PK", "KG", "K", "01", "00"] and high in ["04", "05", "06"]:
            return "Elementary"
        elif low in ["06", "07"] and high in ["08", "09"]:
            return "Middle"
        elif low in ["09", "10"] and high in ["12"]:
            return "High"
        elif high == "12":
            return "High"
        elif low in ["PK", "KG", "K", "01"]:
            return "Elementary"
        else:
            return "Other"

    df["level"] = df.apply(get_school_level, axis=1)

    # Create grades served string
    df["grades_served"] = df["low_grade"].fillna("") + "-" + df["high_grade"].fillna("")

    return df


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    # Back arrow to h-edu.solutions
    st.markdown("""
        <a href="https://h-edu.solutions" target="_self" style="
            display: flex;
            align-items: center;
            color: white;
            text-decoration: none;
            font-size: 0.9rem;
            padding: 8px 0;
            margin-bottom: 10px;
            opacity: 0.9;
        ">
            <span style="font-size: 1.2rem; margin-right: 8px;">←</span>
            Back to H-EDU
        </a>
    """, unsafe_allow_html=True)

    # Display Indiana flag
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("indiana-flag.svg", width=80)

    st.markdown(f"""
        <div style="text-align: center; padding: 10px 0 20px 0;">
            <h2 style="color: white; margin: 10px 0;">VERA-IN</h2>
            <p style="color: {GOLD}; font-size: 0.9rem;">Verification Engine for Results & Accountability</p>
            <p style="color: rgba(255,255,255,0.6); font-size: 0.8rem;">Indiana • Year Zero</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["📊 School Dashboard", "📈 Enrollment Analysis", "🗺️ County Explorer", "🎯 Portrait of a Graduate", "ℹ️ About VERA-IN"],
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
            <a href="https://gis.dhs.in.gov" target="_blank" style="
                color: {GOLD};
                font-size: 0.9rem;
                font-weight: 600;
                text-decoration: none;
                border-bottom: 2px solid {GOLD};
            ">Indiana DHS GIS</a>
        </p>
    """, unsafe_allow_html=True)


# =============================================================================
# Load Data
# =============================================================================

with st.spinner("Loading Indiana school data..."):
    raw_schools = fetch_indiana_schools()
    schools_df = process_schools_data(raw_schools)


# =============================================================================
# Page: School Dashboard
# =============================================================================

if page == "📊 School Dashboard":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("Indiana School Dashboard")
    st.caption("Live data from Indiana DHS GIS • IDOE School Directory")

    if schools_df.empty:
        st.error("Unable to load school data. Please try again later.")
    else:
        st.markdown("""
        **Year Zero** means GPS grades are calculated and published under the new model,
        but carry no consequences. This dashboard provides the foundation for verification.
        """)

        st.markdown("---")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            counties = ["All"] + sorted(schools_df["county"].dropna().unique().tolist())
            selected_county = st.selectbox("County", counties)
        with col2:
            corps = ["All"] + sorted(schools_df["corporation"].dropna().unique().tolist())
            selected_corp = st.selectbox("Corporation", corps)
        with col3:
            levels = ["All", "Elementary", "Middle", "High", "Other"]
            selected_level = st.selectbox("School Level", levels)

        # Filter data
        filtered = schools_df.copy()
        if selected_county != "All":
            filtered = filtered[filtered["county"] == selected_county]
        if selected_corp != "All":
            filtered = filtered[filtered["corporation"] == selected_corp]
        if selected_level != "All":
            filtered = filtered[filtered["level"] == selected_level]

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
            num_corps = filtered["corporation"].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{num_corps:,}</div>
                    <div class="label">Corporations</div>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            num_counties = filtered["county"].nunique()
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{num_counties}</div>
                    <div class="label">Counties</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Charts
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("### Schools by Level")
            level_counts = filtered["level"].value_counts()

            fig = px.pie(
                values=level_counts.values,
                names=level_counts.index,
                color=level_counts.index,
                color_discrete_map={
                    "Elementary": CRIMSON,
                    "Middle": GOLD,
                    "High": "#1A5C38",
                    "Other": "#888"
                },
                hole=0.4
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.markdown("### Enrollment by Level")
            level_enrollment = filtered.groupby("level")["enrollment"].sum().reset_index()

            fig = px.bar(
                level_enrollment,
                x="level",
                y="enrollment",
                color="level",
                color_discrete_map={
                    "Elementary": CRIMSON,
                    "Middle": GOLD,
                    "High": "#1A5C38",
                    "Other": "#888"
                }
            )
            fig.update_layout(height=350, showlegend=False, xaxis_title="School Level", yaxis_title="Total Enrollment")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Schools table
        st.markdown("### Schools")
        display_df = filtered[["school_name", "corporation", "county", "level", "grades_served", "enrollment", "city"]].copy()
        display_df.columns = ["School", "Corporation", "County", "Level", "Grades", "Enrollment", "City"]

        st.dataframe(
            display_df.sort_values("Enrollment", ascending=False),
            use_container_width=True,
            hide_index=True
        )

        csv = filtered.to_csv(index=False)
        st.download_button("Download CSV", csv, "vera_in_schools.csv", "text/csv")


# =============================================================================
# Page: Enrollment Analysis
# =============================================================================

elif page == "📈 Enrollment Analysis":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("Enrollment Analysis")
    st.caption("Analyzing Indiana school enrollment patterns")

    if schools_df.empty:
        st.error("Unable to load school data.")
    else:
        st.markdown("---")

        # Top corporations by enrollment
        st.markdown("### Top Corporations by Enrollment")

        corp_enrollment = schools_df.groupby("corporation").agg({
            "enrollment": "sum",
            "school_name": "count"
        }).reset_index()
        corp_enrollment.columns = ["Corporation", "Enrollment", "Schools"]
        corp_enrollment = corp_enrollment.sort_values("Enrollment", ascending=False).head(20)

        fig = px.bar(
            corp_enrollment,
            x="Enrollment",
            y="Corporation",
            orientation="h",
            color="Enrollment",
            color_continuous_scale=[GOLD, CRIMSON]
        )
        fig.update_layout(height=600, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Enrollment distribution
        st.markdown("### School Size Distribution")

        col1, col2 = st.columns(2)

        with col1:
            fig = px.histogram(
                schools_df,
                x="enrollment",
                nbins=50,
                color_discrete_sequence=[CRIMSON]
            )
            fig.update_layout(
                height=350,
                xaxis_title="Enrollment",
                yaxis_title="Number of Schools"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Size categories
            def size_category(e):
                if e < 200:
                    return "Small (<200)"
                elif e < 500:
                    return "Medium (200-500)"
                elif e < 1000:
                    return "Large (500-1000)"
                else:
                    return "Very Large (1000+)"

            schools_df["size_cat"] = schools_df["enrollment"].apply(size_category)
            size_counts = schools_df["size_cat"].value_counts()

            fig = px.pie(
                values=size_counts.values,
                names=size_counts.index,
                color_discrete_sequence=[GOLD, CRIMSON, "#1A5C38", NAVY]
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Summary stats
        st.markdown("### Enrollment Statistics")

        stats_cols = st.columns(4)

        with stats_cols[0]:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{schools_df['enrollment'].mean():.0f}</div>
                    <div class="label">Avg Enrollment</div>
                </div>
            """, unsafe_allow_html=True)

        with stats_cols[1]:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{schools_df['enrollment'].median():.0f}</div>
                    <div class="label">Median Enrollment</div>
                </div>
            """, unsafe_allow_html=True)

        with stats_cols[2]:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{schools_df['enrollment'].max():,}</div>
                    <div class="label">Largest School</div>
                </div>
            """, unsafe_allow_html=True)

        with stats_cols[3]:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{schools_df['enrollment'].sum():,}</div>
                    <div class="label">Total Students</div>
                </div>
            """, unsafe_allow_html=True)


# =============================================================================
# Page: County Explorer
# =============================================================================

elif page == "🗺️ County Explorer":
    st.markdown('<span class="year-zero-badge">YEAR ZERO • 2025-26</span>', unsafe_allow_html=True)
    st.title("County Explorer")
    st.caption("Explore Indiana schools by county")

    if schools_df.empty:
        st.error("Unable to load school data.")
    else:
        # County summary
        county_stats = schools_df.groupby("county").agg({
            "school_name": "count",
            "enrollment": "sum",
            "corporation": "nunique"
        }).reset_index()
        county_stats.columns = ["County", "Schools", "Enrollment", "Corporations"]
        county_stats = county_stats.sort_values("Enrollment", ascending=False)

        st.markdown("### Counties by Total Enrollment")

        fig = px.bar(
            county_stats.head(25),
            x="County",
            y="Enrollment",
            color="Schools",
            color_continuous_scale=[GOLD, CRIMSON]
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # County selector
        st.markdown("### County Details")

        selected_county = st.selectbox(
            "Select a county to explore",
            sorted(schools_df["county"].dropna().unique().tolist())
        )

        county_schools = schools_df[schools_df["county"] == selected_county]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{len(county_schools):,}</div>
                    <div class="label">Schools in {selected_county}</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{county_schools['enrollment'].sum():,}</div>
                    <div class="label">Total Students</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="stat-card">
                    <div class="value">{county_schools['corporation'].nunique()}</div>
                    <div class="label">Corporations</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Schools in selected county
        st.markdown(f"### Schools in {selected_county} County")

        display_df = county_schools[["school_name", "corporation", "level", "grades_served", "enrollment", "city"]].copy()
        display_df.columns = ["School", "Corporation", "Level", "Grades", "Enrollment", "City"]

        st.dataframe(
            display_df.sort_values("Enrollment", ascending=False),
            use_container_width=True,
            hide_index=True
        )


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

    # School level breakdown from real data
    if not schools_df.empty:
        st.markdown("### Schools by GPS Milestone Band")

        # Map levels to milestone bands
        milestone_mapping = {
            "Elementary": "K-5 Foundation",
            "Middle": "6-8 Transition",
            "High": "9-12 Completion",
            "Other": "Other"
        }

        schools_df["milestone_band"] = schools_df["level"].map(milestone_mapping)
        band_stats = schools_df.groupby("milestone_band").agg({
            "school_name": "count",
            "enrollment": "sum"
        }).reset_index()
        band_stats.columns = ["Milestone Band", "Schools", "Students"]

        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(
                band_stats,
                values="Schools",
                names="Milestone Band",
                color_discrete_sequence=[CRIMSON, GOLD, "#1A5C38", "#888"]
            )
            fig.update_layout(height=300, title="Schools by Band")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                band_stats,
                values="Students",
                names="Milestone Band",
                color_discrete_sequence=[CRIMSON, GOLD, "#1A5C38", "#888"]
            )
            fig.update_layout(height=300, title="Students by Band")
            st.plotly_chart(fig, use_container_width=True)


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

    ## Data Source

    **Live data from Indiana DHS GIS:**

    - **Endpoint:** [gis.dhs.in.gov/arcgis/rest/services/Open/SchoolsOpen](https://gis.dhs.in.gov/arcgis/rest/services/Open/SchoolsOpen/FeatureServer/0)
    - **Source:** Indiana Department of Education (IDOE)
    - **Updates:** Each semester with rolling updates
    - **Coverage:** All Indiana public schools

    **Data Fields:**
    - School name, ID, and type
    - Corporation (district) affiliation
    - County and city location
    - Grade levels served
    - Current enrollment

    ---

    ## Additional Resources

    - [Indiana GPS Portal](https://indianagps.doe.in.gov) — Official GPS dashboard
    - [IDOE EdData](https://eddata.doe.in.gov) — Enrollment and finance data
    - [IDOE Data Exchange](https://www.in.gov/doe/it/link-initiative/data-exchange/) — Ed-Fi integration

    ---

    <p style="color: #666; font-size: 0.9rem;">
        VERA-IN v1.0 | Year Zero Edition | Built by <a href="https://hallucinations.cloud" style="color: {CRIMSON};">Hallucinations.cloud</a> |
        An <a href="https://h-edu.solutions" style="color: {CRIMSON};">H-EDU.Solutions</a> Initiative
    </p>
    """, unsafe_allow_html=True)
