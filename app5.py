import os
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from scipy.interpolate import griddata

# ============================================================
# CONSTANTS & GLOBAL COLORBAR SETTINGS (-85 to -55 dBm)
# ============================================================
APP_BUILD = "ALL-3D-WHITE-v7-2026-11-10"

RSSI_MIN = -85.0
RSSI_MAX = -55.0
COLORSCALE_NAME = "Jet"
TICK_VALS = [-85, -80, -75, -70, -65, -60, -55]

# ============================================================
# FORCE ALL PLOTLY 3D CHARTS TO LIGHT / WHITE
# ============================================================
def force_white_3d(fig):
    """Remove dark Plotly/Streamlit styling from every 3D scene."""
    axis_style = dict(
        backgroundcolor="#FFFFFF",
        showbackground=True,
        gridcolor="#CBD5E1",
        zerolinecolor="#94A3B8",
        linecolor="#64748B",
        color="#111827",
        tickfont=dict(color="#111827"),
        title_font=dict(color="#111827"),
        showgrid=True,
        zeroline=True,
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#111827"),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font_color="#111827",
            bordercolor="#CBD5E1",
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.94)",
            bordercolor="#D1D5DB",
            borderwidth=1,
            font=dict(color="#111827"),
        ),
        scene=dict(
            bgcolor="#FFFFFF",
            xaxis=axis_style,
            yaxis=axis_style,
            zaxis=axis_style,
        ),
    )

    for trace in fig.data:
        try:
            if getattr(trace, "colorbar", None) is not None:
                trace.colorbar.tickfont = dict(color="#111827")
                trace.colorbar.title.font = dict(color="#111827")
        except Exception:
            pass
    return fig


# ============================================================
# PAGE CONFIG & STYLES
# ============================================================
st.set_page_config(
    page_title="Portable Wireless Site Survey and Network Analysis System",
    page_icon="📡",
    layout="wide"
)

