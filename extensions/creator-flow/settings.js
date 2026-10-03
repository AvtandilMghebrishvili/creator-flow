'use strict';
const $ = id => document.getElementById(id);
async function send(message) { const result = await chrome.runtime.sendMessage(message); if (!result?.ok) throw Error(result?.error || 'Extension unavailable. Reload it.'); return result.data; }
const status = value => $('status').textContent = value;
async function refresh() {
  const state = await send({type: 'STATE'});
  $('extension-id').value = state.extensionId;
  $('command').textContent = `creator-flow extension-serve --workspace "WORKSPACE" --extension-id ${state.extensionId}\n\n# Optional local AI:\n# add --provider ollama --model YOUR_INSTALLED_MODEL\n# Or OpenAI API (separate billing, key in terminal environment):\n# add --provider openai --model YOUR_API_MODEL`;
  $('language').value = state.language;
  $('connection-state').textContent = state.connected ? 'Connection saved. Click Connect to check it.' : 'Local checks ready. AI bridge not connected.';
  if (state.connection) { $('url').value = state.connection.url; $('token').value = state.connection.token; }
  $('datasets').textContent = Object.values(state.datasets).map(x => `${x.channel} · ${x.start} → ${x.end} · ${x.videos.length} videos`).join('\n') || 'No imported reports.';
}
function action(id, work) { $(id).onclick = async () => { $(id).disabled = true; try { await work(); } catch (e) { status(e.message); } finally { $(id).disabled = false; } }; }
action('connect', async () => {
  const allowed = await chrome.permissions.request({origins: ['http://127.0.0.1/*']});
  if (!allowed) throw Error('Local connection permission was not granted.');
  const data = await send({type: 'CONNECT', connection: {url: $('url').value, token: $('token').value}});
  await refresh(); status(`Connected · ${data.provider} · ${data.model || 'No model selected'}\n${data.aiReady ? 'AI configuration is ready; use Send on a YouTube page.' : 'AI is not configured. Local review and CSV analytics work.'}`);
});
action('disconnect', async () => { await send({type: 'DISCONNECT'}); $('token').value = ''; await refresh(); status('Disconnected.'); });
action('import', async () => {
  const file = $('csv').files[0]; if (!file || file.size > 3_000_000) throw Error('Choose a CSV under 3 MB.');
  const identity = CreatorFlow.pageIdentity($('channel').value);
  if (identity?.kind !== 'channel') throw Error('Use a YouTube channel URL, for example https://www.youtube.com/@YourChannel.');
  const result = await send({type: 'IMPORT_DATASET', csv: await file.text(), meta: {channel: identity.url, start: $('start').value, end: $('end').value}});
  await refresh(); status(`Imported ${result.count} video rows. Refresh Creator Flow on the matching YouTube channel/video.`);
});
action('clear', async () => { if (!confirm('Delete locally imported Studio data and AI reports?')) return; await send({type: 'CLEAR_DATA'}); await refresh(); status('Imported data cleared.'); });
$('language').onchange = () => send({type: 'LANGUAGE', language: $('language').value}).then(() => status('Language saved. Refresh the YouTube panel.')).catch(e => status(e.message));
refresh().catch(e => status(e.message));
