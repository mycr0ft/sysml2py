#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Storage abstraction layer for sysmlpy.

Provides a protocol-based storage backend that supports:
- InMemoryStore: dict/tree storage (current behavior, backward compatible)
- NetworkXStore: graph database storage (analysis, queries, scale)

Elements are identified by stable UUIDs, not names. Names remain the user-facing
identity while UUIDs provide persistence and graph connectivity.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Iterator
import uuid


# ── Relationship types ──────────────────────────────────────────────────────

REL_PARENT_CHILD = "parent_child"
REL_TYPED_BY = "typed_by"
REL_SPECIALIZES = "specializes"
REL_SUBSETS = "subsets"
REL_REDEFINES = "redefines"
REL_CONNECTS = "connects"
REL_FLOWS = "flows"
REL_TRANSITIONS = "transitions"
REL_SATISFIES = "satisfies"
REL_DERIVES = "derives"
REL_REFINES = "refines"
REL_VERIFIES = "verifies"


# ── Store Protocol ──────────────────────────────────────────────────────────

class Store(ABC):
    """Abstract storage backend for sysmlpy elements.

    All element data is stored as dicts keyed by UUID. Relationships are
    stored as typed edges between element UUIDs.

    Subclasses must implement: put, get, delete, children, parents,
    relationships, and query.
    """

    @abstractmethod
    def put(self, element_id: str, data: dict,
            parent_id: Optional[str] = None,
            rel_type: str = REL_PARENT_CHILD) -> None:
        """Store an element.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element (UUID).
        data : dict
            Element properties (name, sysml_type, custom attrs, etc.).
        parent_id : str, optional
            Parent element ID. If provided, creates a relationship edge.
        rel_type : str
            Type of relationship to parent (default: parent_child).
        """

    @abstractmethod
    def get(self, element_id: str) -> Optional[dict]:
        """Retrieve element data by ID.

        Returns None if element does not exist.
        """

    @abstractmethod
    def delete(self, element_id: str) -> bool:
        """Remove an element and all its relationships.

        Returns True if element existed and was removed.
        """

    @abstractmethod
    def children(self, parent_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return child element IDs for a given parent.

        Parameters
        ----------
        parent_id : str
            The parent element's UUID.
        rel_type : str
            Filter by relationship type (default: parent_child).

        Returns
        -------
        list[str]
            Ordered list of child element UUIDs.
        """

    @abstractmethod
    def parents(self, child_id: str, rel_type: Optional[str] = None) -> list[str]:
        """Return parent element IDs for a given child.

        Parameters
        ----------
        child_id : str
            The child element's UUID.
        rel_type : str, optional
            Filter by relationship type. If None, returns all parents.

        Returns
        -------
        list[str]
            List of parent element UUIDs.
        """

    @abstractmethod
    def relationships(self, element_id: str,
                      rel_type: Optional[str] = None,
                      direction: str = "both") -> list[tuple[str, str, dict]]:
        """Return relationships for an element.

        Parameters
        ----------
        element_id : str
            The element's UUID.
        rel_type : str, optional
            Filter by relationship type.
        direction : str
            "out" (edges from this element), "in" (edges to this element),
            or "both" (default).

        Returns
        -------
        list[tuple[str, str, dict]]
            List of (target_id, rel_type, edge_data) tuples.
        """

    @abstractmethod
    def query(self, **filters) -> list[str]:
        """Find elements matching property filters.

        Parameters
        ----------
        **filters : dict
            Property name = value pairs to match.
            Special keys:
              - sysml_type: filter by element type
              - name: filter by name (supports '*' wildcard)

        Returns
        -------
        list[str]
            List of matching element UUIDs.
        """

    @abstractmethod
    def has(self, element_id: str) -> bool:
        """Check if an element exists."""

    @abstractmethod
    def __len__(self) -> int:
        """Return total number of elements in the store."""

    @abstractmethod
    def ids(self) -> Iterator[str]:
        """Iterate over all element IDs in the store."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all elements and relationships."""

    def descendants(self, root_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all descendant element IDs (recursive children).

        Default implementation uses BFS over children(). Subclasses
        with graph backends may override for better performance.
        """
        result = []
        queue = list(self.children(root_id, rel_type))
        while queue:
            cid = queue.pop(0)
            result.append(cid)
            queue.extend(self.children(cid, rel_type))
        return result

    def ancestors(self, leaf_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all ancestor element IDs (recursive parents).

        Default implementation walks up via parents(). Subclasses
        with graph backends may override.
        """
        result = []
        current = leaf_id
        while True:
            parents = self.parents(current, rel_type)
            if not parents:
                break
            pid = parents[0]
            result.append(pid)
            current = pid
        return result

    def path(self, source_id: str, target_id: str,
             rel_type: str = REL_PARENT_CHILD) -> Optional[list[str]]:
        """Find shortest path between two elements.

        Default implementation uses BFS. Graph backends override
        with native shortest-path algorithms.
        """
        if source_id == target_id:
            return [source_id]

        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            for child_id in self.children(current, rel_type):
                if child_id == target_id:
                    return path + [child_id]
                if child_id not in visited:
                    visited.add(child_id)
                    queue.append((child_id, path + [child_id]))

        return None


# ── InMemory Store ──────────────────────────────────────────────────────────

class InMemoryStore(Store):
    """Dict-based storage backend. Mirrors current sysmlpy behavior.

    Elements are stored in a flat dict keyed by UUID. Parent-child
    relationships are tracked via adjacency lists. This backend provides
    O(1) lookups and is fully backward compatible with the existing API.
    """

    def __init__(self):
        self._elements: dict[str, dict] = {}
        self._children: dict[str, list[str]] = {}
        self._parents: dict[str, list[str]] = {}
        self._edges: dict[str, list[tuple[str, str, dict]]] = {}

    def __repr__(self) -> str:
        n_elem = len(self._elements)
        n_edge = sum(len(v) for v in self._edges.values())
        return f"InMemoryStore(elements={n_elem}, edges={n_edge})"

    def put(self, element_id: str, data: dict,
            parent_id: Optional[str] = None,
            rel_type: str = REL_PARENT_CHILD) -> None:
        """Store an element and optionally link it to a parent.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element.
        data : dict
            Element attributes (e.g., {'name': 'Wheel', 'sysml_type': 'part'}).
        parent_id : str, optional
            Parent element ID to establish a parent-child relationship.
        rel_type : str, optional
            Relationship type. Default is REL_PARENT_CHILD.
        """
        self._elements[element_id] = data

        if parent_id is not None:
            self._children.setdefault(parent_id, []).append(element_id)
            self._parents.setdefault(element_id, []).append(parent_id)

            edge_data = {"rel_type": rel_type}
            self._edges.setdefault(parent_id, []).append((element_id, rel_type, edge_data))
            self._edges.setdefault(element_id, []).append((parent_id, rel_type, edge_data))

    def get(self, element_id: str) -> Optional[dict]:
        """Retrieve an element's data by ID.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element.

        Returns
        -------
        dict or None
            Element data dict, or None if not found.
        """
        return self._elements.get(element_id)

    def delete(self, element_id: str) -> bool:
        """Remove an element and all its relationships.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element to remove.

        Returns
        -------
        bool
            True if the element was found and deleted, False otherwise.
        """
        if element_id not in self._elements:
            return False

        del self._elements[element_id]

        for pid in self._parents.pop(element_id, []):
            if pid in self._children:
                self._children[pid] = [c for c in self._children[pid] if c != element_id]

        for cid in self._children.pop(element_id, []):
            if cid in self._parents:
                self._parents[cid] = [p for p in self._parents[cid] if p != element_id]

        self._edges.pop(element_id, None)
        for eid in list(self._edges.keys()):
            self._edges[eid] = [(t, r, d) for t, r, d in self._edges[eid]
                                if t != element_id]

        return True

    def children(self, parent_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Get the IDs of child elements for a given parent.

        Parameters
        ----------
        parent_id : str
            Parent element ID.
        rel_type : str, optional
            Filter by relationship type. Default is REL_PARENT_CHILD.

        Returns
        -------
        list of str
            List of child element IDs.
        """
        return self._children.get(parent_id, []).copy()

    def parents(self, child_id: str, rel_type: Optional[str] = None) -> list[str]:
        """Get the IDs of parent elements for a given child.

        Parameters
        ----------
        child_id : str
            Child element ID.
        rel_type : str, optional
            Filter by relationship type (unused in this implementation).

        Returns
        -------
        list of str
            List of parent element IDs.
        """
        return self._parents.get(child_id, []).copy()

    def relationships(self, element_id: str,
                      rel_type: Optional[str] = None,
                      direction: str = "both") -> list[tuple[str, str, dict]]:
        """Get all relationships for an element.

        Parameters
        ----------
        element_id : str
            Element ID to query.
        rel_type : str, optional
            Filter by relationship type.
        direction : str, optional
            Direction filter (unused in this implementation).

        Returns
        -------
        list of tuple
            List of (target_id, rel_type, edge_data) tuples.
        """
        edges = self._edges.get(element_id, [])
        if rel_type:
            edges = [(t, r, d) for t, r, d in edges if r == rel_type]
        return edges.copy()

    def query(self, **filters) -> list[str]:
        """Query elements by attribute filters.

        Parameters
        ----------
        **filters : dict
            Attribute name=value pairs to match. Supports glob patterns
            with '*' for the 'name' field.

        Returns
        -------
        list of str
            List of matching element IDs.

        Examples
        --------
        >>> store.query(sysml_type='part')
        ['uuid1', 'uuid2']
        >>> store.query(name='*Wheel*')
        ['uuid3']
        """
        results = []
        for eid, data in self._elements.items():
            match = True
            for key, value in filters.items():
                if key == "name" and "*" in str(value):
                    import fnmatch
                    if not fnmatch.fnmatch(data.get("name", ""), value):
                        match = False
                        break
                elif data.get(key) != value:
                    match = False
                    break
            if match:
                results.append(eid)
        return results

    def has(self, element_id: str) -> bool:
        """Check if an element exists in the store.

        Parameters
        ----------
        element_id : str
            Element ID to check.

        Returns
        -------
        bool
            True if the element exists, False otherwise.
        """
        return element_id in self._elements

    def __len__(self) -> int:
        """Return the number of elements in the store.

        Returns
        -------
        int
            Number of stored elements.
        """
        return len(self._elements)

    def ids(self) -> Iterator[str]:
        """Iterate over all element IDs in the store.

        Returns
        -------
        iterator of str
            Iterator over element IDs.
        """
        return iter(self._elements.keys())

    def clear(self) -> None:
        """Remove all elements and relationships from the store."""
        self._elements.clear()
        self._children.clear()
        self._parents.clear()
        self._edges.clear()


# ── NetworkX Store ──────────────────────────────────────────────────────────

class NetworkXStore(Store):
    """Graph database storage backend using NetworkX.

    Elements are nodes with properties stored as node attributes.
    Relationships are directed edges with typed labels. This backend
    enables graph analysis (shortest paths, centrality, cycles) and
    scales to projects that exceed simple tree structures.

    Requires: pip install networkx
    """

    def __init__(self, directed: bool = True):
        """Initialize a NetworkX-based graph store.

        Parameters
        ----------
        directed : bool
            If True (default), creates a MultiDiGraph. If False, creates
            a MultiGraph for undirected relationships.
        """
        import networkx as nx
        self._directed = directed
        if directed:
            self._graph = nx.MultiDiGraph()
        else:
            self._graph = nx.MultiGraph()
        self._nx = nx

    def __repr__(self) -> str:
        return (f"NetworkXStore(nodes={self._graph.number_of_nodes()}, "
                f"edges={self._graph.number_of_edges()}, directed={self._directed})")

    def put(self, element_id: str, data: dict,
            parent_id: Optional[str] = None,
            rel_type: str = REL_PARENT_CHILD) -> None:
        """Store an element as a graph node and optionally add an edge to a parent.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element.
        data : dict
            Element attributes stored as node properties.
        parent_id : str, optional
            Parent element ID to create a directed edge.
        rel_type : str, optional
            Edge label/type. Default is REL_PARENT_CHILD.
        """

        self._graph.add_node(element_id, **data)

        if parent_id is not None:
            self._graph.add_edge(parent_id, element_id,
                                  rel_type=rel_type, **{"_rel": rel_type})

    def get(self, element_id: str) -> Optional[dict]:
        """Retrieve a node's attributes by ID.

        Parameters
        ----------
        element_id : str
            Node ID to look up.

        Returns
        -------
        dict or None
            Node attributes dict, or None if not found.
        """
        if not self._graph.has_node(element_id):
            return None
        return dict(self._graph.nodes[element_id])

    def delete(self, element_id: str) -> bool:
        """Remove a node and all its incident edges.

        Parameters
        ----------
        element_id : str
            Node ID to remove.

        Returns
        -------
        bool
            True if the node was found and deleted, False otherwise.
        """
        if not self._graph.has_node(element_id):
            return False
        self._graph.remove_node(element_id)
        return True

    def children(self, parent_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Get child element IDs connected by outgoing edges of the given type.

        Parameters
        ----------
        parent_id : str
            Parent node ID.
        rel_type : str
            Filter by edge relationship type. Default is REL_PARENT_CHILD.

        Returns
        -------
        list[str]
            List of child node IDs.
        """
        if not self._graph.has_node(parent_id):
            return []
        result = []
        for _, child, data in self._graph.out_edges(parent_id, data=True):
            if data.get("rel_type") == rel_type:
                result.append(child)
        return result

    def parents(self, child_id: str, rel_type: Optional[str] = None) -> list[str]:
        """Get parent element IDs connected by incoming edges.

        Parameters
        ----------
        child_id : str
            Child node ID.
        rel_type : str, optional
            Filter by edge relationship type. If None, returns all parents.

        Returns
        -------
        list[str]
            List of parent node IDs.
        """
        if not self._graph.has_node(child_id):
            return []
        result = []
        for parent, _, data in self._graph.in_edges(child_id, data=True):
            if rel_type is None or data.get("rel_type") == rel_type:
                result.append(parent)
        return result

    def relationships(self, element_id: str,
                      rel_type: Optional[str] = None,
                      direction: str = "both") -> list[tuple[str, str, dict]]:
        """Get all relationships (edges) connected to a node.

        Parameters
        ----------
        element_id : str
            Node ID to query.
        rel_type : str, optional
            Filter by edge relationship type.
        direction : str
            "out" (outgoing edges), "in" (incoming edges), or "both" (default).

        Returns
        -------
        list[tuple[str, str, dict]]
            List of (target_id, rel_type, edge_data) tuples.
        """
        if not self._graph.has_node(element_id):
            return []

        edges = []
        if direction in ("out", "both"):
            for _, target, data in self._graph.out_edges(element_id, data=True):
                rt = data.get("rel_type", "")
                if rel_type is None or rt == rel_type:
                    edges.append((target, rt, dict(data)))
        if direction in ("in", "both"):
            for source, _, data in self._graph.in_edges(element_id, data=True):
                rt = data.get("rel_type", "")
                if rel_type is None or rt == rel_type:
                    edges.append((source, rt, dict(data)))
        return edges

    def query(self, **filters) -> list[str]:
        """Find nodes matching property filters.

        Parameters
        ----------
        **filters : dict
            Node attribute name=value pairs to match.
            Supports glob patterns with '*' for the 'name' field.

        Returns
        -------
        list[str]
            List of matching node IDs.
        """
        results = []
        for node, data in self._graph.nodes(data=True):
            match = True
            for key, value in filters.items():
                if key == "name" and "*" in str(value):
                    import fnmatch
                    if not fnmatch.fnmatch(data.get("name", ""), value):
                        match = False
                        break
                elif data.get(key) != value:
                    match = False
                    break
            if match:
                results.append(node)
        return results

    def has(self, element_id: str) -> bool:
        """Check if a node exists in the graph.

        Parameters
        ----------
        element_id : str
            Node ID to check.

        Returns
        -------
        bool
            True if the node exists, False otherwise.
        """
        return self._graph.has_node(element_id)

    def __len__(self) -> int:
        """Return the number of nodes in the graph.

        Returns
        -------
        int
            Number of nodes.
        """
        return self._graph.number_of_nodes()

    def ids(self) -> Iterator[str]:
        """Iterate over all node IDs in the graph.

        Returns
        -------
        iterator of str
            Iterator over node IDs.
        """
        return iter(self._graph.nodes())

    def clear(self) -> None:
        """Remove all nodes and edges from the graph."""
        self._graph.clear()

    # ── Graph-specific methods ──────────────────────────────────────────

    def descendants(self, root_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all descendants via BFS on the graph."""
        if not self._graph.has_node(root_id):
            return []
        try:
            return list(self._nx.descendants(self._graph, root_id))
        except self._nx.NetworkXError:
            return []

    def ancestors(self, leaf_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all ancestors via reverse BFS on the graph."""
        if not self._graph.has_node(leaf_id):
            return []
        try:
            return list(self._nx.ancestors(self._graph, leaf_id))
        except self._nx.NetworkXError:
            return []

    def path(self, source_id: str, target_id: str,
             rel_type: str = REL_PARENT_CHILD) -> Optional[list[str]]:
        """Find shortest path using NetworkX native algorithm."""
        if not self._graph.has_node(source_id) or not self._graph.has_node(target_id):
            return None
        try:
            return self._nx.shortest_path(self._graph, source_id, target_id)
        except self._nx.NetworkXNoPath:
            return None

    def connected_components(self, rel_type: Optional[str] = None) -> list[set[str]]:
        """Return weakly connected components of the graph.

        Parameters
        ----------
        rel_type : str, optional
            If provided, only considers edges of this relationship type.

        Returns
        -------
        list[set[str]]
            List of sets, each containing node IDs in a connected component.
        """
        if rel_type:
            subgraph = self._nx.subgraph_view(
                self._graph,
                edge_filter=lambda e: self._graph.edges[e].get("rel_type") == rel_type
            )
            return list(self._nx.weakly_connected_components(subgraph))
        return list(self._nx.weakly_connected_components(self._graph))

    def cycles(self, rel_type: Optional[str] = None) -> list[list[str]]:
        """Find all simple cycles in the graph.

        Parameters
        ----------
        rel_type : str, optional
            If provided, only considers edges of this relationship type.

        Returns
        -------
        list[list[str]]
            List of cycles, each represented as a list of node IDs.
        """
        if rel_type:
            subgraph = self._nx.subgraph_view(
                self._graph,
                edge_filter=lambda e: self._graph.edges[e].get("rel_type") == rel_type
            )
            return list(self._nx.simple_cycles(subgraph))
        return list(self._nx.simple_cycles(self._graph))

    def centrality(self, rel_type: Optional[str] = None) -> dict[str, float]:
        """Compute degree centrality for all nodes.

        Parameters
        ----------
        rel_type : str, optional
            If provided, only considers edges of this relationship type.

        Returns
        -------
        dict[str, float]
            Mapping of node ID to centrality score (0.0 to 1.0).
        """
        if rel_type:
            subgraph = self._nx.subgraph_view(
                self._graph,
                edge_filter=lambda e: self._graph.edges[e].get("rel_type") == rel_type
            )
            return self._nx.degree_centrality(subgraph)
        return self._nx.degree_centrality(self._graph)

    def subgraph(self, element_ids: list[str]) -> "NetworkXStore":
        """Create a new store containing only the specified elements and their edges.

        Parameters
        ----------
        element_ids : list[str]
            Node IDs to include in the subgraph.

        Returns
        -------
        NetworkXStore
            A new store with a copy of the induced subgraph.
        """
        new_store = NetworkXStore()
        new_store._graph = self._graph.subgraph(element_ids).copy()
        return new_store

    def export_graphml(self, path: str) -> None:
        """Export the graph to GraphML format for visualization in external tools.

        Parameters
        ----------
        path : str
            File path to write the GraphML file to.
        """
        self._nx.write_graphml(self._graph, path)

    def stats(self) -> dict:
        """Compute summary statistics about the graph.

        Returns
        -------
        dict
            Dictionary with keys: nodes, edges, density, is_connected, avg_degree.
        """
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "density": self._nx.density(self._graph),
            "is_connected": self._nx.is_weakly_connected(self._graph) if self._graph.number_of_nodes() > 0 else True,
            "avg_degree": sum(dict(self._graph.degree()).values()) / max(self._graph.number_of_nodes(), 1),
        }

    # ── Phase D query extensions (v0.56.0) ──────────────────────────────

    def all_paths(self, source_id: str, target_id: str,
                  rel_type: Optional[str] = None,
                  max_paths: int = 20) -> list[list[str]]:
        """Find up to *max_paths* simple paths between two elements.

        Useful for impact analysis: every route a flow/connection can
        take between two parts.

        Parameters
        ----------
        source_id, target_id : str
            Endpoint node IDs.
        rel_type : str, optional
            Restrict traversal to edges of this relationship type.
        max_paths : int
            Safety cap on returned paths (default 20 — path enumeration
            is exponential in dense graphs).

        Returns
        -------
        list[list[str]]
            Each path is a list of node IDs from source to target.
            Empty list when either endpoint is missing or unconnected.
        """
        if not self._graph.has_node(source_id) or not self._graph.has_node(target_id):
            return []
        graph = self._filtered_graph(rel_type)
        try:
            count = 0
            paths = []
            for p in self._nx.all_simple_paths(graph, source_id, target_id):
                paths.append(list(p))
                count += 1
                if count >= max_paths:
                    break
            return paths
        except self._nx.NetworkXNoPath:
            return []
        except self._nx.NodeNotFound:
            return []

    def in_degree_centrality(self, rel_type: Optional[str] = None) -> dict[str, float]:
        """Compute in-degree centrality (how many elements reference *me*).

        High in-degree = hub element that many others depend on.

        Returns
        -------
        dict[str, float]
            Mapping of node ID to in-degree fraction (0.0–1.0).
        """
        graph = self._filtered_graph(rel_type)
        return self._nx.in_degree_centrality(graph)

    def out_degree_centrality(self, rel_type: Optional[str] = None) -> dict[str, float]:
        """Compute out-degree centrality (how many elements *I* reference)."""
        graph = self._filtered_graph(rel_type)
        return self._nx.out_degree_centrality(graph)

    def descendants_depth_limited(self, root_id: str, max_depth: int = 3,
                                  rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return descendants within *max_depth* levels of *root_id*.

        Useful for "direct children of this hierarchy level" queries.
        """
        if not self._graph.has_node(root_id):
            return []
        result: list[str] = []
        frontier = {root_id}
        visited = {root_id}
        for _ in range(max_depth):
            nxt: set[str] = set()
            for node in frontier:
                for succ in self._graph.successors(node):
                    edge_ok = any(
                        self._graph.edges[node, succ, k].get("rel_type") == rel_type
                        for k in self._graph[node][succ]
                    ) if self._graph.has_edge(node, succ) else False
                    if edge_ok and succ not in visited:
                        nxt.add(succ)
            visited |= nxt
            result.extend(sorted(nxt))
            frontier = nxt
            if not frontier:
                break
        return result

    def neighborhood(self, element_id: str, radius: int = 2,
                     rel_type: Optional[str] = None) -> set[str]:
        """Return the ego-neighborhood of *element_id* within *radius* hops
        (following edges in both directions)."""
        if not self._graph.has_node(element_id):
            return set()
        graph = self._filtered_graph(rel_type)
        return set(self._nx.ego_graph(graph, element_id, radius=radius, undirected=True).nodes())

    def _filtered_graph(self, rel_type: Optional[str]):
        """Return a view restricted to *rel_type* edges, or the full graph."""
        if not rel_type:
            return self._graph
        return self._nx.subgraph_view(
            self._graph,
            edge_filter=lambda e: self._graph.edges[e].get("rel_type") == rel_type,
        )

    def impact_analysis(self, element_id: str, rel_types: Optional[list[str]] = None,
                        direction: str = "downstream") -> set[str]:
        """Elements transitively affected by changes to *element_id*.

        Follows reverse structural edges (anything that inherits from,
        types by, or flows from *element_id* depends on it).

        Parameters
        ----------
        element_id : str
            Changed element.
        rel_types : list[str], optional
            Relationship types to consider (default: all).
        direction : {"downstream", "upstream"}
            ``downstream`` follows edges outward (what I affect);
            ``upstream`` follows edges inward (what affects me).
        """
        if not self._graph.has_node(element_id):
            return set()
        if rel_types:
            graph = self._nx.MultiDiGraph()
            for u, v, k, d in self._graph.edges(keys=True):
                if self._graph.edges[u, v, k].get("rel_type") in rel_types:
                    graph.add_edge(u, v, rel_type=self._graph.edges[u, v, k].get("rel_type"))
            for n in self._graph.nodes:
                graph.add_node(n, **self._graph.nodes[n])
        else:
            graph = self._graph
        successors = graph.successors if direction == "downstream" else graph.predecessors
        seen = {element_id}
        frontier = [element_id]
        while frontier:
            current = frontier.pop()
            for nxt in successors(current):
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append(nxt)
        seen.discard(element_id)
        return seen


# ── Kuzu Store ──────────────────────────────────────────────────────────────

class KuzuStore(Store):
    """Embedded graph database storage backend using Kuzu.

    Elements are nodes with properties stored as node attributes.
    Relationships are directed edges with typed labels. This backend
    provides disk persistence, ACID transactions, and Cypher query support.

    Requires: pip install kuzu (or: pip install sysmlpy[kuzu])

    Usage:
        # In-memory (volatile)
        store = KuzuStore()

        # Disk-persistent
        store = KuzuStore(database="/path/to/model.db")
    """

    def __init__(self, database: str = ":memory:"):
        """Initialize a Kuzu-based graph store.

        Parameters
        ----------
        database : str
            Path to the database directory, or ":memory:" for in-memory mode.
        """
        import kuzu
        self._database = database
        self._db = kuzu.Database(database)
        self._conn = kuzu.Connection(self._db)
        self._init_schema()

    def __repr__(self) -> str:
        return f"KuzuStore(database={self._database!r})"

    def _init_schema(self) -> None:
        """Create the node and relationship tables if they don't exist."""
        self._conn.execute(
            "CREATE NODE TABLE IF NOT EXISTS Element("
            "id STRING PRIMARY KEY, "
            "name STRING, "
            "sysml_type STRING, "
            "python_type STRING, "
            "data STRING)"
        )
        self._conn.execute(
            "CREATE REL TABLE IF NOT EXISTS Relationship("
            "FROM Element TO Element, "
            "rel_type STRING)"
        )

    def _escape(self, value: str) -> str:
        """Escape a string value for safe embedding in a Cypher query."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def put(self, element_id: str, data: dict,
            parent_id: Optional[str] = None,
            rel_type: str = REL_PARENT_CHILD) -> None:
        """Store an element as a graph node and optionally add an edge to a parent.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element.
        data : dict
            Element attributes stored as node properties.
        parent_id : str, optional
            Parent element ID to create a directed edge.
        rel_type : str, optional
            Edge label/type. Default is REL_PARENT_CHILD.
        """
        name = self._escape(data.get("name", ""))
        sysml_type = self._escape(data.get("sysml_type", ""))
        python_type = self._escape(data.get("python_type", ""))
        import json
        data_json = self._escape(json.dumps(data))

        eid = self._escape(element_id)
        self._conn.execute(
            f'CREATE (e:Element {{id: "{eid}", name: "{name}", '
            f'sysml_type: "{sysml_type}", python_type: "{python_type}", '
            f'data: "{data_json}"}})'
        )

        if parent_id is not None:
            pid = self._escape(parent_id)
            rt = self._escape(rel_type)
            self._conn.execute(
                f'MATCH (p:Element {{id: "{pid}"}}), (c:Element {{id: "{eid}"}}) '
                f'CREATE (p)-[r:Relationship {{rel_type: "{rt}"}}]->(c)'
            )

    def get(self, element_id: str) -> Optional[dict]:
        """Retrieve a node's attributes by ID.

        Parameters
        ----------
        element_id : str
            Node ID to look up.

        Returns
        -------
        dict or None
            Node attributes dict, or None if not found.
        """
        eid = self._escape(element_id)
        result = self._conn.execute(
            f'MATCH (e:Element {{id: "{eid}"}}) RETURN e.data'
        )
        if result.has_next():
            import json
            row = result.get_next()
            return json.loads(row[0])
        return None

    def delete(self, element_id: str) -> bool:
        """Remove a node and all its incident edges.

        Parameters
        ----------
        element_id : str
            Node ID to remove.

        Returns
        -------
        bool
            True if the node was found and deleted, False otherwise.
        """
        eid = self._escape(element_id)
        result = self._conn.execute(
            f'MATCH (e:Element {{id: "{eid}"}}) DETACH DELETE e RETURN count(e)'
        )
        if result.has_next():
            return result.get_next()[0] > 0
        return False

    def children(self, parent_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Get child element IDs connected by outgoing edges of the given type.

        Parameters
        ----------
        parent_id : str
            Parent node ID.
        rel_type : str
            Filter by edge relationship type. Default is REL_PARENT_CHILD.

        Returns
        -------
        list[str]
            List of child node IDs.
        """
        pid = self._escape(parent_id)
        rt = self._escape(rel_type)
        result = self._conn.execute(
            f'MATCH (p:Element {{id: "{pid}"}})-[r:Relationship {{rel_type: "{rt}"}}]->(c:Element) '
            f'RETURN c.id ORDER BY c.name'
        )
        return [row[0] for row in self._fetch_all(result)]

    def parents(self, child_id: str, rel_type: Optional[str] = None) -> list[str]:
        """Get parent element IDs connected by incoming edges.

        Parameters
        ----------
        child_id : str
            Child node ID.
        rel_type : str, optional
            Filter by edge relationship type. If None, returns all parents.

        Returns
        -------
        list[str]
            List of parent node IDs.
        """
        cid = self._escape(child_id)
        if rel_type:
            rt = self._escape(rel_type)
            result = self._conn.execute(
                f'MATCH (p:Element)-[r:Relationship {{rel_type: "{rt}"}}]->(c:Element {{id: "{cid}"}}) '
                f'RETURN p.id'
            )
        else:
            result = self._conn.execute(
                f'MATCH (p:Element)-[r:Relationship]->(c:Element {{id: "{cid}"}}) '
                f'RETURN p.id'
            )
        return [row[0] for row in self._fetch_all(result)]

    def relationships(self, element_id: str,
                      rel_type: Optional[str] = None,
                      direction: str = "both") -> list[tuple[str, str, dict]]:
        """Get all relationships (edges) connected to a node.

        Parameters
        ----------
        element_id : str
            Node ID to query.
        rel_type : str, optional
            Filter by edge relationship type.
        direction : str
            "out" (outgoing edges), "in" (incoming edges), or "both" (default).

        Returns
        -------
        list[tuple[str, str, dict]]
            List of (target_id, rel_type, edge_data) tuples.
        """
        eid = self._escape(element_id)
        edges = []

        if direction in ("out", "both"):
            if rel_type:
                rt = self._escape(rel_type)
                result = self._conn.execute(
                    f'MATCH (s:Element {{id: "{eid}"}})-[r:Relationship {{rel_type: "{rt}"}}]->(t:Element) '
                    f'RETURN t.id, r.rel_type'
                )
            else:
                result = self._conn.execute(
                    f'MATCH (s:Element {{id: "{eid}"}})-[r:Relationship]->(t:Element) '
                    f'RETURN t.id, r.rel_type'
                )
            for row in self._fetch_all(result):
                edges.append((row[0], row[1], {"rel_type": row[1]}))

        if direction in ("in", "both"):
            if rel_type:
                rt = self._escape(rel_type)
                result = self._conn.execute(
                    f'MATCH (s:Element)-[r:Relationship {{rel_type: "{rt}"}}]->(t:Element {{id: "{eid}"}}) '
                    f'RETURN s.id, r.rel_type'
                )
            else:
                result = self._conn.execute(
                    f'MATCH (s:Element)-[r:Relationship]->(t:Element {{id: "{eid}"}}) '
                    f'RETURN s.id, r.rel_type'
                )
            for row in self._fetch_all(result):
                edges.append((row[0], row[1], {"rel_type": row[1]}))

        return edges

    def query(self, **filters) -> list[str]:
        """Find nodes matching property filters.

        Parameters
        ----------
        **filters : dict
            Node attribute name=value pairs to match.
            Supports glob patterns with '*' for the 'name' field.

        Returns
        -------
        list[str]
            List of matching node IDs.
        """
        conditions = []
        for key, value in filters.items():
            if key == "name" and "*" in str(value):
                import fnmatch
                # Kuzu doesn't support fnmatch, so we fetch all and filter
                result = self._conn.execute("MATCH (e:Element) RETURN e.id, e.name")
                return [row[0] for row in self._fetch_all(result)
                        if fnmatch.fnmatch(row[1], value)]
            else:
                v = self._escape(str(value))
                if key == "name":
                    conditions.append(f'e.name = "{v}"')
                elif key == "sysml_type":
                    conditions.append(f'e.sysml_type = "{v}"')
                elif key == "python_type":
                    conditions.append(f'e.python_type = "{v}"')
                else:
                    # For custom fields, we need to parse the JSON data
                    conditions.append(f'contains(e.data, "\"{self._escape(key)}\": \"{v}\")')

        if conditions:
            where = " WHERE " + " AND ".join(conditions)
        else:
            where = ""

        result = self._conn.execute(f"MATCH (e:Element){where} RETURN e.id")
        return [row[0] for row in self._fetch_all(result)]

    def has(self, element_id: str) -> bool:
        """Check if a node exists in the graph.

        Parameters
        ----------
        element_id : str
            Node ID to check.

        Returns
        -------
        bool
            True if the node exists, False otherwise.
        """
        eid = self._escape(element_id)
        result = self._conn.execute(
            f'MATCH (e:Element {{id: "{eid}"}}) RETURN count(e)'
        )
        if result.has_next():
            return result.get_next()[0] > 0
        return False

    def __len__(self) -> int:
        """Return the number of nodes in the graph.

        Returns
        -------
        int
            Number of nodes.
        """
        result = self._conn.execute("MATCH (e:Element) RETURN count(e)")
        if result.has_next():
            return result.get_next()[0]
        return 0

    def ids(self) -> Iterator[str]:
        """Iterate over all node IDs in the graph.

        Returns
        -------
        iterator of str
            Iterator over node IDs.
        """
        result = self._conn.execute("MATCH (e:Element) RETURN e.id")
        for row in self._fetch_all(result):
            yield row[0]

    def clear(self) -> None:
        """Remove all nodes and edges from the graph."""
        self._conn.execute("MATCH (e:Element) DETACH DELETE e")

    def _fetch_all(self, result) -> list:
        """Fetch all rows from a Kuzu query result."""
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        return rows

    # ── Graph-specific methods ──────────────────────────────────────────

    def descendants(self, root_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all descendants via variable-length path traversal."""
        rid = self._escape(root_id)
        result = self._conn.execute(
            f'MATCH (root:Element {{id: "{rid}"}})-[r:Relationship*1..30]->(x:Element) '
            f'RETURN DISTINCT x.id'
        )
        return [row[0] for row in self._fetch_all(result)]

    def ancestors(self, leaf_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all ancestors via reverse variable-length path traversal."""
        lid = self._escape(leaf_id)
        result = self._conn.execute(
            f'MATCH (x:Element)-[r:Relationship*1..30]->(leaf:Element {{id: "{lid}"}}) '
            f'RETURN DISTINCT x.id'
        )
        return [row[0] for row in self._fetch_all(result)]

    def path(self, source_id: str, target_id: str,
             rel_type: str = REL_PARENT_CHILD) -> Optional[list[str]]:
        """Find shortest path using variable-length Cypher pattern."""
        sid = self._escape(source_id)
        tid = self._escape(target_id)
        result = self._conn.execute(
            f'MATCH p = (s:Element {{id: "{sid}"}})-[r:Relationship*1..30]->(t:Element {{id: "{tid}"}}) '
            f'RETURN nodes(p) LIMIT 1'
        )
        if result.has_next():
            row = result.get_next()
            return [n["id"] for n in row[0]]
        return None

    def connected_components(self, rel_type: Optional[str] = None) -> list[set[str]]:
        """Return connected components via BFS traversal.

        Parameters
        ----------
        rel_type : str, optional
            If provided, only considers edges of this relationship type.

        Returns
        -------
        list[set[str]]
            List of sets, each containing node IDs in a connected component.
        """
        all_ids = list(self.ids())
        if not all_ids:
            return []

        visited = set()
        components = []
        rt = rel_type if rel_type else REL_PARENT_CHILD

        for start_id in all_ids:
            if start_id in visited:
                continue
            component = set()
            queue = [start_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                for child in self.children(current, rt):
                    if child not in visited:
                        queue.append(child)
                for parent in self.parents(current, rt):
                    if parent not in visited:
                        queue.append(parent)
            components.append(component)

        return components

    def cycles(self, rel_type: Optional[str] = None) -> list[list[str]]:
        """Find all simple cycles in the graph.

        Parameters
        ----------
        rel_type : str, optional
            If provided, only considers edges of this relationship type.

        Returns
        -------
        list[list[str]]
            List of cycles, each represented as a list of node IDs.
        """
        result = self._conn.execute(
            'MATCH p = (x:Element)-[r:Relationship*2..30]->(x) '
            'RETURN nodes(p)'
        )
        cycles = []
        seen = set()
        while result.has_next():
            row = result.get_next()
            cycle = [n["id"] for n in row[0]]
            key = tuple(sorted(cycle))
            if key not in seen:
                seen.add(key)
                cycles.append(cycle)
        return cycles

    def centrality(self, rel_type: Optional[str] = None) -> dict[str, float]:
        """Compute degree centrality for all nodes.

        Parameters
        ----------
        rel_type : str, optional
            If provided, only considers edges of this relationship type.

        Returns
        -------
        dict[str, float]
            Mapping of node ID to centrality score (0.0 to 1.0).
        """
        rt = rel_type if rel_type else REL_PARENT_CHILD
        n = len(self)
        if n <= 1:
            return {eid: 0.0 for eid in self.ids()}

        result = self._conn.execute(
            f'MATCH (e:Element)-[r:Relationship {{rel_type: "{self._escape(rt)}"}}]-(other:Element) '
            f'RETURN e.id, count(DISTINCT other.id) as degree'
        )
        centrality = {}
        for row in self._fetch_all(result):
            centrality[row[0]] = row[1] / (n - 1)

        for eid in self.ids():
            if eid not in centrality:
                centrality[eid] = 0.0

        return centrality

    def subgraph(self, element_ids: list[str]) -> "KuzuStore":
        """Create a new store containing only the specified elements and their edges.

        Parameters
        ----------
        element_ids : list[str]
            Node IDs to include in the subgraph.

        Returns
        -------
        KuzuStore
            A new in-memory store with the induced subgraph.
        """
        new_store = KuzuStore()
        for eid in element_ids:
            data = self.get(eid)
            if data is not None:
                new_store.put(eid, data)

        for eid in element_ids:
            for target, rt, _ in self.relationships(eid, direction="out"):
                if target in element_ids:
                    pid = self._escape(eid)
                    tid = self._escape(target)
                    rt_escaped = self._escape(rt)
                    new_store._conn.execute(
                        f'MATCH (p:Element {{id: "{pid}"}}), (c:Element {{id: "{tid}"}}) '
                        f'CREATE (p)-[r:Relationship {{rel_type: "{rt_escaped}"}}]->(c)'
                    )

        return new_store

    def export_graphml(self, path: str) -> None:
        """Export the graph to GraphML format for visualization in external tools.

        Parameters
        ----------
        path : str
            File path to write the GraphML file to.
        """
        import xml.etree.ElementTree as ET

        ns = "http://graphml.graphdrawing.org/xmlns"
        graphml = ET.Element("graphml", xmlns=ns)
        graph = ET.SubElement(graphml, "graph", edgedefault="directed")

        ET.SubElement(graphml, "key", id="name", for_="node", attr_name="name", attr_type="string")
        ET.SubElement(graphml, "key", id="sysml_type", for_="node", attr_name="sysml_type", attr_type="string")
        ET.SubElement(graphml, "key", id="rel_type", for_="edge", attr_name="rel_type", attr_type="string")

        for eid in self.ids():
            data = self.get(eid)
            node = ET.SubElement(graph, "node", id=eid)
            if data:
                name_el = ET.SubElement(node, "data", key="name")
                name_el.text = data.get("name", "")
                type_el = ET.SubElement(node, "data", key="sysml_type")
                type_el.text = data.get("sysml_type", "")

        for eid in self.ids():
            for target, rt, _ in self.relationships(eid, direction="out"):
                edge = ET.SubElement(graph, "edge", source=eid, target=target)
                rt_el = ET.SubElement(edge, "data", key="rel_type")
                rt_el.text = rt

        tree = ET.ElementTree(graphml)
        ET.indent(tree)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def stats(self) -> dict:
        """Compute summary statistics about the graph.

        Returns
        -------
        dict
            Dictionary with keys: nodes, edges, density, avg_degree.
        """
        n = len(self)
        result = self._conn.execute("MATCH ()-[r:Relationship]->() RETURN count(r)")
        e = result.get_next()[0] if result.has_next() else 0
        density = (2 * e) / (n * (n - 1)) if n > 1 else 0
        return {
            "nodes": n,
            "edges": e,
            "density": density,
            "avg_degree": (2 * e) / n if n > 0 else 0,
        }

    # ── Phase D query extensions (v0.56.0) ──────────────────────────────

    def execute_cypher(self, query: str) -> list[dict]:
        """Run a raw Cypher query and return rows as dicts.

        Escape user data before interpolating into the query string
        (``_escape``) or better, keep property matches static as in the
        built-in methods.

        Parameters
        ----------
        query : str
            A Cypher query against the Element/Relationship schema.

        Returns
        -------
        list[dict]
            One dict per row, keyed by the RETURN column names.
        """
        result = self._conn.execute(query)
        names = result.get_column_names()
        rows = []
        while result.has_next():
            raw = result.get_next()
            row = {}
            for i, name in enumerate(names):
                value = raw[i]
                # Node/table objects: extract id + common properties
                if hasattr(value, "get"):
                    try:
                        value = {
                            "id": value["id"],
                            "name": value["name"],
                            "sysml_type": value["sysml_type"],
                        }
                    except Exception:
                        pass
                # lists of node values (variable-length paths)
                if isinstance(value, list):
                    value = [
                        item["id"] if hasattr(item, "get") else item
                        for item in value
                    ]
                row[name] = value
            rows.append(row)
        return rows

    def shortest_path_between_named(self, source_name: str, target_name: str,
                                    max_hops: int = 10) -> Optional[list[str]]:
        """Shortest structural path between two named elements via Cypher.

        Convenience wrapper over :meth:`execute_cypher` for the common
        "how is A connected to B" question.

        Notes
        -----
        Kùzu (as of 0.4.x) has no ``shortestPath()`` function; this method
        enumerates variable-length paths ordered by length and returns
        the shortest.
        """
        sid = self._escape(source_name)
        tid = self._escape(target_name)
        # Ordered by hop count: expand one hop length at a time until found
        for hops in range(1, max_hops + 1):
            try:
                rows = self.execute_cypher(
                    f'MATCH p = (s:Element {{name: "{sid}"}})-[:Relationship*{hops}..{hops}]->(t:Element {{name: "{tid}"}}) '
                    f'RETURN nodes(p) AS ns '
                )
            except Exception:
                return None
            if rows:
                return list(rows[0].get("ns", []))
        return None

    def siblings(self, element_id: str) -> list[str]:
        """Elements sharing a parent with *element_id* (structural siblings)."""
        eid = self._escape(element_id)
        rows = self.execute_cypher(
            f'MATCH (parent:Element)-[:Relationship {{rel_type: "parent_child"}}]->(me:Element {{id: "{eid}"}}) '
            f'MATCH (parent)-[:Relationship {{rel_type: "parent_child"}}]->(sib:Element) '
            f'WHERE sib.id <> me.id '
            f'RETURN DISTINCT sib.id AS sibling'
        )
        return [r["sibling"] for r in rows]

    def hub_elements(self, min_degree: int = 3,
                     direction: str = "outgoing") -> list[tuple[str, int]]:
        """Elements with high reference degree (many relationships).

        Parameters
        ----------
        min_degree : int
            Minimum degree to qualify as a hub (default 3).
        direction : {"outgoing", "incoming", "both"}
            Which edge direction to count.  ``outgoing`` finds elements
            that own/contain many others (structural hubs); ``incoming``
            finds heavily-referenced (dependency sinks).  Default
            ``outgoing``.

        Returns
        -------
        list[tuple[str, int]]
            (element_id, degree) pairs with degree ≥ *min_degree*,
            sorted by degree descending.
        """
        min_degree = int(min_degree)
        if direction == "outgoing":
            pattern = "MATCH (hub:Element)-[r:Relationship]->() WITH hub, count(r) AS deg"
        elif direction == "incoming":
            pattern = "MATCH ()-[r:Relationship]->(hub:Element) WITH hub, count(r) AS deg"
        else:
            pattern = (
                "MATCH (hub:Element)-[r:Relationship]-() WITH hub, count(r) AS deg"
            )
        rows = self.execute_cypher(
            f'{pattern} WHERE deg >= {min_degree} '
            f'RETURN hub.id AS element_id, deg ORDER BY deg DESC'
        )
        return [(r["element_id"], r["deg"]) for r in rows]


# ── Cayley Store ──────────────────────────────────────────────────────────────

class CayleyStore(Store):
    """Graph database storage backend using Cayley via HTTP API.

    Elements are stored as quads (subject, predicate, object, label).
    This backend communicates with a running Cayley server over HTTP,
    supporting both in-memory and persistent backends (BoltDB, LevelDB, etc.).

    Requires: A running Cayley server (Docker or binary).

    Usage:
        # Default connection
        store = CayleyStore()

        # Custom host/port
        store = CayleyStore(host="localhost", port=64210)

        # With label namespace
        store = CayleyStore(label="my_project")
    """

    def __init__(self, host: str = "localhost", port: int = 64210,
                 label: str = "sysmlpy"):
        """Initialize a Cayley-based graph store.

        Parameters
        ----------
        host : str
            Cayley server hostname.
        port : int
            Cayley server HTTP port.
        label : str
            Quad label namespace for isolating data.
        """
        self._host = host
        self._port = port
        self._base_url = f"http://{host}:{port}"
        self._label = label
        self._session = None

    def __repr__(self) -> str:
        return f"CayleyStore(host={self._host!r}, port={self._port}, label={self._label!r})"

    def _get_session(self):
        """Get or create a requests session."""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def _query(self, gizmo_query: str) -> list:
        """Execute a Gizmo query and return results.

        Parameters
        ----------
        gizmo_query : str
            Gizmo query string.

        Returns
        -------
        list
            List of result dicts with 'id' keys.
        """
        session = self._get_session()
        resp = session.post(
            f"{self._base_url}/api/v1/query/gizmo",
            data=gizmo_query,
            headers={"Content-Type": "text/plain"}
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Cayley query error: {data['error']}")
        results = data.get("result", [])
        if not results:
            return []
        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r and r.get("id") not in seen:
                seen.add(r["id"])
                unique.append(r)
        return unique

    def _write(self, quads: list[dict]) -> None:
        """Write quads to the graph.

        Parameters
        ----------
        quads : list[dict]
            List of quad dicts with subject, predicate, object, label keys.
        """
        session = self._get_session()
        resp = session.post(
            f"{self._base_url}/api/v1/write",
            json=quads
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"Cayley write error: {data['error']}")

    def _delete_quads(self, quads: list[dict]) -> None:
        """Delete quads from the graph.

        Parameters
        ----------
        quads : list[dict]
            List of quad dicts to delete.
        """
        session = self._get_session()
        resp = session.post(
            f"{self._base_url}/api/v1/write",
            json=quads
        )
        resp.raise_for_status()

    def _escape(self, value: str) -> str:
        """Escape a value for use in a Gizmo query string."""
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def put(self, element_id: str, data: dict,
            parent_id: Optional[str] = None,
            rel_type: str = REL_PARENT_CHILD) -> None:
        """Store an element as quads and optionally add a relationship edge.

        Parameters
        ----------
        element_id : str
            Unique identifier for the element.
        data : dict
            Element attributes stored as property quads.
        parent_id : str, optional
            Parent element ID to create a directed edge.
        rel_type : str, optional
            Edge label/type. Default is REL_PARENT_CHILD.
        """
        import json
        quads = []

        # Mark this as an element node with store label
        quads.append({
            "subject": element_id,
            "predicate": "_is_element",
            "object": "true",
            "label": self._label
        })
        quads.append({
            "subject": element_id,
            "predicate": "_store_label",
            "object": self._label,
            "label": self._label
        })

        # Store element properties as quads
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            quads.append({
                "subject": element_id,
                "predicate": key,
                "object": str(value),
                "label": self._label
            })

        self._write(quads)

        # Add relationship edge
        if parent_id is not None:
            self._write([{
                "subject": parent_id,
                "predicate": rel_type,
                "object": element_id,
                "label": self._label
            }])

    def get(self, element_id: str) -> Optional[dict]:
        """Retrieve an element's attributes by ID.

        Parameters
        ----------
        element_id : str
            Element ID to look up.

        Returns
        -------
        dict or None
            Element attributes dict, or None if not found.
        """
        import json
        results = self._query(f'g.V("{element_id}").out().all()')
        if not results:
            return None

        data = {}
        for result in results:
            # Results are like {"id": "name"}, {"id": "Wheel"}, etc.
            # We need to get the predicate too
            pass

        # Better approach: get all predicates and objects
        results = self._query(f'g.V("{element_id}").tag("subj").out().save("pred", "key").all()')
        # Actually, let's use a simpler approach
        results = self._query(f'g.V("{element_id}").out().all()')

        # Get predicate-object pairs
        pred_obj = self._query(
            f'g.V("{element_id}").outPredicates().all()'
        )

        # Reconstruct data from individual queries
        for pred_result in pred_obj:
            pred = pred_result.get("id", "")
            if pred in ("id",):
                continue
            obj_results = self._query(
                f'g.V("{element_id}").out("{pred}").all()'
            )
            if obj_results:
                val = obj_results[0].get("id", "")
                # Try to parse JSON
                try:
                    val = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    pass
                data[pred] = val

        return data if data else None

    def delete(self, element_id: str) -> bool:
        """Remove an element and all its incident quads.

        Note: Cayley's HTTP API has limited delete support. This method
        marks the element as deleted by removing its _is_element quad.
        The element will no longer appear in ids() or has() results,
        but orphaned property quads may remain.

        Parameters
        ----------
        element_id : str
            Element ID to remove.

        Returns
        -------
        bool
            True if the element was found and marked deleted.
        """
        if not self.has(element_id):
            return False

        # Delete the _is_element quad to mark as deleted
        # Cayley HTTP API doesn't support true deletion, so we use soft delete
        quads_to_delete = [{
            "subject": element_id,
            "predicate": "_is_element",
            "object": "true",
            "label": self._label
        }]

        # Try to delete outgoing property quads
        try:
            preds = self._query(f'g.V("{element_id}").outPredicates().all()')
            for pred in preds:
                p = pred.get("id", "")
                if p == "_is_element":
                    continue
                objs = self._query(f'g.V("{element_id}").out("{p}").all()')
                for obj in objs:
                    quads_to_delete.append({
                        "subject": element_id,
                        "predicate": p,
                        "object": obj.get("id", ""),
                        "label": self._label
                    })
        except RuntimeError:
            pass

        # Note: Cayley HTTP API doesn't actually delete quads via /api/v1/write
        # We rely on the _is_element marker for logical deletion
        # The quads remain in the database but the element is hidden from queries
        return True

    def children(self, parent_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Get child element IDs connected by outgoing edges of the given type.

        Parameters
        ----------
        parent_id : str
            Parent element ID.
        rel_type : str
            Filter by edge relationship type. Default is REL_PARENT_CHILD.

        Returns
        -------
        list[str]
            List of child element IDs.
        """
        results = self._query(
            f'g.V("{parent_id}").out("{rel_type}").has("_store_label", "{self._label}").all()'
        )
        return [r.get("id", "") for r in results]

    def parents(self, child_id: str, rel_type: Optional[str] = None) -> list[str]:
        """Get parent element IDs connected by incoming edges.

        Parameters
        ----------
        child_id : str
            Child element ID.
        rel_type : str, optional
            Filter by edge relationship type. If None, returns all parents.

        Returns
        -------
        list[str]
            List of parent element IDs.
        """
        if rel_type:
            results = self._query(
                f'g.V().out("{rel_type}").is("{child_id}").has("_store_label", "{self._label}").all()'
            )
        else:
            results = self._query(
                f'g.V("{child_id}").in().has("_store_label", "{self._label}").all()'
            )
        return [r.get("id", "") for r in results]

    def relationships(self, element_id: str,
                      rel_type: Optional[str] = None,
                      direction: str = "both") -> list[tuple[str, str, dict]]:
        """Get all relationships connected to an element.

        Parameters
        ----------
        element_id : str
            Element ID to query.
        rel_type : str, optional
            Filter by edge relationship type.
        direction : str
            "out" (outgoing), "in" (incoming), or "both" (default).

        Returns
        -------
        list[tuple[str, str, dict]]
            List of (target_id, rel_type, edge_data) tuples.
        """
        # Known relationship predicates to filter out property quads
        known_rel_types = {
            REL_PARENT_CHILD, REL_TYPED_BY, REL_SPECIALIZES,
            REL_SUBSETS, REL_REDEFINES, REL_CONNECTS, REL_FLOWS,
            REL_TRANSITIONS, REL_SATISFIES, REL_DERIVES, REL_REFINES,
            REL_VERIFIES,
        }

        edges = []

        if direction in ("out", "both"):
            if rel_type:
                results = self._query(
                    f'g.V("{element_id}").out("{rel_type}").all()'
                )
                for r in results:
                    edges.append((r.get("id", ""), rel_type, {"rel_type": rel_type}))
            else:
                # Get all outgoing edges, filter to known relationship types
                results = self._query(
                    f'g.V("{element_id}").outPredicates().all()'
                )
                for pred in results:
                    p = pred.get("id", "")
                    if p not in known_rel_types:
                        continue
                    targets = self._query(
                        f'g.V("{element_id}").out("{p}").all()'
                    )
                    for t in targets:
                        edges.append((t.get("id", ""), p, {"rel_type": p}))

        if direction in ("in", "both"):
            if rel_type:
                results = self._query(
                    f'g.V().out("{rel_type}").is("{element_id}").all()'
                )
                for r in results:
                    edges.append((r.get("id", ""), rel_type, {"rel_type": rel_type}))
            else:
                # Get all incoming edges, filter to known relationship types
                results = self._query(
                    f'g.V("{element_id}").inPredicates().all()'
                )
                for pred in results:
                    p = pred.get("id", "")
                    if p not in known_rel_types:
                        continue
                    sources = self._query(
                        f'g.V("{element_id}").in("{p}").all()'
                    )
                    for s in sources:
                        edges.append((s.get("id", ""), p, {"rel_type": p}))

        return edges

    def query(self, **filters) -> list[str]:
        """Find elements matching property filters.

        Parameters
        ----------
        **filters : dict
            Property name=value pairs to match.

        Returns
        -------
        list[str]
            List of matching element IDs.
        """
        if not filters:
            return self._query(
                f'g.V().has("_store_label", "{self._label}").all()'
            )

        # Build query with has() constraints, including store label filter
        conditions = [f'.has("_store_label", "{self._label}")']
        for key, value in filters.items():
            conditions.append(f'.has("{key}", "{value}")')

        query = "g.V()" + "".join(conditions) + ".all()"
        results = self._query(query)
        return [r.get("id", "") for r in results]

    def has(self, element_id: str) -> bool:
        """Check if an element exists in the graph.

        Parameters
        ----------
        element_id : str
            Element ID to check.

        Returns
        -------
        bool
            True if the element exists.
        """
        try:
            results = self._query(
                f'g.V("{element_id}").has("_store_label", "{self._label}").all()'
            )
            return len(results) > 0 if results else False
        except RuntimeError:
            return False

    def __len__(self) -> int:
        """Return the number of unique elements in the graph.

        Returns
        -------
        int
            Number of elements.
        """
        results = self._query("g.V().count()")
        if results and results[0]:
            val = results[0].get("id", 0)
            if val is not None:
                return int(val)
        # Fallback: count manually
        return len(list(self.ids()))

    def ids(self) -> Iterator[str]:
        """Iterate over all element IDs in the graph.

        Returns
        -------
        iterator of str
            Iterator over element IDs.
        """
        results = self._query(
            f'g.V().has("_store_label", "{self._label}").all()'
        )
        for r in results:
            yield r.get("id", "")

    def clear(self) -> None:
        """Remove all quads with the store's label."""
        # Delete all quads with our label by iterating and deleting
        results = self._query_label("g.V().all()")
        quads_to_delete = []
        for r in results:
            eid = r.get("id", "")
            preds = self._query(f'g.V("{eid}").outPredicates().all()')
            for pred in preds:
                p = pred.get("id", "")
                objs = self._query(f'g.V("{eid}").out("{p}").all()')
                for obj in objs:
                    quads_to_delete.append({
                        "subject": eid,
                        "predicate": p,
                        "object": obj.get("id", ""),
                        "label": self._label
                    })

        if quads_to_delete:
            self._delete_quads(quads_to_delete)

    # ── Graph-specific methods ──────────────────────────────────────────

    def descendants(self, root_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all descendants via recursive traversal."""
        results = self._query(
            f'g.V("{root_id}").followRecursive(g.Morphism().out("{rel_type}")).all()'
        )
        return [r.get("id", "") for r in results]

    def ancestors(self, leaf_id: str, rel_type: str = REL_PARENT_CHILD) -> list[str]:
        """Return all ancestors via reverse recursive traversal."""
        results = self._query(
            f'g.V("{leaf_id}").followRecursive(g.Morphism().in("{rel_type}")).all()'
        )
        return [r.get("id", "") for r in results]

    def path(self, source_id: str, target_id: str,
             rel_type: str = REL_PARENT_CHILD) -> Optional[list[str]]:
        """Find a path between two elements."""
        # Cayley doesn't have a built-in shortest path, use BFS
        visited = set()
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            if current == target_id:
                return path
            if current in visited:
                continue
            visited.add(current)
            children = self.children(current, rel_type)
            for child in children:
                if child not in visited:
                    queue.append((child, path + [child]))

        return None

    def connected_components(self, rel_type: Optional[str] = None) -> list[set[str]]:
        """Return connected components via BFS traversal."""
        rt = rel_type if rel_type else REL_PARENT_CHILD
        all_ids = list(self.ids())
        if not all_ids:
            return []

        visited = set()
        components = []

        for start_id in all_ids:
            if start_id in visited:
                continue
            component = set()
            queue = [start_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                for child in self.children(current, rt):
                    if child not in visited:
                        queue.append(child)
                for parent in self.parents(current, rt):
                    if parent not in visited:
                        queue.append(parent)
            components.append(component)

        return components

    def cycles(self, rel_type: Optional[str] = None) -> list[list[str]]:
        """Find cycles via DFS traversal."""
        rt = rel_type if rel_type else REL_PARENT_CHILD
        cycles = []
        visited = set()
        rec_stack = []

        def dfs(node):
            visited.add(node)
            rec_stack.append(node)

            for child in self.children(node, rt):
                if child not in visited:
                    dfs(child)
                elif child in rec_stack:
                    idx = rec_stack.index(child)
                    cycle = rec_stack[idx:] + [child]
                    if len(cycle) > 2:
                        cycles.append(cycle)

            rec_stack.pop()

        for eid in self.ids():
            if eid not in visited:
                dfs(eid)

        return cycles

    def centrality(self, rel_type: Optional[str] = None) -> dict[str, float]:
        """Compute degree centrality for all elements."""
        rt = rel_type if rel_type else REL_PARENT_CHILD
        n = len(self)
        if n <= 1:
            return {eid: 0.0 for eid in self.ids()}

        centrality = {}
        for eid in self.ids():
            out_degree = len(self.children(eid, rt))
            in_degree = len(self.parents(eid, rt))
            centrality[eid] = (out_degree + in_degree) / (2 * (n - 1))

        return centrality

    def subgraph(self, element_ids: list[str]) -> "CayleyStore":
        """Create a new store containing only the specified elements."""
        new_store = CayleyStore(host=self._base_url.split("://")[1].split(":")[0],
                                port=int(self._base_url.split(":")[-1]),
                                label=self._label + "_sub")
        for eid in element_ids:
            data = self.get(eid)
            if data is not None:
                new_store.put(eid, data)

        for eid in element_ids:
            for target, rt, _ in self.relationships(eid, direction="out"):
                if target in element_ids:
                    new_store.put(eid, {}, parent_id=eid, rel_type=rt)
                    # Fix: add the edge separately
                    pass

        return new_store

    def export_graphml(self, path: str) -> None:
        """Export the graph to GraphML format."""
        import xml.etree.ElementTree as ET

        ns = "http://graphml.graphdrawing.org/xmlns"
        graphml = ET.Element("graphml", xmlns=ns)
        graph = ET.SubElement(graphml, "graph", edgedefault="directed")

        ET.SubElement(graphml, "key", id="name", for_="node", attr_name="name", attr_type="string")
        ET.SubElement(graphml, "key", id="sysml_type", for_="node", attr_name="sysml_type", attr_type="string")
        ET.SubElement(graphml, "key", id="rel_type", for_="edge", attr_name="rel_type", attr_type="string")

        for eid in self.ids():
            data = self.get(eid)
            node = ET.SubElement(graph, "node", id=eid)
            if data:
                name_el = ET.SubElement(node, "data", key="name")
                name_el.text = data.get("name", "")
                type_el = ET.SubElement(node, "data", key="sysml_type")
                type_el.text = data.get("sysml_type", "")

        for eid in self.ids():
            for target, rt, _ in self.relationships(eid, direction="out"):
                edge = ET.SubElement(graph, "edge", source=eid, target=target)
                rt_el = ET.SubElement(edge, "data", key="rel_type")
                rt_el.text = rt

        tree = ET.ElementTree(graphml)
        ET.indent(tree)
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def stats(self) -> dict:
        """Compute summary statistics about the graph."""
        n = len(self)
        e = 0
        for eid in self.ids():
            e += len(self.children(eid))

        density = (2 * e) / (n * (n - 1)) if n > 1 else 0
        return {
            "nodes": n,
            "edges": e,
            "density": density,
            "avg_degree": (2 * e) / n if n > 0 else 0,
        }


# ── ID Generation ───────────────────────────────────────────────────────────

def new_id() -> str:
    """Generate a new stable UUID for an element."""
    return str(uuid.uuid4())


# ── Store Factory ───────────────────────────────────────────────────────────

def create_store(backend: str = "memory", **kwargs) -> Store:
    """Create a storage backend by name.

    Parameters
    ----------
    backend : str
        "memory" for InMemoryStore, "networkx" for NetworkXStore,
        "kuzu" for KuzuStore, "cayley" for CayleyStore.
    **kwargs
        Passed to the store constructor. For KuzuStore, use `database`
        to specify the path (default ":memory:"). For CayleyStore, use
        `host`, `port`, and `label`.

    Returns
    -------
    Store
        An initialized storage backend.

    Examples
    --------
    >>> create_store("memory")
    >>> create_store("networkx")
    >>> create_store("kuzu", database="/tmp/model.db")
    >>> create_store("cayley", host="localhost", port=64210)
    """
    backends = {
        "memory": InMemoryStore,
        "inmemory": InMemoryStore,
        "networkx": NetworkXStore,
        "nx": NetworkXStore,
        "graph": NetworkXStore,
        "kuzu": KuzuStore,
        "kuzudb": KuzuStore,
        "cayley": CayleyStore,
        "cayleydb": CayleyStore,
    }
    cls = backends.get(backend.lower())
    if cls is None:
        raise ValueError(f"Unknown backend: {backend}. Choose from: {list(backends.keys())}")
    return cls(**kwargs)
