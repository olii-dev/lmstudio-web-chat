#!/usr/bin/env python3
# lm_web_chat.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib import request, error

HTML_PORT = 8080
LM_PORT = 1234
MODEL_ID = "google/gemma-3-12b"

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>LM Studio — Desktop Chat (Light/Dark)</title>
<style>
:root{
  --muted: #9aa4b2;
  --user: #007aff;
  --ai: #2f2f2f;
  --white: #ffffff;
  --bg: transparent;
  --panel: rgba(0,0,0,0.04);
  --text: #ffffff;
  --code-bg: #0b0b0b;
  --code-color: #e6e6e6;
}

/* Light theme variables */
:root[data-theme="light"]{
  --muted: #6b7280;
  --user: #0b63ff;
  --ai: #e9eef6;
  --white: #0b0b0b;
  --bg: #ffffff;
  --panel: rgba(0,0,0,0.04);
  --text: #0b0b0b;
  --code-bg: #f5f5f7;
  --code-color: #0b0b0b;
}

/* Dark theme defaults (used when data-theme != "light") */
:root[data-theme="dark"]{
  --muted: #9aa4b2;
  --user: #007aff;
  --ai: #2f2f2f;
  --white: #ffffff;
  --bg: #121212;
  --panel: #1c1c1c;
  --text: #ffffff;
  --code-bg: #0b0b0b;
  --code-color: #e6e6e6;
}

html,body{height:100%;margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial;background:var(--bg);color:var(--text);}
body{display:flex;justify-content:center;align-items:stretch;height:100vh;}
#container{width:900px;max-width:95%;display:flex;flex-direction:column;height:100vh;box-sizing:border-box;}
.header{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(0,0,0,0.06);font-weight:600;color:inherit;background:transparent}
#messages{flex:1;padding:20px;overflow:auto;display:flex;flex-direction:column;gap:12px;scroll-behavior:smooth;background:transparent;}
.msg{max-width:76%;padding:12px 14px;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,0.08);word-break:break-word;white-space:pre-wrap;}
.msg.user{align-self:flex-end;background:var(--user);color:var(--white);border-bottom-right-radius:6px;}
.msg.ai{align-self:flex-start;background:var(--ai);color:var(--text);border-bottom-left-radius:6px;}
.msg .codeblock{display:block;background:var(--code-bg);padding:10px;border-radius:8px;color:var(--code-color);overflow:auto;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, "Courier New", monospace;font-size:13px;white-space:pre-wrap}
.msg code{background:rgba(255,255,255,0.06);padding:2px 6px;border-radius:6px;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, "Courier New", monospace;}
.msg a{color:inherit;text-decoration:underline}
.timestamp{font-size:11px;color:var(--muted);margin-top:6px;}
#input-area{display:flex;padding:12px;gap:10px;border-top:1px solid rgba(0,0,0,0.06);background:transparent;}
#input{flex:1;min-height:44px;max-height:300px;padding:10px 12px;border-radius:10px;border:none;background:var(--panel);color:var(--text);outline:none;resize:none;font-size:15px;line-height:1.35;}
#send{background:var(--user);border:none;color:var(--white);padding:10px 14px;border-radius:10px;cursor:pointer;font-weight:600}
#theme-toggle{background:transparent;border:1px solid rgba(0,0,0,0.06);padding:6px 10px;border-radius:8px;color:inherit;cursor:pointer}
.typing-dots{display:inline-block;height:14px}
.typing-dots span{display:inline-block;width:6px;height:6px;margin:0 3px;border-radius:50%;background:var(--muted);opacity:0.6;animation:blink 1s infinite}
.typing-dots span:nth-child(2){animation-delay:0.12s}
.typing-dots span:nth-child(3){animation-delay:0.24s}
@keyframes blink{0%{opacity:0.2}50%{opacity:1}100%{opacity:0.2}}
</style>
</head>
<body>
  <div id="container">
    <div class="header">
      <div>LM Studio — Desktop Chat</div>
      <div style="display:flex;gap:8px;align-items:center">
        <button id="theme-toggle" aria-label="Toggle theme">Toggle theme</button>
      </div>
    </div>
    <div id="messages" aria-live="polite"></div>
    <div id="input-area">
      <textarea id="input" rows="1"></textarea>
      <button id="send">Send</button>
    </div>
  </div>

<script>
const API_URL = "http://localhost:__HTML_PORT__/v1/chat/completions";
const MODEL_ID = "__MODEL_ID__";

const messages = document.getElementById('messages');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const themeToggle = document.getElementById('theme-toggle');

// Theme handling: read from localStorage, default to dark
function applyTheme(theme) {
  if (!theme) theme = 'dark';
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
  themeToggle.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
}
const initial = localStorage.getItem('theme') || 'dark';
applyTheme(initial);

// Toggle theme button
themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
});

// Utilities
function scrollToBottom() { messages.scrollTop = messages.scrollHeight; }

