from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from steam import get_owned_games, get_reviews, get_recent_games, get_achievements, get_achievement_schema, get_player_summary
from claude import get_recommendation, analyze_reviews, generate_insights, analyze_achievements, estimate_backlog, gaming_personality, game_match, generate_landing_commentary, generate_game_of_moment
import asyncio
from fastapi.responses import FileResponse
from rawg import get_genres_for_library, is_single_player
from database import create_db, get_cached, save_cache, engine
from models import CachedDashboard, CachedAchievements, CachedLibrary, CachedGenres, CachedBacklog, CachedPersonality, CachedLanding
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from datetime import datetime, timedelta
from steamspy import get_top_games_by_players, get_top_games_by_owners, get_hidden_gems

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def serve_landing():
    return FileResponse("landing.html")

@app.get("/app")
def serve_frontend():
    return FileResponse("index.html")

@app.get("/dashboard/{steam_id}")
async def dashboard(steam_id: str):
    try:
        games, recent = await asyncio.gather(
            get_owned_games(steam_id),
            get_recent_games(steam_id)
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to connect to Steam. Try again in a moment.")

    if not games:
        raise HTTPException(status_code=403,
                            detail="No games found. Your Steam profile is likely set to private. Set it to public at steamcommunity.com/my/edit/settings — make sure 'Game Details' is also set to public, not just your main profile.")



    review_list = []
    app_name = None
    for game in recent:
        app_name = game["name"]
        review_list = await get_reviews(game["appid"])
        if review_list:
            break

    try:
        recommendation, insights, review_analysis = await asyncio.gather(
            asyncio.to_thread(get_recommendation, games),
            asyncio.to_thread(generate_insights, games, recent),
            asyncio.to_thread(analyze_reviews, app_name, review_list) if review_list else asyncio.to_thread(lambda: "No reviews available.")
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Claude API error. Check your Anthropic API key.")

    return {
        "games_found": len(games),
        "recommendation": recommendation,
        "insights": insights,
        "review_analysis": {
            "game": app_name,
            "analysis": review_analysis
        }
    }

@app.get("/recommend/{steam_id}")
async def recommend(steam_id: str):
    games = await get_owned_games(steam_id)
    if not games:
        raise HTTPException(status_code=404, detail="No games found. Is your Steam profile set to public?")
    result = await asyncio.to_thread(get_recommendation, games)
    return {"recommendation": result}

@app.get("/reviews/{steam_id}")
async def reviews(steam_id: str):
    recent = await get_recent_games(steam_id)
    if not recent:
        raise HTTPException(status_code=404, detail="No recently played games found.")

    review_list = []
    app_id = None
    app_name = None

    for game in recent:
        app_id = game["appid"]
        app_name = game["name"]
        review_list = await get_reviews(app_id)
        if review_list:
            break

    if not review_list:
        raise HTTPException(status_code=404, detail="No reviews found for any recently played games.")

    result = await asyncio.to_thread(analyze_reviews, app_name, review_list)
    return {"game": app_name, "analysis": result}

@app.get("/reviews/game/{app_id}")
async def reviews_by_appid(app_id: int):
    review_list = await get_reviews(app_id)
    if not review_list:
        raise HTTPException(status_code=404, detail="No reviews found for this game.")
    result = await asyncio.to_thread(analyze_reviews, "this game", review_list)
    return {"analysis": result}

@app.get("/insights/{steam_id}")
async def insights(steam_id: str):
    games, recent = await asyncio.gather(
        get_owned_games(steam_id),
        get_recent_games(steam_id)
    )
    if not games:
        raise HTTPException(status_code=404, detail="No games found. Is your Steam profile set to public?")
    result = await asyncio.to_thread(generate_insights, games, recent)
    return {"insights": result}

@app.get("/library/{steam_id}")
async def library(steam_id: str):
    games = await get_owned_games(steam_id)
    if not games:
        raise HTTPException(status_code=404, detail="No games found. Is your Steam profile set to public?")

    sorted_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)
    return {
        "games": [
            {
                "name": g.get("name", "Unknown"),
                "playtime_hours": round(g.get("playtime_forever", 0) / 60, 1),
                "last_played": g.get("rtime_last_played", 0),
                "appid": g.get("appid")
            }
            for g in sorted_games
        ],
        "total": len(games)
    }

@app.get("/genres/{steam_id}")
async def genres(steam_id: str):
    cached = get_cached(CachedGenres, steam_id)
    if cached:
        return cached

    games = await get_owned_games(steam_id)
    if not games:
        raise HTTPException(status_code=404, detail="No games found.")

    top_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:30]
    genre_data = await get_genres_for_library(top_games)
    sorted_genres = sorted(genre_data["playtime"].items(), key=lambda x: x[1], reverse=True)
    result = {
        "genres": [{"name": g, "hours": h} for g, h in sorted_genres],
        "games_by_genre": genre_data["games"]
    }

    save_cache(CachedGenres, steam_id, result)
    return result

