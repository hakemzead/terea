from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import sqlite3
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# اسم ملف قاعدة البيانات المحلي
DB_FILE = "database.db"

def init_db():
    """إنشاء جدول قاعدة البيانات إذا لم يكن موجوداً"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shows (
            show_id TEXT PRIMARY KEY,
            title TEXT,
            category TEXT,
            image TEXT,
            description TEXT,
            episodes TEXT  -- سنخزن الحلقات بصيغة JSON داخل نص
        )
    """)
    conn.commit()
    conn.close()

# تشغيل قاعدة البيانات عند بدء التطبيق
init_db()

import json

def load_data():
    """قراءة البيانات من قاعدة البيانات وترتيبها بنفس هيكل التطبيق القديم"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT show_id, title, category, image, description, episodes FROM shows")
    rows = cursor.fetchall()
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
    """حفظ أو تحديث المسلسل والحلقات في قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO shows (show_id, title, category, image, description, episodes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (show_id, title, category, image, description, json.dumps(episodes, ensure_ascii=False)))
    conn.commit()
    conn.close()

def delete_show_from_db(show_id):
    """حذف مسلسل من قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shows WHERE show_id = ?", (show_id,))
    conn.commit()
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
        # المسلسل موجود مسبقاً، نضيف الحلقة الجديدة عليه
        episodes = shows[show_id]["episodes"]
        episodes[episode_number] = {
            "title": f"الحلقة {episode_number}",
            "servers": {
                "سيرفر المشاهدة": server_url
            }
        }
        save_show_to_db(show_id, shows[show_id]["title"], shows[show_id]["category"], shows[show_id]["image"], shows[show_id]["description"], episodes)
    else:
        # مسلسل جديد كلياً
        episodes = {
            episode_number: {
                "title": f"الحلقة {episode_number}",
                "servers": {
                    "سيرفر المشاهدة": server_url
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
        episodes[episode_number] = {
            "title": f"الحلقة {episode_number}",
            "servers": {
                "سيرفر المشاهدة": server_url
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
        context={"show": show_data}
    )

@app.get("/watch/{episode_id}")
def watch_video(request: Request, episode_id: str):
    data = load_data()
    shows = data.get("shows", {})
    
    target_episode = None
    all_episodes = {}
    found_series_id = None
    
    for s_id, show in shows.items():
        eps = show.get("episodes", {})
        if episode_id in eps:
            target_episode = eps[episode_id]
            all_episodes = eps
            found_series_id = s_id
            break
            
    if not target_episode:
        raise HTTPException(status_code=404, detail="الحلقة غير موجودة")
    
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
            "series_id": found_series_id
        }
    )