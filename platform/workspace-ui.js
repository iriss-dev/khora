(() => {
  'use strict';
  const nodes = [...document.querySelectorAll('[data-en]')];
  nodes.forEach((node) => {
    node.dataset.es = node.textContent;
  });
  function saved(key, fallback) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }
  let language =
    (new URLSearchParams(location.search).get('lang') || saved('khora-language', 'es')) === 'en'
      ? 'en'
      : 'es';
  let theme = saved('khora-theme', 'dark');
  function setLanguage(next) {
    language = next;
    document.documentElement.lang = next;
    nodes.forEach((node) => {
      node.textContent = node.dataset[next];
    });
    document
      .querySelectorAll('[data-language]')
      .forEach((button) =>
        button.setAttribute('aria-pressed', String(button.dataset.language === next)),
      );
    try {
      localStorage.setItem('khora-language', next);
    } catch {}
    const url = new URL(location.href);
    url.searchParams.set('lang', next);
    history.replaceState(null, '', url);
    document.dispatchEvent(new CustomEvent('khora:language', { detail: next }));
  }
  document
    .querySelectorAll('[data-language]')
    .forEach((button) =>
      button.addEventListener('click', () => setLanguage(button.dataset.language)),
    );
  window.KhoraUI = { t: (es, en) => (language === 'es' ? es : en), language: () => language };
  document.documentElement.dataset.theme = theme === 'light' ? 'light' : 'dark';
  setLanguage(language);
})();
