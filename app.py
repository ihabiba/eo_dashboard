import streamlit as st
import pandas as pd
import pydeck as pdk

# page config
st.set_page_config(layout="wide")

# title
st.title("EO Monitoring Dashboard")

st.markdown("---")

# mock data
data = pd.DataFrame({
    "location": ["Zone A", "Zone B"],
    "lat": [3.12, 3.15],
    "lon": [101.65, 101.68],
    "ndvi": [0.62, 0.40],
    "turbidity": [0.31, 0.60]
})

# classify ndvi
def classify_ndvi(value):
    if value < 0.4:
        return "critical"
    elif value < 0.5:
        return "warning"
    else:
        return "normal"

# classify turbidity
def classify_turbidity(value):
    if value > 0.5:
        return "critical"
    elif value > 0.4:
        return "warning"
    else:
        return "normal"

data["ndvi_status"] = data["ndvi"].apply(classify_ndvi)
data["turbidity_status"] = data["turbidity"].apply(classify_turbidity)

# combined status
def get_status(row):
    if "critical" in [row["ndvi_status"], row["turbidity_status"]]:
        return "critical"
    elif "warning" in [row["ndvi_status"], row["turbidity_status"]]:
        return "warning"
    else:
        return "normal"

data["status"] = data.apply(get_status, axis=1)

# SIDEBAR
st.sidebar.header("Filters")

selected_status = st.sidebar.multiselect(
    "Filter by Status",
    options=["normal", "warning", "critical"],
    default=["normal", "warning", "critical"]
)

filtered_data = data[data["status"].isin(selected_status)]

# KPIs
st.subheader("Overview")

col1, col2, col3 = st.columns(3)

avg_ndvi = round(filtered_data["ndvi"].mean(), 2) if not filtered_data.empty else 0
avg_turbidity = round(filtered_data["turbidity"].mean(), 2) if not filtered_data.empty else 0

alerts_count = (filtered_data["status"] != "normal").sum()

col1.metric("🌱 Avg NDVI", avg_ndvi)
col2.metric("💧 Avg Turbidity", avg_turbidity)
col3.metric("⚠️ Alerts", alerts_count)

st.markdown("---")

# MAP
st.subheader("Map Overview")

def get_color(row):
    if row["status"] == "critical":
        return [255, 0, 0, 180]
    elif row["status"] == "warning":
        return [255, 165, 0, 160]
    else:
        return [0, 200, 0, 140]

def get_radius(row):
    if row["status"] == "critical":
        return 500
    elif row["status"] == "warning":
        return 300
    else:
        return 200

filtered_data["color"] = filtered_data.apply(get_color, axis=1)
filtered_data["radius"] = filtered_data.apply(get_radius, axis=1)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered_data,
    get_position='[lon, lat]',
    get_color='color',
    get_radius='radius',
    pickable=True,
)

tooltip = {
    "html": "<b>{location}</b><br/>Status: {status}<br/>NDVI: {ndvi}<br/>Turbidity: {turbidity}",
    "style": {"color": "white"}
}

st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9",
    initial_view_state=pdk.ViewState(
        latitude=data["lat"].mean(),
        longitude=data["lon"].mean(),
        zoom=11,
        pitch=0,
    ),
    layers=[layer],
    tooltip=tooltip
))

st.markdown("---")

# CHARTS
col1, col2 = st.columns(2)

chart_data_ndvi = pd.DataFrame({
    "ndvi": [0.5, 0.55, 0.52, 0.51]
})

chart_data_turbidity = pd.DataFrame({
    "turbidity": [0.3, 0.35, 0.45, 0.60]
})

with col1:
    st.subheader("NDVI Trend")
    st.line_chart(chart_data_ndvi)

with col2:
    st.subheader("Turbidity Trend")
    st.line_chart(chart_data_turbidity)

st.markdown("---")

# ALERTS
st.subheader("Alerts")

for _, row in filtered_data.iterrows():
    if row["status"] == "critical":
        st.error(f"{row['location']}: Critical condition detected")
    elif row["status"] == "warning":
        st.warning(f"{row['location']}: Warning condition detected")

if alerts_count == 0:
    st.success("All areas normal")