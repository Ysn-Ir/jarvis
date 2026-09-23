"""
Multi-turn conversational reasoning, context resolution, and memory test.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from laya.main import LayaAssistant

assistant = LayaAssistant()

print("\n--- Test 1: Multi-Turn File & Folder Path Resolution ---")
r1 = assistant.handle_command("On the desktop create a new folder named ProjectX", speak=False)
print("Turn 1:", r1)
assert "ProjectX" in r1

r2 = assistant.handle_command("In this folder create a python file named main.py", speak=False)
print("Turn 2:", r2)
assert "main.py" in r2

r3 = assistant.handle_command("Where is that file located and what is its path?", speak=False)
print("Turn 3:", r3)
assert "main.py" in r3 or "ProjectX" in r3 or "Desktop" in r3

print("\n--- Test 2: Multi-Turn Durable Memory ---")
r4 = assistant.handle_command("Remember that my flight is at 6pm tomorrow", speak=False)
print("Turn 4:", r4)

r5 = assistant.handle_command("What did I ask you to remember?", speak=False)
print("Turn 5:", r5)
assert "6pm" in r5 or "flight" in r5

print("\n--- Test 3: Multi-Turn Pronoun & Contact Resolution ---")
r6 = assistant.handle_command("The contact name is ysn", speak=False)
print("Turn 6:", r6)

r7 = assistant.handle_command("Send him a message via WhatsApp saying hello", speak=False)
print("Turn 7:", r7)

print("\n🎉 MULTI-TURN VERIFICATION COMPLETED SUCCESSFULLY!")
