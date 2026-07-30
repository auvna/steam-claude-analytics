import httpx
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

RAWG_KEY = os.getenv("RAWG_API_KEY")
BASE = "https://api.rawg.io/api"


async def get_game_genres(game_name: str) -> list:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{BASE}/games", params={
                "key": RAWG_KEY,
                "search": game_name,
                "search_precise": "true",
                "page_size": 1
            })
            data = r.json()
            results = data.get("results", [])

            if not results:

                return []

            matched_name = results[0].get("name", "")
            genres = [g["name"] for g in results[0].get("genres", [])]

            return genres
        except Exception:
           
            return []


async def get_genres_for_library(games: list) -> dict:
    tasks = [get_game_genres(game["name"]) for game in games[:20]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    genre_playtime = {}
    genre_games = {}

    for game, genres in zip(games[:20], results):
        if isinstance(genres, Exception) or not genres:
            continue
        playtime_hours = round(game.get("playtime_forever", 0) / 60, 1)
        for genre in genres:
            if genre in genre_playtime:
                genre_playtime[genre] += playtime_hours
                genre_games[genre].append({
                    "name": game["name"],
                    "hours": playtime_hours
                })
            else:
                genre_playtime[genre] = playtime_hours
                genre_games[genre] = [{
                    "name": game["name"],
                    "hours": playtime_hours
                }]

    return {"playtime": genre_playtime, "games": genre_games}


async def is_single_player(game_name: str) -> bool:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(f"{BASE}/games", params={
                "key": RAWG_KEY,
                "search": game_name,
                "search_precise": "true",
                "page_size": 1
            })
            data = r.json()
            results = data.get("results", [])
            if not results:
                return True
            tags = [t["name"].lower() for t in results[0].get("tags", [])]
            genres = [g["name"].lower() for g in results[0].get("genres", [])]
            multiplayer_keywords = ["multiplayer", "mmo", "massively multiplayer", "online", "co-op", "battle royale"]
            singleplayer_keywords = ["singleplayer", "single player", "single-player"]
            has_singleplayer = any(kw in tags for kw in singleplayer_keywords)
            is_multiplayer_only = any(kw in tags for kw in multiplayer_keywords) and not has_singleplayer
            if "massively multiplayer" in genres:
                return False
            return not is_multiplayer_only
        except Exception:
            return True