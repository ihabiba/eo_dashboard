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
# MOCK DATA
# ──────────────────────────────────────────────────────────────

@st.cache_data
def load_hydro_data():
    return pd.DataFrame([
        {"zone_id":"H1","name":"Temenggor Reservoir","lat":5.416,"lon":101.303,"turbidity":0.28,"status":"normal","trend":"stable","depth_m":45.2,"ph":7.1},
        {"zone_id":"H2","name":"Kenyir Lake","lat":5.165,"lon":102.837,"turbidity":0.52,"status":"warning","trend":"rising","depth_m":38.7,"ph":6.8},
        {"zone_id":"H3","name":"Chenderoh Dam","lat":4.983,"lon":101.047,"turbidity":0.71,"status":"critical","trend":"rising","depth_m":32.1,"ph":6.5},
        {"zone_id":"H4","name":"Perak River Basin","lat":4.750,"lon":100.950,"turbidity":0.35,"status":"normal","trend":"falling","depth_m":41.0,"ph":7.0},
        {"zone_id":"H5","name":"Bersia Reservoir","lat":5.350,"lon":101.250,"turbidity":0.44,"status":"warning","trend":"rising","depth_m":36.5,"ph":6.9},
    ])

@st.cache_data
def load_agri_data():
    return pd.DataFrame([
        {"zone_id":"A1","name":"Kedah Rice Paddy – North","lat":6.120,"lon":100.370,"ndvi":0.72,"status":"normal","trend":"stable","crop_type":"Rice","area_ha":1200},
        {"zone_id":"A2","name":"Kedah Rice Paddy – South","lat":6.050,"lon":100.420,"ndvi":0.45,"status":"warning","trend":"falling","crop_type":"Rice","area_ha":850},
        {"zone_id":"A3","name":"Penang Palm Oil Estate","lat":5.280,"lon":100.450,"ndvi":0.38,"status":"critical","trend":"falling","crop_type":"Palm Oil","area_ha":2400},
        {"zone_id":"A4","name":"Perlis Sugarcane Field","lat":6.450,"lon":100.190,"ndvi":0.65,"status":"normal","trend":"rising","crop_type":"Sugarcane","area_ha":600},
        {"zone_id":"A5","name":"Perak Rubber Plantation","lat":4.590,"lon":101.090,"ndvi":0.51,"status":"warning","trend":"stable","crop_type":"Rubber","area_ha":1800},
        {"zone_id":"A6","name":"Kedah Durian Orchard","lat":5.950,"lon":100.550,"ndvi":0.33,"status":"critical","trend":"falling","crop_type":"Durian","area_ha":320},
    ])

@st.cache_data
def load_hydro_trends():
    return pd.DataFrame({"week":["Week 1","Week 2","Week 3","Week 4","Week 5","Week 6"],
        "Temenggor":[0.22,0.24,0.23,0.25,0.27,0.28],"Kenyir":[0.30,0.35,0.40,0.45,0.48,0.52],
        "Chenderoh":[0.35,0.42,0.51,0.58,0.65,0.71],"Perak Basin":[0.28,0.30,0.32,0.34,0.36,0.35],
        "Bersia":[0.31,0.33,0.36,0.38,0.40,0.44]})

@st.cache_data
def load_agri_trends():
    return pd.DataFrame({"week":["Week 1","Week 2","Week 3","Week 4","Week 5","Week 6"],
        "Kedah North":[0.75,0.74,0.73,0.73,0.72,0.72],"Kedah South":[0.60,0.57,0.53,0.50,0.47,0.45],
        "Penang Palm":[0.55,0.50,0.47,0.43,0.40,0.38],"Perlis":[0.58,0.60,0.61,0.63,0.64,0.65],
        "Perak Rubber":[0.54,0.53,0.52,0.52,0.51,0.51],"Durian Orchard":[0.50,0.47,0.44,0.40,0.36,0.33]})

