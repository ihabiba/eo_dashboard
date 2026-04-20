"""
EO Monitoring Dashboard — NextGen Spark
Sentinel-2 Analytics | Hydro Reservoir & Agriculture Monitoring
Built with Streamlit — Prototype v1.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import altair as alt
import datetime
import json

from utils.theme import DARK, LIGHT
from utils.styles import get_css

# ──────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EO Monitoring Dashboard",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# THEME SYSTEM
# ──────────────────────────────────────────────────────────────
# Colors live in utils/theme.py — imported at the top of this file.
# Theme selection in sidebar (before other sidebar content)
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">
        <div style="width:34px;height:34px;border-radius:10px;
            background:linear-gradient(135deg,#4f8df5,#34d399);
            display:flex;align-items:center;justify-content:center;
            font-size:13px;font-weight:700;color:#fff;
            box-shadow:0 3px 10px rgba(79,141,245,0.25);">NS</div>
        <div>
            <div style="font-size:14px;font-weight:600;" class="sb-header-title">Control Panel</div>
            <div style="font-size:10px;color:#94a3b8;">NextGen Spark EO</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    theme_choice = st.radio("Theme", ["Dark", "Light"], horizontal=True,
                            label_visibility="collapsed")

t = DARK if theme_choice == "Dark" else LIGHT

# ──────────────────────────────────────────────────────────────
# DYNAMIC CSS
# ──────────────────────────────────────────────────────────────
st.markdown(get_css(t, theme_choice), unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
# REAL DATA — CSV + GeoJSON from Nawran
# ──────────────────────────────────────────────────────────────

@st.cache_data
def load_zone_metadata():
    """Extract centroid lat/lon from GeoJSON polygons."""
    with open("data/zones.geojson") as f:
        geojson = json.load(f)
    zones = {}
    for feature in geojson["features"]:
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"][0]
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        zones[props["name"]] = {
            "lat": sum(lats) / len(lats),
            "lon": sum(lons) / len(lons),
            "zone_id": props.get("zone_id", ""),
        }
    return zones

@st.cache_data
def load_raw_csv():
    return pd.read_csv("data/eo_monitoring_output.csv", parse_dates=["date"])

def compute_trend(sorted_series):
    """Compare last two readings to determine direction."""
    if len(sorted_series) < 2:
        return "stable"
    prev, curr = sorted_series.iloc[-2], sorted_series.iloc[-1]
    if curr > prev + 0.01:
        return "rising"
    elif curr < prev - 0.01:
        return "falling"
    return "stable"

@st.cache_data
def load_hydro_data():
    df = load_raw_csv()
    zones = load_zone_metadata()
    hydro = df[df["use_case"] == "Hydro monitoring"].copy()
    result = []
    for zone_name, group in hydro.groupby("zone"):
        if zone_name not in zones:
            continue
        group = group.sort_values("date")
        latest = group.iloc[-1]
        result.append({
            "zone_id": zones[zone_name]["zone_id"],
            "name": zone_name,
            "lat": zones[zone_name]["lat"],
            "lon": zones[zone_name]["lon"],
            "turbidity": round(latest["NDTI_mean"], 4),
            "status": latest["alert_level"],
            "trend": compute_trend(group["NDTI_mean"]),
            "ndwi": round(latest["NDWI_mean"], 4),
            "ndti_min": round(latest["NDTI_min"], 4),
            "ndti_max": round(latest["NDTI_max"], 4),
        })
    return pd.DataFrame(result)

@st.cache_data
def load_agri_data():
    df = load_raw_csv()
    zones = load_zone_metadata()
    agri = df[df["use_case"] == "Agriculture monitoring"].copy()
    result = []
    for zone_name, group in agri.groupby("zone"):
        if zone_name not in zones:
            continue
        group = group.sort_values("date")
        latest = group.iloc[-1]
        result.append({
            "zone_id": zones[zone_name]["zone_id"],
            "name": zone_name,
            "lat": zones[zone_name]["lat"],
            "lon": zones[zone_name]["lon"],
            "ndvi": round(latest["NDVI_mean"], 4),
            "status": latest["alert_level"],
            "trend": compute_trend(group["NDVI_mean"]),
            "ndre": round(latest["NDRE_mean"], 4),
            "ndvi_min": round(latest["NDVI_min"], 4),
            "ndvi_max": round(latest["NDVI_max"], 4),
        })
    return pd.DataFrame(result)

@st.cache_data
def load_hydro_trends():
    df = load_raw_csv()
    hydro = df[df["use_case"] == "Hydro monitoring"][["date","zone","NDTI_mean"]].copy()
    pivot = hydro.pivot(index="date", columns="zone", values="NDTI_mean")
    pivot = pivot.sort_index().reset_index()
    pivot.columns.name = None
    pivot["date"] = pivot["date"].dt.strftime("%d %b %Y")
    return pivot

@st.cache_data
def load_agri_trends():
    df = load_raw_csv()
    agri = df[df["use_case"] == "Agriculture monitoring"][["date","zone","NDVI_mean"]].copy()
    pivot = agri.pivot(index="date", columns="zone", values="NDVI_mean")
    pivot = pivot.sort_index().reset_index()
    pivot.columns.name = None
    pivot["date"] = pivot["date"].dt.strftime("%d %b %Y")
    return pivot

def get_all_alerts(zone_df, vcol):
    alerts = []
    time_str = datetime.datetime.now().strftime("%H:%M")
    non_normal = zone_df[zone_df["status"] != "normal"].copy()
    order = {"critical": 0, "warning": 1}
    non_normal = non_normal.assign(_o=non_normal["status"].map(order)).sort_values("_o")
    for _, row in non_normal.iterrows():
        val = row[vcol]
        if vcol == "turbidity":
            msg = (f"NDTI at {val} — turbidity critical. Immediate inspection recommended."
                   if row["status"] == "critical"
                   else f"NDTI at {val} — turbidity elevated. Monitor closely for next satellite pass.")
        else:
            msg = (f"NDVI at {val} — severe vegetation stress detected. Ground inspection recommended."
                   if row["status"] == "critical"
                   else f"NDVI at {val} — vegetation health below optimal. Monitor closely.")
        alerts.append({"severity": row["status"], "status": row["status"],
                        "zone": row["name"], "time": time_str, "message": msg})
    return alerts


# ──────────────────────────────────────────────────────────────
# MAP
# ──────────────────────────────────────────────────────────────

def build_map(df, vcol):
    map_df = df.copy()

    # pydeck needs colors as (R, G, B, Alpha) tuples, not hex
    color_map = {
        "critical": (int(t['red'][1:3],16),   int(t['red'][3:5],16),   int(t['red'][5:7],16),   210),
        "warning":  (int(t['amber'][1:3],16),  int(t['amber'][3:5],16), int(t['amber'][5:7],16), 190),
        "normal":   (int(t['green'][1:3],16),  int(t['green'][3:5],16), int(t['green'][5:7],16), 180),
    }
    radius_map = {"critical": 6000, "warning": 4500, "normal": 3000}

    map_df["r"]      = map_df["status"].map(lambda s: color_map[s][0])
    map_df["g"]      = map_df["status"].map(lambda s: color_map[s][1])
    map_df["b"]      = map_df["status"].map(lambda s: color_map[s][2])
    map_df["a"]      = map_df["status"].map(lambda s: color_map[s][3])
    map_df["radius"] = map_df["status"].map(radius_map)

    if vcol == "turbidity":
        tooltip_html = f"""
            <div style='font-family:Inter,sans-serif;padding:12px 16px;max-width:260px;'>
                <div style='font-size:15px;font-weight:600;color:{t['text1']};margin-bottom:8px;'>{{name}}</div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    NDTI: <b style="color:{t['text1']}">{{turbidity}}</b>
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    Range: {{ndti_min}} to {{ndti_max}}
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>NDWI: {{ndwi}}</div>
                <div style='font-size:11px;color:{t['text4']};border-top:1px solid {t['border']};padding-top:6px;margin-top:4px;'>
                    Status: <b>{{status}}</b> · Trend: {{trend}}
                </div>
            </div>"""
    else:
        tooltip_html = f"""
            <div style='font-family:Inter,sans-serif;padding:12px 16px;max-width:260px;'>
                <div style='font-size:15px;font-weight:600;color:{t['text1']};margin-bottom:8px;'>{{name}}</div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    NDVI: <b style="color:{t['text1']}">{{ndvi}}</b>
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    Range: {{ndvi_min}} to {{ndvi_max}}
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>NDRE: {{ndre}}</div>
                <div style='font-size:11px;color:{t['text4']};border-top:1px solid {t['border']};padding-top:6px;margin-top:4px;'>
                    Status: <b>{{status}}</b> · Trend: {{trend}}
                </div>
            </div>"""

    layers = []
    critical_df = map_df[map_df["status"] == "critical"].copy()
    if not critical_df.empty:
        critical_df["glow_radius"] = critical_df["radius"] * 2.5
        layers.append(pdk.Layer(
            "ScatterplotLayer", data=critical_df,
            get_position=["lon", "lat"],
            get_color=[color_map["critical"][0], color_map["critical"][1], color_map["critical"][2], 30],
            get_radius="glow_radius", pickable=False,
        ))
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=map_df,
        get_position=["lon", "lat"],
        get_color=["r", "g", "b", "a"],
        get_radius="radius", pickable=True,
        auto_highlight=True, highlight_color=[255, 255, 255, 50],
    ))

    view_state = pdk.ViewState(
        latitude=float(map_df["lat"].mean()),
        longitude=float(map_df["lon"].mean()),
        zoom=7.2 if vcol == "turbidity" else 7.5,
        pitch=0,
    )
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": tooltip_html,
            "style": {
                "backgroundColor": t['tooltip_bg'],
                "border": f"1px solid {t['tooltip_bdr']}",
                "borderRadius": "12px",
                "color": t['text1'],
                "boxShadow": "0 8px 24px rgba(0,0,0,0.15)",
            },
        },
        map_style=t['map_style'],
    )


# ──────────────────────────────────────────────────────────────
# ALTAIR CHART
# ──────────────────────────────────────────────────────────────

def build_trend_chart(tdf, vcol):
    long_df      = tdf.melt(id_vars="date", var_name="Zone", value_name=vcol.upper())
    date_order   = tdf["date"].tolist()
    color_scale  = alt.Scale(range=[t['green'], t['amber'], t['red'], t['blue'], "#a78bfa", "#f472b6"])
    y_domain     = [0, 0.85] if vcol == "ndvi" else [0, 0.8]

    base = alt.Chart(long_df).encode(
        x=alt.X("date:N", sort=date_order, title=None,
            axis=alt.Axis(labelColor=t['text4'], labelFontSize=11, labelFont="Inter",
                          tickColor="transparent", domainColor=t['border'],
                          labelAngle=0, labelPadding=10)),
        y=alt.Y(f"{vcol.upper()}:Q", scale=alt.Scale(domain=y_domain), title=None,
            axis=alt.Axis(labelColor=t['text4'], labelFontSize=10, labelFont="JetBrains Mono",
                          gridColor=t['chart_grid'], tickColor="transparent", domainColor="transparent")),
        color=alt.Color("Zone:N", scale=color_scale, title="Zone",
            legend=alt.Legend(orient="bottom", columns=3, labelColor=t['text3'],
                              labelFontSize=11, labelFont="Inter", titleColor=t['text4'],
                              titleFontSize=10, symbolSize=60)),
    )
    lines  = base.mark_line(strokeWidth=2.5, opacity=0.9)
    points = base.mark_circle(size=50, opacity=1).encode(
        tooltip=[
            alt.Tooltip("date:N",            title="Date"),
            alt.Tooltip("Zone:N",            title="Zone"),
            alt.Tooltip(f"{vcol.upper()}:Q", title=vcol.upper(), format=".4f"),
        ]
    )
    return (lines + points).properties(height=300, background="transparent") \
                           .configure(font="Inter") \
                           .configure_view(strokeWidth=0)


# ══════════════════════════════════════════════════════════════
# REST OF SIDEBAR
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("---")
    st.markdown(f'<p class="sb-label">Monitoring Module</p>', unsafe_allow_html=True)
    view_choice = st.radio("Module", ["Hydro Reservoir","Agriculture"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f'<p class="sb-label">Status Filter</p>', unsafe_allow_html=True)
    s_n=st.checkbox("Normal",value=True)
    s_w=st.checkbox("Warning",value=True)
    s_c=st.checkbox("Critical",value=True)
    active_st=[]
    if s_n: active_st.append("normal")
    if s_w: active_st.append("warning")
    if s_c: active_st.append("critical")

    st.markdown("---")
    st.markdown(f'<p class="sb-label">Threshold Reference</p>', unsafe_allow_html=True)
    if view_choice=="Hydro Reservoir":
        st.markdown(f"""<div style="font-size:11px;line-height:2.2;color:{t['sb_text']};">
            <span style="color:{t['green']};">●</span> Normal: Turbidity &lt; 0.40<br>
            <span style="color:{t['amber']};">●</span> Warning: 0.40 – 0.60<br>
            <span style="color:{t['red']};">●</span> Critical: &gt; 0.60</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="font-size:11px;line-height:2.2;color:{t['sb_text']};">
            <span style="color:{t['green']};">●</span> Normal: NDVI &gt; 0.55<br>
            <span style="color:{t['amber']};">●</span> Warning: 0.40 – 0.55<br>
            <span style="color:{t['red']};">●</span> Critical: &lt; 0.40</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"""<div style="font-size:10px;color:{t['text4']};line-height:1.7;padding-top:6px;">
        <strong style="color:{t['text3']};">Data Source:</strong> Sentinel-2 L2A<br>
        <strong style="color:{t['text3']};">Revisit:</strong> 5-day cycle<br>
        <strong style="color:{t['text3']};">Processing:</strong> Google Earth Engine<br>
        <strong style="color:{t['text3']};">Version:</strong> Prototype v1.0</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# LOAD & FILTER
# ══════════════════════════════════════════════════════════════

if view_choice=="Hydro Reservoir":
    all_z=load_hydro_data(); tdf=load_hydro_trends(); vcol="turbidity"; mname="Turbidity"; tnote="Higher = worse water quality"
else:
    all_z=load_agri_data(); tdf=load_agri_trends(); vcol="ndvi"; mname="NDVI"; tnote="Lower = vegetation stress"

filt=all_z[all_z["status"].isin(active_st)].copy()
tot=len(all_z); ft=len(filt)
nc=len(filt[filt["status"]=="critical"]); nw=len(filt[filt["status"]=="warning"]); nn=len(filt[filt["status"]=="normal"])
av=round(filt[vcol].mean(),2) if not filt.empty else 0
f_alr=[a for a in get_all_alerts(all_z, vcol) if a["status"] in active_st]


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════

h1,h2=st.columns([3,1])
with h1:
    st.markdown(f"""<div class="dash-header"><div class="dash-logo">NS</div><div>
        <p class="dash-title">EO Monitoring Dashboard</p>
        <p class="dash-sub">NextGen Spark — Sentinel-2 Analytics Platform</p></div></div>""", unsafe_allow_html=True)
with h2:
    st.markdown(f"""<div style="display:flex;justify-content:flex-end;align-items:center;gap:14px;padding-top:16px;">
        <span class="meta-tag">Last update: {datetime.datetime.now().strftime("%d %b %Y, %H:%M")}</span>
        <span class="live-pill"><span class="live-dot-anim"></span>LIVE</span></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════

