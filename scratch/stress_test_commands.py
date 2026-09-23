import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis_controller import JarvisController

controller = JarvisController()

test_cmds = [
    "open word and write hello world",
    "open the word and write hello world",
    "open word and write a letter to my boss",
    "open notepad and write hello world",
    "open notebook and write meeting notes",
    "open whatsapp and send a message to mom saying hello",
    "open whatsapp and send a message to ysn saying hi",
    "open whatsapp and send a message to يس saying سلام",
    "send an email to boss@company.com saying I will be late",
    "open chrome",
    "open youtube",
    "open spotify",
    "open settings",
    "open downloads",
    "close notepad",
    "close chrome",
    "what time is it",
    "who are you",
    "tell me a joke",
    "what is quantum computing",
    "volume up",
    "volume down",
    "set volume to 50",
    "mute",
    "take a screenshot",
    "lock pc",
    "check battery",
    "check ram",
    "what is my ip",
    "search for weather today",
    "create a folder named test",
    "create a file named hello.txt",
]

print("\n" + "="*80)
print(f"{'Command':<45} | {'Domain':<12} | {'Action':<15} | {'Status':<8} | {'Message'}")
print("="*80)

for cmd in test_cmds:
    try:
        res = controller.process(cmd)
        domain = res.get("domain", "")
        action = res.get("action", "")
        status = res.get("status", "")
        msg = str(res.get("message", ""))[:45]
        print(f"{cmd:<45} | {domain:<12} | {action:<15} | {status:<8} | {msg}")
    except Exception as e:
        print(f"{cmd:<45} | ERROR: {e}")
