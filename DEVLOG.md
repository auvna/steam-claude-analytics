The Idea

I wanted to build something that combined two things I was already interested in — gaming and AI. Steam has a rich public API with years of player data, and Claude is capable of generating genuinely insightful analysis rather than just summarizing numbers. The question was whether I could connect them in a way that felt useful rather than just a tech demo.

SteamDB is a popular third-party site that surfaces data from Steam's database — things like player counts, price history, game metadata, and store statistics. It's an incredibly useful tool for people who want to dig into the numbers behind Steam. But it's built for analytics, not narrative. It tells you what the data is, not what it means about you as a player.

I wanted to build something different — something that leans into narrative rather than pure data. Instead of showing you a table of statistics, I wanted the app to tell you something about yourself as a gamer. What kind of player are you? What does your library say about your taste? What should you actually play tonight?

The goal was simple: enter your Steam ID and get back something more interesting than what Steam itself shows you. Not just "you have 141 games and 10,000 hours" but "here's what kind of gamer you actually are, here's what your achievement progress says about you, and here's what you should play tonight based on your mood."

The project ended up growing into two distinct things — a personalized analyzer for your own library, and a public landing page showing live Steam stats with AI-generated commentary. Both came from the same core idea: the most interesting thing about your Steam library isn't the numbers — it's what those numbers say about you.

Architecture Overview

The app has three main layers that work together:

Backend — FastAPI (Python)
The core of the app is a REST API built with FastAPI. It handles all the data fetching, caching, and AI calls. FastAPI was the right choice here because it's async-native — when you're making parallel HTTP requests to four different external APIs simultaneously, blocking I/O would make the app unusably slow. Every endpoint that calls an external service uses async/await and asyncio.gather to run requests concurrently rather than sequentially.

Four External APIs

Steam Web API — fetches owned games, recent playtime, achievements, player summaries and reviews
Anthropic Claude API — generates all the AI analysis, from personality profiles to backlog estimates to review summaries
RAWG — a game database API used to fetch genre tags and determine whether unplayed games are single player or multiplayer
SteamSpy — a free public API that provides global Steam statistics like trending games and ownership numbers for the landing page

Frontend — Vanilla HTML/CSS/JavaScript
No framework. The entire frontend is a single index.html for the analyzer and a landing.html for the public page. Chart.js handles the genre breakdown visualizations. Everything else is plain DOM manipulation and fetch calls to the backend.

Caching — SQLite via SQLModel
Every API response that involves Claude is cached in a local SQLite database for 4 hours. Without caching, every page load would cost money and take 30-60 seconds. With caching, repeat visits are near instant and free.

Key Technical Decisions

Why FastAPI over Flask or Django?
Flask was the obvious choice for a small project like this, but FastAPI's async support was a dealbreaker. The analyzer makes 7 parallel API calls when you hit Analyze — dashboard, achievements, library, genres, backlog, personality, and profile all fire simultaneously. In Flask that would mean 7 sequential requests, each waiting for the previous one to finish. In FastAPI with asyncio.gather they all run at the same time, cutting the total wait time dramatically.

Why Claude Sonnet specifically?
Claude Sonnet sits in the sweet spot between quality and cost for this use case. The app makes up to 6 Claude calls per analysis — recommendations, insights, achievements, backlog, personality, and review analysis. Using Opus would make each analysis expensive enough that the app wouldn't be practical to run. Haiku would be fast and cheap but the output quality for nuanced analysis like gaming personality profiles isn't quite there. Sonnet hits the right balance.

Why SQLite over a proper database?
This is a single-server app deployed on Railway. SQLite is fast, requires zero configuration, and lives right next to the application code. There's no need for PostgreSQL or MySQL at this scale — the caching layer just needs to store JSON blobs with a timestamp, and SQLite handles that perfectly. SQLModel provides a clean ORM layer on top so the cache models look and behave like proper database models if the app ever needs to migrate.

Why vanilla JS over React?
The frontend state is simple enough that React would have added complexity without adding value. There's no component tree to manage, no shared state between unrelated parts of the UI, and no need for a build step. Plain DOM manipulation and fetch calls are easier to reason about and faster to ship. The one area where a framework might have helped is the tab switching and card show/hide logic, but even that ended up being manageable with a handful of functions.

Challenges and How I Solved Them

Claude ignoring prompt instructions
The biggest ongoing challenge was getting Claude to return consistently formatted, concise output. Claude naturally writes as much as it can — ask it for a personality profile and it'll write three paragraphs when you wanted three sentences. The solution was two-pronged: explicit format instructions with examples in the prompt, and hard max_tokens limits that physically prevent it from writing more than needed. Even then, some endpoints like the gaming personality function needed the token limit dropped to 200 before the responses were tight enough.

