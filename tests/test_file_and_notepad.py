"""
Tests for File Writing, Appending, and Notepad Text Typing
Validates:
1. Writing to files (both filename-first and content-first syntax)
2. Appending to files (both syntax patterns)
3. Notepad writing (both prefix and suffix syntax)
4. Compound chains:
   - "open notepad and write hello world" -> write_to_notepad
   - "create file X and write Y to it" -> create_file + write_to_file
   - "create file X in folder Y and write Z into it" -> create_file + write_to_file
   - "create a file in a folder and open it write to it" -> create_file + open_file + write_to_file
5. Pronoun resolution and artifact cleaning (no 'to it' left in content)
"""

import pytest
from laya.router.classifier import IntentRouter
from laya.router.taxonomy import ExecutionPath

@pytest.fixture(scope="module")
def router():
    return IntentRouter.get_instance()

def test_notepad_writing_patterns(router):
    # Prefix
    d1 = router.route("write in notepad hello world")
    assert d1.action == "write_to_notepad"
    assert d1.params.get("text") == "hello world"

    d2 = router.route("write to notepad greetings everyone")
    assert d2.action == "write_to_notepad"
    assert d2.params.get("text") == "greetings everyone"

    d3 = router.route("in notepad write this is a note")
    assert d3.action == "write_to_notepad"
    assert d3.params.get("text") == "this is a note"

    # Suffix
    d4 = router.route("write hello world in notepad")
    assert d4.action == "write_to_notepad"
    assert d4.params.get("text") == "hello world"

    d5 = router.route("type sample code into notepad")
    assert d5.action == "write_to_notepad"
    assert d5.params.get("text") == "sample code"

def test_file_writing_patterns(router):
    # Filename first
    d1 = router.route("write to file test.txt hello from laya")
    assert d1.action == "write_to_file"
    assert d1.params.get("filename") == "test.txt"
    assert d1.params.get("content") == "hello from laya"

    d2 = router.route("in file test.txt write important data")
    assert d2.action == "write_to_file"
    assert d2.params.get("filename") == "test.txt"
    assert d2.params.get("content") == "important data"

    d3 = router.route("write test.txt some quick text")
    assert d3.action == "write_to_file"
    assert d3.params.get("filename") == "test.txt"
    assert d3.params.get("content") == "some quick text"

    # Content first
    d4 = router.route("write hello from laya to file test.txt")
    assert d4.action == "write_to_file"
    assert d4.params.get("filename") == "test.txt"
    assert d4.params.get("content") == "hello from laya"

def test_file_appending_patterns(router):
    d1 = router.route("append to file notes.txt another line")
    assert d1.action == "append_to_file"
    assert d1.params.get("filename_or_path") == "notes.txt"
    assert d1.params.get("content") == "another line"

    d2 = router.route("append another line to file notes.txt")
    assert d2.action == "append_to_file"
    assert d2.params.get("filename_or_path") == "notes.txt"
    assert d2.params.get("content") == "another line"

def test_compound_file_and_notepad_chains(router):
    # Open notepad and write
    c1 = router.route("open notepad and write hello world")
    assert c1.action == "execute_compound"
    actions1 = c1.params.get("actions", [])
    assert len(actions1) == 2
    assert actions1[0]["action"] == "open_app"
    assert actions1[1]["action"] == "write_to_notepad"
    assert actions1[1]["params"]["text"] == "hello world"

    # Open notepad and write in it
    c2 = router.route("open notepad and write in it welcome home")
    actions2 = c2.params.get("actions", [])
    assert actions2[1]["action"] == "write_to_notepad"
    assert actions2[1]["params"]["text"] == "welcome home"

    # Create file and write
    c3 = router.route("create file notes.txt and write first note to it")
    actions3 = c3.params.get("actions", [])
    assert len(actions3) == 2
    assert actions3[0]["action"] == "create_file"
    assert actions3[0]["params"]["filename"] == "notes.txt"
    assert actions3[1]["action"] == "write_to_file"
    assert actions3[1]["params"]["filename"] == "notes.txt"
    assert actions3[1]["params"]["content"] == "first note"

    # Create file in folder and write
    c4 = router.route("create file doc.txt in documents and write hello into it")
    actions4 = c4.params.get("actions", [])
    assert len(actions4) == 2
    assert actions4[0]["action"] == "create_file"
    assert actions4[0]["params"]["location"] == "documents"
    assert actions4[1]["action"] == "write_to_file"
    assert actions4[1]["params"]["content"] == "hello"

    # Create file in folder and open it write to it
    c5 = router.route("create a file in a folder and open it write to it")
    actions5 = c5.params.get("actions", [])
    assert len(actions5) == 3
    assert actions5[0]["action"] == "create_file"
    assert actions5[1]["action"] == "open_file"
    assert actions5[2]["action"] == "write_to_file"

    # Open notepad file named notes.txt and write hello world in it
    c6 = router.route("open a notepad file named notes.txt and write hello world in it")
    assert c6.action == "execute_compound"
    actions6 = c6.params.get("actions", [])
    assert actions6[0]["action"] == "write_to_notepad"
    assert actions6[0]["params"]["filename"] == "notes.txt"
    assert actions6[1]["action"] == "write_to_file"
    assert actions6[1]["params"]["filename"] == "notes.txt"
    assert actions6[1]["params"]["content"] == "hello world"

    # Make a python file named app.py and write print('hello') in it
    c7 = router.route("make a python file named app.py and write print('hello') in it")
    assert c7.action == "execute_compound"
    actions7 = c7.params.get("actions", [])
    assert actions7[0]["action"] == "create_file"
    assert actions7[0]["params"]["filename"] == "app.py"
    assert actions7[1]["action"] == "write_to_file"
    assert actions7[1]["params"]["filename"] == "app.py"
    assert actions7[1]["params"]["content"] == "print('hello')"


