import os
import anthropic
from flask import current_app

_FACT_BASE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "static", "about", "prezent_energy_fact_base.txt"
)

with open(os.path.normpath(_FACT_BASE_PATH), encoding="utf-8") as _f:
    _fact_base = _f.read()

SYSTEM_PROMPT = f"""You are the Prezent.Energy AI assistant — a knowledgeable, professional guide
for potential clients exploring our Charging-as-a-Service (CaaS) platform.

Use the fact base below as your sole source of truth. Do not invent specifications not listed here.
If uncertain about a detail, say "our team can confirm that during your demo call."
Always end responses with a soft CTA inviting the user to schedule a demo or fill out the form.

--- FACT BASE ---
{_fact_base}
--- END FACT BASE ---

Response style: concise, confident, and technically authoritative. When asked about pricing,
compatibility, or timelines, cite specific numbers from the fact base above.
"""


def get_chat_response(messages: list[dict]) -> str:
    """
    Send a conversation to Claude and return the assistant reply.
    `messages` is a list of {"role": "user"/"assistant", "content": "..."} dicts.
    """
    client = anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text
