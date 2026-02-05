"""
od_sampling.py
OD Pairs Sampling Utilities for Task 2

Provides:
- compute_drive_lscc: Get largest strongly connected component of drive graph
- get_or_create_od_pairs: Generate and cache OD pairs with various policies
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Set, Optional, Any

import numpy as np
import networkx as nx

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def compute_drive_lscc(G: nx.MultiDiGraph, cache_dir: Path, graph_path: str) -> List[Any]:
    """
    Compute the Largest Strongly Connected Component (LSCC) of the drive layer.
    
    Returns:
        List of node IDs in the LSCC, sorted for stability.
    """
    cache_path = cache_dir / "cache_drive_lscc_nodes.json"
    
    # Check cache
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        if cached.get("graph_path") == graph_path:
            print(f"  [LSCC] Loaded from cache: {len(cached['nodes'])} nodes")
            return cached['nodes']
        else:
            print(f"  [LSCC] Cache graph_path mismatch, recomputing...")
    
    # Step 1: Filter drive nodes
    drive_nodes = set()
    for n, d in G.nodes(data=True):
        if (d.get("layer") == "drive" and 
            d.get("type") == "intersection" and 
            d.get("pos") is not None):
            drive_nodes.add(n)
    
    print(f"  [LSCC] Drive intersection nodes: {len(drive_nodes)}")
    
    # Step 2: Filter drive edges
    drive_edges = []
    for u, v, k, d in G.edges(keys=True, data=True):
        if d.get("mode") == "drive" and u in drive_nodes and v in drive_nodes:
            drive_edges.append((u, v))
    
    print(f"  [LSCC] Drive edges: {len(drive_edges)}")
    
    # Step 3: Construct DiGraph for SCC computation
    D = nx.DiGraph()
    D.add_nodes_from(drive_nodes)
    D.add_edges_from(drive_edges)
    
    # Step 4: Compute LSCC
    comps = list(nx.strongly_connected_components(D))
    if not comps:
        raise ValueError("No strongly connected components found in drive graph!")
    
    lscc = max(comps, key=len)
    lscc_nodes = sorted([n for n in lscc], key=lambda x: str(x))
    
    print(f"  [LSCC] Largest SCC size: {len(lscc_nodes)} / {len(drive_nodes)} ({100*len(lscc_nodes)/len(drive_nodes):.1f}%)")
    
    # Step 5: Cache
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Convert nodes to standard int/str to avoid json serialization error
    native_nodes = [int(n) if isinstance(n, (np.integer, np.int64)) else n for n in lscc_nodes]
    
    cache_data = {
        "graph_path": graph_path,
        "policy": "drive_lcc",
        "definition": "largest strongly connected component on directed drive graph",
        "node_count": len(native_nodes),
        "nodes": native_nodes,
        "created_at": datetime.now().isoformat()
    }
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"  [LSCC] Cached to {cache_path}")
    
    return native_nodes


def get_or_create_od_pairs(
    G: nx.MultiDiGraph,
    K: int,
    od_seed: int,
    od_policy: str,
    outdir: Path,
    graph_path: str
) -> Tuple[List[Tuple[Any, Any]], Path]:
    """
    Get or create OD pairs with caching.
    
    Args:
        G: Graph object
        K: Number of OD pairs
        od_seed: Random seed for sampling
        od_policy: "random" or "drive_lcc"
        outdir: Output directory for caches
        graph_path: Path string used for cache validation
    
    Returns:
        (od_pairs, od_pairs_path)
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    cache_name = f"od_pairs_{od_policy}_K{K}_seed{od_seed}.json"
    cache_path = outdir / cache_name
    
    # Check existing cache
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        if (cached.get("graph_path") == graph_path and 
            cached.get("K") == K and 
            cached.get("od_seed") == od_seed and
            cached.get("od_policy") == od_policy):
            pairs = [(p[0], p[1]) for p in cached["pairs"]]
            print(f"  [OD] Loaded {len(pairs)} pairs from cache: {cache_path}")
            return pairs, cache_path
        else:
            print(f"  [OD] Cache mismatch, regenerating...")
    
    # Determine node pool based on policy
    if od_policy == "drive_lcc":
        node_pool = compute_drive_lscc(G, outdir, graph_path)
    elif od_policy == "random":
        # Use all nodes
        node_pool = list(G.nodes())
    else:
        raise ValueError(f"Unknown od_policy: {od_policy}")
    
    if len(node_pool) < 2:
        raise ValueError(f"Node pool too small for OD sampling: {len(node_pool)}")
    
    # Sample OD pairs
    rng = np.random.default_rng(od_seed)
    pairs = []
    max_attempts = K * 100  # Safeguard against infinite loop
    attempts = 0
    
    while len(pairs) < K and attempts < max_attempts:
        o = rng.choice(node_pool)
        d = rng.choice(node_pool)
        if o != d:
            pairs.append((o, d))
        attempts += 1
    
    if len(pairs) < K:
        raise ValueError(f"Could not sample {K} OD pairs after {max_attempts} attempts")
    
    print(f"  [OD] Generated {len(pairs)} OD pairs using policy '{od_policy}'")
    
    # Compute digest for reproducibility check
    digest = hash(tuple(str(n) for n in node_pool[:100])) % (10**8)
    
    # Convert pairs to native types
    native_pairs = []
    for o, d in pairs:
        native_o = int(o) if isinstance(o, (np.integer, np.int64)) else o
        native_d = int(d) if isinstance(d, (np.integer, np.int64)) else d
        native_pairs.append([native_o, native_d])

    # Cache
    cache_data = {
        "graph_path": graph_path,
        "od_policy": od_policy,
        "K": K,
        "od_seed": od_seed,
        "created_at": datetime.now().isoformat(),
        "node_pool_size": len(node_pool),
        "node_pool_digest": str(digest),
        "pairs": native_pairs
    }
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"  [OD] Cached to {cache_path}")
    
    return [(p[0], p[1]) for p in native_pairs], cache_path


def load_od_pairs_from_file(path: Path) -> List[Tuple[Any, Any]]:
    """Load OD pairs from a JSON cache file."""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [(p[0], p[1]) for p in data["pairs"]]
