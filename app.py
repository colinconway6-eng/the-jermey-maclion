import os, re, json, random, hashlib
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_FILE = "jermey_maclion_v4_db.json"

def get_today(): return datetime.now().strftime("%Y-%m-%d")
def load_db():
    today = get_today()
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: d = json.load(f)
            if today not in d["daily_points"]: d["daily_points"][today] = 0
            if today not in d["daily_progress"]: d["daily_progress"][today] = {}
            return d
        except Exception: pass
    return {"points": 0, "owned_players": {}, "selected_players": {}, "daily_points": {today: 0}, "daily_progress": {today: {}}}

def save_db(d): 
    with open(DB_FILE, "w") as f: json.dump(d, f)

ALL_PLAYERS_POOL = {
    "MLB": [
        {"id": "m1", "tier": 1, "name": "Garrett Stubbs", "role": "Backup C", "cost": 0, "img": "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/596117/headshot/67/current"},
        {"id": "m2", "tier": 2, "name": "Alec Bohm", "role": "3B", "cost": 150, "img": "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/664761/headshot/67/current"},
        {"id": "m3", "tier": 3, "name": "Jimmy Rollins", "role": "SS", "cost": 300, "img": "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/276519/headshot/67/current"},
        {"id": "m4", "tier": 4, "name": "Chase Utley", "role": "2B", "cost": 500, "img": "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/400284/headshot/67/current"},
        {"id": "m5", "tier": 5, "name": "Bryce Harper", "role": "RF", "cost": 750, "img": "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/547180/headshot/67/current"},
        {"id": "m6", "tier": 6, "name": "Barry Bonds", "role": "GOAT", "cost": 1050, "img": "https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/111188/headshot/67/current"}
    ],
    "NFL": [{"id": f"n{i}", "tier": i, "name": n, "role": "Player", "cost": c, "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Boston_Scott_2019.jpg/220px-Boston_Scott_2019.jpg"} for i, (n, c) in enumerate([("Boston Scott",0),("Dallas Goedert",150),("Jason Kelce",300),("DeSean Jackson",500),("Saquon Barkley",750),("Jeremy Maclin",1050)], 1)],
    "EPL": [{"id": f"e{i}", "tier": i, "name": n, "role": "Player", "cost": c, "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Timo_Werner_2018.jpg/220px-Timo_Werner_2018.jpg"} for i, (n, c) in enumerate([("Timo Werner",0),("Jack Grealish",150),("Cole Palmer",300),("Mohamed Salah",500),("Thierry Henry",750),("Ronaldo R9",1050)], 1)],
    "NBA": [{"id": f"b{i}", "tier": i, "name": n, "role": "Player", "cost": c, "img": "https://cdn.nba.com/headshots/nba/latest/1040x760/1627732.png"} for i, (n, c) in enumerate([("Ben Simmons",0),("Tyrese Maxey",150),("Damian Lillard",300),("Allen Iverson",500),("LeBron James",750),("Stephen Curry",1050)], 1)]
}

def get_roster(sport):
    return ALL_PLAYERS_POOL[sport]

QUESTIONS_BANK = {
    "MLB": [{"prompt": "Name an MLB Player in the 500+ HR Club", "answers": {"Barry Bonds": 32, "Babe Ruth": 30, "Hank Aaron": 25, "Alex Rodriguez": 23, "Albert Pujols": 21, "Ken Griffey Jr.": 20}} for _ in range(6)],
    "NFL": [{"prompt": "Name an NFL QB with 40,000+ Passing Yards", "answers": {"Tom Brady": 34, "Peyton Manning": 28, "Drew Brees": 26, "Aaron Rodgers": 24}} for _ in range(6)],
    "EPL": [{"prompt": "Name a Player with 100+ Premier League Goals", "answers": {"Alan Shearer": 31, "Harry Kane": 29, "Wayne Rooney": 28, "Mohamed Salah": 27}} for _ in range(6)],
    "NBA": [{"prompt": "Name an NBA Player with 60+ Points in a Game", "answers": {"Wilt Chamberlain": 32, "Kobe Bryant": 31, "Michael Jordan": 28, "LeBron James": 26}} for _ in range(6)]
}

