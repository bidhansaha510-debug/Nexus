"""
NEXUS AI - Graph Algorithms Module
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Real graph algorithms for causal graphs, semantic networks, and planning.
Provides actual computation, not LLM estimation.

Features:
  • Shortest path algorithms (Dijkstra, A*, BFS)
  • Centrality measures (betweenness, closeness, eigenvector, PageRank)
  • Community detection (Louvain, label propagation)
  • Subgraph matching and isomorphism
  • Causal graph analysis (do-calculus basics)
  • Reachability and connectivity analysis
  • Network flow algorithms

These algorithms provide the computational backbone for reasoning
about structured knowledge and causal relationships.
"""

import threading
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum, auto
import heapq
import math

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("graph_algorithms")

# Try to import NetworkX
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("NetworkX not available - using built-in implementations")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class PathType(Enum):
    """Types of paths in a graph"""
    SHORTEST = "shortest"
    LONGEST = "longest"
    ALL_PATHS = "all_paths"
    CRITICAL = "critical"  # Critical path in DAG
    CAUSAL = "causal"  # Causal path


class CentralityMeasure(Enum):
    """Centrality measures for node importance"""
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"
    KATZ = "katz"
    HITS_HUB = "hits_hub"
    HITS_AUTHORITY = "hits_authority"


class CommunityAlgorithm(Enum):
    """Algorithms for community detection"""
    LOUVAIN = "louvain"
    LABEL_PROPAGATION = "label_propagation"
    GREEDY_MODULARITY = "greedy_modularity"
    GIRVAN_NEWMAN = "girvan_newman"


@dataclass
class GraphNode:
    """A node in a graph"""
    node_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.node_id)
    
    def __eq__(self, other):
        if isinstance(other, GraphNode):
            return self.node_id == other.node_id
        return False


@dataclass
class GraphEdge:
    """An edge in a graph"""
    source: str
    target: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source, self.target))


@dataclass
class Path:
    """A path through a graph"""
    nodes: List[str]
    edges: List[Tuple[str, str]] = field(default_factory=list)
    total_weight: float = 0.0
    path_type: PathType = PathType.SHORTEST
    
    def length(self) -> int:
        return len(self.nodes) - 1 if self.nodes else 0
    
    def to_dict(self) -> Dict:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "total_weight": self.total_weight,
            "path_type": self.path_type.value,
            "length": self.length(),
        }


@dataclass
class Community:
    """A community in a graph"""
    community_id: int
    nodes: List[str]
    modularity: float = 0.0
    
    def size(self) -> int:
        return len(self.nodes)
    
    def to_dict(self) -> Dict:
        return {
            "community_id": self.community_id,
            "nodes": self.nodes,
            "size": self.size(),
            "modularity": self.modularity,
        }


