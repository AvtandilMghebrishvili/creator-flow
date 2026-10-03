(function (root) {
  'use strict';
  const C = root.CreatorFlow;
  const readText = (scope, selectors) => {
    for (const selector of selectors) { const s = scope.querySelector(selector)?.textContent?.trim(); if (s) return s; }
    return '';
  };
  const validThumb = value => { try { const u = new URL(value); return u.protocol === 'https:' && (u.hostname === 'i.ytimg.com' || u.hostname.endsWith('.ytimg.com')) ? u.href : ''; } catch (_) { return ''; } };
  function viewLabel(scope) {
    for (const node of scope.querySelectorAll('#metadata-line span, .yt-content-metadata-view-model__metadata-text, .ytContentMetadataViewModelMetadataText, .view-count, [aria-label*="views"], [aria-label*="ნახვ"]')) {
      for (const raw of [node.getAttribute('aria-label'), node.textContent]) if (raw && C.visibleCount(raw)) return raw;
    }
    return '';
  }
  function extract(doc = document, url = location.href) {
    const identity = C.pageIdentity(url);
    if (!identity) return null;
    const source = {...identity, title: '', description: '', channelName: '', channelUrl: '', views: null, videos: [], thumbnail: '', tags: null};
    if (identity.kind === 'video') {
      const scope = identity.format === 'short' ? doc.querySelector('ytd-reel-video-renderer[is-active]') : doc.querySelector('ytd-watch-flexy');
      if (!scope) return {...source, loading: true};
      const pageId = scope.getAttribute('video-id');
      if (pageId && pageId !== identity.id) return {...source, loading: true};
      source.title = C.text(readText(scope, ['h1.ytd-watch-metadata yt-formatted-string', '#title h1', 'h1', '#video-title', 'h2']), 500);
      source.description = C.text(readText(scope, ['#description-inline-expander #attributed-snippet-text', '#description-inline-expander .yt-core-attributed-string', '#description #description-text', '#description']), 10000);
      // The owner avatar is an empty link before the channel-name link on watch pages.
      const owner = scope.querySelector('ytd-video-owner-renderer ytd-channel-name a, #owner ytd-channel-name a, a.yt-reel-channel-bar-view-model__channel-name')
        || [...scope.querySelectorAll('#owner a[href^="/@"], #owner a[href^="/channel/"]')].find(a => a.textContent.trim());
      source.channelName = C.text(owner?.textContent, 200);
      source.channelUrl = C.pageIdentity(owner?.href)?.url || '';
      const ownMetadata = scope.querySelector('ytd-watch-metadata, #info-container, #info');
      source.views = C.visibleCount(ownMetadata ? viewLabel(ownMetadata) : '')?.value ?? null;
      source.thumbnail = `https://i.ytimg.com/vi/${identity.id}/hqdefault.jpg`;
    } else {
      source.channelUrl = identity.url;
      source.channelName = C.text(readText(doc, ['ytd-page-header-renderer h1', 'yt-page-header-renderer h1', '#channel-name #text', 'h1']), 200);
      source.title = source.channelName;
      const seen = new Set();
      const cards = doc.querySelectorAll('ytd-rich-item-renderer, ytd-grid-video-renderer, ytd-video-renderer, ytd-reel-item-renderer, yt-lockup-view-model');
      for (const card of cards) {
        const a = card.querySelector('a#video-title-link, a#video-title, a[href^="/watch?v="], a[href^="/shorts/"]');
        const id = C.pageIdentity(a?.href);
        if (!id || id.kind !== 'video' || seen.has(id.id)) continue;
        seen.add(id.id);
        const title = C.text(a.getAttribute('title') || readText(card, ['#video-title', 'h3', 'h4']) || a.textContent, 500);
        if (!title) continue;
        const raw = viewLabel(card);
        source.videos.push({id: id.id, title, format: id.format, views: C.visibleCount(raw)?.value ?? null, viewsApproximate: C.visibleCount(raw)?.approximate ?? null, viewsLabel: C.text(raw, 100)});
        if (source.videos.length >= 200) break;
      }
    }
    source.thumbnail = validThumb(source.thumbnail);
    return source;
  }
  root.CreatorFlowExtract = {extract, validThumb};
})(globalThis);
