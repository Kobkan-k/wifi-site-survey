import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from scipy.interpolate import griddata

def create_room_a_combined_heatmap(wifi=None, opacity=0.85, show_ap=True, show_points=True, show_furniture=True):
    """Room A updated from the supplied four-subroom 3D model."""
    ROOM_X, ROOM_Y = 7.20, 8.40
    WALL_HEIGHT, WALL_THICKNESS = 3.0, 0.12
    WALL_COLOR = '#93C5FD'
    WALL_OPACITY = 0.06
    FONT_FAMILY = 'Arial'
    POINT_FONT_SIZE, POINT_FONT_COLOR = 11, '#4B5563'
    ROOM_FONT_SIZE, ROOM_FONT_COLOR = 16, '#4B5563'
    POINT_HEIGHT, TEXT_HEIGHT = 0.15, 0.28
    
    # เปลี่ยน Colorscale เป็นแบบเดียวกับห้องใหญ่ (แดง -> เขียว)
    HEATMAP_COLORSCALE = [[0.000, "#ef4444"], [0.375, "#f97316"], [0.625, "#eab308"], [1.000, "#22c55e"]]
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

    # ฟิกซ์ค่าช่วงสี (Color limit) ให้เท่ากับห้องใหญ่เสมอ เพื่อความเป็นมาตรฐาน
    RSSI_MIN, RSSI_MAX = -90.0, -50.0

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

    # Heatmap Generator
    def add_room_heatmap(room_name, room, room_data):
        if not room_data or len(room_data.get('X', [])) == 0: return
        x_vals = np.asarray(room_data['X'], dtype=float)
        y_vals = np.asarray(room_data['Y'], dtype=float)
        rssi_vals = np.asarray(room_data['RSSI'], dtype=float)
        
        grid_x = np.linspace(room['x_min'], room['x_max'], HEATMAP_RESOLUTION)
        grid_y = np.linspace(room['y_min'], room['y_max'], HEATMAP_RESOLUTION)
        GX, GY = np.meshgrid(grid_x, grid_y)
        
        try:
            GZ = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method='cubic')
        except:
            GZ = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method='nearest')
        nearest = griddata((x_vals, y_vals), rssi_vals, (GX, GY), method='nearest')
        GZ = np.where(np.isnan(GZ), nearest, GZ)
        
        # ตัดค่า GZ ให้อยู่ในช่วง -90 ถึง -50 เหมือนห้องใหญ่
        GZ = np.clip(GZ, -90, -50)
        
        # ยก Z ขึ้นเป็น 0.20 ให้เห็นชัดเจน
        Z_PLANE = np.full_like(GZ, 0.20)

        fig.add_trace(go.Surface(
            x=GX, y=GY, z=Z_PLANE,
            surfacecolor=GZ, colorscale=HEATMAP_COLORSCALE,
            cmin=-90, cmax=-50, opacity=HEATMAP_OPACITY,
            showscale=(room_name == '1'), 
            colorbar=dict(
                title=dict(text="<b>RSSI</b><br>(dBm)", font=dict(color="#111827")), 
                tickvals=[-90, -73, -65, -50], 
                ticktext=["-90 (Weak)", "-73", "-65", "-50 (Strong)"], 
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

# ----------------- Streamlit UI -----------------
def main():
    st.set_page_config(layout="wide", page_title="3D Wi-Fi Heatmap")
    
    st.title("📡 3D Wi-Fi RSSI Heatmap | KMITL Co-Working Space")
    
    st.sidebar.header("🛠️ การแสดงผล (Display Options)")
    opacity = st.sidebar.slider("ความโปร่งใส Heatmap (Opacity)", 0.0, 1.0, 0.85)
    show_points = st.sidebar.checkbox("แสดงจุดสำรวจสัญญาณ (Survey Points)", True)
    show_furniture = st.sidebar.checkbox("แสดงเฟอร์นิเจอร์ (Furniture)", True)
    
    # วาดกราฟ
    fig = create_room_a_combined_heatmap(
        wifi=None, 
        opacity=opacity, 
        show_ap=False, 
        show_points=show_points, 
        show_furniture=show_furniture
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()