def get_all_alerts(view):
    if view=="Hydro Reservoir":
        return [
            {"severity":"critical","status":"critical","zone":"Chenderoh Dam","time":"08:12","message":"Turbidity exceeded 0.70 — possible sediment discharge upstream. Immediate inspection recommended."},
            {"severity":"warning","status":"warning","zone":"Kenyir Lake","time":"08:05","message":"Turbidity rising for 4 consecutive weeks. Approaching critical threshold (0.60)."},
            {"severity":"warning","status":"warning","zone":"Bersia Reservoir","time":"08:05","message":"Turbidity at 0.44 and trending upward. Monitor closely for next satellite pass."},
        ]
    else:
        return [
            {"severity":"critical","status":"critical","zone":"Penang Palm Oil Estate","time":"08:12","message":"NDVI dropped below 0.40 — vegetation stress detected. Possible pest infestation or water deficit."},
            {"severity":"critical","status":"critical","zone":"Kedah Durian Orchard","time":"08:12","message":"NDVI at 0.33 — severe crop stress over 320 ha. Recommend ground inspection."},
            {"severity":"warning","status":"warning","zone":"Kedah Rice Paddy – South","time":"08:05","message":"NDVI declining for 4 consecutive weeks across 850 ha of rice cultivation."},
            {"severity":"warning","status":"warning","zone":"Perak Rubber Plantation","time":"08:05","message":"NDVI below optimal range (0.55) for rubber cultivation. 1,800 ha affected."},
        ]


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
                    Turbidity: <b style="color:{t['text1']}">{{turbidity}}</b> · pH: <b style="color:{t['text1']}">{{ph}}</b>
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>Depth: {{depth_m}}m</div>
                <div style='font-size:11px;color:{t['text4']};border-top:1px solid {t['border']};padding-top:6px;margin-top:4px;'>
                    Status: <b>{{status}}</b> · Trend: {{trend}}
                </div>
            </div>"""
    else:
        tooltip_html = f"""
            <div style='font-family:Inter,sans-serif;padding:12px 16px;max-width:260px;'>
                <div style='font-size:15px;font-weight:600;color:{t['text1']};margin-bottom:8px;'>{{name}}</div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>
                    NDVI: <b style="color:{t['text1']}">{{ndvi}}</b> · Area: <b style="color:{t['text1']}">{{area_ha}} ha</b>
                </div>
                <div style='font-size:12px;color:{t['text3']};margin-bottom:4px;'>Crop: {{crop_type}}</div>
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
    long_df      = tdf.melt(id_vars="week", var_name="Zone", value_name=vcol.upper())
    week_order   = tdf["week"].tolist()
    color_scale  = alt.Scale(range=[t['green'], t['amber'], t['red'], t['blue'], "#a78bfa", "#f472b6"])
    y_domain     = [0, 0.85] if vcol == "ndvi" else [0, 0.8]

    base = alt.Chart(long_df).encode(
        x=alt.X("week:N", sort=week_order, title=None,
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
            alt.Tooltip("week:N",           title="Week"),
            alt.Tooltip("Zone:N",           title="Zone"),
            alt.Tooltip(f"{vcol.upper()}:Q", title=vcol.upper(), format=".2f"),
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
f_alr=[a for a in get_all_alerts(view_choice) if a["status"] in active_st]


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
            dl=f"Depth: {r['depth_m']}m · pH: {r['ph']}" if vcol=="turbidity" else f"{r['crop_type']} · {r['area_ha']} ha"
            st.markdown(f"""<div class="zcard {s['card']}"><div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div><div class="zname"><span class="dot {s['dot']}"></span>{r['name']}</div><div class="zmeta">{dl}</div></div>
                <div style="text-align:right;"><div class="zval {s['color']}">{v}</div><div style="font-size:10px;color:{t['text4']};">{ta} {r['trend']}</div></div></div></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# TREND
# ══════════════════════════════════════════════════════════════

st.markdown("")
st.markdown(f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span class="panel-label" style="margin:0;">TREND: {mname} — 6 Weeks</span><span class="note-box">{tnote}</span></div>""", unsafe_allow_html=True)
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