"""
ai_engine.py — Gemini Flash integration for mouse.ai
Handles both image analysis (Mode 1) and text analysis (Mode 2).
"""

import time
import threading
from google import genai
from google.genai import types


IMAGE_PROMPT = """You are a smart screen assistant. The user captured a region of their screen.

Analyze what's visible and respond helpfully:

• **Text content** → Read it, then briefly summarize or explain the key point.
• **Code** → Identify the language, explain what the code does in plain English.
• **Chart / Graph** → Describe the data, trends, and key takeaways.
• **Image / UI** → Describe what you see and any notable details.
• **Error message** → Explain the error and suggest a fix.
• **Math / Formula** → Solve it or explain the concept.

Rules:
- Be direct. No filler phrases like "This image shows..." — just get to the point.
- Use short paragraphs. Keep it scannable.
- If there's text, always include the exact text first, then your explanation.
- Max 4–5 sentences unless the content genuinely needs more.
"""

TEXT_PROMPT = """You are a smart text assistant. The user selected and highlighted this text from their screen.

Respond based on what the text is:

• **Word or phrase** → Define it clearly.
• **Technical term** → Explain in simple language.
• **Code snippet** → Explain what it does.
• **Error / log** → Diagnose the issue and suggest a fix.
• **URL** → Describe where it leads.
• **Long paragraph** → Summarize the key point.
• **Question** → Answer it directly.
• **Number / data** → Provide context (e.g., unit conversion, meaning).

Rules:
- Be direct and concise. Skip filler like "This text is..." or "The selected text...".
- If the text is short (< 10 words), give a focused explanation.
- If the text is long, summarize first, then add detail.
- Max 3–5 sentences unless it genuinely needs more.

Selected text:
---
{text}
---
"""


class AIEngine:
    """Wrapper around Gemini Flash for image and text analysis."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def analyze_image(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Send a screenshot to Gemini and get analysis."""
        try:
            return self._call_with_retry(
                contents=[
                    IMAGE_PROMPT,
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                ]
            )
        except Exception as e:
            return f"Error: {e}"

    def analyze_text(self, text: str) -> str:
        """Send selected text to Gemini for explanation."""
        if not text.strip():
            return "No text selected."
        try:
            prompt = TEXT_PROMPT.format(text=text)
            return self._call_with_retry(contents=[prompt])
        except Exception as e:
            return f"Error: {e}"

    def _call_with_retry(self, contents: list, max_retries: int = 3) -> str:
        """Call Gemini API with exponential backoff for rate limits."""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
                return response.text or "No response from AI."
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate" in error_str:
                    wait = (2 ** attempt) + 1
                    time.sleep(wait)
                    continue
                raise
        return "Rate limit exceeded. Try again in a moment."

    def analyze_image_async(self, image_bytes: bytes, callback, mime_type: str = "image/png"):
        """Run image analysis in background thread."""
        def _worker():
            result = self.analyze_image(image_bytes, mime_type)
            callback(result)
        threading.Thread(target=_worker, daemon=True).start()

    def analyze_text_async(self, text: str, callback):
        """Run text analysis in background thread."""
        def _worker():
            result = self.analyze_text(text)
            callback(result)
        threading.Thread(target=_worker, daemon=True).start()