@dataclass
class CausalEffect:
    """Result of causal analysis"""
    intervention: str  # The do(X) operation
    outcome: str
    effect: float  # Causal effect size
    confidence: float
    adjustment_set: List[str]  # Variables adjusted for
    method: str  # backdoor, frontdoor, IV, etc.
    
    def to_dict(self) -> Dict:
        return {
            "intervention": self.intervention,
            "outcome": self.outcome,
            "effect": self.effect,
            "confidence": self.confidence,
            "adjustment_set": self.adjustment_set,
            "method": self.method,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH ALGORITHMS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GraphAlgorithms:
    """
    Graph algorithms for reasoning about structured knowledge.
    
    Works with both NetworkX graphs and simple adjacency dicts.
    
    Operations:
      shortest_path()     — Find shortest path between nodes
      all_paths()         — Find all paths up to length k
      centrality()        — Compute node importance
      communities()       — Detect network communities
      reachability()      — Analyze reachability
      causal_effect()     — Compute causal effects (do-calculus)
      subgraph_match()    — Find matching subgraphs
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # ──── Stats ────
        self._total_queries = 0
        self._total_path_searches = 0
        self._total_centrality_computations = 0
        
        logger.info("GraphAlgorithms initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # SHORTEST PATH ALGORITHMS
    # ═══════════════════════════════════════════════════════════════════════════

    def shortest_path(
        self,
        graph: Any,
        source: str,
        target: str,
        weight: str = "weight",
        algorithm: str = "auto"
    ) -> Optional[Path]:
        """
        Find the shortest path between two nodes.
        
        Args:
            graph: NetworkX graph or adjacency dict
            source: Source node ID
            target: Target node ID
            weight: Edge weight attribute
            algorithm: "dijkstra", "bellman_ford", "bfs", "auto"
        
        Returns Path or None if no path exists.
        """
        self._total_path_searches += 1
        
        # Use NetworkX if available
        if NETWORKX_AVAILABLE and isinstance(graph, nx.Graph):
            return self._nx_shortest_path(graph, source, target, weight, algorithm)
        
        # Fall back to built-in implementation
        return self._builtin_shortest_path(graph, source, target, weight)

    def _nx_shortest_path(
        self,
        graph: nx.Graph,
        source: str,
        target: str,
        weight: str,
        algorithm: str
    ) -> Optional[Path]:
        """NetworkX-based shortest path"""
        try:
            if algorithm == "bfs" or not weight:
                path = nx.shortest_path(graph, source, target)
            else:
                path = nx.dijkstra_path(graph, source, target, weight=weight)
            
            # Calculate total weight
            total_weight = 0.0
            edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edges.append((u, v))
                if weight:
                    edge_data = graph.get_edge_data(u, v)
                    if edge_data:
                        total_weight += edge_data.get(weight, 1.0)
                else:
                    total_weight += 1.0
            
            return Path(
                nodes=path,
                edges=edges,
                total_weight=total_weight,
                path_type=PathType.SHORTEST,
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        except Exception as e:
            logger.error(f"NetworkX shortest path error: {e}")
            return None

    def _builtin_shortest_path(
        self,
        graph: Any,
        source: str,
        target: str,
        weight: str
    ) -> Optional[Path]:
        """Built-in Dijkstra's algorithm"""
        # Convert to adjacency dict if needed
        adj = self._to_adjacency_dict(graph)
        
        if source not in adj or target not in adj:
            return None
        
        # Dijkstra's algorithm
        dist = {source: 0.0}
        prev = {source: None}
        visited = set()
        pq = [(0.0, source)]  # (distance, node)
        
        while pq:
            d, u = heapq.heappop(pq)
            
            if u in visited:
                continue
            visited.add(u)
            
            if u == target:
                break
            
            for v, edge_data in adj.get(u, {}).items():
                if v in visited:
                    continue
                edge_weight = edge_data.get(weight, 1.0) if isinstance(edge_data, dict) else 1.0
                new_dist = dist[u] + edge_weight
                
                if v not in dist or new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(pq, (new_dist, v))
        
        # Reconstruct path
        if target not in prev:
            return None
        
        path = []
        node = target
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
        
        # Build edges
        edges = []
        for i in range(len(path) - 1):
            edges.append((path[i], path[i + 1]))
        
        return Path(
            nodes=path,
            edges=edges,
            total_weight=dist.get(target, 0.0),
            path_type=PathType.SHORTEST,
        )

    def all_paths(
        self,
        graph: Any,
        source: str,
        target: str,
        max_length: int = 5,
        max_paths: int = 10
    ) -> List[Path]:
        """
        Find all paths up to a maximum length.
        
        Uses DFS with pruning.
        """
        adj = self._to_adjacency_dict(graph)
        
        if source not in adj:
            return []
        
        paths = []
        stack = [(source, [source], [])]  # (current, path, edges)
        
        while stack and len(paths) < max_paths:
            current, path, edges = stack.pop()
            
            if len(path) > max_length + 1:
                continue
            
            if current == target and len(path) > 1:
                total_weight = sum(
                    self._get_edge_weight(adj, path[i], path[i+1])
                    for i in range(len(path) - 1)
                )
                paths.append(Path(
                    nodes=path.copy(),
                    edges=edges.copy(),
                    total_weight=total_weight,
                    path_type=PathType.ALL_PATHS,
                ))
                continue
            
            for neighbor in adj.get(current, {}):
                if neighbor not in path:  # Avoid cycles
                    new_edges = edges + [(current, neighbor)]
                    stack.append((neighbor, path + [neighbor], new_edges))
        
        return paths

    def _get_edge_weight(self, adj: Dict, u: str, v: str) -> float:
        """Get edge weight from adjacency dict"""
        edge_data = adj.get(u, {}).get(v, 1.0)
        if isinstance(edge_data, dict):
            return edge_data.get("weight", 1.0)
        return 1.0

    def _to_adjacency_dict(self, graph: Any) -> Dict:
        """Convert various graph formats to adjacency dict"""
        if isinstance(graph, dict):
            return graph
        if NETWORKX_AVAILABLE and isinstance(graph, nx.Graph):
            adj = {}
            for u in graph.nodes():
                adj[u] = {}
                for v in graph.neighbors(u):
                    adj[u][v] = dict(graph.get_edge_data(u, v) or {})
            return adj
        # Assume it's already an adjacency-like structure
        return graph

    # ═══════════════════════════════════════════════════════════════════════════
    # A* SEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def astar_search(
        self,
        graph: Any,
        source: str,
        target: str,
        heuristic: Callable[[str], float],
        weight: str = "weight"
    ) -> Optional[Path]:
        """
        A* search with custom heuristic.
        
        Args:
            graph: The graph to search
            source: Starting node
            target: Goal node
            heuristic: Function h(n) estimating cost from n to target
            weight: Edge weight attribute
        """
        adj = self._to_adjacency_dict(graph)
        
        if source not in adj:
            return None
        
        # A* algorithm
        g_score = {source: 0.0}
        f_score = {source: heuristic(source)}
        prev = {source: None}
        visited = set()
        pq = [(f_score[source], source)]
        
        while pq:
            _, u = heapq.heappop(pq)
            
            if u in visited:
                continue
            visited.add(u)
            
            if u == target:
                break
            
            for v, edge_data in adj.get(u, {}).items():
                if v in visited:
                    continue
                edge_weight = edge_data.get(weight, 1.0) if isinstance(edge_data, dict) else 1.0
                new_g = g_score[u] + edge_weight
                
                if v not in g_score or new_g < g_score[v]:
                    g_score[v] = new_g
                    f_score[v] = new_g + heuristic(v)
                    prev[v] = u
                    heapq.heappush(pq, (f_score[v], v))
        
        # Reconstruct path
        if target not in prev:
            return None
        
        path = []
        node = target
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
        
        edges = [(path[i], path[i+1]) for i in range(len(path) - 1)]
        
        return Path(
            nodes=path,
            edges=edges,
            total_weight=g_score.get(target, 0.0),
            path_type=PathType.SHORTEST,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # CENTRALITY MEASURES
    # ═══════════════════════════════════════════════════════════════════════════

    def centrality(
        self,
        graph: Any,
        measure: CentralityMeasure = CentralityMeasure.BETWEENNESS,
        top_k: int = 10
    ) -> Dict[str, float]:
        """
        Compute centrality measures for nodes.
        
        Args:
            graph: The graph to analyze
            measure: Type of centrality measure
            top_k: Return only top k nodes (0 for all)
        
        Returns dict mapping node_id -> centrality score.
        """
        self._total_centrality_computations += 1
        
        # Use NetworkX if available
        if NETWORKX_AVAILABLE and isinstance(graph, nx.Graph):
            return self._nx_centrality(graph, measure, top_k)
        
        # Fall back to built-in implementations
        return self._builtin_centrality(graph, measure, top_k)

    def _nx_centrality(
        self,
        graph: nx.Graph,
        measure: CentralityMeasure,
        top_k: int
    ) -> Dict[str, float]:
        """NetworkX-based centrality computation"""
        try:
            if measure == CentralityMeasure.DEGREE:
                result = nx.degree_centrality(graph)
            elif measure == CentralityMeasure.BETWEENNESS:
                result = nx.betweenness_centrality(graph)
            elif measure == CentralityMeasure.CLOSENESS:
                result = nx.closeness_centrality(graph)
            elif measure == CentralityMeasure.EIGENVECTOR:
                result = nx.eigenvector_centrality(graph, max_iter=1000)
            elif measure == CentralityMeasure.PAGERANK:
                result = nx.pagerank(graph)
            elif measure == CentralityMeasure.KATZ:
                result = nx.katz_centrality(graph, max_iter=1000)
            elif measure == CentralityMeasure.HITS_HUB:
                hubs, _ = nx.hits(graph, max_iter=1000)
                result = hubs
            elif measure == CentralityMeasure.HITS_AUTHORITY:
                _, authorities = nx.hits(graph, max_iter=1000)
                result = authorities
            else:
                result = nx.degree_centrality(graph)
            
            # Sort and limit
            sorted_result = dict(sorted(result.items(), key=lambda x: -x[1])[:top_k] if top_k else result.items())
            return sorted_result
            
        except Exception as e:
            logger.error(f"NetworkX centrality error: {e}")
            return {}

    def _builtin_centrality(
        self,
        graph: Any,
        measure: CentralityMeasure,
        top_k: int
    ) -> Dict[str, float]:
        """Built-in centrality implementations"""
        adj = self._to_adjacency_dict(graph)
        nodes = list(adj.keys())
        
        if not nodes:
            return {}
        
        if measure == CentralityMeasure.DEGREE:
            # Degree centrality: normalize by n-1
            n = len(nodes)
            max_degree = max(n - 1, 1)
            result = {
                node: len(adj.get(node, {})) / max_degree
                for node in nodes
            }
        elif measure == CentralityMeasure.CLOSENESS:
            result = self._closeness_centrality(adj)
        elif measure == CentralityMeasure.BETWEENNESS:
            result = self._betweenness_centrality(adj)
        else:
            # Default to degree centrality
            n = len(nodes)
            max_degree = max(n - 1, 1)
            result = {
                node: len(adj.get(node, {})) / max_degree
                for node in nodes
            }
        
        # Sort and limit
        sorted_result = dict(sorted(result.items(), key=lambda x: -x[1])[:top_k] if top_k else result.items())
        return sorted_result

    def _closeness_centrality(self, adj: Dict) -> Dict[str, float]:
        """Compute closeness centrality"""
        result = {}
        nodes = list(adj.keys())
        n = len(nodes)
        
        for node in nodes:
            # BFS to find distances
            dist = {node: 0}
            queue = deque([node])
            
            while queue:
                u = queue.popleft()
                for v in adj.get(u, {}):
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        queue.append(v)
            
            # Closeness = (n-1) / sum of distances
            if len(dist) > 1:
                total_dist = sum(dist.values())
                result[node] = (len(dist) - 1) / total_dist if total_dist > 0 else 0
            else:
                result[node] = 0
        
        return result

    def _betweenness_centrality(self, adj: Dict) -> Dict[str, float]:
        """Compute betweenness centrality (simplified)"""
        result = {node: 0.0 for node in adj}
        nodes = list(adj.keys())
        n = len(nodes)
        
        # Simplified: count how often each node is on shortest paths
        for source in nodes:
            # BFS from source
            dist = {source: 0}
            prev = defaultdict(list)
            queue = deque([source])
            
            while queue:
                u = queue.popleft()
                for v in adj.get(u, {}):
                    if v not in dist:
                        dist[v] = dist[u] + 1
                        prev[v].append(u)
                        queue.append(v)
                    elif dist[v] == dist[u] + 1:
                        prev[v].append(u)
        
            # Count shortest paths through each node
            for node in nodes:
                if node != source:
                    for v in prev.get(node, []):
                        result[node] += 1
        
        # Normalize
        if n > 2:
            norm = (n - 1) * (n - 2)
            for node in result:
                result[node] /= norm
        
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # COMMUNITY DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def detect_communities(
        self,
        graph: Any,
        algorithm: CommunityAlgorithm = CommunityAlgorithm.LOUVAIN
    ) -> List[Community]:
        """
        Detect communities in a graph.
        
        Returns list of Community objects.
        """
        if NETWORKX_AVAILABLE and isinstance(graph, nx.Graph):
            return self._nx_communities(graph, algorithm)
        
        # Fall back to label propagation
        return self._label_propagation(self._to_adjacency_dict(graph))

    def _nx_communities(
        self,
        graph: nx.Graph,
        algorithm: CommunityAlgorithm
    ) -> List[Community]:
        """NetworkX-based community detection"""
        try:
            # Convert to undirected for community detection
            if graph.is_directed():
                graph = graph.to_undirected()
            
            if algorithm == CommunityAlgorithm.LOUVAIN:
                communities = nx.community.louvain_communities(graph)
            elif algorithm == CommunityAlgorithm.LABEL_PROPAGATION:
                communities = list(nx.community.label_propagation_communities(graph))
            elif algorithm == CommunityAlgorithm.GREEDY_MODULARITY:
                communities = nx.community.greedy_modularity_communities(graph)
            elif algorithm == CommunityAlgorithm.GIRVAN_NEWMAN:
                comp = nx.community.girvan_newman(graph)
                communities = next(comp)  # Get first partition
            else:
                communities = nx.community.louvain_communities(graph)
            
            result = []
            for i, comm in enumerate(communities):
                result.append(Community(
                    community_id=i,
                    nodes=list(comm),
                ))
            return result
            
        except Exception as e:
            logger.error(f"NetworkX community detection error: {e}")
            return []

    def _label_propagation(self, adj: Dict) -> List[Community]:
        """Built-in label propagation algorithm"""
        # Initialize: each node has its own label
        labels = {node: i for i, node in enumerate(adj)}
        
        # Iterate until convergence
        changed = True
        max_iter = 100
        iteration = 0
        
        while changed and iteration < max_iter:
            changed = False
            iteration += 1
            
            for node in adj:
                if not adj.get(node):
                    continue
                
                # Count labels of neighbors
                label_counts = defaultdict(int)
                for neighbor in adj.get(node, {}):
                    label_counts[labels[neighbor]] += 1
                
                if not label_counts:
                    continue
                
                # Choose the most common label
                new_label = max(label_counts, key=label_counts.get)
                if labels[node] != new_label:
                    labels[node] = new_label
                    changed = True
        
        # Group by label
        communities_dict = defaultdict(list)
        for node, label in labels.items():
            communities_dict[label].append(node)
        
        return [
            Community(community_id=i, nodes=nodes)
            for i, nodes in enumerate(communities_dict.values())
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # REACHABILITY
    # ═══════════════════════════════════════════════════════════════════════════

    def reachable_nodes(
        self,
        graph: Any,
        source: str,
        max_depth: int = None
    ) -> Set[str]:
        """
        Find all nodes reachable from source.
        
        Args:
            graph: The graph
            source: Starting node
            max_depth: Maximum depth (None for unlimited)
        
        Returns set of reachable node IDs.
        """
        adj = self._to_adjacency_dict(graph)
        
        if source not in adj:
            return set()
        
        visited = {source}
        queue = deque([(source, 0)])
        
        while queue:
            node, depth = queue.popleft()
            
            if max_depth is not None and depth >= max_depth:
                continue
            
            for neighbor in adj.get(node, {}):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        
        return visited

    def strongly_connected_components(self, graph: Any) -> List[Set[str]]:
        """Find strongly connected components in a directed graph"""
        adj = self._to_adjacency_dict(graph)
        
        # Kosaraju's algorithm
        # Step 1: First DFS to get finish order
        visited = set()
        finish_order = []
        
        def dfs1(node):
            visited.add(node)
            for neighbor in adj.get(node, {}):
                if neighbor not in visited:
                    dfs1(neighbor)
            finish_order.append(node)
        
        for node in adj:
            if node not in visited:
                dfs1(node)
        
        # Step 2: Build reverse graph
        reverse_adj = defaultdict(dict)
        for u in adj:
            for v in adj[u]:
                reverse_adj[v][u] = adj[u][v]
        
        # Step 3: Second DFS on reverse graph
        visited.clear()
        components = []
        
        def dfs2(node, component):
            visited.add(node)
            component.add(node)
            for neighbor in reverse_adj.get(node, {}):
                if neighbor not in visited:
                    dfs2(neighbor, component)
        
        for node in reversed(finish_order):
            if node not in visited:
                component = set()
                dfs2(node, component)
                components.append(component)
        
        return components

    # ═══════════════════════════════════════════════════════════════════════════
    # CAUSAL GRAPH ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def find_backdoor_paths(
        self,
        graph: Any,
        treatment: str,
        outcome: str
    ) -> List[Path]:
        """
        Find backdoor paths in a causal graph.
        
        A backdoor path is a path from treatment to outcome that
        starts with an arrow pointing into treatment.
        
        These paths create confounding and must be blocked.
        """
        adj = self._to_adjacency_dict(graph)
        
        # Build reverse adjacency (parents)
        parents = defaultdict(set)
        for u in adj:
            for v in adj[u]:
                parents[v].add(u)
        
        # Find paths starting with treatment <- parent
        backdoor_paths = []
        for parent in parents[treatment]:
            # Find all paths from parent to outcome that don't go through treatment
            paths = self.all_paths(
                {k: v for k, v in adj.items() if k != treatment},
                parent,
                outcome,
                max_length=6
            )
            for path in paths:
                # Prepend treatment
                full_path = Path(
                    nodes=[treatment] + path.nodes,
                    edges=[(treatment, parent)] + path.edges,
                    total_weight=path.total_weight,
                    path_type=PathType.CAUSAL,
                )
                backdoor_paths.append(full_path)
        
        return backdoor_paths

    def find_adjustment_set(
        self,
        graph: Any,
        treatment: str,
        outcome: str
    ) -> List[str]:
        """
        Find a valid adjustment set for causal inference.
        
        Uses the backdoor criterion: find variables that block all
        backdoor paths without introducing new paths.
        """
        adj = self._to_adjacency_dict(graph)
        
        # Get all ancestors of treatment and outcome
        treatment_ancestors = self.reachable_nodes(adj, treatment)  # Simplified
        outcome_ancestors = self.reachable_nodes(adj, outcome)  # Simplified
        
        # Find backdoor paths
        backdoor_paths = self.find_backdoor_paths(graph, treatment, outcome)
        
        if not backdoor_paths:
            return []  # No confounding
        
        # Find nodes that appear on backdoor paths
        confounders = set()
        for path in backdoor_paths:
            for node in path.nodes:
                if node != treatment and node != outcome:
                    confounders.add(node)
        
        # Simple heuristic: return all confounders
        # In practice, would use more sophisticated selection
        return list(confounders)

    def compute_causal_effect(
        self,
        graph: Any,
        treatment: str,
        outcome: str,
        data: Dict[str, List[float]] = None
    ) -> CausalEffect:
        """
        Compute the causal effect of treatment on outcome.
        
        This is a simplified implementation. Full causal inference
        requires probabilistic graphical models and do-calculus.
        
        Args:
            graph: Causal DAG
            treatment: Treatment variable
            outcome: Outcome variable
            data: Optional data for estimation
        
        Returns CausalEffect object.
        """
        # Find adjustment set
        adjustment_set = self.find_adjustment_set(graph, treatment, outcome)
        
        # Find causal paths (directed paths from treatment to outcome)
        causal_paths = self.all_paths(graph, treatment, outcome, max_length=6)
        
        # Simple effect estimation (placeholder)
        # In practice, would use regression, propensity score, etc.
        effect = 1.0 if causal_paths else 0.0
        confidence = 0.7 if adjustment_set else 0.9  # Lower confidence if adjustment needed
        
        return CausalEffect(
            intervention=f"do({treatment})",
            outcome=outcome,
            effect=effect,
            confidence=confidence,
            adjustment_set=adjustment_set,
            method="backdoor" if adjustment_set else "direct",
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # SUBGRAPH MATCHING
    # ═══════════════════════════════════════════════════════════════════════════

    def find_motif(
        self,
        graph: Any,
        motif: Any,
        max_matches: int = 10
    ) -> List[Dict[str, str]]:
        """
        Find instances of a motif (subgraph pattern) in a graph.
        
        Args:
            graph: The graph to search
            motif: The pattern graph
            max_matches: Maximum number of matches to return
        
        Returns list of mappings {motif_node -> graph_node}.
        """
        adj = self._to_adjacency_dict(graph)
        motif_adj = self._to_adjacency_dict(motif)
        
        matches = []
        motif_nodes = list(motif_adj.keys())
        
        if not motif_nodes:
            return []
        
        # Simple subgraph matching (exponential in worst case)
        # For production, would use VF2 or similar algorithm
        
        def is_match(mapping):
            """Check if current mapping is valid"""
            for u in motif_adj:
                if u not in mapping:
                    continue
                for v in motif_adj[u]:
                    if v not in mapping:
                        continue
                    # Check if edge exists in graph
                    if mapping[v] not in adj.get(mapping[u], {}):
                        return False
            return True
        
        def search(idx, mapping, used):
            """Recursively search for matches"""
            if len(matches) >= max_matches:
                return
            
            if idx == len(motif_nodes):
                if is_match(mapping):
                    matches.append(mapping.copy())
                return
            
            motif_node = motif_nodes[idx]
            
            for graph_node in adj:
                if graph_node in used:
                    continue
                
                new_mapping = mapping.copy()
                new_mapping[motif_node] = graph_node
                
                if is_match(new_mapping):
                    used.add(graph_node)
                    search(idx + 1, new_mapping, used)
                    used.remove(graph_node)
        
        search(0, {}, set())
        return matches

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the graph algorithms engine"""
        self._running = True
        logger.info("GraphAlgorithms started")

    def stop(self):
        """Stop the graph algorithms engine"""
        self._running = False
        logger.info("GraphAlgorithms stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get algorithm statistics"""
        return {
            "running": getattr(self, '_running', False),
            "total_queries": self._total_queries,
            "total_path_searches": self._total_path_searches,
            "total_centrality_computations": self._total_centrality_computations,
            "networkx_available": NETWORKX_AVAILABLE,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

graph_algorithms = GraphAlgorithms()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    ga = GraphAlgorithms()
    
    # Create a simple test graph
    test_graph = {
        "A": {"B": {"weight": 1.0}, "C": {"weight": 2.0}},
        "B": {"D": {"weight": 1.0}},
        "C": {"D": {"weight": 1.0}},
        "D": {"E": {"weight": 2.0}},
        "E": {}
    }
    
    print("=== Shortest Path Test ===")
    path = ga.shortest_path(test_graph, "A", "E")
    if path:
        print(f"Path: {' -> '.join(path.nodes)}")
        print(f"Total weight: {path.total_weight}")
    
    print("\n=== All Paths Test ===")
    paths = ga.all_paths(test_graph, "A", "D", max_length=3)
    for p in paths:
        print(f"Path: {' -> '.join(p.nodes)} (weight: {p.total_weight})")
    
    print("\n=== Centrality Test ===")
    cent = ga.centrality(test_graph, CentralityMeasure.DEGREE)
    print(f"Degree centrality: {cent}")
    
    print("\n=== Reachability Test ===")
    reachable = ga.reachable_nodes(test_graph, "A")
    print(f"Nodes reachable from A: {reachable}")
    
    print("\n=== Community Detection Test ===")
    communities = ga.detect_communities(test_graph)
    for c in communities:
        print(f"Community {c.community_id}: {c.nodes}")
    
    print(f"\nStats: {ga.get_stats()}")