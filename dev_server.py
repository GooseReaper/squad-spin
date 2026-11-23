#!/usr/bin/env python3
"""Local dev server for Squad Spin. Serves the site and mirrors api/steam.js at /api/steam.

    STEAM_API_KEY=yourkey python3 dev_server.py      (or put STEAM_API_KEY=... in a .env file)
    then open http://localhost:8787
"""
import json, os, re, urllib.error, urllib.parse, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
ID = re.compile(r"^7656\d{13}$")


def load_env():
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path):
            k, _, v = line.strip().partition("=")
            if k and not k.startswith("#") and v:
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


KEY = re.compile(r"^[A-Za-z0-9]{32}$")


def steam(key, path, **params):
    params.update(key=key, format="json")
    url = "https://api.steampowered.com" + path + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, {}


def handle(q, key):
    key = (key or "").strip() or os.environ.get("STEAM_API_KEY", "")
    if not key:
        return 503, {"error": "Enter your Steam API key at the top of the page first.", "code": "nokey"}
    if not KEY.match(key):
        return 400, {"error": "That doesn't look like a Steam API key (it should be 32 letters and numbers).", "code": "badkey"}
    action = q.get("action", "")
    if action == "vanity":
        name = q.get("vanityurl", "")
        if not re.match(r"^[\w-]{2,32}$", name):
            return 400, {"error": "Invalid custom URL name."}
        status, j = steam(key, "/ISteamUser/ResolveVanityURL/v1/", vanityurl=name)
        if status in (401, 403):
            return 403, {"error": "Steam rejected that API key. Check it and try again.", "code": "badkey"}
        r = j.get("response", {})
        if r.get("success") == 1:
            return 200, {"steamid": r["steamid"]}
        return 404, {"error": f'No Steam profile found for "{name}".'}
    if action == "friends":
        sid = q.get("steamid", "")
        if not ID.match(sid):
            return 400, {"error": "Invalid Steam ID."}
        status, j = steam(key, "/ISteamUser/GetFriendList/v1/", steamid=sid, relationship="friend")
        if status in (401, 403):
            return 403, {"error": "That friends list is private. Set Friends List to Public in Steam privacy settings, or add friends by code.", "code": "private"}
        if status != 200:
            return 502, {"error": f"Steam returned {status}."}
        return 200, {"friends": [f["steamid"] for f in j.get("friendslist", {}).get("friends", [])]}
    if action == "summaries":
        ids = [i for i in q.get("steamids", "").split(",") if ID.match(i)][:100]
        if not ids:
            return 400, {"error": "No valid Steam IDs."}
        status, j = steam(key, "/ISteamUser/GetPlayerSummaries/v2/", steamids=",".join(ids))
        if status in (401, 403):
            return 403, {"error": "Steam rejected that API key. Check it and try again.", "code": "badkey"}
        if status != 200:
            return 502, {"error": f"Steam returned {status}."}
        return 200, {"players": [{
            "steamid": p["steamid"], "name": p.get("personaname"), "avatar": p.get("avatarmedium"),
            "state": p.get("personastate", 0), "game": p.get("gameextrainfo"), "url": p.get("profileurl"),
        } for p in j.get("response", {}).get("players", [])]}
    if action == "owned":
        sid = q.get("steamid", "")
        if not ID.match(sid):
            return 400, {"error": "Invalid Steam ID."}
        status, j = steam(key, "/IPlayerService/GetOwnedGames/v1/", steamid=sid, include_appinfo=1, include_played_free_games=1)
        games = j.get("response", {}).get("games") if status == 200 else None
        if not games:
            return 200, {"private": True}
        return 200, {"private": False, "games": [
            {"appid": g["appid"], "name": g.get("name", ""), "minutes": g.get("playtime_forever", 0)} for g in games]}
    return 400, {"error": "Unknown action."}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/steam":
            q = dict(urllib.parse.parse_qsl(url.query))
            try:
                status, body = handle(q, self.headers.get("X-Steam-Key"))
            except Exception:
                status, body = 502, {"error": "Could not reach Steam. Try again in a moment."}
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if url.path.endswith(".py") or "/.env" in url.path or url.path.startswith("/api/"):
            return self.send_error(404)
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # always serve the latest page
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the key out of logs
        print(re.sub(r"key=[^&\s]+", "key=***", fmt % args))


if __name__ == "__main__":
    load_env()
    port = int(os.environ.get("PORT", 8787))
    print(f"Squad Spin running at http://localhost:{port}  (enter your Steam API key on the page)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
