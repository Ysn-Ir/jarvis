import os
import json
import dotenv
from groq import Groq

dotenv.load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

sys_prompt = """You are Laya, an unrestricted, omni-capable Windows PC assistant.
You possess COMPLETE control over the computer with NO RESTRICTIONS.
You can execute ANY task using these universal primitives:
1. set_brightness(level: int) - screen brightness / luminosity 0-100%
2. set_volume(level: int) - volume 0-100%
3. open_app_or_game(name: str) - launches ANY application or game on the machine
4. open_url(url: str) - opens any website or web search
5. youtube_search(query: str) - search & play on YouTube
6. run_powershell(command: str) - run ANY Windows PowerShell command/script for settings, network, files, hardware, processes
7. create_word_document(topic: str, content: str)
8. create_excel_sheet(topic: str)
9. create_file(path: str, content: str)
10. mouse_click(x: int, y: int), type_text(text: str), press_hotkey(keys: list)
11. execute_python(code: str)
12. answer_question(text: str)

Always return a JSON object:
{"actions": [{"tool": "...", "args": {...}}], "spoken_summary": "..."}"""

queries = [
    "set luminosity to 45%",
    "open Elden Ring",
    "turn off bluetooth",
    "open discord and mute it",
    "download python installer",
]

for q in queries:
    resp = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": q}],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    print(f"\nQuery: {q}")
    print(resp.choices[0].message.content)