@app.get("/backlog/{steam_id}")
async def backlog(steam_id: str):
    cached = get_cached(CachedBacklog, steam_id)
    if cached:
        return cached

    games = await get_owned_games(steam_id)
    if not games:
        raise HTTPException(status_code=404, detail="No games found.")

    unplayed = [g for g in games if g.get("playtime_forever", 0) == 0]
    if not unplayed:
        return {"backlog": "You've played every game in your library! No backlog to clear.", "unplayed_count": 0}

    tasks = [is_single_player(game["name"]) for game in unplayed[:20]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    filtered_unplayed = [
        game for game, result in zip(unplayed[:20], results)
        if result is True
    ]

    result = await asyncio.to_thread(estimate_backlog, filtered_unplayed)
    response = {"backlog": result, "unplayed_count": len(filtered_unplayed)}

    save_cache(CachedBacklog, steam_id, response)
    return response

@app.get("/personality/{steam_id}")
async def personality(steam_id: str):
    cached = get_cached(CachedPersonality, steam_id)
    if cached:
        return cached

    games, recent = await asyncio.gather(
        get_owned_games(steam_id),
        get_recent_games(steam_id)
    )
    if not games:
        raise HTTPException(status_code=404, detail="No games found.")

    result = await asyncio.to_thread(gaming_personality, games, recent)
    response = {"personality": result}

    save_cache(CachedPersonality, steam_id, response)
    return response

@app.get("/profile/{steam_id}")
async def profile(steam_id: str):
    player, recent = await asyncio.gather(
        get_player_summary(steam_id),
        get_recent_games(steam_id)
    )
    if not player:
        raise HTTPException(status_code=404, detail="Profile not found.")

    recent_hours = round(sum(g.get("playtime_2weeks", 0) for g in recent) / 60, 1)

    return {
        "name": player.get("personaname", "Unknown"),
        "avatar": player.get("avatarfull", ""),
        "profile_url": player.get("profileurl", ""),
        "country": player.get("loccountrycode", ""),
        "recent_hours": recent_hours
    }

@app.get("/achievements/{steam_id}")
async def achievements(steam_id: str):
    cached = get_cached(CachedAchievements, steam_id)
    if cached:
        return cached

    games = await get_owned_games(steam_id)
    if not games:
        raise HTTPException(status_code=404, detail="No games found.")

    score_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:25]
    top_games = score_games

    achievement_data = []
    total_unlocked = 0
    total_possible = 0
    games_with_achievements = 0

    for game in score_games:
        stats = await get_achievements(steam_id, game["appid"])
        if stats and "achievements" in stats:
            unlocked = [a for a in stats["achievements"] if a["achieved"] == 1]
            total = len(stats["achievements"])
            total_unlocked += len(unlocked)
            total_possible += total
            games_with_achievements += 1

            if game in top_games:
                schema = await get_achievement_schema(game["appid"])
                locked = [a for a in stats["achievements"] if a["achieved"] == 0]
                closest_named = [schema.get(a["apiname"], a["apiname"]) for a in locked[:5]]
                achievement_data.append({
                    "game": game["name"],
                    "unlocked": len(unlocked),
                    "total": total,
                    "closest": closest_named
                })

    if not achievement_data:
        raise HTTPException(status_code=404, detail="No achievement data found.")

    achievement_data = [
        g for g in achievement_data
        if g["total"] > 0 and (g["unlocked"] / g["total"]) >= 0.30
    ]
    achievement_data = sorted(achievement_data, key=lambda g: g["unlocked"] / g["total"], reverse=True)[:5]

    overall_percentage = round((total_unlocked / total_possible * 100), 1) if total_possible > 0 else 0

    if overall_percentage >= 75:
        rank = "S-Tier Hunter"
        rank_desc = "Elite completionist — you don't leave achievements on the table"
    elif overall_percentage >= 50:
        rank = "A-Tier Hunter"
        rank_desc = "Dedicated achievement chaser — you finish what you start"
    elif overall_percentage >= 30:
        rank = "B-Tier Hunter"
        rank_desc = "Solid effort — you grab the meaningful achievements"
    elif overall_percentage >= 15:
        rank = "C-Tier Hunter"
        rank_desc = "Casual collector — you unlock what comes naturally"
    else:
        rank = "Casual Player"
        rank_desc = "Achievements aren't really your focus — you play for the experience"

    result = await asyncio.to_thread(analyze_achievements, achievement_data)
    response = {
        "achievements": result,
        "games_analyzed": len(achievement_data),
        "overall_percentage": overall_percentage,
        "total_unlocked": total_unlocked,
        "total_possible": total_possible,
        "games_with_achievements": games_with_achievements,
        "rank": rank,
        "rank_desc": rank_desc,
        "per_game": achievement_data
    }

    save_cache(CachedAchievements, steam_id, response)
    return response

@app.get("/match/{steam_id}")
async def match(steam_id: str, time: str = Query(...), mood: str = Query(...), company: str = Query(...), style: str = Query(...)):
    games = await get_owned_games(steam_id)
    if not games:
        raise HTTPException(status_code=404, detail="No games found.")
    result = await asyncio.to_thread(game_match, games, time, mood, company, style)
    return {"match": result}

@app.get("/trending")
async def trending():
    games = await get_top_games_by_players()
    return {"games": games}

@app.get("/top")
async def top():
    games = await get_top_games_by_owners()
    return {"games": games}

@app.get("/landing-data")
async def landing_data():
    with Session(engine) as session:
        cached = session.exec(select(CachedLanding)).first()
        if cached:
            age = datetime.utcnow() - cached.cached_at.replace(tzinfo=None)
            if age < timedelta(hours=4):
                return cached.data

    trending, top, gems = await asyncio.gather(
        get_top_games_by_players(),
        get_top_games_by_owners(),
        get_hidden_gems()
    )

    commentary, game_of_moment = await asyncio.gather(
        asyncio.to_thread(generate_landing_commentary, trending, top, gems),
        asyncio.to_thread(generate_game_of_moment, trending)
    )

    result = {
        "trending": trending,
        "top": top,
        "gems": gems,
        "commentary": commentary,
        "game_of_moment": game_of_moment
    }

    with Session(engine) as session:
        existing = session.exec(select(CachedLanding)).first()
        if existing:
            existing.data = result
            existing.cached_at = datetime.utcnow()
            session.add(existing)
        else:
            session.add(CachedLanding(id=1, data=result, cached_at=datetime.utcnow()))
        session.commit()

    return result