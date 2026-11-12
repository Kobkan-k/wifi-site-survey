import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata

# ============================================================
# GLOBAL CONFIGURATION
# ============================================================
RSSI_MIN = -90
RSSI_MAX = -30
COLORSCALE_NAME = "Jet"
TICK_VALS = [-90, -80, -70, -60, -50, -40, -30]

st.set_page_config(page_title="3D Wi-Fi Heatmap - Room B", layout="wide")

# ============================================================
# ROOM B 3D HEATMAP FUNCTION
# ============================================================
def create_room_b_heatmap(wifi, opacity=0.80, show_ap=True, show_points=True, show_furniture=True):
    # Room Configuration
    ROOM_X = 6.8
    ROOM_Y = 9.0
    WALL_HEIGHT = 3.0

    FONT_FAMILY = "Arial"
    POINT_FONT_SIZE = 14
    POINT_FONT_COLOR = "#4B5563"
    POINT_HEIGHT = 0.15
    TEXT_HEIGHT = 0.23

    AP_X = 3.4
    AP_Y = 4.5
    AP_HEIGHT = 4.0

    fig = go.Figure()

    d = wifi.dropna(subset=["X", "Y", "RSSI"]).copy()

    # 1. HEATMAP SURFACE
    if len(d) >= 3:
        heatmap_data = d.groupby(["X", "Y"])["RSSI"].max().reset_index()
        grid_x = np.linspace(0, ROOM_X, 180)
        grid_y = np.linspace(0, ROOM_Y, 240)
        GX, GY = np.meshgrid(grid_x, grid_y)
        
        try:
            GZ = griddata((heatmap_data["X"], heatmap_data["Y"]), heatmap_data["RSSI"], (GX, GY), method="cubic")
        except Exception:
            GZ = griddata((heatmap_data["X"], heatmap_data["Y"]), heatmap_data["RSSI"], (GX, GY), method="nearest")
            
        nearest = griddata((heatmap_data["X"], heatmap_data["Y"]), heatmap_data["RSSI"], (GX, GY), method="nearest")
        GZ = np.where(np.isnan(GZ), nearest, GZ)
        GZ = np.clip(GZ, RSSI_MIN, RSSI_MAX)

        fig.add_trace(go.Surface(
            x=GX,
            y=GY,
            z=np.full_like(GZ, 0.01),
            surfacecolor=GZ,
            colorscale=COLORSCALE_NAME,
            cmin=RSSI_MIN,
            cmax=RSSI_MAX,
            opacity=opacity,
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="RSSI (dBm)",
                    font=dict(family=FONT_FAMILY, size=13, color="#111827")
                ),
                tickfont=dict(family=FONT_FAMILY, size=11, color="#111827"),
                tickvals=TICK_VALS,
                x=1.02,
                len=0.75
            ),
            customdata=GZ,
            hovertemplate=(
                "X: %{x:.2f} m"
                "<br>Y: %{y:.2f} m"
                "<br>RSSI: %{customdata:.1f} dBm"
                "<extra></extra>"
            ),
            name="RSSI Heatmap"
        ))

    # 2. SURVEY POINTS & LABELS
    if show_points and not d.empty:
        pt_df = d.sort_values("RSSI", ascending=False).drop_duplicates(subset=["X", "Y"])
        
        # Point Markers
        fig.add_trace(go.Scatter3d(
            x=pt_df["X"],
            y=pt_df["Y"],
            z=np.full(len(pt_df), POINT_HEIGHT),
            mode="markers",
            marker=dict(
                size=5,
                color="#1F2937",
                symbol="circle",
                line=dict(color="#FFFFFF", width=1)
            ),
            customdata=np.column_stack((
                pt_df["Point"] if "Point" in pt_df else [""]*len(pt_df),
                pt_df["SSID"] if "SSID" in pt_df else [""]*len(pt_df),
                pt_df["BSSID"] if "BSSID" in pt_df else [""]*len(pt_df),
                pt_df["RSSI"],
                pt_df["Channel"] if "Channel" in pt_df else [""]*len(pt_df)
            )),
            hovertemplate=(
                "Point: %{customdata[0]}"
                "<br>X: %{x:.2f} m"
                "<br>Y: %{y:.2f} m"
                "<br>SSID: %{customdata[1]}"
                "<br>BSSID: %{customdata[2]}"
                "<br>RSSI: %{customdata[3]} dBm"
                "<br>Channel: %{customdata[4]}"
                "<extra></extra>"
            ),
            name="Survey Points"
        ))

        # Point Labels
        if "Point" in pt_df:
            fig.add_trace(go.Scatter3d(
                x=pt_df["X"],
                y=pt_df["Y"],
                z=np.full(len(pt_df), TEXT_HEIGHT),
                mode="text",
                text=pt_df["Point"],
                textposition="top center",
                textfont=dict(
                    family=FONT_FAMILY,
                    size=POINT_FONT_SIZE,
                    color=POINT_FONT_COLOR
                ),
                hoverinfo="skip",
                showlegend=False,
                name="Point Labels"
            ))

    # 3. ACCESS POINT
    if show_ap:
        fig.add_trace(go.Scatter3d(
            x=[AP_X],
            y=[AP_Y],
            z=[AP_HEIGHT],
            mode="markers+text",
            marker=dict(
                size=14,
                color="#FF2020",
                symbol="diamond",
                line=dict(color="#FFFFFF", width=2)
            ),
            text=["AP"],
            textposition="top center",
            textfont=dict(
                family=FONT_FAMILY,
                size=14,
                color="#4B5563"
            ),
            hovertemplate=(
                "Access Point"
                "<br>X: %{x:.2f} m"
                "<br>Y: %{y:.2f} m"
                "<br>Height: %{z:.2f} m"
                "<extra></extra>"
            ),
            name="Access Point"
        ))

        # Vertical AP reference line
        fig.add_trace(go.Scatter3d(
            x=[AP_X, AP_X],
            y=[AP_Y, AP_Y],
            z=[0, AP_HEIGHT],
            mode="lines",
            line=dict(
                color="#FF3030",
                width=4,
                dash="dash"
            ),
            hoverinfo="skip",
            showlegend=False
        ))

    # 4. WALLS AND DOORS
    def add_wall(x1, y1, x2, y2, height, z_bottom=0):
        fig.add_trace(go.Mesh3d(
            x=[x1, x2, x2, x1, x1, x2, x2, x1],
            y=[y1, y2, y2, y1, y1, y2, y2, y1],
            z=[z_bottom, z_bottom, z_bottom, z_bottom, height, height, height, height],
            i=[0, 0, 0, 4, 4, 4],
            j=[1, 2, 3, 5, 6, 7],
            k=[2, 3, 4, 6, 7, 5],
            color="#B0BEC5",
            opacity=0.6,
            hoverinfo="skip",
            showlegend=False
        ))

    add_wall(0, 0, ROOM_X, 0, WALL_HEIGHT)
    add_wall(0, 0, 0, ROOM_Y, WALL_HEIGHT)
    add_wall(ROOM_X, 0, ROOM_X, ROOM_Y, WALL_HEIGHT)

    DOOR_MID = 1.7
    DOOR_TOTAL_WIDTH = 1.98
    DOOR_X1 = DOOR_MID - DOOR_TOTAL_WIDTH / 2
    DOOR_X2 = DOOR_MID + DOOR_TOTAL_WIDTH / 2
    DOOR_HEIGHT = 2.05

    add_wall(0, ROOM_Y, DOOR_X1, ROOM_Y, WALL_HEIGHT)
    add_wall(DOOR_X2, ROOM_Y, ROOM_X, ROOM_Y, WALL_HEIGHT)
    add_wall(DOOR_X1, ROOM_Y, DOOR_X2, ROOM_Y, WALL_HEIGHT, z_bottom=DOOR_HEIGHT)

    # Door frames
    for door_x, line_width in [(DOOR_X1, 8), (DOOR_X2, 8), (DOOR_MID, 4)]:
        fig.add_trace(go.Scatter3d(
            x=[door_x, door_x],
            y=[ROOM_Y - 0.02, ROOM_Y - 0.02],
            z=[0, DOOR_HEIGHT],
            mode="lines",
            line=dict(color="#607D8B", width=line_width),
            hoverinfo="skip",
            showlegend=False
        ))

    # 5. FURNITURE
    def get_flipped_box(x_min_orig, x_max_orig, y_min_orig, y_max_orig):
        new_x1 = ROOM_X - x_min_orig
        new_x2 = ROOM_X - x_max_orig
        new_y1 = ROOM_Y - y_min_orig
        new_y2 = ROOM_Y - y_max_orig
        return min(new_x1, new_x2), max(new_x1, new_x2), min(new_y1, new_y2), max(new_y1, new_y2)

    def create_box_mesh(x_min, x_max, y_min, y_max, z_min, z_max, color, opacity, name):
        fig.add_trace(go.Mesh3d(
            x=[x_min, x_max, x_max, x_min, x_min, x_max, x_max, x_min],
            y=[y_min, y_min, y_max, y_max, y_min, y_min, y_max, y_max],
            z=[z_min, z_min, z_min, z_min, z_max, z_max, z_max, z_max],
            i=[7, 0, 0, 0, 4, 4, 2, 6, 4, 0, 3, 7],
            j=[3, 4, 1, 2, 5, 6, 3, 7, 5, 1, 2, 6],
            k=[0, 7, 2, 3, 6, 7, 7, 4, 1, 5, 6, 5],
            color=color,
            opacity=opacity,
            name=name,
            hoverinfo="name",
            showlegend=False
        ))

    def add_table_realistic(x_min, x_max, y_min, y_max, h=0.80, top_color="#D7CCC8", leg_color="#795548", name="Table"):
        top_thickness = 0.05
        leg_size = 0.06
        create_box_mesh(x_min, x_max, y_min, y_max, h - top_thickness, h, top_color, 1.0, f"{name} (Top)")
        leg_positions = [
            (x_min, x_min + leg_size, y_min, y_min + leg_size),
            (x_max - leg_size, x_max, y_min, y_min + leg_size),
            (x_max - leg_size, x_max, y_max - leg_size, y_max),
            (x_min, x_min + leg_size, y_max - leg_size, y_max)
        ]
        for lx1, lx2, ly1, ly2 in leg_positions:
            create_box_mesh(lx1, lx2, ly1, ly2, 0, h - top_thickness, leg_color, 1.0, f"{name} (Leg)")

    if show_furniture:
        # Cabinets
        y1_t, y2_t = get_flipped_box(0, 0, 7.50, 8.44)[2:]
        create_box_mesh(0.0, 0.78, y1_t, y2_t, 0, 1.85, "#546E7A", 0.9, "Cabinet 1")

        y1_b, y2_b = get_flipped_box(0, 0, 0.50, 1.44)[2:]
        create_box_mesh(0.0, 0.78, y1_b, y2_b, 0, 1.85, "#546E7A", 0.9, "Cabinet 10")

        # Tables 11-16
        left_tables = [11, 12, 13, 14, 15, 16]
        left_tables_coords = [(7.00, 7.78), (6.20, 6.98), (4.40, 5.18), (3.60, 4.38), (1.80, 2.58), (1.00, 1.78)]
        for item_id, (y_min, y_max) in zip(left_tables, left_tables_coords):
            _, _, y1, y2 = get_flipped_box(0.0, 0.0, y_min, y_max)
            add_table_realistic(ROOM_X - 1.84, ROOM_X, y1, y2, h=0.80, top_color="#D7CCC8", name=f"Table {item_id}")

        # Tables 2-9
        right_tables_grouped = [
            (2, 0.00, 1.84, 5.40, 6.18), (4, 1.84, 3.68, 5.40, 6.18),
            (3, 0.00, 1.84, 4.60, 5.38), (5, 1.84, 3.68, 4.60, 5.38),
            (6, 0.00, 1.84, 2.60, 3.38), (8, 1.84, 3.68, 2.60, 3.38),
            (7, 0.00, 1.84, 1.80, 2.58), (9, 1.84, 3.68, 1.80, 2.58)
        ]
        for item_id, x_min_dir, x_max_dir, y_min_orig, y_max_orig in right_tables_grouped:
            _, _, y1, y2 = get_flipped_box(0, 0, y_min_orig, y_max_orig)
            add_table_realistic(x_min_dir, x_max_dir, y1, y2, h=0.80, top_color="#D7CCC8", name=f"Table {item_id}")

        # Object 17
        x1, x2, y1, y2 = get_flipped_box(2.10, 2.88, 0.0, 0.78)
        create_box_mesh(x1, x2, y1, y2, 0, 0.80, "#90A4AE", 0.88, "Object 17")

    # 6. RENDER LAYOUT
    fig.update_layout(
        title=dict(
            text="3D Wi-Fi RSSI Heatmap | KMITL Co-Working Space (Room B)",
            x=0.5,
            font=dict(family=FONT_FAMILY, size=22, color="#111827")
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family=FONT_FAMILY, color="#111827"),
        scene=dict(
            bgcolor="#F8F9FA",
            xaxis=dict(title="X (m)", range=[-0.5, ROOM_X + 0.7], gridcolor="#E0E0E0", zerolinecolor="#BDBDBD", tickfont=dict(color="#333333")),
            yaxis=dict(title="Y (m)", range=[-0.7, ROOM_Y + 0.5], gridcolor="#E0E0E0", zerolinecolor="#BDBDBD", tickfont=dict(color="#333333")),
            zaxis=dict(title="Height (m)", range=[0, 4.5], gridcolor="#E0E0E0", zerolinecolor="#BDBDBD", tickfont=dict(color="#333333")),
            aspectmode="manual",
            aspectratio=dict(x=6.8, y=9.0, z=3.5),
            camera=dict(eye=dict(x=1.35, y=1.35, z=0.9))
        ),
        height=850,
        margin=dict(l=0, r=0, t=70, b=0),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#E0E0E0",
            borderwidth=1,
            font=dict(color="#333333")
        )
    )

    return fig