function createMessageElement(html, cls) {
  const el = document.createElement('div');
  el.className = 'msg ' + cls;
  el.innerHTML = html;
  messages.appendChild(el);
  scrollToBottom();
  return el;
}

function renderMarkdown(md) {
  if (!md) return '';
  let text = String(md);
  // escape
  text = text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');

  const codeBlocks = [];
  text = text.replace(/```([\s\S]*?)```/g, function(_, code) {
    codeBlocks.push(code);
    return `__CODEBLOCK_PLACEHOLDER_${codeBlocks.length - 1}__`;
  });

  text = text.replace(/`([^`\n]+?)`/g, function(_, c){ return '<code>' + c + '</code>'; });

  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function(_, t, u){
    return '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + t + '</a>';
  });

  text = text.replace(/(\*\*|__)(.*?)\1/g, function(_, __, inner){ return '<strong>' + inner + '</strong>'; });
  text = text.replace(/(\*|_)([^*_].*?)\1/g, function(_, __, inner){ return '<em>' + inner + '</em>'; });

  text = text.replace(/\r\n|\r|\n/g, '<br>');

  text = text.replace(/__CODEBLOCK_PLACEHOLDER_(\d+)__/g, function(_, idx){
    const codeText = codeBlocks[parseInt(idx,10)] || '';
    return '<div class="codeblock"><pre><code>' + codeText + '</code></pre></div>';
  });

  return text;
}

function appendMessage(rawText, cls) {
  const html = renderMarkdown(rawText);
  return createMessageElement(html, cls);
}

function createTypingBubble() {
  const el = document.createElement('div');
  el.className = 'msg ai';
  const dots = document.createElement('span');
  dots.className = 'typing-dots';
  dots.innerHTML = '<span></span><span></span><span></span>';
  el.appendChild(dots);
  messages.appendChild(el);
  scrollToBottom();
  return el;
}

// autosize textarea
function autosize() {
  input.style.height = 'auto';
  input.style.height = (input.scrollHeight) + 'px';
}
input.addEventListener('input', autosize);

// send message
async function sendMessage() {
  const text = input.value;
  if (!text.trim()) return;
  appendMessage(text, 'user');
  input.value = '';
  autosize();

  const typingBubble = createTypingBubble();

  try {
    const payload = { model: MODEL_ID, messages: [{ role: "user", content: text }] };
    const resp = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
      const txt = await resp.text();
      typingBubble.textContent = 'Error: ' + resp.status + ' ' + txt;
      return;
    }

    const data = await resp.json();
    const reply = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) ? data.choices[0].message.content : JSON.stringify(data);

    // replace typing bubble with rendered typing animation (char by char)
    typingBubble.innerHTML = '';
    let i = 0, out = '';
    function step() {
      if (i < reply.length) {
        out += reply[i++];
        typingBubble.innerHTML = renderMarkdown(out);
        scrollToBottom();
        setTimeout(step, 16);
      }
    }
    step();

  } catch (err) {
    typingBubble.textContent = 'Error connecting to LM Studio';
    console.error(err);
  }
}

// Enter = send, Shift+Enter = newline
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    if (e.shiftKey) {
      return; // allow newline
    } else {
      e.preventDefault();
      sendMessage();
    }
  }
});

sendBtn.addEventListener('click', sendMessage);

// focus input on load
input.focus();
autosize();
</script>
</body>
</html>
"""

HTML_PAGE = HTML_TEMPLATE.replace("__HTML_PORT__", str(HTML_PORT)).replace("__MODEL_ID__", MODEL_ID)

class ChatHandler(BaseHTTPRequestHandler):
    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/chat.html":
            data = HTML_PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._set_cors()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length) if length else b''
                lm_url = f"http://localhost:{LM_PORT}/v1/chat/completions"
                req = request.Request(lm_url, data=body, headers={'Content-Type': 'application/json'})
                with request.urlopen(req, timeout=60) as resp:
                    resp_data = resp.read()
                    status = resp.getcode()
                    content_type = resp.headers.get('Content-Type', 'application/json')
                    self.send_response(status)
                    self.send_header("Content-Type", content_type)
                    self._set_cors()
                    self.send_header("Content-Length", str(len(resp_data)))
                    self.end_headers()
                    self.wfile.write(resp_data)
            except error.HTTPError as he:
                msg = he.read().decode('utf-8', errors='ignore')
                payload = json.dumps({"error": f"Upstream HTTPError {he.code}", "detail": msg}).encode('utf-8')
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._set_cors()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                payload = json.dumps({"error": "Proxy error", "detail": str(e)}).encode('utf-8')
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self._set_cors()
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        else:
            self.send_error(404, "Not Found")

def run():
    server = HTTPServer(('localhost', HTML_PORT), ChatHandler)
    print(f"LM web chat running at http://localhost:{HTML_PORT}")
    print(f"Proxying /v1/chat/completions -> http://localhost:{LM_PORT}/v1/chat/completions")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down")
        server.server_close()

if __name__ == "__main__":
    run()