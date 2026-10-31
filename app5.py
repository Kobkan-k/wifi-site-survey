import os

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from scipy.interpolate import griddata

# ============================================================
# FORCE ALL PLOTLY 3D CHARTS TO LIGHT / WHITE
# ============================================================
APP_BUILD = "ALL-3D-WHITE-v5-2026-09-24"

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

    # Colorbar text must also be visible on white.
    for trace in fig.data:
        try:
            if getattr(trace, "colorbar", None) is not None:
                trace.colorbar.tickfont = dict(color="#111827")
                trace.colorbar.title.font = dict(color="#111827")
        except Exception:
            pass
    return fig


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Portable Wireless Site Survey and Network Analysis System",
    page_icon="📡",
    layout="wide"
)

# ============================================================
st.markdown("""
<style>
/* Keep the Plotly host transparent/white instead of inheriting dark app theme. */
div[data-testid="stPlotlyChart"],
div[data-testid="stPlotlyChart"] > div {
    background: #FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)

# MODERN DASHBOARD STYLE
# ============================================================

st.markdown("""
<style>
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

    background: linear-gradient(
        90deg,
        #60a5fa,
        #22c55e
    );

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
    background: linear-gradient(
        135deg,
        rgba(34,197,94,0.13),
        rgba(59,130,246,0.08)
    );
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

    "Room A": {
        "file": None,
        "x": 7.20,
        "y": 8.40
    },

    "Room B": {
        "file": "room_B_wifi_data.csv",
        "x": 6.80,
        "y": 9.00
    },

    "Room C": {
        "file": "room_C_wifi_data.csv",
        "x": 2.70,
        "y": 9.00
    },

    "Room 1": {
        "file": "room_1_wifi_data.csv",
        "x": 3.535,
        "y": 4.13
    },

    "Room 2": {
        "file": "room_2_wifi_data.csv",
        "x": 3.57,
        "y": 5.47
    },

    "Room 3": {
        "file": "room_A3_wifi_data.csv",
        "x": 3.535,
        "y": 4.20
    },

    "Room 4": {
        "file": "room_A4_wifi_data.csv",
        "x": 3.57,
        "y": 2.83
    }
}


