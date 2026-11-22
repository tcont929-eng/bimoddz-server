# server.py - Dành cho Web Cloud (Render/VPS)
import json, os, re, hashlib, secrets, threading, time, smtplib, traceback, queue
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
KEYS_FILE = DATA_DIR / "keys.json"
LOCK = threading.Lock()
SESSIONS = {}
ZALO_PHONE = "0333671076"

# Hàng đợi lệnh cho Termux Agent
AGENT_QUEUE = queue.Queue()
AGENT_RESULTS = {}

def hp(password, salt=None):
    if salt is None: salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 260000)
    return f"{salt}${dk.hex()}"

def vp(password, stored):
    try:
        salt, _ = stored.split("$", 1)
        return secrets.compare_digest(hp(password, salt), stored)
    except: return False

def init_db():
    with LOCK:
        if not ACCOUNTS_FILE.exists():
            admin = {"username": "admin", "password": hp("admin123"), "role": "admin", "premium_until": 0, "credits": 999999}
            ACCOUNTS_FILE.write_text(json.dumps([admin], ensure_ascii=False, indent=2), encoding="utf-8")
        if not KEYS_FILE.exists():
            KEYS_FILE.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")

def load_accounts():
    init_db()
    with LOCK:
        try:
            accs = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
            for a in accs:
                if "credits" not in a: a["credits"] = 999999 if a.get("role") == "admin" else 0
                if "premium_until" not in a: a["premium_until"] = 0
            return accs
        except: return []

def save_accounts(accs):
    with LOCK: ACCOUNTS_FILE.write_text(json.dumps(accs, ensure_ascii=False, indent=2), encoding="utf-8")

def load_keys():
    with LOCK:
        try: return json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        except: return []

def save_keys(keys):
    with LOCK: KEYS_FILE.write_text(json.dumps(keys, ensure_ascii=False, indent=2), encoding="utf-8")

def execute_smtp_spam(sender_email, sender_password, recipients, subject, msg_body, count):
    html_body = f"<html><body style='background:#000;color:#fff;'><h2>{subject}</h2><p>{msg_body}</p><p>Zalo: <a href='https://zalo.me/{ZALO_PHONE}'>{ZALO_PHONE}</a></p></body></html>"
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_password)
        for _ in range(count):
            for rcpt in recipients:
                msg = MIMEMultipart('alternative')
                msg["From"], msg["To"], msg["Subject"] = sender_email, rcpt, subject
                msg.attach(MIMEText(msg_body + f"\n\nZalo: {ZALO_PHONE}", 'plain', 'utf-8'))
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                server.sendmail(sender_email, rcpt, msg.as_string())
                time.sleep(0.3)
        server.quit()
    except Exception: pass

