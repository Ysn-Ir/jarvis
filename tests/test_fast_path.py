import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from laya.router import get_intent_router, ExecutionPath
from laya.fast_path import get_fast_path_executor


def test_fast_path_classification_speed():
    router = get_intent_router()
    test_queries = [
        "raise the volume",
        "turn down the volume",
        "set volume to 60",
        "mute audio",
        "check battery",
        "check ram",
        "what is my ip",
        "what time is it",
        "who are you",
        "close this",
        "open spotify",
        "open chrome",
        "format C: /y",
        "rm -rf / --no-preserve-root",
        "shut down the computer",
    ]

    latencies = []
    for q in test_queries:
        t0 = time.perf_counter()
        decision = router.route(q)
        dt = (time.perf_counter() - t0) * 1000
        latencies.append(dt)
        assert decision is not None

    avg_latency = sum(latencies) / len(latencies)
    print(f"\n[Router Benchmark] Average routing latency: {avg_latency:.3f}ms (Max: {max(latencies):.3f}ms)")
    # Must be sub-5ms
    assert avg_latency < 5.0, f"Router too slow: {avg_latency}ms"


def test_safety_guardrail():
    router = get_intent_router()
    decision = router.route("format C: /y")
    assert decision.path == ExecutionPath.BLOCKED_SAFETY

    decision2 = router.route("rm -rf / --no-preserve-root")
    assert decision2.path == ExecutionPath.BLOCKED_SAFETY


def test_fast_path_hardware_diagnostics():
    executor = get_fast_path_executor()
    
    t0 = time.perf_counter()
    battery_res = executor.check_battery()
    t_battery = (time.perf_counter() - t0) * 1000
    assert "Battery" in battery_res or "AC" in battery_res
    assert t_battery < 100.0

    t0 = time.perf_counter()
    ram_res = executor.check_ram()
    t_ram = (time.perf_counter() - t0) * 1000
    assert "RAM" in ram_res
    assert t_ram < 50.0

    t0 = time.perf_counter()
    time_res = executor.query_time()
    t_time = (time.perf_counter() - t0) * 1000
    assert "time is" in time_res
    assert t_time < 5.0


if __name__ == "__main__":
    test_fast_path_classification_speed()
    test_safety_guardrail()
    test_fast_path_hardware_diagnostics()
    print("All Fast Path & Router tests PASSED!")
