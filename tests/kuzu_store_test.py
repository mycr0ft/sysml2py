#!/usr/bin/env python3
"""Tests for the KuzuStore graph database backend."""

import pytest
import json

kuzu = pytest.importorskip("kuzu")

from sysmlpy.store import (
    KuzuStore, create_store,
    REL_PARENT_CHILD, REL_TYPED_BY, REL_SPECIALIZES
)


@pytest.fixture
def store():
    """Create an in-memory KuzuStore for testing."""
    return KuzuStore()


class TestKuzuStoreBasic:
    """Test basic CRUD operations."""

    def test_put_and_get(self, store):
        store.put("e1", {"name": "Wheel", "sysml_type": "part"})
        result = store.get("e1")
        assert result["name"] == "Wheel"
        assert result["sysml_type"] == "part"

    def test_get_nonexistent(self, store):
        assert store.get("nonexistent") is None

    def test_delete(self, store):
        store.put("e1", {"name": "Wheel"})
        assert store.delete("e1") is True
        assert store.get("e1") is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nonexistent") is False

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

    def test_clear(self, store):
        store.put("e1", {"name": "A"})
        store.put("e2", {"name": "B"})
        store.clear()
        assert len(store) == 0


class TestKuzuStoreRelationships:
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
        assert store.children("nonexistent") == []

    def test_children_by_rel_type(self, store):
        store.put("p", {"name": "Vehicle"})
        store.put("c1", {"name": "Wheel"}, parent_id="p", rel_type=REL_PARENT_CHILD)
        store.put("c2", {"name": "Engine"}, parent_id="p", rel_type=REL_TYPED_BY)
        assert "c1" in store.children("p", REL_PARENT_CHILD)
        assert "c2" not in store.children("p", REL_PARENT_CHILD)
        assert "c2" in store.children("p", REL_TYPED_BY)

    def test_parents(self, store):
        store.put("p", {"name": "Vehicle"})
        store.put("c", {"name": "Wheel"}, parent_id="p")
        parents = store.parents("c")
        assert "p" in parents

    def test_parents_by_rel_type(self, store):
        store.put("p1", {"name": "Vehicle"})
        store.put("p2", {"name": "WheelDef"})
        store.put("c1", {"name": "Wheel"}, parent_id="p1", rel_type=REL_PARENT_CHILD)
        store.put("c2", {"name": "Tire"}, parent_id="p2", rel_type=REL_TYPED_BY)
        parents = store.parents("c1", REL_PARENT_CHILD)
        assert "p1" in parents
        parents2 = store.parents("c2", REL_TYPED_BY)
        assert "p2" in parents2

    def test_relationships_out(self, store):
        store.put("p", {"name": "Vehicle"})
        store.put("c", {"name": "Wheel"}, parent_id="p")
        rels = store.relationships("p", direction="out")
        assert len(rels) == 1
        assert rels[0][0] == "c"

    def test_relationships_in(self, store):
        store.put("p", {"name": "Vehicle"})
        store.put("c", {"name": "Wheel"}, parent_id="p")
        rels = store.relationships("c", direction="in")
        assert len(rels) == 1
        assert rels[0][0] == "p"

    def test_relationships_both(self, store):
        store.put("p", {"name": "Vehicle"})
        store.put("c", {"name": "Wheel"}, parent_id="p")
        rels = store.relationships("p", direction="both")
        assert len(rels) >= 1


class TestKuzuStoreQuery:
    """Test query operations."""

    def test_query_by_sysml_type(self, store):
        store.put("e1", {"name": "Wheel", "sysml_type": "part"})
        store.put("e2", {"name": "Engine", "sysml_type": "part"})
        store.put("e3", {"name": "Speed", "sysml_type": "attribute"})
        results = store.query(sysml_type="part")
        assert set(results) == {"e1", "e2"}

    def test_query_by_name(self, store):
        store.put("e1", {"name": "Wheel", "sysml_type": "part"})
        store.put("e2", {"name": "Engine", "sysml_type": "part"})
        results = store.query(name="Wheel")
        assert results == ["e1"]

    def test_query_wildcard(self, store):
        store.put("e1", {"name": "Wheel", "sysml_type": "part"})
        store.put("e2", {"name": "WheelAssembly", "sysml_type": "part"})
        store.put("e3", {"name": "Engine", "sysml_type": "part"})
        results = store.query(name="Wheel*")
        assert set(results) == {"e1", "e2"}


class TestKuzuStoreGraph:
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
        store.put("a", {"name": "A"})
        store.put("b", {"name": "B"})
        assert store.path("a", "b") is None

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

    def test_subgraph(self, store):
        store.put("a", {"name": "A"})
        store.put("b", {"name": "B"}, parent_id="a")
        store.put("c", {"name": "C"}, parent_id="b")
        sub = store.subgraph(["a", "b"])
        assert len(sub) == 2
        assert sub.has("a")
        assert sub.has("b")
        assert not sub.has("c")

    def test_stats(self, store):
        store.put("a", {"name": "A"})
        store.put("b", {"name": "B"}, parent_id="a")
        stats = store.stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1


class TestKuzuStoreDisk:
    """Test disk-persistent mode."""

    def test_persistence(self, tmp_path):
        db_path = str(tmp_path / "test_db")
        store1 = KuzuStore(database=db_path)
        store1.put("e1", {"name": "Wheel", "sysml_type": "part"})
        del store1

        store2 = KuzuStore(database=db_path)
        assert store2.has("e1")
        data = store2.get("e1")
        assert data["name"] == "Wheel"


class TestCreateStore:
    """Test the factory function."""

    def test_create_kuzu_memory(self):
        store = create_store("kuzu")
        assert isinstance(store, KuzuStore)

    def test_create_kuzu_alias(self):
        store = create_store("kuzudb")
        assert isinstance(store, KuzuStore)

    def test_create_kuzu_with_database(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        store = create_store("kuzu", database=db_path)
        assert isinstance(store, KuzuStore)
