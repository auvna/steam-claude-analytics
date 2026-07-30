import anthropic
import json

client = anthropic.Anthropic()

def call_claude(prompt: str, max_tokens: int=2000) -> str:
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content":prompt}]
    )
    return message.content[0].text


def get_recommendation(games: list) -> str:
    top_games = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:20]
    owned_names = [g["name"].lower() for g in games]
    blocklist = ["sekiro"]

    def is_owned(game_name):
        name = game_name.lower()
        for blocked in blocklist:
            if blocked in name:
                return True
        for owned in owned_names:
            if name in owned or owned in name:
                return True
        return False

    result = call_claude(f"""
        A Steam user's top 20 most played games (playtime in minutes):
        {json.dumps(top_games, indent=2)}

        Recommend 8 games they would enjoy that are NOT in their library.
        Do not recommend Sekiro, Dark Souls, Hades, Elden Ring, or any FromSoftware games
        as the user already owns these.
        Return ONLY a JSON array, no other text:
        [{{"name": "Game Name", "reason": "One sentence reason"}}]
    """, max_tokens=500)

    try:
        clean = result.strip().replace('```json', '').replace('```', '')
        recommendations = json.loads(clean)
        filtered = [r for r in recommendations if not is_owned(r["name"])][:3]
        return '\n'.join([f"{i+1}. **{r['name']}** - {r['reason']}" for i, r in enumerate(filtered)])
    except Exception:
        return result


def analyze_reviews(app_name: str, reviews: list) -> str:
    review_texts = [r["review"] for r in reviews[:30]]
    return call_claude(f"""
        Analyze these Steam reviews for {app_name}:
        {json.dumps(review_texts, indent=2)}

        Provide:
        - Overall sentiment (positive/mixed/negative)
        - Top 3 pros players mention
        - Top 3 cons players mention
        - One sentence Verdict
    """)


def generate_insights(games: list, recent: list) -> str:
    total_hours = round(sum(g.get("playtime_forever", 0) for g in games) / 60)
    return call_claude(f"""
        Analyze this Steam player's gaming habits.

        Total hours played across entire library: {total_hours} hours (use this exact number)

        Full library (playtime in minutes):
        {json.dumps(games, indent=2)}

        Recently played:
        {json.dumps(recent, indent=2)}

        Respond in this exact format, keep each section to 1-2 sentences max:

        ## Total Hours Played
        One sentence only. Use exactly {total_hours} hours as the total.

        ## Top 3 Most Played Genres
        **Genre** — one sentence why.
        **Genre** — one sentence why.
        **Genre** — one sentence why.

        ## Most Active Gaming Period
        One sentence only.

        ## 3 Interesting Observations
        - One sentence.
        - One sentence.
        - One sentence.

        No extra commentary. Stick strictly to this format.
    """, max_tokens=400)


def analyze_achievements(achievement_data: list) -> str:
    return call_claude(f"""
        Here is a Steam player's achievement data across their top games:
        {json.dumps(achievement_data, indent=2)}

        For each game provide:
        - How many achievements they have unlocked vs total
        - Which achievements they are closest to unlocking
        - One sentence suggesting what to focus on next

        Format each game clearly with its name as a header.
    """)


def estimate_backlog(unplayed_games: list) -> str:
    return call_claude(f"""
        Here is a list of Steam games this player owns but has never played:
        {json.dumps([g["name"] for g in unplayed_games][:50], indent=2)}

        Focus only on single player games — ignore any games that are primarily
        multiplayer, MMOs, or online-only experiences.

        IMPORTANT: You must completely ignore and never mention any of the following:
        - Multiplayer-only games
        - MMOs or massively multiplayer games
        - Online-only games
        - Battle royale games
        - Co-op only games
        - Any game that has no meaningful single player content

        Only discuss games that have a proper single player campaign or mode.

        Provide:
        - An estimate of how long it would take to complete the single player games combined.
        - Three single player games from this list worth playing first and why.
        - One sentence summary of what kind of backlog this player has.

        Format your response with clear headers.
    """)


def gaming_personality(games: list, recent: list) -> str:
    top_played = sorted(games, key=lambda g: g.get("playtime_forever", 0), reverse=True)[:20]
    return call_claude(f"""
        Analyze this Steam player's gaming habits and give them a fun gaming personality profile.

        Top 20 most played games (playtime in minutes):
        {json.dumps(top_played, indent=2)}

        Recently played:
        {json.dumps(recent, indent=2)}

        Respond in this exact format, keep each section brief:

        ## Gamer Type
        A creative 2-4 word archetype name only. No explanation.

        ## Personality Breakdown
        Two sentences max.

        ## Signature Genre
        One sentence only.

        ## Hidden Trait
        One sentence only.

        No extra commentary. Stick strictly to this format.
    """, max_tokens=200)


