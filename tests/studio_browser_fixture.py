"""Isolated Studio browser fixture; no model calls or real account data."""
import json
import sys
from pathlib import Path
from http.server import ThreadingHTTPServer
from podcut.extension import Bridge, handler
from podcut.core import ffmpeg, read, write
from podcut import clips

bridge = Bridge(sys.argv[1], [], studio_enabled=True)
episode = Path(sys.argv[1]) / 'episode'
episode.mkdir()
video = episode / 'synthetic.mp4'
ffmpeg(['-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=25:duration=6',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=6',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-shortest', str(video)])
transcript = episode / 'transcript.json'
write(transcript, {'complete': True, 'clock': 'media seconds', 'segments': [
    {'start': i, 'end': i+2, 'text': f'Synthetic sentence {i}'} for i in (0, 2, 4)]})
review = clips.init(video, transcript, episode / 'review', 1, 1, 6, 'Synthetic test scope')
clips.propose(review)
data = read(review)
data['clips'] = [{'id': 'clip-01', 'start': 0, 'end': 4, 'hook': {'start': 0, 'end': 2, 'mode': 'repeat'}, 'captions': False}]
data['layout'] = 'source'
write(review, data)
server = ThreadingHTTPServer(('127.0.0.1', 0), handler(bridge))
print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}', 'token': bridge.token, 'review': str(review)}), flush=True)
server.serve_forever()
