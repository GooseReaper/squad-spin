# 🎡 Squad Spin

Load your Steam friends, select who's playing tonight, pick a vibe (Chill Nights, Weeknights,
Drunk Nights, Competitive, Friendship Ruiners, or your own wheels) and spin for a game or a friend.

## What you need
- A Steam Web API key: https://steamcommunity.com/dev/apikey (any domain name works for the form)
- Your Steam profile's **Friends List** set to Public (or add friends one by one by friend code)
- Friends' **Game details** set to Public for the "who owns what" filters

## Put it online (Vercel, free)
1. Push this folder to a GitHub repo.
2. On https://vercel.com → Add New → Project → import the repo (no build settings needed).
3. Deploy. Each visitor pastes their own Steam API key at the top of the page.

The key is held in the page's memory only and sent to `api/steam.js` with each request.
Nothing is saved: closing or reloading the page clears the key, friends and wheels.

## Run it on your Mac
```
python3 dev_server.py
```
Then open http://localhost:8787 and paste your Steam API key at the top. Without a key you can still click "Try a demo squad".

## Run it on Windows
1. Install Python from https://www.python.org/downloads/ (tick "Add python.exe to PATH").
2. In the project folder, open PowerShell and run:
```
python dev_server.py
```
Then open http://localhost:8787 and paste your Steam API key at the top of the page.

## Games in common
The "Games in common" tab compares the libraries of everyone selected and lists what you all own
(or what all but one of you own), most played first. "Add" puts a game on the current wheel.

## What you can type
Friend code (e.g. `12345678`), SteamID64 (`7656…`), `steamcommunity.com/profiles/…` or `/id/…` URLs, or a custom URL name.
