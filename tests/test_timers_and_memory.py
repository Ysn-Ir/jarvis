import pytest
from laya.router.classifier import IntentRouter
from laya.router.taxonomy import ExecutionPath
from laya.orchestrator.memory import get_memory_store
from laya.fast_path.executor import get_executor


def test_timer_and_reminder_routing():
    router = IntentRouter.get_instance()
    
    # Duration timers
    d = router.route("set a timer for 5 minutes")
    assert d.action == "set_reminder"
    assert d.path == ExecutionPath.FAST_PATH
    assert d.params["minutes"] == 5.0

    d = router.route("start a timer for 10 minutes")
    assert d.action == "set_reminder"
    assert d.path == ExecutionPath.FAST_PATH
    assert d.params["minutes"] == 10.0

    d = router.route("timer for 30 seconds")
    assert d.action == "set_reminder"
    assert d.path == ExecutionPath.FAST_PATH
    assert d.params["seconds"] == 30.0

    # Bare timer -> clarify
    d = router.route("set a timer")
    assert d.action == "clarify"
    assert d.path == ExecutionPath.CLARIFY
    assert "How many minutes or seconds" in d.clarification_prompt

    # Relative reminder
    d = router.route("remind me in 15 minutes to check the oven")
    assert d.action == "set_reminder"
    assert d.path == ExecutionPath.FAST_PATH
    assert d.params["minutes"] == 15.0
    assert d.params["message"] == "check the oven"

    # Listing & cancelling
    d = router.route("show my timers")
    assert d.action == "list_reminders"
    assert d.path == ExecutionPath.FAST_PATH

    d = router.route("cancel timer")
    assert d.action == "cancel_reminders"
    assert d.path == ExecutionPath.FAST_PATH


def test_memory_and_identity_routing():
    router = IntentRouter.get_instance()

    d = router.route("who am i")
    assert d.action == "who_am_i"
    assert d.path == ExecutionPath.FAST_PATH

    d = router.route("what is my name")
    assert d.action == "who_am_i"
    assert d.path == ExecutionPath.FAST_PATH

    d = router.route("my name is Yasin")
    assert d.action == "update_user_profile"
    assert d.path == ExecutionPath.FAST_PATH
    assert d.params["key"] == "name"
    assert d.params["value"].lower() == "yasin"

    d = router.route("my role is AI Engineer")
    assert d.action == "update_user_profile"
    assert d.path == ExecutionPath.FAST_PATH
    assert d.params["key"] == "role"
    assert d.params["value"].lower() == "ai engineer"

    d = router.route("remember that my favorite color is teal")
    assert d.action == "save_user_fact"
    assert d.path == ExecutionPath.FAST_PATH
    assert "favorite color is teal" in d.params["fact"]


def test_memory_store_execution():
    mem = get_memory_store()
    mem.clean_messy_memory()

    # User profile
    mem.set_profile("name", "Yasin")
    assert mem.get_profile("name") == "Yasin"

    # Add fact with prefix stripping
    msg = mem.add_fact("remember that I prefer dark mode")
    assert "Remembered" in msg

    # Conversational noise should be ignored
    ignored = mem.add_fact("hello how are you")
    assert "Filtered" in ignored or "Ignored" in ignored

    # Timer execution
    rem_msg = mem.add_reminder("timer: test timer", seconds=20)
    assert "Timer set" in rem_msg or "Reminder set" in rem_msg

    # Cancellation
    cancel_msg = mem.cancel_reminders("all")
    assert "Cancelled" in cancel_msg or "No active" in cancel_msg


def test_executor_memory_methods():
    executor = get_executor()

    # who am i
    resp = executor.who_am_i()
    assert "Yasin" in resp or "sir" in resp

    # update profile
    u_resp = executor.update_user_profile("city", "Paris")
    assert "Paris" in u_resp

    # save user fact
    f_resp = executor.save_user_fact("User loves building autonomous AI agents")
    assert "Remembered" in f_resp
