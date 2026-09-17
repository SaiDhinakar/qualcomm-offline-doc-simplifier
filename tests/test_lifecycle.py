"""Tests for the vector store lifecycle manager."""


from src.embed_index.lifecycle import VectorStoreManager


def test_create_session():
    manager = VectorStoreManager()
    session = manager.create_session("doc1")
    assert session.document_id == "doc1"
    assert manager.active_count == 1


def test_get_session():
    manager = VectorStoreManager()
    manager.create_session("doc1")
    session = manager.get_session("doc1")
    assert session is not None
    assert session.document_id == "doc1"


def test_get_nonexistent_session():
    manager = VectorStoreManager()
    session = manager.get_session("nonexistent")
    assert session is None


def test_clear_session():
    manager = VectorStoreManager()
    manager.create_session("doc1")
    result = manager.clear_session("doc1")
    assert result is True
    assert manager.active_count == 0


def test_clear_nonexistent_session():
    manager = VectorStoreManager()
    result = manager.clear_session("nonexistent")
    assert result is False


def test_clear_all_sessions():
    manager = VectorStoreManager()
    manager.create_session("doc1")
    manager.create_session("doc2")
    count = manager.clear_all()
    assert count == 2
    assert manager.active_count == 0


def test_list_sessions():
    manager = VectorStoreManager()
    manager.create_session("doc1")
    manager.create_session("doc2")
    sessions = manager.list_sessions()
    assert set(sessions) == {"doc1", "doc2"}


def test_session_expiry():
    manager = VectorStoreManager(session_timeout_minutes=-1)
    manager.create_session("doc1")
    session = manager.get_session("doc1")
    assert session is None  # Already expired


def test_create_session_replaces_existing():
    manager = VectorStoreManager()
    s1 = manager.create_session("doc1")
    s1.overview = "old overview"
    s2 = manager.create_session("doc1")
    assert s2.overview == ""  # New session, not the old one
    assert manager.active_count == 1
