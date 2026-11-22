# server.py - BIMODDZ v6 (Direct QR Image Integration)
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
            admin = {"username": "admin", "password": hp("admin123"), "role": "admin", "premium_until": 0, "credits": 999999, "trial_uses": 999, "total_donated": 0}
            fake_users = [
                {"username": "Minh_IT", "password": hp("123"), "role": "user", "premium_until": 9999999999, "credits": 5000, "trial_uses": 0, "total_donated": 500000},
                {"username": "Trần_Hùng", "password": hp("123"), "role": "user", "premium_until": 9999999999, "credits": 5000, "trial_uses": 0, "total_donated": 200000},
                {"username": "Ngọc_Anh", "password": hp("123"), "role": "user", "premium_until": 9999999999, "credits": 5000, "trial_uses": 0, "total_donated": 100000},
                {"username": "Quang_Dev", "password": hp("123"), "role": "user", "premium_until": 9999999999, "credits": 5000, "trial_uses": 0, "total_donated": 50000},
                {"username": "Bảo_Nam", "password": hp("123"), "role": "user", "premium_until": 9999999999, "credits": 5000, "trial_uses": 0, "total_donated": 15000}
            ]
            ACCOUNTS_FILE.write_text(json.dumps([admin] + fake_users, ensure_ascii=False, indent=2), encoding="utf-8")
        if not KEYS_FILE.exists():
            KEYS_FILE.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")

def load_accounts():
    init_db()
    with LOCK:
        try:
            accs = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
            for a in accs:
                if "trial_uses" not in a: a["trial_uses"] = 3
                if "total_donated" not in a: a["total_donated"] = 0
                if "premium_until" not in a: a["premium_until"] = 0
                if "credits" not in a: a["credits"] = 0
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
    html_body = f"""
    <html>
    <body style="background-color:#000000;color:#ffffff;font-family:Arial,sans-serif;padding:20px;margin:0;">
      <div style="max-width:600px;margin:0 auto;background-color:#111111;border:1px solid #333333;border-radius:12px;padding:30px;">
        <h2 style="color:#00ffd5;margin-top:0;">{subject}</h2>
        <p style="color:#e0e0e0;line-height:1.6;white-space:pre-wrap;">{msg_body}</p>
        <hr style="border-color:#333333;margin:24px 0;">
        <p style="color:#888888;font-size:12px;">Gửi từ BIMODDZ Cloud Node</p>
        <a href="https://zalo.me/{ZALO_PHONE}" style="display:inline-block;background-color:#0068ff;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:bold;margin-top:10px;">Zalo: {ZALO_PHONE}</a>
      </div>
    </body>
    </html>
    """
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        server.starttls()
        server.login(sender_email, sender_password)
        for _ in range(count):
            for rcpt in recipients:
                msg = MIMEMultipart('alternative')
                msg["From"], msg["To"], msg["Subject"] = sender_email, rcpt, subject
                msg["X-Priority"] = "1 (Highest)"
                msg.attach(MIMEText(msg_body + f"\n\nZalo: https://zalo.me/{ZALO_PHONE}", 'plain', 'utf-8'))
                msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                server.sendmail(sender_email, rcpt, msg.as_string())
                time.sleep(0.3)
        server.quit()
    except Exception: pass

