import os
import json
import time
import dotenv
from groq import Groq

dotenv.load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

system_prompt = """You are Laya, an autonomous Windows PC desktop assistant.
Convert ANY user utterance into an executable sequence of one or more tool actions.
You are NOT restricted to fixed commands. You handle complex, multi-step, spoken requests naturally.

Available Tools:
- youtube_search(query: str): Open YouTube and search for video/creator.
- web_search(query: str): Search Google or web.
- open_url(url: str): Open specific URL in browser.
- open_app(name: str): Launch any application (e.g. 'chrome', 'spotify', 'notepad', 'word', 'calculator').
- close_app(name: str): Close an application or window.
- set_volume(level: int): Set volume between 0 and 100.
- volume_up(steps: int = 5): Increase volume.
- volume_down(steps: int = 5): Decrease volume.
- mute(): Mute/unmute audio.
- create_note(content: str): Create text note in Notepad.
- create_word_document(topic: str, content: str = ""): Create formatted Word document.
- create_excel_sheet(topic: str): Create Excel spreadsheet.
- send_whatsapp(contact: str, message: str): Send message to contact.
- send_email(recipient: str, subject: str, body: str): Draft/send email.
- take_screenshot(): Capture screenshot.
- lock_workstation(): Lock PC screen.
- check_system(metric: str): Check battery, ram, cpu, or ip.
- answer_question(text: str): General knowledge, time, date, chit-chat, or joke.

Return ONLY a valid JSON object:
{
  "actions": [
    {"tool": "tool_name", "args": {"arg1": "value"}}
  ],
  "spoken_summary": "Short confirmation to speak to user"
}
"""

queries = [
    "Open YouTube for MrBeast",
    "I open the notebook and write me an email",
    "He's up the volume to the maximum",
    "raise up the volume",
    "Open cromancers for Mr. Beast",
    "Open spotify and play music then set volume to 80",
]

for q in queries:
    t0 = time.time()
    resp = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    dt = (time.time() - t0) * 1000
    print(f"\nQuery: '{q}' ({dt:.1f}ms)")
    print(resp.choices[0].message.content)
