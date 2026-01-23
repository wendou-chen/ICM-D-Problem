import os
import pickle
import pandas as pd
import networkx as nx
import numpy as np
from scipy.spatial import cKDTree

class BaltimoreDataManager:
    """
    巴尔地摩交通项目数据管理器。
    负责加载原始数据并初始化交通网络图。
    """
    
    # 定义不同道路类型的默认速度（英里/小时）
    DEFAULT_SPEEDS = {
        'motorway': 65,      # 高速公路
        'trunk': 55,       # 干线公路
        'primary': 45,     # 一级公路
        'secondary': 35,   # 二级公路
        'tertiary': 30,    # 三级公路
        'residential': 25, # 住宅区道路
        'unclassified': 25,
        'service': 15,     # 服务型道路
        'bus_route': 20,   # 公交路线平均速度（含停站时间）
        'walking': 3       # 平均步行速度
    }

    def __init__(self, root_dir='.'):
        """
        初始化数据管理器。
        
        :param root_dir: 包含 data/ 和 src/ 目录的项目根目录
        """
        self.root_dir = root_dir
        # 根据脚本相对于根目录的运行位置调整路径
        # 假设数据存放在 data/ 目录下
        self.raw_data_dir = os.path.join(root_dir, 'data', 'raw')
        self.processed_data_dir = os.path.join(root_dir, 'data', 'processed')
        
        # 确保处理后的数据目录存在
        os.makedirs(self.processed_data_dir, exist_ok=True)
        
        # 初始化一个空的 MultiDiGraph
        # MultiDiGraph 允许在相同节点间存在多条边（例如同时存在驾车、公交和步行路径）
        self.G = nx.MultiDiGraph()
        
        # 数据框占位符
        self.nodes_df = None
        self.edges_df = None
        self.bus_stops_df = None
        self.kdtree = None # 用于空间检索

    @staticmethod
    def haversine_dist(lat1, lon1, lat2, lon2):
        """
        计算地球上两点之间的大圆距离（半正矢公式）。
        
        :param lat1: 点1的纬度
        :param lon1: 点1的经度
        :param lat2: 点2的纬度
        :param lon2: 点2的经度
        :return: 以米为单位的距离
        """
        # 将十进制度数转换为弧度 
        lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

        # 半正矢公式
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a)) 
        r = 6371000 # 地球半径（米）
        return c * r

    def load_raw_data(self):
        """
        加载经数据清洗后的 CSV 数据 (data/processed/*_clean.csv)。
        """
        # 使用 processed 目录下的清洗后数据
        nodes_path = os.path.join(self.processed_data_dir, 'nodes_clean.csv')
        edges_path = os.path.join(self.processed_data_dir, 'edges_clean.csv')
        bus_stops_path = os.path.join(self.processed_data_dir, 'bus_stops_clean.csv')

        print(f"正在加载清洗后的数据...")
        print(f"  Nodes: {nodes_path}")
        print(f"  Edges: {edges_path}")
        print(f"  Stops: {bus_stops_path}")

        try:
            # 加载节点数据 (使用 low_memory=False 消除混合类型警告)
            if os.path.exists(nodes_path):
                self.nodes_df = pd.read_csv(nodes_path, low_memory=False)
                # 删除缺少关键信息（如坐标）的行
                if 'y' in self.nodes_df.columns and 'x' in self.nodes_df.columns:
                    original_len = len(self.nodes_df)
                    self.nodes_df = self.nodes_df.dropna(subset=['y', 'x', 'osmid'])
                    if len(self.nodes_df) < original_len:
                        print(f"删除了 {original_len - len(self.nodes_df)} 个缺少坐标或ID的节点。")
                print(f"成功加载了 {len(self.nodes_df)} 个驾车节点。")
            else:
                print(f"警告: 未找到 {nodes_path}。")

            # 加载边数据 (使用 low_memory=False 消除混合类型警告)
            if os.path.exists(edges_path):
                self.edges_df = pd.read_csv(edges_path, low_memory=False)
                print(f"成功加载了 {len(self.edges_df)} 条驾车边。")
            else:
                print(f"警告: 未找到 {edges_path}。")

            # 加载公交站点数据
            if os.path.exists(bus_stops_path):
                self.bus_stops_df = pd.read_csv(bus_stops_path, low_memory=False)
                
                # 列名标准化：检测并统一坐标列名
                # 新数据使用 'X' (经度) 和 'Y' (纬度)，旧数据使用 'stop_lon' 和 'stop_lat'
                rename_map = {}
                if 'X' in self.bus_stops_df.columns and 'stop_lon' not in self.bus_stops_df.columns:
                    rename_map['X'] = 'stop_lon'
                if 'Y' in self.bus_stops_df.columns and 'stop_lat' not in self.bus_stops_df.columns:
                    rename_map['Y'] = 'stop_lat'
                if rename_map:
                    self.bus_stops_df = self.bus_stops_df.rename(columns=rename_map)
                    print(f"  已将列名 {list(rename_map.keys())} 重命名为 {list(rename_map.values())}")
                
                # 删除缺少关键信息的行
                self.bus_stops_df = self.bus_stops_df.dropna(subset=['stop_lat', 'stop_lon', 'stop_id'])
                print(f"成功加载了 {len(self.bus_stops_df)} 个公交站点。")
            else:
                print(f"警告: 未找到 {bus_stops_path}。")

        except Exception as e:
            print(f"加载数据时发生严重错误: {e}")
            raise

    def build_drive_layer(self):
        """
        构建交通网络的驾车层。
        将加载的驾车数据节点和边添加到 self.G 中。
        
        节点属性: pos=(经度, 纬度), type='intersection', layer='drive'
        边属性: weight=travel_time (分钟), distance=length_km, mode='drive', capacity
        """
        if self.nodes_df is None or self.edges_df is None:
            print("错误: 请先调用 load_raw_data() 加载原始数据")
            return
        
        print("正在构建驾车层...")
        
        # =====================
        # 1. 添加节点
        # =====================
        # 遍历节点数据框
        # 'osmid' 是唯一标识符，'x' 是经度，'y' 是纬度
        nodes_added = 0
        for _, row in self.nodes_df.iterrows():
            node_id = row['osmid']
            self.G.add_node(
                node_id,
                pos=(row['x'], row['y']),  # (经度, 纬度) 元组
                type='intersection',
                layer='drive'
            )
            nodes_added += 1
        
        print(f"  添加了 {nodes_added} 个驾车节点。")
        
        # =====================
        # 2. 添加边
        # =====================
        # 单位转换常数：
        # - CSV 中的长度单位为米
        # - DEFAULT_SPEEDS 中的速度单位为英里/小时 (mph)
        # - 我们需要旅行时间单位为分钟
        # 
        # 公式: 时间 (分钟) = 距离 (米) / 速度 (米/分钟)
        #        = 距离 (米) / (速度 (mph) * 1609.34 米/英里 / 60 分钟/小时)
        #        = 距离 (米) / (速度 * 26.82 米/分钟)
        #        = 距离 (米) * 60 / (速度 * 1609.34)
        
        MPH_TO_METERS_PER_MIN = 1609.34 / 60  # ≈ 26.82 米/分钟每 mph
        DEFAULT_CAPACITY = 2000  # 每小时车辆数（流量建模占位符）
        
        edges_added = 0
        stats_mode = {'drive': 0, 'walk': 0, 'other': 0}
        
        # Define walk-only highways
        WALK_HIGHWAYS = {'footway', 'path', 'pedestrian', 'steps', 'cycleway', 'bridleway', 'track'}
        
        for _, row in self.edges_df.iterrows():
            u = row['u']  # 起点节点
            v = row['v']  # 终点节点
            
            # 如果节点不在图中则跳过（边连接到了已删除的节点）
            if u not in self.G or v not in self.G:
                continue
            
            # 获取长度（米），如果缺失则默认为100米
            length_m = row.get('length', 100)
            if pd.isna(length_m):
                length_m = 100
            
            # 获取道路类型及对应速度
            highway_type = row.get('highway', 'residential')
            if pd.isna(highway_type):
                highway_type = 'residential'
            
            # 处理列表形式的道路类型（例如 "['primary', 'secondary']"）
            if isinstance(highway_type, str) and highway_type.startswith('['):
                # 获取列表字符串中的第一个类型
                highway_type = highway_type.strip("[]'\"").split(',')[0].strip("' ")
            
            # Determine Mode and Speed
            # 默认 fallback 到 residential 速度
            speed_mph = self.DEFAULT_SPEEDS.get(highway_type, self.DEFAULT_SPEEDS['residential'])
            mode = 'drive'
            
            if highway_type in WALK_HIGHWAYS:
                mode = 'walk'
                speed_mph = self.DEFAULT_SPEEDS['walking']
            
            # 计算旅行时间（分钟）
            # 时间 = 距离 / 速度
            speed_m_per_min = speed_mph * MPH_TO_METERS_PER_MIN
            if speed_m_per_min <= 0: speed_m_per_min = 1.0 # 避免除以零
            
            travel_time_min = length_m / speed_m_per_min
            
            # 将长度转换为千米作为距离属性
            length_km = length_m / 1000
            
            # 将边添加到 MultiDiGraph（有向图，允许平行边）
            self.G.add_edge(
                u, v,
                weight=travel_time_min,      # 路由的主要权重
                distance=length_km,          # 距离（千米）
                mode=mode,                   # 交通模式 (Corrected)
                capacity=DEFAULT_CAPACITY,   # 流量建模容量
                highway=highway_type,        # 道路分类
                cost=travel_time_min         # 广义代价 = 旅行时间（分钟）
            )
            edges_added += 1
            stats_mode[mode] = stats_mode.get(mode, 0) + 1
            
        print(f"  添加了 {edges_added} 条边。")
        print(f"  边模式统计: {stats_mode}")
        if stats_mode['walk'] == 0:
            print("  [WARNING] No walk edges detected! Check highway tags in source data.")
        print(f"  驾车/步行层构建完成。当前图包含 {self.G.number_of_nodes()} 个节点，{self.G.number_of_edges()} 条边。")

    def build_bus_layer_and_connect(self, transfer_penalty_min=5.0, transfer_penalty_by_type=None):
        """
        构建公交层并将其连接到驾车层（多模态融合）。
        
        该方法执行以下操作：
        1. 添加带有前缀 ID 的公交站点节点以避免 ID 冲突
        2. 基于道路节点坐标构建 KDTree，以便进行高效的最近邻搜索
        3. 在每个公交站点与其最近的道路节点之间创建双向换乘边
        
        :param transfer_penalty_min: 默认换乘时间惩罚（分钟），作为 fallback
        :param transfer_penalty_by_type: 按类型分档的惩罚字典，例如 {"road_to_bus": 7.0, "bus_to_road": 2.0}
                                        cost 将作为 generalized cost (等于分钟数)
        """
        if self.bus_stops_df is None:
            print("错误: 公交站点数据未加载。请先调用 load_raw_data()。")
            return
        
        if self.nodes_df is None or len(self.G.nodes()) == 0:
            print("错误: 必须先构建驾车层。请先调用 build_drive_layer()。")
            return
        
        print("正在构建公交层并连接到驾车层...")

        # 设置默认的分档惩罚
        if transfer_penalty_by_type is None:
            transfer_penalty_by_type = {"road_to_bus": 7.0, "bus_to_road": 2.0}
        
        # =====================
        # 1. 基于道路节点构建 KDTree
        # =====================
        # 提取道路节点坐标: (经度, 纬度) = (x, y)
        # 仅过滤驾车层节点
        road_node_ids = []
        road_node_coords = []
        
        for node_id, attrs in self.G.nodes(data=True):
            # 仅使用驾车层节点（排除重新运行时可能已添加的公交节点）
            if attrs.get('layer') == 'drive':
                pos = attrs.get('pos')
                if pos is not None:
                    road_node_ids.append(node_id)
                    road_node_coords.append(pos)  # (经度, 纬度)
        
        if len(road_node_coords) == 0:
            print("错误: 在图中未找到带有坐标的道路节点。")
            return
        
        # 使用 (经度, 纬度) 坐标构建 KDTree
        # 注意：KDTree 使用欧几里得距离，虽然是近似值但速度很快
        # 对于更大规模的精确计算，建议转换为投影坐标系
        road_coords_array = np.array(road_node_coords)
        self.kdtree = cKDTree(road_coords_array)
        
        print(f"  已基于 {len(road_node_ids)} 个道路节点构建 KDTree。")
        
        # =====================
        # 2. 添加公交站点节点
        # =====================
        bus_nodes_added = 0
        transfer_edges_added = 0
        
        for _, row in self.bus_stops_df.iterrows():
            # 获取公交站点信息
            original_stop_id = row.get('stop_id')
            if pd.isna(original_stop_id):
                continue
            
            # 关键：为公交站点 ID 添加前缀，避免与道路节点 ID (osmid) 冲突
            bus_node_id = f"bus_{original_stop_id}"
            
            # 获取坐标 - 检查多种可能的列名
            stop_lon = row.get('stop_lon')
            stop_lat = row.get('stop_lat')
            
            # 处理备选列名
            if pd.isna(stop_lon):
                stop_lon = row.get('longitude', row.get('x'))
            if pd.isna(stop_lat):
                stop_lat = row.get('latitude', row.get('y'))
            
            if pd.isna(stop_lon) or pd.isna(stop_lat):
                continue  # 跳过没有有效坐标的站点
            
            # 向图中添加公交站点节点
            self.G.add_node(
                bus_node_id,
                pos=(stop_lon, stop_lat),  # 统一使用 (经度, 纬度) 格式
                type='bus_stop',
                layer='bus',
                original_id=original_stop_id,
                name=row.get('stop_name', '')
            )
            bus_nodes_added += 1
            
            # =====================
            # 3. 创建连接到最近道路节点的换成边
            # =====================
            # 查询 KDTree 寻找最近的道路交叉口
            bus_coord = np.array([[stop_lon, stop_lat]])
            
            try:
                # k=1 寻找单个最近邻
                # 返回 (距离, 索引)
                dist, idx = self.kdtree.query(bus_coord, k=1)
                
                # 处理单个结果和数组结果的情况
                if hasattr(idx, '__len__'):
                    idx = idx[0]
                    dist = dist[0]
                
                nearest_road_node_id = road_node_ids[idx]
                
                # 创建双向换乘边
                
                # --- A. 道路 -> 公交 (步行至公交站 + 期望等候) ---
                penalty_r2b = transfer_penalty_by_type.get("road_to_bus", transfer_penalty_min)
                self.G.add_edge(
                    nearest_road_node_id,
                    bus_node_id,
                    weight=float(penalty_r2b),    # 时间惩罚（分钟）
                    distance=0.0,                 # 无额外距离成本
                    mode='transfer',
                    cost=float(penalty_r2b),      # 将 penalty 作为广义 cost
                    transfer_type='road_to_bus'
                )
                
                # --- B. 公交 -> 道路 (下车 + 出站/步行连接) ---
                penalty_b2r = transfer_penalty_by_type.get("bus_to_road", transfer_penalty_min)
                self.G.add_edge(
                    bus_node_id,
                    nearest_road_node_id,
                    weight=float(penalty_b2r),
                    distance=0.0,
                    mode='transfer',
                    cost=float(penalty_b2r),      # 将 penalty 作为广义 cost
                    transfer_type='bus_to_road'
                )
                
                transfer_edges_added += 2
                
            except Exception as e:
                # 即使单个点失败也不要使整个过程崩溃
                print(f"  警告: 无法连接公交站点 {bus_node_id} 到最近的道路节点: {e}")
                continue
        
        print(f"  已添加 {bus_nodes_added} 个公交站点节点。")
        print(f"  已添加 {transfer_edges_added} 条换乘边 (road <-> bus)。")
        print(f"  公交层构建完成。当前图包含 {self.G.number_of_nodes()} 个节点，{self.G.number_of_edges()} 条边。")

    def sanity_check_and_prune(self):
        """
        执行完整性检查并对图进行剪枝。
        
        提取最大的弱连通分量 (LWCC)，以确保所有节点在网络中都是可达的。
        孤立的“孤岛”会导致路由计算失败。
        
        对于有向图，我们使用弱连通（忽略边方向），因为我们关注物理连通性，而不仅是有向可达性。
        """
        if self.G.number_of_nodes() == 0:
            print("错误: 图为空，无法剪枝。")
            return
        
        print("正在进行完整性检查和剪枝...")
        
        original_nodes = self.G.number_of_nodes()
        original_edges = self.G.number_of_edges()
        
        # 获取所有弱连通分量
        # 返回节点集合列表
        wccs = list(nx.weakly_connected_components(self.G))
        
        if len(wccs) == 0:
            print("  错误: 未找到连通分量。")
            return
        
        # 寻找最大的连通分量
        largest_wcc = max(wccs, key=len)
        
        # 创建仅包含最大连通分量的子图
        self.G = self.G.subgraph(largest_wcc).copy()
        
        pruned_nodes = self.G.number_of_nodes()
        pruned_edges = self.G.number_of_edges()
        
        nodes_removed = original_nodes - pruned_nodes
        edges_removed = original_edges - pruned_edges
        
        print(f"  原始节点数: {original_nodes}, 剪枝后节点数: {pruned_nodes}")
        print(f"  原始边数: {original_edges}, 剪枝后边数: {pruned_edges}")
        print(f"  删除了 {nodes_removed} 个孤立节点和 {edges_removed} 条多余的边。")
        print(f"  共发现 {len(wccs)} 个弱连通分量，保留了最大的一个。")
        
        # 额外的完整性统计
        drive_nodes = sum(1 for _, d in self.G.nodes(data=True) if d.get('layer') == 'drive')
        bus_nodes = sum(1 for _, d in self.G.nodes(data=True) if d.get('layer') == 'bus')
        
        drive_edges = sum(1 for _, _, d in self.G.edges(data=True) if d.get('mode') == 'drive')
        transfer_edges = sum(1 for _, _, d in self.G.edges(data=True) if d.get('mode') == 'transfer')
        
        print(f"  最终组成: {drive_nodes} 个驾车节点, {bus_nodes} 个公交节点")
        print(f"  最终边数: {drive_edges} 条驾车边, {transfer_edges} 条换乘边")

    def finalize_cost(self, transfer_penalty_min=5.0, transfer_penalty_by_type=None):
        """
        补全所有边的 cost 字段，确保 100% 覆盖率。
        
        对于 drive 边：cost = weight（旅行时间，分钟）
        对于 transfer 边：cost = weight + penalty（根据 transfer_type 分档）
        
        :param transfer_penalty_min: 默认换乘惩罚（分钟），作为 fallback
        :param transfer_penalty_by_type: 按类型分档的惩罚字典
        """
        print("正在补全 cost 字段...")
        
        # 设置默认的分档惩罚
        if transfer_penalty_by_type is None:
            transfer_penalty_by_type = {"road_to_bus": 7.0, "bus_to_road": 2.0}
        
        # 统计变量
        cost_added = 0
        cost_existed = 0
        drive_costs = []
        transfer_costs = []
        
        # 遍历所有边并补全 cost
        for u, v, k, data in self.G.edges(keys=True, data=True):
            mode = data.get('mode', '')
            
            if 'cost' in data and data['cost'] is not None and data['cost'] > 0:
                # 已有有效 cost
                cost_existed += 1
                if mode == 'drive':
                    drive_costs.append(data['cost'])
                elif mode == 'transfer':
                    transfer_costs.append(data['cost'])
            else:
                # 需要补全 cost
                if mode == 'transfer':
                    # 换乘边：cost = weight + penalty
                    weight = float(data.get('weight', transfer_penalty_min))
                    transfer_type = data.get('transfer_type', '')
                    penalty = transfer_penalty_by_type.get(transfer_type, transfer_penalty_min)
                    cost = weight + penalty
                    self.G[u][v][k]['cost'] = cost
                    transfer_costs.append(cost)
                else:
                    # 非换乘边（drive 等）：cost = weight
                    weight = float(data.get('weight', 0.0))
                    cost = weight
                    self.G[u][v][k]['cost'] = cost
                    if mode == 'drive':
                        drive_costs.append(cost)
                cost_added += 1
        
        # 统计输出
        total_edges = self.G.number_of_edges()
        cost_coverage = sum(1 for _, _, _, d in self.G.edges(keys=True, data=True) if 'cost' in d and d['cost'] is not None)
        coverage_pct = 100.0 * cost_coverage / total_edges if total_edges > 0 else 0.0
        
        print(f"  已补全 cost: {cost_added} 条边")
        print(f"  已有 cost: {cost_existed} 条边")
        print(f"  cost 覆盖率: {cost_coverage}/{total_edges} = {coverage_pct:.2f}%")
        
        if drive_costs:
            import numpy as np
            arr = np.array(drive_costs)
            print(f"  Drive 边 cost: min={arr.min():.4f}  max={arr.max():.4f}  mean={arr.mean():.4f}")
        
        if transfer_costs:
            import numpy as np
            arr = np.array(transfer_costs)
            print(f"  Transfer 边 cost: min={arr.min():.4f}  max={arr.max():.4f}  mean={arr.mean():.4f}")
        
        # 断言 100% 覆盖
        assert coverage_pct == 100.0, f"cost 覆盖率为 {coverage_pct:.2f}%，应为 100%！"

    def export_data(self):
        """
        导出处理后的图数据和各人工件。

        输出文件：
        - data/processed/graph.pkl: 完整的 NetworkX 图对象
        - data/processed/base_map.csv: 用于可视化的简化节点数据 (保留现有)
        - data/processed/graph_nodes.csv: 完整节点表 (新增)
        - data/processed/graph_edges.csv: 完整边表 (新增)
        - data/processed/boundary.geojson: 研究区域凸包 (新增)
        """
        print("正在导出处理后的数据...")
        
        # =====================
        # 1. 以 Pickle 格式导出图
        # =====================
        graph_path = os.path.join(self.processed_data_dir, 'graph.pkl')
        
        try:
            with open(graph_path, 'wb') as f:
                pickle.dump(self.G, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"  图数据已保存至: {graph_path}")
            print(f"    - 节点数: {self.G.number_of_nodes()}")
            print(f"    - 边数: {self.G.number_of_edges()}")
        except Exception as e:
            print(f"  保存图数据时出错: {e}")
            raise
        
        # =====================
        # 2. 导出 base_map.csv (保持不变)
        # =====================
        csv_path = os.path.join(self.processed_data_dir, 'base_map.csv')
        node_records = []
        for node_id, attrs in self.G.nodes(data=True):
            pos = attrs.get('pos', (None, None))
            lon, lat = pos if pos else (None, None)
            record = {
                'id': node_id,
                'lat': lat,
                'lon': lon,
                'type': attrs.get('type', 'unknown'),
                'layer': attrs.get('layer', 'unknown')
            }
            node_records.append(record)
        
        base_map_df = pd.DataFrame(node_records)
        required_columns = ['id', 'lat', 'lon', 'type', 'layer']
        for col in required_columns:
            if col not in base_map_df.columns:
                base_map_df[col] = []
        base_map_df.to_csv(csv_path, index=False)
        print(f"  base_map.csv 已保存至: {csv_path}")

        # =====================
        # 3. 导出 graph_nodes.csv (新增)
        # =====================
        # 字段: node_id, lon, lat, type, layer, original_id, name
        gn_path = os.path.join(self.processed_data_dir, 'graph_nodes.csv')
        gn_records = []
        missing_pos_count = 0
        
        for node_id, attrs in self.G.nodes(data=True):
            pos = attrs.get('pos', (None, None))
            if pos is None or len(pos) != 2:
                lon, lat = None, None
                missing_pos_count += 1
            else:
                lon, lat = pos
            
            gn_records.append({
                "node_id": str(node_id),
                "lon": lon, 
                "lat": lat,
                "type": attrs.get("type", ""),
                "layer": attrs.get("layer", ""),
                "original_id": attrs.get("original_id", ""),
                "name": attrs.get("name", "")
            })
        
        # 排序: layer, type, node_id
        gn_records.sort(key=lambda x: (str(x["layer"]), str(x["type"]), str(x["node_id"])))
        
        pd.DataFrame(gn_records).to_csv(gn_path, index=False)
        print(f"  graph_nodes.csv 已保存, 共 {len(gn_records)} 行")
        print(f"    - missing_pos_count: {missing_pos_count}")

        # =====================
        # 4. 建立节点坐标查表 (用于 kepler CSV)
        # =====================
        node_pos = {}
        for node_id, attrs in self.G.nodes(data=True):
            pos = attrs.get('pos')
            if pos and len(pos) == 2:
                lon, lat = pos
                node_pos[str(node_id)] = (lon, lat)
        
        # =====================
        # 5. 导出 graph_edges.csv (新增)
        # =====================
        # 字段: u, v, key, mode, cost, weight, distance, transfer_type, highway, capacity
        ge_path = os.path.join(self.processed_data_dir, 'graph_edges.csv')
        ge_records = []
        missing_cost_count = 0
        
        for u, v, k, attrs in self.G.edges(keys=True, data=True):
            cost = attrs.get("cost")
            if pd.isna(cost):
                missing_cost_count += 1
            
            ge_records.append({
                "u": str(u),
                "v": str(v),
                "key": str(k),
                "mode": attrs.get("mode", ""),
                "cost": cost,
                "weight": attrs.get("weight", ""),
                "distance": attrs.get("distance", ""),
                "transfer_type": attrs.get("transfer_type", ""),
                "highway": attrs.get("highway", ""),
                "capacity": attrs.get("capacity", "")
            })
            
        if missing_cost_count > 0:
            raise ValueError(f"CRITICAL ERROR: Found {missing_cost_count} edges with missing cost!")
            
        # 排序: mode, u, v, key
        ge_records.sort(key=lambda x: (str(x["mode"]), str(x["u"]), str(x["v"]), str(x["key"])))
        
        ge_df = pd.DataFrame(ge_records)
        ge_df.to_csv(ge_path, index=False)
        print(f"  graph_edges.csv 已保存, 共 {len(ge_records)} 行")
        print(f"    - missing_cost_count: {missing_cost_count}")

        # =====================
        # 6. 导出 graph_edges_kepler.csv (新增 - Kepler.gl 专用)
        # =====================
        # 字段: 原字段 + u_lat, u_lon, v_lat, v_lon
        gek_path = os.path.join(self.processed_data_dir, 'graph_edges_kepler.csv')
        gek_records = []
        missing_endpoint_pos_count = 0
        
        for u, v, k, attrs in self.G.edges(keys=True, data=True):
            cost = attrs.get("cost")
            
            # 查询起点和终点坐标
            u_lon, u_lat = node_pos.get(str(u), (None, None))
            v_lon, v_lat = node_pos.get(str(v), (None, None))
            
            if u_lon is None or v_lon is None:
                missing_endpoint_pos_count += 1
            
            gek_records.append({
                "u": str(u),
                "v": str(v),
                "key": str(k),
                "mode": attrs.get("mode", ""),
                "cost": cost,
                "weight": attrs.get("weight", ""),
                "distance": attrs.get("distance", ""),
                "transfer_type": attrs.get("transfer_type", ""),
                "highway": attrs.get("highway", ""),
                "capacity": attrs.get("capacity", ""),
                "u_lat": u_lat,
                "u_lon": u_lon,
                "v_lat": v_lat,
                "v_lon": v_lon
            })
        
        # 排序: mode, u, v, key (同 graph_edges.csv)
        gek_records.sort(key=lambda x: (str(x["mode"]), str(x["u"]), str(x["v"]), str(x["key"])))
        
        gek_df = pd.DataFrame(gek_records)
        gek_df.to_csv(gek_path, index=False)
        print(f"  graph_edges_kepler.csv 已保存, 共 {len(gek_records)} 行")
        print(f"    - missing_endpoint_pos_count: {missing_endpoint_pos_count}")
        if missing_endpoint_pos_count > 0:
            print(f"    ⚠️  警告: {missing_endpoint_pos_count} 条边缺少端点坐标")

        # =====================
        # 7. 导出 boundary.geojson (新增)
        # =====================
        boundary_path = os.path.join(self.processed_data_dir, 'boundary.geojson')
        
        # 提取 drive 节点
        points = []
        for node_id, attrs in self.G.nodes(data=True):
            if attrs.get("layer") == "drive":
                pos = attrs.get("pos")
                if pos and len(pos) == 2:
                    points.append(list(pos)) # [lon, lat]
        
        if len(points) >= 3:
            hull_points = self._compute_convex_hull(points)
            # GeoJSON 闭合 Polygon 需要首尾一致
            if hull_points and hull_points[0] != hull_points[-1]:
                hull_points.append(hull_points[0])
                
            geojson = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "source": "drive_nodes_convex_hull",
                            "node_count": len(points),
                            "hull_vertices": len(hull_points)
                        },
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [hull_points]
                        }
                    }
                ]
            }
            
            import json
            with open(boundary_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, indent=2)
            print(f"  boundary.geojson 已保存")
            print(f"    - drive_node_count_used: {len(points)}")
            print(f"    - hull_vertices: {len(hull_points)}")
        else:
            print("  警告: drive 节点不足 3 个，无法计算凸包，跳过 boundary.geojson")

        print("导出完成！")
        
        # 最终校验刚写出的 CSV
        print("校验 graph_edges.csv cost 完整性...")
        check_df = pd.read_csv(ge_path)
        if check_df["cost"].isna().sum() > 0:
            raise ValueError("校验失败: 刚导出的 CSV 存在缺失 cost!")
        if (check_df["cost"] <= 0).any():
            print("注意: 存在 cost <= 0 的边")
        print("校验通过 [OK]")

    def _compute_convex_hull(self, points):
        """Monotone Chain algorithm for 2D convex hull."""
        points = sorted(points) # Lexicographical sort (x, y)
        if len(points) <= 1:
            return points
        
        # Lower hull
        lower = []
        for p in points:
            while len(lower) >= 2 and self._cross_product(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
            
        # Upper hull
        upper = []
        for p in reversed(points):
            while len(upper) >= 2 and self._cross_product(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
            
        # Concatenate (last of each is duplicate of first of other)
        return lower[:-1] + upper[:-1]

    def _cross_product(self, o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

if __name__ == "__main__":
    # =========================================
    # 巴尔地摩交通网络构建流水线
    # =========================================
    # 该脚本构建一个结合驾车道路和公交站点的多模态交通图。
    
    import time
    
    # 根据脚本位置推断项目根目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)  # 从 src/ 向上移动一级到项目根目录
    
    print("=" * 60)
    print("巴尔地摩交通网络构建程序")
    print("=" * 60)
    print(f"项目根目录: {project_root}")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 初始化管理器
    manager = BaltimoreDataManager(root_dir=project_root)
    
    # 步骤 1: 加载原始数据
    print("\n[步骤 1/6] 正在加载原始数据...")
    manager.load_raw_data()
    
    # 步骤 2: 构建驾车层
    print("\n[步骤 2/6] 正在构建驾车层...")
    manager.build_drive_layer()
    
    # 步骤 3: 构建公交层并连接
    print("\n[步骤 3/6] 正在构建公交层及多模态连接...")
    manager.build_bus_layer_and_connect()
    
    # 步骤 4: 完整性检查与剪枝
    print("\n[步骤 4/6] 正在进行完整性检查与剪枝...")
    manager.sanity_check_and_prune()
    
    # 步骤 5: 补全 cost 字段（确保 100% 覆盖率）
    print("\n[步骤 5/6] 正在补全 cost 字段...")
    manager.finalize_cost()
    
    # 步骤 6: 导出数据
    print("\n[步骤 6/6] 正在导出处理后的数据...")
    manager.export_data()
    
    print("\n" + "=" * 60)
    print("处理流水线全部完成！")
    print("=" * 60)
