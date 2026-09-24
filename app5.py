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
    page_title="ระบบสำรวจและวิเคราะห์คุณภาพเครือข่ายไร้สายแบบพกพา",
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

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        if uploaded_file.name.lower().endswith(".csv"):

            df = pd.read_csv(
                uploaded_file,
                skipinitialspace=True
            )

        # ----------------------------------------------------
        # Excel
        # ----------------------------------------------------

        elif uploaded_file.name.lower().endswith(".xlsx"):

            df = pd.read_excel(
                uploaded_file
            )

        else:

            return None

        # ----------------------------------------------------
        # Clean Column Names
        # ----------------------------------------------------

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
        )

        # ----------------------------------------------------
        # Rename Columns
        # ----------------------------------------------------

        rename_mapping = {

            "Point ID": "Point",
            "Point": "Point",

            "X (m)": "X",
            "X": "X",

            "Y (m)": "Y",
            "Y": "Y",

            "RSSI (dBm)": "RSSI",
            "RSSI_dBm": "RSSI",
            "RSSI": "RSSI",

            "Frequency (MHz)": "Frequency",
            "Frequency": "Frequency",

            "Channel": "Channel",
            "channel": "Channel",

            "SSID": "SSID",
            "BSSID": "BSSID",

            "Band": "Band"
        }

        df.rename(
            columns=rename_mapping,
            inplace=True
        )

        # ----------------------------------------------------
        # Check Required Columns
        # ----------------------------------------------------

        required_columns = [
            "Point",
            "X",
            "Y",
            "SSID",
            "BSSID",
            "RSSI"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:

            st.error(
                "❌ ไม่พบ Column ที่จำเป็น: "
                + ", ".join(missing_columns)
            )

            st.info(
                "Column ที่พบในไฟล์: "
                + ", ".join(df.columns.tolist())
            )

            return pd.DataFrame()

        # ----------------------------------------------------
        # Convert Numeric
        # ----------------------------------------------------

        df["X"] = pd.to_numeric(
            df["X"],
            errors="coerce"
        )

        df["Y"] = pd.to_numeric(
            df["Y"],
            errors="coerce"
        )

        df["RSSI"] = pd.to_numeric(
            df["RSSI"],
            errors="coerce"
        )

        if "Channel" in df.columns:

            df["Channel"] = pd.to_numeric(
                df["Channel"],
                errors="coerce"
            )

        # ----------------------------------------------------
        # Remove Invalid Rows
        # ----------------------------------------------------

        df = df.dropna(
            subset=[
                "X",
                "Y",
                "RSSI"
            ]
        ).copy()

        return df

    except Exception as e:

        st.error(
            f"❌ ไม่สามารถอ่านไฟล์ได้: {e}"
        )

        return pd.DataFrame()


# ============================================================
# FIND DEFAULT CSV
# ============================================================

def find_default_file(filename):

    if os.path.exists(filename):

        return filename

    return None


# ============================================================
# GET ROOM SIZE
# ============================================================

def get_room_size(df, room_name):

    config = ROOMS[room_name]

    room_x = config["x"]
    room_y = config["y"]

    # --------------------------------------------------------
    # ถ้ากำหนดขนาดห้องไว้แล้ว
    # --------------------------------------------------------

    if room_x is not None and room_y is not None:

        return room_x, room_y

    # --------------------------------------------------------
    # ถ้ายังไม่ได้กำหนด
    # ให้ใช้ขนาดจากข้อมูล CSV
    # --------------------------------------------------------

    if df is not None and not df.empty:

        room_x = float(
            df["X"].max()
        )

        room_y = float(
            df["Y"].max()
        )

    else:

        room_x = 5.0
        room_y = 5.0

    return room_x, room_y


# ============================================================
# CREATE 3D HEATMAP
# ============================================================



def create_room_b_heatmap(wifi, opacity=0.85, show_ap=True, show_points=True, show_furniture=True):
    """Room B: 6.80 x 9.00 m based on the supplied Room B model."""
    RX, RY, WH = 6.80, 9.00, 3.0
    AP_X_B, AP_Y_B, AP_H_B = 3.4, 4.5, 4.0
    fig = go.Figure()

    d = wifi.dropna(subset=["X", "Y", "RSSI"]).copy()

    # Smooth RSSI heatmap
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
        GZ = np.clip(GZ, -90, -50)

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=np.zeros_like(GZ)+0.01,
            surfacecolor=GZ,
            colorscale=[
                [0.00, "#ef4444"],
                [0.375, "#f97316"],
                [0.625, "#eab308"],
                [1.00, "#22c55e"]
            ],
            cmin=-90, cmax=-50, opacity=opacity, showscale=True,
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
            marker=dict(size=5, color="white", symbol="circle",
                        line=dict(color="black", width=1.5)),
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
            text=["📡 AP"], textposition="top center",
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

    # Double door on rear wall, centered around X=1.70 m
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
        # Cabinets
        y1,y2=flip_y(7.50,8.44)
        box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 1")
        y1,y2=flip_y(0.50,1.44)
        box(0,0.78,y1,y2,0,1.85,"#2C3E50",0.9,"Cabinet 10")

        # Tables 11-16
        for item,(ymin,ymax) in zip(
            [11,12,13,14,15,16],
            [(7.00,7.78),(6.20,6.98),(4.40,5.18),
             (3.60,4.38),(1.80,2.58),(1.00,1.78)]
        ):
            y1,y2=flip_y(ymin,ymax)
            table(RX-1.84,RX,y1,y2,f"Table {item}")

        # Tables 2-9
        grouped=[
            (2,0,1.84,5.40,6.18),(4,1.84,3.68,5.40,6.18),
            (3,0,1.84,4.60,5.38),(5,1.84,3.68,4.60,5.38),
            (6,0,1.84,2.60,3.38),(8,1.84,3.68,2.60,3.38),
            (7,0,1.84,1.80,2.58),(9,1.84,3.68,1.80,2.58)
        ]
        for item,x1,x2,ymin,ymax in grouped:
            y1,y2=flip_y(ymin,ymax)
            table(x1,x2,y1,y2,f"Table {item}")

        # Object 17 - same flipped coordinates as supplied code
        ox1,ox2 = RX-2.10, RX-2.88
        oy1,oy2 = flip_y(0.0,0.78)
        box(min(ox1,ox2),max(ox1,ox2),oy1,oy2,0,0.80,
            "#78909C",0.88,"Object 17")

    fig.update_layout(
        title=dict(text="3D Wi-Fi RSSI Heatmap | Room B",x=0.5),
        paper_bgcolor="#FFFFFF",plot_bgcolor="#FFFFFF",font=dict(color="#111827"),
        scene=dict(
            bgcolor="#FFFFFF",
            xaxis=dict(title="X (m)",range=[-0.5,RX+0.7],gridcolor="#273746"),
            yaxis=dict(title="Y (m)",range=[-0.7,RY+0.5],gridcolor="#273746"),
            zaxis=dict(title="Height (m)",range=[0,4.5],gridcolor="#273746"),
            aspectmode="manual",aspectratio=dict(x=6.8,y=9.0,z=3.5),
            camera=dict(eye=dict(x=1.35,y=1.35,z=0.9))
        ),
        height=780,margin=dict(l=0,r=0,t=60,b=0),
        legend=dict(bgcolor="rgba(255,255,255,0.94)",bordercolor="#444",borderwidth=1)
    )
    return fig


def create_room_c_heatmap(wifi, opacity=0.80, show_points=True, show_furniture=True):
    """Room C: 2.70 x 9.00 m — updated white 3D layout, top double glass doors and 4 tables."""
    ROOM_X_C, ROOM_Y_C = 2.70, 9.00
    WALL_H_C, WALL_T_C = 3.0, 0.12
    DOOR_EACH_W, DOOR_H = 0.99, 2.05
    DOOR_TOTAL_W = DOOR_EACH_W * 2
    DOOR_X_START = (ROOM_X_C - DOOR_TOTAL_W) / 2
    DOOR_X_END = DOOR_X_START + DOOR_TOTAL_W

    fig = go.Figure()

    # Floor
    fig.add_trace(go.Mesh3d(
        x=[0, ROOM_X_C, ROOM_X_C, 0],
        y=[0, 0, ROOM_Y_C, ROOM_Y_C],
        z=[0, 0, 0, 0],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color="#E5E7EB", opacity=0.8,
        name="Room C Floor", hoverinfo="skip", showlegend=True
    ))

    def wall(x1, y1, x2, y2, height=WALL_H_C, z0=0):
        dx, dy = x2-x1, y2-y1
        length = np.hypot(dx, dy)
        if length == 0:
            return
        nx = -dy / length * WALL_T_C / 2
        ny = dx / length * WALL_T_C / 2
        pts = [(x1+nx,y1+ny),(x2+nx,y2+ny),(x2-nx,y2-ny),(x1-nx,y1-ny)]
        xs = [p[0] for p in pts] * 2
        ys = [p[1] for p in pts] * 2
        zs = [z0]*4 + [z0+height]*4
        fig.add_trace(go.Mesh3d(
            x=xs,y=ys,z=zs,
            i=[0,0,0,4,4,4], j=[1,2,3,5,6,7], k=[2,3,4,6,7,5],
            color="#6B7280", opacity=0.85, hoverinfo="skip", showlegend=False
        ))

    # Bottom closed, double-door opening on top Y=9
    wall(0,0,0,ROOM_Y_C)
    wall(ROOM_X_C,0,ROOM_X_C,ROOM_Y_C)
    wall(0,0,ROOM_X_C,0)
    wall(0,ROOM_Y_C,DOOR_X_START,ROOM_Y_C)
    wall(DOOR_X_END,ROOM_Y_C,ROOM_X_C,ROOM_Y_C)
    wall(DOOR_X_START,ROOM_Y_C,DOOR_X_END,ROOM_Y_C,
         height=WALL_H_C-DOOR_H,z0=DOOR_H)

    # Use dashboard data when available; otherwise use embedded Room C measurements.
    if wifi is not None and not wifi.empty and {"X","Y","RSSI"}.issubset(wifi.columns):
        d = wifi.dropna(subset=["X","Y","RSSI"]).copy()
    else:
        d = pd.DataFrame({
            "X":[0.00,1.35,2.70,0.00,1.35,2.70,0.00,1.35,2.70],
            "Y":[0.00,0.00,0.00,4.50,4.50,4.50,9.00,9.00,9.00],
            "RSSI":[-82,-90,-84,-77,-67,-58,-77,-84,-75]
        })

    if len(d) >= 3:
        gx=np.linspace(0,ROOM_X_C,80)
        gy=np.linspace(0,ROOM_Y_C,80)
        GX,GY=np.meshgrid(gx,gy)
        try:
            GZ=griddata((d["X"],d["Y"]),d["RSSI"],(GX,GY),method="cubic")
        except Exception:
            GZ=None
        nearest=griddata((d["X"],d["Y"]),d["RSSI"],(GX,GY),method="nearest")
        if GZ is None:
            GZ=nearest
        else:
            GZ=np.where(np.isnan(GZ),nearest,GZ)

        fig.add_trace(go.Surface(
            x=GX,y=GY,z=np.full_like(GZ,0.10),
            surfacecolor=GZ,colorscale="Jet",
            opacity=opacity,showscale=True,
            colorbar=dict(
                title=dict(text="RSSI (dBm)",font=dict(color="#111827",size=13)),
                tickfont=dict(color="#111827",size=11),x=1.02
            ),
            name="Room C Heatmap"
        ))

    if show_points and not d.empty:
        fig.add_trace(go.Scatter3d(
            x=d["X"],y=d["Y"],z=[0.15]*len(d),
            mode="markers+text",
            marker=dict(size=6,color="#111827",line=dict(width=1,color="white")),
            text=[f"<b>{v:.0f}</b>" for v in d["RSSI"]],
            textposition="top center",
            textfont=dict(size=12,color="#000000"),
            name="Survey Points"
        ))

    def box(x,y,z,w,l,h,color,name,op=1.0):
        x0,x1=x-w/2,x+w/2
        y0,y1=y-l/2,y+l/2
        xs=[x0,x1,x1,x0,x0,x1,x1,x0]
        ys=[y0,y0,y1,y1,y0,y0,y1,y1]
        zs=[z,z,z,z,z+h,z+h,z+h,z+h]
        fig.add_trace(go.Mesh3d(
            x=xs,y=ys,z=zs,
            i=[0,0,4,4,0,0,2,2,0,0,1,1],
            j=[1,2,5,6,1,5,3,7,3,7,2,6],
            k=[2,3,6,7,5,4,7,6,7,4,6,5],
            color=color,opacity=op,name=name,hoverinfo="name",showlegend=False
        ))

    def table(name,x,y,w=0.73,l=1.83,h=0.80):
        top_t,leg=0.05,0.06
        box(x,y,h-top_t,w,l,top_t,"#D4A373",name+" Top")
        for xx in [x-w/2+leg/2,x+w/2-leg/2]:
            for yy in [y-l/2+leg/2,y+l/2-leg/2]:
                box(xx,yy,0,leg,leg,h-top_t,"#582F0E",name+" Leg")

    def glass_door(name,hinge_x,angle_deg):
        a=np.radians(angle_deg)
        px1,py1=hinge_x,ROOM_Y_C
        px2=hinge_x+DOOR_EACH_W*np.cos(a)
        py2=ROOM_Y_C+DOOR_EACH_W*np.sin(a)
        t=0.02
        px3=px2-t*np.sin(a); py3=py2+t*np.cos(a)
        px4=px1-t*np.sin(a); py4=py1+t*np.cos(a)
        fig.add_trace(go.Mesh3d(
            x=[px1,px2,px3,px4]*2,y=[py1,py2,py3,py4]*2,
            z=[0]*4+[DOOR_H]*4,
            i=[0,0,4,4,0,0,2,2,0,0,1,1],
            j=[1,2,5,6,1,5,3,7,3,7,2,6],
            k=[2,3,6,7,5,4,7,6,7,4,6,5],
            color="#0EA5E9",opacity=0.35,name=name,
            hoverinfo="name",showlegend=False
        ))

    if show_furniture:
        glass_door("Left Glass Door",DOOR_X_START,-45)
        glass_door("Right Glass Door",DOOR_X_END,225)

        cx=ROOM_X_C/2
        tl=1.83
        y1=ROOM_Y_C-0.60-tl/2
        y2=y1-tl
        y3=y2-tl-0.50
        y4=y3-tl
        for n,yy in enumerate([y1,y2,y3,y4],1):
            table(f"Table {n}",cx,yy)

    fig.update_layout(
        title=dict(text="3D Wi-Fi RSSI Heatmap | Room C",x=0.5,
                   font=dict(size=20,color="#111827")),
        template=None,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#111827"),
        scene=dict(
            bgcolor="#FFFFFF",
            xaxis=dict(title="X (m)",range=[-0.5,ROOM_X_C+0.5],
                       backgroundcolor="#FFFFFF",showbackground=True,
                       gridcolor="#CBD5E1",zerolinecolor="#64748B",color="#111827"),
            yaxis=dict(title="Y (m)",range=[-0.5,ROOM_Y_C+0.5],
                       backgroundcolor="#FFFFFF",showbackground=True,
                       gridcolor="#CBD5E1",zerolinecolor="#64748B",color="#111827"),
            zaxis=dict(title="Height (m)",range=[0,WALL_H_C+0.5],
                       backgroundcolor="#FFFFFF",showbackground=True,
                       gridcolor="#CBD5E1",zerolinecolor="#64748B",color="#111827"),
            aspectmode="manual",
            aspectratio=dict(x=2.7,y=9.0,z=3.0),
            camera=dict(eye=dict(x=1.5,y=1.5,z=1.0))
        ),
        width=1350,
        height=850,
        margin=dict(l=0,r=0,t=70,b=0),
        legend=dict(bgcolor="rgba(255,255,255,0.92)",
                    bordercolor="#D1D5DB",borderwidth=1,
                    font=dict(color="#111827"))
    )
    return fig

def create_3d_heatmap(
    wifi,
    room_name,
    room_x,
    room_y,
    opacity,
    show_ap,
    show_points,
    show_furniture
):

    # ========================================================
    # PREPARE HEATMAP DATA
    # ========================================================

    heatmap_data = (
        wifi
        .groupby(
            ["X", "Y"]
        )["RSSI"]
        .max()
        .reset_index()
    )

    # --------------------------------------------------------
    # Grid
    # --------------------------------------------------------

    grid_x = np.linspace(
        0,
        room_x,
        180
    )

    grid_y = np.linspace(
        0,
        room_y,
        240
    )

    GX, GY = np.meshgrid(
        grid_x,
        grid_y
    )

    # ========================================================
    # INTERPOLATION
    # ========================================================

    points = (
        heatmap_data[
            ["X", "Y"]
        ]
        .values
    )

    values = (
        heatmap_data[
            "RSSI"
        ]
        .values
    )

    # --------------------------------------------------------
    # ใช้ cubic ถ้าข้อมูลเพียงพอ
    # --------------------------------------------------------

    GZ = None

    if len(points) >= 4:

        try:

            GZ = griddata(
                points,
                values,
                (GX, GY),
                method="cubic"
            )

        except Exception:

            GZ = None

    # --------------------------------------------------------
    # ถ้า cubic ใช้ไม่ได้
    # ใช้ linear
    # --------------------------------------------------------

    if GZ is None:

        if len(points) >= 3:

            try:

                GZ = griddata(
                    points,
                    values,
                    (GX, GY),
                    method="linear"
                )

            except Exception:

                GZ = None

    # --------------------------------------------------------
    # เติมพื้นที่ด้วย nearest
    # --------------------------------------------------------

    nearest = griddata(
        points,
        values,
        (GX, GY),
        method="nearest"
    )

    if GZ is None:

        GZ = nearest

    else:

        GZ = np.where(
            np.isnan(GZ),
            nearest,
            GZ
        )

    # --------------------------------------------------------
    # RSSI Range
    # --------------------------------------------------------

    GZ = np.clip(
        GZ,
        -90,
        -50
    )

    # ========================================================
    # COLOR SCALE
    # ========================================================

    custom_scale = [

        # -90 dBm = weak (red)  ->  -50 dBm = strong (green)
        [0.000, "#ef4444"],
        [0.375, "#f97316"],
        [0.625, "#eab308"],
        [1.000, "#22c55e"]

    ]

    # ========================================================
    # CREATE FIGURE
    # ========================================================

    fig = go.Figure()

    # ========================================================
    # HEATMAP SURFACE
    # ========================================================

    fig.add_trace(
        go.Surface(

            x=GX,

            y=GY,

            z=np.zeros_like(GZ) + 0.01,

            surfacecolor=GZ,

            colorscale=custom_scale,

            cmin=-90,

            cmax=-50,

            opacity=opacity,

            showscale=True,

            colorbar=dict(

                title=dict(
                    text="<b>RSSI</b><br>(dBm)"
                ),

                tickvals=[
                    -90,
                    -73,
                    -65,
                    -50
                ],

                ticktext=[
                    "-90 (Weak)",
                    "-73",
                    "-65",
                    "-50 (Strong)"
                ],

                len=0.75,

                thickness=20,

                outlinewidth=0
            ),

            customdata=GZ,

            hovertemplate=(
                "<b>Wi-Fi Signal</b><br>"
                "X : %{x:.2f} m<br>"
                "Y : %{y:.2f} m<br>"
                "RSSI : %{customdata:.1f} dBm"
                "<extra></extra>"
            ),

            name="RSSI Heatmap"
        )
    )

    # ========================================================
    # SURVEY POINTS
    # ========================================================

    if show_points:

        band_data = (
            wifi["Band"]
            if "Band" in wifi.columns
            else pd.Series(
                ["N/A"] * len(wifi),
                index=wifi.index
            )
        )

        channel_data = (
            wifi["Channel"]
            if "Channel" in wifi.columns
            else pd.Series(
                ["N/A"] * len(wifi),
                index=wifi.index
            )
        )

        custom_data_stack = np.column_stack(
            (
                wifi["Point"].astype(str),

                wifi["SSID"].astype(str),

                wifi["RSSI"],

                channel_data,

                band_data.astype(str)
            )
        )

        fig.add_trace(
            go.Scatter3d(

                x=wifi["X"],

                y=wifi["Y"],

                z=np.ones(
                    len(wifi)
                ) * 0.15,

                mode="markers+text",

                text=wifi["Point"],

                textposition="top center",

                marker=dict(

                    size=6,

                    color="white",

                    symbol="circle",

                    line=dict(
                        color="black",
                        width=1.5
                    )
                ),

                customdata=custom_data_stack,

                hovertemplate=(

                    "<b>%{customdata[0]}</b><br>"

                    "RSSI: %{customdata[2]} dBm<br>"

                    "Channel: %{customdata[3]}<br>"

                    "Band: %{customdata[4]}<br>"

                    "SSID: %{customdata[1]}"

                    "<extra></extra>"
                ),

                name="Survey Points"
            )
        )

    # ========================================================
    # ACCESS POINT
    # ========================================================

    if show_ap:

        AP_X = room_x / 2

        AP_Y = room_y / 2

        fig.add_trace(
            go.Scatter3d(

                x=[AP_X],

                y=[AP_Y],

                z=[AP_HEIGHT],

                mode="markers+text",

                marker=dict(

                    size=14,

                    color="#FF0D0D",

                    symbol="diamond",

                    line=dict(
                        color="white",
                        width=2
                    )
                ),

                text=["📡 AP"],

                textposition="top center",

                name="Access Point"
            )
        )

        fig.add_trace(
            go.Scatter3d(

                x=[
                    AP_X,
                    AP_X
                ],

                y=[
                    AP_Y,
                    AP_Y
                ],

                z=[
                    0,
                    AP_HEIGHT
                ],

                mode="lines",

                line=dict(

                    color="#FF3030",

                    width=4,

                    dash="dash"
                ),

                hoverinfo="skip",

                showlegend=False
            )
        )

    # ========================================================
    # FURNITURE / WALLS
    # ========================================================

    if show_furniture:

        # ====================================================
        # WALL FUNCTION
        # ====================================================

        def add_wall(
            x1,
            y1,
            x2,
            y2,
            height,
            z_bottom=0
        ):

            # ทำกำแพงเป็นกล่องบาง ๆ
            thickness = 0.08

            if x1 == x2:

                xx1 = x1 - thickness
                xx2 = x1 + thickness

                yy1 = min(y1, y2)
                yy2 = max(y1, y2)

            else:

                xx1 = min(x1, x2)
                xx2 = max(x1, x2)

                yy1 = y1 - thickness
                yy2 = y1 + thickness

            fig.add_trace(
                go.Mesh3d(

                    x=[
                        xx1,
                        xx2,
                        xx2,
                        xx1,
                        xx1,
                        xx2,
                        xx2,
                        xx1
                    ],

                    y=[
                        yy1,
                        yy1,
                        yy2,
                        yy2,
                        yy1,
                        yy1,
                        yy2,
                        yy2
                    ],

                    z=[
                        z_bottom,
                        z_bottom,
                        z_bottom,
                        z_bottom,
                        height,
                        height,
                        height,
                        height
                    ],

                    i=[
                        0,
                        0,
                        0,
                        4,
                        4,
                        4
                    ],

                    j=[
                        1,
                        2,
                        3,
                        5,
                        6,
                        7
                    ],

                    k=[
                        2,
                        3,
                        4,
                        6,
                        7,
                        5
                    ],

                    color="#8A8A8A",

                    opacity=0.72,

                    hoverinfo="skip",

                    showlegend=False
                )
            )

        # ====================================================
        # ROOM WALLS
        # ====================================================

        # Bottom
        add_wall(
            0,
            0,
            room_x,
            0,
            WALL_HEIGHT
        )

        # Left
        add_wall(
            0,
            0,
            0,
            room_y,
            WALL_HEIGHT
        )

        # Right
        add_wall(
            room_x,
            0,
            room_x,
            room_y,
            WALL_HEIGHT
        )

        # ====================================================
        # DOOR
        # ====================================================

        DOOR_MID = room_x / 2

        DOOR_WIDTH = min(
            1.6,
            room_x * 0.35
        )

        DOOR_HEIGHT = 2.2

        DOOR_X1 = (
            DOOR_MID
            -
            DOOR_WIDTH / 2
        )

        DOOR_X2 = (
            DOOR_MID
            +
            DOOR_WIDTH / 2
        )

        # Wall left side
        add_wall(
            0,
            room_y,
            DOOR_X1,
            room_y,
            WALL_HEIGHT
        )

        # Wall right side
        add_wall(
            DOOR_X2,
            room_y,
            room_x,
            room_y,
            WALL_HEIGHT
        )

        # Door top
        add_wall(
            DOOR_X1,
            room_y,
            DOOR_X2,
            room_y,
            WALL_HEIGHT,
            z_bottom=DOOR_HEIGHT
        )

        # Door frame
        fig.add_trace(
            go.Scatter3d(

                x=[
                    DOOR_X1,
                    DOOR_X1
                ],

                y=[
                    room_y - 0.02,
                    room_y - 0.02
                ],

                z=[
                    0,
                    DOOR_HEIGHT
                ],

                mode="lines",

                line=dict(
                    color="#444",
                    width=8
                ),

                hoverinfo="skip",

                showlegend=False
            )
        )

        fig.add_trace(
            go.Scatter3d(

                x=[
                    DOOR_X2,
                    DOOR_X2
                ],

                y=[
                    room_y - 0.02,
                    room_y - 0.02
                ],

                z=[
                    0,
                    DOOR_HEIGHT
                ],

                mode="lines",

                line=dict(
                    color="#444",
                    width=8
                ),

                hoverinfo="skip",

                showlegend=False
            )
        )

        fig.add_trace(
            go.Scatter3d(

                x=[
                    DOOR_MID,
                    DOOR_MID
                ],

                y=[
                    room_y - 0.02,
                    room_y - 0.02
                ],

                z=[
                    0,
                    DOOR_HEIGHT
                ],

                mode="lines",

                line=dict(
                    color="#444",
                    width=4
                ),

                hoverinfo="skip",

                showlegend=False
            )
        )

        # ====================================================
        # ROOM B FURNITURE
        # ====================================================

        # ใช้เฟอร์นิเจอร์เดิมของโค้ดคุณ
        # เฉพาะ Room B เพราะตำแหน่งเดิมอ้างอิงห้อง 6.8 x 9 m
        # ====================================================

        if room_name == "Room B":

            def create_box_mesh(
                x_min,
                x_max,
                y_min,
                y_max,
                z_min,
                z_max,
                color,
                box_opacity,
                name
            ):

                fig.add_trace(
                    go.Mesh3d(

                        x=[
                            x_min,
                            x_max,
                            x_max,
                            x_min,
                            x_min,
                            x_max,
                            x_max,
                            x_min
                        ],

                        y=[
                            y_min,
                            y_min,
                            y_max,
                            y_max,
                            y_min,
                            y_min,
                            y_max,
                            y_max
                        ],

                        z=[
                            z_min,
                            z_min,
                            z_min,
                            z_min,
                            z_max,
                            z_max,
                            z_max,
                            z_max
                        ],

                        i=[
                            7,
                            0,
                            0,
                            0,
                            4,
                            4,
                            2,
                            6,
                            4,
                            0,
                            3,
                            7
                        ],

                        j=[
                            3,
                            4,
                            1,
                            2,
                            5,
                            6,
                            3,
                            7,
                            5,
                            1,
                            2,
                            6
                        ],

                        k=[
                            0,
                            7,
                            2,
                            3,
                            6,
                            7,
                            7,
                            4,
                            1,
                            5,
                            6,
                            5
                        ],

                        color=color,

                        opacity=box_opacity,

                        name=name,

                        hoverinfo="name"
                    )
                )

            # ------------------------------------------------
            # Flip coordinates
            # ------------------------------------------------

            def get_flipped_box(
                x_min_orig,
                x_max_orig,
                y_min_orig,
                y_max_orig
            ):

                new_x1 = (
                    room_x
                    -
                    x_min_orig
                )

                new_x2 = (
                    room_x
                    -
                    x_max_orig
                )

                new_y1 = (
                    room_y
                    -
                    y_min_orig
                )

                new_y2 = (
                    room_y
                    -
                    y_max_orig
                )

                return (
                    min(new_x1, new_x2),
                    max(new_x1, new_x2),
                    min(new_y1, new_y2),
                    max(new_y1, new_y2)
                )

            # ------------------------------------------------
            # Cabinet 1
            # ------------------------------------------------

            y1_t, y2_t = get_flipped_box(
                0,
                0,
                7.50,
                8.44
            )[2:]

            create_box_mesh(
                0.0,
                0.78,
                y1_t,
                y2_t,
                0,
                1.85,
                "slategray",
                0.85,
                "Cabinet 1"
            )

            # ------------------------------------------------
            # Cabinet 10
            # ------------------------------------------------

            y1_b, y2_b = get_flipped_box(
                0,
                0,
                0.50,
                1.44
            )[2:]

            create_box_mesh(
                0.0,
                0.78,
                y1_b,
                y2_b,
                0,
                1.85,
                "slategray",
                0.85,
                "Cabinet 10"
            )

            # ------------------------------------------------
            # Left Tables
            # ------------------------------------------------

            left_tables = [

                (
                    11,
                    7.00,
                    7.78,
                    "chocolate"
                ),

                (
                    12,
                    6.20,
                    6.98,
                    "chocolate"
                ),

                (
                    13,
                    4.40,
                    5.18,
                    "peru"
                ),

                (
                    14,
                    3.60,
                    4.38,
                    "peru"
                ),

                (
                    15,
                    1.80,
                    2.58,
                    "burlywood"
                ),

                (
                    16,
                    1.00,
                    1.78,
                    "burlywood"
                )
            ]

            for (
                item_id,
                y_min,
                y_max,
                col
            ) in left_tables:

                _, _, y1, y2 = (
                    get_flipped_box(
                        0.0,
                        0.0,
                        y_min,
                        y_max
                    )
                )

                create_box_mesh(
                    room_x - 1.84,
                    room_x,
                    y1,
                    y2,
                    0,
                    0.80,
                    col,
                    0.85,
                    f"Table {item_id}"
                )

            # ------------------------------------------------
            # Right Tables
            # ------------------------------------------------

            right_tables_grouped = [

                (
                    2,
                    0.00,
                    1.84,
                    5.40,
                    6.18,
                    "saddlebrown"
                ),

                (
                    4,
                    1.84,
                    3.68,
                    5.40,
                    6.18,
                    "saddlebrown"
                ),

                (
                    3,
                    0.00,
                    1.84,
                    4.60,
                    5.38,
                    "saddlebrown"
                ),

                (
                    5,
                    1.84,
                    3.68,
                    4.60,
                    5.38,
                    "saddlebrown"
                ),

                (
                    6,
                    0.00,
                    1.84,
                    2.60,
                    3.38,
                    "sandybrown"
                ),

                (
                    8,
                    1.84,
                    3.68,
                    2.60,
                    3.38,
                    "sandybrown"
                ),

                (
                    7,
                    0.00,
                    1.84,
                    1.80,
                    2.58,
                    "sandybrown"
                ),

                (
                    9,
                    1.84,
                    3.68,
                    1.80,
                    2.58,
                    "sandybrown"
                )
            ]

            for (
                item_id,
                x_min_dir,
                x_max_dir,
                y_min_orig,
                y_max_orig,
                col
            ) in right_tables_grouped:

                _, _, y1, y2 = (
                    get_flipped_box(
                        0,
                        0,
                        y_min_orig,
                        y_max_orig
                    )
                )

                create_box_mesh(
                    x_min_dir,
                    x_max_dir,
                    y1,
                    y2,
                    0,
                    0.80,
                    col,
                    0.85,
                    f"Table {item_id}"
                )

            # ------------------------------------------------
            # Object 17
            # ------------------------------------------------

            x1, x2, y1, y2 = (
                get_flipped_box(
                    2.10,
                    2.88,
                    0.0,
                    0.78
                )
            )

            create_box_mesh(
                x1,
                x2,
                y1,
                y2,
                0,
                0.80,
                "darkkhaki",
                0.85,
                "Object 17"
            )

    # ========================================================
    # FIGURE LAYOUT
    # ========================================================

    # ให้ aspect ratio เปลี่ยนตามขนาดห้อง
    ratio_x = max(room_x, 1)
    ratio_y = max(room_y, 1)

    fig.update_layout(

        paper_bgcolor="#FFFFFF",

        plot_bgcolor="#FFFFFF",

        font=dict(
            color="white"
        ),

        scene=dict(

            xaxis=dict(

                title="X (m)",

                range=[
                    -0.5,
                    room_x + 0.7
                ],

                gridcolor="#273746",

                zerolinecolor="#273746"
            ),

            yaxis=dict(

                title="Y (m)",

                range=[
                    -0.7,
                    room_y + 0.5
                ],

                gridcolor="#273746",

                zerolinecolor="#273746"
            ),

            zaxis=dict(

                title="Height (m)",

                range=[
                    0,
                    4.5
                ],

                gridcolor="#273746",

                zerolinecolor="#273746"
            ),

            aspectmode="manual",

            aspectratio=dict(

                x=ratio_x,

                y=ratio_y,

                z=3.5
            ),

            camera=dict(

                eye=dict(
                    x=1.35,
                    y=1.35,
                    z=0.9
                )
            )
        ),

        height=700,

        margin=dict(
            l=0,
            r=0,
            t=10,
            b=0
        ),

        legend=dict(

            bgcolor="rgba(255,255,255,0.94)",

            bordercolor="#D1D5DB",

            borderwidth=1
        )
    )

    return fig



# ============================================================
# ROOM A — COMBINED 3D HEATMAP (A1-A4)
# ============================================================
ROOM_A_X = 7.20
ROOM_A_Y = 8.40
ROOM_A_WALL_THICKNESS = 0.12

ROOM_A_LAYOUT = {
    "A1": {"room_key": "Room 1", "x_min": 0.0,   "x_max": 3.535, "y_min": 4.20, "y_max": 8.33},
    "A2": {"room_key": "Room 2", "x_min": 3.535, "x_max": 7.105, "y_min": 2.83, "y_max": 8.30},
    "A3": {"room_key": "Room 3", "x_min": 0.0,   "x_max": 3.535, "y_min": 0.0,  "y_max": 4.20},
    "A4": {"room_key": "Room 4", "x_min": 3.535, "x_max": 7.105, "y_min": 0.0,  "y_max": 2.83},
}


ROOM_A_FALLBACK_DATA = {
    "Room 1": pd.DataFrame({
        "Point": [f"A1-P{i}" for i in range(1, 10)],
        "X": [0.00, 1.77, 3.54, 0.00, 1.77, 3.54, 0.00, 1.77, 3.54],
        "Y": [0.00, 0.00, 0.00, 2.07, 2.07, 2.07, 4.13, 4.13, 4.13],
        "RSSI": [-70, -64, -68, -68, -74, -70, -77, -68, -75],
        "SSID": ["KMITL-WIFI"] * 9, "BSSID": ["Room-A1"] * 9
    }),
    "Room 2": pd.DataFrame({
        "Point": [f"A2-P{i}" for i in range(1, 13)],
        "X": [0.00,1.78,3.57,0.00,1.78,3.57,0.00,1.78,3.57,0.00,1.78,3.57],
        "Y": [0.00,0.00,0.00,1.82,1.82,1.82,3.65,3.65,3.65,5.47,5.47,5.47],
        "RSSI": [-56,-66,-81,-85,-71,-75,-65,-70,-70,-70,-69,-71],
        "SSID": ["KMITL-WIFI"] * 12, "BSSID": ["Room-A2"] * 12
    }),
    "Room 3": pd.DataFrame({
        "Point": [f"A3-P{i}" for i in range(1, 10)],
        "X": [0.00,1.77,3.54,0.00,1.77,3.54,0.00,1.77,3.54],
        "Y": [0.00,0.00,0.00,2.10,2.10,2.10,4.20,4.20,4.20],
        "RSSI": [-74,-62,-71,-63,-69,-70,-67,-60,-64],
        "SSID": ["KMITL-WIFI"] * 9, "BSSID": ["Room-A3"] * 9
    }),
    "Room 4": pd.DataFrame({
        "Point": [f"A4-P{i}" for i in range(1, 10)],
        "X": [0.00,1.78,3.57,0.00,1.78,3.57,0.00,1.78,3.57],
        "Y": [0.00,0.00,0.00,1.41,1.41,1.41,2.83,2.83,2.83],
        "RSSI": [-73,-67,-74,-63,-66,-70,-64,-66,-75],
        "SSID": ["KMITL-WIFI"] * 9, "BSSID": ["Room-A4"] * 9
    }),
}


def _load_room_a_csv(room_key):
    """Load A1-A4 CSV; if unavailable, use the Room A survey data supplied by the user."""
    filename = ROOMS[room_key]["file"]
    if not filename or not os.path.exists(filename):
        return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()
    try:
        d = pd.read_csv(filename, skipinitialspace=True)
        d.columns = d.columns.astype(str).str.strip()
        d.rename(columns={
            "Point ID": "Point", "X (m)": "X", "Y (m)": "Y",
            "RSSI (dBm)": "RSSI", "RSSI_dBm": "RSSI",
            "Frequency (MHz)": "Frequency", "channel": "Channel"
        }, inplace=True)
        for col in ["X", "Y", "RSSI", "Channel"]:
            if col in d.columns:
                d[col] = pd.to_numeric(d[col], errors="coerce")
        required = {"X", "Y", "RSSI"}
        if not required.issubset(d.columns):
            return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()
        return d.dropna(subset=["X", "Y", "RSSI"]).copy()
    except Exception:
        return ROOM_A_FALLBACK_DATA.get(room_key, pd.DataFrame()).copy()


def load_room_a_combined_data():
    """
    Build one dataframe for the complete Room A (A1-A4).
    CSV files are used when available; embedded fallback data is used otherwise.
    Local X/Y coordinates are shifted into the 7.20 x 8.40 m Room A plan.
    """
    frames = []

    for label, layout in ROOM_A_LAYOUT.items():
        room_key = layout["room_key"]
        d = _load_room_a_csv(room_key).copy()

        if d.empty:
            continue

        # Keep original local coordinates for reference.
        d["Local_X"] = pd.to_numeric(d["X"], errors="coerce")
        d["Local_Y"] = pd.to_numeric(d["Y"], errors="coerce")

        # Shift each sub-room into the full Room A coordinate system.
        d["X"] = d["Local_X"] + layout["x_min"]
        d["Y"] = d["Local_Y"] + layout["y_min"]
        d["Subroom"] = label

        # Make point names unique across A1-A4.
        if "Point" not in d.columns:
            d["Point"] = [f"{label}-P{i+1}" for i in range(len(d))]
        else:
            d["Point"] = label + "-" + d["Point"].astype(str)

        if "SSID" not in d.columns:
            d["SSID"] = "KMITL-WIFI"
        if "BSSID" not in d.columns:
            d["BSSID"] = label + "-AP"

        frames.append(d)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def create_room_a_combined_heatmap(opacity=0.85, show_ap=True, show_points=True, show_furniture=True):
    """Create the complete Room A 3D view with four sub-room heatmaps."""
    fig = go.Figure()
    custom_scale = [[0.0, "#ef4444"], [0.375, "#f97316"], [0.625, "#eab308"], [1.0, "#22c55e"]]

    def add_wall(x1, y1, x2, y2, height=WALL_HEIGHT, z0=0):
        dx, dy = x2-x1, y2-y1
        length = float(np.hypot(dx, dy))
        if length == 0:
            return
        nx = -dy / length * ROOM_A_WALL_THICKNESS / 2
        ny =  dx / length * ROOM_A_WALL_THICKNESS / 2
        pts = [(x1+nx,y1+ny),(x2+nx,y2+ny),(x2-nx,y2-ny),(x1-nx,y1-ny)]
        xs=[q[0] for q in pts]*2; ys=[q[1] for q in pts]*2
        zs=[z0,z0,z0,z0,z0+height,z0+height,z0+height,z0+height]
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,
            i=[0,0,0,4,4,4,0,1,2,3,0,1],
            j=[1,2,3,5,6,7,1,2,3,0,4,5],
            k=[2,3,4,6,7,5,5,6,7,4,5,6],
            color="#808080", opacity=.72, hoverinfo="skip", showlegend=False))

    def add_box(x, y, z, w, l, h, color, name):
        x0,x1=x-w/2,x+w/2; y0,y1=y-l/2,y+l/2; z0,z1=z,z+h
        xs=[x0,x1,x1,x0,x0,x1,x1,x0]; ys=[y0,y0,y1,y1,y0,y0,y1,y1]; zs=[z0]*4+[z1]*4
        fig.add_trace(go.Mesh3d(x=xs,y=ys,z=zs,
            i=[0,0,4,4,0,0,2,2,0,0,1,1], j=[1,2,5,6,1,5,3,7,3,7,2,6],
            k=[2,3,6,7,5,4,7,6,7,4,6,5], color=color, opacity=1.0,
            name=name, hoverinfo="name", showlegend=False))

    def add_table(name, x, y, w, l, h=.80):
        top=.05; leg=.06
        add_box(x,y,h-top,w,l,top,"#DEB887",name)
        for sx in (-1,1):
            for sy in (-1,1):
                add_box(x+sx*(w/2-leg/2), y+sy*(l/2-leg/2), 0, leg,leg,h-top,"#5C4033",name)

    # Four heatmap surfaces, each generated from its own CSV and shifted into Room A coordinates.
    for label, cfg in ROOM_A_LAYOUT.items():
        d = _load_room_a_csv(cfg["room_key"])
        cx=(cfg["x_min"]+cfg["x_max"])/2; cy=(cfg["y_min"]+cfg["y_max"])/2
        fig.add_trace(go.Scatter3d(x=[cx],y=[cy],z=[0.18],mode="text",text=[label],
                                   textfont=dict(size=20,color="white"),hoverinfo="skip",showlegend=False))
        if d.empty:
            continue
        xoff=cfg["x_min"]; yoff=cfg["y_min"]
        local_x=d["X"].to_numpy(float); local_y=d["Y"].to_numpy(float); vals=d["RSSI"].to_numpy(float)
        gx=np.linspace(0, cfg["x_max"]-cfg["x_min"], 90)
        gy=np.linspace(0, cfg["y_max"]-cfg["y_min"], 110)
        GX0,GY0=np.meshgrid(gx,gy)
        GZ=None
        if len(d)>=4:
            try: GZ=griddata((local_x,local_y),vals,(GX0,GY0),method="cubic")
            except Exception: GZ=None
        if GZ is None and len(d)>=3:
            try: GZ=griddata((local_x,local_y),vals,(GX0,GY0),method="linear")
            except Exception: GZ=None
        nearest=griddata((local_x,local_y),vals,(GX0,GY0),method="nearest")
        GZ=nearest if GZ is None else np.where(np.isnan(GZ),nearest,GZ)
        GZ=np.clip(GZ,-90,-50)
        GX=GX0+xoff; GY=GY0+yoff
        fig.add_trace(go.Surface(x=GX,y=GY,z=np.zeros_like(GZ)+.03,surfacecolor=GZ,
            colorscale=custom_scale,cmin=-90,cmax=-50,opacity=opacity,showscale=(label=="A1"),
            colorbar=dict(title="RSSI (dBm)",len=.72,thickness=18) if label=="A1" else None,
            customdata=GZ,hovertemplate=f"<b>{label}</b><br>X: %{{x:.2f}} m<br>Y: %{{y:.2f}} m<br>RSSI: %{{customdata:.1f}} dBm<extra></extra>",
            name=f"Heatmap {label}",showlegend=False))
        if show_points:
            fig.add_trace(go.Scatter3d(x=local_x+xoff,y=local_y+yoff,z=np.full(len(d),.13),mode="markers",
                marker=dict(size=4,color="white",line=dict(color="black",width=1)),
                customdata=vals,hovertemplate=f"<b>{label}</b><br>RSSI: %{{customdata:.1f}} dBm<extra></extra>",
                name=f"{label} Survey",showlegend=False))

    # --------------------------------------------------------
    # Room A walls and door openings — updated from supplied plan
    # --------------------------------------------------------
    DOOR_H = 2.06
    DOOR_W = 0.97

    # Outer walls. A3 has a 1.94 m double swing door at X=1.03..2.97.
    add_wall(0, 0, 1.03, 0)
    add_wall(2.97, 0, ROOM_A_X, 0)
    add_wall(1.03, 0, 2.97, 0, height=WALL_HEIGHT-DOOR_H, z0=DOOR_H)
    add_wall(0, 0, 0, ROOM_A_Y)
    add_wall(ROOM_A_X, 0, ROOM_A_X, ROOM_A_Y)
    add_wall(0, ROOM_A_Y, ROOM_A_X, ROOM_A_Y)

    # A1/A3 divider with sliding door at X=2.45..3.42.
    add_wall(0, 4.20, 2.45, 4.20)
    add_wall(3.42, 4.20, 3.535, 4.20)
    add_wall(2.45, 4.20, 3.42, 4.20, height=WALL_HEIGHT-DOOR_H, z0=DOOR_H)

    # A2/A4 divider.
    add_wall(3.535, 2.83, 7.105, 2.83)

    # A1/A2 divider.
    add_wall(3.535, 4.20, 3.535, 8.33)

    # A3/A4 divider with A4 sliding door at Y=1.86..2.83.
    add_wall(3.535, 0, 3.535, 1.86)
    add_wall(3.535, 1.86, 3.535, 2.83, height=WALL_HEIGHT-DOOR_H, z0=DOOR_H)

    # A2/A3 divider with A2 sliding door at Y=3.03..4.00.
    add_wall(3.535, 2.83, 3.535, 3.03)
    add_wall(3.535, 4.00, 3.535, 4.20)
    add_wall(3.535, 3.03, 3.535, 4.00, height=WALL_HEIGHT-DOOR_H, z0=DOOR_H)

    def add_sliding_door(name, x, y, length, orientation="horizontal"):
        t = 0.04
        if orientation == "horizontal":
            add_box(x + length/2, y, 0, length, t, DOOR_H, "lightblue", name)
        else:
            add_box(x, y + length/2, 0, t, length, DOOR_H, "lightblue", name)

    def add_swing_door(name, hinge_x, hinge_y, width, angle_deg):
        a = np.radians(angle_deg)
        x2 = hinge_x + width*np.cos(a)
        y2 = hinge_y + width*np.sin(a)
        t = 0.02
        nx, ny = -np.sin(a)*t, np.cos(a)*t
        xs = [hinge_x, x2, x2+nx, hinge_x+nx]*2
        ys = [hinge_y, y2, y2+ny, hinge_y+ny]*2
        zs = [0]*4 + [DOOR_H]*4
        fig.add_trace(go.Mesh3d(
            x=xs, y=ys, z=zs,
            i=[0,0,4,4,0,0,2,2,0,0,1,1],
            j=[1,2,5,6,1,5,3,7,3,7,2,6],
            k=[2,3,6,7,5,4,7,6,7,4,6,5],
            color="lightblue", opacity=0.40, name=name,
            hoverinfo="name", showlegend=False
        ))

    if show_furniture:
        # Doors
        add_sliding_door("A1 Sliding Door", 2.45, 4.20-(ROOM_A_WALL_THICKNESS/2+0.01), 0.97, "horizontal")
        add_sliding_door("A2 Sliding Door", 3.535+(ROOM_A_WALL_THICKNESS/2+0.01), 3.03, 0.97, "vertical")
        add_sliding_door("A4 Sliding Door", 3.535-(ROOM_A_WALL_THICKNESS/2+0.01), 1.86, 0.97, "vertical")
        add_swing_door("A3 Left Swing Door", 1.03, 0.0, 0.97, 45)
        add_swing_door("A3 Right Swing Door", 2.97, 0.0, 0.97, 135)

        tw,tl=.73,1.83
        # A1: two central tables
        cx=(0+3.535)/2; cy=(4.20+8.33)/2
        add_table("A1 Table 1",cx,cy+tw/2,tl,tw); add_table("A1 Table 2",cx,cy-tw/2,tl,tw)
        # A2: four central tables
        cx=(3.535+7.105)/2; cy=(2.83+8.30)/2; gap=.50
        for idx,yy in enumerate([cy+gap/2+tw/2,cy+gap/2+1.5*tw,cy-gap/2-tw/2,cy-gap/2-1.5*tw],1):
            add_table(f"A2 Table {idx}",cx,yy,tl,tw)
        # A3: two tables at left + cabinet
        cy=2.10; x1=tw/2+ROOM_A_WALL_THICKNESS/2
        add_table("A3 Table 1",x1,cy,tw,tl); add_table("A3 Table 2",x1+tw,cy,tw,tl)
        add_box(ROOM_A_WALL_THICKNESS/2+.49/2,4.20-ROOM_A_WALL_THICKNESS/2-.95/2,0,.49,.95,1.86,"#8B4513","A3 Cabinet")
        # A4: two central tables
        cx=(3.535+7.105)/2; cy=2.83/2
        add_table("A4 Table 1",cx,cy+tw/2,tl,tw); add_table("A4 Table 2",cx,cy-tw/2,tl,tw)

    if show_ap:
        # AP marker at the center of the complete Room A plan.
        ap_x, ap_y = ROOM_A_X/2, ROOM_A_Y/2
        fig.add_trace(go.Scatter3d(
            x=[ap_x], y=[ap_y], z=[AP_HEIGHT],
            mode="markers+text",
            marker=dict(size=14, color="#FF0D0D", symbol="diamond",
                        line=dict(color="white", width=2)),
            text=["📡 AP"], textposition="top center",
            name="Access Point"
        ))
        fig.add_trace(go.Scatter3d(
            x=[ap_x, ap_x], y=[ap_y, ap_y], z=[0, AP_HEIGHT],
            mode="lines", line=dict(color="#FF3030", width=4, dash="dash"),
            hoverinfo="skip", showlegend=False
        ))

    fig.update_layout(
        title=dict(text="Room A — 3D Wi-Fi RSSI Heatmap (A1–A4)",x=.5),
        paper_bgcolor="#FFFFFF",plot_bgcolor="#FFFFFF",font=dict(color="#111827"),
        scene=dict(bgcolor="#FFFFFF",
            xaxis=dict(title="X (m)",range=[-.5,ROOM_A_X+.5],gridcolor="#273746"),
            yaxis=dict(title="Y (m)",range=[-.5,ROOM_A_Y+.5],gridcolor="#273746"),
            zaxis=dict(title="Height (m)",range=[0,WALL_HEIGHT+.5],gridcolor="#273746"),
            aspectmode="manual",aspectratio=dict(x=7.2,y=8.4,z=3.5),
            camera=dict(eye=dict(x=1.35,y=1.35,z=.9))),
        height=820,margin=dict(l=0,r=0,t=60,b=0),
        legend=dict(bgcolor="rgba(0,0,0,.4)"))
    return fig

