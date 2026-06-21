(function () {
  var LOADER_ID = 'pageLoaderOverlay';
  var STYLE_ID = 'pageLoaderStyles';

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = '' +
      '#' + LOADER_ID + '{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:99999;opacity:0;visibility:hidden;pointer-events:none;transition:opacity .22s ease,visibility .22s ease;background:rgba(12,16,24,.34);-webkit-backdrop-filter:blur(10px) saturate(1.08);backdrop-filter:blur(10px) saturate(1.08);}'+
      '#' + LOADER_ID + '.is-visible{opacity:1;visibility:visible;pointer-events:auto;}'+
      '#' + LOADER_ID + ' .loader-box{display:flex;flex-direction:column;align-items:center;gap:12px;color:#f3f6ff;font:600 14px/1.2 Urbanist,Segoe UI,Roboto,Arial,sans-serif;letter-spacing:.02em;text-shadow:0 2px 10px rgba(0,0,0,.25);}'+
      '#' + LOADER_ID + ' .loader-spinner{width:54px;height:54px;border-radius:50%;border:3px solid rgba(255,255,255,.32);border-top-color:#7d8cff;border-right-color:#4f67f4;animation:pageLoaderSpin .85s linear infinite;box-shadow:0 0 16px rgba(79,103,244,.25);}'+
      '@media (prefers-color-scheme: light){#' + LOADER_ID + '{background:rgba(244,248,255,.48);}#' + LOADER_ID + ' .loader-box{color:#223048;text-shadow:0 1px 8px rgba(255,255,255,.65);}#' + LOADER_ID + ' .loader-spinner{border-color:rgba(34,48,72,.22);border-top-color:#5b74f7;border-right-color:#3c5cf0;box-shadow:0 0 12px rgba(60,92,240,.18);}}'+
      '@keyframes pageLoaderSpin{to{transform:rotate(360deg);}}';
    document.head.appendChild(style);
  }

  function ensureLoader() {
    var existing = document.getElementById(LOADER_ID);
    if (existing) return existing;

    var overlay = document.createElement('div');
    overlay.id = LOADER_ID;
    overlay.setAttribute('aria-hidden', 'true');
    overlay.innerHTML = '<div class="loader-box"><div class="loader-spinner" aria-hidden="true"></div><div>Cargando...</div></div>';
    document.body.appendChild(overlay);
    return overlay;
  }

  var loaderEl;
  var skipBeforeUnload = false;

  function showLoader() {
    loaderEl = loaderEl || ensureLoader();
    loaderEl.classList.add('is-visible');
  }

  function hideLoader() {
    if (!loaderEl) loaderEl = document.getElementById(LOADER_ID);
    if (loaderEl) loaderEl.classList.remove('is-visible');
  }

  function isModifiedClick(e) {
    return e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0;
  }

  function shouldSkipPageLoaderAttribute(link) {
    return !!(link && link.dataset && (link.dataset.skipPageLoader === 'true' || link.dataset.skipPageLoader === '1'));
  }

  function isPdfLink(link) {
    if (!link) return false;
    var href = (link.getAttribute('href') || '').split('?')[0].split('#')[0].trim().toLowerCase();
    return href.indexOf('/pdf/') !== -1 || href.endsWith('.pdf');
  }

  function shouldSkipLink(link) {
    if (!link) return true;
    if (shouldSkipPageLoaderAttribute(link)) return true;
    // Omitir enlaces gestionados por JS (abrir modal / agregar al carrito por AJAX).
    if (link.classList && (link.classList.contains('view') || link.classList.contains('add-cart'))) return true;
    if (link.closest && link.closest('.view, .add-cart')) return true;
    var href = link.getAttribute('href') || '';
    if (!href || href === '#' || href.startsWith('javascript:') || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('data:')) return true;
    if (href.indexOf('/add_to_cart/') !== -1) return true;
    if (link.hasAttribute('download')) return true;
    if (link.target && link.target.toLowerCase() !== '_self') return true;
    if (isPdfLink(link)) return true;
    return false;
  }

  function shouldSkipForm(form) {
    if (!form) return true;
    if ((form.target || '').toLowerCase() && (form.target || '').toLowerCase() !== '_self') return true;
    return false;
  }

  function init() {
    injectStyles();
    loaderEl = ensureLoader();

    document.addEventListener('click', function (e) {
      if (isModifiedClick(e)) return;
      skipBeforeUnload = false;
      var target = e.target;
      if (target && target.nodeType !== 1) target = target.parentElement;
      var link = target && target.closest ? target.closest('a[href]') : null;
      if (link && (isPdfLink(link) || shouldSkipPageLoaderAttribute(link))) {
        skipBeforeUnload = true;
        hideLoader();
        return;
      }
      if (shouldSkipLink(link)) return;
      showLoader();
    }, true);

    document.addEventListener('submit', function (e) {
      skipBeforeUnload = false;
      var form = e.target;
      if (shouldSkipForm(form)) return;
      showLoader();
    }, true);

    window.addEventListener('beforeunload', function () {
      if (skipBeforeUnload) return;
      showLoader();
    });

    window.addEventListener('pageshow', function () {
      skipBeforeUnload = false;
      hideLoader();
    });

    window.addEventListener('load', function () {
      skipBeforeUnload = false;
      hideLoader();
    });

    // Exponer controles para páginas con flujos asíncronos que deben ocultar el overlay manualmente.
    window.PageLoader = {
      show: showLoader,
      hide: hideLoader
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
