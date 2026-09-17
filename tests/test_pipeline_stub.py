"""Tests for the pipeline stub (legacy test)."""



from src.pipeline.run import Pipeline


def test_pipeline_ask_without_analysis():
    """Test that asking a question without analysis returns an error."""
    pipeline = Pipeline(llm_backend="stub", embedding_backend="hash")
    from src.models import DocumentSession
    session = DocumentSession(document_id="test")
    result = pipeline.ask_question(session, "What is this?")
    assert result["status"] == "error"