# ============================================================
# SMART WI-FI ADVISOR
# ============================================================

def analyze_wifi_recommendation(df):
    """
    Compare SSIDs using average RSSI, percentage of good measurements,
    signal stability, and a penalty for weak measurements.
    """
    if df is None or df.empty or "SSID" not in df.columns:
        return pd.DataFrame()

    results = []

    for ssid, group in df.groupby("SSID"):
        rssi = pd.to_numeric(group["RSSI"], errors="coerce").dropna()
        if rssi.empty:
            continue

        avg_rssi = float(rssi.mean())
        min_rssi = float(rssi.min())
        max_rssi = float(rssi.max())
        std_rssi = float(rssi.std()) if len(rssi) > 1 else 0.0
        if np.isnan(std_rssi):
            std_rssi = 0.0

        total = len(rssi)
        good_percent = float((rssi >= -65).sum() / total * 100)
        weak_percent = float((rssi <= -75).sum() / total * 100)

        # Normalize -90..-50 dBm to 0..100.
        rssi_score = float(np.clip(((avg_rssi + 90) / 40) * 100, 0, 100))
        stability_score = float(np.clip(100 - std_rssi * 8, 0, 100))

        score = (
            rssi_score * 0.50
            + good_percent * 0.25
            + stability_score * 0.15
            + (100 - weak_percent) * 0.10
        )

        if avg_rssi >= -60:
            quality = "Excellent"
        elif avg_rssi >= -67:
            quality = "Good"
        elif avg_rssi >= -75:
            quality = "Fair"
        else:
            quality = "Weak"

        results.append({
            "SSID": str(ssid),
            "Average RSSI": avg_rssi,
            "Weakest RSSI": min_rssi,
            "Strongest RSSI": max_rssi,
            "Stability": std_rssi,
            "Good Signal (%)": good_percent,
            "Weak Signal (%)": weak_percent,
            "Measurements": total,
            "Score": score,
            "Quality": quality,
        })

    result = pd.DataFrame(results)
    if not result.empty:
        result = result.sort_values(
            ["Score", "Average RSSI"],
            ascending=[False, False]
        ).reset_index(drop=True)

    return result


