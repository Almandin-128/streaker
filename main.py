import praw
import os
import time
import logging
import threading
import schedule
from flask import Flask, jsonify
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# CONFIGURATION LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# CONFIGURATION REDDIT
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="Almandin",
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD")
)

SUBREDDIT = "toyhouse"

def check_if_i_posted_today():
    """Vérifie si l'utilisateur a posté dans les dernières 24h"""
    try:
        me = reddit.user.me()
        subreddit = reddit.subreddit(SUBREDDIT)
        cutoff = time.time() - 86400
        
        for submission in subreddit.new(limit=30):
            if (submission.author == me and submission.created_utc > cutoff):
                return True
        return False
    except Exception as e:
        log.error(f"Erreur lors du check Reddit : {e}")
        return False

def action_if_streak_incomplete():
    """Action déclenchée si aucune activité n'est détectée"""
    if check_if_i_posted_today():
        log.info("✅ STREAK OK : Activité déjà détectée aujourd'hui.")
        return {"status": "ok", "message": "Streak already secured"}
    
    # Remplacer l'upvote auto par un log système
    log.warning("⚠️ ACTION REQUISE : La streak est incomplète !")
    log.info("LOG : 'action_if_streak_incomplete' déclenché à la fin de la journée.")
    
    return {"status": "pending", "message": "Action log generated - Check required"}

def get_dashboard_data():
    """Prépare les données pour l'interface web"""
    me = reddit.user.me()
    posted = check_if_i_posted_today()
    return {
        "user": me.name,
        "subreddit": SUBREDDIT,
        "utc_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "streak_secured": posted,
        "status": "🟢 SÉCURISÉ" if posted else "🔴 ACTION REQUISE"
    }

# --- PLANIFICATION (UTC) ---
schedule.every().day.at("23:50").do(action_if_streak_incomplete)

def run_scheduler():
    log.info("⏰ Planificateur démarré (Checks à 23:50 UTC)")
    while True:
        schedule.run_pending()
        time.sleep(30)

# --- ROUTES FLASK ---
@app.route('/')
@app.route('/health')
def health():
    data = get_dashboard_data()
    return f"<h1>Toyhouse Bot Status</h1><pre>{data}</pre>"

@app.route('/api/status')
def api_status():
    return jsonify(get_dashboard_data())

if __name__ == "__main__":
    # Lancement du planificateur en arrière-plan
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # Lancement du serveur (Render définit la variable PORT)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