HTML_CONTENT = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>BIMODDZ Cloud</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="bg">
    <span class="blob b1"></span><span class="blob b2"></span><span class="blob b3"></span><span class="blob b4"></span>
  </div>

  <div id="splash" aria-hidden="true">
    <div class="splash-noise"></div><div class="splash-grid"></div>
    <div class="splash-stage">
      <div class="splash-halo"></div>
      <div class="splash-card glass">
        <div class="splash-shine"></div>
        <div class="splash-orb">
          <div class="orb-ring r1"></div><div class="orb-ring r2"></div><div class="orb-ring r3"></div>
          <div class="orb-core" style="background:transparent;box-shadow:none;display:grid;place-items:center;">
            <span id="serverLetter" class="b-letter">B</span>
          </div>
        </div>
        <div class="splash-copy">
          <h1 style="font-size:32px; letter-spacing:0.1em;">BIMODDZ</h1>
          <p style="letter-spacing:0.15em; color:#00ffd5; margin-top:5px;">ZALO 0333671076</p>
        </div>
        <div class="splash-progress">
          <div class="splash-progress-track"><i id="splashBar"></i></div>
          <div class="splash-meta"><span id="splashStatus">ĐANG KHỞI TẠO</span><span id="splashPercent">0%</span></div>
        </div>
      </div>
      <button id="splashSkip" class="splash-skip" type="button">BỎ QUA</button>
    </div>
  </div>

  <main id="app" class="hidden">
    <header class="top">
      <div class="brand">
        <span class="logo">B</span>
        <div><b>BIMODDZ CLOUD</b><small style="line-height:1.2;">Zalo 0333671076</small></div>
      </div>
      <div class="right">
        <span id="userBadge" class="badge">Khách</span>
        <button id="logoutBtn" class="btn ghost hidden">Đăng xuất</button>
      </div>
    </header>

    <section id="authView" class="glass auth">
      <div class="tabs">
        <button data-tab="login" class="active">Đăng nhập</button>
        <button data-tab="register">Đăng ký</button>
        <button data-tab="admin">Quản trị</button>
      </div>
      <form id="loginForm" class="form">
        <label>Tên đăng nhập<input id="loginUser" required></label>
        <label>Mật khẩu<input id="loginPass" type="password" required></label>
        <button class="btn primary" type="submit">Đăng nhập</button>
      </form>
      <form id="registerForm" class="form hidden">
        <label>Tên đăng nhập<input id="regUser" required></label>
        <label>Mật khẩu<input id="regPass" type="password" required></label>
        <button class="btn primary" type="submit">Tạo tài khoản (Tặng 3 lượt dùng thử)</button>
      </form>
      <form id="adminForm" class="form hidden">
        <label>Tên Quản trị<input id="adminUser" required></label>
        <label>Mật khẩu Quản trị<input id="adminPass" type="password" required></label>
        <button class="btn primary" type="submit">Đăng nhập Admin</button>
      </form>
    </section>

    <section id="dashView" class="hidden">
      <div class="status-bar glass">
        <div><b>Quyền:</b> <span id="statRole"></span></div>
        <div><b>Lượt thử/Tín dụng:</b> <span id="statTrialCredits"></span></div>
        <div><b>Cao cấp:</b> <span id="statPremium"></span></div>
      </div>

      <div class="grid">
        <div class="glass card">
          <h2>Gửi Email Hàng Loạt (Cloud)</h2>
          <p class="muted">Gửi trực tiếp từ Server Render.</p>
          <form id="spamForm" class="form">
            <label>Gmail Người gửi<input id="spamSenderEmail" type="email" required></label>
            <label>Mật khẩu ứng dụng<input id="spamSenderPass" type="password" required></label>
            <label>Người nhận (mỗi dòng 1 email)<textarea id="spamRecipients" rows="2" required></textarea></label>
            <label>Tiêu đề<input id="spamSubject" required></label>
            <label>Nội dung<textarea id="spamBody" rows="2"></textarea></label>
            <label>Số lần gửi<input id="spamCount" type="number" min="1" max="100" value="1"></label>
            <button class="btn primary" type="submit">Bắt đầu gửi</button>
          </form>
          <pre id="spamResult" class="result"></pre>
        </div>

        <div class="glass card">
          <h2>Termux API Agent (SMS/BT)</h2>
          <p class="muted">Lệnh sẽ truyền xuống điện thoại của bạn.</p>
          <form id="termuxForm" class="form">
            <label>Mục tiêu (MAC / Số điện thoại)<input id="termuxTarget" placeholder="AA:BB:CC:DD:EE:FF hoặc +849..." required></label>
            <label>Nội dung (Dùng cho SMS)<input id="termuxPayload" placeholder="Tin nhắn rác..."></label>
            <label>Phương thức
              <select id="termuxType">
                <option value="bluetooth">Quét Bluetooth (Bluetooth Spam)</option>
                <option value="sms">Gửi SMS rác</option>
                <option value="call">Gọi điện rác</option>
              </select>
            </label>
            <label>Số lần lặp<input id="termuxCount" type="number" min="1" max="50" value="1"></label>
            <button class="btn primary" type="submit">Gửi lệnh xuống Agent</button>
          </form>
          <pre id="termuxResult" class="result"></pre>
        </div>

        <!-- VIP SHOP -->
        <div class="glass card" style="grid-column: 1 / -1;">
          <h2>💎 Nâng Cấp VIP & Bảng Xếp Hạng</h2>
          <div style="display:flex; gap:20px; flex-wrap:wrap;">
            <div style="flex:1; min-width:280px;">
              <p class="muted">Quét mã QR để thanh toán. Sau khi chuyển khoản, bấm xác nhận để hệ thống tự động cấp Key.</p>
              <div style="text-align:center; margin-bottom:15px;">
                <!-- ẢNH QR ĐÃ ĐƯỢC TÍCH HỢP TỰ ĐỘNG -->
                <img src="/qr.jpg" alt="QR Nạp Tiền" style="width:100%; max-width:250px; border-radius:15px; border: 2px solid rgba(255,255,255,0.2); background:#fff;">
                <p style="font-size:12px; margin-top:10px;">Chủ TK: <b>NGUYEN THI CUONG</b></p>
              </div>
              
              <div style="display:grid; gap:10px;">
                <button class="btn" onclick="buyVIP('week', 15000)">Gói 1 Tuần - 15.000đ</button>
                <button class="btn" onclick="buyVIP('month', 50000)">Gói 1 Tháng - 50.000đ</button>
                <button class="btn primary" onclick="buyVIP('life', 100000)">Gói Vĩnh Viễn - 100.000đ</button>
              </div>
              <p style="font-size:11px; color:#ff0055; margin-top:10px; font-style:italic;">* Lưu ý: Nếu quá 4 phút không thấy Key, vui lòng liên hệ Admin qua Zalo: <b>0333671076</b> để được hỗ trợ.</p>
            </div>
            <div style="flex:1; min-width:280px;">
              <h3 style="margin-top:0;">🏆 Bảng Xếp Hạng Nạp</h3>
              <div id="leaderboard" class="result" style="max-height:300px; overflow-y:auto;">
                Đang tải...
              </div>
            </div>
          </div>
        </div>

        <div class="glass card hidden" id="adminCard">
          <h2>Bảng điều khiển Admin</h2>
          <div style="display:flex;gap:10px;margin-bottom:15px;">
            <button id="genKeyBtn" class="btn primary">Tạo Key Thủ Công</button>
          </div>
          <div id="adminOutput" class="result"></div>
        </div>

      </div>
    </section>
  </main>
  <div id="toast" class="toast"></div>
  <script src="app.js"></script>
