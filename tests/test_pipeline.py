"""Tests for the pipeline orchestrator."""


from src.pipeline.run import Pipeline


def test_pipeline_initialization():
    pipeline = Pipeline(llm_backend="stub", embedding_backend="hash")
    assert pipeline._llm is not None
    assert pipeline._embedder is not None


def test_pipeline_convenience_function():
    from src.pipeline.run import get_default_pipeline
    pipeline = get_default_pipeline()
    assert pipeline is not None
    # Should return the same instance
    assert pipeline is get_default_pipeline()


def test_pipeline_ask_question_without_analysis():
    pipeline = Pipeline(llm_backend="stub", embedding_backend="hash")
    from src.models import DocumentSession
    session = DocumentSession(document_id="test")
    result = pipeline.ask_question(session, "What is this?")
    assert result["status"] == "error"


def test_pipeline_clear_sessions():
    pipeline = Pipeline(llm_backend="stub", embedding_backend="hash")
    pipeline._session_manager.create_session("doc1")
    pipeline._session_manager.create_session("doc2")
    count = pipeline.clear_all_sessions()
    assert count == 2
