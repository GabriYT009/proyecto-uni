(function(){
    function init(){
        const grid = document.getElementById('grid');
        const search = document.getElementById('search');
        const searchBtn = document.getElementById('searchBtn');
        const modal = document.getElementById('detailModal');
        const mTitle = document.getElementById('m-title');
        const mImg = document.getElementById('m-img');
        const mDesc = document.getElementById('m-desc');
        const mPrice = document.getElementById('m-price');
        const mClose = document.getElementById('m-close');
        const mBuy = document.getElementById('m-buy');

        function openDetailFromButton(button){
        try {
            try { window.__catalog_debug = true; } catch(e){}
            if (window.__catalog_debug) console.log('[catalog-debug] openDetailFromButton start, scrollY=', window.scrollY, 'button=', button && button.dataset && button.dataset.id);
            console.log('[catalog.js] openDetailFromButton called', button && button.dataset && button.dataset.id);
            const id = button && button.dataset && button.dataset.id ? Number(button.dataset.id) : null;
            // save current scroll position so we can restore it after opening modal
            const __catalog_saved_scroll = (typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0;
            // If a global `openDetail(id)` exists (the function used on the home page), call it
            // but don't bail out: some pages may not fully populate the modal, so
            // after delegating we'll verify and apply a local fallback to ensure
            // the modal content and visibility match the home page behavior.
            var delegated = false;
            if (id !== null && typeof window.openDetail === 'function') {
                try {
                    console.log('[catalog.js] delegating to global openDetail for id', id);
                    window.openDetail(id);
                    delegated = true;
                    // If the global handler already made the modal visible, stop here.
                    try {
                        if (modal && window.getComputedStyle && getComputedStyle(modal).display !== 'none') {
                            return;
                        }
                    } catch(e){}
                    // otherwise continue with local fallback to ensure visibility
                } catch (e) {
                    console.warn('[catalog.js] global openDetail threw, falling back', e);
                }
            }

            const title = button.dataset.title || '';
            const img = button.dataset.img || '';
            const desc = button.dataset.desc || '';
            const price = button.dataset.price || '';
            console.log('[catalog.js] data values', { title, img, desc, price });
            // If the global `openDetail` didn't populate the modal, populate here
            // (this handles cases where `products` isn't available or openDetail didn't set elements).
            if ((!mTitle || !mTitle.textContent) && typeof products !== 'undefined') {
                const prod = products.find(p => Number(p.id) === Number(id));
                if (prod) {
                        if (mTitle) mTitle.textContent = prod.title || title;
                        if (mImg) mImg.src = prod.img || img || '';
                        if (mDesc) mDesc.textContent = prod.desc || desc;
                        if (mPrice) mPrice.textContent = (prod.price && String(prod.price).trim().indexOf('$')===0) ? String(prod.price).trim() : (prod.price ? ('$ ' + String(prod.price).trim()) : (price || ''));
                    } else {
                        if (mTitle) mTitle.textContent = title;
                        if (mImg) mImg.src = img || '';
                        if (mDesc) mDesc.textContent = desc;
                        if (mPrice) mPrice.textContent = (price && String(price).trim().indexOf('$')===0) ? String(price).trim() : (price ? ('$ ' + String(price).trim()) : '');
                    }
            } else {
                if (mTitle) mTitle.textContent = title;
                if (mImg) mImg.src = img || '';
                if (mDesc) mDesc.textContent = desc;
                if (mPrice) mPrice.textContent = price;
            }
        } catch (err) {
            console.error('openDetailFromButton error:', err);
        }
        // click feedback: highlight the card briefly
        const cardEl = button.closest('.card');
        if (cardEl) {
            cardEl.classList.add('selected');
            setTimeout(()=> cardEl.classList.remove('selected'), 260);
        }
        // store current product id for add/buy handlers
        window.currentProductId = button.dataset.id || null;
        console.log('[catalog.js] elements', { modal: !!modal, mTitle: !!mTitle, mImg: !!mImg, mDesc: !!mDesc, mPrice: !!mPrice });
            if(modal){
            // show modal (templates expect .show to toggle visibility)
            modal.classList.add('show');
            // ensure dataset productId for any page-level handlers
            try { if (window.currentProductId) modal.dataset.productId = window.currentProductId; } catch(e){}
            modal.setAttribute('aria-hidden','false');
            // ensure inline style display if used and force visibility
                if (modal.style) {
                    modal.style.display = 'flex';
                    modal.style.visibility = 'visible';
                    modal.style.opacity = '1';
                    modal.style.zIndex = '99999';
                }
                // prevent background scroll while modal open without jumping: fix body position
                try {
                    // blur the currently focused element to avoid browser auto-scrolling
                    try {
                        if (window.__catalog_debug) console.log('[catalog-debug] before blur scrollY=', window.scrollY, 'activeElement=', document.activeElement);
                        if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur();
                        if (window.__catalog_debug) setTimeout(function(){ console.log('[catalog-debug] after blur scrollY=', window.scrollY); }, 10);
                    } catch(e){}
                        // store globally so closeModal can restore scroll position
                        window.__catalog_saved_scroll = (typeof __catalog_saved_scroll !== 'undefined' && __catalog_saved_scroll !== null) ? __catalog_saved_scroll : ((typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0);
                        // disable scrolling on root element
                        try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch(e){}
                        // try to keep viewport at saved position
                        try { window.scrollTo(0, window.__catalog_saved_scroll || 0); } catch(e){}
                } catch(e){}
            console.log('[catalog.js] modal forced visible, style.display=', modal.style && modal.style.display);

                // Ensure inner dialog matches catalog sizing (max-width and margin)
            try {
                const inner = modal.querySelector('.detail-modal');
                if (inner && inner.style) {
                    inner.style.maxWidth = '520px';
                    inner.style.margin = '40px auto';
                    // make inner focusable but avoid calling focus to prevent browser auto-scrolling
                    try { inner.tabIndex = -1; } catch(e){}
                    if (window.__catalog_debug) {
                        console.log('[catalog-debug] modal shown, scrollY=', window.scrollY);
                        var __dbg_focus = function(e){ console.log('[catalog-debug] focusin', e.target, 'scrollY=', window.scrollY); };
                        try { document.addEventListener('focusin', __dbg_focus); setTimeout(function(){ try{ document.removeEventListener('focusin', __dbg_focus); }catch(e){} }, 5000); } catch(e){}
                    }
                }
            } catch(e){ }

            // Debug overlay: show quick visual diagnostics so the user can see state
            try {
                const info = {
                    openDetailType: typeof window.openDetail,
                    productId: window.currentProductId || id,
                    productFromProducts: (typeof products !== 'undefined') ? products.find(p=>Number(p.id)===Number(window.currentProductId||id)) : null,
                    modalExists: !!modal,
                    modalDisplay: window.getComputedStyle ? getComputedStyle(modal).display : (modal.style && modal.style.display),
                    mTitle: mTitle ? (mTitle.textContent || '') : null,
                };
                console.log('[catalog.js] debug info', info);

                // create a small overlay so the user can see the values visually
                const dbgId = 'catalog-debug-overlay';
                let dbg = document.getElementById(dbgId);
                if (!dbg) {
                    dbg = document.createElement('div');
                    dbg.id = dbgId;
                    dbg.style.position = 'fixed';
                    dbg.style.right = '12px';
                    dbg.style.bottom = '12px';
                    dbg.style.zIndex = '100000';
                    dbg.style.background = 'rgba(0,0,0,0.75)';
                    dbg.style.color = '#fff';
                    dbg.style.padding = '10px 12px';
                    dbg.style.borderRadius = '8px';
                    dbg.style.fontSize = '12px';
                    dbg.style.maxWidth = '320px';
                    dbg.style.boxShadow = '0 6px 20px rgba(0,0,0,0.3)';
                    document.body.appendChild(dbg);
                }
                dbg.innerText = 'openDetail: ' + info.openDetailType + '\n' +
                                'prodId: ' + info.productId + '\n' +
                                'prodFound: ' + (info.productFromProducts ? 'yes' : 'no') + '\n' +
                                'modalDisplay: ' + info.modalDisplay + '\n' +
                                'mTitle: ' + (info.mTitle || '(empty)');
                setTimeout(()=> { try{ dbg.remove(); } catch(e){} }, 6000);
            } catch(e){ console.warn('[catalog.js] debug overlay failed', e); }
        }
        }

        function attachListeners(){
        const els = document.querySelectorAll('.view');
        if(!els || !els.length) {
            console.log('[catalog.js] attachListeners: no .view buttons found');
        } else {
            console.log('[catalog.js] attachListeners: found', els.length, 'buttons; using delegated capture handler instead of per-button listeners');
        }
        }

        // Also add event delegation as a fallback for dynamically added buttons
    // capture-phase handler to catch clicks even if something blocks bubbling
    document.addEventListener('click', function(e){
        try{
            const btn = e.target && e.target.closest ? e.target.closest('.view') : null;
            if (btn) {
                // ignore clicks originating from category links (they should navigate to catalog)
                try {
                    const catAncestor = btn.closest('.category-card') || btn.closest('a.category-card');
                    const anchorAncestor = btn.closest('a');
                    const href = anchorAncestor && anchorAncestor.getAttribute ? (anchorAncestor.getAttribute('href') || '') : '';
                    if (catAncestor || (/catalogo|catalog/gi.test(href))) {
                        // allow normal navigation for category selection
                        return;
                    }
                } catch(e){ /* ignore */ }

                // dedupe rapid duplicate events (avoid double-calling when multiple handlers existed)
                try {
                    window.__catalog_last_open_ts = window.__catalog_last_open_ts || 0;
                    window.__catalog_last_open_id = window.__catalog_last_open_id || null;
                    const now = Date.now();
                    if (window.__catalog_last_open_id == btn.dataset.id && (now - window.__catalog_last_open_ts) < 800) {
                        console.log('[catalog.js] duplicate click ignored for id', btn.dataset.id);
                        return;
                    }
                    window.__catalog_last_open_ts = now;
                    window.__catalog_last_open_id = btn.dataset.id;
                } catch(e){}
                console.log('[catalog.js] capture click on .view', btn.dataset && btn.dataset.id);
                const localType = typeof openDetailFromButton === 'function';
                const winType = !!window.openDetailFromButton;
                console.log('[catalog.js] handlers present', { localType, winType });
                e.preventDefault();
                if (localType) {
                    try { openDetailFromButton(btn); console.log('[catalog.js] called local openDetailFromButton'); }
                    catch(err){ console.error('[catalog.js] openDetailFromButton threw', err); }
                } else if (winType) {
                    try { window.openDetailFromButton(btn); console.log('[catalog.js] called window.openDetailFromButton'); }
                    catch(err){ console.error('[catalog.js] window.openDetailFromButton threw', err); }
                } else {
                    console.log('[catalog.js] no openDetailFromButton available');
                }
            }
        } catch(err){ console.error('[catalog.js] delegation handler error', err); }
    }, true);
        // expose for inline debugging / template hooks
        try { window.openDetailFromButton = openDetailFromButton; } catch(e){/* ignore */}

        // reusable close logic (in outer scope so other handlers can call it)
        function closeModal(){
            try {
                if (modal) {
                    modal.classList.remove('show');
                    modal.setAttribute('aria-hidden','true');
                    if (modal.style) modal.style.display = 'none';
                    try {
                        // restore body scroll state using whichever saved var exists
                        var saved = null;
                        if (typeof window.__catalog_saved_scroll !== 'undefined' && window.__catalog_saved_scroll !== null) saved = window.__catalog_saved_scroll;
                        if (saved === null && typeof window.__home_saved_scroll !== 'undefined' && window.__home_saved_scroll !== null) saved = window.__home_saved_scroll;
                        if (saved === null) saved = 0;
                        // restore overflow and scroll
                        try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; } catch(e){}
                        // restore only if we actually have a numeric saved position
                        try {
                            if (saved !== null && Number.isFinite(Number(saved))) {
                                try { window.scrollTo(0, Number(saved)); } catch(e){}
                                try { setTimeout(function(){ window.scrollTo(0, Number(saved)); }, 50); } catch(e){}
                            }
                        } catch(e){}
                        // cleanup both markers
                        try { delete window.__catalog_saved_scroll; } catch(e){}
                        try { delete window.__home_saved_scroll; } catch(e){}
                    } catch(e){}
                }
            } catch(e){ console.warn('[catalog.js] closeModal error', e); }
        }

        if (mClose) {
            try { mClose.addEventListener('click', closeModal); } catch(e){}
        }

        // Also close modal when clicking anywhere outside the inner dialog
        try {
            document.addEventListener('click', function(ev){
                try {
                    if (!modal || !modal.classList.contains('show')) return;
                    const inner = modal.querySelector('.detail-modal') || modal.querySelector('.modal');
                    if (!inner) return;
                    // if the click target is not inside the inner dialog, close
                    if (!inner.contains(ev.target)) {
                        closeModal();
                    }
                } catch(e){}
            }, true);
        } catch(e){}

        // Add to cart handler: try to call page-level addToCart if provided
        const mAddCart = document.getElementById('m-add-cart');
        if (mAddCart) {
            mAddCart.addEventListener('click', ()=>{
                const id = window.currentProductId;
                if (window.addToCart) return window.addToCart(id);
                if (id) {
                    // fallback: submit a form POST to /carrito/
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/carrito/';
                    form.style.display = 'none';
                    const csrf = document.querySelector('meta[name="csrf-token"]');
                    if (csrf && csrf.content) {
                        const inputCsrf = document.createElement('input');
                        inputCsrf.name = 'csrfmiddlewaretoken';
                        inputCsrf.value = csrf.content;
                        form.appendChild(inputCsrf);
                    }
                    const input = document.createElement('input');
                    input.name = 'product_id';
                    input.value = id;
                    form.appendChild(input);
                    document.body.appendChild(form);
                    form.submit();
                }
            });
        }

        if(mBuy){
            mBuy.addEventListener('click', ()=> {
                const id = window.currentProductId;
                if (window.buyNow) return window.buyNow(id);
                if (id) {
                    // default: add to cart then go to cart page
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/carrito/';
                    form.style.display = 'none';
                    const csrf = document.querySelector('meta[name="csrf-token"]');
                    if (csrf && csrf.content) {
                        const inputCsrf = document.createElement('input');
                        inputCsrf.name = 'csrfmiddlewaretoken';
                        inputCsrf.value = csrf.content;
                        form.appendChild(inputCsrf);
                    }
                    const input = document.createElement('input');
                    input.name = 'product_id';
                    input.value = id;
                    form.appendChild(input);
                    const buyNow = document.createElement('input');
                    buyNow.name = 'buy_now';
                    buyNow.value = '1';
                    form.appendChild(buyNow);
                    document.body.appendChild(form);
                    form.submit();
                } else {
                    try{
                        // fallback: if we have a product id, submit a buy form to the server
                        const pid = window.currentProductId || (modal && modal.dataset && modal.dataset.productId) || id;
                        if (pid) {
                            const form = document.createElement('form');
                            form.method = 'POST';
                            form.action = '/producto/' + pid + '/comprar/';
                            const input = document.createElement('input'); input.name = 'product_id'; input.value = pid; form.appendChild(input);
                            document.body.appendChild(form);
                            form.submit();
                        }
                    }catch(e){ /* ignore fallback failure */ }
                }
            });
        }

        // attach initially
        attachListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOMContentLoaded already fired
        init();
    }
})();
(function(){
    function init(){
        const grid = document.getElementById('grid');
        const search = document.getElementById('search');
        const searchBtn = document.getElementById('searchBtn');
        const modal = document.getElementById('detailModal');
        const mTitle = document.getElementById('m-title');
        const mImg = document.getElementById('m-img');
        const mDesc = document.getElementById('m-desc');
        const mPrice = document.getElementById('m-price');
        const mClose = document.getElementById('m-close');
        const mBuy = document.getElementById('m-buy');
        // Prevent pointer interactions from causing native focus -> browser auto-scroll.
        try {
            document.addEventListener('pointerdown', function(e){
                try {
                    const btn = e.target && e.target.closest ? e.target.closest('.view') : null;
                    if (!btn) return;
                    // mark suppression flag for the next focus event; do NOT call preventDefault here
                    // so native click behavior remains consistent
                    window.__suppress_next_focus = true;
                    setTimeout(function(){ window.__suppress_next_focus = false; }, 120);
                    // store the bounding rect of the clicked view so modal can be anchored
                    try { window.__last_view_rect = btn.getBoundingClientRect(); } catch(e){}
                } catch(e){}
            }, true);
            document.addEventListener('focusin', function(ev){
                try {
                    if (window.__suppress_next_focus && ev.target && ev.target.closest && ev.target.closest('.view')) {
                        try { ev.target.blur(); } catch(e){}
                    }
                } catch(e){}
            }, true);
        } catch(e){}

        function openDetailFromButton(button){
        try {
            try { window.__catalog_debug = true; } catch(e){}
            if (window.__catalog_debug) console.log('[catalog-debug] openDetailFromButton start, scrollY=', window.scrollY, 'button=', button && button.dataset && button.dataset.id);
            console.log('[catalog.js] openDetailFromButton called', button && button.dataset && button.dataset.id);
            const id = button && button.dataset && button.dataset.id ? Number(button.dataset.id) : null;
            // save current scroll position so we can restore it after opening modal
            const __catalog_saved_scroll = (typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0;
            // If a global `openDetail(id)` exists (the function used on the home page), call it
            // but don't bail out: some pages may not fully populate the modal, so
            // after delegating we'll verify and apply a local fallback to ensure
            // the modal content and visibility match the home page behavior.
            var delegated = false;
            if (id !== null && typeof window.openDetail === 'function') {
                try {
                    console.log('[catalog.js] delegating to global openDetail for id', id);
                    window.openDetail(id);
                    delegated = true;
                    // If the global handler already made the modal visible, stop here.
                    try {
                        if (modal && window.getComputedStyle && getComputedStyle(modal).display !== 'none') {
                            return;
                        }
                    } catch(e){}
                    // otherwise continue with local fallback to ensure visibility
                } catch (e) {
                    console.warn('[catalog.js] global openDetail threw, falling back', e);
                }
            }

            const title = button.dataset.title || '';
            const img = button.dataset.img || '';
            const desc = button.dataset.desc || '';
            const price = button.dataset.price || '';
            console.log('[catalog.js] data values', { title, img, desc, price });
            // If the global `openDetail` didn't populate the modal, populate here
            // (this handles cases where `products` isn't available or openDetail didn't set elements).
            if ((!mTitle || !mTitle.textContent) && typeof products !== 'undefined') {
                const prod = products.find(p => Number(p.id) === Number(id));
                if (prod) {
                        if (mTitle) mTitle.textContent = prod.title || title;
                        if (mImg) mImg.src = prod.img || img || '';
                        if (mDesc) mDesc.textContent = prod.desc || desc;
                        if (mPrice) mPrice.textContent = (prod.price && String(prod.price).trim().indexOf('$')===0) ? String(prod.price).trim() : (prod.price ? ('$ ' + String(prod.price).trim()) : (price || ''));
                    } else {
                        if (mTitle) mTitle.textContent = title;
                        if (mImg) mImg.src = img || '';
                        if (mDesc) mDesc.textContent = desc;
                        if (mPrice) mPrice.textContent = (price && String(price).trim().indexOf('$')===0) ? String(price).trim() : (price ? ('$ ' + String(price).trim()) : '');
                    }
            } else {
                if (mTitle) mTitle.textContent = title;
                if (mImg) mImg.src = img || '';
                if (mDesc) mDesc.textContent = desc;
                if (mPrice) mPrice.textContent = price;
            }
        } catch (err) {
            console.error('openDetailFromButton error:', err);
        }
        // click feedback: highlight the card briefly
        const cardEl = button.closest('.card');
        if (cardEl) {
            cardEl.classList.add('selected');
            setTimeout(()=> cardEl.classList.remove('selected'), 260);
        }
        // store current product id for add/buy handlers
        window.currentProductId = button.dataset.id || null;
        console.log('[catalog.js] elements', { modal: !!modal, mTitle: !!mTitle, mImg: !!mImg, mDesc: !!mDesc, mPrice: !!mPrice });
            if(modal){
            // show modal (templates expect .show to toggle visibility)
            modal.classList.add('show');
            // ensure dataset productId for any page-level handlers
            try { if (window.currentProductId) modal.dataset.productId = window.currentProductId; } catch(e){}
            modal.setAttribute('aria-hidden','false');
            // ensure inline style display if used and force visibility
                if (modal.style) {
                    modal.style.display = 'flex';
                    modal.style.visibility = 'visible';
                    modal.style.opacity = '1';
                    modal.style.zIndex = '99999';
                }
                // prevent background scroll while modal open without jumping: fix body position
                try {
                    // blur the currently focused element to avoid browser auto-scrolling
                    try {
                        if (window.__catalog_debug) console.log('[catalog-debug] before blur scrollY=', window.scrollY, 'activeElement=', document.activeElement);
                        if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur();
                        if (window.__catalog_debug) setTimeout(function(){ console.log('[catalog-debug] after blur scrollY=', window.scrollY); }, 10);
                    } catch(e){}
                        // store globally so closeModal can restore scroll position
                        window.__catalog_saved_scroll = (typeof __catalog_saved_scroll !== 'undefined' && __catalog_saved_scroll !== null) ? __catalog_saved_scroll : ((typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0);
                        // disable scrolling on root element and avoid layout shift
                        try {
                            const sb = window.innerWidth - document.documentElement.clientWidth;
                            if (sb > 0) {
                                try { document.documentElement.style.paddingRight = sb + 'px'; document.body.style.paddingRight = sb + 'px'; } catch(e){}
                            }
                            try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch(e){}
                        } catch(e){}
                        // do NOT force-scroll here; rely on overflow:hidden to keep viewport
                        // restore will be attempted on close only when a numeric saved value exists
                } catch(e){}
            console.log('[catalog.js] modal forced visible, style.display=', modal.style && modal.style.display);

                // Ensure inner dialog matches catalog sizing. If we have a recent
                // `__last_view_rect` (from pointerdown), anchor the dialog near that
                // element instead of centering it — this keeps the modal where the
                // user clicked and avoids scrolling the page.
            try {
                const inner = modal.querySelector('.detail-modal');
                if (inner && inner.style) {
                    inner.style.maxWidth = '520px';
                    // default to centered modal
                    inner.style.position = '';
                    inner.style.left = '';
                    inner.style.top = '';
                    inner.style.margin = '40px auto';
                    // If we have a saved rect, position absolutely relative to viewport
                    try {
                        const rect = window.__last_view_rect || null;
                        if (rect && typeof rect.top !== 'undefined') {
                            // anchor below the element if it fits, otherwise above
                            const spaceBelow = window.innerHeight - rect.bottom;
                            const spaceAbove = rect.top;
                            inner.style.position = 'absolute';
                            // compute left so dialog is roughly aligned with element
                            let left = rect.left;
                            // ensure dialog doesn't overflow viewport horizontally
                            const dialogWidth = Math.min(520, window.innerWidth - 32);
                            if (left + dialogWidth + 16 > window.innerWidth) left = Math.max(8, window.innerWidth - dialogWidth - 16);
                            inner.style.left = left + 'px';
                            // place below if enough space, else above
                            if (spaceBelow > (inner.offsetHeight || 200) || spaceBelow > spaceAbove) {
                                inner.style.top = (rect.bottom + 8) + 'px';
                            } else {
                                inner.style.top = Math.max(8, rect.top - (inner.offsetHeight || 200) - 8) + 'px';
                            }
                            // remove automatic entrance animation so it appears instantly
                            try { inner.style.animation = 'none'; inner.style.transform = 'none'; inner.style.opacity = '1'; } catch(e){}
                        } else {
                            inner.style.margin = '40px auto';
                        }
                    } catch(e){}
                    // make inner focusable but avoid calling focus to prevent browser auto-scrolling
                    try { inner.tabIndex = -1; } catch(e){}
                    if (window.__catalog_debug) {
                        console.log('[catalog-debug] modal shown, scrollY=', window.scrollY);
                        var __dbg_focus = function(e){ console.log('[catalog-debug] focusin', e.target, 'scrollY=', window.scrollY); };
                        try { document.addEventListener('focusin', __dbg_focus); setTimeout(function(){ try{ document.removeEventListener('focusin', __dbg_focus); }catch(e){} }, 5000); } catch(e){}
                    }
                }
            } catch(e){ }

            // Debug overlay: show quick visual diagnostics so user can see state
            try {
                const info = {
                    openDetailType: typeof window.openDetail,
                    productId: window.currentProductId || id,
                    productFromProducts: (typeof products !== 'undefined') ? products.find(p=>Number(p.id)===Number(window.currentProductId||id)) : null,
                    modalExists: !!modal,
                    modalDisplay: window.getComputedStyle ? getComputedStyle(modal).display : (modal.style && modal.style.display),
                    mTitle: mTitle ? (mTitle.textContent || '') : null,
                };
                console.log('[catalog.js] debug info', info);

                // create a small overlay so the user can see the values visually
                const dbgId = 'catalog-debug-overlay';
                let dbg = document.getElementById(dbgId);
                if (!dbg) {
                    dbg = document.createElement('div');
                    dbg.id = dbgId;
                    dbg.style.position = 'fixed';
                    dbg.style.right = '12px';
                    dbg.style.bottom = '12px';
                    dbg.style.zIndex = '100000';
                    dbg.style.background = 'rgba(0,0,0,0.75)';
                    dbg.style.color = '#fff';
                    dbg.style.padding = '10px 12px';
                    dbg.style.borderRadius = '8px';
                    dbg.style.fontSize = '12px';
                    dbg.style.maxWidth = '320px';
                    dbg.style.boxShadow = '0 6px 20px rgba(0,0,0,0.3)';
                    document.body.appendChild(dbg);
                }
                dbg.innerText = 'openDetail: ' + info.openDetailType + '\n' +
                                'prodId: ' + info.productId + '\n' +
                                'prodFound: ' + (info.productFromProducts ? 'yes' : 'no') + '\n' +
                                'modalDisplay: ' + info.modalDisplay + '\n' +
                                'mTitle: ' + (info.mTitle || '(empty)');
                setTimeout(()=> { try{ dbg.remove(); } catch(e){} }, 6000);
            } catch(e){ console.warn('[catalog.js] debug overlay failed', e); }
        }
        }

        function attachListeners(){
        const els = document.querySelectorAll('.view');
        if(!els || !els.length) {
            console.log('[catalog.js] attachListeners: no .view buttons found');
        } else {
            console.log('[catalog.js] attachListeners: found', els.length, 'buttons; using delegated capture handler instead of per-button listeners');
        }
        }

        // Also add event delegation as a fallback for dynamically added buttons
    // capture-phase handler to catch clicks even if something blocks bubbling
    document.addEventListener('click', function(e){
        try{
            const btn = e.target && e.target.closest ? e.target.closest('.view') : null;
                if (btn) {
                // ignore clicks originating from category links (they should navigate to catalog)
                try {
                    const catAncestor = btn.closest('.category-card') || btn.closest('a.category-card');
                    const anchorAncestor = btn.closest('a');
                    const href = anchorAncestor && anchorAncestor.getAttribute ? (anchorAncestor.getAttribute('href') || '') : '';
                    if (catAncestor || (/catalogo|catalog/gi.test(href))) {
                        // allow normal navigation for category selection
                        return;
                    }
                } catch(e){ /* ignore */ }

                // dedupe rapid duplicate events (avoid double-calling when multiple handlers existed)
                try {
                    window.__catalog_last_open_ts = window.__catalog_last_open_ts || 0;
                    window.__catalog_last_open_id = window.__catalog_last_open_id || null;
                    const now = Date.now();
                    if (window.__catalog_last_open_id == btn.dataset.id && (now - window.__catalog_last_open_ts) < 800) {
                        console.log('[catalog.js] duplicate click ignored for id', btn.dataset.id);
                        return;
                    }
                    window.__catalog_last_open_ts = now;
                    window.__catalog_last_open_id = btn.dataset.id;
                } catch(e){}
                console.log('[catalog.js] capture click on .view', btn.dataset && btn.dataset.id);
                const localType = typeof openDetailFromButton === 'function';
                const winType = !!window.openDetailFromButton;
                console.log('[catalog.js] handlers present', { localType, winType });
                // Prevent other handlers from executing for this event and open modal
                // asynchronously to avoid layout/scroll side-effects while the browser
                // is still handling the input event.
                try { e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation(); } catch(e){}
                if (localType || winType) {
                    setTimeout(function(){
                        try {
                            if (localType) { openDetailFromButton(btn); console.log('[catalog.js] called local openDetailFromButton (async)'); }
                            else if (winType) { window.openDetailFromButton(btn); console.log('[catalog.js] called window.openDetailFromButton (async)'); }
                        } catch(err){ console.error('[catalog.js] async openDetailFromButton threw', err); }
                    }, 0);
                } else {
                    console.log('[catalog.js] no openDetailFromButton available');
                }
            }
        } catch(err){ console.error('[catalog.js] delegation handler error', err); }
    }, true);
        // expose for inline debugging / template hooks
        try { window.openDetailFromButton = openDetailFromButton; } catch(e){/* ignore */}

        // reusable close logic (in outer scope so other handlers can call it)
        function closeModal(){
            try {
                if (modal) {
                    modal.classList.remove('show');
                    modal.setAttribute('aria-hidden','true');
                    if (modal.style) modal.style.display = 'none';
                    try {
                        // restore body scroll state using whichever saved var exists
                        var saved = null;
                        if (typeof window.__catalog_saved_scroll !== 'undefined' && window.__catalog_saved_scroll !== null) saved = window.__catalog_saved_scroll;
                        if (saved === null && typeof window.__home_saved_scroll !== 'undefined' && window.__home_saved_scroll !== null) saved = window.__home_saved_scroll;
                        if (saved === null) saved = 0;
                        // restore overflow and scroll (also remove padding added to avoid layout shift)
                        try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; document.documentElement.style.paddingRight = ''; document.body.style.paddingRight = ''; } catch(e){}
                        // restore only if we actually have a numeric saved position
                        try {
                            if (saved !== null && Number.isFinite(Number(saved))) {
                                try { window.scrollTo(0, Number(saved)); } catch(e){}
                                try { setTimeout(function(){ window.scrollTo(0, Number(saved)); }, 50); } catch(e){}
                            }
                        } catch(e){}
                        // cleanup both markers
                        try { delete window.__catalog_saved_scroll; } catch(e){}
                        try { delete window.__home_saved_scroll; } catch(e){}
                    } catch(e){}
                }
            } catch(e){ console.warn('[catalog.js] closeModal error', e); }
        }

        if (mClose) {
            try { mClose.addEventListener('click', closeModal); } catch(e){}
        }

        // Also close modal when clicking anywhere outside the inner dialog
        try {
            document.addEventListener('click', function(ev){
                try {
                    if (!modal || !modal.classList.contains('show')) return;
                    const inner = modal.querySelector('.detail-modal') || modal.querySelector('.modal');
                    if (!inner) return;
                    // if the click target is not inside the inner dialog, close
                    if (!inner.contains(ev.target)) {
                        closeModal();
                    }
                } catch(e){}
            }, true);
        } catch(e){}

        // Add to cart handler: try to call page-level addToCart if provided
        const mAddCart = document.getElementById('m-add-cart');
        if (mAddCart) {
            mAddCart.addEventListener('click', ()=>{
                const id = window.currentProductId;
                if (window.addToCart) return window.addToCart(id);
                if (id) {
                    // fallback: submit a form POST to /carrito/
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/carrito/';
                    form.style.display = 'none';
                    const csrf = document.querySelector('meta[name="csrf-token"]');
                    if (csrf && csrf.content) {
                        const inputCsrf = document.createElement('input');
                        inputCsrf.name = 'csrfmiddlewaretoken';
                        inputCsrf.value = csrf.content;
                        form.appendChild(inputCsrf);
                    }
                    const input = document.createElement('input');
                    input.name = 'product_id';
                    input.value = id;
                    form.appendChild(input);
                    document.body.appendChild(form);
                    form.submit();
                }
            });
        }

        if(mBuy){
            mBuy.addEventListener('click', ()=> {
                const id = window.currentProductId;
                if (window.buyNow) return window.buyNow(id);
                if (id) {
                    // default: add to cart then go to cart page
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/carrito/';
                    form.style.display = 'none';
                    const csrf = document.querySelector('meta[name="csrf-token"]');
                    if (csrf && csrf.content) {
                        const inputCsrf = document.createElement('input');
                        inputCsrf.name = 'csrfmiddlewaretoken';
                        inputCsrf.value = csrf.content;
                        form.appendChild(inputCsrf);
                    }
                    const input = document.createElement('input');
                    input.name = 'product_id';
                    input.value = id;
                    form.appendChild(input);
                    const buyNow = document.createElement('input');
                    buyNow.name = 'buy_now';
                    buyNow.value = '1';
                    form.appendChild(buyNow);
                    document.body.appendChild(form);
                    form.submit();
                } else {
                    try{
                        const pid = window.currentProductId || (modal && modal.dataset && modal.dataset.productId) || id;
                        if (pid) window.location.href = '/producto/' + pid + '/comprar/';
                    }catch(e){/* ignore */}
                }
            });
        }

        // attach initially
        attachListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOMContentLoaded already fired
        init();
    }
})();