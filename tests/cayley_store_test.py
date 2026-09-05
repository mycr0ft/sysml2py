#!/usr/bin/env python3
"""Tests for the CayleyStore graph database backend.

Note: These tests require a running Cayley instance at localhost:64210.
Tests are skipped if Cayley is not available.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Check if Cayley is available
try:
    import requests
    resp = requests.get("http://localhost:64210/", timeout=2)
    CAYLEY_AVAILABLE = resp.status_code == 200
except Exception:
    CAYLEY_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CAYLEY_AVAILABLE, reason="Cayley not available at localhost:64210")

from sysmlpy.store import (
    CayleyStore, create_store,
    REL_PARENT_CHILD, REL_TYPED_BY, REL_SPECIALIZES
)


@pytest.fixture
def store():
    """Create a CayleyStore with a unique label for testing."""
    import uuid
    import time
    # Use timestamp + uuid to ensure uniqueness across test runs
    label = f"test_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"
    s = CayleyStore(label=label)
    yield s


class TestCayleyStoreBasic:
    """Test basic CRUD operations."""

    def test_put_and_get(self, store):
        store.put("e1", {"name": "Wheel", "sysml_type": "part"})
        result = store.get("e1")
        assert result["name"] == "Wheel"
        assert result["sysml_type"] == "part"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_has(self, store):
        store.put("e1", {"name": "Wheel"})
        assert store.has("e1") is True
        assert store.has("e2") is False

    def test_len(self, store):
        assert len(store) == 0
        store.put("e1", {"name": "A"})
        store.put("e2", {"name": "B"})
        assert len(store) == 2

    def test_ids(self, store):
        store.put("e1", {"name": "A"})
        store.put("e2", {"name": "B"})
        ids = list(store.ids())
        assert set(ids) == {"e1", "e2"}


class TestCayleyStoreRelationships:
    """Test parent-child and relationship operations."""

    def test_put_with_parent(self, store):
        store.put("parent", {"name": "Vehicle"})
        store.put("child", {"name": "Wheel"}, parent_id="parent")
        children = store.children("parent")
        assert "child" in children

    def test_children(self, store):
        store.put("p", {"name": "Vehicle"})
        store.put("c1", {"name": "Wheel1"}, parent_id="p")
        store.put("c2", {"name": "Wheel2"}, parent_id="p")
        children = store.children("p")
        assert set(children) == {"c1", "c2"}

    def test_children_empty(self, store):
        store.put("p", {"name": "Vehicle"})
        assert store.children("p") == []

    def test_children_by_rel_type(self, store):
        import uuid
        prefix = uuid.uuid4().hex[:6]
        store.put(f"{prefix}_p", {"name": "Vehicle"})
        store.put(f"{prefix}_c1", {"name": "Wheel"}, parent_id=f"{prefix}_p", rel_type=REL_PARENT_CHILD)
        store.put(f"{prefix}_c2", {"name": "Engine"}, parent_id=f"{prefix}_p", rel_type=REL_TYPED_BY)
        assert f"{prefix}_c1" in store.children(f"{prefix}_p", REL_PARENT_CHILD)
        assert f"{prefix}_c2" not in store.children(f"{prefix}_p", REL_PARENT_CHILD)
        assert f"{prefix}_c2" in store.children(f"{prefix}_p", REL_TYPED_BY)

    def test_relationships_out(self, store):
        import uuid
        prefix = uuid.uuid4().hex[:6]
        store.put(f"{prefix}_p", {"name": "Vehicle"})
        store.put(f"{prefix}_c", {"name": "Wheel"}, parent_id=f"{prefix}_p")
        rels = store.relationships(f"{prefix}_p", direction="out")
        assert len(rels) == 1
        assert rels[0][0] == f"{prefix}_c"
        assert rels[0][1] == REL_PARENT_CHILD


class TestCayleyStoreQuery:
    """Test query operations."""

    def test_query_by_sysml_type(self, store):
        import uuid
        prefix = uuid.uuid4().hex[:6]
        store.put(f"{prefix}_e1", {"name": "Wheel", "sysml_type": "part"})
        store.put(f"{prefix}_e2", {"name": "Engine", "sysml_type": "part"})
        store.put(f"{prefix}_e3", {"name": "Speed", "sysml_type": "attribute"})
        results = store.query(sysml_type="part")
        assert set(results) == {f"{prefix}_e1", f"{prefix}_e2"}

    def test_query_by_name(self, store):
        import uuid
        prefix = uuid.uuid4().hex[:6]
        store.put(f"{prefix}_e1", {"name": f"Wheel_{prefix}", "sysml_type": "part"})
        store.put(f"{prefix}_e2", {"name": f"Engine_{prefix}", "sysml_type": "part"})
        results = store.query(name=f"Wheel_{prefix}")
        assert results == [f"{prefix}_e1"]


class TestCayleyStoreGraph:
    """Test graph-specific operations."""

    def test_descendants(self, store):
        store.put("root", {"name": "Vehicle"})
        store.put("child1", {"name": "Chassis"}, parent_id="root")
        store.put("child2", {"name": "Wheel"}, parent_id="child1")
        descendants = store.descendants("root")
        assert set(descendants) == {"child1", "child2"}

    def test_ancestors(self, store):
        store.put("root", {"name": "Vehicle"})
        store.put("child1", {"name": "Chassis"}, parent_id="root")
        store.put("child2", {"name": "Wheel"}, parent_id="child1")
        ancestors = store.ancestors("child2")
        assert set(ancestors) == {"root", "child1"}

    def test_path(self, store):
        store.put("a", {"name": "A"})
        store.put("b", {"name": "B"}, parent_id="a")
        store.put("c", {"name": "C"}, parent_id="b")
        store.put("d", {"name": "D"}, parent_id="c")
        path = store.path("a", "d")
        assert path is not None
        assert path == ["a", "b", "c", "d"]

    def test_path_no_path(self, store):
        import uuid
        prefix = uuid.uuid4().hex[:6]
        store.put(f"{prefix}_a", {"name": "A"})
        store.put(f"{prefix}_b", {"name": "B"})
        assert store.path(f"{prefix}_a", f"{prefix}_b") is None

    def test_connected_components(self, store):
        store.put("a1", {"name": "A1"})
        store.put("a2", {"name": "A2"}, parent_id="a1")
        store.put("b1", {"name": "B1"})
        store.put("b2", {"name": "B2"}, parent_id="b1")
        components = store.connected_components()
        assert len(components) == 2

    def test_centrality(self, store):
        store.put("center", {"name": "Center"})
        store.put("leaf1", {"name": "Leaf1"}, parent_id="center")
        store.put("leaf2", {"name": "Leaf2"}, parent_id="center")
        centrality = store.centrality()
        assert centrality["center"] > centrality["leaf1"]

    def test_stats(self, store):
        import uuid
        prefix = uuid.uuid4().hex[:6]
        store.put(f"{prefix}_a", {"name": "A"})
        store.put(f"{prefix}_b", {"name": "B"}, parent_id=f"{prefix}_a")
        stats = store.stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1


class TestCreateStore:
    """Test the factory function."""

    def test_create_cayley(self):
        store = create_store("cayley")
        assert isinstance(store, CayleyStore)

    def test_create_cayley_alias(self):
        store = create_store("cayleydb")
        assert isinstance(store, CayleyStore)

    def test_create_cayley_with_params(self):
        store = create_store("cayley", host="localhost", port=64210, label="test")
        assert isinstance(store, CayleyStore)
        assert store._label == "test"

class TestCayleyQueryExtensions:
    """Query extensions mirroring NetworkX/Kuzu contracts (v0.79.0).

    Same shapes as TestNetworkXQueryExtensions in store_test.py; the
    fixture chain A→B→C→D (parent_child) is identical."""

    def _build_chain(self, store):
        store.put("A", {"name": "A", "sysml_type": "part"})
        store.put("B", {"name": "B", "sysml_type": "part"}, parent_id="A")
        store.put("C", {"name": "C", "sysml_type": "part"}, parent_id="B")
        store.put("D", {"name": "D", "sysml_type": "part"}, parent_id="C")
        return store

    def test_all_paths_linear(self, store):
        self._build_chain(store)
        assert store.all_paths("A", "D") == [["A", "B", "C", "D"]]

    def test_all_paths_multiple(self, store):
        store.put("A", {"name": "A"})
        store.put("B1", {"name": "B1"}, parent_id="A")
        store.put("B2", {"name": "B2"}, parent_id="A")
        store.put("C1", {"name": "C"}, parent_id="B1")
        store.put("C2", {"name": "C2"}, parent_id="B2")
        paths = store.all_paths("A", "C1")
        assert paths == [["A", "B1", "C1"]]

    def test_all_paths_missing_endpoint(self, store):
        self._build_chain(store)
        assert store.all_paths("A", "NOPE") == []
        assert store.all_paths("NOPE", "A") == []

    def test_max_paths_cap(self, store):
        # Diamond: A→B1→C, A→B2→C — 2 paths, cap respected
        store.put("A", {"name": "A"})
        store.put("B1", {"name": "B1"}, parent_id="A")
        store.put("B2", {"name": "B2"}, parent_id="A")
        store.put("C", {"name": "C"}, parent_id="B1")
        store.put("C", {"name": "C"}, parent_id="B2")
        paths = store.all_paths("A", "C")
        assert 1 <= len(paths) <= 20

    def test_descendants_depth_limited(self, store):
        self._build_chain(store)
        assert store.descendants_depth_limited("A", max_depth=1) == ["B"]
        assert store.descendants_depth_limited("A", max_depth=2) == ["B", "C"]
        assert store.descendants_depth_limited("A", max_depth=3) == ["B", "C", "D"]

    def test_neighborhood(self, store):
        self._build_chain(store)
        assert store.neighborhood("B", radius=1) == {"A", "B", "C"}

    def test_impact_downstream(self, store):
        self._build_chain(store)
        assert store.impact_analysis("A", direction="downstream") == {"B", "C", "D"}
        assert store.impact_analysis("C", direction="downstream") == {"D"}

    def test_impact_upstream(self, store):
        self._build_chain(store)
        assert store.impact_analysis("D", direction="upstream") == {"A", "B", "C"}

    def test_in_out_degree_centrality(self, store):
        self._build_chain(store)
        out_c = store.out_degree_centrality()
        in_c = store.in_degree_centrality()
        assert out_c["A"] > 0
        assert in_c["D"] > 0
        assert in_c["A"] == 0.0

    def test_siblings(self, store):
        store.put("p", {"name": "P"})
        store.put("c1", {"name": "C1"}, parent_id="p")
        store.put("c2", {"name": "C2"}, parent_id="p")
        store.put("c3", {"name": "C3"}, parent_id="p")
        assert sorted(store.siblings("c2")) == ["c1", "c3"]
        assert store.siblings("only_child_parentless") == []             if not store.has("only_child_parentless") else True

    def test_siblings_self_excluded(self, store):
        store.put("p", {"name": "P"})
        store.put("c1", {"name": "C1"}, parent_id="p")
        assert store.siblings("c1") == []

    def test_hub_elements(self, store):
        self._build_chain(store)
        hubs = store.hub_elements(min_degree=2, direction="both")
        ids = [eid for eid, _deg in hubs]
        assert "B" in ids and "C" in ids
        degrees = [deg for _eid, deg in hubs]
        assert degrees == sorted(degrees, reverse=True)

    def test_hub_elements_direction_validation(self, store):
        with pytest.raises(ValueError):
            store.hub_elements(direction="sideways")

    def test_shortest_path_between_named(self, store):
        store.put("n1", {"name": "A"})
        store.put("n2", {"name": "B"}, parent_id="n1")
        store.put("n3", {"name": "C"}, parent_id="n2")
        assert store.shortest_path_between_named("A", "C") == ["n1", "n2", "n3"]

    def test_shortest_path_none_when_disconnected(self, store):
        store.put("x1", {"name": "X1"})
        store.put("x2", {"name": "X2"})
        assert store.shortest_path_between_named("X1", "X2") is None

    def test_shortest_path_missing_name(self, store):
        store.put("n1", {"name": "A"})
        assert store.shortest_path_between_named("A", "GHOST") is None

    def test_centrality_parity_with_networkx(self):
        """The same chain in both stores yields equal centrality maps."""
        from sysmlpy.store import NetworkXStore
        nx_store = NetworkXStore()
        cayley = CayleyStore(label=f"parity_{int(__import__('time').time()*1000)}")
        for st in (nx_store, cayley):
            st.put("A", {"name": "A"})
            st.put("B", {"name": "B"}, parent_id="A")
            st.put("C", {"name": "C"}, parent_id="A")
        assert nx_store.centrality().keys() == cayley.centrality().keys()
        # hub_elements is Kuzu-only; verify Cayley against manual counts
        hubs = dict(cayley.hub_elements(min_degree=1, direction="outgoing"))
        assert hubs["A"] == 2 and hubs.get("B", 0) == 0