Slow first load times
The first analysis of any Steam ID took 60+ seconds because the genre detection and backlog filtering were making sequential HTTP requests to RAWG — up to 50 individual API calls one after the other. The fix was switching to asyncio.gather for both endpoints, running all the RAWG calls concurrently instead of sequentially. This cut the genre and backlog load times from 30-60 seconds each down to 5-10 seconds. Combined with the 4-hour cache, subsequent loads are near instant.

Steam API limitations
Steam's public API has some frustrating gaps. Family shared games don't appear in the owned games endpoint at all — the API only returns games tied to your own license. Animated profile avatars aren't accessible through the API either, only static JPGs. And some games return empty achievement data even on public profiles if the user has their game details set to private separately from their main profile visibility. Most of these can't be fixed — they're Steam API limitations — so the approach was to handle them gracefully with clear messaging rather than pretending the data exists.

Prompt engineering for structured output
Several endpoints need Claude to return data in a specific format that JavaScript can parse — the personality profile needs to be split into four named sections, the game recommendations need to be a JSON array, the landing page commentary needs three distinct paragraphs. The solution was a combination of explicit format instructions, section headers that the parser looks for, and JSON output for endpoints where the data needs to be filtered programmatically before display. The recommendation endpoint for example asks Claude for 8 suggestions, returns them as JSON, filters out any games the user already owns using string matching, and then displays the top 3 — meaning Claude's occasional mistakes get caught by the code rather than shown to the user.

What I Learned

Async Python is genuinely transformative for API-heavy apps
Coming from synchronous Python, the difference asyncio makes to a project like this is hard to overstate. The analyzer makes dozens of external HTTP requests per analysis. Without async, that's a sequential chain of waiting. With async, it's parallel. The mental model takes some getting used to — understanding when to use await, when to use asyncio.gather, and when to use asyncio.to_thread for blocking code like the Claude API calls — but once it clicks it changes how you think about backend architecture entirely.

Prompt engineering is a real skill
I went into this project thinking prompt engineering was mostly just asking nicely. It's not. Getting Claude to return consistent, concise, correctly formatted output across six different use cases required careful iteration on every prompt. The difference between a prompt that returns a usable result 95% of the time and one that returns a usable result 70% of the time comes down to specificity — naming the exact format, giving examples of what you don't want, setting explicit constraints, and adding fallback parsing for when the output isn't quite right anyway.

Caching is essential when you're paying per token
Without the SQLite caching layer, running the analyzer would cost meaningful money on every request. With it, the cost per user is effectively zero after the first visit. Building the cache early in the project rather than as an afterthought made every subsequent decision easier — I never had to worry about API costs during development because repeat runs hit the cache.

API limitations are part of the design
Every external API has gaps, rate limits, and undocumented behaviors. Steam doesn't expose family shared games. RAWG times out on some requests. SteamSpy returns zero for player counts in some environments. Learning to design around these limitations rather than against them — handling them gracefully, showing clear messages, building fallbacks — is what separates a project that works from a project that works most of the time.

What I'd Do Differently

Start with the caching layer
I added caching after most of the endpoints were built, which meant retrofitting the cache models onto existing code. Starting with caching as a first-class concern from day one would have made the architecture cleaner and saved time.

Tighter prompt design from the start
I spent a lot of time going back and fixing prompts that were too verbose or inconsistently formatted. Having a clear prompt template and output format defined before writing any parsing code would have saved significant iteration time.

Use a proper frontend framework for the analyzer
The vanilla JS approach worked but the show/hide state management for 15+ cards and 4 tabs got messy. Something lightweight like Alpine.js or even just a cleaner vanilla JS architecture with proper state management would have made the frontend easier to maintain as features were added.

Plan the tab structure earlier
The Overview and Stats tabs went through multiple restructures as I added features and realized the content didn't fit where I'd put it. Thinking through the information architecture before building would have saved a lot of moving cards between tabs.

The Result

The finished app has two parts. The landing page shows live Steam data — trending games, hidden gems, genre pulse, and AI-generated editorial commentary that updates every 4 hours. The analyzer takes any public Steam ID and generates a full profile: gamer archetype, stat boxes, most played showcase, achievement tracking with a circular progress ring, genre breakdown charts, backlog analysis filtered to single-player games, review analysis for any game in the library, and a mood-based quiz that picks something from your unplayed backlog based on how you're feeling right now.

It's deployed on Railway, the code is on GitHub, and the whole thing is built with Python, FastAPI, SQLite, vanilla JavaScript, and Claude AI. No React, no Docker, no microservices — just a clean stack that solves the problem without unnecessary complexity.

The most important thing I learned building it isn't technical. It's that the gap between a data dump and something people actually want to read is entirely about framing. The same Steam API data that SteamDB shows as a table becomes genuinely interesting when Claude wraps it in narrative. That's the whole idea, and I think it works.