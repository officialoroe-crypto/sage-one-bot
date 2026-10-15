"""A tiny OpenAI-compatible server for LOCAL TESTING ONLY.

It lets you test the whole SAGE pipeline (website -> server -> worker -> AI provider -> answer)
without a paid AI key. It is not used in production and its answers are test text, not intelligence.

    python scripts/dev_test_llm.py            # listens on 127.0.0.1:11434
    SAGE_PREFER_LOCAL=true python -m uvicorn app.main:app

Real use: put a real key (GEMINI_API_KEY, GROQ_API_KEY, ...) in .env instead.
"""
from __future__ import annotations

import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "llama3.2:3b"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):  # keep the console quiet
        pass

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            return self._send(200, {"object": "list", "data": [{"id": MODEL, "object": "model", "created": 0, "owned_by": "test"}]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or b"{}")
        msgs = req.get("messages", [])
        last = next((m.get("content", "") for m in reversed(msgs) if m.get("role") == "user"), "")
        system = " ".join(str(m.get("content", "")) for m in msgs if m.get("role") == "system")
        json_mode = (req.get("response_format") or {}).get("type") in ("json_object", "json_schema")
        if "mission planner" in system:
            text = json.dumps({
                "mission_summary": "Answer the user's message",
                "tasks": [{
                    "id": "task_1", "title": "Answer the user",
                    "description": f"Reply helpfully to: {str(last)[:300]}",
                    "agent": "general", "priority": 1, "depends_on": [],
                    "verification": ["A reply was produced"],
                }],
                "mission_verification": ["The user received a reply"],
            })
        elif "verification agent" in system:
            text = json.dumps({"passed": True, "evidence": "test verifier: output present"})
        elif "result synthesizer" in system or json_mode:
            text = json.dumps({"summary": f"[test AI] I received: {str(last)[:160]}",
                               "key_results": [], "next_actions": [], "confidence": "test"})
        else:
            text = f"[test AI] I received: {str(last)[:200]}"
        self._send(200, {
            "id": "test-1", "object": "chat.completion", "created": int(time.time()), "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11434
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
