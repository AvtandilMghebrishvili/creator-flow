"""Same-device Studio UI and narrowly scoped companion endpoints."""
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs


def route(handler, bridge):
    studio = getattr(bridge, 'studio', None)
    if studio is None:
        return False
    path = urlsplit(handler.path).path
    origin = f'http://127.0.0.1:{handler.server.server_port}'
    if path == '/auth/callback' and handler.command == 'GET':
        if handler.headers.get('Host') != origin.removeprefix('http://'):
            handler.reply(403, {'error': 'Invalid callback host.'}); return True
        try:
            raw = parse_qs(urlsplit(handler.path).query, max_num_fields=12)
            if any(len(v) != 1 for v in raw.values()):
                raise ValueError('Duplicate callback fields.')
            result = studio.ai.finish({k: v[0] for k, v in raw.items()})
            message = 'ChatGPT connected. Return to Creator Flow and refresh.' if result['planEnabled'] else 'Signed in, but ChatGPT plan usage was not granted. Enable it before generating.'
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else 'Sign-in could not be validated. Return to Creator Flow and retry sign-in.'
        # Never echo codes, tokens or callback URLs.
        handler.reply(200, {'message': message}); return True
    if path.startswith('/studio/') and handler.command == 'GET':
        if handler.headers.get('Host') != origin.removeprefix('http://'):
            handler.reply(403, {'error': 'Invalid host.'}); return True
        # Cross-site embeds must not obtain a pairing token. Top-level navigation is fine.
        if handler.headers.get('Sec-Fetch-Site') == 'cross-site' and handler.headers.get('Sec-Fetch-Mode') != 'navigate':
            handler.reply(403, {'error': 'Open Studio directly.'}); return True
        name = path.removeprefix('/studio/') or 'index.html'
        if name not in ('index.html', 'studio.js', 'studio.css'):
            handler.reply(404, {'error': 'Not found.'}); return True
        content = (Path(__file__).parent / 'studio_ui' / name).read_bytes()
        if name == 'index.html':
            content = content.replace(b'__LOCAL_PAIRING_TOKEN__', bridge.token.encode())
        handler.send_response(200)
        handler.send_header('Content-Type', {'index.html': 'text/html; charset=utf-8', 'studio.js': 'text/javascript; charset=utf-8', 'studio.css': 'text/css; charset=utf-8'}[name])
        handler.send_header('Content-Length', str(len(content)))
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.send_header('X-Frame-Options', 'DENY')
        handler.send_header('Referrer-Policy', 'no-referrer')
        handler.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob: data:; media-src blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        handler.end_headers(); handler.wfile.write(content); return True
    if path != '/v1/studio':
        return False
    if not handler.allowed():
        return True
    try:
        if handler.command == 'GET':
            handler.reply(200, studio.snapshot())
        elif handler.command == 'POST':
            size = int(handler.headers.get('Content-Length', '0'))
            if not 0 < size <= 2_000_000 or handler.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Expected a JSON request below 2 MB.')
            request = json.loads(handler.rfile.read(size))
            if not isinstance(request, dict):
                raise ValueError('Invalid Studio request.')
            handler.reply(200, studio.dispatch(request, origin))
        else:
            handler.reply(405, {'error': 'Method not allowed.'})
    except (ValueError, KeyError, FileNotFoundError) as exc:
        handler.reply(400, {'error': str(exc)[:2000]})
    except Exception:
        handler.reply(500, {'error': 'Studio could not complete the operation. Check local configuration.'})
    return True