# ============================================================
# GENERAL 3D SETTINGS
# ============================================================

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

        rename_mapping = {
            "Point ID": "Point", "Point": "Point",
            "X (m)": "X", "X": "X",
            "Y (m)": "Y", "Y": "Y",
            "RSSI (dBm)": "RSSI", "RSSI_dBm": "RSSI", "RSSI": "RSSI",
            "Frequency (MHz)": "Frequency", "Frequency": "Frequency",
            "Channel": "Channel", "channel": "Channel",
            "SSID": "SSID", "BSSID": "BSSID", "Band": "Band"
        }

        df.rename(columns=rename_mapping, inplace=True)

        required_columns = ["Point", "X", "Y", "SSID", "BSSID", "RSSI"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            st.error("❌ ไม่พบ Column ที่จำเป็น: " + ", ".join(missing_columns))
            st.info("Column ที่พบในไฟล์: " + ", ".join(df.columns.tolist()))
            return pd.DataFrame()

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
    if os.path.exists(filename):
        return filename
    return None


def get_room_size(df, room_name):
    config = ROOMS[room_name]
    room_x = config["x"]
    room_y = config["y"]

    if room_x is not None and room_y is not None:
        return room_x, room_y

    if df is not None and not df.empty:
        room_x = float(df["X"].max())
        room_y = float(df["Y"].max())
    else:
        room_x = 5.0
        room_y = 5.0
    return room_x, room_y


def create_room_b_heatmap(wifi, opacity=0.80, show_ap=True, show_points=True, show_furniture=True):
    """Room B: 6.80 x 9.00 m based on the supplied Room B model."""
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
        GZ = np.clip(GZ, float(d["RSSI"].min()), float(d["RSSI"].max()))

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=np.zeros_like(GZ)+0.01,
            surfacecolor=GZ,
            colorscale="Jet",
            cmin=float(d["RSSI"].min()), cmax=float(d["RSSI"].max()), opacity=opacity, showscale=True,
            colorbar=dict(title="RSSI (dBm)", len=0.65),
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
            marker=dict(size=5, color="#1F2937", symbol="circle",
                        line=dict(color="white", width=1)),
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
            x=[AP_X_B], y=[AP_Y_B], z=[AP_H_B],
            mode="markers+text",
            marker=dict(size=14, color="#FF2020", symbol="diamond",
                        line=dict(color="white", width=2)),
            text=["AP"], textposition="top center",
            name="Access Point"
        ))
        fig.add_trace(go.Scatter3d(
            x=[AP_X_B, AP_X_B], y=[AP_Y_B, AP_Y_B], z=[0, AP_H_B],
            mode="lines", line=dict(color="#FF3030", width=4, dash="dash"),
            hoverinfo="skip", showlegend=False
        ))

    def wall(x1,y1,x2,y2,height,z_bottom=0):
        fig.add_trace(go.Mesh3d(
            x=[x1,x2,x2,x1,x1,x2,x2,x1],
            y=[y1,y2,y2,y1,y1,y2,y2,y1],
            z=[z_bottom]*4+[height]*4,
            i=[0,0,0,4,4,4], j=[1,2,3,5,6,7], k=[2,3,4,6,7,5],
            color="#8A8A8A", opacity=0.72,
            hoverinfo="skip", showlegend=False
        ))

    wall(0,0,RX,0,WH)
    wall(0,0,0,RY,WH)
    wall(RX,0,RX,RY,WH)

    door_mid, door_w, door_h = 1.70, 1.98, 2.05
    dx1, dx2 = door_mid-door_w/2, door_mid+door_w/2
    wall(0,RY,dx1,RY,WH)
    wall(dx2,RY,RX,RY,WH)
    wall(dx1,RY,dx2,RY,WH,door_h)

    for xx, width in [(dx1,8),(dx2,8),(door_mid,4)]:
        fig.add_trace(go.Scatter3d(
            x=[xx,xx], y=[RY-0.02,RY-0.02], z=[0,door_h],
            mode="lines", line=dict(color="#444",width=width),
            hoverinfo="skip",showlegend=False
        ))

    def box(xmin,xmax,ymin,ymax,zmin,zmax,color,op,name):
        fig.add_trace(go.Mesh3d(
            x=[xmin,xmax,xmax,xmin,xmin,xmax,xmax,xmin],
            y=[ymin,ymin,ymax,ymax,ymin,ymin,ymax,ymax],
            z=[zmin,zmin,zmin,zmin,zmax,zmax,zmax,zmax],
            i=[7,0,0,0,4,4,2,6,4,0,3,7],
            j=[3,4,1,2,5,6,3,7,5,1,2,6],
            k=[0,7,2,3,6,7,7,4,1,5,6,5],
            color=color,opacity=op,name=name,
            hoverinfo="name",showlegend=False
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
        y1,y2=flip_y(7.50,8.44)
        box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 1")
        y1,y2=flip_y(0.50,1.44)
        box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 10")

        for item,(ymin,ymax) in zip(
            [11,12,13,14,15,16],
            [(7.00,7.78),(6.20,6.98),(4.40,5.18),
             (3.60,4.38),(1.80,2.58),(1.00,1.78)]
        ):
            y1,y2=flip_y(ymin,ymax)
            table(RX-1.84,RX,y1,y2,f"Table {item}")

        grouped=[
            (2,0,1.84,5.40,6.18),(4,1.84,3.68,5.40,6.18),
            (3,0,1.84,4.60,5.38),(5,1.84,3.68,4.60,5.38),
            (6,0,1.84,2.60,3.38),(8,1.84,3.68,2.60,3.38),
            (7,0,1.84,1.80,2.58),(9,1.84,3.68,1.80,2.58)
        ]
        for item,x1,x2,ymin,ymax in grouped:
            y1,y2=flip_y(ymin,ymax)
            table(x1,x2,y1,y2,f"Table {item}")

        ox1,ox2 = RX-2.10, RX-2.88
        oy1,oy2 = flip_y(0.0,0.78)
        box(min(ox1,ox2),max(ox1,ox2),oy1,oy2,0,0.80,
            "#78909C",0.88,"Object 17")

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


def create_room_c_heatmap(wifi, opacity=0.80, show_points=True, show_furniture=True):
    ROOM_X = 2.70
    ROOM_Y = 9.00
    WALL_HEIGHT = 3.0
    WALL_THICKNESS = 0.12

    DOOR_EACH_W = 0.99
    DOOR_TOTAL_W = DOOR_EACH_W * 2
    DOOR_H = 2.05

    DOOR_X_START = (ROOM_X - DOOR_TOTAL_W) / 2
    DOOR_X_END = DOOR_X_START + DOOR_TOTAL_W

    ROOMS = {
        "1": {
            "x_min": 0.0,
            "x_max": ROOM_X,
            "y_min": 0.0,
            "y_max": ROOM_Y,
            "color": "#E5E7EB"
        }
    }

    FONT_FAMILY = "Arial"
    FONT_SIZE = 10
    FONT_COLOR = "#4B5563"  

    MARKER_HEIGHT = 0.15
    TEXT_HEIGHT = 1.05

    fig = go.Figure()

    def add_room_floor(room_name, room):
        x1, x2 = room["x_min"], room["x_max"]
        y1, y2 = room["y_min"], room["y_max"]
        fig.add_trace(go.Mesh3d(
            x=[x1, x2, x2, x1],
            y=[y1, y1, y2, y2],
            z=[0, 0, 0, 0],
            i=[0, 0],
            j=[1, 2],
            k=[2, 3],
            color=room["color"],
            opacity=0.8,
            name=f"Room {room_name} Floor",
            hoverinfo="skip",
            showlegend=True
        ))

    def add_wall(x1, y1, x2, y2, height=WALL_HEIGHT, z0=0):
        dx = x2 - x1
        dy = y2 - y1
        length = np.sqrt(dx**2 + dy**2)
        if length == 0:
            return
        nx = -dy / length * WALL_THICKNESS / 2
        ny = dx / length * WALL_THICKNESS / 2
        points = [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)]
        x = [p[0] for p in points] * 2
        y = [p[1] for p in points] * 2
        z = [z0, z0, z0, z0, z0 + height, z0 + height, z0 + height, z0 + height]
        fig.add_trace(go.Mesh3d(
            x=x, y=y, z=z,
            i=[0,0,4,4,0,0,2,2,0,0,1,1],
            j=[1,2,5,6,1,5,3,7,3,7,2,6],
            k=[2,3,6,7,5,4,7,6,7,4,6,5],
            color="#93C5FD", opacity=0.06, hoverinfo="skip", showlegend=False
        ))

    add_room_floor("Main", ROOMS["1"])
    add_wall(0, 0, 0, ROOM_Y)
    add_wall(ROOM_X, 0, ROOM_X, ROOM_Y)
    add_wall(0, 0, ROOM_X, 0)
    add_wall(0, ROOM_Y, DOOR_X_START, ROOM_Y)
    add_wall(DOOR_X_END, ROOM_Y, ROOM_X, ROOM_Y)
    add_wall(DOOR_X_START, ROOM_Y, DOOR_X_END, ROOM_Y, height=WALL_HEIGHT - DOOR_H, z0=DOOR_H)

    def add_room_heatmap(room_name, room_data):
        room = ROOMS[room_name]
        x_min, x_max = room["x_min"], room["x_max"]
        y_min, y_max = room["y_min"], room["y_max"]
        x_values = np.asarray(room_data["X"], dtype=float)
        y_values = np.asarray(room_data["Y"], dtype=float)
        rssi_values = np.asarray(room_data["RSSI"], dtype=float)
        grid_x = np.linspace(x_min, x_max, 80)
        grid_y = np.linspace(y_min, y_max, 120)
        GX, GY = np.meshgrid(grid_x, grid_y)
        GZ = griddata((x_values, y_values), rssi_values, (GX, GY), method="cubic")
        nearest_grid = griddata((x_values, y_values), rssi_values, (GX, GY), method="nearest")
        GZ = np.where(np.isnan(GZ), nearest_grid, GZ)
        rssi_min = float(np.min(rssi_values))
        rssi_max = float(np.max(rssi_values))

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=np.full_like(GZ, 0.1), surfacecolor=GZ,
            colorscale="Jet", cmin=rssi_min, cmax=rssi_max, opacity=opacity, showscale=True,
            colorbar=dict(title=dict(text="RSSI (dBm)", font=dict(color="#111827", size=13, family=FONT_FAMILY)),
                          tickfont=dict(color="#111827", size=11, family=FONT_FAMILY), x=1.02),
            name="Heatmap", hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<extra></extra>"
        ))

        if show_points:
            fig.add_trace(go.Scatter3d(
                x=x_values, y=y_values, z=np.full(len(x_values), MARKER_HEIGHT),
                mode="markers", marker=dict(size=6, color="#1F2937", line=dict(width=1, color="#FFFFFF")),
                customdata=[f"P{i:02d}" for i in range(1, len(x_values) + 1)],
                hovertemplate="X: %{x:.2f} m<br>Y: %{y:.2f} m<extra></extra>",
                name="Survey Points", showlegend=False
            ))

        labels = [f"P{i:02d}" for i in range(1, len(x_values) + 1)]
        label_x, label_y = [], []
        for idx, (xx, yy) in enumerate(zip(x_values, y_values)):
            col = int(np.argmin(np.abs(np.array([0, ROOM_X / 2, ROOM_X]) - xx)))
            row = int(np.argmin(np.abs(np.array([0, ROOM_Y / 2, ROOM_Y]) - yy)))
            dx = [0.27, 0.0, -0.27][col]
            dy = [0.38, 0.0, -0.38][row]
            label_x.append(float(np.clip(xx + dx, 0.25, ROOM_X - 0.25)))
            label_y.append(float(np.clip(yy + dy, 0.30, ROOM_Y - 0.30)))

        if show_points:
            fig.add_trace(go.Scatter3d(
                x=label_x, y=label_y, z=np.full(len(x_values), TEXT_HEIGHT),
                mode="text", text=labels, textposition="middle center",
                textfont=dict(family=FONT_FAMILY, size=FONT_SIZE, color=FONT_COLOR),
                hoverinfo="skip", name="Point Labels", showlegend=False
            ))

    real_data = {
        "X": [0.00, 1.35, 2.70, 0.00, 1.35, 2.70, 0.00, 1.35, 2.70],
        "Y": [0.00, 0.00, 0.00, 4.50, 4.50, 4.50, 9.00, 9.00, 9.00],
        "RSSI": [-82, -90, -84, -77, -67, -58, -77, -84, -75]
    }
    if wifi is not None and not wifi.empty and {"X", "Y", "RSSI"}.issubset(wifi.columns):
        measurements = wifi.dropna(subset=["X", "Y", "RSSI"])
        real_data = {key: measurements[key].to_numpy() for key in ("X", "Y", "RSSI")}

    add_room_heatmap("1", real_data)

    def add_box(x, y, z, w, l, h, color, name, opacity=1.0):
        x0, x1 = x - w / 2, x + w / 2
        y0, y1 = y - l / 2, y + l / 2
        z0, z1 = z, z + h
        xs = [x0, x1, x1, x0, x0, x1, x1, x0]
        ys = [y0, y0, y1, y1, y0, y0, y1, y1]
        zs = [z0, z0, z0, z0, z1, z1, z1, z1]
        i = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1]
        j = [1, 2, 5, 6, 1, 5, 3, 7, 3, 7, 2, 6]
        k = [2, 3, 6, 7, 5, 4, 7, 6, 7, 4, 6, 5]
        fig.add_trace(go.Mesh3d(x=xs, y=ys, z=zs, i=i, j=j, k=k, color=color, opacity=opacity, name=name, hoverinfo="name", showlegend=False))

    def add_table(name, x, y, z, w, l, h):
        top_color, leg_color = "#D4A373", "#582F0E"
        top_thickness, leg_size = 0.05, 0.06
        add_box(x, y, z + h - top_thickness, w, l, top_thickness, top_color, f"{name} (Top)")
        leg_positions = [(x - w/2 + leg_size/2, y - l/2 + leg_size/2), (x + w/2 - leg_size/2, y - l/2 + leg_size/2),
                         (x + w/2 - leg_size/2, y + l/2 - leg_size/2), (x - w/2 + leg_size/2, y + l/2 - leg_size/2)]
        for leg_x, leg_y in leg_positions:
            add_box(leg_x, leg_y, z, leg_size, leg_size, h - top_thickness, leg_color, f"{name} (Leg)")

    def add_glass_swing_door(name, hinge_x, hinge_y, w, h, t, angle_deg, is_left=True):
        angle = np.radians(angle_deg if is_left else -angle_deg)
        px1, py1 = hinge_x, hinge_y
        px2 = hinge_x + w * np.cos(angle)
        py2 = hinge_y + w * np.sin(angle)
        if is_left:
            px3, py3 = px2 - t * np.sin(angle), py2 + t * np.cos(angle)
            px4, py4 = px1 - t * np.sin(angle), py1 + t * np.cos(angle)
        else:
            px3, py3 = px2 + t * np.sin(angle), py2 - t * np.cos(angle)
            px4, py4 = px1 + t * np.sin(angle), py1 - t * np.cos(angle)
        xs, ys, zs = [px1, px2, px3, px4, px1, px2, px3, px4], [py1, py2, py3, py4, py1, py2, py3, py4], [0, 0, 0, 0, h, h, h, h]
        i, j, k = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1], [1, 2, 5, 6, 1, 5, 3, 7, 3, 7, 2, 6], [2, 3, 6, 7, 5, 4, 7, 6, 7, 4, 6, 5]
        fig.add_trace(go.Mesh3d(x=xs, y=ys, z=zs, i=i, j=j, k=k, color="#0EA5E9", opacity=0.35, name=name, hoverinfo="name", showlegend=False))

    add_glass_swing_door("Left Glass Door", hinge_x=DOOR_X_START, hinge_y=ROOM_Y, w=DOOR_EACH_W, h=DOOR_H, t=0.02, angle_deg=-45, is_left=True)
    add_glass_swing_door("Right Glass Door", hinge_x=DOOR_X_END, hinge_y=ROOM_Y, w=DOOR_EACH_W, h=DOOR_H, t=0.02, angle_deg=225, is_left=True)

    T_WIDTH, T_LENGTH, T_HEIGHT = 0.73, 1.83, 0.80
    center_x = ROOM_X / 2
    door_y = ROOM_Y
    distance_from_door = 0.60
    table1_y = door_y - distance_from_door - T_LENGTH / 2
    add_table("Table 1", center_x, table1_y, 0, T_WIDTH, T_LENGTH, T_HEIGHT)
    table2_y = table1_y - T_LENGTH
    add_table("Table 2", center_x, table2_y, 0, T_WIDTH, T_LENGTH, T_HEIGHT)
    GAP = 0.50
    table3_y = table2_y - T_LENGTH - GAP
    add_table("Table 3", center_x, table3_y, 0, T_WIDTH, T_LENGTH, T_HEIGHT)
    table4_y = table3_y - T_LENGTH
    add_table("Table 4", center_x, table4_y, 0, T_WIDTH, T_LENGTH, T_HEIGHT)

    fig.update_layout(
        title=dict(text="3D Wi-Fi RSSI Heatmap", x=0.5, font=dict(size=20, color="#111827", family=FONT_FAMILY)),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", font=dict(family=FONT_FAMILY, color="#111827"),
        scene=dict(bgcolor="#F8FAFC",
                   xaxis=dict(title=dict(text="X (m)", font=dict(color="#111827")), range=[-0.5, ROOM_X + 0.5], gridcolor="#CBD5E1", zerolinecolor="#64748B", tickfont=dict(color="#111827")),
                   yaxis=dict(title=dict(text="Y (m)", font=dict(color="#111827")), range=[-0.5, ROOM_Y + 0.5], gridcolor="#CBD5E1", zerolinecolor="#64748B", tickfont=dict(color="#111827")),
                   zaxis=dict(title=dict(text="Height (m)", font=dict(color="#111827")), range=[0, WALL_HEIGHT + 0.5], gridcolor="#CBD5E1", zerolinecolor="#64748B", tickfont=dict(color="#111827")),
                   aspectmode="manual", aspectratio=dict(x=2.7, y=9.0, z=3.0), camera=dict(eye=dict(x=1.5, y=1.5, z=1.0))),
        width=1350, height=850, margin=dict(l=0, r=0, t=70, b=0)
    )

    if not show_points:
        fig.data = tuple(t for t in fig.data if t.name not in ("Survey Points", "RSSI Labels"))
    if not show_furniture:
        fig.data = tuple(t for t in fig.data if t.type == "surface" or t.name in ("Room Main Floor", "Survey Points", "RSSI Labels"))
    return fig


