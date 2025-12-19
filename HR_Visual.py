import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(
    page_title="Industry Workforce Business Analytics",
    layout="wide"
)

st.title("📊 Workforce Distribution Across Industries & Geographies")

# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv(
        r"D:\Sailaja\Guvi\AIML\Mini Project 6 - Resource Management\Industry_cluster.csv"
    )

data = load_data()

# -----------------------------
# Normalize column names
# -----------------------------
data.columns = data.columns.str.strip().str.replace(" ", "_")

# -----------------------------
# Identify Worker Columns
# -----------------------------
worker_cols = [c for c in data.columns if c.startswith(("Main_Workers", "Marginal_Workers"))]
id_cols = [c for c in data.columns if c not in worker_cols]

# -----------------------------
# Wide → Long
# -----------------------------
long_data = data.melt(
    id_vars=id_cols,
    value_vars=worker_cols,
    var_name="Variable",
    value_name="Count"
)

# -----------------------------
# Split Worker Metadata
# -----------------------------
split_cols = long_data["Variable"].str.split("-", expand=True)

long_data["Worker_Type"] = split_cols[0].replace({
    "Main_Workers": "Main",
    "Marginal_Workers": "Marginal"
})
long_data["Area"] = split_cols[1]
long_data["Gender"] = split_cols[2].replace({
    "Males": "Male",
    "Females": "Female",
    "Persons": "Total"
})

long_data.drop(columns="Variable", inplace=True)

# -----------------------------
# Convert Count to numeric
# -----------------------------
long_data["Count"] = pd.to_numeric(long_data["Count"], errors="coerce")
long_data = long_data.dropna(subset=["Count"])

# =============================
# Sidebar – Business Controls
# =============================
st.sidebar.header("🔍 Business Controls")

use_case = st.sidebar.selectbox(
    "Select Business Use Case",
    [
        "General Workforce Overview",
        "Industrial Investment Planning",
        "Skill Gap Analysis",
        "Gender & Inclusion Analysis",
        "Industry Dependency Risk",
        "Urbanization & Migration"
    ]
)

view_level = st.sidebar.radio("View Level", ["District-wise", "State-wise"])
show_percentage = st.sidebar.checkbox("Show Percentage")

# -----------------------------
# Geography Filters
# -----------------------------
states = sorted(long_data["State"].unique())

# ✅ Multiselect instead of selectbox, with Tamil Nadu as default
selected_states = st.sidebar.multiselect(
    "Select State(s)",
    options=states,
    default=["Tamilnadu"] if "Tamilnadu" in states else []
)

if view_level == "District-wise":
    districts = sorted(
        long_data.loc[long_data["State"].isin(selected_states), "District"]
        .dropna().unique()
    )
    selected_districts = st.sidebar.multiselect(
        "Select District(s)",
        options=districts,
        default=districts
    )
else:
    selected_districts = None

# -----------------------------
# Filter by Geography
# -----------------------------
filtered_data = long_data[long_data["State"].isin(selected_states)]

if selected_districts:
    filtered_data = filtered_data[
        filtered_data["District"].isin(selected_districts)
    ]

if filtered_data.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# -----------------------------
# Worker Filters
# -----------------------------
worker_type = st.sidebar.selectbox(
    "Worker Type", sorted(filtered_data["Worker_Type"].unique())
)
area = st.sidebar.selectbox(
    "Area", sorted(filtered_data["Area"].unique())
)
gender = st.sidebar.selectbox(
    "Gender", sorted(filtered_data["Gender"].unique())
)

filtered_data = filtered_data[
    (filtered_data["Worker_Type"] == worker_type) &
    (filtered_data["Area"] == area) &
    (filtered_data["Gender"] == gender)
]

# -----------------------------
# Industry Filter (district-aware)
# -----------------------------
industry_options = sorted(filtered_data["Industry_Category"].unique())
selected_clusters = st.sidebar.multiselect(
    "Select Industry",
    industry_options,
    default=industry_options
)
filtered_data = filtered_data[
    filtered_data["Industry_Category"].isin(selected_clusters)
]

# -----------------------------
# Percentage Handling
# -----------------------------
if show_percentage:
    total = filtered_data["Count"].sum()
    filtered_data["Value"] = (filtered_data["Count"] / total) * 100
    value_col = "Value"
    y_label = "Percentage (%)"
else:
    value_col = "Count"
    y_label = "Workers"

# =============================
# KPI Section
# =============================
st.subheader("📌 Key Workforce Indicators")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Workers", f"{filtered_data['Count'].sum():,.0f}")
col2.metric("Industries", filtered_data["Industry_Category"].nunique())
col3.metric("States", filtered_data["State"].nunique())
col4.metric("Districts", filtered_data["District"].nunique())

# =============================
# Core Visualizations
# =============================
st.subheader("🏭 Industry-wise Workforce")

industry_df = (
    filtered_data.groupby("Industry_Category")[value_col]
    .sum()
    .reset_index()
    .sort_values(value_col, ascending=False)
)

fig_industry = px.bar(
    industry_df,
    x="Industry_Category",
    y=value_col,
    text_auto=True,
    labels={value_col: y_label},
    title="Workforce by Industry"
)
st.plotly_chart(fig_industry, use_container_width=True)

geo_col = "District" if view_level == "District-wise" else "State"

geo_df = (
    filtered_data.groupby(geo_col)[value_col]
    .sum()
    .reset_index()
    .sort_values(value_col, ascending=False)
)

st.subheader("🌍 Geography-wise Workforce")

