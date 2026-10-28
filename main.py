from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import json
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def load_data():
    if not os.path.exists("episodes.json"):
        return {"shows": {}}
    with open("episodes.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("episodes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
    if "shows" not in data:
        data["shows"] = {}
    
    if show_id in data["shows"]:
        data["shows"][show_id]["episodes"][episode_number] = {
            "title": f"الحلقة {episode_number}",
            "servers": {
                "سيرفر المشاهدة": server_url
            }
        }
    else:
        data["shows"][show_id] = {
            "title": title,
            "category": category,
            "image": image,
            "description": description,
            "episodes": {
                episode_number: {
                    "title": f"الحلقة {episode_number}",
                    "servers": {
                        "سيرفر المشاهدة": server_url
                    }
                }
            }
        }
    
    save_data(data)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/add-episode")
def add_episode(
    show_id: str = Form(...),
    episode_number: str = Form(...),
    server_url: str = Form(...)
):
    data = load_data()
    if "shows" in data and show_id in data["shows"]:
        if "episodes" not in data["shows"][show_id]:
            data["shows"][show_id]["episodes"] = {}
        
        data["shows"][show_id]["episodes"][episode_number] = {
            "title": f"الحلقة {episode_number}",
            "servers": {
                "سيرفر المشاهدة": server_url
            }
        }
        save_data(data)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/delete-show/{show_id}")
def delete_show(show_id: str):
    data = load_data()
    if "shows" in data and show_id in data["shows"]:
        del data["shows"][show_id]
        save_data(data)
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