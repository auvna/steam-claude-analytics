import httpx
import os
from dotenv import load_dotenv

load_dotenv()

STEAM_KEY = os.getenv("STEAM_API_KEY")
BASE = "https://api.steampowered.com"

async def get_owned_games(steam_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/IPlayerService/GetOwnedGames/v1/", params={
            "key": STEAM_KEY,
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json"
        })
        data = r.json()
        return data.get("response", {}).get("games", [])

async def get_recent_games(steam_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/IPlayerService/GetRecentlyPlayedGames/v1/", params={
            "key": STEAM_KEY,
            "steamid": steam_id,
            "format": "json"
        })
        data = r.json()
        return data.get("response", {}).get("games", [])

async def get_reviews(app_id: int):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"https://store.steampowered.com/appreviews/{app_id}", params={
            "json": 1,
            "num_per_page": 30,
            "language": "english"
        })
        data = r.json()
        reviews = data.get("reviews", [])

        if not reviews:
            r = await client.get(f"https://store.steampowered.com/appreviews/{app_id}", params={
                "json": 1,
                "num_per_page": 30,
                "language": "all"
            })
            data = r.json()
            reviews = data.get("reviews", [])

        return reviews

async def get_achievements(steam_id: str, app_id: int):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/ISteamUserStats/GetPlayerAchievements/v1/", params={
            "key": STEAM_KEY,
            "steamid": steam_id,
            "appid": app_id,
            "format": "json"
        })
        data = r.json()
        return data.get("playerstats", {})

async def get_achievement_schema(app_id: int):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/ISteamUserStats/GetSchemaForGame/v2/", params={
            "key": STEAM_KEY,
            "appid": app_id,
            "format": "json"
        })
        data = r.json()
        achievements = data.get("game", {}).get("availableGameStats", {}).get("achievements", [])
        return {a["name"]: a["displayName"] for a in achievements}

async def get_player_summary(steam_id: str):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/ISteamUser/GetPlayerSummaries/v2/", params={
            "key": STEAM_KEY,
            "steamids": steam_id,
            "format": "json"
        })
        data = r.json()
        players = data.get("response", {}).get("players", [])
        return players[0] if players else None