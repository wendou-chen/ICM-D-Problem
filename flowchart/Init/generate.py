import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# 设置绘图风格
plt.figure(figsize=(14, 9), dpi=100)
ax = plt.gca()
ax.set_aspect('equal')
ax.axis('off')  # 关闭坐标轴
ax.set_facecolor('white')

# --- 参数定义 (示意性单位) ---
R_EARTH = 10
R_GEO = 25
R_APEX = 65  # 对应 100,000 km
D_MOON = 130 # 地月距离 (为了视觉效果进行了压缩)
R_MOON = 4

# --- 1. 绘制天体 (Celestial Bodies) ---

# 地球 (Earth)
earth = patches.Circle((0, 0), R_EARTH, color='#4B89DC', alpha=0.9, zorder=10)
ax.add_patch(earth)
# 地球上的陆地示意 (简单的绿色斑块)
land = patches.Circle((0, 0), R_EARTH*0.8, color='#66BB6A', alpha=0.6, zorder=11)
ax.add_patch(land)
plt.text(0, -R_EARTH-3, "Earth", ha='center', fontsize=12, fontweight='bold')

# 赤道线 (Equator Line)
theta = np.linspace(0, 2*np.pi, 100)
ax.plot(R_EARTH * np.cos(theta), R_EARTH * 0.1 * np.sin(theta), color='white', linewidth=0.5, zorder=12)

# 月球 (Moon)
moon = patches.Circle((D_MOON, 0), R_MOON, color='#C0C0C0', zorder=10)
ax.add_patch(moon)
# 月球陨石坑示意
crater1 = patches.Circle((D_MOON-1, 1), 1, color='#A0A0A0', zorder=11)
crater2 = patches.Circle((D_MOON+1.5, -0.5), 0.8, color='#A0A0A0', zorder=11)
ax.add_patch(crater1)
ax.add_patch(crater2)
plt.text(D_MOON, -R_MOON-3, "Moon\n(Colony)", ha='center', fontsize=12, fontweight='bold')

# GEO 轨道 (Geosynchronous Orbit)
geo_orbit = patches.Circle((0, 0), R_GEO, fill=False, edgecolor='#FF9800', linestyle='--', linewidth=1, alpha=0.7)
ax.add_patch(geo_orbit)
plt.text(0, R_GEO+2, "GEO Orbit\n(35,786 km)", ha='center', fontsize=9, color='#E65100')

# --- 2. 绘制基础设施: Galactic Harbours (Infrastructure Systems) ---

def draw_harbour(angle_deg, label):
    # 角度转弧度
    rad = np.radians(angle_deg)
    
    # Apex (顶点) 坐标
    apex_x = R_APEX * np.cos(rad)
    apex_y = R_APEX * np.sin(rad)
    
    # Base (地球端口) 坐标 - V型底部的两个点
    # 在地球表面，中心角度左右各偏移一点
    base_offset = np.radians(3) 
    base1_x = R_EARTH * np.cos(rad - base_offset)
    base1_y = R_EARTH * np.sin(rad - base_offset)
    base2_x = R_EARTH * np.cos(rad + base_offset)
    base2_y = R_EARTH * np.sin(rad + base_offset)
    
    # 绘制系缆 (Tethers - V Shape)
    plt.plot([base1_x, apex_x], [base1_y, apex_y], color='#333333', linewidth=1.5, zorder=5)
    plt.plot([base2_x, apex_x], [base2_y, apex_y], color='#333333', linewidth=1.5, zorder=5)
    
    # 绘制 Apex Anchor
    apex_circle = patches.Circle((apex_x, apex_y), 1.5, color='black', zorder=6)
    ax.add_patch(apex_circle)
    
    # 绘制 Earth Port
    port_circle = patches.Circle((R_EARTH * np.cos(rad), R_EARTH * np.sin(rad)), 1, color='red', zorder=13)
    ax.add_patch(port_circle)
    
    # 标签
    plt.text(apex_x, apex_y+3, label, ha='center', fontsize=8, rotation=angle_deg)
    plt.text(apex_x, apex_y+1.5, "Apex Anchor", ha='center', fontsize=6, rotation=angle_deg, color='gray')

# 绘制三个港口 (items in prompt)
# 稍微调整角度以便在图中错开显示
draw_harbour(15, "Galactic Harbour 1")
draw_harbour(40, "Galactic Harbour 3")
# Harbour 2 作为主要路径绘制在中间
draw_harbour(27.5, "Galactic Harbour 2") 

# --- 3. 绘制运输路线 (Transport Routes) ---

# --- Route 1: Hybrid Elevator/Rocket ---
# Step 1: Elevator Segment
h2_angle = 27.5
rad_h2 = np.radians(h2_angle)
apex_x = R_APEX * np.cos(rad_h2)
apex_y = R_APEX * np.sin(rad_h2)

# 在系缆上画一个向上的箭头
mid_x = (R_EARTH + (R_APEX - R_EARTH)*0.6) * np.cos(rad_h2)
mid_y = (R_EARTH + (R_APEX - R_EARTH)*0.6) * np.sin(rad_h2)
plt.arrow(mid_x, mid_y, np.cos(rad_h2)*2, np.sin(rad_h2)*2, 
          head_width=2, color='#2E7D32', zorder=20)
