"""Browser-test-only provider. Never used by the production CLI."""
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from podcut import extension as ex


def fake_advice(context, provider, model):
    return {'summary': 'Synthetic test report: clarify the practical outcome.',
            'findings': [{'title': '<img src=x onerror=alert(1)>', 'detail': 'Escaped text must remain harmless.', 'evidence': 'Fictional browser fixture only.'}],
            'titles': ['AI tools: a practical comparison'], 'description': 'A test description.', 'tags': ['AI', 'tools'],
            'ideas': [{'title': 'A practical AI experiment', 'format': 'Video', 'hook': 'Which workflow saves time?', 'why': 'Matches the supplied fictional topic.', 'evidence': 'Synthetic page title; no trend claim.'}]}


if __name__ == '__main__':
    ex.generate = fake_advice
    bridge = ex.Bridge(sys.argv[1], [sys.argv[2]], 'ollama', 'synthetic-browser-test', studio_enabled=True)
    bridge.studio.dispatch({'action': 'create_project', 'name': 'Synthetic YouTube project'}, '')
    base = ex.handler(bridge)
    class Handler(base):
        def do_POST(self):
            if self.path == '/test-stop' and self.allowed():
                self.reply(200, {'stopping': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                super().do_POST()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}', 'token': bridge.token}), flush=True)
    server.serve_forever()
    server.server_close()