def create_3d_heatmap(wifi, room_name, room_x, room_y, opacity, show_ap, show_points, show_furniture):
    heatmap_data = wifi.groupby(["X", "Y"])["RSSI"].max().reset_index()
    grid_x = np.linspace(0, room_x, 180)
    grid_y = np.linspace(0, room_y, 240)
    GX, GY = np.meshgrid(grid_x, grid_y)
    points = heatmap_data[["X", "Y"]].values
    values = heatmap_data["RSSI"].values

    GZ = None
    if len(points) >= 4:
        try:
            GZ = griddata(points, values, (GX, GY), method="cubic")
        except Exception:
            GZ = None
    if GZ is None and len(points) >= 3:
        try:
            GZ = griddata(points, values, (GX, GY), method="linear")
        except Exception:
            GZ = None

    nearest = griddata(points, values, (GX, GY), method="nearest")
    if GZ is None:
        GZ = nearest
    else:
        GZ = np.where(np.isnan(GZ), nearest, GZ)

    GZ = np.clip(GZ, -90, -50)
    custom_scale = [[0.000, "#ef4444"], [0.375, "#f97316"], [0.625, "#eab308"], [1.000, "#22c55e"]]
    fig = go.Figure()

    fig.add_trace(go.Surface(
        x=GX, y=GY, z=np.zeros_like(GZ) + 0.01, surfacecolor=GZ, colorscale=custom_scale, cmin=-90, cmax=-50, opacity=opacity, showscale=True,
        colorbar=dict(title=dict(text="<b>RSSI</b><br>(dBm)"), tickvals=[-90, -73, -65, -50], ticktext=["-90 (Weak)", "-73", "-65", "-50 (Strong)"], len=0.75, thickness=20, outlinewidth=0),
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

    if show_ap:
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
# ROOM A — COMBINED 3D HEATMAP (UPDATED LOGIC)
# ============================================================
ROOM_A_LAYOUT = {
    "A1": {"room_key": "Room 1", "x_min": 0.0,   "x_max": 3.535, "y_min": 4.20, "y_max": 8.33},
    "A2": {"room_key": "Room 2", "x_min": 3.535, "x_max": 7.105, "y_min": 2.83, "y_max": 8.30},
    "A3": {"room_key": "Room 3", "x_min": 0.0,   "x_max": 3.535, "y_min": 0.0,  "y_max": 4.20},
    "A4": {"room_key": "Room 4", "x_min": 3.535, "x_max": 7.105, "y_min": 0.0,  "y_max": 2.83},
}

ROOM_A_FALLBACK_DATA = {
    'Room 1': pd.DataFrame({'Point': ['P01', 'P02', 'P03', 'P04', 'P05', 'P06', 'P07', 'P08', 'P09'], 'X': [0.0, 1.77, 3.54, 0.0, 1.77, 3.54, 0.0, 1.77, 3.54], 'Y': [0.0, 0.0, 0.0, 2.07, 2.07, 2.07, 4.13, 4.13, 4.13], 'RSSI': [-70, -64, -68, -68, -74, -70, -77, -68, -75]}),
    'Room 2': pd.DataFrame({'Point': ['P10', 'P11', 'P12', 'P13', 'P14', 'P15', 'P16', 'P17', 'P18', 'P19', 'P20', 'P21'], 'X': [0.0, 1.78, 3.57, 0.0, 1.78, 3.57, 0.0, 1.78, 3.57, 0.0, 1.78, 3.57], 'Y': [0.0, 0.0, 0.0, 1.82, 1.82, 1.82, 3.65, 3.65, 3.65, 5.47, 5.47, 5.47], 'RSSI': [-50, -66, -81, -85, -71, -75, -50, -70, -70, -70, -69, -71]}),
    'Room 3': pd.DataFrame({'Point': ['P22', 'P23', 'P24', 'P25', 'P26', 'P27', 'P28', 'P29', 'P30'], 'X': [0.0, 1.77, 3.54, 0.0, 1.77, 3.54, 0.0, 1.77, 3.54], 'Y': [0.0, 0.0, 0.0, 2.1, 2.1, 2.1, 4.2, 4.2, 4.2], 'RSSI': [-74, -62, -71, -63, -69, -70, -67, -60, -64]}),
    'Room 4': pd.DataFrame({'Point': ['P31', 'P32', 'P33', 'P34', 'P35', 'P36', 'P37', 'P38', 'P39'], 'X': [0.0, 1.78, 3.57, 0.0, 1.78, 3.57, 0.0, 1.78, 3.57], 'Y': [0.0, 0.0, 0.0, 1.41, 1.41, 1.41, 2.83, 2.83, 2.83], 'RSSI': [-73, -67, -74, -63, -66, -70, -64, -66, -75]}),
}

def _load_room_a_csv(room_key):
    filename = ROOMS[room_key]["file"]
    if not filename or not os.path.exists(filename):
        return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()
    try:
        d = pd.read_csv(filename, skipinitialspace=True)
        d.columns = d.columns.astype(str).str.strip()
        d.rename(columns={"Point ID": "Point", "X (m)": "X", "Y (m)": "Y", "RSSI (dBm)": "RSSI", "RSSI_dBm": "RSSI", "Frequency (MHz)": "Frequency", "channel": "Channel"}, inplace=True)
        for col in ["X", "Y", "RSSI", "Channel"]:
            if col in d.columns: d[col] = pd.to_numeric(d[col], errors="coerce")
        if not {"X", "Y", "RSSI"}.issubset(d.columns): return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()
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
        else: d["Point"] = label + "-" + d["Point"].astype(str)
        if "SSID" not in d.columns: d["SSID"] = "KMITL-WIFI"
        if "BSSID" not in d.columns: d["BSSID"] = label + "-AP"
        frames.append(d)
    if not frames: return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def create_room_a_combined_heatmap(wifi=None, opacity=0.85, show_ap=True, show_points=True, show_furniture=True):
    ROOM_X, ROOM_Y = 7.20, 8.40
    WALL_HEIGHT, WALL_THICKNESS = 3.0, 0.12
    WALL_COLOR = '#93C5FD'
    WALL_OPACITY = 0.06
    FONT_FAMILY = 'Arial'
    POINT_FONT_SIZE, POINT_FONT_COLOR = 11, '#4B5563'
    ROOM_FONT_SIZE, ROOM_FONT_COLOR = 16, '#4B5563'
    POINT_HEIGHT, TEXT_HEIGHT = 0.25, 0.35 
    HEATMAP_COLORSCALE, HEATMAP_OPACITY, HEATMAP_RESOLUTION = 'Jet', opacity, 80

    ROOM_CONFIGS = {
        '1': {'x_min': 0., 'x_max': 3.535, 'y_min': 4.20, 'y_max': 8.33, 'color': '#E5E7EB'},
        '2': {'x_min': 3.535, 'x_max': 7.105, 'y_min': 2.83, 'y_max': 8.30, 'color': '#E5E7EB'},
        '3': {'x_min': 0., 'x_max': 3.535, 'y_min': 0., 'y_max': 4.20, 'color': '#E5E7EB'},
        '4': {'x_min': 3.535, 'x_max': 7.105, 'y_min': 0., 'y_max': 2.83, 'color': '#E5E7EB'},
    }

    # Original measurement data fallback mappings
    room_a_data = {'X':[0,1.77,3.54,0,1.77,3.54,0,1.77,3.54], 'Y':[4.20,4.20,4.20,6.27,6.27,6.27,8.33,8.33,8.33], 'RSSI':[-70,-64,-68,-68,-74,-70,-77,-68,-75]}
    room_b_data = {'X':[3.535,5.315,7.105]*4, 'Y':[2.83]*3+[4.65]*3+[6.48]*3+[8.30]*3, 'RSSI':[-50,-66,-81,-85,-71,-75,-50,-70,-70,-70,-69,-71]}
    room_c_data = {'X':[0,1.77,3.54]*3, 'Y':[0]*3+[2.10]*3+[4.20]*3, 'RSSI':[-74,-62,-71,-63,-69,-70,-67,-60,-64]}
    room_d_data = {'X':[3.535,5.315,7.105]*3, 'Y':[0]*3+[1.41]*3+[2.83]*3, 'RSSI':[-73,-67,-74,-63,-66,-70,-64,-66,-75]}
    
    ROOM_DATA = {'1':room_a_data, '2':room_b_data, '3':room_c_data, '4':room_d_data}

    # Override with dataframe if passed from Streamlit UI
    if wifi is not None and not wifi.empty and {"X", "Y", "RSSI"}.issubset(wifi.columns):
        for k in ROOM_DATA.keys():
            ROOM_DATA[k] = {'X': [], 'Y': [], 'RSSI': []}
            
        for _, row in wifi.dropna(subset=["X", "Y", "RSSI"]).iterrows():
            x, y, rssi = float(row['X']), float(row['Y']), float(row['RSSI'])
            if x <= 3.535 and y >= 4.20: r = '1'
            elif x > 3.535 and y >= 2.83: r = '2'
            elif x <= 3.535 and y < 4.20: r = '3'
            else: r = '4'
            ROOM_DATA[r]['X'].append(x)
            ROOM_DATA[r]['Y'].append(y)
            ROOM_DATA[r]['RSSI'].append(rssi)

    all_rssi_lists = [np.asarray(d['RSSI'],dtype=float) for d in ROOM_DATA.values() if len(d['RSSI'])>0]
    if all_rssi_lists:
        all_rssi = np.concatenate(all_rssi_lists)
        RSSI_MIN, RSSI_MAX = float(all_rssi.min()), float(all_rssi.max())
    else:
        RSSI_MIN, RSSI_MAX = -90.0, -30.0

    fig = go.Figure()

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

    for room_name, room in ROOM_CONFIGS.items():
        add_room_floor(room_name, room)

    def add_wall(x1,y1,x2,y2,height=WALL_HEIGHT,z0=0):
        dx,dy=x2-x1,y2-y1
        length=np.hypot(dx,dy)
        if length == 0 or height <= 0: return
        nx,ny=-dy/length*WALL_THICKNESS/2,dx/length*WALL_THICKNESS/2
        pts=[(x1+nx,y1+ny),(x2+nx,y2+ny),(x2-nx,y2-ny),(x1-nx,y1-ny)]
        xs=[p[0] for p in pts]*2
        ys=[p[1] for p in pts]*2
        zs=[z0]*4+[z0+height]*4
        faces=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),
               (0,4,5),(0,5,1),(1,5,6),(1,6,2),
               (2,6,7),(2,7,3),(3,7,4),(3,4,0)]
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=[f[0] for f in faces],
                                j=[f[1] for f in faces],k=[f[2] for f in faces],
                                color=WALL_COLOR,opacity=WALL_OPACITY,hoverinfo='skip',showlegend=False))

    add_wall(0,0,1.03,0)
    add_wall(2.97,0,ROOM_X,0)
    add_wall(1.03,0,2.97,0,height=WALL_HEIGHT-2.06,z0=2.06)
    add_wall(0,0,0,ROOM_Y)
    add_wall(ROOM_X,0,ROOM_X,ROOM_Y)
    add_wall(0,ROOM_Y,ROOM_X,ROOM_Y)
    DOOR_1_W,DOOR_1_H,DOOR_1_X=0.97,2.06,2.45
    add_wall(0,4.20,DOOR_1_X,4.20)
    add_wall(DOOR_1_X+DOOR_1_W,4.20,3.535,4.20)
    add_wall(DOOR_1_X,4.20,DOOR_1_X+DOOR_1_W,4.20,height=WALL_HEIGHT-DOOR_1_H,z0=DOOR_1_H)
    add_wall(3.535,2.83,7.105,2.83)
    add_wall(3.535,4.20,3.535,8.33)
    add_wall(3.535,0,3.535,1.86)
    add_wall(3.535,1.86,3.535,2.83,height=WALL_HEIGHT-2.06,z0=2.06)
    DOOR_2_W,DOOR_2_H,DOOR_2_Y=0.97,2.06,3.03
    add_wall(3.535,2.83,3.535,DOOR_2_Y)
    add_wall(3.535,DOOR_2_Y+DOOR_2_W,3.535,4.20)
    add_wall(3.535,DOOR_2_Y,3.535,DOOR_2_Y+DOOR_2_W,height=WALL_HEIGHT-DOOR_2_H,z0=DOOR_2_H)

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

    def add_room_heatmap(room_name, room_data, start_point=1):
        if not room_data or len(room_data.get('X', [])) == 0: return
        room=ROOM_CONFIGS[room_name]
        xv=np.asarray(room_data['X'],dtype=float)
        yv=np.asarray(room_data['Y'],dtype=float)
        rv=np.asarray(room_data['RSSI'],dtype=float)

        gx=np.linspace(room['x_min'],room['x_max'],HEATMAP_RESOLUTION)
        gy=np.linspace(room['y_min'],room['y_max'],HEATMAP_RESOLUTION)
        GX,GY=np.meshgrid(gx,gy)

        try:
            GZ=griddata((xv,yv),rv,(GX,GY),method='cubic')
        except Exception:
            GZ = None
            
        nearest=griddata((xv,yv),rv,(GX,GY),method='nearest')
        if GZ is not None:
            GZ=np.where(np.isnan(GZ),nearest,GZ)
        else:
            GZ = nearest

        Z_PLANE = np.full_like(GZ, 0.20)

        fig.add_trace(go.Surface(x=GX,y=GY,z=Z_PLANE,surfacecolor=GZ,
                                 colorscale=HEATMAP_COLORSCALE,cmin=RSSI_MIN,cmax=RSSI_MAX,
                                 opacity=HEATMAP_OPACITY,showscale=(room_name=='1'),
                                 colorbar=dict(title=dict(text='RSSI (dBm)',font=dict(family=FONT_FAMILY,size=13,color='#111827')),
                                               tickfont=dict(family=FONT_FAMILY,size=11,color='#111827'),x=1.02),
                                 name=f'Heatmap Room {room_name}',
                                 hovertemplate='X: %{x:.2f} m<br>Y: %{y:.2f} m<br>RSSI: %{surfacecolor:.1f} dBm<extra></extra>'))

        if show_points:
            point_labels=[f'P{i:02d}' for i in range(start_point,start_point+len(xv))]

            fig.add_trace(go.Scatter3d(x=xv,y=yv,z=np.full(len(xv),POINT_HEIGHT),mode='markers',
                                       marker=dict(size=4,color='#1F2937',line=dict(width=1,color='white')),
                                       customdata=np.column_stack((point_labels, rv)),
                                       hovertemplate='Point: %{customdata[0]}<br>X: %{x:.2f} m<br>Y: %{y:.2f} m<br>RSSI: %{customdata[1]} dBm<extra></extra>',
                                       name=f'Survey Points Room {room_name}',showlegend=False))

            lx,ly=place_labels(xv,yv,room)
            fig.add_trace(go.Scatter3d(x=lx,y=ly,z=np.full(len(lx),TEXT_HEIGHT),mode='text',
                                       text=point_labels,textposition='middle center',
                                       textfont=dict(family=FONT_FAMILY,size=POINT_FONT_SIZE,color=POINT_FONT_COLOR),
                                       hoverinfo='skip',name=f'Point Labels Room {room_name}',showlegend=False))

    add_room_heatmap('1', ROOM_DATA.get('1', {}), 1)
    add_room_heatmap('2', ROOM_DATA.get('2', {}), 1)
    add_room_heatmap('3', ROOM_DATA.get('3', {}), 1)
    add_room_heatmap('4', ROOM_DATA.get('4', {}), 1)

    if show_furniture:
        def add_box(x,y,z,w,l,h,color,name):
            x0,x1=x-w/2,x+w/2
            y0,y1=y-l/2,y+l/2
            z0,z1=z,z+h
            xs=[x0,x1,x1,x0,x0,x1,x1,x0]
            ys=[y0,y0,y1,y1,y0,y0,y1,y1]
            zs=[z0,z0,z0,z0,z1,z1,z1,z1]
            i=[0,0,4,4,0,0,2,2,0,0,1,1]
            j=[1,2,5,6,1,5,3,7,3,7,2,6]
            k=[2,3,6,7,5,4,7,6,7,4,6,5]
            fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=i,j=j,k=k,color=color,opacity=1.,name=name,hoverinfo='name',showlegend=False))

        def add_table(name,x,y,z,w,l,h):
            top_color,leg_color='#D4A373','#582F0E'
            top_thickness,leg_size=0.05,0.06
            add_box(x,y,z+h-top_thickness,w,l,top_thickness,top_color,f'{name} (Top)')
            for sx in (-1,1):
                for sy in (-1,1):
                    add_box(x+sx*(w/2-leg_size/2),y+sy*(l/2-leg_size/2),z,
                            leg_size,leg_size,h-top_thickness,leg_color,f'{name} (Leg)')

        def add_cabinet(name,x,y,z,w,l,h):
            add_box(x,y,z,w,l,h,'#A0522D',name)

        def add_glass_swing_door(name,hinge_x,hinge_y,w,h,t,angle_deg):
            a=np.radians(angle_deg)
            px1,py1=hinge_x,hinge_y
            px2,py2=hinge_x+w*np.cos(a),hinge_y+w*np.sin(a)
            px3,py3=px2-t*np.sin(a),py2+t*np.cos(a)
            px4,py4=px1-t*np.sin(a),py1+t*np.cos(a)
            xs=[px1,px2,px3,px4]*2
            ys=[py1,py2,py3,py4]*2
            zs=[0]*4+[h]*4
            i=[0,0,4,4,0,0,2,2,0,0,1,1]
            j=[1,2,5,6,1,5,3,7,3,7,2,6]
            k=[2,3,6,7,5,4,7,6,7,4,6,5]
            fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=i,j=j,k=k,color='#38BDF8',opacity=0.45,name=name,hoverinfo='name',showlegend=False))

        def add_sliding_door(name,x,y,length,t,h,orientation='horizontal'):
            if orientation=='horizontal':
                x0,x1=x,x+length
                y0,y1=y-t/2,y+t/2
            else:
                x0,x1=x-t/2,x+t/2
                y0,y1=y,y+length
            xs=[x0,x1,x1,x0]*2
            ys=[y0,y0,y1,y1]*2
            zs=[0]*4+[h]*4
            i=[0,0,4,4,0,0,2,2,0,0,1,1]
            j=[1,2,5,6,1,5,3,7,3,7,2,6]
            k=[2,3,6,7,5,4,7,6,7,4,6,5]
            fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,i=i,j=j,k=k,color='#38BDF8',opacity=0.45,name=name,hoverinfo='name',showlegend=False))

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
        CABINET_W,CABINET_L,CABINET_H=0.49,0.95,1.86
        cabinet_x_pos=WALL_THICKNESS/2+CABINET_W/2
        cabinet_y_pos=4.20-WALL_THICKNESS/2-CABINET_L/2
        add_cabinet('Cabinet (Room 3)',cabinet_x_pos,cabinet_y_pos,0,CABINET_W,CABINET_L,CABINET_H)
        add_glass_swing_door('Left Swing Door (Room 3)',hinge_x=1.03,hinge_y=0.,w=0.97,h=2.06,t=0.02,angle_deg=45)
        add_glass_swing_door('Right Swing Door (Room 3)',hinge_x=2.97,hinge_y=0.,w=0.97,h=2.06,t=0.02,angle_deg=135)

        # Room 4
        center_x4,center_y4=(3.535+7.105)/2,(0.+2.83)/2
        add_table('Table 1 (Room 4)',center_x4,center_y4+T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        add_table('Table 2 (Room 4)',center_x4,center_y4-T_WIDTH/2,0,T_LENGTH,T_WIDTH,T_HEIGHT)
        DOOR_4_X=3.535-(WALL_THICKNESS/2+0.01)
        add_sliding_door('Sliding Door (Room 4)',x=DOOR_4_X,y=1.86,length=0.97,t=0.04,h=2.06,orientation='vertical')

    fig.update_layout(
        title=dict(text='3D Wi-Fi RSSI Heatmap',x=0.5,font=dict(size=22,color='#111827',family=FONT_FAMILY)),
        paper_bgcolor='#FFFFFF',plot_bgcolor='#FFFFFF',font=dict(family=FONT_FAMILY,color='#111827'),
        scene=dict(bgcolor='#F8FAFC',
                   xaxis=dict(title='X (m)',range=[-0.5,ROOM_X+0.5],gridcolor='#9CA3AF',zerolinecolor='#4B5563',tickfont=dict(color='#111827')),
                   yaxis=dict(title='Y (m)',range=[-0.5,ROOM_Y+0.5],gridcolor='#9CA3AF',zerolinecolor='#4B5563',tickfont=dict(color='#111827')),
                   zaxis=dict(title='Height (m)',range=[0,WALL_HEIGHT+0.5],gridcolor='#9CA3AF',zerolinecolor='#4B5563',tickfont=dict(color='#111827')),
                   aspectmode='manual',aspectratio=dict(x=7.2,y=8.4,z=3.5),
                   camera=dict(eye=dict(x=1.35,y=1.35,z=0.9))),
        width=1350,height=850,margin=dict(l=0,r=0,t=70,b=0))

    return fig