# Nhúng thẳng HTML/CSS/JS vào đây (Rút gọn để bạn dễ copy)
HTML_CONTENT = """<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BIMODDZ Cloud</title><link rel="stylesheet" href="style.css"></head><body>
<div id="bg"><span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span></div>
<main id="app" class="hidden">
  <header class="top"><div class="brand"><span class="logo">B</span><div><b>BIMODDZ CLOUD</b><small>Zalo 0333671076</small></div></div><div class="right"><span id="userBadge" class="badge">Khách</span><button id="logoutBtn" class="btn ghost hidden">Đăng xuất</button></div></header>
  <section id="authView" class="glass auth">
    <div class="tabs"><button data-tab="login" class="active">Đăng nhập</button><button data-tab="register">Đăng ký</button><button data-tab="admin">Admin</button></div>
    <form id="loginForm" class="form"><label>Tên đăng nhập<input id="loginUser" required></label><label>Mật khẩu<input id="loginPass" type="password" required></label><button class="btn primary" type="submit">Đăng nhập</button></form>
    <form id="registerForm" class="form hidden"><label>Tên đăng nhập<input id="regUser" required></label><label>Mật khẩu<input id="regPass" type="password" required></label><button class="btn primary" type="submit">Tạo tài khoản</button></form>
    <form id="adminForm" class="form hidden"><label>Admin<input id="adminUser" required></label><label>Mật khẩu<input id="adminPass" type="password" required></label><button class="btn primary" type="submit">Đăng nhập Admin</button></form>
  </section>
  <section id="dashView" class="hidden">
    <div class="status-bar glass"><div><b>Quyền:</b> <span id="statRole"></span></div><div><b>Tín dụng:</b> <span id="statCredits"></span></div><div><b>Cao cấp:</b> <span id="statPremium"></span></div></div>
    <div class="grid">
      <div class="glass card"><h2>Gửi Email (SMTP)</h2><form id="spamForm" class="form"><label>Gmail<input id="spamSenderEmail" type="email" required></label><label>Mật khẩu ứng dụng<input id="spamSenderPass" type="password" required></label><label>Người nhận<textarea id="spamRecipients" rows="2" required></textarea></label><label>Tiêu đề<input id="spamSubject" required></label><label>Nội dung<textarea id="spamBody" rows="2"></textarea></label><label>Số lần<input id="spamCount" type="number" min="1" value="1"></label><button class="btn primary" type="submit">Gửi Email</button></form><pre id="spamResult" class="result"></pre></div>
      <div class="glass card"><h2>Termux Agent (SMS/BT)</h2><p class="muted">Lệnh sẽ được gửi xuống điện thoại của Admin.</p><form id="termuxForm" class="form"><label>Mục tiêu (SĐT/MAC)<input id="termuxTarget" required></label><label>Nội dung (SMS)<input id="termuxPayload"></label><label>Phương thức<select id="termuxType"><option value="bluetooth">Bluetooth Spam</option><option value="sms">SMS Spam</option><option value="call">Call Spam</option></select></label><label>Số lần<input id="termuxCount" type="number" min="1" value="1"></label><button class="btn primary" type="submit">Gửi lệnh xuống Agent</button></form><pre id="termuxResult" class="result"></pre></div>
      <div class="glass card hidden" id="adminCard"><h2>Admin Console</h2><button id="genKeyBtn" class="btn primary">Tạo Key Cao Cấp</button><div id="adminOutput" class="result"></div></div>
      <div class="glass card hidden" id="userCard"><h2>Nâng cấp Cao Cấp</h2><form id="redeemForm" class="form"><label>Nhập Key<input id="redeemKey" placeholder="BIMODDZ-XXXX" required></label><button class="btn primary" type="submit">Kích hoạt</button></form><pre id="redeemResult" class="result"></pre></div>
    </div>
  </section>
</main><div id="toast" class="toast"></div><script src="app.js"></script></body></html>"""

CSS_CONTENT = """*{box-sizing:border-box}body{margin:0;background:#05060a;color:#eaf2ff;font-family:sans-serif;overflow-x:hidden}.hidden{display:none!important}#bg{position:fixed;inset:0;z-index:-2;background:radial-gradient(circle at 10% 10%,rgba(90,120,255,.2),transparent),#05060a}.blob{position:absolute;filter:blur(80px);opacity:.5;border-radius:50%;animation:float 18s infinite alternate}.b1{width:400px;height:400px;background:#5a78ff;top:-100px;left:-100px}.b2{width:300px;height:300px;background:#00ffd5;bottom:-100px;right:-100px}@keyframes float{to{transform:translate(30px,30px)}}.glass{background:rgba(255,255,255,.05);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.15);border-radius:24px;padding:20px;margin-bottom:15px}#app{max-width:900px;margin:0 auto;padding:20px}.top{display:flex;justify-content:space-between;margin-bottom:20px}.logo{background:linear-gradient(135deg,#5a78ff,#00ffd5);width:40px;height:40px;border-radius:12px;display:grid;place-items:center;font-weight:bold;color:#000}.form{display:grid;gap:10px}label{display:grid;gap:5px;font-size:12px;color:#9fb0d0}input,textarea,select{width:100%;background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:10px;color:#fff}.btn{border:0;padding:10px;border-radius:12px;font-weight:bold;cursor:pointer}.primary{background:linear-gradient(135deg,#5a78ff,#00ffd5);color:#000}.grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}@media(max-width:700px){.grid{grid-template-columns:1fr}}.result{background:rgba(0,0,0,.3);padding:10px;border-radius:12px;font-size:12px;white-space:pre-wrap}.status-bar{display:flex;justify-content:space-between;font-size:13px}.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#222;padding:10px 20px;border-radius:20px;opacity:0;transition:0.3s}.toast.show{opacity:1}"""

