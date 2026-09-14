from pathlib import Path

import pytest

from src.pipeline.run import run_pipeline


def test_pipeline_not_yet_implemented():
    """Placeholder: replace as each stage gets implemented."""
    with pytest.raises(NotImplementedError):
        run_pipeline(Path("data/samples/does_not_exist_yet.png"))