def recommend_wifi_at_point(df, point):
    """
    Recommend an SSID at one measured survey point.
    If an SSID has multiple BSSIDs, use its strongest observed BSSID
    at that point.
    """
    if df is None or df.empty:
        return None, pd.DataFrame()

    point_data = df[
        df["Point"].astype(str) == str(point)
    ].copy()

    if point_data.empty:
        return None, pd.DataFrame()

    point_summary = (
        point_data
        .groupby("SSID")
        .agg(
            RSSI=("RSSI", "max"),
            AP_Count=("BSSID", "nunique")
        )
        .reset_index()
        .sort_values("RSSI", ascending=False)
        .reset_index(drop=True)
    )

    if point_summary.empty:
        return None, point_summary

    return point_summary.iloc[0], point_summary


def signal_quality(rssi, language="ไทย"):
    if rssi >= -60:
        return ("🟢 Excellent", "สัญญาณแรงมาก เหมาะสำหรับ Video Call, Streaming และงานที่ต้องการความเสถียร") \
            if language == "ไทย" else ("🟢 Excellent", "Very strong signal for video calls, streaming and demanding use.")
    if rssi >= -67:
        return ("🟢 Good", "สัญญาณดี เหมาะสำหรับการใช้งานทั่วไปและ Video Call") \
            if language == "ไทย" else ("🟢 Good", "Good signal for general use and video calls.")
    if rssi >= -75:
        return ("🟡 Fair", "สามารถใช้งานได้ แต่อาจมีความไม่เสถียรในบางช่วง") \
            if language == "ไทย" else ("🟡 Fair", "Usable signal, but performance may be less stable.")
    return ("🔴 Weak", "สัญญาณค่อนข้างอ่อน แนะนำให้ลอง Wi-Fi อื่นหรือขยับเข้าใกล้ Access Point") \
        if language == "ไทย" else ("🔴 Weak", "Weak signal. Try another Wi-Fi or move closer to an access point.")


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
ROOM_DISPLAY = {"Room 1": "A1", "Room 2": "A2", "Room 3": "A3", "Room 4": "A4",
                "Room B": "B", "Room C": "C"}

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    language = st.selectbox(
        "🌐 ภาษา / Language",
        ["ไทย", "English"],
        index=0,
        key="language_selector"
    )
    t = TEXT[language]

    st.header(t["settings"])
    st.subheader(t["area_select"])

    # เรียงพื้นที่ตามลำดับ A → B → C
    selected_area = st.radio(
        t["area"],
        ["Room A", "Room B", "Room C"],
        index=0
    )

    # Room A can be used as one complete survey area or as A1-A4.
    if selected_area == "Room A":
        room_a_options = (
            ["ภาพรวม Room A", "A1", "A2", "A3", "A4"]
            if language == "ไทย"
            else ["Room A Overview", "A1", "A2", "A3", "A4"]
        )

        st.markdown(
            "#### 🚪 ห้องย่อย Room A"
            if language == "ไทย"
            else "#### 🚪 Room A Subrooms"
        )

        selected_subroom = st.selectbox(
            "เลือกมุมมอง / ห้องย่อย"
            if language == "ไทย"
            else "Select overview / subroom",
            room_a_options,
            key="room_a_view"
        )

        if selected_subroom in ["ภาพรวม Room A", "Room A Overview"]:
            selected_room = "Room A"
        else:
            selected_room = ROOM_A_DISPLAY[selected_subroom]
    else:
        selected_room = selected_area

    display_room = ROOM_DISPLAY.get(selected_room, selected_room)
    st.divider()

    # ========================================================
    # FILE
    # ========================================================

    default_filename = ROOMS[
        selected_room
    ]["file"]

    if selected_room == "Room A":
        st.caption(
            "ข้อมูล Room A: A1 + A2 + A3 + A4"
            if language == "ไทย"
            else "Room A data: A1 + A2 + A3 + A4"
        )
    else:
        st.caption(
            f"{t['default_file']}: `{default_filename}`"
        )

    uploaded_file = st.file_uploader(
        t["upload"],
        type=[
            "csv",
            "xlsx"
        ],
        key=f"upload_{selected_room}"
    )


