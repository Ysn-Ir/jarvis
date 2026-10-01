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
