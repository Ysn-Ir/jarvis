import sys
from pathlib import Path

# Add project root to sys.path before any local imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
from laya.tools.notebook_tools import NotebookTools
from laya.audio.wake_word import WAKE_KEYWORDS_REGEX, NON_COMMAND_WORDS
from laya.router.classifier import classify_intent


def test_notebook_tools_crud(tmp_path):
    nb = NotebookTools.get_instance()
    nb_path = str(tmp_path / "test_run.ipynb")
    
    # 1. Create notebook
    res_create = nb.create_notebook(nb_path)
    assert "Created" in res_create
    assert Path(nb_path).exists()
    
    # 2. Write code cell
    res_write = nb.write_notebook_cell(nb_path, "x = 42\nprint(x)", cell_type="code")
    assert "Successfully wrote code cell" in res_write
    
    # 3. Write markdown cell
    res_md = nb.write_notebook_cell(nb_path, "# Analysis Section", cell_type="markdown")
    assert "Successfully wrote markdown cell" in res_md
    
    # 4. Read back cells summary
    summary = nb.read_notebook_cells(nb_path)
    assert "x = 42" in summary
    assert "code" in summary
    assert "Analysis Section" in summary


def test_wake_word_parsing():
    import re

    # Test "Hey, Jarvis." -> command is empty or stripped
    text = "Hey, Jarvis."
    match = re.search(WAKE_KEYWORDS_REGEX, text, re.IGNORECASE)
    assert match is not None
    cmd = text[match.end():].strip().strip(".,!?").strip()
    assert cmd == ""

    # Test "Jarvis, are you ready?" -> command is "are you ready"
    text2 = "Jarvis, are you ready?"
    match2 = re.search(WAKE_KEYWORDS_REGEX, text2, re.IGNORECASE)
    assert match2 is not None
    cmd2 = text2[match2.end():].strip().strip(".,!?").strip()
    assert cmd2.lower() == "are you ready"

    # Fast-path classification of readiness
    intent = classify_intent(cmd2)
    assert intent.action == "query_identity"


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        test_notebook_tools_crud(Path(td))
    test_wake_word_parsing()
    print("SUCCESS: ALL NOTEBOOK AND WAKE WORD TESTS PASSED 100%!")