JS_CONTENT = """const $ = (s) => document.querySelector(s);const state = { token: localStorage.getItem("lg_token") || "", user: null };const toastEl = $("#toast");let toastTimer;
function toast(msg){toastEl.textContent=msg;toastEl.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>toastEl.classList.remove("show"),2500);}
async function api(path, body=null, method=null){const headers={"Content-Type":"application/json"};if(state.token)headers["X-Token"]=state.token;const opts={method:method||(body?"POST":"GET"),headers};if(body)opts.body=JSON.stringify(body);const res=await fetch(path,opts);const data=await res.json().catch(()=>({ok:false}));if(!res.ok||data.ok===false)throw new Error(data.error||"Lỗi");return data;}
function setTab(name){document.querySelectorAll(".tabs button").forEach(b=>b.classList.toggle("active",b.dataset.tab===name));$("#loginForm").classList.toggle("hidden",name!=="login");$("#registerForm").classList.toggle("hidden",name!=="register");$("#adminForm").classList.toggle("hidden",name!=="admin");}
function showAuth(){$("#app").classList.remove("hidden");$("#authView").classList.remove("hidden");$("#dashView").classList.add("hidden");$("#logoutBtn").classList.add("hidden");$("#userBadge").textContent="Khách";state.user=null;}
function updateStats(){if(!state.user)return;$("#userBadge").textContent=state.user.username+" • "+(state.user.role==='admin'?'Admin':'User');$("#statRole").textContent=state.user.role==='admin'?'QUẢN TRỊ':'THÀNH VIÊN';$("#statCredits").textContent=state.user.credits;const now=Date.now()/1000;if(state.user.role==="admin"){$("#statPremium").textContent="VĨNH VIỄN";$("#statPremium").style.color="#00ffd5";}else if(state.user.premium_until>now){$("#statPremium").textContent=Math.ceil((state.user.premium_until-now)/86400)+" NGÀY";$("#statPremium").style.color="#00ffd5";}else{$("#statPremium").textContent="CHƯA KÍCH HOẠT";$("#statPremium").style.color="#ff0055";}}
function showDash(){$("#app").classList.remove("hidden");$("#authView").classList.add("hidden");$("#dashView").classList.remove("hidden");$("#logoutBtn").classList.remove("hidden");updateStats();const isAdmin=state.user.role==="admin";$("#adminCard").classList.toggle("hidden",!isAdmin);$("#userCard").classList.toggle("hidden",isAdmin);}
async function refreshMe(){if(!state.token)return showAuth();try{const d=await api("/api/me",null,"GET");state.user=d.user;showDash();}catch(e){state.token="";localStorage.removeItem("lg_token");showAuth();}}
async function doLogin(path,user,pass){const d=await api(path,{username:user,password:pass});state.token=d.token;state.user=d.user;localStorage.setItem("lg_token",d.token);showDash();toast("Đăng nhập thành công");}
document.querySelectorAll(".tabs button").forEach(b=>b.addEventListener("click",()=>setTab(b.dataset.tab)));
$("#loginForm").addEventListener("submit",async(e)=>{e.preventDefault();try{await doLogin("/api/login",$("#loginUser").value.trim(),$("#loginPass").value);}catch(err){toast(err.message);}});
$("#registerForm").addEventListener("submit",async(e)=>{e.preventDefault();try{await api("/api/register",{username:$("#regUser").value.trim(),password:$("#regPass").value});toast("Đã tạo tài khoản");setTab("login");}catch(err){toast(err.message);}});
$("#adminForm").addEventListener("submit",async(e)=>{e.preventDefault();try{await doLogin("/api/admin-login",$("#adminUser").value.trim(),$("#adminPass").value);}catch(err){toast(err.message);}});
$("#logoutBtn").addEventListener("click",async()=>{try{await api("/api/logout",{});}catch(_){}state.token="";state.user=null;localStorage.removeItem("lg_token");showAuth();});
$("#spamForm").addEventListener("submit",async(e)=>{e.preventDefault();const btn=e.target.querySelector("button");btn.disabled=true;btn.textContent="Đang gửi...";try{const d=await api("/api/spam_smtp",{sender_email:$("#spamSenderEmail").value,sender_password:$("#spamSenderPass").value,recipients:$("#spamRecipients").value,subject:$("#spamSubject").value,body:$("#spamBody").value,count:Number($("#spamCount").value)});$("#spamResult").textContent=JSON.stringify(d,null,2);toast(d.message);refreshMe();}catch(err){$("#spamResult").textContent="LỖI: "+err.message;}finally{btn.disabled=false;btn.textContent="Gửi Email";}});
$("#termuxForm").addEventListener("submit",async(e)=>{e.preventDefault();const btn=e.target.querySelector("button");btn.disabled=true;btn.textContent="Đang gửi lệnh...";try{const d=await api("/api/spam_termux",{target:$("#termuxTarget").value,payload:$("#termuxPayload").value,type:$("#termuxType").value,count:Number($("#termuxCount").value)});$("#termuxResult").textContent=JSON.stringify(d,null,2);toast(d.message);refreshMe();}catch(err){$("#termuxResult").textContent="LỖI: "+err.message;}finally{btn.disabled=false;btn.textContent="Gửi lệnh xuống Agent";}});
$("#genKeyBtn").addEventListener("click",async()=>{try{const d=await api("/api/gen_key",{});$("#adminOutput").textContent="KEY MỚI: "+d.key;toast("Đã tạo Key");}catch(err){toast(err.message);}});
$("#redeemForm").addEventListener("submit",async(e)=>{e.preventDefault();try{const d=await api("/api/redeem",{key:$("#redeemKey").value.trim()});$("#redeemResult").textContent=d.message;toast("Kích hoạt thành công");refreshMe();}catch(err){$("#redeemResult").textContent="LỖI: "+err.message;}});
window.addEventListener("load",()=>{refreshMe();});"""