fig_geo = px.bar(
    geo_df,
    x=geo_col,
    y=value_col,
    text_auto=True,
    labels={value_col: y_label},
    title=f"Workforce by {geo_col}"
)
st.plotly_chart(fig_geo, use_container_width=True)

st.subheader("🔥 Industry vs Geography Heatmap")

pivot_df = filtered_data.pivot_table(
    values=value_col,
    index="Industry_Category",
    columns=geo_col,
    aggfunc="sum",
    fill_value=0
)

fig_heatmap = px.imshow(
    pivot_df,
    labels=dict(x=geo_col, y="Industry", color=y_label),
    title="Industry–Geography Workforce Intensity"
)

# ✅ Enlarge cells by increasing figure size
fig_heatmap.update_layout(
    autosize=False,
    width=1600,   # increase width
    height=900,   # increase height
    margin=dict(l=100, r=100, t=100, b=200),
    xaxis=dict(tickangle=45, tickfont=dict(size=12)),
    yaxis=dict(tickfont=dict(size=12))
)

st.plotly_chart(fig_heatmap, use_container_width=False)

# =============================
# Business Use Case Modules
# =============================

# 1️⃣ Industrial Investment Planning
if use_case == "Industrial Investment Planning":
    st.subheader("🏗️ Investment Opportunity Analysis")

    invest_df = (
        filtered_data.groupby("District")
        .agg(
            Total_Workers=("Count", "sum"),
            Industry_Count=("Industry_Category", "nunique")
        )
        .reset_index()
    )

    invest_df["Investment_Score"] = (
        invest_df["Total_Workers"] / invest_df["Industry_Count"]
    )

    st.dataframe(
        invest_df.sort_values("Investment_Score", ascending=False)
    )

    st.info(
        "Districts with high workforce and low industry saturation "
        "are ideal for new industrial investments."
    )

# 2️⃣ Skill Gap Analysis
elif use_case == "Skill Gap Analysis":
    st.subheader("🎓 Skill Gap Analysis")

    skill_df = (
        filtered_data.groupby(["District", "Industry_Category"])["Count"]
        .sum()
        .reset_index()
    )

    st.dataframe(skill_df)

    st.info(
        "High workforce but limited industry diversity indicates "
        "the need for skill development programs."
    )

# 3️⃣ Gender & Inclusion Analysis
elif use_case == "Gender & Inclusion Analysis":
    st.subheader("👩‍👩‍👧 Gender Participation Analysis")

    gender_df = (
        long_data[
            (long_data["State"].isin(selected_states)) &
            (long_data["Worker_Type"] == worker_type)
        ]
        .groupby(["Industry_Category", "Gender"])["Count"]
        .sum()
        .reset_index()
    )

    fig_gender = px.bar(
        gender_df,
        x="Industry_Category",
        y="Count",
        color="Gender",
        barmode="stack",
        title="Gender-wise Workforce Composition"
    )
    st.plotly_chart(fig_gender, use_container_width=True)

# 4️⃣ Industry Dependency Risk
elif use_case == "Industry Dependency Risk":
    st.subheader("⚠️ Industry Dependency Risk")

    dep_df = (
        filtered_data.groupby(["District", "Industry_Category"])["Count"]
        .sum()
        .reset_index()
    )

    dep_df["Share"] = dep_df.groupby("District")["Count"]\
                            .transform(lambda x: x / x.sum())

    risk_df = dep_df[dep_df["Share"] > 0.6]

    st.dataframe(risk_df)

    st.warning(
        "Districts heavily dependent on a single industry are "
        "economically vulnerable."
    )

# 5️⃣ Urbanization & Migration
elif use_case == "Urbanization & Migration":
    st.subheader("🏙️ Urban vs Rural Workforce")

    # ⚡ Use long_data filtered only by geography, NOT by Area
    ur_data = long_data[
        (long_data["State"].isin(selected_states)) &
        (long_data["Industry_Category"].isin(selected_clusters)) &
        (long_data["Worker_Type"] == worker_type) &
        (long_data["Gender"] == gender)
    ]

    if selected_districts:
        ur_data = ur_data[ur_data["District"].isin(selected_districts)]

    ur_df = (
        ur_data.groupby("Area")["Count"]
        .sum()
        .reset_index()
    )

    fig_ur = px.pie(
        ur_df,
        values="Count",
        names="Area",
        title="Urban vs Rural Workforce Distribution"
    )
    st.plotly_chart(fig_ur, use_container_width=True)

# =============================
# Download Data
# =============================
st.download_button(
    "⬇️ Download Filtered Data",
    filtered_data.to_csv(index=False),
    "filtered_workforce_data.csv",
    mime="text/csv"
)

# =============================
# Recommendations
# =============================
st.subheader("🧠 Business Recommendations")

recommendations = {
    "Industrial Investment Planning":
        "Promote industries in high-workforce, low-saturation districts.",
    "Skill Gap Analysis":
        "Launch targeted skill development programs aligned with local industries.",
    "Gender & Inclusion Analysis":
        "Introduce incentives to improve female workforce participation.",
    "Industry Dependency Risk":
        "Encourage industry diversification to reduce economic risk.",
    "Urbanization & Migration":
        "Strengthen rural employment to reduce migration pressure."
}

st.markdown(
    f"- **Key Recommendation:** {recommendations.get(use_case, 'Use filters to explore workforce patterns.')}"
)

st.info(
    "💡 This platform enables data-driven workforce planning, "
    "investment decisions, and inclusive policy formulation."
)