sub_lbl="NDTI Index" if vcol=="turbidity" else "Vegetation Index"
cb='<span class="kpi-tag tag-red">Immediate attention</span>' if nc>0 else '<span class="kpi-tag tag-green">All clear</span>'
wb='<span class="kpi-tag tag-amber">Under observation</span>' if nw>0 else '<span class="kpi-tag tag-green">All clear</span>'

st.markdown(f"""
<div class="kpi-row">
    <div class="kpi"><div class="kpi-accent" style="background:linear-gradient(90deg,{t['blue']},{t['green']});"></div>
        <div class="kpi-label">Avg {mname}</div><div class="kpi-val">{av}</div><span class="kpi-tag tag-blue">{sub_lbl}</span></div>
    <div class="kpi {'kpi-glow' if nc>0 else ''}"><div class="kpi-accent" style="background:{t['red']};"></div>
        <div class="kpi-label">Critical Zones</div><div class="kpi-val">{nc}</div>{cb}</div>
    <div class="kpi"><div class="kpi-accent" style="background:{t['amber']};"></div>
        <div class="kpi-label">Warning Zones</div><div class="kpi-val">{nw}</div>{wb}</div>
    <div class="kpi"><div class="kpi-accent" style="background:{t['green']};"></div>
        <div class="kpi-label">Normal Zones</div><div class="kpi-val">{nn}</div><span class="kpi-tag tag-green">Within safe range</span></div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# MAP + ZONES
# ══════════════════════════════════════════════════════════════

mc,dc=st.columns([2,1])
with mc:
    ml="Reservoir Locations — Peninsular Malaysia" if vcol=="turbidity" else "Agricultural Zones — Northern Malaysia"
    st.markdown(f"""<div class="panel" style="margin-bottom:0;overflow:hidden;"><div class="panel-head">
        <span class="panel-label">MAP: {ml}</span><span class="meta-tag">Sentinel-2 L2A</span></div></div>""", unsafe_allow_html=True)
    if not filt.empty:
        st.pydeck_chart(build_map(filt,vcol),height=520)
    else:
        st.markdown(f"""<div style="height:520px;display:flex;align-items:center;justify-content:center;
            background:{t['bg_card']};border:1px solid {t['border']};border-top:none;border-radius:0 0 14px 14px;">
            <span style="color:{t['text4']};font-size:13px;">No zones match the current filter</span></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="display:flex;gap:24px;justify-content:center;margin-top:10px;">
        <div style="display:flex;align-items:center;gap:6px;"><span class="dot dot-g"></span><span style="font-size:11px;color:{t['text3']};">Normal</span></div>
        <div style="display:flex;align-items:center;gap:6px;"><span class="dot dot-y"></span><span style="font-size:11px;color:{t['text3']};">Warning</span></div>
        <div style="display:flex;align-items:center;gap:6px;"><span class="dot dot-r"></span><span style="font-size:11px;color:{t['text3']};">Critical</span></div>
    </div>""", unsafe_allow_html=True)

with dc:
    st.markdown(f"""<div class="panel"><div class="panel-body"><div class="panel-label" style="margin-bottom:16px;">DISTRIBUTION: Zone Health</div>""", unsafe_allow_html=True)
    for lb,cnt,ch in [("Normal",nn,t['green']),("Warning",nw,t['amber']),("Critical",nc,t['red'])]:
        pc=round((cnt/tot)*100) if tot>0 else 0
        st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:12.5px;color:{t['text2']};">{lb}</span>
            <span style="font-size:12.5px;color:{ch};font-weight:600;font-family:'JetBrains Mono',monospace;">{cnt} <span style="color:{t['text4']};font-weight:400;">({pc}%)</span></span></div>
        <div class="dbar-track"><div class="dbar-fill" style="width:{pc}%;background:{ch};"></div></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="border-top:1px solid {t['border']};padding-top:14px;margin-top:4px;display:flex;justify-content:space-between;align-items:center;">
            <span style="font-size:11px;color:{t['text4']};">Showing / Total</span>
            <span style="font-size:24px;font-weight:800;color:{t['text1']};font-family:'JetBrains Mono',monospace;">{ft}<span style="font-size:14px;color:{t['text4']};font-weight:400;">/{tot}</span></span>
        </div></div></div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f'<p class="sb-label" style="margin-top:8px;">Zone Details</p>', unsafe_allow_html=True)
    if filt.empty:
        st.markdown(f'<div style="color:{t["text4"]};font-size:12px;padding:12px 0;">No zones to display</div>', unsafe_allow_html=True)
    else:
        STATUS = {
            "critical": {"card": "zcard-crit", "color": "c-r", "dot": "dot-r"},
            "warning":  {"card": "zcard-warn", "color": "c-y", "dot": "dot-y"},
            "normal":   {"card": "",            "color": "c-g", "dot": "dot-g"},
        }
        for _, r in filt.iterrows():
            s  = STATUS[r["status"]]
            v  = r[vcol]
            ta={"rising":"↑","falling":"↓"}.get(r["trend"],"→")
            dl=f"NDWI: {r['ndwi']}" if vcol=="turbidity" else f"NDRE: {r['ndre']}"
            st.markdown(f"""<div class="zcard {s['card']}"><div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div><div class="zname"><span class="dot {s['dot']}"></span>{r['name']}</div><div class="zmeta">{dl}</div></div>
                <div style="text-align:right;"><div class="zval {s['color']}">{v}</div><div style="font-size:10px;color:{t['text4']};">{ta} {r['trend']}</div></div></div></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TREND
# ══════════════════════════════════════════════════════════════

st.markdown("")
st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span class="panel-label" style="margin:0;">TREND: {mname} — Historical Readings</span><span class="note-box">{tnote}</span></div>""", unsafe_allow_html=True)
st.altair_chart(build_trend_chart(tdf,vcol), use_container_width=True)


# ══════════════════════════════════════════════════════════════
# ALERTS
# ══════════════════════════════════════════════════════════════

st.markdown("")
fc=[a for a in f_alr if a["severity"]=="critical"]
ah=f"ALERTS: Active ({len(f_alr)})"
if fc: ah+=f" · {len(fc)} critical"
st.markdown(f"""<div class="panel" style="overflow:hidden;"><div class="panel-head">
    <span class="panel-label">{ah}</span><span class="meta-tag">Today, {datetime.datetime.now().strftime("%d %b %Y")}</span></div>""", unsafe_allow_html=True)
if f_alr:
    for a in f_alr:
        ac = "alrt-crit" if a["severity"] == "critical" else "alrt-warn"
        st.markdown(f"""<div class="alrt {ac}"><div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="alrt-zone">{a['zone']}</span><span class="alrt-time">{a['time']}</span></div>
            <div class="alrt-msg">{a['message']}</div></div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""<div style="padding:28px;text-align:center;color:{t['text4']};font-size:12px;">No alerts for the current filter</div>""", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════

st.markdown("")
st.markdown(f"""<div style="text-align:center;padding:24px 0 16px;border-top:1px solid {t['border']};margin-top:24px;">
    <span style="font-size:11px;color:{t['text4']};">NextGen Spark Sdn Bhd · EO Monitoring Prototype v1.0 · Powered by Sentinel-2 & Google Earth Engine</span></div>""", unsafe_allow_html=True)