import os
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from scipy.interpolate import griddata

# ============================================================
# SAFE INTERPOLATION HELPER (PREVENTS CRASHES ON SPARSE DATA)
# ============================================================
def safe_interpolate(x, y, z, GX, GY):
    """Safely interpolate heatmap data even if there are <4 points."""
    pts = np.column_stack((x, y))
    if len(pts) == 0:
        return np.zeros_like(GX)
    if len(pts) == 1:
        return np.full_like(GX, z[0])
    
    GZ = None
    # Try cubic first (needs >= 4 points)
    if len(pts) >= 4:
        try:
            GZ = griddata(pts, z, (GX, GY), method='cubic')
        except:
            pass
            
    # Fallback to linear (needs >= 3 points)
    if GZ is None and len(pts) >= 3:
        try:
            GZ = griddata(pts, z, (GX, GY), method='linear')
        except:
            pass
            
    # Always compute nearest for boundary filling
    try:
        nearest = griddata(pts, z, (GX, GY), method='nearest')
    except:
        nearest = np.full_like(GX, np.mean(z))
        
    # Merge
    if GZ is not None:
        return np.where(np.isnan(GZ), nearest, GZ)
    return nearest

# ============================================================
# FORCE ALL PLOTLY 3D CHARTS TO LIGHT / WHITE
# ============================================================
APP_BUILD = "ALL-3D-WHITE-v5.6"

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
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Portable Wireless Site Survey and Network Analysis System",
    page_icon="📡",
    layout="wide"
)