# ============================================================
# LOAD FILE
# ============================================================

if uploaded_file is not None:

    df = load_data(
        uploaded_file
    )

elif selected_room == "Room A":

    # ภาพรวม Room A: รวมข้อมูล A1-A4
    df = load_room_a_combined_data()

    if df is None or df.empty:
        st.error(
            "❌ ไม่สามารถโหลดข้อมูล Room A (A1-A4) ได้"
            if language == "ไทย"
            else "❌ Unable to load Room A data (A1-A4)."
        )
        st.stop()

elif selected_room in ["Room 1", "Room 2", "Room 3", "Room 4"]:

    # A1-A4: ใช้ CSV ถ้ามี และใช้ข้อมูล fallback ที่ฝังไว้ถ้าไม่มีไฟล์
    df = _load_room_a_csv(selected_room)

    if df is None or df.empty:
        st.error(
            f"❌ ไม่พบข้อมูล {ROOM_DISPLAY.get(selected_room, selected_room)}"
            if language == "ไทย"
            else f"❌ No data found for {ROOM_DISPLAY.get(selected_room, selected_room)}."
        )
        st.stop()

else:

    default_file = find_default_file(
        default_filename
    )

    if default_file is not None:

        try:

            df = pd.read_csv(
                default_file,
                skipinitialspace=True
            )

            df.columns = (
                df.columns
                .astype(str)
                .str.strip()
            )

            rename_mapping = {

                "Point ID": "Point",
                "X (m)": "X",
                "Y (m)": "Y",
                "RSSI (dBm)": "RSSI",
                "Frequency (MHz)": "Frequency"
            }

            df.rename(
                columns=rename_mapping,
                inplace=True
            )

            # Convert
            df["X"] = pd.to_numeric(
                df["X"],
                errors="coerce"
            )

            df["Y"] = pd.to_numeric(
                df["Y"],
                errors="coerce"
            )

            df["RSSI"] = pd.to_numeric(
                df["RSSI"],
                errors="coerce"
            )

            if "Channel" in df.columns:

                df["Channel"] = pd.to_numeric(
                    df["Channel"],
                    errors="coerce"
                )

            df = df.dropna(
                subset=[
                    "X",
                    "Y",
                    "RSSI"
                ]
            ).copy()

        except Exception as e:

            st.error(
                f"ไม่สามารถอ่าน `{default_filename}` ได้: {e}"
            )

            st.stop()

    else:

        st.info(
            f"""
👆 ยังไม่พบไฟล์ `{default_filename}`

สามารถอัปโหลดไฟล์ CSV/XLSX
ด้านซ้ายเพื่อเริ่มใช้งาน
"""
        )

        st.stop()


