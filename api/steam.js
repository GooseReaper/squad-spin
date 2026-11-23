// Vercel serverless function: proxies the Steam Web API so the browser isn't blocked by CORS.
// The Steam API key comes from the page (X-Steam-Key header) and is never stored.
// GET /api/steam?action=vanity|friends|summaries|owned&...
const BASE = 'https://api.steampowered.com';
const ID = /^7656\d{13}$/;

async function steam(key, path, params) {
  const url = new URL(BASE + path);
  for (const [k, v] of Object.entries({ ...params, key, format: 'json' })) {
    url.searchParams.set(k, v);
  }
  return fetch(url);
}

module.exports = async (req, res) => {
  const send = (status, body, cache = 0) => {
    res.statusCode = status;
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Cache-Control', 'no-store');
    res.end(JSON.stringify(body));
  };

  const key = String(req.headers['x-steam-key'] || '').trim() || process.env.STEAM_API_KEY || '';
  if (!key) return send(503, { error: 'Enter your Steam API key at the top of the page first.', code: 'nokey' });
  if (!/^[A-Za-z0-9]{32}$/.test(key)) {
    return send(400, { error: "That doesn't look like a Steam API key (it should be 32 letters and numbers).", code: 'badkey' });
  }
  const badKey = () => send(403, { error: 'Steam rejected that API key. Check it and try again.', code: 'badkey' });
  const q = req.query || Object.fromEntries(new URL(req.url, 'http://x').searchParams);

  try {
    switch (q.action) {
      case 'vanity': {
        const name = String(q.vanityurl || '');
        if (!/^[\w-]{2,32}$/.test(name)) return send(400, { error: 'Invalid custom URL name.' });
        const r = await steam(key, '/ISteamUser/ResolveVanityURL/v1/', { vanityurl: name });
        if (r.status === 401 || r.status === 403) return badKey();
        const j = await r.json();
        if (j.response?.success === 1) return send(200, { steamid: j.response.steamid }, 3600);
        return send(404, { error: `No Steam profile found for "${name}".` });
      }
      case 'friends': {
        if (!ID.test(q.steamid || '')) return send(400, { error: 'Invalid Steam ID.' });
        const r = await steam(key, '/ISteamUser/GetFriendList/v1/', { steamid: q.steamid, relationship: 'friend' });
        if (r.status === 401 || r.status === 403) {
          return send(403, { error: 'That friends list is private. Set Friends List to Public in Steam privacy settings, or add friends by code.', code: 'private' });
        }
        if (!r.ok) return send(502, { error: `Steam returned ${r.status}.` });
        const j = await r.json();
        return send(200, { friends: (j.friendslist?.friends || []).map(f => f.steamid) }, 60);
      }
      case 'summaries': {
        const ids = String(q.steamids || '').split(',').filter(id => ID.test(id)).slice(0, 100);
        if (!ids.length) return send(400, { error: 'No valid Steam IDs.' });
        const r = await steam(key, '/ISteamUser/GetPlayerSummaries/v2/', { steamids: ids.join(',') });
        if (r.status === 401 || r.status === 403) return badKey();
        if (!r.ok) return send(502, { error: `Steam returned ${r.status}.` });
        const j = await r.json();
        const players = (j.response?.players || []).map(p => ({
          steamid: p.steamid,
          name: p.personaname,
          avatar: p.avatarmedium,
          state: p.personastate || 0,
          game: p.gameextrainfo || null,
          url: p.profileurl,
        }));
        return send(200, { players }, 60);
      }
      case 'owned': {
        if (!ID.test(q.steamid || '')) return send(400, { error: 'Invalid Steam ID.' });
        const r = await steam(key, '/IPlayerService/GetOwnedGames/v1/', {
          steamid: q.steamid, include_appinfo: 1, include_played_free_games: 1,
        });
        if (!r.ok) return send(200, { private: true }, 300);
        const j = await r.json();
        const games = j.response?.games;
        if (!games) return send(200, { private: true }, 300);
        return send(200, {
          private: false,
          games: games.map(g => ({ appid: g.appid, name: g.name, minutes: g.playtime_forever || 0 })),
        }, 300);
      }
      default:
        return send(400, { error: 'Unknown action.' });
    }
  } catch (e) {
    return send(502, { error: 'Could not reach Steam. Try again in a moment.' });
  }
};