def get_questions(sport): return QUESTIONS_BANK[sport]
def normalize(s): return re.sub(r"[^a-z0-9]", "", s.lower())

def get_state(sport):
    db = load_db(); today = get_today()
    if sport not in db["daily_progress"][today]: db["daily_progress"][today][sport] = {"history": [], "total_pts": 0}
    roster = get_roster(sport)
    owned = db["owned_players"].get(sport, [roster[0]["id"]])
    sel_id = db["selected_players"].get(sport, roster[0]["id"])
    sel_player = next((p for p in roster if p["id"] == sel_id), roster[0])
    return {
        "date": today, "points": db["points"], "today_points": db["daily_points"].get(today, 0),
        "owned_players": owned, "selected_player": sel_player, "roster": roster,
        "questions": get_questions(sport), "sport_progress": db["daily_progress"][today][sport]
    }

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>THE JERMEY MACLION</title>
  <style>
    :root{
      --bg:#070b14;--panel:#11192c;--border:#293856;--gold:#fbbf24;--neon:#38bdf8;--green:#22c55e;--red:#ef4444;
    }
    *{box-sizing:border-box;font-family:'Trebuchet MS',sans-serif;}
    body{margin:0;background:radial-gradient(circle at top,#1e293b 0%,#070b14 75%);color:#f8fafc;min-height:100vh;}
    .cartoon-headshot{width:76px;height:76px;border-radius:50%;object-fit:cover;border:4px solid var(--gold);background:#1e293b;filter:contrast(1.4) saturate(1.65);}
    header{background:rgba(11,17,32,0.96);border-bottom:3px solid var(--gold);padding:14px 24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;position:sticky;top:0;z-index:100;}
    .brand{font-size:28px;font-weight:900;color:var(--gold);text-shadow:3px 3px 0px #000;}
    .hud-bar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;}
    .hud-pill{background:#1e293b;border:2px solid #334155;padding:7px 14px;border-radius:12px;font-size:13px;font-weight:700;}
    .hud-pill span{color:var(--neon);}
    .pts-badge{background:linear-gradient(135deg,#fbbf24,#d97706);color:#090d16;padding:8px 18px;border-radius:12px;font-size:17px;font-weight:900;border:2px solid #fff;}
    .container{max-width:1180px;margin:22px auto;padding:0 16px;}
    .sport-tabs{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
    .sport-btn{background:#172136;border:3px solid #2e4166;color:#fff;padding:14px;border-radius:14px;font-size:16px;font-weight:900;cursor:pointer;}
    .sport-btn.active,.sport-btn:hover{background:#1d4ed8;border-color:var(--gold);}
    .card{background:var(--panel);border:2px solid var(--border);border-radius:18px;padding:20px;box-shadow:0 10px 28px rgba(0,0,0,0.5);margin-bottom:20px;}
    .q-progress{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:16px;}
    .q-step{background:#0b1120;border:2px solid #334155;border-radius:10px;padding:10px 6px;text-align:center;font-size:12px;font-weight:800;}
    .q-step.current{border-color:var(--gold);background:#1e3a8a;}
    .q-step.done{border-color:var(--green);background:rgba(34,197,94,0.15);}
    .q-step.miss{border-color:var(--red);background:rgba(239,68,68,0.15);}
    .question-banner{background:linear-gradient(135deg,#0b1329,#1e293b);border:3px solid var(--neon);border-radius:16px;padding:20px;text-align:center;}
    .q-title{font-size:22px;font-weight:900;color:#fde047;margin:6px 0 12px 0;}
    .input-row{display:flex;gap:10px;max-width:720px;margin:0 auto;}
    .ans-input{flex:1;padding:14px;border-radius:12px;border:2px solid #475569;background:#070b14;color:#fff;font-size:16px;font-weight:700;outline:none;}
    .submit-btn{background:linear-gradient(135deg,#22c55e,#15803d);color:#fff;border:2px solid #fff;padding:0 22px;border-radius:12px;font-weight:900;font-size:15px;cursor:pointer;}
    #postSixPopUp{display:none;}
    .popup-grid{display:grid;grid-template-columns:1.15fr 1.25fr;gap:20px;}
    .roster-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:10px;}
    .player-card{background:#0b1120;border:2px solid #334155;border-radius:14px;padding:10px;display:flex;gap:10px;align-items:center;}
    .player-card.selected{border-color:var(--green);background:rgba(34,197,94,0.16);}
    .p-info{flex:1;}
    .p-name{font-weight:900;font-size:15px;color:#fbbf24;}
    .p-tier{font-size:11px;color:#38bdf8;}
    .buy-btn{background:var(--gold);color:#090d16;border:none;padding:6px 12px;border-radius:8px;font-weight:900;font-size:12px;cursor:pointer;}
  </style>
</head>
<body>
  <header>
    <div class="brand">★ THE JERMEY MACLION</div>
    <div class="hud-bar">
      <div class="hud-pill">Ὄ5 Date: <span id="hudDate"></span></div>
      <div class="hud-pill">ὒ5 Today: <span id="hudTodayPts">0</span> PTS</div>
      <div class="pts-badge">Ὃ0 Bank: <span id="hudBankPts">0</span> PTS</div>
    </div>
  </header>
  <div class="container">
    <div class="sport-tabs">
      <button class="sport-btn active" onclick="switchSport('MLB',this)">⚾ MLB</button>
      <button class="sport-btn" onclick="switchSport('NFL',this)">Ἴ8 NFL</button>
      <button class="sport-btn" onclick="switchSport('EPL',this)">⚽ EPL</button>
      <button class="sport-btn" onclick="switchSport('NBA',this)">Ἴ0 NBA</button>
    </div>
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <div style="font-weight:900;color:#38bdf8;" id="sportHeaderLabel">MLB Questions</div>
        <button class="buy-btn" style="background:#334155;color:#cbd5e1;" onclick="resetSport()">↻ Replay</button>
      </div>
      <div class="q-progress" id="qProgressRow"></div>
      <div class="question-banner">
        <div class="q-title" id="qPromptText">Loading...</div>
        <div class="input-row">
          <input type="text" id="ansInput" class="ans-input" placeholder="Type answer..." onkeydown="if(event.key==='Enter') submitAnswer()">
          <button class="submit-btn" onclick="submitAnswer()">⚡ SUBMIT</button>
        </div>
      </div>
    </div>
    <div id="postSixPopUp">
      <div class="popup-grid">
        <div class="card">
          <h3 style="margin:0;color:#fbbf24;">Pick Player for <span id="rosterSportLabel">MLB</span></h3>
          <div class="roster-grid" id="rosterGrid"></div>
        </div>
      </div>
    </div>
  </div>
  <script>
    let current='MLB', state=null;
    async function fetchState(){
      const r=await fetch(`/api/state?sport=${current}`);
      state=await r.json();
      render();
    }
    function switchSport(s,btn){
      current=s;
      document.querySelectorAll('.sport-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      fetchState();
    }
    function render(){
      document.getElementById('hudDate').innerText=state.date;
      document.getElementById('hudTodayPts').innerText=state.today_points;
      document.getElementById('hudBankPts').innerText=state.points;
      document.getElementById('sportHeaderLabel').innerText=`${current} - Daily Challenge`;
      document.getElementById('rosterSportLabel').innerText=current;
      let pRow=document.getElementById('qProgressRow'); pRow.innerHTML='';
      let hist=state.sport_progress.history;
      for(let i=0; i<6; i++){
        let h=hist[i];
        if(h) pRow.innerHTML+=`<div class="q-step ${h.pts>0?'done':'miss'}">Q${i+1}</div>`;
        else if(i===hist.length) pRow.innerHTML+=`<div class="q-step current">Q${i+1}</div>`;
        else pRow.innerHTML+=`<div class="q-step">Q${i+1}</div>`;
      }
      let pop=document.getElementById('postSixPopUp'), inp=document.querySelector('.input-row');
      if(hist.length<6){
        document.getElementById('qPromptText').innerText=state.questions[hist.length].prompt;
        inp.style.display='flex'; pop.style.display='none';
      } else {
        document.getElementById('qPromptText').innerHTML='🏆 Challenge Completed!';
        inp.style.display='none'; pop.style.display='block';
      }
      let rGrid=document.getElementById('rosterGrid'); rGrid.innerHTML='';
      state.roster.forEach(p=>{
        let owned=state.owned_players.includes(p.id)||p.cost===0, sel=state.selected_player.id===p.id;
        rGrid.innerHTML+=`<div class="player-card ${sel?'selected':''}"><img src="${p.img}" class="cartoon-headshot"><div class="p-info"><div class="p-name">${p.name}</div><div class="p-tier">${p.role}</div><button class="buy-btn" onclick="selectPlayer('${p.id}')">${sel?'SELECTED':(owned?'SELECT':'BUY ('+p.cost+')')}</button></div></div>`;
      });
    }
    async function submitAnswer(){
      let inp=document.getElementById('ansInput'), g=inp.value.trim(); if(!g)return;
      let r=await fetch('/api/answer_question',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sport:current,guess:g})});
      let d=await r.json(); inp.value=''; state=d.state; render();
    }
    async function selectPlayer(id){
      let r=await fetch('/api/select_player',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sport:current,player_id:id})});
      let d=await r.json(); state=d.state; render();
    }
    async function resetSport(){
      let r=await fetch('/api/reset_sport',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sport:current})});
      let d=await r.json(); state=d.state; render();
    }
    window.onload=fetchState;
  </script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/api/state")
def api_state(): return jsonify(get_state(request.args.get("sport", "MLB")))

@app.route("/api/answer_question", methods=["POST"])
def api_answer():
    b = request.json; sport = b.get("sport", "MLB"); guess = b.get("guess", "").strip()
    db = load_db(); today = get_today()
    prog = db["daily_progress"][today][sport]
    idx = len(prog["history"])
    qs = get_questions(sport)
    if idx >= 6: return jsonify({"state": get_state(sport)})
    ans_dict = qs[idx]["answers"]
    matched = next((k for k in ans_dict if normalize(k) == normalize(guess)), None)
    
    if matched:
        pts = 100
        prog["history"].append({"ans": matched, "pts": pts, "cat": "SUCCESS"})
        prog["total_pts"] += pts; db["points"] += pts; db["daily_points"][today] += pts
        save_db(db)
        fb = f"\\u2705 Correct! +{pts} PTS"
    else:
        prog["history"].append({"ans": guess, "pts": 0, "cat": "MISS"})
        save_db(db)
        fb = "\\u274c Incorrect answer."
    return jsonify({"feedback": fb, "state": get_state(sport)})

@app.route("/api/select_player", methods=["POST"])
def api_select():
    b = request.json; sport = b.get("sport", "MLB"); pid = b.get("player_id")
    db = load_db(); roster = get_roster(sport)
    target = next((p for p in roster if p["id"] == pid), None)
    if not target: return jsonify({})
    owned = db["owned_players"].get(sport, [roster[0]["id"]])
    if pid in owned or target["cost"] == 0:
        db["selected_players"][sport] = pid; save_db(db)
    elif db["points"] >= target["cost"]:
        db["points"] -= target["cost"]; owned.append(pid); db["owned_players"][sport] = owned; db["selected_players"][sport] = pid; save_db(db)
    return jsonify({"state": get_state(sport)})

@app.route("/api/reset_sport", methods=["POST"])
def api_reset():
    sport = request.json.get("sport", "MLB"); db = load_db(); today = get_today()
    db["daily_progress"][today][sport] = {"history": [], "total_pts": 0}; save_db(db)
    return jsonify({"state": get_state(sport)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