# ============================================================
# CHECK DATA
# ============================================================

if df is None or df.empty:

    st.error(
        "❌ ไม่พบข้อมูล Survey"
    )

    st.stop()


# ============================================================
# ROOM SIZE
# ============================================================

ROOM_X, ROOM_Y = get_room_size(
    df,
    selected_room
)


# ============================================================
# SIDEBAR CONTROLS
# ============================================================

with st.sidebar:

    st.divider()

    # ========================================================
    # SSID
    # ========================================================

    st.subheader(
        t["ssid"]
    )

    if "SSID" in df.columns:

        ssid_options = sorted(
            df["SSID"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_ssids = st.multiselect(
            "SSID",
            options=ssid_options,
            default=ssid_options
        )

    else:

        selected_ssids = []

        st.warning(
            "ไม่พบ Column SSID"
        )

    # ========================================================
    # HEATMAP OPACITY
    # ========================================================

    opacity = st.slider(
        t["opacity"],
        0.0,
        1.0,
        0.85,
        0.05
    )

    # ========================================================
    # 3D LAYERS
    # ========================================================

    st.divider()

    st.subheader(
        t["layers"]
    )

    show_ap = st.checkbox(
        t["show_ap"],
        True
    )

    show_points = st.checkbox(
        t["show_points"],
        True
    )

    show_furniture = st.checkbox(
        t["show_furniture"],
        True
    )


# ============================================================
# FILTER SSID
# ============================================================

if selected_ssids:

    wifi = df[
        df["SSID"]
        .astype(str)
        .isin(selected_ssids)
    ].copy()

else:

    wifi = df.copy()


# ============================================================
# SMART WI-FI RECOMMENDATION FOR CURRENT ROOM
# ============================================================

wifi_recommendation = analyze_wifi_recommendation(wifi)
best_wifi = (
    wifi_recommendation.iloc[0]
    if not wifi_recommendation.empty
    else None
)


# ============================================================
# HEADER
# ============================================================

page_subtitle = (
    "ระบบวิเคราะห์คุณภาพสัญญาณและแนะนำ Wi-Fi ตามพื้นที่ใช้งาน"
    if language == "ไทย"
    else "Wireless signal analysis and smart Wi-Fi recommendation dashboard"
)

st.markdown(
    f"""
    <div class="dashboard-title">Portable Wireless Site Survey and Network Analysis System</div>
    <div class="dashboard-subtitle">ระบบสำรวจและวิเคราะห์คุณภาพเครือข่ายไร้สายแบบพกพา</div>
    <div class="room-badge">📍 {display_room}</div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# ROOM INFORMATION
# ============================================================

col_info, col_blank = st.columns(
    [1, 1]
)

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


# ============================================================
# QUICK RECOMMENDATION
# ============================================================

if best_wifi is not None:
    best_ssid = best_wifi["SSID"]
    best_avg = float(best_wifi["Average RSSI"])
    best_good = float(best_wifi["Good Signal (%)"])
    best_quality = best_wifi["Quality"]

    if language == "ไทย":
        recommendation_title = f"Wi-Fi แนะนำสำหรับห้อง {display_room}"
        recommendation_detail = (
            f"RSSI เฉลี่ย {best_avg:.1f} dBm • "
            f"จุดวัดสัญญาณดี {best_good:.1f}% • "
            f"คุณภาพ {best_quality}"
        )
    else:
        recommendation_title = f"Recommended Wi-Fi for {display_room}"
        recommendation_detail = (
            f"Average RSSI {best_avg:.1f} dBm • "
            f"Good measurements {best_good:.1f}% • "
            f"Quality {best_quality}"
        )

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


# ============================================================
# OVERVIEW
# ============================================================

if not wifi.empty:

    total_points = (
        wifi["Point"]
        .nunique()
    )

    detected_aps = (
        wifi["BSSID"]
        .nunique()
    )

    avg_rssi = (
        wifi["RSSI"]
        .mean()
    )

    strong_signals = len(
        wifi[
            wifi["RSSI"] >= -65
        ]
    )

    weak_signals = len(
        wifi[
            wifi["RSSI"] <= -75
        ]
    )

    # --------------------------------------------------------
    # KPI ROW 1
    # --------------------------------------------------------

    c1, c2, c3 = st.columns(3)

    c1.metric(
        f"📍 {t['survey_points']}",
        total_points
    )

    c2.metric(
        f"📡 {t['access_points']}",
        detected_aps
    )

    c3.metric(
        f"📈 {t['avg_rssi']}",
        f"{avg_rssi:.1f} dBm"
    )

    # --------------------------------------------------------
    # KPI ROW 2
    # --------------------------------------------------------

    c4, c5, c6 = st.columns(3)

    c4.metric(
        f"🟢 {t['strong']} (>= -65 dBm)",
        strong_signals
    )

    c5.metric(
        f"🔴 {t['weak']} (<= -75 dBm)",
        weak_signals
    )

    c6.metric(
        f"📐 {t['room_size']}",
        f"{ROOM_X:.2f} × {ROOM_Y:.2f} m"
    )

    # Signal quality summary based on measured records
    st.subheader(t["signal_summary"])
    total_records = max(len(wifi), 1)
    good_n = int((wifi["RSSI"] >= -65).sum())
    fair_n = int(((wifi["RSSI"] < -65) & (wifi["RSSI"] > -75)).sum())
    weak_n = int((wifi["RSSI"] <= -75).sum())
    q1, q2, q3 = st.columns(3)
    q1.metric(f"🟢 {t['excellent']} (≥ -65 dBm)", f"{good_n / total_records * 100:.1f}%", f"{good_n} records")
    q2.metric(f"🟡 {t['fair']} (-75 to -65 dBm)", f"{fair_n / total_records * 100:.1f}%", f"{fair_n} records")
    q3.metric(f"🔴 {t['poor']} (≤ -75 dBm)", f"{weak_n / total_records * 100:.1f}%", f"{weak_n} records")


st.markdown(
    "────────────────────────────────────────────"
)


# ============================================================
# TABS
# ============================================================

if not wifi.empty:

    tab_overview, tab_map, tab_advisor, tab_analysis, tab_raw = st.tabs(
        [
            "🏠 Overview" if language == "English" else "🏠 ภาพรวม",
            t["map"],
            "🤖 Wi-Fi Advisor",
            t["analysis"],
            t["raw"]
        ]
    )

    # ========================================================
    # OVERVIEW TAB
    # ========================================================

    with tab_overview:
        st.subheader(
            f"🏠 {'ภาพรวมห้อง' if language == 'ไทย' else 'Room Overview'} {display_room}"
        )

        if best_wifi is not None:
            oc1, oc2, oc3, oc4 = st.columns(4)
            oc1.metric("📶 Recommended Wi-Fi" if language == "English" else "📶 Wi-Fi แนะนำ",
                       best_wifi["SSID"])
            oc2.metric("📈 Average RSSI" if language == "English" else "📈 RSSI เฉลี่ย",
                       f"{best_wifi['Average RSSI']:.1f} dBm")
            oc3.metric("🟢 Good Signal" if language == "English" else "🟢 จุดวัดสัญญาณดี",
                       f"{best_wifi['Good Signal (%)']:.1f}%")
            oc4.metric("⭐ Advisor Score" if language == "English" else "⭐ คะแนนแนะนำ",
                       f"{best_wifi['Score']:.0f}/100")

        st.markdown(
            "### 📊 Wi-Fi Comparison"
            if language == "English"
            else "### 📊 เปรียบเทียบ Wi-Fi ในห้องนี้"
        )

        if not wifi_recommendation.empty:
            overview_table = wifi_recommendation[
                [
                    "SSID",
                    "Average RSSI",
                    "Weakest RSSI",
                    "Good Signal (%)",
                    "Weak Signal (%)",
                    "Score",
                    "Quality"
                ]
            ].copy()

            for col in [
                "Average RSSI",
                "Weakest RSSI",
                "Good Signal (%)",
                "Weak Signal (%)",
                "Score"
            ]:
                overview_table[col] = overview_table[col].round(1)

            st.dataframe(
                overview_table,
                use_container_width=True,
                hide_index=True
            )

        st.caption(
            "คำแนะนำคำนวณจากข้อมูล Survey ของห้องที่เลือก โดยพิจารณา RSSI เฉลี่ย "
            "ความสม่ำเสมอ และสัดส่วนจุดวัดที่สัญญาณดี/อ่อน"
            if language == "ไทย"
            else
            "Recommendations use the selected room's survey data, considering average RSSI, "
            "stability, and the share of good/weak measurements."
        )

    # ========================================================
    # WI-FI ADVISOR TAB
    # ========================================================

    with tab_advisor:
        st.subheader("🤖 Wi-Fi Advisor")
        st.write(
            "เลือกจุดที่กำลังนั่ง ระบบจะแนะนำ Wi-Fi จากค่าที่วัดได้ ณ จุดนั้น"
            if language == "ไทย"
            else
            "Select where you are sitting. The advisor recommends Wi-Fi from measurements at that point."
        )

        advisor_points = sorted(
            wifi["Point"].dropna().astype(str).unique().tolist()
        )

        if advisor_points:
            selected_point = st.selectbox(
                "📍 เลือกจุดที่กำลังนั่ง"
                if language == "ไทย"
                else "📍 Select your survey point",
                advisor_points,
                key=f"advisor_point_{selected_room}"
            )

            point_best, point_table = recommend_wifi_at_point(
                wifi,
                selected_point
            )

            if point_best is not None:
                point_ssid = str(point_best["SSID"])
                point_rssi = float(point_best["RSSI"])
                status, description = signal_quality(point_rssi, language)

                st.markdown(
                    f"""
                    <div class="recommend-card">
                        <div class="recommend-label">📍 {display_room} • {selected_point}</div>
                        <div class="recommend-wifi">📶 {point_ssid}</div>
                        <div class="recommend-rssi">{point_rssi:.1f} dBm • {status}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.info(description)

                st.markdown(
                    f"### 📊 {'Wi-Fi ที่ตรวจพบ ณ จุด' if language == 'ไทย' else 'Wi-Fi detected at'} {selected_point}"
                )
                show_point_table = point_table.copy()
                show_point_table["RSSI"] = show_point_table["RSSI"].round(1)
                st.dataframe(
                    show_point_table,
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info(
                "ไม่พบจุด Survey"
                if language == "ไทย"
                else "No survey points found."
            )

    # ========================================================
    # 3D HEATMAP
    # ========================================================

    with tab_map:

        if selected_room == "Room A":
            st.subheader("🏠 3D Wi-Fi RSSI Heatmap — Room A (A1–A4)")

            room_a_fig = create_room_a_combined_heatmap(
                opacity=opacity,
                show_ap=show_ap,
                show_points=show_points,
                show_furniture=show_furniture
            )

            room_a_fig = force_white_3d(room_a_fig)
            st.plotly_chart(room_a_fig,
                use_container_width=True,
                key="room_a_complete_heatmap"
            , theme=None)

            st.success(
                f"โหลดข้อมูล Room A แล้ว: {wifi['Point'].nunique()} จุดสำรวจ • "
                f"{wifi['SSID'].nunique()} SSID • {len(wifi)} records"
                if language == "ไทย"
                else
                f"Room A loaded: {wifi['Point'].nunique()} survey points • "
                f"{wifi['SSID'].nunique()} SSIDs • {len(wifi)} records"
            )

        else:
            st.subheader(
                f"3D Wi-Fi RSSI Heatmap — {display_room}"
            )

            if selected_room == "Room C":
                fig = create_room_c_heatmap(
                    wifi=wifi,
                    opacity=opacity,
                    show_points=show_points,
                    show_furniture=show_furniture
                )
            elif selected_room == "Room B":
                fig = create_room_b_heatmap(
                    wifi=wifi,
                    opacity=opacity,
                    show_ap=show_ap,
                    show_points=show_points,
                    show_furniture=show_furniture
                )
            else:
                fig = create_3d_heatmap(
                    wifi=wifi,
                    room_name=selected_room,
                    room_x=ROOM_X,
                    room_y=ROOM_Y,
                    opacity=opacity,
                    show_ap=show_ap,
                    show_points=show_points,
                    show_furniture=show_furniture
                )

            fig = force_white_3d(fig)
            st.plotly_chart(fig,
                use_container_width=True
            , theme=None)

        # ----------------------------------------------------
        # Room Information
        # ----------------------------------------------------

        info_col1, info_col2, info_col3 = st.columns(3)

        info_col1.info(
            f"📐 {t['room_size']}\n\n"
            f"{ROOM_X:.2f} × {ROOM_Y:.2f} m"
        )

        info_col2.info(
            f"📍 {t['survey_points']}\n\n"
            f"{wifi['Point'].nunique()}"
        )

        info_col3.info(
            f"📡 Access Points\n\n"
            f"{wifi['BSSID'].nunique()} AP"
        )

    # ========================================================
    # DATA ANALYSIS
    # ========================================================

    with tab_analysis:

        st.subheader(
            "การวิเคราะห์ข้อมูลเชิงลึก (Deep Analysis)"
        )

        # ----------------------------------------------------
        # Strongest AP
        # ----------------------------------------------------

        strongest_idx = (
            wifi["RSSI"]
            .idxmax()
        )

        strongest = (
            wifi.loc[
                strongest_idx
            ]
        )

        channel_value = (
            strongest["Channel"]
            if "Channel" in wifi.columns
            else "N/A"
        )

        st.success(
            f"""
🏆 **Strongest Access Point:** {strongest["SSID"]}

**BSSID:** {strongest["BSSID"]}

**RSSI:** {strongest["RSSI"]} dBm

**พบที่จุด:** {strongest["Point"]}

**ตำแหน่ง:** 
({strongest["X"]:.2f}, {strongest["Y"]:.2f}) m

**Channel:** {channel_value}
"""
        )

        # ----------------------------------------------------
        # Weakest AP
        # ----------------------------------------------------

        weakest_idx = (
            wifi["RSSI"]
            .idxmin()
        )

        weakest = (
            wifi.loc[
                weakest_idx
            ]
        )

        weakest_channel = (
            weakest["Channel"]
            if "Channel" in wifi.columns
            else "N/A"
        )

        st.warning(
            f"""
📉 **Weakest Access Point:** {weakest["SSID"]}

**BSSID:** {weakest["BSSID"]}

**RSSI:** {weakest["RSSI"]} dBm

**พบที่จุด:** {weakest["Point"]}

**ตำแหน่ง:** 
({weakest["X"]:.2f}, {weakest["Y"]:.2f}) m

**Channel:** {weakest_channel}
"""
        )

        # ====================================================
        # TWO COLUMNS
        # ====================================================

        col_a, col_b = st.columns(2)

        # ----------------------------------------------------
        # AP COUNT
        # ----------------------------------------------------

        with col_a:

            st.markdown(
                "**📍 จำนวน Access Point ที่พบในแต่ละจุด**"
            )

            ap_counts = (
                wifi
                .groupby("Point")["BSSID"]
                .nunique()
                .reset_index()
            )

            ap_counts.columns = [
                "Point",
                "AP Count"
            ]

            fig_ap = px.bar(

                ap_counts,

                x="Point",

                y="AP Count",

                text="AP Count",

                color="AP Count",

                color_continuous_scale="Greens"
            )

            fig_ap.update_layout(
                xaxis_tickangle=-45,
                margin=dict(
                    l=0,
                    r=0,
                    t=30,
                    b=0
                )
            )

            st.plotly_chart(
                fig_ap,
                use_container_width=True
            )

        # ----------------------------------------------------
        # CHANNEL
        # ----------------------------------------------------

        with col_b:

            st.markdown(
                "**📡 การกระจายตัวของการใช้ Channel**"
            )

            if "Channel" in wifi.columns:

                channel_counts = (
                    wifi["Channel"]
                    .value_counts()
                    .reset_index()
                )

                channel_counts.columns = [
                    "Channel",
                    "Count"
                ]

                channel_counts[
                    "Channel"
                ] = channel_counts[
                    "Channel"
                ].astype(str)

                fig_ch = px.pie(

                    channel_counts,

                    names="Channel",

                    values="Count",

                    hole=0.4,

                    color_discrete_sequence=(
                        px.colors.qualitative.Pastel
                    )
                )

                fig_ch.update_traces(
                    textposition="inside",
                    textinfo="percent+label"
                )

                fig_ch.update_layout(
                    margin=dict(
                        l=0,
                        r=0,
                        t=30,
                        b=0
                    )
                )

                st.plotly_chart(
                    fig_ch,
                    use_container_width=True
                )

            else:

                st.info(
                    "ไม่พบข้อมูล Channel"
                )

        # ====================================================
        # RSSI DISTRIBUTION
        # ====================================================

        st.markdown(
            "**📶 การกระจายตัวของคุณภาพสัญญาณ (RSSI Distribution)**"
        )

        fig_rssi = px.histogram(

            wifi,

            x="RSSI",

            nbins=20,

            color="SSID",

            marginal="box",

            color_discrete_sequence=(
                px.colors.qualitative.Set1
            )
        )

        fig_rssi.update_layout(

            xaxis_title=(
                "ความแรงสัญญาณ RSSI (dBm)"
            ),

            yaxis_title=(
                "ความถี่ที่ตรวจพบ (จุด)"
            ),

            margin=dict(
                l=0,
                r=0,
                t=10,
                b=0
            )
        )

        st.plotly_chart(
            fig_rssi,
            use_container_width=True
        )

        # ====================================================
        # RSSI BY SSID
        # ====================================================

        st.markdown(
            "**📡 ค่า RSSI เฉลี่ยของแต่ละ SSID**"
        )

        rssi_by_ssid = (
            wifi
            .groupby("SSID")["RSSI"]
            .agg(
                [
                    "mean",
                    "min",
                    "max",
                    "count"
                ]
            )
            .reset_index()
        )

        rssi_by_ssid.columns = [
            "SSID",
            "Average RSSI",
            "Minimum RSSI",
            "Maximum RSSI",
            "Measurements"
        ]

        st.dataframe(
            rssi_by_ssid.round(1),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # RAW DATA
    # ========================================================

    with tab_raw:

        st.subheader(
            "📋 ข้อมูลการสำรวจดิบ (Raw Survey Data)"
        )

        st.dataframe(
            wifi,
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # Download CSV
        # ----------------------------------------------------

        csv_data = wifi.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(

            label="⬇️ ดาวน์โหลดข้อมูล CSV",

            data=csv_data,

            file_name=(
                f"{selected_room}_survey_data.csv"
            ),

            mime="text/csv"
        )

else:

    st.warning(
        "⚠️ ไม่พบข้อมูลจาก SSID ที่เลือก"
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    "────────────────────────────────────────────"
)

st.caption(
    f"Portable Wireless Site Survey and Network Analysis System | "
    f"{selected_room} | "
    f"{ROOM_X:.2f} × {ROOM_Y:.2f} m"
)