class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers(); self.wfile.write(data)

    def _string(self, text, ctype):
        data = text.encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def _session(self):
        return self.headers.get("X-Token", ""), SESSIONS.get(self.headers.get("X-Token", ""))

    def _check_quota(self, username, is_admin, cost=1):
        if is_admin: return True, ""
        accs = load_accounts()
        for a in accs:
            if a["username"] == username:
                if a.get("premium_until", 0) > time.time() and a.get("credits", 0) >= cost:
                    a["credits"] -= cost; save_accounts(accs); return True, ""
                return False, "Hết hạn hoặc không đủ tín dụng."
        return False, "Lỗi User"

    def do_GET(self):
        try:
            p = urlparse(self.path).path
            if p in ["/", "/index.html"]: return self._string(HTML_CONTENT, "text/html")
            if p == "/style.css": return self._string(CSS_CONTENT, "text/css")
            if p == "/app.js": return self._string(JS_CONTENT, "application/javascript")
            if p == "/api/agent_poll":
                # Agent gọi API này liên tục để lấy lệnh
                try:
                    task = AGENT_QUEUE.get(timeout=10)
                    return self._json(200, {"ok": True, "task": task})
                except queue.Empty:
                    return self._json(200, {"ok": True, "task": None})
            if p == "/api/me":
                _, s = self._session()
                if not s: return self._json(401, {"ok": False, "error": "Unauthorized"})
                for a in load_accounts():
                    if a["username"] == s["username"]:
                        s["credits"], s["premium_until"] = a.get("credits", 0), a.get("premium_until", 0)
                return self._json(200, {"ok": True, "user": s})
            return self._json(404, {"ok": False})
        except Exception as e: return self._json(500, {"ok": False, "error": str(e)})

    def do_POST(self):
        try:
            p = urlparse(self.path).path
            n = int(self.headers.get("Content-Length", "0") or 0)
            try: body = json.loads(self.rfile.read(n) or b"{}")
            except: return self._json(400, {"ok": False})

            if p == "/api/agent_result":
                # Agent trả kết quả về
                task_id = body.get("task_id")
                if task_id: AGENT_RESULTS[task_id] = body.get("result", "Done")
                return self._json(200, {"ok": True})
                
            if p == "/api/register":
                u, pw = str(body.get("username", "")).strip(), str(body.get("password", ""))
                accs = load_accounts()
                if any(a["username"].lower() == u.lower() for a in accs): return self._json(409, {"ok": False, "error": "Tên đã tồn tại"})
                accs.append({"username": u, "password": hp(pw), "role": "user", "premium_until": 0, "credits": 0})
                save_accounts(accs); return self._json(200, {"ok": True})
                
            if p in ["/api/login", "/api/admin-login"]:
                u, pw = str(body.get("username", "")).strip(), str(body.get("password", ""))
                for a in load_accounts():
                    if a["username"].lower() == u.lower() and vp(pw, a["password"]):
                        if p == "/api/admin-login" and a.get("role") != "admin": return self._json(401, {"ok": False, "error": "Không phải Admin"})
                        token = secrets.token_hex(24)
                        user = {"username": a["username"], "role": a.get("role", "user"), "premium_until": a.get("premium_until", 0), "credits": a.get("credits", 0)}
                        SESSIONS[token] = user
                        return self._json(200, {"ok": True, "token": token, "user": user})
                return self._json(401, {"ok": False, "error": "Sai tài khoản"})

            _, s = self._session()
            if not s: return self._json(401, {"ok": False})

            if p == "/api/spam_smtp":
                allowed, err = self._check_quota(s["username"], s.get("role")=="admin", 10)
                if not allowed: return self._json(403, {"ok": False, "error": err})
                recipients = [x.strip() for x in str(body.get("recipients", "")).replace(",", "\n").splitlines() if x.strip()]
                threading.Thread(target=execute_smtp_spam, args=(
                    str(body.get("sender_email", "")), str(body.get("sender_password", "")),
                    recipients, str(body.get("subject", "")), str(body.get("body", "")), int(body.get("count", 1))
                )).start()
                return self._json(200, {"ok": True, "message": f"Đã gửi yêu cầu SMTP (Tốn 10 tín dụng)"})

            if p == "/api/spam_termux":
                allowed, err = self._check_quota(s["username"], s.get("role")=="admin", 5)
                if not allowed: return self._json(403, {"ok": False, "error": err})
                task_id = secrets.token_hex(8)
                AGENT_QUEUE.put({"id": task_id, "type": body.get("type"), "target": body.get("target"), "payload": body.get("payload"), "count": int(body.get("count", 1))})
                return self._json(200, {"ok": True, "message": f"Lệnh đã đẩy vào hàng đợi Agent (Tốn 5 tín dụng)"})

            if p == "/api/gen_key":
                if s.get("role") != "admin": return self._json(401, {"ok": False})
                keys = load_keys()
                new_key = f"BIMODDZ-{secrets.token_hex(4).upper()}"
                keys.append({"key": new_key, "used": False})
                save_keys(keys); return self._json(200, {"ok": True, "key": new_key})

            if p == "/api/redeem":
                k = str(body.get("key", "")).strip().upper()
                keys = load_keys()
                for entry in keys:
                    if entry["key"] == k and not entry["used"]:
                        entry["used"] = True; save_keys(keys)
                        accs = load_accounts()
                        for a in accs:
                            if a["username"] == s["username"]:
                                a["premium_until"] = time.time() + (30 * 86400)
                                a["credits"] = a.get("credits", 0) + 500
                                save_accounts(accs)
                                return self._json(200, {"ok": True, "message": "Đã kích hoạt 30 ngày + 500 tín dụng!"})
                return self._json(400, {"ok": False, "error": "Key sai hoặc đã dùng"})
            return self._json(404, {"ok": False})
        except Exception as e: return self._json(500, {"ok": False, "error": str(e)})

def main():
    init_db()
    port = int(os.environ.get("PORT", "10000")) # Render.com dùng port 10000
    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    print(f"[*] Server đang chạy tại port {port}")
    srv.serve_forever()

if __name__ == "__main__":
    main()