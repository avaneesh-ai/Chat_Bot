from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib import error, request
from uuid import uuid4


APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
HOST = "127.0.0.1"
PORT = 8000
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3"

TEMPLATE = """
Answer the question below.

Here is the conversation history: {context}

question: {question}

Answer:

"""

CONVERSATIONS = {}


def build_prompt(context, question):
    return TEMPLATE.format(context=context, question=question)


def ask_ollama(prompt):
    payload = json.dumps(
        {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")

    req = request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "").strip()
    except error.URLError as exc:
        raise RuntimeError(
            "Ollama is not reachable. Start Ollama and make sure the llama3 model is available."
        ) from exc


def make_json_response(handler, status, payload):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class ChatHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_HEAD(self):
        if self.path in {"/", "/index.html"}:
            self.serve_head(STATIC_DIR / "index.html", "text/html")
            return

        static_path = STATIC_DIR / self.path.lstrip("/")
        content_type = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".svg": "image/svg+xml",
        }.get(static_path.suffix, "application/octet-stream")

        if static_path.exists() and static_path.is_file():
            self.serve_head(static_path, content_type)
            return

        self.send_error(404)

    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            self.serve_file(STATIC_DIR / "index.html", "text/html")
            return

        static_path = STATIC_DIR / self.path.lstrip("/")
        content_type = {
            ".css": "text/css",
            ".js": "application/javascript",
            ".svg": "image/svg+xml",
        }.get(static_path.suffix, "application/octet-stream")

        if static_path.exists() and static_path.is_file():
            self.serve_file(static_path, content_type)
            return

        self.send_error(404)

    def do_POST(self):
        if self.path == "/api/chat":
            self.handle_chat()
            return

        if self.path == "/api/clear":
            self.handle_clear()
            return

        self.send_error(404)

    def serve_file(self, path, content_type):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_head(self, path, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}

        raw_body = self.rfile.read(length).decode("utf-8")
        return json.loads(raw_body)

    def handle_chat(self):
        try:
            body = self.read_json_body()
            question = body.get("message", "").strip()
            session_id = body.get("sessionId") or uuid4().hex

            if not question:
                make_json_response(self, 400, {"error": "Please enter a message."})
                return

            context = CONVERSATIONS.get(session_id, "")
            prompt = build_prompt(context, question)
            answer = ask_ollama(prompt)
            CONVERSATIONS[session_id] = f"{context}\nUser: {question}\nAI: {answer}"

            make_json_response(
                self,
                200,
                {
                    "reply": answer,
                    "sessionId": session_id,
                },
            )
        except json.JSONDecodeError:
            make_json_response(self, 400, {"error": "The request was not valid JSON."})
        except RuntimeError as exc:
            make_json_response(self, 503, {"error": str(exc)})
        except Exception:
            make_json_response(self, 500, {"error": "Something went wrong."})

    def handle_clear(self):
        try:
            body = self.read_json_body()
            session_id = body.get("sessionId")
            if session_id:
                CONVERSATIONS.pop(session_id, None)

            make_json_response(self, 200, {"ok": True})
        except Exception:
            make_json_response(self, 500, {"error": "Could not clear the chat."})


def main():
    server = ThreadingHTTPServer((HOST, PORT), ChatHandler)
    print(f"AI ChatBot is running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
