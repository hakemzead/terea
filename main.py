from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import psycopg2
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# رابط الاتصال بقاعدة بيانات Supabase باستخدام Transaction Pooler
DATABASE_URL = "postgresql://postgres.xhhkpnwagcpmjgdhxsku:HHhakem2000%40@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shows (
            show_id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            image TEXT,
            description TEXT,
            episodes TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# تشغيل دالة إنشاء الجدول عند تشغيل السيرفر
init_db()

def load_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT show_id, title, category, image, description, episodes FROM shows")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    shows = {}
    for row in rows:
        show_id, title, category, image, description, episodes_json = row
        shows[show_id] = {
            "title": title,
            "category": category,
            "image": image,
            "description": description,
            "episodes": json.loads(episodes_json) if episodes_json else {}
        }
    return {"shows": shows}

def save_show_to_db(show_id, title, category, image, description, episodes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO shows (show_id, title, category, image, description, episodes)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (show_id) DO UPDATE SET
            title = EXCLUDED.title,
            category = EXCLUDED.category,
            image = EXCLUDED.image,
            description = EXCLUDED.description,
            episodes = EXCLUDED.episodes
    """, (show_id, title, category, image, description, json.dumps(episodes, ensure_ascii=False)))
    conn.commit()
    cursor.close()
    conn.close()

def delete_show_from_db(show_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shows WHERE show_id = %s", (show_id,))
    conn.commit()
    cursor.close()
    conn.close()

@app.get("/")
def home(request: Request):
    data = load_data()
    shows = data.get("shows", {})
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"shows": shows}
    )

@app.get("/dashboard")
def dashboard(request: Request):
    data = load_data()
    shows = data.get("shows", {})
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html",
        context={"shows": shows}
    )

@app.post("/add-show")
def add_show(
    show_id: str = Form(...),
    title: str = Form(...),
    category: str = Form(...),
    image: str = Form(...),
    description: str = Form(...),
    episode_number: str = Form(...),
    server_url: str = Form(...)
):
    data = load_data()
    shows = data.get("shows", {})
    
    if show_id in shows:
        episodes = shows[show_id]["episodes"]
        episodes[str(episode_number)] = {
            "title": f"الحلقة {episode_number}",
            "servers": {
                "سيرفر 1": server_url
            }
        }
        save_show_to_db(
            show_id, 
            shows[show_id]["title"], 
            shows[show_id]["category"], 
            shows[show_id]["image"], 
            shows[show_id]["description"], 
            episodes
        )
    else:
        episodes = {
            str(episode_number): {
                "title": f"الحلقة {episode_number}",
                "servers": {
                    "سيرفر 1": server_url
                }
            }
        }
        save_show_to_db(show_id, title, category, image, description, episodes)
    
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/add-episode")
def add_episode(
    show_id: str = Form(...),
    episode_number: str = Form(...),
    server_url: str = Form(...)
):
    data = load_data()
    shows = data.get("shows", {})
    
    if show_id in shows:
        episodes = shows[show_id]["episodes"]
        episodes[str(episode_number)] = {
            "title": f"الحلقة {episode_number}",
            "servers": {
                "سيرفر 1": server_url
            }
        }
        save_show_to_db(
            show_id, 
            shows[show_id]["title"], 
            shows[show_id]["category"], 
            shows[show_id]["image"], 
            shows[show_id]["description"], 
            episodes
        )
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/delete-show/{show_id}")
def delete_show(show_id: str):
    delete_show_from_db(show_id)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/series/{series_id}")
def series_details(request: Request, series_id: str):
    data = load_data()
    shows = data.get("shows", {})
    
    if series_id not in shows:
        raise HTTPException(status_code=404, detail="المسلسل غير موجود")
    
    show_data = shows[series_id]
    return templates.TemplateResponse(
        request=request, 
        name="series.html", 
        context={"show": show_data, "series_id": series_id}
    )

@app.get("/watch/{series_id}/{episode_id}")
def watch_video(request: Request, series_id: str, episode_id: str):
    data = load_data()
    shows = data.get("shows", {})
    
    if series_id not in shows:
        raise HTTPException(status_code=404, detail="المسلسل غير موجود")
    
    show_data = shows[series_id]
    all_episodes = show_data.get("episodes", {})
    
    if episode_id not in all_episodes:
        raise HTTPException(status_code=404, detail="الحلقة غير موجودة")
        
    target_episode = all_episodes[episode_id]
    
    episode_keys = sorted(all_episodes.keys(), key=lambda x: int(x) if x.isdigit() else x)
    current_index = episode_keys.index(episode_id)
    
    prev_id = episode_keys[current_index - 1] if current_index > 0 else None
    next_id = episode_keys[current_index + 1] if current_index < len(episode_keys) - 1 else None
    
    return templates.TemplateResponse(
        request=request, 
        name="watch.html", 
        context={
            "episode": target_episode,
            "prev_id": prev_id,
            "next_id": next_id,
            "series_id": series_id
        }
    )