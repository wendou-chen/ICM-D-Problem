"""
loaders.py
Standard data loaders for fast-track data ingestion.
Supports CSV/Excel -> NetworkX/Numpy.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import networkx as nx
from typing import Optional, List, Tuple, Union, Dict
from pathlib import Path

class GraphLoader:
    """
    Load Graph from Node/Edge CSVs.
    """
    @staticmethod
    def load_from_csv(
        node_csv: Union[str, Path],
        edge_csv: Union[str, Path],
        node_id_col: str = "id",
        edge_source_col: str = "u",
        edge_target_col: str = "v",
        edge_weight_col: str = "weight",
        directed: bool = False
    ) -> Tuple[nx.Graph, np.ndarray]:
        """
        Load graph and return (NetworkX Graph, Adjacency Matrix).
        """
        # Load Nodes
        df_nodes = pd.read_csv(node_csv)
        df_edges = pd.read_csv(edge_csv)
        
        # Create Graph
        G = nx.DiGraph() if directed else nx.Graph()
        
        # Add Nodes
        for _, row in df_nodes.iterrows():
            G.add_node(row[node_id_col], **row.to_dict())
            
        # Add Edges
        for _, row in df_edges.iterrows():
            u, v = row[edge_source_col], row[edge_target_col]
            attr = row.to_dict()
            # Ensure weight is float
            if edge_weight_col in attr:
                attr[edge_weight_col] = float(attr[edge_weight_col])
                
            G.add_edge(u, v, **attr)
            
        # Adjacency
        n = G.number_of_nodes()
        adj = nx.to_numpy_array(G, weight=edge_weight_col)
        
        return G, adj

    @staticmethod
    def load_coordinates(node_csv: Union[str, Path], 
                         x_col: str = "x", 
                         y_col: str = "y") -> np.ndarray:
        """Extract Nx2 coordinate matrix."""
        df = pd.read_csv(node_csv)
        return df[[x_col, y_col]].values

class MatrixLoader:
    """
    Load Matrices from CSV/Excel (Distance, Cost, Flow).
    """
    @staticmethod
    def load_matrix(path: Union[str, Path], 
                    header: Optional[int] = None, 
                    index_col: Optional[int] = None) -> np.ndarray:
        """Load dense matrix from CSV."""
        df = pd.read_csv(path, header=header, index_col=index_col)
        return df.values

    @staticmethod
    def load_od_list(path: Union[str, Path], 
                     o_col: str = "o", 
                     d_col: str = "d", 
                     flow_col: str = "flow") -> List[Tuple[int, int, float]]:
        """Load OD list: [(o, d, flow), ...]"""
        df = pd.read_csv(path)
        return list(zip(df[o_col], df[d_col], df[flow_col]))
