from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib import request
import threading
import time

HTML_PORT = 8080
LM_PORT = 1234
MODEL_ID = "google/gemma-3-12b"

HTML_PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LM Studio Chat</title>
<style>
body {{ font-family: system-ui; background:#121212; color:#fff; display:flex; flex-direction:column; height:100vh; margin:0; }}
#messages {{ flex:1; overflow-y:auto; padding:1em; display:flex; flex-direction:column; }}
.msg {{ margin:0.5em 0; max-width:70%; padding:0.6em 1em; border-radius:15px; line-height:1.4; word-wrap:break-word; }}
.user {{ background:#007aff; align-self:flex-end; color:white; }}
.ai {{ background:#333; align-self:flex-start; color:white; }}
#input-area {{ display:flex; padding:0.5em; background:#1c1c1c; }}
#input {{ flex:1; padding:0.6em; border:none; outline:none; background:#2b2b2b; color:white; border-radius:10px; }}
button {{ margin-left:0.5em; padding:0.6em 1em; border:none; border-radius:10px; background:#007aff; color:white; cursor:pointer; }}
.typing {{ font-style:italic; opacity:0.7; }}
</style>
</head>
<body>
<div id="messages"></div>
<div id="input-area">
  <input id="input" placeholder="Type a message...">
  <button id="send">Send</button>
</div>
<script>
const API_URL = "http://localhost:{HTML_PORT}/v1/chat/completions";
const MODEL_ID = "{MODEL_ID}";

const messagesDiv = document.getElementById("messages");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");

function addMessage(text, type, typing=false){{
    const msg = document.createElement("div");
    msg.textContent = text;
    msg.className = "msg " + type;
    if(typing) msg.classList.add("typing");
    messagesDiv.appendChild(msg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return msg;
}}

async function sendMessage(){{
    const userText = input.value.trim();
    if(!userText) return;
    addMessage(userText,"user");
    input.value = "";

    const typingMsg = addMessage("AI is typing...","ai",true);

    try{{
        const response = await fetch(API_URL,{{
            method:"POST",
            headers:{{"Content-Type":"application/json"}},
            body:JSON.stringify({{ model: MODEL_ID, messages:[{{role:"user", content:userText}}] }})
        }});
        const data = await response.json();
        const reply = data.choices?.[0]?.message?.content || "No response.";

        // Typing animation effect
        let i=0;
        typingMsg.textContent="";
        typingMsg.classList.remove("typing");
        const interval = setInterval(()=>{{
            typingMsg.textContent += reply[i];
            i++;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            if(i>=reply.length) clearInterval(interval);
        }},20);

    }}catch(err){{
        typingMsg.textContent="Error connecting to LM Studio.";
        typingMsg.classList.remove("typing");
        console.error(err);
    }}
}}

sendBtn.addEventListener("click", sendMessage);
input.addEventListener("keypress", e=>{{if(e.key==="Enter") sendMessage();}});
</script>
</body>
</html>
"""

class ChatHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path == "/chat.html":
            self._set_headers("text/html")
            self.wfile.write(HTML_PAGE.encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            req = request.Request(f"http://localhost:{LM_PORT}/v1/chat/completions", data=post_body, headers={'Content-Type':'application/json'})
            try:
                with request.urlopen(req) as resp:
                    data = resp.read()
                    self._set_headers()
                    self.wfile.write(data)
            except Exception as e:
                self._set_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_error(404)

def run_server():
    server = HTTPServer(('localhost', HTML_PORT), ChatHandler)
    print(f"Chat server running at http://localhost:{HTML_PORT}")
    server.serve_forever()

if __name__=="__main__":
    run_server()