def game_match(games: list, time: str, mood: str, company: str, style: str) -> str:
    exclude_keywords = ['test server', 'beta', 'demo', 'trial', 'playtest', 'pts', 'public test', 'mod', 'sdk', 'dedicated server', 'soundtrack', 'dlc']
    unplayed_games = [
        g for g in games
        if g.get("playtime_forever", 0) == 0
        and not any(kw in g.get("name", "").lower() for kw in exclude_keywords)
    ]
    top_games = unplayed_games[:50]
    return call_claude(f"""
        A Steam player wants to know what to play right now based on their mood.

        Their UNPLAYED games (games with zero playtime):
        {json.dumps(top_games, indent=2)}

        Their current mood:
        - Time available: {time}
        - Mood: {mood}
        - Solo or multiplayer: {company}
        - Preference: {style}

        Pick exactly ONE game from the unplayed list that best fits their mood.
        Avoid recommending games that are remasters or sequels of games the player
        likely already knows well — focus on fresh experiences.
        Format your response as:
        **[Game Name]**
        [2-3 sentences explaining why this game fits their current mood perfectly.]

        No intro, no outro. Just the game name in bold and an explanation.
    """, max_tokens=200)


def generate_landing_commentary(trending_games: list, top_games: list, gems: list = []) -> dict:
    trending_names = [g["name"] for g in trending_games[:8]]
    top_names = [g["name"] for g in top_games[:6]]

    result = call_claude(f"""
        You are writing short, personality-driven editorial commentary for a Steam gaming stats page.

        Currently trending games this week (most played):
        {json.dumps(trending_names, indent=2)}

        Most owned games of all time on Steam:
        {json.dumps(top_names, indent=2)}

        Hidden gems (highly rated, under 2M owners):
        {json.dumps([g["name"] for g in gems[:6]], indent=2)}

        Write the following, be concise and give it personality like a gaming journalist:

        ## Weekly Summary
        2-3 sentences summarizing what's happening on Steam this week based on the trending games.

        ## Trending Insight
        One sentence observation about what the trending list says about what gamers are into right now.

        ## All Time Insight
        One sentence about what the all-time list says about Steam's history and player base.

        ## Gems Insight
        One sentence about what makes these hidden gems worth discovering.

        No intros, no outros. Just the four sections with their headers.
    """, max_tokens=300)

    lines = result.split('\n')
    sections = {}
    current = None
    current_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith('## '):
            if current and current_lines:
                sections[current] = ' '.join(current_lines).strip()
            current = line[3:].strip()
            current_lines = []
        elif line and current:
            current_lines.append(line)

    if current and current_lines:
        sections[current] = ' '.join(current_lines).strip()

    return {
        "weekly_summary": sections.get("Weekly Summary", ""),
        "trending_insight": sections.get("Trending Insight", ""),
        "all_time_insight": sections.get("All Time Insight", ""),
        "gems_insight": sections.get("Gems Insight", "")
    }


def generate_game_of_moment(trending_games: list) -> dict:
    top_trending = trending_games[:8]
    result = call_claude(f"""
        Here are the most played games on Steam this week:
        {json.dumps([g["name"] for g in top_trending], indent=2)}

        Pick ONE game from this list that is the most interesting or noteworthy right now.
        Write a short spotlight on it like a gaming journalist would.

        Format exactly as:
        ## Game
        [Game name only, no extra text]

        ## Why Now
        [2-3 sentences on why this game is worth playing or noteworthy right now. Be specific and interesting, not generic.]

        ## Best For
        [One sentence describing who this game is perfect for.]

        No intros, no outros. Just the three sections.
    """, max_tokens=250)

    lines = result.split('\n')
    sections = {}
    current = None
    current_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith('## '):
            if current and current_lines:
                sections[current] = ' '.join(current_lines).strip()
            current = line[3:].strip()
            current_lines = []
        elif line and current:
            current_lines.append(line)

    if current and current_lines:
        sections[current] = ' '.join(current_lines).strip()

    game_name = sections.get("Game", "")
    matched = next((g for g in top_trending if g["name"].lower() == game_name.lower()), None)

    return {
        "name": game_name,
        "appid": matched["appid"] if matched else None,
        "why_now": sections.get("Why Now", ""),
        "best_for": sections.get("Best For", "")
    }