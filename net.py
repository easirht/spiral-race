# net.py - WebSocket + share helper for the web build (polling, no callbacks)
import json
import sys

IS_WEB = sys.platform == "emscripten"
if IS_WEB:
    import platform

URL = "wss://spiral-server.onrender.com/ws"
HTTP = "https://spiral-server.onrender.com/"

JS = """
window.sr = {ws:null, q:[], err:''};
window.sr_connect = function(url){
  try{ if(window.sr.ws){ window.sr.ws.onclose=null; window.sr.ws.close(); } }catch(e){}
  window.sr.q=[]; window.sr.err='';
  try{
    var w=new WebSocket(url);
    window.sr.ws=w;
    w.onmessage=function(e){ window.sr.q.push(e.data); };
    w.onerror=function(){ window.sr.err='error'; };
  }catch(e){ window.sr.err=String(e); }
};
window.sr_state=function(){ return window.sr.ws ? window.sr.ws.readyState : -1; };
window.sr_send=function(s){ var w=window.sr.ws; if(w && w.readyState===1){ w.send(s); return 1; } return 0; };
window.sr_pop=function(){ return window.sr.q.length ? window.sr.q.shift() : ''; };
window.sr_close=function(){ try{ if(window.sr.ws){ window.sr.ws.onmessage=null; window.sr.ws.close(); } }catch(e){} window.sr.ws=null; window.sr.q=[]; };
window.sr_warm=function(u){ try{ fetch(u,{mode:'no-cors'}); }catch(e){} };
window.sr_copy=function(t){ try{ navigator.clipboard.writeText(t).catch(function(){ window.prompt('Copy this link:',t); }); }catch(e){ window.prompt('Copy this link:',t); } };
window.sr_share=function(u,t){
  try{
    if(navigator.share){ navigator.share({title:'Spiral Race',text:t,url:u}).catch(function(){}); return 'shared'; }
  }catch(e){}
  window.sr_copy(u); return 'copied';
};
window.sr_room=function(){ try{ return (new URLSearchParams(window.location.search).get('room')||''); }catch(e){ return ''; } };
window.sr_size=function(){ return window.innerWidth+','+window.innerHeight; };
"""


class Net:
    def __init__(self):
        self.connecting = False
        self.connected = False
        self.error = ""
        self.pending = None
        self.t = 0.0
        self.last = 0.0
        self.none_count = 0
        self._ready = False

    # ----- low level -----
    def _setup(self):
        if IS_WEB and not self._ready:
            try:
                platform.window.eval(JS)
                self._ready = True
            except Exception:
                pass

    def _js(self, name, *args):
        if not IS_WEB:
            return None
        try:
            return getattr(platform.window, name)(*args)
        except Exception:
            try:
                call = name + "(" + ",".join(json.dumps(a) for a in args) + ")"
                return platform.window.eval(call)
            except Exception:
                return None

    @staticmethod
    def _int(v):
        try:
            return int(v)
        except Exception:
            return None

    # ----- public -----
    def warm(self):
        self._setup()
        self._js("sr_warm", HTTP)

    def room_param(self):
        self._setup()
        r = self._js("sr_room")
        r = str(r or "").upper().strip()
        return r[:4] if r.isalpha() else ""

    def window_size(self):
        """Browser window size (w, h) or None when not on the web."""
        if not IS_WEB:
            return None
        self._setup()
        try:
            s = str(self._js("sr_size"))
            w, h = s.split(",")
            return int(float(w)), int(float(h))
        except Exception:
            return None

    def connect(self, first_msg):
        self.error = ""
        self.pending = first_msg
        self.connected = False
        self.t = 0.0
        self.last = 0.0
        self.none_count = 0
        if not IS_WEB:
            self.connecting = False
            self.error = "Online play works in the web version only"
            return
        self.connecting = True
        self._setup()
        self._js("sr_connect", URL)

    def send(self, msg):
        self._js("sr_send", json.dumps(msg))

    def copy(self, text):
        self._js("sr_copy", text)

    def share(self, url, text):
        """Opens the phone share sheet, or copies the link. Returns 'shared', 'copied' or ''."""
        if not IS_WEB:
            return ""
        self._setup()
        try:
            return str(self._js("sr_share", url, text) or "")
        except Exception:
            return ""

    def close(self):
        self.connecting = False
        self.connected = False
        self.pending = None
        self._js("sr_close")

    def update(self, dt):
        out = []
        if not IS_WEB:
            return out
        if self.connecting:
            self.t += dt
            st = self._int(self._js("sr_state"))
            if st is None:
                self.none_count += 1
                if self.t > 4:
                    self.connecting = False
                    self.error = "Browser bridge unavailable"
            elif st == 1:
                self.connecting = False
                self.connected = True
                if self.pending:
                    self.send(self.pending)
                    self.pending = None
            elif st in (3, -1):
                if self.t < 80:
                    if self.t - self.last >= 3:
                        self.last = self.t
                        self._js("sr_connect", URL)
                else:
                    self.connecting = False
                    self.error = "Could not connect to server"
            elif self.t > 90:
                self.connecting = False
                self.error = "Server did not respond"
        elif self.connected:
            for _ in range(30):
                s = self._js("sr_pop")
                if not s:
                    break
                try:
                    out.append(json.loads(str(s)))
                except Exception:
                    pass
            st = self._int(self._js("sr_state"))
            if st in (2, 3, -1):
                self.connected = False
                out.append({"t": "closed"})
        return out