# ============================================================
# STREAMLIT UI & MAIN EXECUTION
# ============================================================
st.title("📡 Wi-Fi 3D Heatmap Viewer (Room B)")
st.write("อัปโหลดไฟล์ข้อมูล Wi-Fi Survey เพื่อสร้าง Heatmap 3 มิติ")

# Controls in Sidebar
st.sidebar.header("การตั้งค่าการแสดงผล")
opacity = st.sidebar.slider("ความโปร่งใสของ Heatmap", min_value=0.1, max_value=1.0, value=0.8, step=0.1)
show_ap = st.sidebar.checkbox("แสดง Access Point", value=True)
show_points = st.sidebar.checkbox("แสดงจุด Survey", value=True)
show_furniture = st.sidebar.checkbox("แสดงเฟอร์นิเจอร์ (โต๊ะ/ตู้)", value=True)

uploaded_file = st.file_uploader("เลือกไฟล์ CSV ที่มีข้อมูลคอลัมน์ [Point, X, Y, SSID, BSSID, RSSI, Channel]", type=["csv"])

if uploaded_file is not None:
    try:
        # อ่านไฟล์ CSV
        df = pd.read_csv(uploaded_file)
        
        # ตรวจสอบคอลัมน์ที่จำเป็นอย่างน้อย X, Y, RSSI
        if all(col in df.columns for col in ["X", "Y", "RSSI"]):
            st.success("โหลดข้อมูลสำเร็จ!")
            
            # เรียกใช้ฟังก์ชันสร้างกราฟ
            fig = create_room_b_heatmap(
                wifi=df, 
                opacity=opacity, 
                show_ap=show_ap, 
                show_points=show_points, 
                show_furniture=show_furniture
            )
            
            # แสดงผลกราฟ
            st.plotly_chart(fig, use_container_width=True)
            
            # แสดงข้อมูลดิบแบบย่อ
            with st.expander("ดูข้อมูลดิบที่อัปโหลด"):
                st.dataframe(df)
        else:
            st.error("ไม่พบคอลัมน์ที่จำเป็น: กรุณาตรวจสอบให้แน่ใจว่าไฟล์ CSV มีคอลัมน์ X, Y, และ RSSI")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {e}")
else:
    st.info("กรุณาอัปโหลดไฟล์ CSV เพื่อแสดงผล 3D Heatmap")