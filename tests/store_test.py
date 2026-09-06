#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the storage abstraction layer."""

import time

import pytest
from sysmlpy.store import (
    Store, InMemoryStore, NetworkXStore, KuzuStore, CayleyStore,
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


# ---------------------------------------------------------------------------
# Phase D (v0.56.0): graph query extensions
# ---------------------------------------------------------------------------

class TestNetworkXQueryExtensions:
    """all_paths, depth-limited descendants, neighborhoods, impact analysis."""

    def _build_chain(self):
        from sysmlpy.store import NetworkXStore
        st = NetworkXStore()
        st.put("A", {"name": "A", "sysml_type": "part"})
        st.put("B", {"name": "B", "sysml_type": "part"}, parent_id="A")
        st.put("C", {"name": "C", "sysml_type": "part"}, parent_id="B")
        st.put("D", {"name": "D", "sysml_type": "part"}, parent_id="C")
        return st

    def test_all_paths_linear(self):
        st = self._build_chain()
        paths = st.all_paths("A", "D")
        assert paths == [["A", "B", "C", "D"]]

    def test_all_paths_multiple(self):
        from sysmlpy.store import NetworkXStore
        st = NetworkXStore()
        st.put("A", {"name": "A"})
        st.put("B1", {"name": "B1"}, parent_id="A")
        st.put("B2", {"name": "B2"}, parent_id="A")
        st.put("C", {"name": "C"}, parent_id="B1")
        st.put("C", {"name": "C2"}, parent_id="B2")
        paths = st.all_paths("A", "C")
        assert len(paths) == 2

    def test_all_paths_missing_endpoint(self):
        st = self._build_chain()
        assert st.all_paths("A", "NOPE") == []
        assert st.all_paths("NOPE", "A") == []

    def test_max_paths_cap(self):
        from sysmlpy.store import NetworkXStore
        st = self._build_chain()
        # linear graph — no explosion; cap respected via diamond below
        st.put("B2", {"name": "B2"}, parent_id="A")
        st.put("C", {"name": "CX"}, parent_id="B2")
        paths = st.all_paths("A", "C")
        assert len(paths) <= 20

    def test_descendants_depth_limited(self):
        st = self._build_chain()
        assert st.descendants_depth_limited("A", max_depth=1) == ["B"]
        assert st.descendants_depth_limited("A", max_depth=2) == ["B", "C"]
        assert st.descendants_depth_limited("A", max_depth=3) == ["B", "C", "D"]

    def test_neighborhood(self):
        st = self._build_chain()
        nb = st.neighborhood("B", radius=1)
        assert nb == {"A", "B", "C"}

    def test_impact_downstream(self):
        st = self._build_chain()
        assert st.impact_analysis("A", direction="downstream") == {"B", "C", "D"}
        # Change to C only affects D
        assert st.impact_analysis("C", direction="downstream") == {"D"}

    def test_impact_upstream(self):
        st = self._build_chain()
        assert st.impact_analysis("D", direction="upstream") == {"A", "B", "C"}

    def test_in_out_degree_centrality(self):
        st = self._build_chain()
        out_c = st.out_degree_centrality()
        in_c = st.in_degree_centrality()
        assert out_c["A"] > 0
        assert in_c["D"] > 0
        assert in_c["A"] == 0.0


class TestKuzuQueryExtensions:
    """Cypher passthrough and convenience queries."""

    def _kuzu(self):
        pytest.importorskip("kuzu")
        from sysmlpy.store import KuzuStore
        return KuzuStore()

    def test_execute_cypher_raw(self):
        st = self._kuzu()
        st.put("a", {"name": "A"})
        st.put("b", {"name": "B"}, parent_id="a")
        rows = st.execute_cypher("MATCH (e:Element) RETURN e.id AS id ORDER BY id")
        assert [r["id"] for r in rows] == ["a", "b"]

    def test_siblings(self):
        st = self._kuzu()
        st.put("a", {"name": "A"})
        st.put("b", {"name": "B"}, parent_id="a")
        st.put("c", {"name": "C"}, parent_id="a")
        st.put("d", {"name": "D"}, parent_id="a")
        sibs = set(st.siblings("b"))
        assert sibs == {"c", "d"}

    def test_hub_elements_outgoing(self):
        st = self._kuzu()
        st.put("a", {"name": "A"})
        st.put("b", {"name": "B"}, parent_id="a")
        st.put("c", {"name": "C"}, parent_id="a")
        st.put("d", {"name": "D"}, parent_id="a")
        hubs = st.hub_elements(3, direction="outgoing")
        assert hubs == [("a", 3)]

    def test_hub_elements_incoming(self):
        st = self._kuzu()
        # b, c, d all point INTO a (reverse edges)
        st.put("a", {"name": "A"})
        st.put("b", {"name": "B"}, parent_id="a")
        st.put("c", {"name": "C"}, parent_id="a")
        st.put("d", {"name": "D"}, parent_id="a")
        # incoming into b/c/d is 1; nothing >= 2
        hubs = st.hub_elements(2, direction="incoming")
        assert hubs == []

    def test_shortest_path_between_named(self):
        st = self._kuzu()
        st.put("n1", {"name": "A"})
        st.put("n2", {"name": "B"}, parent_id="n1")
        st.put("n3", {"name": "C"}, parent_id="n2")
        path = st.shortest_path_between_named("A", "C")
        assert path == ["n1", "n2", "n3"]

    def test_shortest_path_none_when_disconnected(self):
        st = self._kuzu()
        st.put("x1", {"name": "X1"})
        st.put("x2", {"name": "X2"})
        assert st.shortest_path_between_named("X1", "X2") is None


# ── Cayley (requires a running Cayley server) ──────────────────────────────

def _cayley_server_available() -> bool:
    """Probe for a Cayley server at localhost:64210 (podman default)."""
    try:
        import requests
        r = requests.post(
            "http://localhost:64210/api/v1/query/gizmo",
            data="g.V().limit(1).all()",
            timeout=1,
        )
        return r.status_code == 200
    except Exception:
        return False


_CAYLEY_UP = _cayley_server_available()


@pytest.mark.skipif(
    not _CAYLEY_UP,
    reason=(
        "Cayley server not reachable at localhost:64210 "
        "(start it: podman run -d --name cayley -p 64210:64210 "
        "docker.io/cayleygraph/cayley)"
    ),
)
class TestCayleyStore:
    """Goal 10 batch 3: CayleyStore hardening + query parity.

    Verified against a live Cayley v0.7 server.  Fixes covered here:
    clear() stub (missing _query_label), _delete_quads posting to
    /write instead of /delete, delete() discarding its quad list,
    get() leaking marker/edge keys, put() overwrite semantics, and
    query() glob parity with the other backends.
    """

    def _store(self) -> CayleyStore:
        st = CayleyStore(label="test_cayley")
        st.clear()
        return st

    def _populated(self) -> CayleyStore:
        st = self._store()
        st.put("m", {"name": "M", "kind": "model"})
        st.put("p1", {"name": "Engine", "kind": "part"}, parent_id="m")
        st.put("p2", {"name": "Wheel", "kind": "part"}, parent_id="m")
        st.put("a1", {"name": "power", "kind": "attribute"}, parent_id="p1")
        return st

    def test_put_and_get_roundtrip(self):
        st = self._store()
        st.put("e1", {"name": "Engine", "sysml_type": "part"})
        assert st.get("e1") == {"name": "Engine", "sysml_type": "part"}

    def test_get_missing(self):
        assert self._store().get("nonexistent") is None

    def test_put_overwrites(self):
        st = self._store()
        st.put("e1", {"name": "v1"})
        st.put("e1", {"name": "v2"})
        assert st.get("e1") == {"name": "v2"}

    def test_put_overwrite_keeps_parent_edge(self):
        st = self._store()
        st.put("parent", {"name": "P"})
        st.put("child", {"name": "v1"}, parent_id="parent")
        st.put("child", {"name": "v2"})
        assert st.get("child") == {"name": "v2"}
        assert st.parents("child") == ["parent"]

    def test_put_with_parent(self):
        st = self._store()
        st.put("pid", {"name": "parent"})
        st.put("cid", {"name": "child"}, parent_id="pid")
        assert st.get("cid") is not None
        assert st.children("pid") == ["cid"]
        assert st.parents("cid") == ["pid"]

    def test_delete_removes_everything(self):
        st = self._populated()
        assert st.delete("p2") is True
        assert st.has("p2") is False
        assert st.get("p2") is None
        assert st.children("m") == ["p1"]  # no ghost edge

    def test_delete_missing(self):
        assert self._populated().delete("ghost") is False

    def test_children_parents(self):
        st = self._populated()
        assert st.children("m") == ["p1", "p2"]
        assert st.children("p1") == ["a1"]
        assert st.parents("a1") == ["p1"]

    def test_relationships(self):
        st = self._populated()
        rels = st.relationships("p1")
        pairs = {(r[0], r[1]) for r in rels}
        assert ("a1", REL_PARENT_CHILD) in pairs
        assert ("m", REL_PARENT_CHILD) in pairs

    def test_query_by_type(self):
        st = self._populated()
        results = st.query(kind="part")
        assert sorted(results) == ["p1", "p2"]

    def test_query_by_name(self):
        st = self._populated()
        assert st.query(name="Engine") == ["p1"]

    def test_query_wildcard(self):
        st = self._populated()
        results = st.query(name="Eng*")
        assert results == ["p1"]

    def test_query_wildcard_parity_with_networkx(self):
        st = self._populated()
        nx = NetworkXStore()
        nx.clear()
        nx.put("m", {"name": "M", "kind": "model"})
        nx.put("p1", {"name": "Engine", "kind": "part"})
        nx.put("p2", {"name": "Wheel", "kind": "part"})
        nx.put("a1", {"name": "power", "kind": "attribute"})
        for case in (
            {"name": "Eng*"}, {"name": "*e*"}, {"name": "*"},
            {"name": "*", "kind": "part"}, {"kind": "part"},
            {"name": "Engine"}, {"kind": "missing"},
        ):
            assert sorted(st.query(**case)) == sorted(nx.query(**case)), case
        nx.clear()

    def test_query_no_filters(self):
        st = self._populated()
        assert sorted(st.query()) == ["a1", "m", "p1", "p2"]

    def test_query_empty_result(self):
        assert self._populated().query(kind="nonexistent") == []

    def test_descendants_ancestors(self):
        st = self._populated()
        assert sorted(st.descendants("m")) == ["a1", "p1", "p2"]
        assert st.ancestors("a1") == ["p1", "m"]

    def test_path(self):
        st = self._populated()
        assert st.path("m", "a1") == ["m", "p1", "a1"]

    def test_components_cycles_centrality(self):
        st = self._populated()
        comps = st.connected_components()
        assert comps == [{"m", "p1", "p2", "a1"}]
        assert st.cycles() == []
        cent = st.centrality()
        assert cent["m"] > cent["a1"]

    def test_len_ids_has(self):
        st = self._populated()
        assert len(st) == 4
        assert sorted(st.ids()) == ["a1", "m", "p1", "p2"]
        assert st.has("p1") is True
        assert st.has("nope") is False

    def test_clear_empties(self):
        st = self._populated()
        st.clear()
        assert len(st) == 0
        assert list(st.ids()) == []

    def test_label_isolation(self):
        a = CayleyStore(label="iso_a")
        a.clear()
        b = CayleyStore(label="iso_b")
        b.clear()
        a.put("x", {"name": "InA"})
        b.put("y", {"name": "InB"})
        assert sorted(a.ids()) == ["x"]
        assert sorted(b.ids()) == ["y"]
        assert a.query(name="InB") == []
        assert b.query(name="InA") == []
        a.clear()
        b.clear()


class TestBackendParity:
    """The same query surface and results on NetworkX, Kùzu and Cayley.

    Goal 10 close-out: the analytics extensions shipped per-backend
    (NetworkX v0.79.0 client-side gizmo parity, Kùzu v0.85.0) must
    agree on the same element graph, including deterministic ordering.
    """

    GRAPH = [
        ("veh", {"name": "Vehicle"}, None),
        ("eng", {"name": "Engine"}, "veh"),
        ("pump", {"name": "Pump"}, "eng"),
        ("w1", {"name": "Wheel"}, "veh"),
        ("w2", {"name": "Wheel"}, "veh"),
    ]

    def _stores(self):
        stores = {"nx": NetworkXStore()}
        try:
            stores["kuzu"] = KuzuStore()
        except Exception:
            pass  # kuzu not installed
        stores["cayley"] = CayleyStore(
            label=f"parity_{int(time.time() * 1_000_000)}")
        for st in stores.values():
            for eid, data, parent in self.GRAPH:
                if parent is None:
                    st.put(eid, data)
                else:
                    st.put(eid, data, parent_id=parent)
        return stores

    OPS = {
        "children(veh)": lambda s: sorted(s.children("veh")),
        "descendants(veh)": lambda s: sorted(s.descendants("veh")),
        "all_paths": lambda s: s.all_paths("veh", "pump"),
        "in_cent": lambda s: {k: round(v, 3)
                              for k, v in s.in_degree_centrality().items() if v},
        "out_cent": lambda s: {k: round(v, 3)
                               for k, v in s.out_degree_centrality().items() if v},
        "desc_depth_lim": lambda s: sorted(
            s.descendants_depth_limited("veh", max_depth=1)),
        "neighborhood": lambda s: sorted(s.neighborhood("eng", radius=1)),
        "impact_down": lambda s: sorted(s.impact_analysis("eng")),
        "impact_up": lambda s: sorted(
            s.impact_analysis("pump", direction="upstream")),
        "siblings": lambda s: sorted(s.siblings("eng")),
        "hubs_out": lambda s: dict(
            s.hub_elements(min_degree=1, direction="outgoing")),
        "hubs_in": lambda s: dict(
            s.hub_elements(min_degree=1, direction="incoming")),
        "hubs_both_ties": lambda s: dict(
            s.hub_elements(min_degree=1, direction="both")),
        "shortest_named": lambda s: s.shortest_path_between_named(
            "Vehicle", "Pump"),
        "shortest_missing": lambda s: s.shortest_path_between_named(
            "Vehicle", "GHOST"),
    }

    def test_parity_all_backends(self):
        stores = self._stores()
        for name, op in self.OPS.items():
            results = {}
            for key, st in stores.items():
                results[key] = op(st)
            vals = list(results.values())
            assert all(str(v) == str(vals[0]) for v in vals), \
                f"{name} mismatch: {results}"

    def test_surface_parity(self):
        """Every backend exposes the same public query methods."""
        surface = ["all_paths", "in_degree_centrality",
                   "out_degree_centrality", "descendants_depth_limited",
                   "neighborhood", "impact_analysis", "siblings",
                   "hub_elements", "shortest_path_between_named",
                   "centrality", "children", "parents", "relationships",
                   "query", "has", "ids"]
        for cls in (NetworkXStore, KuzuStore, CayleyStore):
            for method in surface:
                assert hasattr(cls, method), \
                    f"{cls.__name__} lacks {method}"

    def test_hub_elements_invalid_direction(self):
        for st in self._stores().values():
            with pytest.raises(ValueError, match="direction"):
                st.hub_elements(direction="sideways")
            st.clear() if hasattr(st, "clear") else None
