(function () {
  'use strict';

  const input = document.getElementById('lp-search-input');
  const results = document.getElementById('lp-search-results');
  if (!input || !results) return;

  const INDEX_URL = (document.querySelector('meta[name="lp-search-index"]') || {}).content || '/index.json';
  const MAX_RESULTS = 8;

  let index = null;
  let loading = null;
  let activeIdx = -1;

  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (loading) return loading;
    loading = fetch(INDEX_URL, { credentials: 'same-origin' })
      .then(r => r.ok ? r.json() : [])
      .then(j => { index = Array.isArray(j) ? j : []; return index; })
      .catch(err => { console.error('search index load failed', err); index = []; return index; });
    return loading;
  }

  function score(item, terms) {
    const titleAll = (item.title || '').toLowerCase();
    const tagStr = (item.tags || []).join(' ').toLowerCase();
    const hay = (titleAll + ' ' + tagStr + ' ' + (item.summary || '') + ' ' + (item.section || '')).toLowerCase();

    let s = 0;
    for (const t of terms) {
      if (!t) continue;
      if (hay.indexOf(t) === -1) return 0;
      s += 1;
      if (titleAll.indexOf(t) !== -1) s += 6;
      if (tagStr.indexOf(t) !== -1) s += 3;
      if ((item.section || '').toLowerCase().indexOf(t) !== -1) s += 2;
    }
    return s;
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  function highlight(text, terms) {
    let out = escapeHtml(text);
    for (const t of terms) {
      if (!t) continue;
      const re = new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
      out = out.replace(re, '<mark>$1</mark>');
    }
    return out;
  }

  function render(items, terms) {
    if (!items.length) {
      results.innerHTML = '<div class="lp-nav-search-empty">No matches</div>';
      results.hidden = false;
      activeIdx = -1;
      return;
    }
    results.innerHTML = items.slice(0, MAX_RESULTS).map(it => (
      '<a href="' + escapeHtml(it.url) + '">' +
        '<div class="lp-nav-search-result-section">' + escapeHtml(it.section || '') + '</div>' +
        '<div class="lp-nav-search-result-title">' + highlight(it.title || '', terms) + '</div>' +
        (it.summary ? '<div class="lp-nav-search-result-snippet">' + highlight(it.summary, terms) + '</div>' : '') +
      '</a>'
    )).join('');
    results.hidden = false;
    activeIdx = -1;
  }

  function onInput() {
    const q = input.value.trim().toLowerCase();
    if (!q) { results.hidden = true; results.innerHTML = ''; activeIdx = -1; return; }
    loadIndex().then(idx => {
      const terms = q.split(/\s+/).filter(Boolean);
      const ranked = idx
        .map(it => ({ it: it, s: score(it, terms) }))
        .filter(r => r.s > 0)
        .sort((a, b) => b.s - a.s)
        .map(r => r.it);
      render(ranked, terms);
    });
  }

  function setActive(delta) {
    const links = results.querySelectorAll('a');
    if (!links.length) return;
    activeIdx = (activeIdx + delta + links.length) % links.length;
    links.forEach((a, i) => a.classList.toggle('is-active', i === activeIdx));
    const el = links[activeIdx];
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest' });
  }

  input.addEventListener('input', onInput);
  input.addEventListener('focus', () => { if (input.value.trim()) onInput(); });
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(-1); }
    else if (e.key === 'Enter') {
      const links = results.querySelectorAll('a');
      if (activeIdx >= 0 && links[activeIdx]) {
        e.preventDefault();
        window.location.href = links[activeIdx].href;
      }
    } else if (e.key === 'Escape') {
      results.hidden = true;
      input.blur();
    }
  });
  document.addEventListener('click', e => {
    if (!results.contains(e.target) && e.target !== input) {
      results.hidden = true;
    }
  });

  // Keyboard shortcut: '/' focuses the search bar (when not in an input)
  document.addEventListener('keydown', e => {
    if (e.key === '/' && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
      e.preventDefault();
      input.focus();
    }
  });
})();
