#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the storage abstraction layer."""

import pytest
from sysmlpy.store import (
    Store, InMemoryStore, NetworkXStore,
    create_store, new_id,
    REL_PARENT_CHILD, REL_TYPED_BY, REL_SPECIALIZES,
)


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(params=["memory", "networkx"])
def store(request):
    """Run each test against both backends."""
    if request.param == "networkx":
        pytest.importorskip("networkx")
    return create_store(request.param)


@pytest.fixture
def mem_store():
    return InMemoryStore()


@pytest.fixture
def nx_store():
    pytest.importorskip("networkx")
    return NetworkXStore()


# ── Factory ─────────────────────────────────────────────────────────────────

class TestCreateStore:
    def test_memory_backend(self):
        s = create_store("memory")
        assert isinstance(s, InMemoryStore)

    def test_networkx_backend(self):
        pytest.importorskip("networkx")
        s = create_store("networkx")
        assert isinstance(s, NetworkXStore)

    def test_short_names(self):
        assert isinstance(create_store("inmemory"), InMemoryStore)
        pytest.importorskip("networkx")
        assert isinstance(create_store("nx"), NetworkXStore)
        assert isinstance(create_store("graph"), NetworkXStore)

    def test_invalid_backend(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            create_store("redis")


# ── ID Generation ───────────────────────────────────────────────────────────

class TestNewId:
    def test_generates_uuid(self):
        eid = new_id()
        assert isinstance(eid, str)
        assert len(eid) == 36

    def test_unique(self):
        ids = {new_id() for _ in range(1000)}
        assert len(ids) == 1000


# ── Basic CRUD ──────────────────────────────────────────────────────────────

class TestPutGet:
    def test_put_and_get(self, store: Store):
        eid = new_id()
        data = {"name": "test_part", "sysml_type": "part"}
        store.put(eid, data)
        result = store.get(eid)
        assert result == data

    def test_get_missing(self, store: Store):
        assert store.get("nonexistent") is None

    def test_put_overwrites(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "v1"})
        store.put(eid, {"name": "v2"})
        assert store.get(eid)["name"] == "v2"

    def test_put_with_parent(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        assert store.get(cid) is not None


class TestDelete:
    def test_delete_existing(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "x"})
        assert store.delete(eid) is True
        assert store.get(eid) is None

    def test_delete_missing(self, store: Store):
        assert store.delete("nonexistent") is False

    def test_delete_removes_relationships(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        store.delete(pid)
        assert store.get(pid) is None
        assert cid not in store.children(pid)

    def test_delete_child_cleans_parent(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        store.delete(cid)
        assert cid not in store.children(pid)


# ── Parent-Child ────────────────────────────────────────────────────────────

class TestChildren:
    def test_no_children(self, store: Store):
        pid = new_id()
        store.put(pid, {"name": "parent"})
        assert store.children(pid) == []

    def test_single_child(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        assert store.children(pid) == [cid]

    def test_multiple_children(self, store: Store):
        pid = new_id()
        c1, c2, c3 = new_id(), new_id(), new_id()
        store.put(pid, {"name": "parent"})
        store.put(c1, {"name": "c1"}, parent_id=pid)
        store.put(c2, {"name": "c2"}, parent_id=pid)
        store.put(c3, {"name": "c3"}, parent_id=pid)
        assert store.children(pid) == [c1, c2, c3]

    def test_children_returns_copy(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        children = store.children(pid)
        children.append("fake")
        assert store.children(pid) == [cid]


class TestParents:
    def test_no_parent(self, store: Store):
        cid = new_id()
        store.put(cid, {"name": "child"})
        assert store.parents(cid) == []

    def test_single_parent(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        assert store.parents(cid) == [pid]

    def test_parents_returns_copy(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        parents = store.parents(cid)
        parents.append("fake")
        assert store.parents(cid) == [pid]


# ── Relationships ───────────────────────────────────────────────────────────

class TestRelationships:
    def test_no_relationships(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "lonely"})
        assert store.relationships(eid) == []

    def test_parent_child_relationship(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        rels = store.relationships(pid)
        assert len(rels) == 1
        assert rels[0][0] == cid
        assert rels[0][1] == REL_PARENT_CHILD

    def test_filter_by_type(self, store: Store):
        eid = new_id()
        tid = new_id()
        store.put(eid, {"name": "element"})
        store.put(tid, {"name": "type"})
        store.put(eid, {"name": "element"}, parent_id=tid, rel_type=REL_TYPED_BY)
        rels = store.relationships(eid, rel_type=REL_TYPED_BY)
        assert len(rels) >= 1
        assert any(r[1] == REL_TYPED_BY for r in rels)

    def test_direction_out(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        out = store.relationships(pid, direction="out")
        assert any(t == cid for t, _, _ in out)

    def test_direction_in(self, store: Store):
        pid = new_id()
        cid = new_id()
        store.put(pid, {"name": "parent"})
        store.put(cid, {"name": "child"}, parent_id=pid)
        in_rels = store.relationships(cid, direction="in")
        assert any(t == pid for t, _, _ in in_rels)


# ── Query ───────────────────────────────────────────────────────────────────

class TestQuery:
    def test_query_by_type(self, store: Store):
        e1 = new_id()
        e2 = new_id()
        store.put(e1, {"name": "p1", "sysml_type": "part"})
        store.put(e2, {"name": "i1", "sysml_type": "item"})
        results = store.query(sysml_type="part")
        assert e1 in results
        assert e2 not in results

    def test_query_by_name(self, store: Store):
        e1 = new_id()
        e2 = new_id()
        store.put(e1, {"name": "Engine"})
        store.put(e2, {"name": "Wheel"})
        results = store.query(name="Engine")
        assert e1 in results
        assert e2 not in results

    def test_query_wildcard(self, store: Store):
        e1 = new_id()
        e2 = new_id()
        e3 = new_id()
        store.put(e1, {"name": "Engine"})
        store.put(e2, {"name": "EngineBlock"})
        store.put(e3, {"name": "Wheel"})
        results = store.query(name="Engine*")
        assert e1 in results
        assert e2 in results
        assert e3 not in results

    def test_query_multiple_filters(self, store: Store):
        e1 = new_id()
        e2 = new_id()
        store.put(e1, {"name": "Engine", "sysml_type": "part"})
        store.put(e2, {"name": "Engine", "sysml_type": "item"})
        results = store.query(name="Engine", sysml_type="part")
        assert e1 in results
        assert e2 not in results

    def test_query_empty(self, store: Store):
        results = store.query(sysml_type="nonexistent")
        assert results == []


# ── Has / Len / IDs / Clear ─────────────────────────────────────────────────

class TestStoreMetadata:
    def test_has(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "x"})
        assert store.has(eid) is True
        assert store.has("nonexistent") is False

    def test_len(self, store: Store):
        assert len(store) == 0
        store.put(new_id(), {"name": "a"})
        store.put(new_id(), {"name": "b"})
        assert len(store) == 2

    def test_ids(self, store: Store):
        e1 = new_id()
        e2 = new_id()
        store.put(e1, {"name": "a"})
        store.put(e2, {"name": "b"})
        ids = set(store.ids())
        assert ids == {e1, e2}

    def test_clear(self, store: Store):
        store.put(new_id(), {"name": "a"})
        store.put(new_id(), {"name": "b"})
        store.clear()
        assert len(store) == 0


# ── Descendants / Ancestors ─────────────────────────────────────────────────

class TestTreeTraversal:
    def test_descendants(self, store: Store):
        root = new_id()
        c1 = new_id()
        c2 = new_id()
        gc1 = new_id()
        store.put(root, {"name": "root"})
        store.put(c1, {"name": "c1"}, parent_id=root)
        store.put(c2, {"name": "c2"}, parent_id=root)
        store.put(gc1, {"name": "gc1"}, parent_id=c1)
        desc = store.descendants(root)
        assert set(desc) == {c1, c2, gc1}

    def test_ancestors(self, store: Store):
        root = new_id()
        c1 = new_id()
        gc1 = new_id()
        store.put(root, {"name": "root"})
        store.put(c1, {"name": "c1"}, parent_id=root)
        store.put(gc1, {"name": "gc1"}, parent_id=c1)
        anc = store.ancestors(gc1)
        assert set(anc) == {c1, root}

    def test_descendants_empty(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "leaf"})
        assert store.descendants(eid) == []

    def test_ancestors_empty(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "root"})
        assert store.ancestors(eid) == []


# ── Path ────────────────────────────────────────────────────────────────────

class TestPath:
    def test_path_exists(self, store: Store):
        root = new_id()
        c1 = new_id()
        c2 = new_id()
        store.put(root, {"name": "root"})
        store.put(c1, {"name": "c1"}, parent_id=root)
        store.put(c2, {"name": "c2"}, parent_id=c1)
        path = store.path(root, c2)
        assert path is not None
        assert path[0] == root
        assert path[-1] == c2

    def test_path_no_path(self, store: Store):
        e1 = new_id()
        e2 = new_id()
        store.put(e1, {"name": "e1"})
        store.put(e2, {"name": "e2"})
        assert store.path(e1, e2) is None

    def test_path_same_node(self, store: Store):
        eid = new_id()
        store.put(eid, {"name": "x"})
        assert store.path(eid, eid) == [eid]


# ── NetworkX-specific ───────────────────────────────────────────────────────

class TestNetworkXSpecific:
    def test_connected_components(self, nx_store: NetworkXStore):
        e1 = new_id()
        e2 = new_id()
        e3 = new_id()
        nx_store.put(e1, {"name": "a"})
        nx_store.put(e2, {"name": "b"}, parent_id=e1)
        nx_store.put(e3, {"name": "c"})
        components = nx_store.connected_components()
        assert len(components) == 2

    def test_centrality(self, nx_store: NetworkXStore):
        root = new_id()
        c1 = new_id()
        c2 = new_id()
        nx_store.put(root, {"name": "root"})
        nx_store.put(c1, {"name": "c1"}, parent_id=root)
        nx_store.put(c2, {"name": "c2"}, parent_id=root)
        centrality = nx_store.centrality()
        assert centrality[root] > centrality[c1]

    def test_stats(self, nx_store: NetworkXStore):
        e1 = new_id()
        e2 = new_id()
        nx_store.put(e1, {"name": "a"})
        nx_store.put(e2, {"name": "b"}, parent_id=e1)
        stats = nx_store.stats()
        assert stats["nodes"] == 2
        assert stats["edges"] >= 1

    def test_subgraph(self, nx_store: NetworkXStore):
        e1 = new_id()
        e2 = new_id()
        e3 = new_id()
        nx_store.put(e1, {"name": "a"})
        nx_store.put(e2, {"name": "b"}, parent_id=e1)
        nx_store.put(e3, {"name": "c"})
        sub = nx_store.subgraph([e1, e2])
        assert len(sub) == 2
        assert sub.has(e1)
        assert sub.has(e2)
        assert not sub.has(e3)