plt.text(mid_x-5, mid_y+2, "Route 1: Step 1\nElevator Ascent", color='#2E7D32', fontsize=9, fontweight='bold')

# Step 2: Rocket Transfer (Apex -> Moon)
# 绘制虚线曲线
path_x = np.linspace(apex_x, D_MOON, 50)
# 简单的贝塞尔曲线模拟
control_x = (apex_x + D_MOON) / 2
control_y = apex_y + 10 # 向上弯曲
path_t = np.linspace(0, 1, 50)
curve_x = (1-path_t)**2 * apex_x + 2*(1-path_t)*path_t * control_x + path_t**2 * D_MOON
curve_y = (1-path_t)**2 * apex_y + 2*(1-path_t)*path_t * control_y + path_t**2 * 0

plt.plot(curve_x, curve_y, color='#2E7D32', linestyle='--', linewidth=2, zorder=4)
# 箭头
mid_curve_idx = 25
plt.arrow(curve_x[mid_curve_idx], curve_y[mid_curve_idx], 
          curve_x[mid_curve_idx+1]-curve_x[mid_curve_idx], 
          curve_y[mid_curve_idx+1]-curve_y[mid_curve_idx],
          head_width=2, color='#2E7D32', zorder=20)
plt.text(control_x, control_y+2, "Route 1: Step 2\nApex Transfer", color='#2E7D32', fontsize=9, ha='center')


# --- Route 2: Direct Surface Launch ---
# Earth Launch Site (与港口分开)
launch_angle = -30
rad_launch = np.radians(launch_angle)
ls_x = R_EARTH * np.cos(rad_launch)
ls_y = R_EARTH * np.sin(rad_launch)

# 标记发射场
plt.plot(ls_x, ls_y, 'X', color='red', markersize=8, zorder=15)
plt.text(ls_x-2, ls_y-5, "Earth\nLaunch Site", ha='center', fontsize=8, color='red')

# 绘制直接轨道 (Direct Rocket)
# 大弧线
control_x_d = (ls_x + D_MOON) / 2
control_y_d = -40 # 向下弯曲
path_t = np.linspace(0, 1, 50)
curve_d_x = (1-path_t)**2 * ls_x + 2*(1-path_t)*path_t * control_x_d + path_t**2 * D_MOON
curve_d_y = (1-path_t)**2 * ls_y + 2*(1-path_t)*path_t * control_y_d + path_t**2 * 0

plt.plot(curve_d_x, curve_d_y, color='#D32F2F', linestyle=':', linewidth=2, zorder=4)
# 箭头
mid_d_idx = 25
plt.arrow(curve_d_x[mid_d_idx], curve_d_y[mid_d_idx], 
          curve_d_x[mid_d_idx+1]-curve_d_x[mid_d_idx], 
          curve_d_y[mid_d_idx+1]-curve_d_y[mid_d_idx],
          head_width=2, color='#D32F2F', zorder=20)
plt.text(control_x_d, control_y_d-5, "Route 2: Direct Launch", color='#D32F2F', fontsize=9, ha='center')

# --- 4. 视觉元素和标注 (Visual Elements & Technical Specs) ---

# 地月距离标注线 (带断裂符号)
line_y = -50
plt.plot([0, D_MOON], [line_y, line_y], 'k-', linewidth=1)
# 端点
plt.plot([0, 0], [line_y-1, line_y+1], 'k-', linewidth=1)
plt.plot([D_MOON, D_MOON], [line_y-1, line_y+1], 'k-', linewidth=1)
# 断裂符号 (Axis break symbol //)
break_x = D_MOON * 0.7
plt.text(break_x, line_y, "//", ha='center', va='center', fontsize=14, backgroundcolor='white')
plt.text(D_MOON/2, line_y+2, "Distance ~ 384,400 km", ha='center', fontsize=10)

# 标题
plt.title("EARTH-MOON TRANSPORT INFRASTRUCTURE & ROUTES", fontsize=16, fontweight='bold', pad=20)

# 图例 (手动绘制)
legend_x = -50
legend_y = 50
plt.text(legend_x, legend_y, "LEGEND", fontweight='bold')
# Item 1
plt.plot(legend_x, legend_y-5, 'o', color='red')
plt.text(legend_x+3, legend_y-6, "Earth Port / Launch Site", va='center')
# Item 2
plt.plot(legend_x, legend_y-10, 'o', color='black')
plt.text(legend_x+3, legend_y-11, "Apex Anchor", va='center')
# Item 3
plt.plot([legend_x-2, legend_x+2], [legend_y-15, legend_y-15], color='#2E7D32', linestyle='--')
plt.text(legend_x+3, legend_y-16, "Hybrid Route", va='center')
# Item 4
plt.plot([legend_x-2, legend_x+2], [legend_y-20, legend_y-20], color='#D32F2F', linestyle=':')
plt.text(legend_x+3, legend_y-21, "Direct Route", va='center')

# 调整视窗范围
plt.xlim(-60, 150)
plt.ylim(-60, 80)

plt.tight_layout()
plt.show()