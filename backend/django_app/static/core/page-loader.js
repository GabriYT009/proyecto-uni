(function () {
  if (window.__pageLoaderInit) return;
  window.__pageLoaderInit = true;

  var STYLE_ID = 'global-page-loader-style';
  var LOADER_ID = 'pageLoader';

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = [
      '#' + LOADER_ID + '{position:fixed;inset:0;z-index:30000;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;',
      'background:radial-gradient(circle at 30% 20%,rgba(230,88,255,.22),transparent 45%),linear-gradient(160deg,rgba(18,8,33,.96),rgba(26,12,44,.98));',
      'opacity:0;visibility:hidden;transition:opacity .28s ease,visibility .28s ease;}',
      '#' + LOADER_ID + '.show{opacity:1;visibility:visible;}',
      '#' + LOADER_ID + ' .loader-ring{width:54px;height:54px;border-radius:50%;border:3px solid rgba(255,194,255,.25);border-top-color:#ee7bff;border-right-color:#9d5cff;animation:plSpin .8s linear infinite;}',
      '#' + LOADER_ID + ' p{margin:0;color:#f4e7ff;font-weight:700;}',
      '@keyframes plSpin{to{transform:rotate(360deg);}}'
    ].join('');
    document.head.appendChild(style);
  }

  function ensureLoader() {
    var loader = document.getElementById(LOADER_ID);
    if (loader) return loader;

    loader = document.createElement('div');
    loader.id = LOADER_ID;
    loader.setAttribute('aria-hidden', 'true');
    loader.innerHTML = '<div class="loader-ring" aria-hidden="true"></div><p>Cargando vista...</p>';
    document.body.appendChild(loader);
    return loader;
  }

  function showLoader() {
    var loader = ensureLoader();
    loader.classList.add('show');
    loader.setAttribute('aria-hidden', 'false');
  }

  function hideLoader() {
    var loader = document.getElementById(LOADER_ID);
    if (!loader) return;
    loader.classList.remove('show');
    loader.setAttribute('aria-hidden', 'true');
  }

  function shouldIgnoreLink(link, event) {
    if (!link) return true;
    var href = (link.getAttribute('href') || '').trim();
    if (!href) return true;
    if (href.startsWith('#')) return true;
    if (href.toLowerCase().startsWith('javascript:')) return true;
    if (href.toLowerCase().startsWith('mailto:')) return true;
    if (href.toLowerCase().startsWith('tel:')) return true;
    if (link.target === '_blank') return true;
    if (link.hasAttribute('download')) return true;
    if (event && (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) return true;
    return false;
  }

  injectStyle();
  if (document.readyState !== 'loading') ensureLoader();
  else document.addEventListener('DOMContentLoaded', ensureLoader, { once: true });

  window.addEventListener('load', function () {
    setTimeout(hideLoader, 100);
  });

  window.addEventListener('pageshow', hideLoader);

  document.addEventListener(
    'click',
    function (e) {
      var link = e.target && e.target.closest ? e.target.closest('a[href]') : null;
      if (shouldIgnoreLink(link, e)) return;
      showLoader();
    },
    true
  );

  document.addEventListener(
    'submit',
    function () {
      showLoader();
    },
    true
  );

  window.PageLoader = { show: showLoader, hide: hideLoader };
})();