def test_word_and_notepad_named_files(router):
    # Word file creation / opening
    w1 = router.route("open a word file named report.docx and write hello in it")
    assert w1.action in ["create_word_document", "execute_compound"]
    if w1.action == "create_word_document":
        assert w1.params.get("filename") == "report.docx"
        assert w1.params.get("content") == "hello"

    w2 = router.route("open a word document named report.docx")
    assert w2.action == "create_word_document"
    assert w2.params.get("filename") == "report.docx"

    w3 = router.route("create a word file named summary.docx with executive overview")
    assert w3.action == "create_word_document"
    assert w3.params.get("filename") == "summary.docx"
    assert w3.params.get("content") == "executive overview"

    # Notepad file with specific name
    n1 = router.route("open a notepad file named notes.txt and write test content in it")
    assert n1.action in ["write_to_notepad", "execute_compound"]
    if n1.action == "write_to_notepad":
        assert n1.params.get("filename") == "notes.txt"

    n2 = router.route("open notepad file my_notes.txt")
    assert n2.action == "write_to_notepad"
    assert n2.params.get("filename") == "my_notes.txt"


def test_python_and_code_files(router):
    p1 = router.route("make a python file named script.py and write import sys in it")
    assert p1.action in ["create_file", "execute_compound"]
    if p1.action == "create_file":
        assert p1.params.get("filename") == "script.py"

    p2 = router.route("create a python file called test.py with def test(): pass")
    assert p2.action == "create_file"
    assert p2.params.get("filename") == "test.py"
    assert p2.params.get("content") == "def test(): pass"


def test_line_level_writing_and_editing(router):
    # In file write on line N
    l1 = router.route("in main.py write on line 5: print('hello')")
    assert l1.action == "write_to_file_line"
    assert l1.params.get("filename_or_path") == "main.py"
    assert l1.params.get("line_number") == 5
    assert l1.params.get("content") == "print('hello')"

    # Write on line N in file
    l2 = router.route("write on line 10 in app.py: x = 100")
    assert l2.action == "write_to_file_line"
    assert l2.params.get("filename_or_path") == "app.py"
    assert l2.params.get("line_number") == 10
    assert l2.params.get("content") == "x = 100"

    # Replace line N
    l3 = router.route("replace line 3 in main.py with y = 20")
    assert l3.action == "replace_file_line"
    assert l3.params.get("filename_or_path") == "main.py"
    assert l3.params.get("line_number") == 3
    assert l3.params.get("content") == "y = 20"

    # Delete line N
    l4 = router.route("delete line 4 in main.py")
    assert l4.action == "delete_file_line"
    assert l4.params.get("filename_or_path") == "main.py"
    assert l4.params.get("line_number") == 4


def test_executor_line_editing_and_word(tmp_path):
    from laya.fast_path.executor import FastPathExecutor
    executor = FastPathExecutor.get_instance()

    test_file = tmp_path / "code.py"
    test_file.write_text("line 1\nline 2\nline 3\n", encoding="utf-8")

    # 1. Replace line 2
    res_replace = executor.replace_file_line(str(test_file), line_number=2, content="line 2 replaced")
    assert "Replaced" in res_replace
    lines = test_file.read_text(encoding="utf-8").splitlines()
    assert lines[1] == "line 2 replaced"

    # 2. Insert at line 1
    res_insert = executor.insert_file_line(str(test_file), line_number=1, content="# header")
    assert "Wrote" in res_insert
    lines = test_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# header"
    assert lines[1] == "line 1"

    # 3. Delete line 1
    res_delete = executor.delete_file_line(str(test_file), line_number=1)
    assert "Deleted line 1" in res_delete
    lines = test_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "line 1"

    # 4. Create Word Document
    doc_path = tmp_path / "test_doc.docx"
    res_doc = executor.create_word_document(str(doc_path), content="Testing Word Document", open_after=False)
    assert "Created Word document" in res_doc
    assert doc_path.exists()