</body>
</html>"""

CSS_CONTENT = """*{box-sizing:border-box}
html,body{min-height:100%}
body{margin:0;background:#05060a;color:#eaf2ff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;overflow-x:hidden}
.hidden{display:none!important}
#bg{position:fixed;inset:0;overflow:hidden;z-index:-2;background:radial-gradient(1200px 800px at 10% 10%,rgba(90,120,255,.25),transparent 60%),radial-gradient(1000px 700px at 90% 20%,rgba(0,255,220,.18),transparent 60%),radial-gradient(900px 700px at 50% 100%,rgba(255,0,200,.16),transparent 60%),#05060a}
.blob{position:absolute;filter:blur(80px);opacity:.55;border-radius:50%;animation:float 18s ease-in-out infinite alternate}
.b1{width:420px;height:420px;background:#5a78ff;top:-120px;left:-120px}
.b2{width:360px;height:360px;background:#00ffd5;top:20%;right:-140px;animation-delay:-4s}
.b3{width:500px;height:500px;background:#ff00c8;bottom:-200px;left:20%;animation-delay:-8s}
.b4{width:300px;height:300px;background:#ffd166;bottom:10%;right:10%;animation-delay:-12s}
@keyframes float{to{transform:translate3d(40px,-30px,0) scale(1.08)}}
.glass{position:relative;background:linear-gradient(135deg,rgba(255,255,255,.14),rgba(255,255,255,.05));backdrop-filter:blur(28px) saturate(180%);-webkit-backdrop-filter:blur(28px) saturate(180%);border:1px solid rgba(255,255,255,.18);border-radius:30px;box-shadow:0 20px 70px rgba(0,0,0,.45),inset 0 1px 0 rgba(255,255,255,.35);overflow:hidden}
.glass::before{content:"";position:absolute;inset:0;pointer-events:none;background:linear-gradient(120deg,rgba(255,255,255,.25),transparent 35%,transparent 65%,rgba(255,255,255,.08))}
#splash{position:fixed;inset:0;z-index:100;display:grid;place-items:center;overflow:hidden;background:radial-gradient(900px 700px at 50% 42%,rgba(90,120,255,.26),transparent 62%),radial-gradient(700px 520px at 18% 82%,rgba(0,255,213,.14),transparent 60%),radial-gradient(760px 560px at 84% 18%,rgba(255,0,200,.13),transparent 60%),#04060b;transition:opacity .9s cubic-bezier(.2,.8,.2,1),visibility .9s cubic-bezier(.2,.8,.2,1)}
#splash.hide{opacity:0;visibility:hidden;pointer-events:none}
#splash::before{content:"";position:absolute;inset:-30%;background:conic-gradient(from 180deg at 50% 50%,rgba(90,120,255,.00),rgba(90,120,255,.16),rgba(0,255,213,.12),rgba(255,0,200,.10),rgba(90,120,255,.00));filter:blur(70px);animation:splashAurora 12s linear infinite}
#splash::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(255,255,255,.04),transparent 20%,transparent 80%,rgba(0,0,0,.35)),radial-gradient(circle at 50% 50%,transparent 40%,rgba(0,0,0,.35) 100%);pointer-events:none}
.splash-noise{position:absolute;inset:0;opacity:.06;pointer-events:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.7'/%3E%3C/svg%3E")}
.splash-grid{position:absolute;inset:0;opacity:.10;background-image:linear-gradient(rgba(255,255,255,.10) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.10) 1px,transparent 1px);background-size:56px 56px;mask-image:radial-gradient(circle at 50% 50%,#000 0%,transparent 72%);-webkit-mask-image:radial-gradient(circle at 50% 50%,#000 0%,transparent 72%);animation:splashGrid 8s linear infinite}
.splash-stage{position:relative;width:min(92vw,430px);display:grid;justify-items:center;gap:18px;animation:splashStageIn 1s cubic-bezier(.2,.9,.2,1.15) both}
.splash-halo{position:absolute;width:360px;height:360px;border-radius:50%;background:radial-gradient(circle,rgba(90,120,255,.32),rgba(0,255,213,.10) 45%,transparent 70%);filter:blur(30px);animation:splashHalo 3.2s ease-in-out infinite alternate;pointer-events:none}
.splash-card{position:relative;width:100%;padding:34px 28px 24px;border-radius:34px;background:linear-gradient(135deg,rgba(255,255,255,.16),rgba(255,255,255,.045) 45%,rgba(255,255,255,.08));backdrop-filter:blur(34px) saturate(190%);-webkit-backdrop-filter:blur(34px) saturate(190%);border:1px solid rgba(255,255,255,.20);box-shadow:0 30px 100px rgba(0,0,0,.55),inset 0 1px 0 rgba(255,255,255,.42),inset 0 -1px 0 rgba(255,255,255,.06);overflow:hidden;text-align:center}
.splash-card::before{content:"";position:absolute;inset:1px;border-radius:33px;background:linear-gradient(120deg,rgba(255,255,255,.28),transparent 28%,transparent 68%,rgba(255,255,255,.08));pointer-events:none}
.splash-card::after{content:"";position:absolute;inset:0;border-radius:34px;box-shadow:inset 0 0 40px rgba(90,120,255,.10);pointer-events:none}
.splash-shine{position:absolute;top:-60%;left:-30%;width:60%;height:220%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.20),transparent);transform:rotate(22deg);animation:splashShine 3.8s ease-in-out infinite;pointer-events:none}
.splash-orb{position:relative;width:132px;height:132px;margin:0 auto 20px;display:grid;place-items:center}
.b-letter{font-size:68px;font-weight:900;background:linear-gradient(135deg,#5a78ff,#00ffd5,#ff00c8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;filter:drop-shadow(0 0 20px rgba(0,255,213,.6));z-index:2;animation:splashCore 3.6s ease-in-out infinite}
.orb-ring{position:absolute;border-radius:50%;border:1px solid rgba(255,255,255,.26);animation:splashRing 3s cubic-bezier(.2,.7,.2,1) infinite}
.orb-ring.r1{inset:0}
.orb-ring.r2{inset:-12px;animation-delay:.45s}
.orb-ring.r3{inset:-24px;animation-delay:.9s}
.splash-copy h1{margin:0;font-weight:800;color:#f2f7ff;text-shadow:0 0 28px rgba(90,120,255,.55);animation:splashText 1.1s cubic-bezier(.2,.9,.2,1) both}
.splash-copy p{margin:9px 0 24px;font-size:12px;font-weight:700;animation:splashText 1.1s .15s cubic-bezier(.2,.9,.2,1) both}
.splash-progress{position:relative;z-index:2}
.splash-progress-track{height:6px;border-radius:99px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.08);overflow:hidden;box-shadow:inset 0 1px 3px rgba(0,0,0,.45)}
.splash-progress-track i{display:block;height:100%;width:0%;border-radius:99px;background:linear-gradient(90deg,#5a78ff,#00ffd5 55%,#ff00c8);box-shadow:0 0 18px rgba(0,255,213,.45);transition:width .18s linear}
.splash-meta{display:flex;justify-content:space-between;align-items:center;margin-top:10px;font-size:10px;font-weight:700;letter-spacing:.16em;color:#8fa3c8}
#splashPercent{color:#dffcff;font-variant-numeric:tabular-nums}
.splash-skip{position:relative;z-index:3;border:1px solid rgba(255,255,255,.16);border-radius:99px;padding:9px 18px;background:rgba(255,255,255,.07);color:#bcd0f5;font-size:10px;font-weight:800;letter-spacing:.22em;backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);cursor:pointer;transition:.2s}
.splash-skip:active{transform:scale(.96);background:rgba(255,255,255,.12)}
@keyframes splashAurora{to{transform:rotate(360deg)}}
@keyframes splashGrid{to{background-position:56px 56px,56px 56px}}
@keyframes splashStageIn{from{opacity:0;transform:translateY(18px) scale(.96)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes splashHalo{from{transform:scale(.92);opacity:.65}to{transform:scale(1.08);opacity:1}}
@keyframes splashShine{0%,55%{transform:translateX(-160%) rotate(22deg)}100%{transform:translateX(420%) rotate(22deg)}}
@keyframes splashCore{0%,100%{transform:scale(1);filter:hue-rotate(0deg)}50%{transform:scale(1.04);filter:hue-rotate(18deg)}}
@keyframes splashRing{0%{transform:scale(.86);opacity:.85}100%{transform:scale(1.28);opacity:0}}
@keyframes splashText{from{opacity:0;transform:translateY(10px);filter:blur(8px)}to{opacity:1;transform:translateY(0);filter:blur(0)}}
#app{max-width:1120px;margin:0 auto;padding:22px 18px 60px}
.top{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:8px 0 22px}
.brand{display:flex;align-items:center;gap:12px}
.brand b{display:block;font-size:16px;letter-spacing:1px;}.brand small{display:block;color:#8fa3c8;font-size:10px;letter-spacing:.05em}
.logo{width:44px;height:44px;border-radius:16px;display:grid;place-items:center;font-weight:800;background:linear-gradient(135deg,#5a78ff,#00ffd5);color:#041018;box-shadow:0 10px 30px rgba(90,120,255,.35)}
.right{display:flex;align-items:center;gap:10px}
.badge{padding:8px 12px;border-radius:99px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);font-size:12px;color:#bcd0f5}
.auth{max-width:520px;margin:0 auto;padding:22px}
.tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:18px;position:relative;z-index:1}
.tabs button{border:0;padding:11px 10px;border-radius:16px;background:rgba(255,255,255,.06);color:#9fb0d0;font-weight:600}
.tabs button.active{background:linear-gradient(135deg,rgba(90,120,255,.85),rgba(0,255,213,.55));color:#031018;box-shadow:0 10px 30px rgba(90,120,255,.28)}
.form{display:grid;gap:14px;position:relative;z-index:1}
.form label{display:grid;gap:7px;font-size:12px;color:#9fb0d0;letter-spacing:.04em}
input,textarea,select{width:100%;border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:13px 14px;background:rgba(0,0,0,.22);color:#eaf2ff;outline:none;font:inherit;transition:border-color .2s,box-shadow .2s,background .2s}
input:focus,textarea:focus,select:focus{border-color:rgba(0,255,213,.55);box-shadow:0 0 0 4px rgba(0,255,213,.10);background:rgba(0,0,0,.30)}
textarea{resize:vertical;min-height:90px}
select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23eaf2ff' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 14px center}
.btn{border:1px solid rgba(255,255,255,.16);border-radius:16px;padding:12px 16px;background:rgba(255,255,255,.08);color:#eaf2ff;font-weight:700;letter-spacing:.02em;cursor:pointer}
.btn.primary{border:0;background:linear-gradient(135deg,#5a78ff,#00ffd5);color:#031018;box-shadow:0 14px 34px rgba(0,255,213,.18)}
.btn.ghost{background:transparent}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.status-bar{padding:15px 20px;margin-bottom:20px;display:flex;justify-content:space-between;font-size:13px;color:#bcd0f5}
.status-bar b{color:#eaf2ff}
.card{padding:22px}
.card h2{margin:0 0 8px;font-size:18px}
.muted{margin:0 0 16px;color:#8fa3c8;font-size:13px}
.result{min-height:20px;margin:16px 0 0;padding:14px;border-radius:16px;background:rgba(0,0,0,.28);border:1px solid rgba(255,255,255,.10);color:#bcd0f5;font-size:12px;white-space:pre-wrap;overflow:auto;max-height:200px;}
.toast{position:fixed;left:50%;bottom:26px;transform:translateX(-50%) translateY(20px);opacity:0;pointer-events:none;padding:12px 18px;border-radius:16px;background:rgba(10,14,25,.88);border:1px solid rgba(255,255,255,.18);backdrop-filter:blur(18px);color:#eaf2ff;font-size:13px;transition:.25s;z-index:80}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
@media(max-width:820px){.grid{grid-template-columns:1fr}.top{align-items:flex-start}.right{flex-wrap:wrap;justify-content:flex-end}}"""

JS_CONTENT = """const $ = (s) => document.querySelector(s);
const state = { token: localStorage.getItem("lg_token") || "", user: null };
const toastEl = $("#toast");
let toastTimer = null;

function toast(msg) { toastEl.textContent = msg; toastEl.classList.add("show"); clearTimeout(toastTimer); toastTimer = setTimeout(() => toastEl.classList.remove("show"), 3500); }

async function api(path, body = null, method = null) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers["X-Token"] = state.token;
  const opts = { method: method || (body ? "POST" : "GET"), headers };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({ ok: false, error: "Lỗi định dạng" }));
    if (!res.ok || data.ok === false) throw new Error(data.error || "Yêu cầu thất bại");
    return data;
  } catch (e) { throw new Error(e.message || "Không thể kết nối đến Server."); }
}

function setTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $("#loginForm").classList.toggle("hidden", name !== "login");
  $("#registerForm").classList.toggle("hidden", name !== "register");
  $("#adminForm").classList.toggle("hidden", name !== "admin");
}

function showAuth() { $("#app").classList.remove("hidden"); $("#authView").classList.remove("hidden"); $("#dashView").classList.add("hidden"); $("#logoutBtn").classList.add("hidden"); $("#userBadge").textContent = "Khách"; state.user = null; }

function updateStats() {
  if (!state.user) return;
  $("#userBadge").textContent = state.user.username + " • " + (state.user.role === 'admin' ? 'Quản trị' : 'Thành viên');
  $("#statRole").textContent = state.user.role === 'admin' ? 'QUẢN TRỊ VIÊN' : 'NGƯỜI DÙNG';
  
  if (state.user.role === 'admin' || state.user.premium_until > Date.now()/1000) {
      $("#statTrialCredits").textContent = "Không giới hạn";
  } else {
      $("#statTrialCredits").textContent = state.user.trial_uses + " lượt thử";
  }

  const now = Date.now() / 1000;
  if (state.user.role === "admin") { $("#statPremium").textContent = "VĨNH VIỄN"; $("#statPremium").style.color = "#00ffd5"; }
  else if (state.user.premium_until > now) { 
      if (state.user.premium_until > now + 31536000) { $("#statPremium").textContent = "VĨNH VIỄN"; }
      else { $("#statPremium").textContent = Math.ceil((state.user.premium_until - now) / 86400) + " NGÀY"; }
      $("#statPremium").style.color = "#00ffd5"; 
  }
  else { $("#statPremium").textContent = "CHƯA KÍCH HOẠT"; $("#statPremium").style.color = "#ff0055"; }
}

async function loadLeaderboard() {
  try {
    const d = await api("/api/top_donors", null, "GET");
    let html = "";
    d.top.forEach((u, i) => {
      let medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : "🏅";
      let color = i < 3 ? "#00ffd5" : "#bcd0f5";
      html += `<div style="display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.1); color:${color};">
        <span><b>${medal} ${u.username}</b></span>
        <span>${u.total_donated.toLocaleString('vi-VN')} đ</span>
      </div>`;
    });
    $("#leaderboard").innerHTML = html;
  } catch(e) {}
}

function showDash() { 
  $("#app").classList.remove("hidden"); $("#authView").classList.add("hidden"); $("#dashView").classList.remove("hidden"); 
  $("#logoutBtn").classList.remove("hidden"); updateStats(); loadLeaderboard();
  $("#adminCard").classList.toggle("hidden", state.user.role !== "admin"); 
}

async function refreshMe() {
  if (!state.token) return showAuth();
  try { const d = await api("/api/me", null, "GET"); state.user = d.user; showDash(); } catch (e) { state.token = ""; localStorage.removeItem("lg_token"); showAuth(); }
}

async function doLogin(path, user, pass) { const d = await api(path, { username: user, password: pass }); state.token = d.token; state.user = d.user; localStorage.setItem("lg_token", d.token); showDash(); toast("Đăng nhập thành công"); }

document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => setTab(b.dataset.tab)));
$("#loginForm").addEventListener("submit", async (e) => { e.preventDefault(); try { await doLogin("/api/login", $("#loginUser").value.trim(), $("#loginPass").value); } catch (err) { toast(err.message); } });
$("#registerForm").addEventListener("submit", async (e) => { e.preventDefault(); try { await api("/api/register", { username: $("#regUser").value.trim(), password: $("#regPass").value }); toast("Tạo TK thành công! Bạn có 3 lượt dùng thử."); setTab("login"); } catch (err) { toast(err.message); } });
$("#adminForm").addEventListener("submit", async (e) => { e.preventDefault(); try { await doLogin("/api/admin-login", $("#adminUser").value.trim(), $("#adminPass").value); } catch (err) { toast(err.message); } });
$("#logoutBtn").addEventListener("click", async () => { try { await api("/api/logout", {}); } catch (_) {} state.token = ""; state.user = null; localStorage.removeItem("lg_token"); showAuth(); });

async function buyVIP(tier, price) {
  if (!state.user) return toast("Vui lòng đăng nhập!");
  const confirmPay = confirm(`Bạn đã chuyển khoản ${price.toLocaleString('vi-VN')}đ chưa?\\n\\nBấm OK để hệ thống tự động duyệt và cấp Key.`);
  if (!confirmPay) return;
  
  toast("Đang kiểm tra giao dịch... Vui lòng đợi (khoảng 3s).");
  try {
    const d = await api("/api/buy_vip", { tier, price });
    alert(`THANH TOÁN THÀNH CÔNG!\\n\\nMã Key VIP của bạn là: ${d.key}\\n\\nHãy copy mã này và dán vào phần "Kích hoạt Key" để sử dụng.`);
    refreshMe();
  } catch (err) { toast(err.message); }
}

$("#spamForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const btn = e.target.querySelector("button"); btn.disabled = true; btn.textContent = "Đang xử lý...";
  try {
    const d = await api("/api/spam_smtp", { sender_email: $("#spamSenderEmail").value.trim(), sender_password: $("#spamSenderPass").value, recipients: $("#spamRecipients").value, subject: $("#spamSubject").value, body: $("#spamBody").value, count: Number($("#spamCount").value || 1) });
    $("#spamResult").textContent = JSON.stringify(d, null, 2); toast(d.message); refreshMe();
  } catch (err) { $("#spamResult").textContent = "LỖI:\\n" + err.message; } finally { btn.disabled = false; btn.textContent = "Bắt đầu gửi"; }
});

$("#termuxForm").addEventListener("submit", async (e) => {
  e.preventDefault(); const btn = e.target.querySelector("button"); btn.disabled = true; btn.textContent = "Đang gửi...";
  try {
    const d = await api("/api/spam_termux", { target: $("#termuxTarget").value.trim(), payload: $("#termuxPayload").value, type: $("#termuxType").value, count: Number($("#termuxCount").value || 1) });
    $("#termuxResult").textContent = JSON.stringify(d, null, 2); toast(d.message); refreshMe();
  } catch (err) { $("#termuxResult").textContent = "LỖI:\\n" + err.message; } finally { btn.disabled = false; btn.textContent = "Gửi lệnh xuống Agent"; }
});

$("#genKeyBtn").addEventListener("click", async () => { try { const d = await api("/api/gen_key", {}); $("#adminOutput").textContent = "KEY ĐÃ TẠO:\\n\\n" + d.key; toast("Đã tạo Key"); } catch (err) { toast(err.message); } });

(function initSplash(){
  const splash = document.getElementById("splash"); const bar = document.getElementById("splashBar"); const percent = document.getElementById("splashPercent"); const status = document.getElementById("splashStatus"); const skip = document.getElementById("splashSkip"); const letter = document.getElementById("serverLetter");
  if (!splash || !bar || !percent || !status || !skip) return;
  fetch("/api/boot").then(r => r.json()).then(d => { if (d.ok && letter) letter.textContent = d.letter; }).catch(() => {});
  const phases = [[0,"ĐANG KHỞI ĐỘNG"],[18,"TẢI LÕI GLASS"],[38,"GẮN LƯU TRỮ"],[58,"ĐỒNG BỘ TÀI KHOẢN"],[76,"HIỆU CHỈNH UI"],[92,"HOÀN TẤT"],[100,"SẴN SÀNG"]];
  let closed = false; let raf = null; const duration = 5000; const startTime = performance.now();
  function render(v){ const n = Math.max(0, Math.min(100, Math.round(v))); bar.style.width = n + "%"; percent.textContent = n + "%"; let label = phases[0][1]; for (const p of phases) if (n >= p[0]) label = p[1]; status.textContent = label; }
  function close(){ if (closed) return; closed = true; cancelAnimationFrame(raf); render(100); splash.classList.add("hide"); setTimeout(() => splash.remove(), 1000); }
  function tick(now){ if (closed) return; const elapsed = now - startTime; const progress = (elapsed / duration) * 100; if (progress >= 100){ close(); return; } render(progress); raf = requestAnimationFrame(tick); }
  skip.addEventListener("click", close); render(0); raf = requestAnimationFrame(tick); 
})();
window.addEventListener("load", () => { refreshMe(); });"""

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
        
    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f: data = f.read()
            self.send_response(200); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        except Exception:
            self.send_response(404); self.end_headers()

    def _session(self):
        return self.headers.get("X-Token", ""), SESSIONS.get(self.headers.get("X-Token", ""))

    def _check_quota(self, username, is_admin, cost=1):
        if is_admin: return True, ""
        accs = load_accounts()
        for a in accs:
            if a["username"] == username:
                if a.get("premium_until", 0) > time.time():
                    return True, ""
                elif a.get("trial_uses", 0) > 0:
                    a["trial_uses"] -= 1
                    save_accounts(accs)
                    return True, ""
                else:
                    return False, "Bạn đã hết 3 lượt dùng thử. Vui lòng nạp VIP để tiếp tục sử dụng."
        return False, "Lỗi User"

    def do_GET(self):
        try:
            p = urlparse(self.path).path
            if p in ["/", "/index.html"]: return self._string(HTML_CONTENT, "text/html")
            if p == "/style.css": return self._string(CSS_CONTENT, "text/css")
            if p == "/app.js": return self._string(JS_CONTENT, "application/javascript")
            if p in ["/qr.jpg", "/qr.png"]: 
                # Tự động tìm ảnh QR trong thư mục
                if os.path.exists("qr.jpg"): return self._file("qr.jpg", "image/jpeg")
                if os.path.exists("qr.png"): return self._file("qr.png", "image/png")
                return self._json(404, {"error": "QR image not found"})
                
            if p == "/api/boot": return self._json(200, {"ok": True, "letter": "B"})
            if p == "/api/agent_poll":
                try:
                    task = AGENT_QUEUE.get(timeout=5)
                    return self._json(200, {"ok": True, "task": task})
                except queue.Empty:
                    return self._json(200, {"ok": True, "task": None})
            if p == "/api/top_donors":
                accs = load_accounts()
                sorted_accs = sorted([a for a in accs if a.get("total_donated", 0) > 0], key=lambda x: x.get("total_donated", 0), reverse=True)
                top = [{"username": a["username"], "total_donated": a.get("total_donated", 0)} for a in sorted_accs[:10]]
                return self._json(200, {"ok": True, "top": top})
            if p == "/api/me":
                _, s = self._session()
                if not s: return self._json(401, {"ok": False, "error": "Unauthorized"})
                for a in load_accounts():
                    if a["username"] == s["username"]:
                        s["trial_uses"], s["premium_until"], s["total_donated"] = a.get("trial_uses", 0), a.get("premium_until", 0), a.get("total_donated", 0)
                return self._json(200, {"ok": True, "user": s})
            return self._json(404, {"ok": False})
        except Exception as e: return self._json(500, {"ok": False, "error": str(e)})

    def do_POST(self):
        try:
            p = urlparse(self.path).path
            n = int(self.headers.get("Content-Length", "0") or 0)
            try: body = json.loads(self.rfile.read(n) or b"{}")
            except: return self._json(400, {"ok": False})

            if p == "/api/register":
                u, pw = str(body.get("username", "")).strip(), str(body.get("password", ""))
                accs = load_accounts()
                if any(a["username"].lower() == u.lower() for a in accs): return self._json(409, {"ok": False, "error": "Tên đã tồn tại"})
                accs.append({"username": u, "password": hp(pw), "role": "user", "premium_until": 0, "credits": 0, "trial_uses": 3, "total_donated": 0})
                save_accounts(accs); return self._json(200, {"ok": True})
                
            if p in ["/api/login", "/api/admin-login"]:
                u, pw = str(body.get("username", "")).strip(), str(body.get("password", ""))
                for a in load_accounts():
                    if a["username"].lower() == u.lower() and vp(pw, a["password"]):
                        if p == "/api/admin-login" and a.get("role") != "admin": return self._json(401, {"ok": False, "error": "Không phải Admin"})
                        token = secrets.token_hex(24)
                        user = {"username": a["username"], "role": a.get("role", "user"), "premium_until": a.get("premium_until", 0), "trial_uses": a.get("trial_uses", 0), "total_donated": a.get("total_donated", 0)}
                        SESSIONS[token] = user
                        return self._json(200, {"ok": True, "token": token, "user": user})
                return self._json(401, {"ok": False, "error": "Sai tài khoản"})

            _, s = self._session()
            if not s: return self._json(401, {"ok": False})

            if p == "/api/buy_vip":
                tier = body.get("tier")
                price = int(body.get("price", 0))
                time.sleep(3) # Giả lập thời gian chờ ngân hàng xử lý
                
                keys = load_keys()
                new_key = f"BIMODDZ-VIP-{secrets.token_hex(4).upper()}"
                keys.append({"key": new_key, "used": False, "tier": tier})
                save_keys(keys)
                
                accs = load_accounts()
                for a in accs:
                    if a["username"] == s["username"]:
                        a["total_donated"] = a.get("total_donated", 0) + price
                        save_accounts(accs)
                        break
                return self._json(200, {"ok": True, "key": new_key, "message": "Tạo Key thành công!"})

            if p == "/api/spam_smtp":
                allowed, err = self._check_quota(s["username"], s.get("role")=="admin")
                if not allowed: return self._json(403, {"ok": False, "error": err})
                recipients = [x.strip() for x in str(body.get("recipients", "")).replace(",", "\n").splitlines() if x.strip()]
                threading.Thread(target=execute_smtp_spam, args=(
                    str(body.get("sender_email", "")), str(body.get("sender_password", "")),
                    recipients, str(body.get("subject", "")), str(body.get("body", "")), int(body.get("count", 1))
                )).start()
                return self._json(200, {"ok": True, "message": "Đã gửi yêu cầu SMTP"})

            if p == "/api/spam_termux":
                allowed, err = self._check_quota(s["username"], s.get("role")=="admin")
                if not allowed: return self._json(403, {"ok": False, "error": err})
                task_id = secrets.token_hex(8)
                AGENT_QUEUE.put({"id": task_id, "type": body.get("type"), "target": body.get("target"), "payload": body.get("payload"), "count": int(body.get("count", 1))})
                return self._json(200, {"ok": True, "message": f"Lệnh đã đẩy vào hàng đợi Agent"})

            if p == "/api/gen_key":
                if s.get("role") != "admin": return self._json(401, {"ok": False})
                keys = load_keys()
                new_key = f"BIMODDZ-ADMIN-{secrets.token_hex(4).upper()}"
                keys.append({"key": new_key, "used": False, "tier": "life"})
                save_keys(keys); return self._json(200, {"ok": True, "key": new_key})

            return self._json(404, {"ok": False})
        except Exception as e: return self._json(500, {"ok": False, "error": str(e)})

def main():
    init_db()
    port = int(os.environ.get("PORT", "10000"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    print(f"[*] Server đang chạy tại port {port}")
    srv.serve_forever()

if __name__ == "__main__":
    main()