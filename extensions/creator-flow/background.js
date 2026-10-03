'use strict';
importScripts('core.js');
chrome.storage.local.setAccessLevel({accessLevel: 'TRUSTED_CONTEXTS'}).catch(() => {});
const ownPage = sender => sender.url?.startsWith(chrome.runtime.getURL(''));
const youtubePage = sender => { try { const u = new URL(sender.url); return u.protocol === 'https:' && ['www.youtube.com', 'youtube.com'].includes(u.hostname); } catch (_) { return false; } };
function connection(value) {
  const url = new URL(value?.url || 'http://127.0.0.1:8772');
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || url.username || url.password || !url.port || url.pathname !== '/' || url.search || url.hash) throw Error('Use http://127.0.0.1:PORT only.');
  const token = String(value.token || '').trim();
  if (!/^[a-zA-Z0-9_-]{32,100}$/.test(token)) throw Error('Invalid pairing token.');
  return {url: url.origin, token};
}
async function bridge(path, payload) {
  const state = await chrome.storage.local.get('connection');
  if (!state.connection) throw Error('Connect the local Creator Flow bridge in Settings first.');
  const config = connection(state.connection);
  if (!await chrome.permissions.contains({origins: ['http://127.0.0.1/*']})) throw Error('Local connection permission is missing. Reconnect in Settings.');
  const response = await fetch(config.url + path, {method: payload ? 'POST' : 'GET', headers: {'Authorization': 'Bearer ' + config.token, ...(payload ? {'Content-Type': 'application/json'} : {})}, body: payload ? JSON.stringify(payload) : undefined, signal: AbortSignal.timeout(12000), redirect: 'error', credentials: 'omit'});
  const result = await response.json();
  if (!response.ok) throw Error(result.error || `Bridge error: ${response.status}`);
  return result;
}
async function handle(message, sender) {
  if (sender.id !== chrome.runtime.id || !(ownPage(sender) || youtubePage(sender))) throw Error('Unsupported caller.');
  const state = await chrome.storage.local.get(['language', 'datasets', 'reports', 'connection', 'pending']);
  switch (message?.type) {
    case 'STATE': return {language: state.language || 'ka', datasets: state.datasets || {}, reports: state.reports || {}, pending: state.pending || {}, connected: !!state.connection, extensionId: chrome.runtime.id, ...(ownPage(sender) ? {connection: state.connection || null} : {})};
    case 'LANGUAGE':
      if (!['ka', 'en'].includes(message.language)) throw Error('Unsupported language.');
      await chrome.storage.local.set({language: message.language}); return {};
    case 'STUDIO_OPEN': {
      const saved = state.connection;
      const url = saved ? connection(saved).url : 'http://127.0.0.1:8772';
      await chrome.tabs.create({url: url + '/studio/'}); return {};
    }
    case 'STUDIO_PROJECTS': {
      const studio = await bridge('/v1/studio');
      return Object.values(studio.projects).map(p => ({id: p.id, name: p.name, revision: p.revision}));
    }
    case 'STUDIO_ATTACH': {
      if (!/^[a-f0-9]{32}$/.test(message.project) || !Number.isInteger(message.revision)) throw Error('Choose a Studio project first.');
      if (!message.context || JSON.stringify(message.context).length > 220000) throw Error('Context is missing or too large.');
      await bridge('/v1/studio', {action: 'page_context', project: message.project, revision: message.revision, context: {...message.context, contextKey: message.key, includeThumbnail: false}});
      await chrome.tabs.create({url: connection(state.connection).url + '/studio/#project=' + message.project});
      return {};
    }
    case 'SETTINGS': await chrome.runtime.openOptionsPage(); return {};
    case 'CONNECT':
      if (!ownPage(sender)) throw Error('Use the extension Settings page.');
      await chrome.storage.local.set({connection: connection(message.connection)}); return bridge('/v1/health');
    case 'DISCONNECT':
      if (!ownPage(sender)) throw Error('Use Settings.');
      await chrome.storage.local.remove(['connection', 'pending']); return {};
    case 'IMPORT_DATASET': {
      if (!ownPage(sender)) throw Error('Use Settings.');
      const dataset = CreatorFlow.importStudio(message.csv, message.meta);
      const datasets = state.datasets || {};
      if (!datasets[dataset.channel] && Object.keys(datasets).length >= 8) throw Error('Remove an older imported channel first (maximum 8).');
      datasets[dataset.channel] = dataset;
      if (new TextEncoder().encode(JSON.stringify(datasets)).length > 5_000_000) throw Error('Imported data exceeds the 5 MB limit.');
      await chrome.storage.local.set({datasets}); return {count: dataset.videos.length};
    }
    case 'CLEAR_DATA':
      if (!ownPage(sender)) throw Error('Use Settings.');
      await chrome.storage.local.remove(['datasets', 'reports', 'pending']); return {};
    case 'HEALTH': return bridge('/v1/health');
    case 'START_AI': {
      if (!message.context || JSON.stringify(message.context).length > 220000) throw Error('Context is missing or too large.');
      const result = await bridge('/v1/jobs', {context: message.context, contextKey: message.key, requestId: message.requestId});
      const pending = state.pending || {}; pending[message.key] = result.id;
      await chrome.storage.local.set({pending}); return result;
    }
    case 'POLL_AI': {
      if (!/^[a-f0-9]{32}$/.test(message.id)) throw Error('Invalid job ID.');
      const result = await bridge('/v1/jobs/' + message.id);
      if (result.status === 'completed') {
        CreatorFlow.validateReport(result.report, message.key);
        const reports = state.reports || {}; reports[message.key] = result.report;
        const keys = Object.keys(reports); while (keys.length > 20) delete reports[keys.shift()];
        const pending = state.pending || {}; delete pending[message.key];
        await chrome.storage.local.set({reports, pending});
      }
      if (result.status === 'failed') {const pending = state.pending || {}; delete pending[message.key]; await chrome.storage.local.set({pending});}
      return result;
    }
    case 'IMPORT_REPORT': {
      const report = CreatorFlow.validateReport(message.report, message.key);
      const reports = state.reports || {}; reports[message.key] = report;
      const keys = Object.keys(reports); while (keys.length > 20) delete reports[keys.shift()];
      await chrome.storage.local.set({reports}); return {};
    }
    default: throw Error('Unknown request.');
  }
}
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  handle(message, sender).then(data => reply({ok: true, data})).catch(error => reply({ok: false, error: error.message}));
  return true;
});
chrome.action.onClicked.addListener(async tab => {
  if (tab.id && youtubePage({url: tab.url})) {
    try { await chrome.tabs.sendMessage(tab.id, {type: 'TOGGLE'}); }
    catch (_) { await chrome.runtime.openOptionsPage(); }
  } else await chrome.tabs.create({url: 'https://www.youtube.com/'});
});
