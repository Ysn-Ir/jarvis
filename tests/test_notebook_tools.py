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

    # 5. Update cell 1
    res_up = nb.update_notebook_cell(nb_path, cell_index=1, code="x = 100\nprint(x)")
    assert "Successfully updated cell #1" in res_up
    summary2 = nb.read_notebook_cells(nb_path)
    assert "x = 100" in summary2

    # 6. Delete cell 2
    res_del = nb.delete_notebook_cell(nb_path, cell_index=2)
    assert "Successfully deleted" in res_del
    with open(nb_path, "r", encoding="utf-8") as f:
        nb_data = json.load(f)
    assert len(nb_data["cells"]) == 1

    # 7. Clear all cells
    res_clear = nb.clear_notebook_cells(nb_path)
    assert "Cleared all 1 cells" in res_clear
    assert "empty" in nb.read_notebook_cells(nb_path)


def test_notebook_router_routing():
    from laya.router.classifier import IntentRouter
    router = IntentRouter.get_instance()

    # Create notebook
    r1 = router.route("make a notebook named analysis.ipynb")
    assert r1.action == "create_notebook"
    assert r1.params.get("notebook_name") == "analysis.ipynb"

    # Write cell with notebook name
    r2 = router.route("in notebook.ipynb write a new cell with import pandas as pd")
    assert r2.action == "write_notebook_cell"
    assert r2.params.get("notebook_name") == "notebook.ipynb"
    assert r2.params.get("code") == "import pandas as pd"

    # Write cell implicitly
    r3 = router.route("write a new cell with import numpy as np")
    assert r3.action == "write_notebook_cell"
    assert r3.params.get("code") == "import numpy as np"

    # Update cell
    r4 = router.route("update cell 2 in notebook.ipynb with x = 10")
    assert r4.action == "update_notebook_cell"
    assert r4.params.get("notebook_name") == "notebook.ipynb"
    assert r4.params.get("cell_index") == 2
    assert r4.params.get("code") == "x = 10"

    # Delete cell
    r5 = router.route("delete cell 2 in notebook.ipynb")
    assert r5.action == "delete_notebook_cell"
    assert r5.params.get("notebook_name") == "notebook.ipynb"
    assert r5.params.get("cell_index") == 2

    # Read cells
    r6 = router.route("read notebook cells in test.ipynb")
    assert r6.action == "read_notebook_cells"
    assert r6.params.get("notebook_name") == "test.ipynb"

    # Compound create and write cell
    r7 = router.route("make a notebook named test.ipynb and write a new cell with import math")
    assert r7.action == "execute_compound"
    actions7 = r7.params.get("actions", [])
    assert actions7[0]["action"] == "create_notebook"
    assert actions7[0]["params"]["notebook_name"] == "test.ipynb"
    assert actions7[1]["action"] == "write_notebook_cell"
    assert actions7[1]["params"]["code"] == "import math"



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

    # Test interruption keywords: "stop", "shut up", "quiet", "cancel"
    from laya.audio.wake_word import INTERRUPT_KEYWORDS_REGEX
    for phrase in ["stop", "hey stop", "shut up", "be quiet", "cancel that"]:
        assert re.search(INTERRUPT_KEYWORDS_REGEX, phrase, re.IGNORECASE) is not None, f"Failed on: {phrase}"


def test_follow_up_echo_rejection():
    from laya.audio.wake_word import is_echo_of_assistant

    assistant_spoken = "Created folder 'projectx' at 'C:\\Users\\khali\\OneDrive\\Bureau\\projectx'."
    
    # 1. Exact or partial echo of assistant output must be rejected
    assert is_echo_of_assistant("created folder projectx", assistant_spoken) is True
    assert is_echo_of_assistant("at c users bureau projectx", assistant_spoken) is True
    assert is_echo_of_assistant("Created folder 'projectx' at 'C:\\Users\\khali\\OneDrive\\Bureau\\projectx'.", assistant_spoken) is True

    # 2. Known assistant output signature prefixes must be rejected even without prompt text
    assert is_echo_of_assistant("reminder set for 6pm") is True
    assert is_echo_of_assistant("the file is located at desktop") is True
    assert is_echo_of_assistant("from our history you are yasin") is True
    assert is_echo_of_assistant("active contact set to ysn") is True
    assert is_echo_of_assistant("could not find or open whatsapp") is True

    # 3. Real user follow-up commands must NOT be rejected
    assert is_echo_of_assistant("open spotify and play synthwave", assistant_spoken) is False
    assert is_echo_of_assistant("close this window", assistant_spoken) is False
    assert is_echo_of_assistant("in this folder create a python file named main.py", assistant_spoken) is False
    assert is_echo_of_assistant("what is my name", assistant_spoken) is False
    assert is_echo_of_assistant("send him a message via whatsapp saying hello", assistant_spoken) is False


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        test_notebook_tools_crud(Path(td))
    test_wake_word_parsing()
    test_follow_up_echo_rejection()
    print("SUCCESS: ALL NOTEBOOK AND WAKE WORD TESTS PASSED 100%!")