st.markdown("""
<style>
div[data-testid="stPlotlyChart"],
div[data-testid="stPlotlyChart"] > div {
    background: #FFFFFF !important;
}
.block-container {
    padding-top: 3.5rem !important;
    padding-bottom: 3rem;
    max-width: 1500px;
}
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,0.18);
}
[data-testid="stMetric"] {
    padding: 14px 16px;
    border-radius: 16px;
    border: 1px solid rgba(128,128,128,0.18);
    background: rgba(128,128,128,0.035);
}
.dashboard-title {
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.3;
    margin-top: 0.5rem;
    margin-bottom: 6px;
    background: linear-gradient(90deg, #60a5fa, #22c55e);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.dashboard-subtitle {
    font-size: 1rem;
    font-weight: 400;
    opacity: 0.80;
    margin-bottom: 1.3rem;
}
.room-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(59,130,246,0.12);
    border: 1px solid rgba(59,130,246,0.32);
    font-weight: 700;
    margin: 3px 0 12px 0;
}
.recommend-card {
    padding: 22px 24px;
    border-radius: 18px;
    border: 1px solid rgba(34,197,94,0.35);
    background: linear-gradient(135deg, rgba(34,197,94,0.13), rgba(59,130,246,0.08));
    margin: 10px 0 18px 0;
}
.recommend-label {
    font-size: 0.82rem;
    opacity: 0.72;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.recommend-wifi {
    font-size: 1.85rem;
    font-weight: 800;
    margin-top: 4px;
}
.recommend-rssi {
    font-size: 1rem;
    margin-top: 5px;
}
button[data-baseweb="tab"] {
    font-weight: 650;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# ROOM CONFIGURATION
# ============================================================
ROOMS = {
    "Room A": {"file": None, "x": 7.20, "y": 8.40},
    "Room B": {"file": "room_B_wifi_data.csv", "x": 6.80, "y": 9.00},
    "Room C": {"file": "room_C_wifi_data.csv", "x": 2.70, "y": 9.00},
    "Room 1": {"file": "room_1_wifi_data.csv", "x": 3.535, "y": 4.13},
    "Room 2": {"file": "room_2_wifi_data.csv", "x": 3.57, "y": 5.47},
    "Room 3": {"file": "room_A3_wifi_data.csv", "x": 3.535, "y": 4.20},
    "Room 4": {"file": "room_A4_wifi_data.csv", "x": 3.57, "y": 2.83}
}

WALL_HEIGHT = 3.0
AP_HEIGHT = 4.0

# ============================================================
# LOAD DATA FUNCTION
# ============================================================
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file, skipinitialspace=True)
        elif uploaded_file.name.lower().endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            return None

        df.columns = df.columns.astype(str).str.strip()
        header_aliases = {
            "point id": "Point", "point": "Point",
            "x (m)": "X", "x": "X",
            "y (m)": "Y", "y": "Y",
            "rssi (dbm)": "RSSI", "rssi_dbm": "RSSI", "rssi": "RSSI",
            "frequency (mhz)": "Frequency", "frequency": "Frequency",
            "channel": "Channel", "ssid": "SSID", "bssid": "BSSID",
            "band": "Band", "security": "Security",
        }
        df.rename(columns={col: header_aliases.get(col.lower(), col) for col in df.columns}, inplace=True)

        required_columns = ["Point", "X", "Y", "SSID", "RSSI"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error("❌ ไม่พบ Column ที่จำเป็น: " + ", ".join(missing_columns))
            return pd.DataFrame()

        if "BSSID" not in df.columns:
            df["BSSID"] = df["SSID"].astype(str).str.strip()
        else:
            missing_bssid = df["BSSID"].isna() | df["BSSID"].astype(str).str.strip().eq("")
            df.loc[missing_bssid, "BSSID"] = df.loc[missing_bssid, "SSID"].astype(str).str.strip()

        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
        df["RSSI"] = pd.to_numeric(df["RSSI"], errors="coerce")
        if "Channel" in df.columns:
            df["Channel"] = pd.to_numeric(df["Channel"], errors="coerce")

        df = df.dropna(subset=["X", "Y", "RSSI"]).copy()
        return df
    except Exception as e:
        st.error(f"❌ ไม่สามารถอ่านไฟล์ได้: {e}")
        return pd.DataFrame()


ROOM_B_EMBEDDED_CSV = 'Point,X,Y,SSID,BSSID,RSSI,Channel,Frequency,Band,Security\nP01,0,0,KMITL-WIFI,00:2E:C7:90:94:61,-73,11,2462,2.4GHz,OPEN\nP02,1.7,0,KMITL-WIFI,00:2E:C7:90:94:61,-71,11,2462,2.4GHz,OPEN\nP03,3.4,0,KMITL-WIFI,00:2E:C7:90:94:61,-61,11,2462,2.4GHz,OPEN\nP04,5.1,0,KMITL-WIFI,00:2E:C7:90:94:61,-58,11,2462,2.4GHz,OPEN\nP05,6.8,0,KMITL-WIFI,00:2E:C7:90:94:61,-68,11,2462,2.4GHz,OPEN\nP06,0,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-73,11,2462,2.4GHz,OPEN\nP07,1.7,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-64,11,2462,2.4GHz,OPEN\nP08,3.4,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP09,5.1,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP10,6.8,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-61,11,2462,2.4GHz,OPEN\nP11,0,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-67,11,2462,2.4GHz,OPEN\nP12,1.7,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-65,11,2462,2.4GHz,OPEN\nP13,3.4,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-64,11,2462,2.4GHz,OPEN\nP14,5.1,3.6,KMITL-Legacy,00:2E:C7:90:94:60,-64,11,2462,2.4GHz,WPA2-ENT\nP15,6.8,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-66,11,2462,2.4GHz,OPEN\nP16,0,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-61,11,2462,2.4GHz,OPEN\nP17,1.7,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-56,11,2462,2.4GHz,OPEN\nP18,3.4,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP19,5.1,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-59,11,2462,2.4GHz,OPEN\nP20,6.8,5.4,KMITL-Legacy,00:2E:C7:90:94:60,-68,11,2462,2.4GHz,WPA2-ENT\nP21,0,7.2,KMITL-WIFI,00:2E:C7:90:94:61,-59,11,2462,2.4GHz,OPEN\nP22,1.7,7.2,KMITL-Legacy,00:2E:C7:90:94:60,-60,11,2462,2.4GHz,WPA2-ENT\nP23,3.4,7.2,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP24,5.1,7.2,KMITL-WIFI,00:2E:C7:90:94:61,-63,11,2462,2.4GHz,OPEN\nP25,6.8,7.2,KMITL-Legacy,00:2E:C7:90:94:60,-61,11,2462,2.4GHz,WPA2-ENT\nP26,0,9,KMITL-WIFI,00:2E:C7:90:94:61,-68,11,2462,2.4GHz,OPEN\nP27,1.7,9,KMITL-WIFI,00:2E:C7:90:94:61,-67,11,2462,2.4GHz,OPEN\nP28,3.4,9,KMITL-WIFI,00:2E:C7:90:94:61,-71,11,2462,2.4GHz,OPEN\nP29,5.1,9,KMITL-WIFI,00:2E:C7:90:94:61,-74,11,2462,2.4GHz,OPEN\nP30,6.8,9,KMITL-WIFI,00:2E:C7:90:94:61,-75,11,2462,2.4GHz,OPEN'

def load_room_b_embedded():
    import io
    return pd.read_csv(io.StringIO(ROOM_B_EMBEDDED_CSV))

def find_default_file(filename):
    if filename and os.path.exists(filename):
        return filename
    return None

def get_room_size(df, room_name):
    config = ROOMS.get(room_name, {"x": 5.0, "y": 5.0})
    room_x, room_y = config["x"], config["y"]
    if room_x is not None and room_y is not None:
        return room_x, room_y
    if df is not None and not df.empty:
        room_x = float(df["X"].max())
        room_y = float(df["Y"].max())
    else:
        room_x, room_y = 5.0, 5.0
    return room_x, room_y


# ============================================================
# ROOM B 3D HEATMAP (เกณฑ์เท่ากัน: -85 ถึง -55 dBm)
# ============================================================
def create_room_b_heatmap(wifi, opacity=0.80, show_ap=True, show_points=True, show_furniture=True):
    RX, RY, WH = 6.80, 9.00, 3.0
    AP_X_B, AP_Y_B, AP_H_B = 3.4, 4.5, 4.0
    fig = go.Figure()

    d = wifi.dropna(subset=["X", "Y", "RSSI"]).copy()

    if len(d) >= 3:
        gx = np.linspace(0, RX, 180)
        gy = np.linspace(0, RY, 240)
        GX, GY = np.meshgrid(gx, gy)
        try:
            GZ = griddata((d["X"], d["Y"]), d["RSSI"], (GX, GY), method="cubic")
        except Exception:
            GZ = griddata((d["X"], d["Y"]), d["RSSI"], (GX, GY), method="nearest")
        nearest = griddata((d["X"], d["Y"]), d["RSSI"], (GX, GY), method="nearest")
        GZ = np.where(np.isnan(GZ), nearest, GZ)
        GZ = np.clip(GZ, RSSI_MIN, RSSI_MAX)

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=np.zeros_like(GZ)+0.01,
            surfacecolor=GZ, colorscale=COLORSCALE_NAME,
            cmin=RSSI_MIN, cmax=RSSI_MAX, opacity=opacity, showscale=True,
            colorbar=dict(
                title=dict(text="<b>RSSI</b><br>(dBm)", font=dict(color="#111827")),
                tickvals=TICK_VALS,
                tickfont=dict(color="#111827"),
                len=0.75, thickness=20, outlinewidth=0, x=1.02
            ),
            customdata=GZ,
            hovertemplate="<b>Wi-Fi Signal</b><br>X: %{x:.2f} m<br>Y: %{y:.2f} m<br>RSSI: %{customdata:.1f} dBm<extra></extra>",
            name="RSSI Heatmap"
        ))

    if show_points and not d.empty:
        fig.add_trace(go.Scatter3d(
            x=d["X"], y=d["Y"], z=np.ones(len(d))*0.15,
            mode="markers+text",
            text=d["Point"] if "Point" in d else None,
            textposition="top center",
            textfont=dict(family="Arial", size=14, color="#4B5563"),
            marker=dict(size=5, color="#1F2937", symbol="circle", line=dict(color="white", width=1)),
            customdata=np.column_stack((
                d["Point"].astype(str) if "Point" in d else [""]*len(d),
                d["SSID"].astype(str) if "SSID" in d else [""]*len(d),
                d["BSSID"].astype(str) if "BSSID" in d else [""]*len(d),
                d["RSSI"],
                d["Channel"].astype(str) if "Channel" in d else [""]*len(d)
            )),
            hovertemplate="<b>%{customdata[0]}</b><br>X: %{x:.2f} m<br>Y: %{y:.2f} m<br>SSID: %{customdata[1]}<br>RSSI: %{customdata[3]} dBm<extra></extra>",
            name="Survey Points"
        ))

    if show_ap:
        fig.add_trace(go.Scatter3d(
            x=[AP_X_B], y=[AP_Y_B], z=[AP_H_B], mode="markers+text",
            marker=dict(size=14, color="#FF2020", symbol="diamond", line=dict(color="white", width=2)),
            text=["AP"], textposition="top center", name="Access Point"
        ))
        fig.add_trace(go.Scatter3d(
            x=[AP_X_B, AP_X_B], y=[AP_Y_B, AP_Y_B], z=[0, AP_H_B],
            mode="lines", line=dict(color="#FF3030", width=4, dash="dash"), hoverinfo="skip", showlegend=False
        ))

    def wall(x1,y1,x2,y2,height,z_bottom=0):
        fig.add_trace(go.Mesh3d(
            x=[x1,x2,x2,x1,x1,x2,x2,x1], y=[y1,y2,y2,y1,y1,y2,y2,y1],
            z=[z_bottom]*4+[height]*4,
            i=[0,0,0,4,4,4], j=[1,2,3,5,6,7], k=[2,3,4,6,7,5],
            color="#8A8A8A", opacity=0.72, hoverinfo="skip", showlegend=False
        ))

    wall(0,0,RX,0,WH); wall(0,0,0,RY,WH); wall(RX,0,RX,RY,WH)
    door_mid, door_w, door_h = 1.70, 1.98, 2.05
    dx1, dx2 = door_mid-door_w/2, door_mid+door_w/2
    wall(0,RY,dx1,RY,WH); wall(dx2,RY,RX,RY,WH); wall(dx1,RY,dx2,RY,WH,door_h)

    def box(xmin,xmax,ymin,ymax,zmin,zmax,color,op,name):
        fig.add_trace(go.Mesh3d(
            x=[xmin,xmax,xmax,xmin,xmin,xmax,xmax,xmin],
            y=[ymin,ymin,ymax,ymax,ymin,ymin,ymax,ymax],
            z=[zmin,zmin,zmin,zmin,zmax,zmax,zmax,zmax],
            i=[7,0,0,0,4,4,2,6,4,0,3,7], j=[3,4,1,2,5,6,3,7,5,1,2,6], k=[0,7,2,3,6,7,7,4,1,5,6,5],
            color=color, opacity=op, name=name, hoverinfo="name", showlegend=False
        ))

    def table(xmin,xmax,ymin,ymax,name):
        h, top, leg = 0.80, 0.05, 0.06
        box(xmin,xmax,ymin,ymax,h-top,h,"#D7CCC8",1,name+" Top")
        box(xmin,xmin+leg,ymin,ymin+leg,0,h-top,"#5C4033",1,name+" Leg")
        box(xmax-leg,xmax,ymin,ymin+leg,0,h-top,"#5C4033",1,name+" Leg")
        box(xmax-leg,xmax,ymax-leg,ymax,0,h-top,"#5C4033",1,name+" Leg")
        box(xmin,xmin+leg,ymax-leg,ymax,0,h-top,"#5C4033",1,name+" Leg")

    def flip_y(ymin,ymax):
        a,b=RY-ymin,RY-ymax
        return min(a,b),max(a,b)

    if show_furniture:
        y1,y2=flip_y(7.50,8.44); box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 1")
        y1,y2=flip_y(0.50,1.44); box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 10")
        for item,(ymin,ymax) in zip([11,12,13,14,15,16], [(7.00,7.78),(6.20,6.98),(4.40,5.18),(3.60,4.38),(1.80,2.58),(1.00,1.78)]):
            y1,y2=flip_y(ymin,ymax); table(RX-1.84,RX,y1,y2,f"Table {item}")
        grouped=[(2,0,1.84,5.40,6.18),(4,1.84,3.68,5.40,6.18),(3,0,1.84,4.60,5.38),(5,1.84,3.68,4.60,5.38),
                 (6,0,1.84,2.60,3.38),(8,1.84,3.68,2.60,3.38),(7,0,1.84,1.80,2.58),(9,1.84,3.68,1.80,2.58)]
        for item,x1,x2,ymin,ymax in grouped:
            y1,y2=flip_y(ymin,ymax); table(x1,x2,y1,y2,f"Table {item}")

    fig.update_layout(
        title=dict(text="3D Wi-Fi RSSI Heatmap | KMITL Co-Working Space (Room B)",x=0.5),
        paper_bgcolor="#FFFFFF",plot_bgcolor="#FFFFFF",font=dict(color="#111827"),
        scene=dict(
            bgcolor="#FFFFFF",
            xaxis=dict(title="X (m)",range=[-0.5,RX+0.7],gridcolor="#273746"),
            yaxis=dict(title="Y (m)",range=[-0.7,RY+0.5],gridcolor="#273746"),
            zaxis=dict(title="Height (m)",range=[0,4.5],gridcolor="#273746"),
            aspectmode="manual",aspectratio=dict(x=6.8,y=9.0,z=3.5),
            camera=dict(eye=dict(x=1.35,y=1.35,z=0.9))
        ),
        height=850,margin=dict(l=0,r=0,t=60,b=0),
        legend=dict(bgcolor="rgba(255,255,255,0.94)",bordercolor="#444",borderwidth=1)
    )
    return fig


# ============================================================
# ROOM C 3D HEATMAP (เกณฑ์เท่ากัน: -85 ถึง -55 dBm)
# ============================================================
def create_room_c_heatmap(wifi, opacity=0.80, show_points=True, show_furniture=True):
    ROOM_X, ROOM_Y = 2.70, 9.00
    WALL_HEIGHT, WALL_THICKNESS = 3.0, 0.12
    DOOR_EACH_W, DOOR_H = 0.99, 2.05
    DOOR_TOTAL_W = DOOR_EACH_W * 2
    DOOR_X_START = (ROOM_X - DOOR_TOTAL_W) / 2
    DOOR_X_END = DOOR_X_START + DOOR_TOTAL_W

    fig = go.Figure()

    def add_room_floor(room_name, room):
        x1, x2, y1, y2 = room["x_min"], room["x_max"], room["y_min"], room["y_max"]
        fig.add_trace(go.Mesh3d(x=[x1, x2, x2, x1], y=[y1, y1, y2, y2], z=[0]*4,
                                i=[0, 0], j=[1, 2], k=[2, 3], color=room["color"], opacity=0.8,
                                name=f"Room {room_name} Floor", hoverinfo="skip", showlegend=True))

    def add_wall(x1, y1, x2, y2, height=WALL_HEIGHT, z0=0):
        dx, dy = x2 - x1, y2 - y1
        length = np.hypot(dx, dy)
        if length == 0: return
        nx, ny = -dy / length * WALL_THICKNESS / 2, dx / length * WALL_THICKNESS / 2
        pts = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
        fig.add_trace(go.Mesh3d(x=[p[0] for p in pts]*2, y=[p[1] for p in pts]*2, z=[z0]*4+[z0+height]*4,
                                i=[0,0,4,4,0,0,2,2,0,0,1,1], j=[1,2,5,6,1,5,3,7,3,7,2,6], k=[2,3,6,7,5,4,7,6,7,4,6,5],
                                color="#93C5FD", opacity=0.06, hoverinfo="skip", showlegend=False))

    add_room_floor("Main", {"x_min": 0., "x_max": ROOM_X, "y_min": 0., "y_max": ROOM_Y, "color": "#E5E7EB"})
    add_wall(0, 0, 0, ROOM_Y); add_wall(ROOM_X, 0, ROOM_X, ROOM_Y); add_wall(0, 0, ROOM_X, 0)
    add_wall(0, ROOM_Y, DOOR_X_START, ROOM_Y); add_wall(DOOR_X_END, ROOM_Y, ROOM_X, ROOM_Y)
    add_wall(DOOR_X_START, ROOM_Y, DOOR_X_END, ROOM_Y, height=WALL_HEIGHT - DOOR_H, z0=DOOR_H)

    real_data = {"X": [0.00, 1.35, 2.70, 0.00, 1.35, 2.70, 0.00, 1.35, 2.70],
                 "Y": [0.00, 0.00, 0.00, 4.50, 4.50, 4.50, 9.00, 9.00, 9.00],
                 "RSSI": [-82, -85, -84, -77, -67, -58, -77, -84, -75]}
    if wifi is not None and not wifi.empty and {"X", "Y", "RSSI"}.issubset(wifi.columns):
        m = wifi.dropna(subset=["X", "Y", "RSSI"])
        real_data = {k: m[k].to_numpy() for k in ("X", "Y", "RSSI")}

    x_vals, y_vals, rssi_vals = np.asarray(real_data["X"], dtype=float), np.asarray(real_data["Y"], dtype=float), np.asarray(real_data["RSSI"], dtype=float)
    GX, GY = np.meshgrid(np.linspace(0, ROOM_X, 80), np.linspace(0, ROOM_Y, 120))
    try:
        GZ = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method="cubic")
    except:
        GZ = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method="nearest")
    GZ = np.where(np.isnan(GZ), griddata((x_vals, y_vals), rssi_vals, (GX, GY), method="nearest"), GZ)
    GZ = np.clip(GZ, RSSI_MIN, RSSI_MAX)

    fig.add_trace(go.Surface(
        x=GX, y=GY, z=np.full_like(GZ, 0.1), surfacecolor=GZ, colorscale=COLORSCALE_NAME,
        cmin=RSSI_MIN, cmax=RSSI_MAX, opacity=opacity, showscale=True,
        colorbar=dict(
            title=dict(text="<b>RSSI</b><br>(dBm)", font=dict(color="#111827")),
            tickvals=TICK_VALS,
            tickfont=dict(color="#111827"),
            len=0.75, thickness=20, outlinewidth=0, x=1.02
        ),
        name="Heatmap", hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<extra></extra>"
    ))

    if show_points:
        fig.add_trace(go.Scatter3d(
            x=x_vals, y=y_vals, z=np.full(len(x_vals), 0.15),
            mode="markers", marker=dict(size=6, color="#1F2937", line=dict(width=1, color="#FFFFFF")),
            hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<extra></extra>", showlegend=False
        ))

    def add_box(x, y, z, w, l, h, color, name, opacity=1.0):
        x0, x1, y0, y1, z0, z1 = x - w/2, x + w/2, y - l/2, y + l/2, z, z + h
        fig.add_trace(go.Mesh3d(x=[x0,x1,x1,x0]*2, y=[y0,y0,y1,y1]*2, z=[z0]*4+[z1]*4,
                                i=[0,0,4,4,0,0,2,2,0,0,1,1], j=[1,2,5,6,1,5,3,7,3,7,2,6], k=[2,3,6,7,5,4,7,6,7,4,6,5],
                                color=color, opacity=opacity, name=name, hoverinfo="name", showlegend=False))

    def add_table(name, x, y, z, w, l, h):
        top_color, leg_color, top_thickness, leg_size = "#D4A373", "#582F0E", 0.05, 0.06
        add_box(x, y, z + h - top_thickness, w, l, top_thickness, top_color, f"{name} (Top)")
        for leg_x, leg_y in [(x-w/2+leg_size/2, y-l/2+leg_size/2), (x+w/2-leg_size/2, y-l/2+leg_size/2),
                             (x+w/2-leg_size/2, y+l/2-leg_size/2), (x-w/2+leg_size/2, y+l/2-leg_size/2)]:
            add_box(leg_x, leg_y, z, leg_size, leg_size, h - top_thickness, leg_color, f"{name} (Leg)")

    if show_furniture:
        T_WIDTH, T_LENGTH, T_HEIGHT = 0.73, 1.83, 0.80
        center_x = ROOM_X / 2
        t1 = ROOM_Y - 0.60 - T_LENGTH / 2
        add_table("Table 1", center_x, t1, 0, T_WIDTH, T_LENGTH, T_HEIGHT)
        add_table("Table 2", center_x, t1 - T_LENGTH, 0, T_WIDTH, T_LENGTH, T_HEIGHT)
        t3 = t1 - T_LENGTH - T_LENGTH - 0.50
        add_table("Table 3", center_x, t3, 0, T_WIDTH, T_LENGTH, T_HEIGHT)
        add_table("Table 4", center_x, t3 - T_LENGTH, 0, T_WIDTH, T_LENGTH, T_HEIGHT)

    fig.update_layout(
        title=dict(text="3D Wi-Fi RSSI Heatmap", x=0.5, font=dict(size=20, color="#111827")),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(color="#111827"),
        scene=dict(bgcolor="#F8FAFC",
                   xaxis=dict(title="X (m)", range=[-0.5, ROOM_X + 0.5]),
                   yaxis=dict(title="Y (m)", range=[-0.5, ROOM_Y + 0.5]),
                   zaxis=dict(title="Height (m)", range=[0, WALL_HEIGHT + 0.5]),
                   aspectmode="manual", aspectratio=dict(x=2.7, y=9.0, z=3.0), camera=dict(eye=dict(x=1.5, y=1.5, z=1.0))),
        width=1350, height=850, margin=dict(l=0, r=0, t=70, b=0)
    )
    return fig


# ============================================================
# GENERAL 3D HEATMAP (สำหรับห้องย่อย Room 1 - Room 4 ซ่อน AP)
# ============================================================
def create_3d_heatmap(wifi, room_name, room_x, room_y, opacity, show_ap, show_points, show_furniture):
    heatmap_data = wifi.groupby(["X", "Y"])["RSSI"].max().reset_index()
    grid_x = np.linspace(0, room_x, 180)
    grid_y = np.linspace(0, room_y, 240)
    GX, GY = np.meshgrid(grid_x, grid_y)
    points = heatmap_data[["X", "Y"]].values
    values = heatmap_data["RSSI"].values

    GZ = None
    if len(points) >= 4:
        try: GZ = griddata(points, values, (GX, GY), method="cubic")
        except Exception: GZ = None
    if GZ is None and len(points) >= 3:
        try: GZ = griddata(points, values, (GX, GY), method="linear")
        except Exception: GZ = None

    nearest = griddata(points, values, (GX, GY), method="nearest")
    if GZ is None: GZ = nearest
    else: GZ = np.where(np.isnan(GZ), nearest, GZ)

    GZ = np.clip(GZ, RSSI_MIN, RSSI_MAX)
    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=GX, y=GY, z=np.zeros_like(GZ) + 0.01, surfacecolor=GZ, colorscale=COLORSCALE_NAME, cmin=RSSI_MIN, cmax=RSSI_MAX, opacity=opacity, showscale=True,
        colorbar=dict(
            title=dict(text="<b>RSSI</b><br>(dBm)", font=dict(color="#111827")),
            tickvals=TICK_VALS,
            tickfont=dict(color="#111827"),
            len=0.75, thickness=20, outlinewidth=0, x=1.02
        ),
        customdata=GZ, hovertemplate="<b>Wi-Fi Signal</b><br>X : %{x:.2f} m<br>Y : %{y:.2f} m<br>RSSI : %{customdata:.1f} dBm<extra></extra>", name="RSSI Heatmap"
    ))

    if show_points:
        band_data = wifi["Band"] if "Band" in wifi.columns else pd.Series(["N/A"] * len(wifi), index=wifi.index)
        channel_data = wifi["Channel"] if "Channel" in wifi.columns else pd.Series(["N/A"] * len(wifi), index=wifi.index)
        custom_data_stack = np.column_stack((wifi["Point"].astype(str), wifi["SSID"].astype(str), wifi["RSSI"], channel_data, band_data.astype(str)))
        fig.add_trace(go.Scatter3d(
            x=wifi["X"], y=wifi["Y"], z=np.ones(len(wifi)) * 0.15, mode="markers+text", text=wifi["Point"], textposition="top center",
            marker=dict(size=6, color="white", symbol="circle", line=dict(color="black", width=1.5)), customdata=custom_data_stack,
            hovertemplate="<b>%{customdata[0]}</b><br>RSSI: %{customdata[2]} dBm<br>Channel: %{customdata[3]}<br>Band: %{customdata[4]}<br>SSID: %{customdata[1]}<extra></extra>", name="Survey Points"
        ))

    # ซ่อน AP สำหรับห้องย่อย A1-A4 (Room 1, Room 2, Room 3, Room 4)
    if show_ap and room_name not in ["Room 1", "Room 2", "Room 3", "Room 4"]:
        AP_X, AP_Y = room_x / 2, room_y / 2
        fig.add_trace(go.Scatter3d(
            x=[AP_X], y=[AP_Y], z=[AP_HEIGHT], mode="markers+text",
            marker=dict(size=14, color="#FF0D0D", symbol="diamond", line=dict(color="white", width=2)),
            text=["📡 AP"], textposition="top center", name="Access Point"
        ))
        fig.add_trace(go.Scatter3d(x=[AP_X, AP_X], y=[AP_Y, AP_Y], z=[0, AP_HEIGHT], mode="lines", line=dict(color="#FF3030", width=4, dash="dash"), hoverinfo="skip", showlegend=False))

    fig.update_layout(
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(color="white"),
        scene=dict(
            xaxis=dict(title="X (m)", range=[-0.5, room_x + 0.7], gridcolor="#273746", zerolinecolor="#273746"),
            yaxis=dict(title="Y (m)", range=[-0.7, room_y + 0.5], gridcolor="#273746", zerolinecolor="#273746"),
            zaxis=dict(title="Height (m)", range=[0, 4.5], gridcolor="#273746", zerolinecolor="#273746"),
            aspectmode="manual", aspectratio=dict(x=max(room_x, 1), y=max(room_y, 1), z=3.5), camera=dict(eye=dict(x=1.35, y=1.35, z=0.9))
        ),
        height=700, margin=dict(l=0, r=0, t=10, b=0), legend=dict(bgcolor="rgba(255,255,255,0.94)", bordercolor="#D1D5DB", borderwidth=1)
    )
    return fig


# ============================================================
# ROOM A — COMBINED 3D HEATMAP (ภาพรวม Room A เกณฑ์เท่ากัน)
# ============================================================
ROOM_A_LAYOUT = {
    "A1": {"room_key": "Room 1", "x_min": 0.0,   "x_max": 3.535, "y_min": 4.20, "y_max": 8.33},
    "A2": {"room_key": "Room 2", "x_min": 3.535, "x_max": 7.105, "y_min": 2.83, "y_max": 8.30},
    "A3": {"room_key": "Room 3", "x_min": 0.0,   "x_max": 3.535, "y_min": 0.0,  "y_max": 4.20},
    "A4": {"room_key": "Room 4", "x_min": 3.535, "x_max": 7.105, "y_min": 0.0,  "y_max": 2.83},
}

ROOM_A_FALLBACK_DATA = {
    'Room 1': pd.DataFrame({'Point': ['P01', 'P02', 'P03', 'P04', 'P05', 'P06', 'P07', 'P08', 'P09'], 'X': [0.0, 1.77, 3.54, 0.0, 1.77, 3.54, 0.0, 1.77, 3.54], 'Y': [0.0, 0.0, 0.0, 2.07, 2.07, 2.07, 4.13, 4.13, 4.13], 'RSSI': [-70, -64, -68, -68, -74, -70, -77, -68, -75], 'SSID': ['KMITL-WIFI']*9, 'BSSID': ['Room 1']*9}),
    'Room 2': pd.DataFrame({'Point': ['P10', 'P11', 'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18', 'P19', 'P20', 'P21'], 'X': [0.0, 1.78, 3.57]*4, 'Y': [0.0]*3+[1.82]*3+[3.65]*3+[5.47]*3, 'RSSI': [-50, -66, -81, -85, -71, -75, -50, -70, -70, -70, -69, -71], 'SSID': ['KMITL-WIFI']*12, 'BSSID': ['Room 2']*12}),
    'Room 3': pd.DataFrame({'Point': ['P22', 'P23', 'P24', 'P25', 'P26', 'P27', 'P28', 'P29', 'P30'], 'X': [0.0, 1.77, 3.54]*3, 'Y': [0.0]*3+[2.1]*3+[4.2]*3, 'RSSI': [-74, -62, -71, -63, -69, -70, -67, -60, -64], 'SSID': ['KMITL-WIFI']*9, 'BSSID': ['Room 3']*9}),
    'Room 4': pd.DataFrame({'Point': ['P31', 'P32', 'P33', 'P34', 'P35', 'P36', 'P37', 'P38', 'P39'], 'X': [0.0, 1.78, 3.57]*3, 'Y': [0.0]*3+[1.41]*3+[2.83]*3, 'RSSI': [-73, -67, -74, -63, -66, -70, -64, -66, -75], 'SSID': ['KMITL-WIFI']*9, 'BSSID': ['Room 4']*9}),
}

def _load_room_a_csv(room_key):
    filename = ROOMS[room_key]["file"]
    if not filename or not os.path.exists(filename):
        return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()
    try:
        d = pd.read_csv(filename, skipinitialspace=True)
        d.columns = d.columns.astype(str).str.strip()
        d.rename(columns={"Point ID": "Point", "X (m)": "X", "Y (m)": "Y", "RSSI (dBm)": "RSSI", "RSSI_dBm": "RSSI"}, inplace=True)
        for col in ["X", "Y", "RSSI"]:
            if col in d.columns: d[col] = pd.to_numeric(d[col], errors="coerce")
        return d.dropna(subset=["X", "Y", "RSSI"]).copy()
    except Exception:
        return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()

def load_room_a_combined_data():
    frames = []
    for label, layout in ROOM_A_LAYOUT.items():
        room_key = layout["room_key"]
        d = _load_room_a_csv(room_key).copy()
        if d.empty: continue

        d["Local_X"] = pd.to_numeric(d["X"], errors="coerce")
        d["Local_Y"] = pd.to_numeric(d["Y"], errors="coerce")
        d["X"] = d["Local_X"] + layout["x_min"]
        d["Y"] = d["Local_Y"] + layout["y_min"]
        d["Subroom"] = label

        if "Point" not in d.columns: d["Point"] = [f"{label}-P{i+1}" for i in range(len(d))]
        if "SSID" not in d.columns: d["SSID"] = "KMITL-WIFI"
        if "BSSID" not in d.columns: d["BSSID"] = label + "-AP"
        frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def create_room_a_combined_heatmap(wifi=None, opacity=0.85, show_ap=True, show_points=True, show_furniture=True):
    ROOM_X, ROOM_Y = 7.20, 8.40
    WALL_HEIGHT, WALL_THICKNESS = 3.0, 0.12
    WALL_COLOR = '#93C5FD'
    WALL_OPACITY = 0.06
    FONT_FAMILY = 'Arial'
    POINT_FONT_SIZE, POINT_FONT_COLOR = 11, '#4B5563'
    ROOM_FONT_SIZE, ROOM_FONT_COLOR = 16, '#4B5563'
    POINT_HEIGHT, TEXT_HEIGHT = 0.15, 0.28
    
    HEATMAP_OPACITY, HEATMAP_RESOLUTION = opacity, 80

    ROOMS_CONFIG = {
        '1': {'x_min': 0., 'x_max': 3.535, 'y_min': 4.20, 'y_max': 8.33, 'color': '#E5E7EB'},
        '2': {'x_min': 3.535, 'x_max': 7.105, 'y_min': 2.83, 'y_max': 8.30, 'color': '#E5E7EB'},
        '3': {'x_min': 0., 'x_max': 3.535, 'y_min': 0., 'y_max': 4.20, 'color': '#E5E7EB'},
        '4': {'x_min': 3.535, 'x_max': 7.105, 'y_min': 0., 'y_max': 2.83, 'color': '#E5E7EB'},
    }

    room_a_data = {'X':[0,1.77,3.54,0,1.77,3.54,0,1.77,3.54], 'Y':[4.20,4.20,4.20,6.27,6.27,6.27,8.33,8.33,8.33], 'RSSI':[-70,-64,-68,-68,-74,-70,-77,-68,-75]}
    room_b_data = {'X':[3.535,5.315,7.105]*4, 'Y':[2.83]*3+[4.65]*3+[6.48]*3+[8.30]*3, 'RSSI':[-50,-66,-81,-85,-71,-75,-50,-70,-70,-70,-69,-71]}
    room_c_data = {'X':[0,1.77,3.54]*3, 'Y':[0]*3+[2.10]*3+[4.20]*3, 'RSSI':[-74,-62,-71,-63,-69,-70,-67,-60,-64]}
    room_d_data = {'X':[3.535,5.315,7.105]*3, 'Y':[0]*3+[1.41]*3+[2.83]*3, 'RSSI':[-73,-67,-74,-63,-66,-70,-64,-66,-75]}
    
    ROOM_DATA = {'1':room_a_data,'2':room_b_data,'3':room_c_data,'4':room_d_data}

    if wifi is not None and not wifi.empty and {"X", "Y", "RSSI"}.issubset(wifi.columns):
        for k in ROOM_DATA.keys(): ROOM_DATA[k] = {'X': [], 'Y': [], 'RSSI': []}
        for _, row in wifi.dropna(subset=["X", "Y", "RSSI"]).iterrows():
            x, y, rssi = float(row['X']), float(row['Y']), float(row['RSSI'])
            if x <= 3.535 and y >= 4.20: r = '1'
            elif x > 3.535 and y >= 2.83: r = '2'
            elif x <= 3.535 and y < 4.20: r = '3'
            else: r = '4'
            ROOM_DATA[r]['X'].append(x)
            ROOM_DATA[r]['Y'].append(y)
            ROOM_DATA[r]['RSSI'].append(rssi)

    fig = go.Figure()

    # Floors
    def add_room_floor(room_name, room):
        x1,x2,y1,y2 = room['x_min'],room['x_max'],room['y_min'],room['y_max']
        fig.add_trace(go.Mesh3d(x=[x1,x2,x2,x1],y=[y1,y1,y2,y2],z=[0]*4,
                                i=[0,0],j=[1,2],k=[2,3],color=room['color'],opacity=0.7,
                                name=f'Room {room_name} Floor',hoverinfo='skip',showlegend=False))
        cx,cy=(x1+x2)/2,(y1+y2)/2
        fig.add_trace(go.Scatter3d(x=[cx],y=[cy],z=[1.12],mode='text',
                                   text=[f'ROOM {room_name}'],
                                   textfont=dict(family=FONT_FAMILY,size=ROOM_FONT_SIZE,color=ROOM_FONT_COLOR),
                                   hoverinfo='skip',showlegend=False))
        fig.add_trace(go.Scatter3d(x=[cx],y=[cy-0.35],z=[1.12],mode='text',
                                   text=[f'{x2-x1:.2f} × {y2-y1:.2f} m'],
                                   textfont=dict(family=FONT_FAMILY,size=10,color='#6B7280'),
                                   hoverinfo='skip',showlegend=False))

    for room_name, room in ROOMS_CONFIG.items():
        add_room_floor(room_name, room)

    # Walls
    def add_wall(x1,y1,x2,y2,height=WALL_HEIGHT,z0=0):
        dx,dy=x2-x1,y2-y1
        length=np.hypot(dx,dy)
        if length == 0 or height <= 0: return
        nx,ny=-dy/length*WALL_THICKNESS/2,dx/length*WALL_THICKNESS/2
        pts=[(x1+nx,y1+ny),(x2+nx,y2+ny),(x2-nx,y2-ny),(x1-nx,y1-ny)]
        xs=[p[0] for p in pts]*2
        ys=[p[1] for p in pts]*2
        zs=[z0]*4+[z0+height]*4
        faces=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=[f[0] for f in faces],j=[f[1] for f in faces],k=[f[2] for f in faces],
                                color=WALL_COLOR,opacity=WALL_OPACITY,hoverinfo='skip',showlegend=False))

    add_wall(0,0,1.03,0); add_wall(2.97,0,ROOM_X,0); add_wall(1.03,0,2.97,0,height=WALL_HEIGHT-2.06,z0=2.06)
    add_wall(0,0,0,ROOM_Y); add_wall(ROOM_X,0,ROOM_X,ROOM_Y); add_wall(0,ROOM_Y,ROOM_X,ROOM_Y)
    DOOR_1_W,DOOR_1_H,DOOR_1_X=0.97,2.06,2.45
    add_wall(0,4.20,DOOR_1_X,4.20); add_wall(DOOR_1_X+DOOR_1_W,4.20,3.535,4.20); add_wall(DOOR_1_X,4.20,DOOR_1_X+DOOR_1_W,4.20,height=WALL_HEIGHT-DOOR_1_H,z0=DOOR_1_H)
    add_wall(3.535,2.83,7.105,2.83); add_wall(3.535,4.20,3.535,8.33); add_wall(3.535,0,3.535,1.86); add_wall(3.535,1.86,3.535,2.83,height=WALL_HEIGHT-2.06,z0=2.06)
    DOOR_2_W,DOOR_2_H,DOOR_2_Y=0.97,2.06,3.03
    add_wall(3.535,2.83,3.535,DOOR_2_Y); add_wall(3.535,DOOR_2_Y+DOOR_2_W,3.535,4.20); add_wall(3.535,DOOR_2_Y,3.535,DOOR_2_Y+DOOR_2_W,height=WALL_HEIGHT-DOOR_2_H,z0=DOOR_2_H)

    LABEL_OFFSETS=[(-0.20,-0.18),(0.0,-0.22),(0.20,-0.18),(-0.20,0.18),(0.0,0.22),(0.20,0.18)]
    used_label_positions=[]
    def place_labels(x_values,y_values,room):
        lx,ly=[],[]
        for idx,(x,y) in enumerate(zip(x_values,y_values)):
            candidates=LABEL_OFFSETS[idx%6:]+LABEL_OFFSETS[:idx%6]
            best=None
            for dx,dy in candidates:
                px=float(np.clip(x+dx,room['x_min']+0.12,room['x_max']-0.12))
                py=float(np.clip(y+dy,room['y_min']+0.12,room['y_max']-0.12))
                separation=min((np.hypot(px-ux,py-uy) for ux,uy in used_label_positions),default=99.)
                if best is None or separation>best[0]: best=(separation,px,py)
            _,px,py=best
            lx.append(px);ly.append(py)
            used_label_positions.append((px,py))
        return lx,ly

    # Heatmap Generator
    def add_room_heatmap(room_name, room, room_data):
        if not room_data or len(room_data.get('X', [])) == 0: return
        x_vals = np.asarray(room_data['X'], dtype=float)
        y_vals = np.asarray(room_data['Y'], dtype=float)
        rssi_vals = np.asarray(room_data['RSSI'], dtype=float)
        
        grid_x = np.linspace(room['x_min'], room['x_max'], HEATMAP_RESOLUTION)
        grid_y = np.linspace(room['y_min'], room['y_max'], HEATMAP_RESOLUTION)
        GX, GY = np.meshgrid(grid_x, grid_y)
        
        try: GZ = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method='cubic')
        except: GZ = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method='nearest')
        nearest = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method='nearest')
        GZ = np.where(np.isnan(GZ), nearest, GZ)
        GZ = np.clip(GZ, RSSI_MIN, RSSI_MAX)
        
        Z_PLANE = np.full_like(GZ, 0.20)

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=Z_PLANE,
            surfacecolor=GZ, colorscale=COLORSCALE_NAME,
            cmin=RSSI_MIN, cmax=RSSI_MAX, opacity=HEATMAP_OPACITY,
            showscale=(room_name == '1'), 
            colorbar=dict(
                title=dict(text="<b>RSSI</b><br>(dBm)", font=dict(color="#111827")), 
                tickvals=TICK_VALS, 
                tickfont=dict(color="#111827"), 
                len=0.75, thickness=20, outlinewidth=0, x=1.02
            ) if room_name == '1' else None,
            name=f'Heatmap Room {room_name}',
            hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<br>RSSI: %{surfacecolor:.1f} dBm<extra></extra>"
        ))
        
        if show_points:
            fig.add_trace(go.Scatter3d(
                x=x_vals, y=y_vals, z=np.full(len(x_vals), POINT_HEIGHT),
                mode='markers', marker=dict(size=4, color='#1F2937', line=dict(width=1, color='white')),
                name=f'Points Room {room_name}',
                hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<br>RSSI: %{customdata:.1f} dBm<extra></extra>",
                customdata=rssi_vals
            ))
            labels = [f"P{i+1}" for i in range(len(x_vals))]
            lx,ly=place_labels(x_vals,y_vals,room)
            fig.add_trace(go.Scatter3d(
                x=lx, y=ly, z=np.full(len(lx), TEXT_HEIGHT),
                mode='text', text=labels, textposition='middle center',
                textfont=dict(family=FONT_FAMILY, size=POINT_FONT_SIZE, color=POINT_FONT_COLOR),
                hoverinfo='skip', showlegend=False
            ))

    for room_name, room in ROOMS_CONFIG.items():
        if room_name in ROOM_DATA:
            add_room_heatmap(room_name, room, ROOM_DATA[room_name])
            
    # Furniture
    def add_box(x,y,z,w,l,h,color,name):
        x0,x1=x-w/2,x+w/2
        y0,y1=y-l/2,y+l/2
        z0,z1=z,z+h
        xs=[x0,x1,x1,x0,x0,x1,x1,x0]; ys=[y0,y0,y1,y1,y0,y0,y1,y1]; zs=[z0,z0,z0,z0,z1,z1,z1,z1]
        i=[0,0,4,4,0,0,2,2,0,0,1,1]; j=[1,2,5,6,1,5,3,7,3,7,2,6]; k=[2,3,6,7,5,4,7,6,7,4,6,5]
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=i,j=j,k=k,color=color,opacity=1.,name=name,hoverinfo='name',showlegend=False))

    def add_table(name,x,y,z,w,l,h):
        top_color,leg_color='#D4A373','#582F0E'
        top_thickness,leg_size=0.05,0.06
        add_box(x,y,z+h-top_thickness,w,l,top_thickness,top_color,f'{name} (Top)')
        for sx in (-1,1):
            for sy in (-1,1):
                add_box(x+sx*(w/2-leg_size/2),y+sy*(l/2-leg_size/2),z,leg_size,leg_size,h-top_thickness,leg_color,f'{name} (Leg)')

    def add_cabinet(name,x,y,z,w,l,h): add_box(x,y,z,w,l,h,'#A0522D',name)

    def add_glass_swing_door(name,hinge_x,hinge_y,w,h,t,angle_deg):
        a=np.radians(angle_deg)
        px1,py1=hinge_x,hinge_y; px2,py2=hinge_x+w*np.cos(a),hinge_y+w*np.sin(a)
        px3,py3=px2-t*np.sin(a),py2+t*np.cos(a); px4,py4=px1-t*np.sin(a),py1+t*np.cos(a)
        xs=[px1,px2,px3,px4]*2; ys=[py1,py2,py3,py4]*2; zs=[0]*4+[h]*4
        i=[0,0,4,4,0,0,2,2,0,0,1,1]; j=[1,2,5,6,1,5,3,7,3,7,2,6]; k=[2,3,6,7,5,4,7,6,7,4,6,5]
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=i,j=j,k=k,color='#38BDF8',opacity=0.45,name=name,hoverinfo='name',showlegend=False))

    def add_sliding_door(name,x,y,length,t,h,orientation='horizontal'):
        if orientation=='horizontal': x0,x1=x,x+length; y0,y1=y-t/2,y+t/2
        else: x0,x1=x-t/2,x+t/2; y0,y1=y,y+length
        xs=[x0,x1,x1,x0]*2; ys=[y0,y0,y1,y1]*2; zs=[0]*4+[h]*4
        i=[0,0,4,4,0,0,2,2,0,0,1,1]; j=[1,2,5,6,1,5,3,7,3,7,2,6]; k=[2,3,6,7,5,4,7,6,7,4,6,5]
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=i,j=j,k=k,color='#38BDF8',opacity=0.45,name=name,hoverinfo='name',showlegend=False))

    if show_furniture:
        T_WIDTH,T_LENGTH,T_HEIGHT=0.73,1.83,0.80
        # Room 1
        center_x1,center_y1=(0+3.535)/2,(4.20+8.33)/2
        add_table('Table 1 (Room 1)',center_x1,center_y1+T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_table('Table 2 (Room 1)',center_x1,center_y1-T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_sliding_door('Sliding Door 1',x=DOOR_1_X,y=4.20-(WALL_THICKNESS/2+0.01),length=DOOR_1_W,t=0.04,h=DOOR_1_H,orientation='horizontal')

        # Room 2
        center_x2,center_y2=(3.535+7.105)/2,(2.83+8.30)/2
        GAP=0.50
        add_table('Table 2 (Room 2)',center_x2,center_y2+GAP/2+T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_table('Table 1 (Room 2)',center_x2,center_y2+GAP/2+T_WIDTH+T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_table('Table 3 (Room 2)',center_x2,center_y2-GAP/2-T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_table('Table 4 (Room 2)',center_x2,center_y2-GAP/2-T_WIDTH-T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        DOOR_2_X=3.535+(WALL_THICKNESS/2+0.01)
        add_sliding_door('Sliding Door (Room 2)',x=DOOR_2_X,y=3.03,length=0.97,t=0.04,h=2.06,orientation='vertical')

        # Room 3
        center_y3=(0.+4.20)/2
        table1_x_pos=T_WIDTH/2+WALL_THICKNESS/2
        add_table('Table 1 (Room 3)',table1_x_pos,center_y3,0,T_WIDTH,T_LENGTH,T_HEIGHT)
        add_table('Table 2 (Room 3)',table1_x_pos+T_WIDTH,center_y3,0,T_WIDTH,T_LENGTH,T_HEIGHT)
        add_cabinet('Cabinet (Room 3)',WALL_THICKNESS/2+0.49/2,4.20-WALL_THICKNESS/2-0.95/2,0,0.49,0.95,1.86)
        add_glass_swing_door('Left Swing Door (Room 3)',hinge_x=1.03,hinge_y=0.,w=0.97,h=2.06,t=0.02,angle_deg=45)
        add_glass_swing_door('Right Swing Door (Room 3)',hinge_x=2.97,hinge_y=0.,w=0.97,h=2.06,t=0.02,angle_deg=135)

        # Room 4
        center_x4,center_y4=(3.535+7.105)/2,(0.+2.83)/2
        add_table('Table 1 (Room 4)',center_x4,center_y4+T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_table('Table 2 (Room 4)',center_x4,center_y4-T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_sliding_door('Sliding Door (Room 4)',x=3.535-(WALL_THICKNESS/2+0.01),y=1.86,length=0.97,t=0.04,h=2.06,orientation='vertical')

    fig.update_layout(
        title=dict(text='3D Wi-Fi RSSI Heatmap | KMITL Co-Working Space (Room A Combined)',x=0.5,font=dict(size=22,color='#111827',family=FONT_FAMILY)),
        paper_bgcolor='#FFFFFF',plot_bgcolor='#FFFFFF',font=dict(family=FONT_FAMILY,color='#111827'),
        scene=dict(bgcolor='#F8FAFC',
                   xaxis=dict(title='X (m)',range=[-0.5,ROOM_X+0.5],gridcolor='#CBD5E1',zerolinecolor='#4B5563',tickfont=dict(color='#111827')),
                   yaxis=dict(title='Y (m)',range=[-0.5,ROOM_Y+0.5],gridcolor='#CBD5E1',zerolinecolor='#4B5563',tickfont=dict(color='#111827')),
                   zaxis=dict(title='Height (m)',range=[0,WALL_HEIGHT+0.5],gridcolor='#CBD5E1',zerolinecolor='#4B5563',tickfont=dict(color='#111827')),
                   aspectmode='manual',aspectratio=dict(x=7.2,y=8.4,z=3.5),
                   camera=dict(eye=dict(x=1.35,y=1.35,z=0.9))),
        width=1350,height=850,margin=dict(l=0,r=0,t=70,b=0))

    if not show_points:
        fig.data = tuple(t for t in fig.data if not ((getattr(t, 'name', '') or '').startswith(('Survey Points Room', 'Point Labels Room'))))
    if not show_furniture:
        fig.data = tuple(t for t in fig.data if not ((getattr(t, 'name', '') or '').startswith(('Table ', 'Cabinet ', 'Sliding Door', 'Left Swing Door', 'Right Swing Door'))))

    return fig


# ============================================================
# SMART WI-FI ADVISOR
# ============================================================
def analyze_wifi_recommendation(df):
    if df is None or df.empty or "SSID" not in df.columns: return pd.DataFrame()
    results = []
    for ssid, group in df.groupby("SSID"):
        rssi = pd.to_numeric(group["RSSI"], errors="coerce").dropna()
        if rssi.empty: continue
        avg_rssi = float(rssi.mean())
        min_rssi = float(rssi.min())
        max_rssi = float(rssi.max())
        std_rssi = float(rssi.std()) if len(rssi) > 1 else 0.0
        if np.isnan(std_rssi): std_rssi = 0.0
        total = len(rssi)
        good_percent = float((rssi >= -65).sum() / total * 100)
        weak_percent = float((rssi <= -75).sum() / total * 100)
        rssi_score = float(np.clip(((avg_rssi + 90) / 40) * 100, 0, 100))
        stability_score = float(np.clip(100 - std_rssi * 8, 0, 100))
        score = rssi_score * 0.50 + good_percent * 0.25 + stability_score * 0.15 + (100 - weak_percent) * 0.10

        if avg_rssi >= -60: quality = "Excellent"
        elif avg_rssi >= -67: quality = "Good"
        elif avg_rssi >= -75: quality = "Fair"
        else: quality = "Weak"

        results.append({
            "SSID": str(ssid), "Average RSSI": avg_rssi, "Weakest RSSI": min_rssi,
            "Strongest RSSI": max_rssi, "Stability": std_rssi, "Good Signal (%)": good_percent,
            "Weak Signal (%)": weak_percent, "Measurements": total, "Score": score, "Quality": quality,
        })
    result = pd.DataFrame(results)
    if not result.empty:
        result = result.sort_values(["Score", "Average RSSI"], ascending=[False, False]).reset_index(drop=True)
    return result

def recommend_wifi_at_point(df, point):
    if df is None or df.empty: return None, pd.DataFrame()
    point_data = df[df["Point"].astype(str) == str(point)].copy()
    if point_data.empty: return None, pd.DataFrame()
    point_summary = (point_data.groupby("SSID").agg(RSSI=("RSSI", "max"), AP_Count=("BSSID", "nunique"))
                     .reset_index().sort_values("RSSI", ascending=False).reset_index(drop=True))
    if point_summary.empty: return None, point_summary
    return point_summary.iloc[0], point_summary

def signal_quality(rssi, language="ไทย"):
    if rssi >= -60:
        return ("🟢 Excellent", "สัญญาณแรงมาก เหมาะสำหรับ Video Call, Streaming และงานที่ต้องการความเสถียร") if language == "ไทย" else ("🟢 Excellent", "Very strong signal for video calls, streaming and demanding use.")
    if rssi >= -67:
        return ("🟢 Good", "สัญญาณดี เหมาะสำหรับการใช้งานทั่วไปและ Video Call") if language == "ไทย" else ("🟢 Good", "Good signal for general use and video calls.")
    if rssi >= -75:
        return ("🟡 Fair", "สามารถใช้งานได้ แต่อาจมีความไม่เสถียรในบางช่วง") if language == "ไทย" else ("🟡 Fair", "Usable signal, but performance may be less stable.")
    return ("🔴 Weak", "สัญญาณค่อนข้างอ่อน แนะนำให้ลอง Wi-Fi อื่นหรือขยับเข้าใกล้ Access Point") if language == "ไทย" else ("🔴 Weak", "Weak signal. Try another Wi-Fi or move closer to an access point.")


# ============================================================
# LANGUAGE / DISPLAY HELPERS
# ============================================================
TEXT = {
    "ไทย": {
        "settings": "📂 นำเข้าและตั้งค่า", "language": "🌐 ภาษา / Language",
        "area_select": "เลือกพื้นที่", "area": "พื้นที่", "subroom": "เลือกห้องย่อย",
        "default_file": "ไฟล์เริ่มต้น", "upload": "อัปโหลดข้อมูล Survey",
        "ssid": "📶 เลือก SSID", "opacity": "ความโปร่งใส Heatmap",
        "layers": "เลเยอร์แผนที่ 3D", "show_ap": "แสดงตำแหน่ง AP",
        "show_points": "แสดงจุด Survey", "show_furniture": "แสดงผนังและเฟอร์นิเจอร์",
        "survey_area": "พื้นที่สำรวจ", "location": "ตำแหน่ง", "current_room": "ห้องปัจจุบัน",
        "room_size": "ขนาดห้อง", "frequency": "ความถี่", "survey_points": "จุดสำรวจ",
        "access_points": "Access Points", "avg_rssi": "RSSI เฉลี่ย", "strong": "สัญญาณดี",
        "weak": "สัญญาณอ่อน", "map": "🗺️ แผนที่ 3D", "analysis": "📊 วิเคราะห์",
        "raw": "📋 ข้อมูลดิบ", "signal_summary": "📶 สรุปคุณภาพสัญญาณ",
        "excellent": "ดี", "fair": "ปานกลาง", "poor": "อ่อน",
    },
    "English": {
        "settings": "📂 Import & Settings", "language": "🌐 Language / ภาษา",
        "area_select": "Select Area", "area": "Area", "subroom": "Select Subroom",
        "default_file": "Default file", "upload": "Upload Survey Data",
        "ssid": "📶 Select SSID", "opacity": "Heatmap Opacity",
        "layers": "3D Map Layers", "show_ap": "Show AP Position",
        "show_points": "Show Survey Points", "show_furniture": "Show Walls & Furniture",
        "survey_area": "Survey Area", "location": "Location", "current_room": "Current Room",
        "room_size": "Room Size", "frequency": "Frequency", "survey_points": "Survey Points",
        "access_points": "Access Points", "avg_rssi": "Average RSSI", "strong": "Strong Signal",
        "weak": "Weak Signal", "map": "🗺️ 3D Map", "analysis": "📊 Analysis",
        "raw": "📋 Raw Data", "signal_summary": "📶 Signal Quality Summary",
        "excellent": "Good", "fair": "Fair", "poor": "Weak",
    }
}

ROOM_A_DISPLAY = {"A1": "Room 1", "A2": "Room 2", "A3": "Room 3", "A4": "Room 4"}
ROOM_DISPLAY = {"Room 1": "A1", "Room 2": "A2", "Room 3": "A3", "Room 4": "A4", "Room B": "B", "Room C": "C"}


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    language = st.selectbox("🌐 ภาษา / Language", ["ไทย", "English"], index=0, key="language_selector")
    t = TEXT[language]

    st.header(t["settings"])
    st.subheader(t["area_select"])

    selected_area = st.radio(t["area"], ["Room A", "Room B", "Room C"], index=0)

    if selected_area == "Room A":
        room_a_options = ["ภาพรวม Room A", "A1", "A2", "A3", "A4"] if language == "ไทย" else ["Room A Overview", "A1", "A2", "A3", "A4"]
        st.markdown("#### 🚪 ห้องย่อย Room A" if language == "ไทย" else "#### 🚪 Room A Subrooms")
        selected_subroom = st.selectbox("เลือกมุมมอง / ห้องย่อย" if language == "ไทย" else "Select overview / subroom", room_a_options, key="room_a_view")
        if selected_subroom in ["ภาพรวม Room A", "Room A Overview"]: selected_room = "Room A"
        else: selected_room = ROOM_A_DISPLAY[selected_subroom]
    else:
        selected_room = selected_area

    display_room = ROOM_DISPLAY.get(selected_room, selected_room)
    st.divider()

    default_filename = ROOMS[selected_room]["file"]
    if selected_room == "Room A":
        st.caption("ข้อมูล Room A: รวมอัปโหลด A1-A4 ในไฟล์เดียวได้" if language == "ไทย" else "Room A data: single file for A1-A4 supported")
    else:
        st.caption(f"{t['default_file']}: `{default_filename}`")

    uploaded_file = st.file_uploader(t["upload"], type=["csv", "xlsx"], key=f"upload_{selected_area}")


# ============================================================
# LOAD FILE AND PROCESS FOR ROOM A & OTHERS
# ============================================================
if uploaded_file is not None:
    uploaded_df = load_data(uploaded_file)
    if selected_area == "Room A":
        if selected_room == "Room A":
            df = uploaded_df
        else:
            layout = ROOM_A_LAYOUT[display_room]
            df = uploaded_df[
                (uploaded_df["X"] >= layout["x_min"]) & (uploaded_df["X"] <= layout["x_max"]) &
                (uploaded_df["Y"] >= layout["y_min"]) & (uploaded_df["Y"] <= layout["y_max"])
            ].copy()
            df["X"] = df["X"] - layout["x_min"]
            df["Y"] = df["Y"] - layout["y_min"]
    elif selected_room == "Room B":
        base_df = load_room_b_embedded()
        df = pd.concat([base_df, uploaded_df], ignore_index=True).drop_duplicates(subset=["Point", "SSID", "BSSID"], keep="last")
    else:
        df = uploaded_df

elif selected_room == "Room A":
    df = load_room_a_combined_data()
    if df is None or df.empty:
        st.error("❌ ไม่สามารถโหลดข้อมูล Room A ได้" if language == "ไทย" else "❌ Unable to load Room A data.")
        st.stop()

elif selected_room in ["Room 1", "Room 2", "Room 3", "Room 4"]:
    df = _load_room_a_csv(selected_room)
    if df is None or df.empty:
        st.error(f"❌ ไม่พบข้อมูล {ROOM_DISPLAY.get(selected_room, selected_room)}")
        st.stop()

else:
    default_file = find_default_file(default_filename)
    if selected_room == "Room B": df = load_room_b_embedded()
    elif default_file is not None:
        try:
            df = pd.read_csv(default_file, skipinitialspace=True)
            df.columns = df.columns.astype(str).str.strip()
            df.rename(columns={"Point ID": "Point", "X (m)": "X", "Y (m)": "Y", "RSSI (dBm)": "RSSI"}, inplace=True)
            for col in ["X", "Y", "RSSI"]:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["X", "Y", "RSSI"]).copy()
        except Exception as e:
            st.error(f"ไม่สามารถอ่าน `{default_filename}` ได้: {e}")
            st.stop()
    else:
        st.info(f"👆 ยังไม่พบไฟล์ `{default_filename}` อัปโหลดไฟล์เพื่อเริ่มใช้งาน")
        st.stop()

if df is None or df.empty:
    st.error("❌ ไม่พบข้อมูล Survey")
    st.stop()

df.columns = df.columns.astype(str).str.strip()
global_aliases = {"point id": "Point", "point": "Point", "x (m)": "X", "x": "X", "y (m)": "Y", "y": "Y", "rssi (dbm)": "RSSI", "rssi_dbm": "RSSI", "rssi": "RSSI", "ssid": "SSID", "bssid": "BSSID"}
df.rename(columns={col: global_aliases.get(col.lower(), col) for col in df.columns}, inplace=True)

if "BSSID" not in df.columns: df["BSSID"] = df["SSID"].astype(str).str.strip()

ROOM_X, ROOM_Y = get_room_size(df, selected_room)

# ============================================================
# SIDEBAR CONTROLS
# ============================================================
with st.sidebar:
    st.divider()
    st.subheader(t["ssid"])
    if "SSID" in df.columns:
        ssid_options = sorted(df["SSID"].dropna().astype(str).unique().tolist())
        selected_ssids = st.multiselect("SSID", options=ssid_options, default=ssid_options)
    else:
        selected_ssids = []
        st.warning("ไม่พบ Column SSID")

    opacity = st.slider(t["opacity"], 0.0, 1.0, 0.85, 0.05)
    st.divider()
    st.subheader(t["layers"])
    show_ap = st.checkbox(t["show_ap"], True)
    show_points = st.checkbox(t["show_points"], True)
    show_furniture = st.checkbox(t["show_furniture"], True)

if selected_ssids: wifi = df[df["SSID"].astype(str).isin(selected_ssids)].copy()
else: wifi = df.copy()

wifi_recommendation = analyze_wifi_recommendation(wifi)
best_wifi = wifi_recommendation.iloc[0] if not wifi_recommendation.empty else None

# ============================================================
# HEADER & ROOM INFO
# ============================================================
st.markdown(
    f"""
    <div class="dashboard-title">ระบบสำรวจและวิเคราะห์คุณภาพเครือข่ายไร้สายแบบพกพา</div>
    <div class="dashboard-subtitle">Portable Wireless Site Survey and Network Analysis System</div>
    <div class="room-badge">📍 {display_room}</div>
    """,
    unsafe_allow_html=True
)

col_info, col_blank = st.columns([1, 1])
with col_info:
    st.markdown(
        f"""
**{t["survey_area"]}:** Telecommunication Engineering Department  
**{t["location"]}:** 3rd Floor – Co-working Space  
**{t["current_room"]}:** {display_room}  
**{t["room_size"]}:** {ROOM_X:.2f} × {ROOM_Y:.2f} m  
**{t["frequency"]}:** 2.4 GHz
"""
    )

if best_wifi is not None:
    best_ssid, best_avg, best_good, best_quality = best_wifi["SSID"], float(best_wifi["Average RSSI"]), float(best_wifi["Good Signal (%)"]), best_wifi["Quality"]
    recommendation_title = f"Wi-Fi แนะนำสำหรับห้อง {display_room}" if language == "ไทย" else f"Recommended Wi-Fi for {display_room}"
    recommendation_detail = f"RSSI เฉลี่ย {best_avg:.1f} dBm • จุดวัดสัญญาณดี {best_good:.1f}% • คุณภาพ {best_quality}" if language == "ไทย" else f"Average RSSI {best_avg:.1f} dBm • Good measurements {best_good:.1f}% • Quality {best_quality}"

    st.markdown(
        f"""
        <div class="recommend-card">
            <div class="recommend-label">✨ {recommendation_title}</div>
            <div class="recommend-wifi">📶 {best_ssid}</div>
            <div class="recommend-rssi">{recommendation_detail}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

if not wifi.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric(f"📍 {t['survey_points']}", wifi["Point"].nunique())
    c2.metric(f"📡 {t['access_points']}", wifi["BSSID"].nunique())
    c3.metric(f"📈 {t['avg_rssi']}", f"{wifi['RSSI'].mean():.1f} dBm")

    c4, c5, c6 = st.columns(3)
    c4.metric(f"🟢 {t['strong']} (>= -65 dBm)", len(wifi[wifi["RSSI"] >= -65]))
    c5.metric(f"🔴 {t['weak']} (<= -75 dBm)", len(wifi[wifi["RSSI"] <= -75]))
    c6.metric(f"📐 {t['room_size']}", f"{ROOM_X:.2f} × {ROOM_Y:.2f} m")

st.markdown("────────────────────────────────────────────")

# ============================================================
# TABS
# ============================================================
if not wifi.empty:
    tab_overview, tab_map, tab_advisor, tab_analysis, tab_raw = st.tabs(
        ["🏠 Overview" if language == "English" else "🏠 ภาพรวม", t["map"], "🤖 Wi-Fi Advisor", t["analysis"], t["raw"]]
    )

    with tab_overview:
        st.subheader(f"🏠 {'ภาพรวมห้อง' if language == 'ไทย' else 'Room Overview'} {display_room}")
        if not wifi_recommendation.empty:
            overview_table = wifi_recommendation[["SSID", "Average RSSI", "Weakest RSSI", "Good Signal (%)", "Weak Signal (%)", "Score", "Quality"]].copy()
            st.dataframe(overview_table.round(1), use_container_width=True, hide_index=True)

    with tab_advisor:
        st.subheader("🤖 Wi-Fi Advisor")
        advisor_points = sorted(wifi["Point"].dropna().astype(str).unique().tolist())
        if advisor_points:
            selected_point = st.selectbox("📍 เลือกจุดที่กำลังนั่ง", advisor_points, key=f"advisor_point_{selected_room}")
            point_best, point_table = recommend_wifi_at_point(wifi, selected_point)
            if point_best is not None:
                status, description = signal_quality(float(point_best["RSSI"]), language)
                st.info(f"📶 {point_best['SSID']} ({point_best['RSSI']:.1f} dBm) - {status}\n\n{description}")
                st.dataframe(point_table.round(1), use_container_width=True, hide_index=True)

    with tab_map:
        if selected_room == "Room A":
            st.subheader("🏠 3D Wi-Fi RSSI Heatmap — Room A (A1–A4)")
            room_a_fig = create_room_a_combined_heatmap(
                wifi=wifi, opacity=opacity, show_ap=False, show_points=show_points, show_furniture=show_furniture
            )
            room_a_fig = force_white_3d(room_a_fig)
            st.plotly_chart(room_a_fig, use_container_width=True, key="room_a_complete_heatmap", theme=None)

        else:
            st.subheader(f"3D Wi-Fi RSSI Heatmap — {display_room}")
            if selected_room == "Room C":
                fig = create_room_c_heatmap(wifi=wifi, opacity=opacity, show_points=show_points, show_furniture=show_furniture)
            elif selected_room == "Room B":
                fig = create_room_b_heatmap(wifi=wifi, opacity=opacity, show_ap=show_ap, show_points=show_points, show_furniture=show_furniture)
            else:
                fig = create_3d_heatmap(wifi=wifi, room_name=selected_room, room_x=ROOM_X, room_y=ROOM_Y, opacity=opacity, show_ap=show_ap, show_points=show_points, show_furniture=show_furniture)

            fig = force_white_3d(fig)
            st.plotly_chart(fig, use_container_width=True, theme=None)

    with tab_analysis:
        st.subheader("การวิเคราะห์ข้อมูลเชิงลึก (Deep Analysis)")
        col_a, col_b = st.columns(2)
        with col_a:
            ap_counts = wifi.groupby("Point")["BSSID"].nunique().reset_index()
            fig_ap = px.bar(ap_counts, x="Point", y="BSSID", text="BSSID", color="BSSID", color_continuous_scale="Greens")
            st.plotly_chart(fig_ap, use_container_width=True)
        with col_b:
            if "Channel" in wifi.columns:
                fig_ch = px.pie(wifi["Channel"].value_counts().reset_index(), names="Channel", values="count", hole=0.4)
                st.plotly_chart(fig_ch, use_container_width=True)

    with tab_raw:
        st.subheader("📋 ข้อมูลการสำรวจดิบ (Raw Survey Data)")
        st.dataframe(wifi, use_container_width=True, hide_index=True)