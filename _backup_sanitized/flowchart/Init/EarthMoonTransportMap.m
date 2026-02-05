function EarthMoonTransportMap()
    % 创建绘图窗口
    figure('Name', 'Earth-Moon Transport Infrastructure', 'Color', 'w', 'Position', [100, 100, 1200, 800]);
    hold on;
    axis equal;
    axis off; % 关闭坐标轴
    
    % --- 参数定义 (示意性单位) ---
    R_EARTH = 10;
    R_GEO = 25;
    R_APEX = 65;  % 对应 100,000 km
    D_MOON = 130; % 地月距离 (压缩比例)
    R_MOON = 4;
    
    % 设置绘图范围
    xlim([-60, 150]);
    ylim([-60, 80]);

    % --- 1. 绘制天体 (Celestial Bodies) ---
    
    % 地球 (Earth) - 蓝色填充
    draw_circle(0, 0, R_EARTH, [0.29, 0.54, 0.86], 0.9); % #4B89DC
    % 地球陆地示意 (绿色)
    draw_circle(0, 0, R_EARTH*0.8, [0.4, 0.73, 0.42], 0.6); % #66BB6A
    text(0, -R_EARTH-5, 'Earth', 'HorizontalAlignment', 'center', 'FontSize', 12, 'FontWeight', 'bold');
    
    % 赤道线 (白色)
    theta = linspace(0, 2*pi, 100);
    plot(R_EARTH * cos(theta), R_EARTH * 0.1 * sin(theta), 'w-', 'LineWidth', 1);

    % GEO 轨道 (橙色虚线)
    plot(R_GEO * cos(theta), R_GEO * sin(theta), '--', 'Color', [1, 0.6, 0], 'LineWidth', 1);
    text(0, R_GEO+4, {'GEO Orbit', '(35,786 km)'}, 'HorizontalAlignment', 'center', 'FontSize', 8, 'Color', [0.9, 0.3, 0]);

    % 月球 (Moon) - 灰色填充
    draw_circle(D_MOON, 0, R_MOON, [0.75, 0.75, 0.75], 1.0); % #C0C0C0
    % 陨石坑
    draw_circle(D_MOON-1, 1, 1, [0.63, 0.63, 0.63], 1.0);
    draw_circle(D_MOON+1.5, -0.5, 0.8, [0.63, 0.63, 0.63], 1.0);
    text(D_MOON, -R_MOON-5, {'Moon', '(Colony)'}, 'HorizontalAlignment', 'center', 'FontSize', 12, 'FontWeight', 'bold');

    % --- 2. 绘制基础设施: Galactic Harbours ---
    
    % 绘制三个港口
    draw_harbour(15, 'Galactic Harbour 1', R_EARTH, R_APEX);
    draw_harbour(40, 'Galactic Harbour 3', R_EARTH, R_APEX);
    % Harbour 2 (中间，用于路径)
    [h2_apex_x, h2_apex_y] = draw_harbour(27.5, 'Galactic Harbour 2', R_EARTH, R_APEX);

    % --- 3. 绘制运输路线 (Transport Routes) ---
    
    % Route 1: Hybrid (Green)
    % Step 1: Elevator Ascent (Arrow on tether)
    angle_h2 = deg2rad(27.5);
    mid_r = R_EARTH + (R_APEX - R_EARTH) * 0.6;
    arrow_x = mid_r * cos(angle_h2);
    arrow_y = mid_r * sin(angle_h2);
    draw_arrow(arrow_x - 2*cos(angle_h2), arrow_y - 2*sin(angle_h2), ...
               arrow_x + 2*cos(angle_h2), arrow_y + 2*sin(angle_h2), [0.18, 0.49, 0.2], 2);
    text(arrow_x-8, arrow_y+2, {'Route 1: Step 1', 'Elevator Ascent'}, 'Color', [0.18, 0.49, 0.2], 'FontSize', 9, 'FontWeight', 'bold');

    % Step 2: Rocket Transfer (Apex -> Moon) - Bezier Curve
    t = linspace(0, 1, 50);
    p0 = [h2_apex_x, h2_apex_y];
    p2 = [D_MOON, 0];
    p1 = [(h2_apex_x + D_MOON)/2, h2_apex_y + 15]; % Control point (upward curve)
    
    curve_x = (1-t).^2 * p0(1) + 2*(1-t).*t * p1(1) + t.^2 * p2(1);
    curve_y = (1-t).^2 * p0(2) + 2*(1-t).*t * p1(2) + t.^2 * p2(2);
    
    plot(curve_x, curve_y, '--', 'Color', [0.18, 0.49, 0.2], 'LineWidth', 2);
    % Mid-path arrow
    mid_idx = 25;
    draw_arrow(curve_x(mid_idx), curve_y(mid_idx), curve_x(mid_idx+1), curve_y(mid_idx+1), [0.18, 0.49, 0.2], 2);
    text(p1(1), p1(2)+3, {'Route 1: Step 2', 'Apex Transfer'}, 'Color', [0.18, 0.49, 0.2], 'HorizontalAlignment', 'center', 'FontSize', 9);

    % Route 2: Direct Launch (Red)
    launch_angle = deg2rad(-30);
    ls_x = R_EARTH * cos(launch_angle);
    ls_y = R_EARTH * sin(launch_angle);
    
    % Mark Launch Site
    plot(ls_x, ls_y, 'rx', 'MarkerSize', 10, 'LineWidth', 2);
    text(ls_x-2, ls_y-8, {'Earth', 'Launch Site'}, 'Color', 'r', 'HorizontalAlignment', 'center', 'FontSize', 8);
    
    % Direct Path Curve
    p0_d = [ls_x, ls_y];
    p2_d = [D_MOON, 0];
    p1_d = [(ls_x + D_MOON)/2, -50]; % Control point (downward curve)
    
    curve_d_x = (1-t).^2 * p0_d(1) + 2*(1-t).*t * p1_d(1) + t.^2 * p2_d(1);
    curve_d_y = (1-t).^2 * p0_d(2) + 2*(1-t).*t * p1_d(2) + t.^2 * p2_d(2);
    
    plot(curve_d_x, curve_d_y, ':', 'Color', [0.83, 0.18, 0.18], 'LineWidth', 2);
    % Arrow
    draw_arrow(curve_d_x(mid_idx), curve_d_y(mid_idx), curve_d_x(mid_idx+1), curve_d_y(mid_idx+1), [0.83, 0.18, 0.18], 2);
    text(p1_d(1), p1_d(2)-5, {'Route 2: Direct Launch'}, 'Color', [0.83, 0.18, 0.18], 'HorizontalAlignment', 'center', 'FontSize', 9);

    % --- 4. 视觉元素 (Legend & Annotations) ---
    
    % Distance Break Line
    line_y = -50;
    plot([0, D_MOON], [line_y, line_y], 'k-', 'LineWidth', 1);
    plot([0, 0], [line_y-1, line_y+1], 'k-', 'LineWidth', 1);
    plot([D_MOON, D_MOON], [line_y-1, line_y+1], 'k-', 'LineWidth', 1);
    
    % Break Symbol (//)
    text(D_MOON*0.7, line_y, '//', 'HorizontalAlignment', 'center', 'BackgroundColor', 'w', 'FontSize', 14);
    text(D_MOON/2, line_y+3, 'Distance ~ 384,400 km', 'HorizontalAlignment', 'center', 'FontSize', 10);
    
    % Title
    title('EARTH-MOON TRANSPORT INFRASTRUCTURE & ROUTES', 'FontSize', 16, 'FontWeight', 'bold');

    % Legend (Manual)
    lx = -55; ly = 60;
    text(lx, ly, 'LEGEND', 'FontWeight', 'bold');
    
    plot(lx, ly-5, 'ro', 'MarkerFaceColor', 'r', 'MarkerSize', 6);
    text(lx+3, ly-5, 'Earth Port / Launch Site');
    
    plot(lx, ly-10, 'ko', 'MarkerFaceColor', 'k', 'MarkerSize', 6);
    text(lx+3, ly-10, 'Apex Anchor');
    
    plot([lx-2, lx+2], [ly-15, ly-15], '--', 'Color', [0.18, 0.49, 0.2], 'LineWidth', 2);
    text(lx+3, ly-15, 'Hybrid Route');
    
    plot([lx-2, lx+2], [ly-20, ly-20], ':', 'Color', [0.83, 0.18, 0.18], 'LineWidth', 2);
    text(lx+3, ly-20, 'Direct Route');

    hold off;
end

% --- 辅助函数 ---

function draw_circle(x, y, r, color, alpha_val)
    % 绘制填充圆
    theta = linspace(0, 2*pi, 100);
    xc = x + r*cos(theta);
    yc = y + r*sin(theta);
    fill(xc, yc, color, 'EdgeColor', 'none', 'FaceAlpha', alpha_val);
end

function [apex_x, apex_y] = draw_harbour(angle_deg, label_txt, R_EARTH, R_APEX)
    % 绘制单个港口 (V型系缆)
    rad = deg2rad(angle_deg);
    
    % Apex 坐标
    apex_x = R_APEX * cos(rad);
    apex_y = R_APEX * sin(rad);
    
    % Base 坐标 (V型底座)
    offset = deg2rad(3);
    base1_x = R_EARTH * cos(rad - offset);
    base1_y = R_EARTH * sin(rad - offset);
    base2_x = R_EARTH * cos(rad + offset);
    base2_y = R_EARTH * sin(rad + offset);
    
    % 画线
    plot([base1_x, apex_x], [base1_y, apex_y], 'Color', [0.2, 0.2, 0.2], 'LineWidth', 1.5);
    plot([base2_x, apex_x], [base2_y, apex_y], 'Color', [0.2, 0.2, 0.2], 'LineWidth', 1.5);
    
    % 画点
    plot(apex_x, apex_y, 'ko', 'MarkerFaceColor', 'k', 'MarkerSize', 4); % Apex
    plot(R_EARTH*cos(rad), R_EARTH*sin(rad), 'ro', 'MarkerFaceColor', 'r', 'MarkerSize', 4); % Port
    
    % 标签
    text(apex_x, apex_y+4, label_txt, 'HorizontalAlignment', 'center', 'FontSize', 8, 'Rotation', angle_deg);
    text(apex_x, apex_y+2, 'Apex Anchor', 'HorizontalAlignment', 'center', 'FontSize', 6, 'Rotation', angle_deg, 'Color', [0.5,0.5,0.5]);
end

function draw_arrow(x1, y1, x2, y2, color, scale)
    % 简单的向量箭头绘制
    % 计算方向
    u = x2 - x1;
    v = y2 - y1;
    % 归一化
    len = sqrt(u^2 + v^2);
    u = u/len; v = v/len;
    
    % 绘制箭头三角形
    head_len = 2 * scale;
    head_width = 1 * scale;
    
    % 箭头尖端
    tip_x = x2; 
    tip_y = y2;
    
    % 箭头后部中心
    back_x = tip_x - u * head_len;
    back_y = tip_y - v * head_len;
    
    % 箭头两侧
    left_x = back_x - v * head_width;
    left_y = back_y + u * head_width;
    right_x = back_x + v * head_width;
    right_y = back_y - u * head_width;
    
    patch([tip_x, left_x, right_x], [tip_y, left_y, right_y], color, 'EdgeColor', 'none');
end