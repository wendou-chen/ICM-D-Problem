import networkx as nx
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional

class NetworkSolver:
    """
    针对 ICM D 题封装的网络科学算法库。
    集成最短路径、多维中心性分析、最小生成树及网络鲁棒性指标。
    """
    
    def __init__(self, graph_input: Union[np.ndarray, List[Tuple], nx.Graph], 
                 directed: bool = False, 
                 weight_label: str = 'weight'):
        """
        初始化网络求解器。
        :param graph_input: 邻接矩阵(numpy), 边列表(list of tuples), 或 nx.Graph 对象
        :param directed: 是否为有向图
        :param weight_label: 边权重的键名 (默认为 'weight')
        """
        self.directed = directed
        self.weight_label = weight_label
        
        # 统一转化为 NetworkX 对象
        if isinstance(graph_input, nx.Graph) or isinstance(graph_input, nx.DiGraph):
            self.G = graph_input
        elif isinstance(graph_input, np.ndarray):
            create_func = nx.from_numpy_array
            self.G = create_func(graph_input, create_using=(nx.DiGraph if directed else nx.Graph))
        elif isinstance(graph_input, list):
            self.G = nx.DiGraph() if directed else nx.Graph()
            self.G.add_weighted_edges_from(graph_input, weight=weight_label)
        else:
            raise ValueError("Unsupported input format.")

    # --- 1. 最短路径算法 (Routing & Flow) ---
    
    def get_shortest_path(self, source: int, target: int) -> Tuple[List[int], float]:
        """
        计算两点间最短路径 (Dijkstra/Bellman-Ford)。
        :return: (路径节点列表, 总代价)
        """
        try:
            path = nx.shortest_path(self.G, source=source, target=target, weight=self.weight_label)
            length = nx.shortest_path_length(self.G, source=source, target=target, weight=self.weight_label)
            return path, length
        except nx.NetworkXNoPath:
            return [], float('inf')

    def get_all_pairs_shortest_path_avg(self) -> float:
        """
        计算网络平均最短路径长度 (Average Path Length)。
        这是衡量网络传输效率（Efficiency）的关键指标。
        """
        if nx.is_connected(self.G) or (self.directed and nx.is_strongly_connected(self.G)):
            return nx.average_shortest_path_length(self.G, weight=self.weight_label)
        else:
            # 如果图不连通，计算最大连通分量的平均路径
            largest_cc = max(nx.connected_components(self.G), key=len)
            subgraph = self.G.subgraph(largest_cc)
            return nx.average_shortest_path_length(subgraph, weight=self.weight_label)

    # --- 2. 关键节点识别 (Centrality Analysis) ---
    
    def calculate_centralities(self, top_k: int = 5) -> pd.DataFrame:
        """
        一键计算所有核心中心性指标，用于识别 Key Nodes。
        包含：度中心性、介数中心性、接近中心性、特征向量中心性。
        :return: Pandas DataFrame, 索引为节点ID
        """
        # 1. Degree Centrality (连接度)
        dc = nx.degree_centrality(self.G)
        
        # 2. Betweenness Centrality (流量枢纽) - 通信网络中最重要的指标
        # 针对大规模网络进行采样近似，避免 O(N^3)
        bc = nx.betweenness_centrality(self.G, weight=self.weight_label, normalized=True)
        
        # 3. Closeness Centrality (拓扑中心)
        cc = nx.closeness_centrality(self.G, distance=self.weight_label)
        
        # 4. Eigenvector Centrality (影响力) - 类似 PageRank
        try:
            ec = nx.eigenvector_centrality_numpy(self.G, weight=self.weight_label)
        except:
            ec = {n: 0 for n in self.G.nodes()} # 收敛失败时的 fallback

        df = pd.DataFrame({
            'Degree': pd.Series(dc),
            'Betweenness': pd.Series(bc),
            'Closeness': pd.Series(cc),
            'Eigenvector': pd.Series(ec)
        })
        
        # O奖加分项：计算综合得分 (简单的加权平均，可根据题目修改权重)
        df['Score'] = 0.3*df['Degree'] + 0.4*df['Betweenness'] + 0.2*df['Closeness'] + 0.1*df['Eigenvector']
        return df.sort_values('Score', ascending=False).head(top_k)

    # --- 3. 拓扑骨干提取 (MST) ---
    
    def get_mst(self) -> Tuple[nx.Graph, float]:
        """
        计算最小生成树 (Minimum Spanning Tree)。
        用于解决“以最小代价连接所有节点”的问题。
        :return: (MST子图对象, MST总权重)
        """
        if self.directed:
            # 有向图的最小生成树通常指最小树形图 (Arborescence)，计算较慢，这里简化处理
            # 这里的实现视具体题目而定，美赛中通常转为无向图计算骨干
            mst = nx.minimum_spanning_tree(self.G.to_undirected(), weight=self.weight_label)
        else:
            mst = nx.minimum_spanning_tree(self.G, weight=self.weight_label)
            
        total_weight = mst.size(weight=self.weight_label)
        return mst, total_weight

    # --- 4. 网络鲁棒性 (Robustness) ---
    
    def check_robustness(self, remove_nodes: List[int]) -> Dict:
        """
        破坏性测试：移除指定节点后，评估网络性能的下降。
        这是 O 奖论文 Sensitivity Analysis 章节的必备数据。
        """
        G_temp = self.G.copy()
        G_temp.remove_nodes_from(remove_nodes)
        
        # 1. 连通性
        if self.directed:
            is_connected = nx.is_strongly_connected(G_temp)
            num_components = nx.number_strongly_connected_components(G_temp)
        else:
            is_connected = nx.is_connected(G_temp)
            num_components = nx.number_connected_components(G_temp)
            
        # 2. 网络效率 (Efficiency) - 通信背景常用
        try:
            eff = nx.global_efficiency(G_temp)
        except:
            eff = 0
            
        return {
            "remnant_nodes": len(G_temp.nodes),
            "is_connected": is_connected,
            "num_components": num_components,
            "global_efficiency": eff
        }