st.markdown("""
<style>
div[data-testid="stPlotlyChart"], div[data-testid="stPlotlyChart"] > div {
    background: #FFFFFF !important;
}
.block-container { padding-top: 3.5rem !important; padding-bottom: 3rem; max-width: 1500px; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,0.18); }
[data-testid="stMetric"] {
    padding: 14px 16px; border-radius: 16px;
    border: 1px solid rgba(128,128,128,0.18); background: rgba(128,128,128,0.035);
}
.dashboard-title {
    font-size: 2.4rem; font-weight: 800; line-height: 1.3;
    margin-top: 0.5rem; margin-bottom: 6px;
    background: linear-gradient(90deg, #60a5fa, #22c55e);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.dashboard-subtitle { font-size: 1rem; font-weight: 400; opacity: 0.80; margin-bottom: 1.3rem; }
.room-badge {
    display: inline-block; padding: 6px 12px; border-radius: 999px;
    background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.32);
    font-weight: 700; margin: 3px 0 12px 0;
}
.recommend-card {
    padding: 22px 24px; border-radius: 18px; border: 1px solid rgba(34,197,94,0.35);
    background: linear-gradient(135deg, rgba(34,197,94,0.13), rgba(59,130,246,0.08));
    margin: 10px 0 18px 0;
}
.recommend-label { font-size: 0.82rem; opacity: 0.72; text-transform: uppercase; letter-spacing: 0.08em; }
.recommend-wifi { font-size: 1.85rem; font-weight: 800; margin-top: 4px; }
.recommend-rssi { font-size: 1rem; margin-top: 5px; }
button[data-baseweb="tab"] { font-weight: 650; }
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

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None: return None
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file, skipinitialspace=True)
        elif uploaded_file.name.lower().endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else: return None

        df.columns = df.columns.astype(str).str.strip()
        header_aliases = {
            "point id": "Point", "point": "Point", "x (m)": "X", "x": "X",
            "y (m)": "Y", "y": "Y", "rssi (dbm)": "RSSI", "rssi_dbm": "RSSI", "rssi": "RSSI",
            "frequency (mhz)": "Frequency", "frequency": "Frequency",
            "channel": "Channel", "ssid": "SSID", "bssid": "BSSID", "band": "Band"
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

        for col in ["X", "Y", "RSSI", "Channel"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df.dropna(subset=["X", "Y", "RSSI"]).copy()
    except Exception as e:
        st.error(f"❌ ไม่สามารถอ่านไฟล์ได้: {e}")
        return pd.DataFrame()


ROOM_B_EMBEDDED_CSV = 'Point,X,Y,SSID,BSSID,RSSI,Channel,Frequency,Band,Security\nP01,0,0,KMITL-WIFI,00:2E:C7:90:94:61,-73,11,2462,2.4GHz,OPEN\nP02,1.7,0,KMITL-WIFI,00:2E:C7:90:94:61,-71,11,2462,2.4GHz,OPEN\nP03,3.4,0,KMITL-WIFI,00:2E:C7:90:94:61,-61,11,2462,2.4GHz,OPEN\nP04,5.1,0,KMITL-WIFI,00:2E:C7:90:94:61,-58,11,2462,2.4GHz,OPEN\nP05,6.8,0,KMITL-WIFI,00:2E:C7:90:94:61,-68,11,2462,2.4GHz,OPEN\nP06,0,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-73,11,2462,2.4GHz,OPEN\nP07,1.7,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-64,11,2462,2.4GHz,OPEN\nP08,3.4,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP09,5.1,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP10,6.8,1.8,KMITL-WIFI,00:2E:C7:90:94:61,-61,11,2462,2.4GHz,OPEN\nP11,0,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-67,11,2462,2.4GHz,OPEN\nP12,1.7,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-65,11,2462,2.4GHz,OPEN\nP13,3.4,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-64,11,2462,2.4GHz,OPEN\nP14,5.1,3.6,KMITL-Legacy,00:2E:C7:90:94:60,-64,11,2462,2.4GHz,WPA2-ENT\nP15,6.8,3.6,KMITL-WIFI,00:2E:C7:90:94:61,-66,11,2462,2.4GHz,OPEN\nP16,0,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-61,11,2462,2.4GHz,OPEN\nP17,1.7,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-56,11,2462,2.4GHz,OPEN\nP18,3.4,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP19,5.1,5.4,KMITL-WIFI,00:2E:C7:90:94:61,-59,11,2462,2.4GHz,OPEN\nP20,6.8,5.4,KMITL-Legacy,00:2E:C7:90:94:60,-68,11,2462,2.4GHz,WPA2-ENT\nP21,0,7.2,KMITL-WIFI,00:2E:C7:90:94:61,-59,11,2462,2.4GHz,OPEN\nP22,1.7,7.2,KMITL-Legacy,00:2E:C7:90:94:60,-60,11,2462,2.4GHz,WPA2-ENT\nP23,3.4,7.2,KMITL-WIFI,00:2E:C7:90:94:61,-57,11,2462,2.4GHz,OPEN\nP24,5.1,7.2,KMITL-WIFI,00:2E:C7:90:94:61,-63,11,2462,2.4GHz,OPEN\nP25,6.8,7.2,KMITL-Legacy,00:2E:C7:90:94:60,-61,11,2462,2.4GHz,WPA2-ENT\nP26,0,9,KMITL-WIFI,00:2E:C7:90:94:61,-68,11,2462,2.4GHz,OPEN\nP27,1.7,9,KMITL-WIFI,00:2E:C7:90:94:61,-67,11,2462,2.4GHz,OPEN\nP28,3.4,9,KMITL-WIFI,00:2E:C7:90:94:61,-71,11,2462,2.4GHz,OPEN\nP29,5.1,9,KMITL-WIFI,00:2E:C7:90:94:61,-74,11,2462,2.4GHz,OPEN\nP30,6.8,9,KMITL-WIFI,00:2E:C7:90:94:61,-75,11,2462,2.4GHz,OPEN'
def load_room_b_embedded():
    import io
    return pd.read_csv(io.StringIO(ROOM_B_EMBEDDED_CSV))

def find_default_file(filename):
    return filename if os.path.exists(filename) else None

def get_room_size(df, room_name):
    config = ROOMS[room_name]
    if config["x"] is not None and config["y"] is not None:
        return config["x"], config["y"]
    if df is not None and not df.empty:
        return float(df["X"].max()), float(df["Y"].max())
    return 5.0, 5.0


def create_room_b_heatmap(wifi, opacity=0.80, show_ap=True, show_points=True, show_furniture=True):
    RX, RY, WH = 6.80, 9.00, 3.0
    AP_X_B, AP_Y_B, AP_H_B = 3.4, 4.5, 4.0
    fig = go.Figure()

    d = wifi.dropna(subset=["X", "Y", "RSSI"]).copy()
    if not d.empty:
        gx = np.linspace(0, RX, 180)
        gy = np.linspace(0, RY, 240)
        GX, GY = np.meshgrid(gx, gy)
        
        # Use safe interpolation
        GZ = safe_interpolate(d["X"], d["Y"], d["RSSI"], GX, GY)
        GZ = np.clip(GZ, float(d["RSSI"].min()), float(d["RSSI"].max()))

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=np.zeros_like(GZ)+0.01, surfacecolor=GZ,
            colorscale="Jet", cmin=float(d["RSSI"].min()), cmax=float(d["RSSI"].max()), opacity=opacity, showscale=True,
            colorbar=dict(title="RSSI (dBm)", len=0.65), customdata=GZ,
            hovertemplate="<b>Wi-Fi Signal</b><br>X: %{x:.2f} m<br>Y: %{y:.2f} m<br>RSSI: %{customdata:.1f} dBm<extra></extra>",
            name="RSSI Heatmap"
        ))

    if show_points and not d.empty:
        fig.add_trace(go.Scatter3d(
            x=d["X"], y=d["Y"], z=np.ones(len(d))*0.15, mode="markers+text", text=d["Point"] if "Point" in d else None,
            textposition="top center", textfont=dict(family="Arial", size=14, color="#4B5563"),
            marker=dict(size=5, color="#1F2937", symbol="circle", line=dict(color="white", width=1)),
            customdata=np.column_stack((
                d["Point"].astype(str) if "Point" in d else [""]*len(d),
                d["SSID"].astype(str) if "SSID" in d else [""]*len(d),
                d["RSSI"]
            )),
            hovertemplate="<b>%{customdata[0]}</b><br>X: %{x:.2f} m<br>Y: %{y:.2f} m<br>SSID: %{customdata[1]}<br>RSSI: %{customdata[2]} dBm<extra></extra>",
            name="Survey Points"
        ))

    if show_ap:
        fig.add_trace(go.Scatter3d(x=[AP_X_B], y=[AP_Y_B], z=[AP_H_B], mode="markers+text", marker=dict(size=14, color="#FF2020", symbol="diamond", line=dict(color="white", width=2)), text=["AP"], textposition="top center", name="Access Point"))
        fig.add_trace(go.Scatter3d(x=[AP_X_B, AP_X_B], y=[AP_Y_B, AP_Y_B], z=[0, AP_H_B], mode="lines", line=dict(color="#FF3030", width=4, dash="dash"), hoverinfo="skip", showlegend=False))

    def wall(x1,y1,x2,y2,height,z_bottom=0):
        fig.add_trace(go.Mesh3d(
            x=[x1,x2,x2,x1,x1,x2,x2,x1], y=[y1,y2,y2,y1,y1,y2,y2,y1], z=[z_bottom]*4+[height]*4,
            i=[0,0,0,4,4,4], j=[1,2,3,5,6,7], k=[2,3,4,6,7,5], color="#8A8A8A", opacity=0.72, hoverinfo="skip", showlegend=False
        ))
    wall(0,0,RX,0,WH); wall(0,0,0,RY,WH); wall(RX,0,RX,RY,WH)
    door_mid, door_w, door_h = 1.70, 1.98, 2.05
    dx1, dx2 = door_mid-door_w/2, door_mid+door_w/2
    wall(0,RY,dx1,RY,WH); wall(dx2,RY,RX,RY,WH); wall(dx1,RY,dx2,RY,WH,door_h)

    def box(xmin,xmax,ymin,ymax,zmin,zmax,color,op,name):
        fig.add_trace(go.Mesh3d(x=[xmin,xmax,xmax,xmin,xmin,xmax,xmax,xmin], y=[ymin,ymin,ymax,ymax,ymin,ymin,ymax,ymax], z=[zmin,zmin,zmin,zmin,zmax,zmax,zmax,zmax],
            i=[7,0,0,0,4,4,2,6,4,0,3,7], j=[3,4,1,2,5,6,3,7,5,1,2,6], k=[0,7,2,3,6,7,7,4,1,5,6,5], color=color,opacity=op,name=name, hoverinfo="name",showlegend=False))
    def table(xmin,xmax,ymin,ymax,name):
        h, top, leg = 0.80, 0.05, 0.06
        box(xmin,xmax,ymin,ymax,h-top,h,"#D7CCC8",1,name+" Top"); box(xmin,xmin+leg,ymin,ymin+leg,0,h-top,"#5C4033",1,name+" Leg"); box(xmax-leg,xmax,ymin,ymin+leg,0,h-top,"#5C4033",1,name+" Leg"); box(xmax-leg,xmax,ymax-leg,ymax,0,h-top,"#5C4033",1,name+" Leg"); box(xmin,xmin+leg,ymax-leg,ymax,0,h-top,"#5C4033",1,name+" Leg")

    if show_furniture:
        def flip_y(ymin,ymax): a,b=RY-ymin,RY-ymax; return min(a,b),max(a,b)
        y1,y2=flip_y(7.50,8.44); box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 1")
        y1,y2=flip_y(0.50,1.44); box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 10")
        for item,(ymin,ymax) in zip([11,12,13,14,15,16], [(7.00,7.78),(6.20,6.98),(4.40,5.18),(3.60,4.38),(1.80,2.58),(1.00,1.78)]):
            y1,y2=flip_y(ymin,ymax); table(RX-1.84,RX,y1,y2,f"Table {item}")
        for item,x1,x2,ymin,ymax in [(2,0,1.84,5.40,6.18),(4,1.84,3.68,5.40,6.18),(3,0,1.84,4.60,5.38),(5,1.84,3.68,4.60,5.38),(6,0,1.84,2.60,3.38),(8,1.84,3.68,2.60,3.38),(7,0,1.84,1.80,2.58),(9,1.84,3.68,1.80,2.58)]:
            y1,y2=flip_y(ymin,ymax); table(x1,x2,y1,y2,f"Table {item}")
        ox1,ox2, oy1,oy2 = RX-2.10, RX-2.88, *flip_y(0.0,0.78)
        box(min(ox1,ox2),max(ox1,ox2),oy1,oy2,0,0.80,"#78909C",0.88,"Object 17")

    fig.update_layout(
        title=dict(text="3D Wi-Fi RSSI Heatmap | KMITL Co-Working Space (Room B)",x=0.5), paper_bgcolor="#FFFFFF",plot_bgcolor="#FFFFFF",font=dict(color="#111827"),
        scene=dict(xaxis=dict(title="X (m)",range=[-0.5,RX+0.7]), yaxis=dict(title="Y (m)",range=[-0.7,RY+0.5]), zaxis=dict(title="Height (m)",range=[0,4.5]), aspectmode="manual",aspectratio=dict(x=6.8,y=9.0,z=3.5), camera=dict(eye=dict(x=1.35,y=1.35,z=0.9))),
        height=850,margin=dict(l=0,r=0,t=60,b=0)
    )
    return fig


def create_room_c_heatmap(wifi, opacity=0.80, show_points=True, show_furniture=True):
    ROOM_X, ROOM_Y, WALL_HEIGHT, WALL_THICKNESS = 2.70, 9.00, 3.0, 0.12
    DOOR_EACH_W, DOOR_TOTAL_W, DOOR_H = 0.99, 1.98, 2.05
    DOOR_X_START, DOOR_X_END = (ROOM_X - DOOR_TOTAL_W) / 2, (ROOM_X - DOOR_TOTAL_W) / 2 + DOOR_TOTAL_W

    fig = go.Figure()
    fig.add_trace(go.Mesh3d(x=[0, ROOM_X, ROOM_X, 0], y=[0, 0, ROOM_Y, ROOM_Y], z=[0, 0, 0, 0], i=[0, 0], j=[1, 2], k=[2, 3], color="#E5E7EB", opacity=0.8, hoverinfo="skip"))
    
    def wall(x1, y1, x2, y2, height=WALL_HEIGHT, z0=0):
        dx, dy = x2 - x1, y2 - y1
        l = np.sqrt(dx**2 + dy**2)
        if l == 0: return
        nx, ny = -dy / l * WALL_THICKNESS / 2, dx / l * WALL_THICKNESS / 2
        pts = [(x1+nx, y1+ny), (x2+nx, y2+ny), (x2-nx, y2-ny), (x1-nx, y1-ny)]
        x, y, z = [p[0] for p in pts]*2, [p[1] for p in pts]*2, [z0]*4+[z0+height]*4
        fig.add_trace(go.Mesh3d(x=x, y=y, z=z, i=[0,0,4,4,0,0,2,2,0,0,1,1], j=[1,2,5,6,1,5,3,7,3,7,2,6], k=[2,3,6,7,5,4,7,6,7,4,6,5], color="#93C5FD", opacity=0.06, hoverinfo="skip"))
    wall(0, 0, 0, ROOM_Y); wall(ROOM_X, 0, ROOM_X, ROOM_Y); wall(0, 0, ROOM_X, 0)
    wall(0, ROOM_Y, DOOR_X_START, ROOM_Y); wall(DOOR_X_END, ROOM_Y, ROOM_X, ROOM_Y); wall(DOOR_X_START, ROOM_Y, DOOR_X_END, ROOM_Y, height=WALL_HEIGHT-DOOR_H, z0=DOOR_H)

    real_data = {"X": [0.00, 1.35, 2.70]*3, "Y": [0.00]*3 + [4.50]*3 + [9.00]*3, "RSSI": [-82, -90, -84, -77, -67, -58, -77, -84, -75]}
    if wifi is not None and not wifi.empty and {"X", "Y", "RSSI"}.issubset(wifi.columns):
        real_data = {k: wifi.dropna(subset=["X","Y","RSSI"])[k].to_numpy() for k in ("X","Y","RSSI")}

    if real_data and len(real_data['X']) > 0:
        xv, yv, rv = np.asarray(real_data["X"], dtype=float), np.asarray(real_data["Y"], dtype=float), np.asarray(real_data["RSSI"], dtype=float)
        GX, GY = np.meshgrid(np.linspace(0, ROOM_X, 80), np.linspace(0, ROOM_Y, 120))
        
        GZ = safe_interpolate(xv, yv, rv, GX, GY)
        
        fig.add_trace(go.Surface(x=GX, y=GY, z=np.full_like(GZ, 0.1), surfacecolor=GZ, colorscale="Jet", cmin=float(np.min(rv)), cmax=float(np.max(rv)), opacity=opacity, showscale=True))
        if show_points:
            fig.add_trace(go.Scatter3d(x=xv, y=yv, z=np.full(len(xv), 0.15), mode="markers", marker=dict(size=6, color="#1F2937", line=dict(width=1, color="white"))))

    fig.update_layout(title=dict(text="3D Wi-Fi RSSI Heatmap", x=0.5), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", scene=dict(xaxis=dict(range=[-0.5, ROOM_X + 0.5]), yaxis=dict(range=[-0.5, ROOM_Y + 0.5]), zaxis=dict(range=[0, 3.5]), aspectmode="manual", aspectratio=dict(x=2.7, y=9.0, z=3.0), camera=dict(eye=dict(x=1.5, y=1.5, z=1.0))), height=850, margin=dict(l=0, r=0, t=70, b=0))
    return fig


def create_3d_heatmap(wifi, room_name, room_x, room_y, opacity, show_ap, show_points, show_furniture):
    fig = go.Figure()
    if wifi is not None and not wifi.empty:
        heatmap_data = wifi.groupby(["X", "Y"])["RSSI"].max().reset_index()
        GX, GY = np.meshgrid(np.linspace(0, room_x, 180), np.linspace(0, room_y, 240))
        GZ = safe_interpolate(heatmap_data["X"].values, heatmap_data["Y"].values, heatmap_data["RSSI"].values, GX, GY)
        GZ = np.clip(GZ, -90, -50)
        custom_scale = [[0.000, "#ef4444"], [0.375, "#f97316"], [0.625, "#eab308"], [1.000, "#22c55e"]]
        fig.add_trace(go.Surface(x=GX, y=GY, z=np.zeros_like(GZ) + 0.01, surfacecolor=GZ, colorscale=custom_scale, cmin=-90, cmax=-50, opacity=opacity, showscale=True, name="RSSI Heatmap"))

        if show_points:
            fig.add_trace(go.Scatter3d(x=wifi["X"], y=wifi["Y"], z=np.ones(len(wifi))*0.15, mode="markers+text", text=wifi["Point"], textposition="top center", marker=dict(size=6, color="white", line=dict(color="black", width=1.5))))
            
    fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF", scene=dict(xaxis=dict(range=[-0.5, room_x + 0.7]), yaxis=dict(range=[-0.7, room_y + 0.5]), zaxis=dict(range=[0, 4.5]), aspectmode="manual", aspectratio=dict(x=max(room_x, 1), y=max(room_y, 1), z=3.5), camera=dict(eye=dict(x=1.35, y=1.35, z=0.9))), height=700, margin=dict(l=0, r=0, t=10, b=0))
    return fig


# ============================================================
# ROOM A — COMBINED 3D HEATMAP
# ============================================================
ROOM_A_LAYOUT = {
    "A1": {"room_key": "Room 1", "x_min": 0.0,   "x_max": 3.535, "y_min": 4.20, "y_max": 8.33},
    "A2": {"room_key": "Room 2", "x_min": 3.535, "x_max": 7.105, "y_min": 2.83, "y_max": 8.30},
    "A3": {"room_key": "Room 3", "x_min": 0.0,   "x_max": 3.535, "y_min": 0.0,  "y_max": 4.20},
    "A4": {"room_key": "Room 4", "x_min": 3.535, "x_max": 7.105, "y_min": 0.0,  "y_max": 2.83},
}

ROOM_A_FALLBACK = {
    'Room 1': pd.DataFrame({'Point': ['P01', 'P02', 'P03'], 'X': [0.0, 1.77, 3.54], 'Y': [0.0, 2.07, 4.13], 'RSSI': [-70, -64, -68]}),
    'Room 2': pd.DataFrame({'Point': ['P10', 'P11', 'P12'], 'X': [0.0, 1.78, 3.57], 'Y': [0.0, 1.82, 3.65], 'RSSI': [-50, -66, -81]}),
    'Room 3': pd.DataFrame({'Point': ['P22', 'P23', 'P24'], 'X': [0.0, 1.77, 3.54], 'Y': [0.0, 2.1, 4.2], 'RSSI': [-74, -62, -71]}),
    'Room 4': pd.DataFrame({'Point': ['P31', 'P32', 'P33'], 'X': [0.0, 1.78, 3.57], 'Y': [0.0, 1.41, 2.83], 'RSSI': [-73, -67, -74]}),
}

def _load_room_a_csv(room_key):
    filename = ROOMS[room_key]["file"]
    if filename and os.path.exists(filename):
        try:
            d = pd.read_csv(filename, skipinitialspace=True)
            d.columns = d.columns.astype(str).str.strip()
            d.rename(columns={"Point ID": "Point", "X (m)": "X", "Y (m)": "Y", "RSSI (dBm)": "RSSI"}, inplace=True)
            for col in ["X", "Y", "RSSI"]: 
                if col in d: d[col] = pd.to_numeric(d[col], errors="coerce")
            return d.dropna(subset=["X", "Y", "RSSI"]).copy()
        except: pass
    return ROOM_A_FALLBACK.get(room_key, pd.DataFrame()).copy()

def load_room_a_combined_data():
    frames = []
    for label, layout in ROOM_A_LAYOUT.items():
        d = _load_room_a_csv(layout["room_key"])
        if d.empty: continue
        d["X"] = pd.to_numeric(d["X"], errors="coerce") + layout["x_min"]
        d["Y"] = pd.to_numeric(d["Y"], errors="coerce") + layout["y_min"]
        d["Point"] = label + "-" + d["Point"].astype(str) if "Point" in d else [f"{label}-P{i}" for i in range(len(d))]
        if "SSID" not in d: d["SSID"] = "KMITL-WIFI"
        frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def create_room_a_combined_heatmap(wifi=None, opacity=0.85, show_ap=True, show_points=True, show_furniture=True):
    ROOM_X, ROOM_Y = 7.20, 8.40
    WALL_HEIGHT, WALL_THICKNESS = 3.0, 0.12
    ROOM_CONFIGS = {
        '1': {'label': 'A1', 'x_min': 0., 'x_max': 3.535, 'y_min': 4.20, 'y_max': 8.33, 'color': '#E5E7EB'},
        '2': {'label': 'A2', 'x_min': 3.535, 'x_max': 7.105, 'y_min': 2.83, 'y_max': 8.30, 'color': '#E5E7EB'},
        '3': {'label': 'A3', 'x_min': 0., 'x_max': 3.535, 'y_min': 0., 'y_max': 4.20, 'color': '#E5E7EB'},
        '4': {'label': 'A4', 'x_min': 3.535, 'x_max': 7.105, 'y_min': 0., 'y_max': 2.83, 'color': '#E5E7EB'},
    }

    ROOM_DATA = {'1': {'X':[],'Y':[],'RSSI':[]}, '2': {'X':[],'Y':[],'RSSI':[]}, '3': {'X':[],'Y':[],'RSSI':[]}, '4': {'X':[],'Y':[],'RSSI':[]}}
    
    if wifi is not None and not wifi.empty and {"X", "Y", "RSSI"}.issubset(wifi.columns):
        for _, row in wifi.dropna(subset=["X", "Y", "RSSI"]).iterrows():
            x, y, rssi = float(row['X']), float(row['Y']), float(row['RSSI'])
            if x <= 3.535 and y >= 4.20: r = '1'
            elif x > 3.535 and y >= 2.83: r = '2'
            elif x <= 3.535 and y < 4.20: r = '3'
            else: r = '4'
            ROOM_DATA[r]['X'].append(x); ROOM_DATA[r]['Y'].append(y); ROOM_DATA[r]['RSSI'].append(rssi)

    fig = go.Figure()

    for room_name, room in ROOM_CONFIGS.items():
        x1,x2,y1,y2 = room['x_min'],room['x_max'],room['y_min'],room['y_max']
        fig.add_trace(go.Mesh3d(x=[x1,x2,x2,x1],y=[y1,y1,y2,y2],z=[0]*4, i=[0,0],j=[1,2],k=[2,3],color=room['color'],opacity=0.7, hoverinfo='skip'))
        fig.add_trace(go.Scatter3d(x=[(x1+x2)/2],y=[(y1+y2)/2],z=[1.12],mode='text', text=[f"ROOM {room['label']}"], textfont=dict(size=16,color='#4B5563'), hoverinfo='skip'))

    def add_wall(x1,y1,x2,y2,height=WALL_HEIGHT,z0=0):
        dx,dy = x2-x1, y2-y1
        if np.hypot(dx,dy) == 0: return
        nx, ny = -dy/np.hypot(dx,dy)*WALL_THICKNESS/2, dx/np.hypot(dx,dy)*WALL_THICKNESS/2
        pts = [(x1+nx,y1+ny),(x2+nx,y2+ny),(x2-nx,y2-ny),(x1-nx,y1-ny)]
        x, y, z = [p[0] for p in pts]*2, [p[1] for p in pts]*2, [z0]*4+[z0+height]*4
        fig.add_trace(go.Mesh3d(x=x,y=y,z=z, i=[0,0,4,4,0,0,2,2,0,0,1,1], j=[1,2,5,6,1,5,3,7,3,7,2,6], k=[2,3,6,7,5,4,7,6,7,4,6,5], color='#93C5FD',opacity=0.06,hoverinfo='skip'))

    add_wall(0,0,1.03,0); add_wall(2.97,0,ROOM_X,0); add_wall(1.03,0,2.97,0,height=WALL_HEIGHT-2.06,z0=2.06)
    add_wall(0,0,0,ROOM_Y); add_wall(ROOM_X,0,ROOM_X,ROOM_Y); add_wall(0,ROOM_Y,ROOM_X,ROOM_Y)
    add_wall(0,4.20,2.45,4.20); add_wall(2.45+0.97,4.20,3.535,4.20); add_wall(2.45,4.20,2.45+0.97,4.20,height=WALL_HEIGHT-2.06,z0=2.06)
    add_wall(3.535,2.83,7.105,2.83); add_wall(3.535,4.20,3.535,8.33); add_wall(3.535,0,3.535,1.86); add_wall(3.535,1.86,3.535,2.83,height=WALL_HEIGHT-2.06,z0=2.06)
    add_wall(3.535,2.83,3.535,3.03); add_wall(3.535,3.03+0.97,3.535,4.20); add_wall(3.535,3.03,3.535,3.03+0.97,height=WALL_HEIGHT-2.06,z0=2.06)

    def add_room_heatmap(room_name, room_data):
        if not room_data or len(room_data.get('X', [])) == 0: return
        room = ROOM_CONFIGS[room_name]
        xv, yv, rv = np.asarray(room_data['X']), np.asarray(room_data['Y']), np.asarray(room_data['RSSI'])
        GX, GY = np.meshgrid(np.linspace(room['x_min'], room['x_max'], 80), np.linspace(room['y_min'], room['y_max'], 80))
        
        GZ = safe_interpolate(xv, yv, rv, GX, GY)
        fig.add_trace(go.Surface(x=GX,y=GY,z=np.full_like(GZ,0.20),surfacecolor=GZ, colorscale='Jet', opacity=opacity, showscale=(room_name=='1'), name=f"Heatmap {room['label']}"))
        if show_points:
            fig.add_trace(go.Scatter3d(x=xv,y=yv,z=np.full(len(xv),0.25),mode='markers',marker=dict(size=4,color='#1F2937',line=dict(width=1,color='white'))))

    add_room_heatmap('1', ROOM_DATA.get('1', {}))
    add_room_heatmap('2', ROOM_DATA.get('2', {}))
    add_room_heatmap('3', ROOM_DATA.get('3', {}))
    add_room_heatmap('4', ROOM_DATA.get('4', {}))

    fig.update_layout(title=dict(text='3D Wi-Fi RSSI Heatmap',x=0.5), paper_bgcolor='#FFFFFF',plot_bgcolor='#FFFFFF', scene=dict(xaxis=dict(range=[-0.5,ROOM_X+0.5]), yaxis=dict(range=[-0.5,ROOM_Y+0.5]), zaxis=dict(range=[0,3.5]), aspectmode='manual',aspectratio=dict(x=7.2,y=8.4,z=3.5)), height=850,margin=dict(l=0,r=0,t=70,b=0))
    return fig

# ============================================================
# SMART WI-FI ADVISOR & OTHER LOGIC
# ============================================================
def analyze_wifi_recommendation(df):
    if df is None or df.empty or "SSID" not in df.columns: return pd.DataFrame()
    results = []
    for ssid, group in df.groupby("SSID"):
        rssi = pd.to_numeric(group["RSSI"], errors="coerce").dropna()
        if rssi.empty: continue
        avg_rssi, min_rssi, max_rssi, std_rssi = float(rssi.mean()), float(rssi.min()), float(rssi.max()), float(rssi.std()) if len(rssi) > 1 else 0.0
        if np.isnan(std_rssi): std_rssi = 0.0
        good_percent, weak_percent = float((rssi >= -65).sum() / len(rssi) * 100), float((rssi <= -75).sum() / len(rssi) * 100)
        score = float(np.clip(((avg_rssi + 90) / 40) * 100, 0, 100)) * 0.50 + good_percent * 0.25 + float(np.clip(100 - std_rssi * 8, 0, 100)) * 0.15 + (100 - weak_percent) * 0.10
        quality = "Excellent" if avg_rssi >= -60 else "Good" if avg_rssi >= -67 else "Fair" if avg_rssi >= -75 else "Weak"
        results.append({"SSID": str(ssid), "Average RSSI": avg_rssi, "Weakest RSSI": min_rssi, "Strongest RSSI": max_rssi, "Stability": std_rssi, "Good Signal (%)": good_percent, "Weak Signal (%)": weak_percent, "Measurements": len(rssi), "Score": score, "Quality": quality})
    return pd.DataFrame(results).sort_values(["Score", "Average RSSI"], ascending=[False, False]).reset_index(drop=True) if results else pd.DataFrame()

def recommend_wifi_at_point(df, point):
    if df is None or df.empty: return None, pd.DataFrame()
    p_data = df[df["Point"].astype(str) == str(point)]
    if p_data.empty: return None, pd.DataFrame()
    summ = p_data.groupby("SSID").agg(RSSI=("RSSI", "max"), AP_Count=("BSSID", "nunique")).reset_index().sort_values("RSSI", ascending=False).reset_index(drop=True)
    return summ.iloc[0], summ

def signal_quality(rssi, language="ไทย"):
    if rssi >= -60: return ("🟢 Excellent", "สัญญาณแรงมาก เหมาะสำหรับ Video Call, Streaming และงานที่ต้องการความเสถียร") if language == "ไทย" else ("🟢 Excellent", "Very strong signal for video calls, streaming and demanding use.")
    if rssi >= -67: return ("🟢 Good", "สัญญาณดี เหมาะสำหรับการใช้งานทั่วไปและ Video Call") if language == "ไทย" else ("🟢 Good", "Good signal for general use and video calls.")
    if rssi >= -75: return ("🟡 Fair", "สามารถใช้งานได้ แต่อาจมีความไม่เสถียรในบางช่วง") if language == "ไทย" else ("🟡 Fair", "Usable signal, but performance may be less stable.")
    return ("🔴 Weak", "สัญญาณค่อนข้างอ่อน แนะนำให้ลอง Wi-Fi อื่นหรือขยับเข้าใกล้ Access Point") if language == "ไทย" else ("🔴 Weak", "Weak signal. Try another Wi-Fi or move closer to an access point.")

TEXT = {
    "ไทย": {"settings": "📂 นำเข้าและตั้งค่า", "language": "🌐 ภาษา / Language", "area_select": "เลือกพื้นที่", "area": "พื้นที่", "subroom": "เลือกห้องย่อย", "default_file": "ไฟล์เริ่มต้น", "upload": "อัปโหลดข้อมูล Survey", "ssid": "📶 เลือก SSID", "opacity": "ความโปร่งใส Heatmap", "layers": "เลเยอร์แผนที่ 3D", "show_ap": "แสดงตำแหน่ง AP", "show_points": "แสดงจุด Survey", "show_furniture": "แสดงผนังและเฟอร์นิเจอร์", "survey_area": "พื้นที่สำรวจ", "location": "ตำแหน่ง", "current_room": "ห้องปัจจุบัน", "room_size": "ขนาดห้อง", "frequency": "ความถี่", "survey_points": "จุดสำรวจ", "access_points": "Access Points", "avg_rssi": "RSSI เฉลี่ย", "strong": "สัญญาณดี", "weak": "สัญญาณอ่อน", "map": "🗺️ แผนที่ 3D", "analysis": "📊 วิเคราะห์", "raw": "📋 ข้อมูลดิบ", "signal_summary": "📶 สรุปคุณภาพสัญญาณ", "excellent": "ดี", "fair": "ปานกลาง", "poor": "อ่อน"},
    "English": {"settings": "📂 Import & Settings", "language": "🌐 Language / ภาษา", "area_select": "Select Area", "area": "Area", "subroom": "Select Subroom", "default_file": "Default file", "upload": "Upload Survey Data", "ssid": "📶 Select SSID", "opacity": "Heatmap Opacity", "layers": "3D Map Layers", "show_ap": "Show AP Position", "show_points": "Show Survey Points", "show_furniture": "Show Walls & Furniture", "survey_area": "Survey Area", "location": "Location", "current_room": "Current Room", "room_size": "Room Size", "frequency": "Frequency", "survey_points": "Survey Points", "access_points": "Access Points", "avg_rssi": "Average RSSI", "strong": "Strong Signal", "weak": "Weak Signal", "map": "🗺️ 3D Map", "analysis": "📊 Analysis", "raw": "📋 Raw Data", "signal_summary": "📶 Signal Quality Summary", "excellent": "Good", "fair": "Fair", "poor": "Weak"}
}
ROOM_A_DISPLAY = {"A1": "Room 1", "A2": "Room 2", "A3": "Room 3", "A4": "Room 4"}
ROOM_DISPLAY = {"Room 1": "A1", "Room 2": "A2", "Room 3": "A3", "Room 4": "A4", "Room B": "B", "Room C": "C"}

with st.sidebar:
    language = st.selectbox("🌐 ภาษา / Language", ["ไทย", "English"], index=0, key="language_selector")
    t = TEXT[language]
    st.header(t["settings"]); st.subheader(t["area_select"])
    selected_area = st.radio(t["area"], ["Room A", "Room B", "Room C"], index=0)

    if selected_area == "Room A":
        room_a_options = (["ภาพรวม Room A", "A1", "A2", "A3", "A4"] if language == "ไทย" else ["Room A Overview", "A1", "A2", "A3", "A4"])
        st.markdown("#### 🚪 ห้องย่อย Room A" if language == "ไทย" else "#### 🚪 Room A Subrooms")
        selected_subroom = st.selectbox("เลือกมุมมอง / ห้องย่อย" if language == "ไทย" else "Select overview / subroom", room_a_options, key="room_a_view")
        selected_room = "Room A" if selected_subroom in ["ภาพรวม Room A", "Room A Overview"] else ROOM_A_DISPLAY[selected_subroom]
    else: selected_room = selected_area

    display_room = ROOM_DISPLAY.get(selected_room, selected_room)
    st.divider()
    default_filename = ROOMS[selected_room]["file"]

    if selected_area == "Room A":
        st.caption("อัปโหลดไฟล์รวม Room A (A1-A4) เพื่อดูภาพรวม" if selected_room == "Room A" and language == "ไทย" else f"อัปโหลดไฟล์สำหรับห้องย่อย {selected_room} เพื่อดูเฉพาะจุด" if language == "ไทย" else "Upload combined Room A (A1-A4) data for overview" if selected_room == "Room A" else f"Upload data for subroom {selected_room} for specific view")
    else: st.caption(f"{t['default_file']}: `{default_filename}`")
    uploaded_file = st.file_uploader(t["upload"], type=["csv", "xlsx"], key=f"upload_{selected_room}")

df = None
if uploaded_file is not None:
    uploaded_df = load_data(uploaded_file)
    if selected_room == "Room B": df = pd.concat([load_room_b_embedded(), uploaded_df], ignore_index=True).drop_duplicates(subset=["Point", "SSID", "BSSID"], keep="last")
    else: df = uploaded_df
elif selected_room == "Room A":
    df = load_room_a_combined_data()
    if df.empty: st.error("❌ ไม่สามารถโหลดข้อมูล Room A (A1-A4) ได้"); st.stop()
elif selected_room in ["Room 1", "Room 2", "Room 3", "Room 4"]:
    df = _load_room_a_csv(selected_room)
    if df.empty: st.error(f"❌ ไม่พบข้อมูล {display_room}"); st.stop()
else:
    if selected_room == "Room B": df = load_room_b_embedded()
    elif find_default_file(default_filename):
        try:
            df = pd.read_csv(default_filename, skipinitialspace=True)
            df.columns = df.columns.astype(str).str.strip()
            df.rename(columns={"Point ID": "Point", "X (m)": "X", "Y (m)": "Y", "RSSI (dBm)": "RSSI", "Frequency (MHz)": "Frequency"}, inplace=True)
            for col in ["X", "Y", "RSSI", "Channel"]:
                if col in df: df[col] = pd.to_numeric(df[col], errors="coerce")
            df = df.dropna(subset=["X", "Y", "RSSI"]).copy()
        except Exception as e: st.error(f"ไม่สามารถอ่าน `{default_filename}` ได้: {e}"); st.stop()
    else: st.info(f"👆 ยังไม่พบไฟล์ `{default_filename}`"); st.stop()

if df is None or df.empty: st.error("❌ ไม่พบข้อมูล Survey"); st.stop()

df.columns = df.columns.astype(str).str.strip()
df.rename(columns={col: {"point id":"Point", "point":"Point", "x (m)":"X", "x":"X", "y (m)":"Y", "y":"Y", "rssi (dbm)":"RSSI", "rssi_dbm":"RSSI", "rssi":"RSSI", "ssid":"SSID", "bssid":"BSSID", "channel":"Channel"}.get(col.lower(), col) for col in df.columns}, inplace=True)
if "BSSID" not in df: df["BSSID"] = df["SSID"].astype(str).str.strip()
else: missing = df["BSSID"].isna() | df["BSSID"].astype(str).str.strip().eq(""); df.loc[missing, "BSSID"] = df.loc[missing, "SSID"].astype(str).str.strip()

ROOM_X, ROOM_Y = get_room_size(df, selected_room)

with st.sidebar:
    st.divider(); st.subheader(t["ssid"])
    selected_ssids = st.multiselect("SSID", options=sorted(df["SSID"].dropna().astype(str).unique()), default=sorted(df["SSID"].dropna().astype(str).unique())) if "SSID" in df else []
    opacity = st.slider(t["opacity"], 0.0, 1.0, 0.85, 0.05)
    st.divider(); st.subheader(t["layers"])
    show_ap, show_points, show_furniture = st.checkbox(t["show_ap"], True), st.checkbox(t["show_points"], True), st.checkbox(t["show_furniture"], True)

wifi = df[df["SSID"].astype(str).isin(selected_ssids)].copy() if selected_ssids else df.copy()
wifi_recommendation = analyze_wifi_recommendation(wifi)
best_wifi = wifi_recommendation.iloc[0] if not wifi_recommendation.empty else None

st.markdown(f'<div class="dashboard-title">ระบบสำรวจและวิเคราะห์คุณภาพเครือข่ายไร้สายแบบพกพา</div><div class="dashboard-subtitle">Portable Wireless Site Survey and Network Analysis System</div><div class="room-badge">📍 {display_room}</div>', unsafe_allow_html=True)
st.markdown(f'**{t["survey_area"]}:** Telecommunication Engineering Department  \n**{t["location"]}:** 3rd Floor – Co-working Space  \n**{t["current_room"]}:** {display_room}  \n**{t["room_size"]}:** {ROOM_X:.2f} × {ROOM_Y:.2f} m  \n**{t["frequency"]}:** 2.4 GHz')

if best_wifi is not None:
    st.markdown(f'<div class="recommend-card"><div class="recommend-label">✨ Wi-Fi แนะนำ / Recommended</div><div class="recommend-wifi">📶 {best_wifi["SSID"]}</div><div class="recommend-rssi">RSSI: {float(best_wifi["Average RSSI"]):.1f} dBm • Quality: {best_wifi["Quality"]}</div></div>', unsafe_allow_html=True)

if not wifi.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric(f"📍 {t['survey_points']}", wifi["Point"].nunique())
    c2.metric(f"📡 {t['access_points']}", wifi["BSSID"].nunique())
    c3.metric(f"📈 {t['avg_rssi']}", f"{wifi['RSSI'].mean():.1f} dBm")
    
    st.markdown("────────────────────────────────────────────")
    tab_overview, tab_map, tab_advisor, tab_analysis, tab_raw = st.tabs(["🏠 Overview" if language == "English" else "🏠 ภาพรวม", t["map"], "🤖 Wi-Fi Advisor", t["analysis"], t["raw"]])

    with tab_overview:
        if not wifi_recommendation.empty:
            st.dataframe(wifi_recommendation[["SSID", "Average RSSI", "Good Signal (%)", "Score", "Quality"]].round(1), use_container_width=True, hide_index=True)

    with tab_map:
        with st.spinner("กำลังสร้าง 3D Heatmap..." if language == "ไทย" else "Generating 3D Heatmap..."):
            if selected_room == "Room A": fig = create_room_a_combined_heatmap(wifi, opacity, show_ap, show_points, show_furniture)
            elif selected_room == "Room B": fig = create_room_b_heatmap(wifi, opacity, show_ap, show_points, show_furniture)
            elif selected_room == "Room C": fig = create_room_c_heatmap(wifi, opacity, show_points, show_furniture)
            else: fig = create_3d_heatmap(wifi, selected_room, ROOM_X, ROOM_Y, opacity, show_ap, show_points, show_furniture)
            st.plotly_chart(force_white_3d(fig), use_container_width=True, height=850, theme=None)

    with tab_advisor:
        if points := sorted(wifi["Point"].dropna().astype(str).unique().tolist()):
            sel_pt = st.selectbox("📍 เลือกจุดที่กำลังนั่ง" if language == "ไทย" else "📍 Select survey point", points)
            p_best, p_tbl = recommend_wifi_at_point(wifi, sel_pt)
            if p_best is not None:
                st.success(f'แนะนำ {p_best["SSID"]} ({p_best["RSSI"]:.1f} dBm)')
                st.dataframe(p_tbl, use_container_width=True, hide_index=True)
                
    with tab_analysis:
        if not wifi_recommendation.empty:
            st.plotly_chart(px.bar(wifi_recommendation, x="SSID", y="Average RSSI", color="Score", color_continuous_scale="RdYlGn"), use_container_width=True)

    with tab_raw:
        st.dataframe(wifi, use_container_width=True, hide_index=True)
        st.download_button("⬇️ ดาวน์โหลดข้อมูล CSV", wifi.to_csv(index=False).encode("utf-8-sig"), f"{selected_room}_survey_data.csv", "text/csv")
