import httpx

BASE = "https://steamspy.com/api.php"

async def get_top_games_by_players() -> list:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(BASE, params={"request": "top100in2weeks"})
            data = r.json()
            games = []
            for appid, info in list(data.items())[:12]:
                games.append({
                    "appid": appid,
                    "name": info.get("name", "Unknown"),
                    "players_2weeks": info.get("players_2weeks", 0),
                    "average_forever": info.get("average_forever", 0),
                })
            return games
        except Exception:
            return []

async def get_top_games_by_owners() -> list:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(BASE, params={"request": "top100forever"})
            data = r.json()
            games = []
            for appid, info in list(data.items())[:6]:
                games.append({
                    "appid": appid,
                    "name": info.get("name", "Unknown"),
                    "owners": info.get("owners", "0"),
                    "average_forever": info.get("average_forever", 0),
                })
            return games
        except Exception:
            return []

async def get_hidden_gems() -> list:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(BASE, params={"request": "top100in2weeks"})
            data = r.json()
            games = []
            for appid, info in data.items():
                owners_str = info.get("owners", "0 .. 0")
                try:
                    max_owners = int(owners_str.split(" .. ")[1].replace(",", "").replace(".", "").strip())
                except Exception:
                    max_owners = 999999999
                positive = info.get("positive", 0)
                negative = info.get("negative", 0)
                total_reviews = positive + negative
                if total_reviews < 100:
                    continue
                ratio = positive / total_reviews if total_reviews > 0 else 0
                if ratio >= 0.90 and max_owners < 2000000:
                    games.append({
                        "appid": appid,
                        "name": info.get("name", "Unknown"),
                        "owners": info.get("owners", ""),
                        "positive": positive,
                        "negative": negative,
                        "ratio": round(ratio * 100, 1)
                    })
            games = sorted(games, key=lambda g: g["ratio"], reverse=True)[:6]
            return games
        except Exception:
            return []