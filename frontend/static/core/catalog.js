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
            // Guardar la posición actual de scroll para restaurarla tras abrir el modal
            const __catalog_saved_scroll = (typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0;
            // Si existe `openDetail(id)` global (función usada en home), llamarlo
            // pero no salir de inmediato: algunas páginas no llenan todo el modal,
            // así que después de delegar verificamos y aplicamos fallback local para asegurar
            // que el contenido y la visibilidad coincidan con el comportamiento de home.
            var delegated = false;
            if (id !== null && typeof window.openDetail === 'function') {
                try {
                    console.log('[catalog.js] delegating to global openDetail for id', id);
                    window.openDetail(id);
                    delegated = true;
                    // Si el handler global ya dejó visible el modal, detener aquí.
                    try {
                        if (modal && window.getComputedStyle && getComputedStyle(modal).display !== 'none') {
                            return;
                        }
                    } catch(e){}
                    // de lo contrario, continuar con fallback local para asegurar visibilidad
                } catch (e) {
                    console.warn('[catalog.js] global openDetail threw, falling back', e);
                }
            }

            const title = button.dataset.title || '';
            const img = button.dataset.img || '';
            const desc = button.dataset.desc || '';
            const price = button.dataset.price || '';
            console.log('[catalog.js] data values', { title, img, desc, price });
            // Si `openDetail` global no llenó el modal, poblarlo aquí
            // (cubre casos donde `products` no está disponible o openDetail no seteó elementos).
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
        // Feedback de clic: resaltar la tarjeta brevemente
        const cardEl = button.closest('.card');
        if (cardEl) {
            cardEl.classList.add('selected');
            setTimeout(()=> cardEl.classList.remove('selected'), 260);
        }
        // Guardar ID y stock actual para handlers de agregar/comprar
        window.currentProductId = button.dataset.id || null;
        window.currentProductStock = Number(button.dataset.stock || 0);
        console.log('[catalog.js] elements', { modal: !!modal, mTitle: !!mTitle, mImg: !!mImg, mDesc: !!mDesc, mPrice: !!mPrice });
            if(modal){
            // Mostrar modal (los templates esperan .show para visibilidad)
            modal.classList.add('show');
            // Asegurar dataset productId para handlers de página
            try { if (window.currentProductId) modal.dataset.productId = window.currentProductId; } catch(e){}
            modal.setAttribute('aria-hidden','false');
            // Asegurar display inline si aplica y forzar visibilidad
                if (modal.style) {
                    modal.style.display = 'flex';
                    modal.style.visibility = 'visible';
                    modal.style.opacity = '1';
                    modal.style.zIndex = '99999';
                }
                // Evitar scroll de fondo con modal abierto sin saltos: ajustar body
                try {
                    // Quitar foco al elemento activo para evitar auto-scroll del navegador
                    try {
                        if (window.__catalog_debug) console.log('[catalog-debug] before blur scrollY=', window.scrollY, 'activeElement=', document.activeElement);
                        if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur();
                        if (window.__catalog_debug) setTimeout(function(){ console.log('[catalog-debug] after blur scrollY=', window.scrollY); }, 10);
                    } catch(e){}
                        // Guardar globalmente para que closeModal pueda restaurar el scroll
                        window.__catalog_saved_scroll = (typeof __catalog_saved_scroll !== 'undefined' && __catalog_saved_scroll !== null) ? __catalog_saved_scroll : ((typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0);
                        // Deshabilitar scroll en el elemento raíz
                        try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch(e){}
                        // Mantener posición del viewport; evitar saltos forzados de scroll.
                } catch(e){}
            console.log('[catalog.js] modal forced visible, style.display=', modal.style && modal.style.display);

                // Asegurar que el diálogo interno respete medidas del catálogo (max-width y margen)
            try {
                const inner = modal.querySelector('.detail-modal');
                if (inner && inner.style) {
                    inner.style.maxWidth = '520px';
                    inner.style.margin = '40px auto';
                    // Hacer focusable el modal interno, pero sin llamar a focus para evitar auto-scroll.
                    try { inner.tabIndex = -1; } catch(e){}
                    if (window.__catalog_debug) {
                        console.log('[catalog-debug] modal shown, scrollY=', window.scrollY);
                        var __dbg_focus = function(e){ console.log('[catalog-debug] focusin', e.target, 'scrollY=', window.scrollY); };
                        try { document.addEventListener('focusin', __dbg_focus); setTimeout(function(){ try{ document.removeEventListener('focusin', __dbg_focus); }catch(e){} }, 5000); } catch(e){}
                    }
                }
            } catch(e){ }
                try {
                    const addBtn = modal.querySelector('#m-add-cart');
                    const stockNote = modal.querySelector('#m-stock-note');
                    const outOfStock = Number(window.currentProductStock || 0) <= 0;
                    if (addBtn) {
                        addBtn.disabled = outOfStock;
                        addBtn.textContent = outOfStock ? 'No disponible' : 'Añadir al carrito';
                        addBtn.style.opacity = outOfStock ? '0.65' : '1';
                        addBtn.style.cursor = outOfStock ? 'not-allowed' : 'pointer';
                    }
                    if (stockNote) {
                        const lowStock = !outOfStock && Number(window.currentProductStock || 0) > 0 && Number(window.currentProductStock || 0) <= 10;
                        if (outOfStock) {
                            stockNote.style.display = 'block';
                            stockNote.textContent = 'Este producto no se encuentra en stock actualmente. Puedes verlo, pero no agregarlo al carrito.';
                        } else if (lowStock) {
                            const units = Number(window.currentProductStock) === 1 ? 'unidad' : 'unidades';
                            stockNote.style.display = 'block';
                            stockNote.textContent = `Quedan solo ${window.currentProductStock} ${units} en stock. ¡Apresúrate!`;
                        } else {
                            stockNote.style.display = 'none';
                            stockNote.textContent = '';
                        }
                    }
                } catch(e){}

            // Overlay de depuración: diagnóstico visual rápido para ver el estado
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

                // crear un overlay pequeño para ver visualmente los valores
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

        // Agregar también delegación de eventos como fallback para botones dinámicos
    // Handler en fase capture para capturar clics aunque algo bloquee bubbling
    document.addEventListener('click', function(e){
        try{
            const btn = e.target && e.target.closest ? e.target.closest('.view') : null;
            if (btn) {
                // Ignorar clics originados en enlaces de categoría (deben navegar al catálogo)
                try {
                    const catAncestor = btn.closest('.category-card') || btn.closest('a.category-card');
                    const anchorAncestor = btn.closest('a');
                    const href = anchorAncestor && anchorAncestor.getAttribute ? (anchorAncestor.getAttribute('href') || '') : '';
                    if (catAncestor || (/catalogo|catalog/gi.test(href))) {
                        // Permitir navegación normal para selección de categoría
                        return;
                    }
                } catch(e){ /* ignore */ }

                // Deduplicar eventos rápidos para evitar doble llamada
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
        // Exponer para depuración inline / hooks de template
        try { window.openDetailFromButton = openDetailFromButton; } catch(e){/* ignore */}

        // Lógica reutilizable de cierre (scope externo para otros handlers)
        function closeModal(){
            try {
                if (modal) {
                    modal.classList.remove('show');
                    modal.setAttribute('aria-hidden','true');
                    if (modal.style) modal.style.display = 'none';
                    try {
                        // Restaurar estado de scroll del body con la variable guardada disponible
                        var saved = null;
                        if (typeof window.__catalog_saved_scroll !== 'undefined' && window.__catalog_saved_scroll !== null) saved = window.__catalog_saved_scroll;
                        if (saved === null && typeof window.__home_saved_scroll !== 'undefined' && window.__home_saved_scroll !== null) saved = window.__home_saved_scroll;
                        if (saved === null) saved = 0;
                        // Restaurar overflow y scroll
                        try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; } catch(e){}
                        // Restaurar solo si existe una posición guardada numérica
                        // Mantener la posición actual al cerrar; evitar saltos forzados
                        // Limpiar ambos marcadores
                        try { delete window.__catalog_saved_scroll; } catch(e){}
                        try { delete window.__home_saved_scroll; } catch(e){}
                    } catch(e){}
                }
            } catch(e){ console.warn('[catalog.js] closeModal error', e); }
        }

        if (mClose) {
            try { mClose.addEventListener('click', closeModal); } catch(e){}
        }

        // Cerrar modal también al hacer clic fuera del diálogo interno
        try {
            document.addEventListener('click', function(ev){
                try {
                    if (!modal || !modal.classList.contains('show')) return;
                    const inner = modal.querySelector('.detail-modal') || modal.querySelector('.modal');
                    if (!inner) return;
                    // Si el objetivo del clic no está dentro del diálogo interno, cerrar
                    if (!inner.contains(ev.target)) {
                        closeModal();
                    }
                } catch(e){}
            }, true);
        } catch(e){}

        // Handler de agregar al carrito: intentar usar addToCart si existe en la página
        const mAddCart = document.getElementById('m-add-cart');
        if (mAddCart) {
            mAddCart.addEventListener('click', ()=>{
                const id = window.currentProductId;
                if (window.addToCart) return window.addToCart(id);
                if (id) {
                    // Fallback: enviar formulario POST a /carrito/
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
                    // Por defecto: agregar al carrito y luego ir a su página
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

        // Enlazar inicialmente
        attachListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOMContentLoaded ya se ejecutó
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
        // Evitar que interacciones de puntero causen foco nativo y auto-scroll del navegador.
        try {
            document.addEventListener('pointerdown', function(e){
                try {
                    const btn = e.target && e.target.closest ? e.target.closest('.view') : null;
                    if (!btn) return;
                    // Marcar supresión para el siguiente evento de foco; NO usar preventDefault aquí
                    // para mantener consistente el comportamiento nativo del clic
                    window.__suppress_next_focus = true;
                    setTimeout(function(){ window.__suppress_next_focus = false; }, 120);
                    // Guardar bounding rect del elemento clicado para poder anclar el modal
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
            // Guardar la posición actual de scroll para restaurarla tras abrir el modal
            const __catalog_saved_scroll = (typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0;
            // Si existe `openDetail(id)` global (función usada en home), llamarlo
            // pero no salir de inmediato: algunas páginas no llenan todo el modal,
            // así que después de delegar verificamos y aplicamos fallback local para asegurar
            // que el contenido y la visibilidad coincidan con el comportamiento de home.
            var delegated = false;
            if (id !== null && typeof window.openDetail === 'function') {
                try {
                    console.log('[catalog.js] delegating to global openDetail for id', id);
                    window.openDetail(id);
                    delegated = true;
                    // Si el handler global ya dejó visible el modal, detener aquí.
                    try {
                        if (modal && window.getComputedStyle && getComputedStyle(modal).display !== 'none') {
                            return;
                        }
                    } catch(e){}
                    // de lo contrario, continuar con fallback local para asegurar visibilidad
                } catch (e) {
                    console.warn('[catalog.js] global openDetail threw, falling back', e);
                }
            }

            const title = button.dataset.title || '';
            const img = button.dataset.img || '';
            const desc = button.dataset.desc || '';
            const price = button.dataset.price || '';
            console.log('[catalog.js] data values', { title, img, desc, price });
            // Si el `openDetail` global no llenó el modal, completarlo aquí.
            // (Esto cubre casos donde `products` no existe o openDetail no asignó elementos).
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
        // Feedback de clic: resaltar la tarjeta brevemente
        const cardEl = button.closest('.card');
        if (cardEl) {
            cardEl.classList.add('selected');
            setTimeout(()=> cardEl.classList.remove('selected'), 260);
        }
        // Guardar ID actual de producto para handlers de agregar/comprar
        window.currentProductId = button.dataset.id || null;
        console.log('[catalog.js] elements', { modal: !!modal, mTitle: !!mTitle, mImg: !!mImg, mDesc: !!mDesc, mPrice: !!mPrice });
            if(modal){
            // Mostrar modal (los templates esperan .show para visibilidad)
            modal.classList.add('show');
            // Asegurar dataset productId para handlers de página
            try { if (window.currentProductId) modal.dataset.productId = window.currentProductId; } catch(e){}
            modal.setAttribute('aria-hidden','false');
            // Asegurar display inline si aplica y forzar visibilidad
                if (modal.style) {
                    modal.style.display = 'flex';
                    modal.style.visibility = 'visible';
                    modal.style.opacity = '1';
                    modal.style.zIndex = '99999';
                }
                // Evitar scroll de fondo con modal abierto sin saltos: ajustar body
                try {
                    // Quitar foco al elemento activo para evitar auto-scroll del navegador
                    try {
                        if (window.__catalog_debug) console.log('[catalog-debug] before blur scrollY=', window.scrollY, 'activeElement=', document.activeElement);
                        if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur();
                        if (window.__catalog_debug) setTimeout(function(){ console.log('[catalog-debug] after blur scrollY=', window.scrollY); }, 10);
                    } catch(e){}
                        // Guardar globalmente para que closeModal pueda restaurar el scroll
                        window.__catalog_saved_scroll = (typeof __catalog_saved_scroll !== 'undefined' && __catalog_saved_scroll !== null) ? __catalog_saved_scroll : ((typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0);
                        // Deshabilitar scroll en el elemento raíz and avoid layout shift
                        try {
                            const sb = window.innerWidth - document.documentElement.clientWidth;
                            if (sb > 0) {
                                try { document.documentElement.style.paddingRight = sb + 'px'; document.body.style.paddingRight = sb + 'px'; } catch(e){}
                            }
                            try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch(e){}
                        } catch(e){}
                        // NO forzar scroll aquí; usar overflow:hidden para mantener el viewport
                        // La restauración se intenta al cerrar solo si existe un valor numérico guardado
                } catch(e){}
            console.log('[catalog.js] modal forced visible, style.display=', modal.style && modal.style.display);

                // Asegurar medidas del diálogo interno. Si existe un valor reciente
                // `__last_view_rect` (de pointerdown), anclar el diálogo cerca de ese
                // elemento en lugar de centrarlo; así el modal queda donde el
                // usuario hizo clic y se evita desplazar la página.
            try {
                const inner = modal.querySelector('.detail-modal');
                if (inner && inner.style) {
                    inner.style.maxWidth = '520px';
                    // Por defecto, modal centrado
                    inner.style.position = '';
                    inner.style.left = '';
                    inner.style.top = '';
                    inner.style.margin = '40px auto';
                    // Si hay un rect guardado, posicionar absoluto respecto al viewport.
                    try {
                        const rect = window.__last_view_rect || null;
                        if (rect && typeof rect.top !== 'undefined') {
                            // anclar debajo del elemento si cabe; si no, arriba
                            const spaceBelow = window.innerHeight - rect.bottom;
                            const spaceAbove = rect.top;
                            inner.style.position = 'absolute';
                            // calcular left para alinear aproximadamente el diálogo con el elemento
                            let left = rect.left;
                            // asegurar que el diálogo no se desborde horizontalmente del viewport
                            const dialogWidth = Math.min(520, window.innerWidth - 32);
                            if (left + dialogWidth + 16 > window.innerWidth) left = Math.max(8, window.innerWidth - dialogWidth - 16);
                            inner.style.left = left + 'px';
                            // Ubicar abajo si hay espacio suficiente; si no, arriba.
                            if (spaceBelow > (inner.offsetHeight || 200) || spaceBelow > spaceAbove) {
                                inner.style.top = (rect.bottom + 8) + 'px';
                            } else {
                                inner.style.top = Math.max(8, rect.top - (inner.offsetHeight || 200) - 8) + 'px';
                            }
                            // quitar animación automática de entrada para que aparezca al instante
                            try { inner.style.animation = 'none'; inner.style.transform = 'none'; inner.style.opacity = '1'; } catch(e){}
                        } else {
                            inner.style.margin = '40px auto';
                        }
                    } catch(e){}
                    // Hacer focusable el modal interno, pero sin llamar a focus para evitar auto-scroll.
                    try { inner.tabIndex = -1; } catch(e){}
                    if (window.__catalog_debug) {
                        console.log('[catalog-debug] modal shown, scrollY=', window.scrollY);
                        var __dbg_focus = function(e){ console.log('[catalog-debug] focusin', e.target, 'scrollY=', window.scrollY); };
                        try { document.addEventListener('focusin', __dbg_focus); setTimeout(function(){ try{ document.removeEventListener('focusin', __dbg_focus); }catch(e){} }, 5000); } catch(e){}
                    }
                }
            } catch(e){ }

            // Overlay de depuración: diagnóstico visual rápido para ver el estado
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

                // crear un overlay pequeño para ver visualmente los valores
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

        // Agregar también delegación de eventos como fallback para botones dinámicos
    // Handler en fase capture para capturar clics aunque algo bloquee bubbling
    document.addEventListener('click', function(e){
        try{
            const btn = e.target && e.target.closest ? e.target.closest('.view') : null;
                if (btn) {
                // Ignorar clics originados en enlaces de categoría (deben navegar al catálogo)
                try {
                    const catAncestor = btn.closest('.category-card') || btn.closest('a.category-card');
                    const anchorAncestor = btn.closest('a');
                    const href = anchorAncestor && anchorAncestor.getAttribute ? (anchorAncestor.getAttribute('href') || '') : '';
                    if (catAncestor || (/catalogo|catalog/gi.test(href))) {
                        // Permitir navegación normal para selección de categoría
                        return;
                    }
                } catch(e){ /* ignore */ }

                // Deduplicar eventos rápidos para evitar doble llamada
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
                // Evitar que otros handlers ejecuten este evento y abrir modal
                // de forma asíncrona para evitar efectos secundarios de layout/scroll mientras el navegador
                // todavía procesa el evento de entrada.
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
        // Exponer para depuración inline / hooks de template
        try { window.openDetailFromButton = openDetailFromButton; } catch(e){/* ignore */}

        // Lógica reutilizable de cierre (scope externo para otros handlers)
        function closeModal(){
            try {
                if (modal) {
                    modal.classList.remove('show');
                    modal.setAttribute('aria-hidden','true');
                    if (modal.style) modal.style.display = 'none';
                    try {
                        // Restaurar estado de scroll del body con la variable guardada disponible
                        var saved = null;
                        if (typeof window.__catalog_saved_scroll !== 'undefined' && window.__catalog_saved_scroll !== null) saved = window.__catalog_saved_scroll;
                        if (saved === null && typeof window.__home_saved_scroll !== 'undefined' && window.__home_saved_scroll !== null) saved = window.__home_saved_scroll;
                        if (saved === null) saved = 0;
                        // Restaurar overflow y scroll (también remover padding agregado para evitar salto de layout)
                        try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; document.documentElement.style.paddingRight = ''; document.body.style.paddingRight = ''; } catch(e){}
                        // Restaurar solo si existe una posición guardada numérica
                        // Mantener la posición actual al cerrar; evitar saltos forzados
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

        // Cerrar modal también al hacer clic fuera del diálogo interno
        try {
            document.addEventListener('click', function(ev){
                try {
                    if (!modal || !modal.classList.contains('show')) return;
                    const inner = modal.querySelector('.detail-modal') || modal.querySelector('.modal');
                    if (!inner) return;
                    // Si el objetivo del clic no está dentro del diálogo interno, cerrar
                    if (!inner.contains(ev.target)) {
                        closeModal();
                    }
                } catch(e){}
            }, true);
        } catch(e){}

        // Handler de agregar al carrito: intentar usar addToCart si existe en la página
        const mAddCart = document.getElementById('m-add-cart');
        if (mAddCart) {
            mAddCart.addEventListener('click', ()=>{
                const id = window.currentProductId;
                if (window.addToCart) return window.addToCart(id);
                if (id) {
                    // Fallback: enviar formulario POST a /carrito/
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
                    // Por defecto: agregar al carrito y luego ir a su página
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

        // Enlazar inicialmente
        attachListeners();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOMContentLoaded ya se ejecutó
        init();
    }
})();

// Handler global seguro para cerrar el modal de detalle de producto.
(function(){
    if (window.__detailModalGlobalCloseBound) return;
    window.__detailModalGlobalCloseBound = true;

    function closeDetailModal(){
        const modalEl = document.getElementById('detailModal');
        if (!modalEl) return;
        modalEl.classList.remove('show');
        modalEl.setAttribute('aria-hidden', 'true');
        if (modalEl.style) modalEl.style.display = 'none';
        try {
            document.documentElement.style.overflow = '';
            document.body.style.overflow = '';
            document.documentElement.style.paddingRight = '';
            document.body.style.paddingRight = '';
        } catch(e){}
    }

    document.addEventListener('click', function(ev){
        const modalEl = document.getElementById('detailModal');
        if (!modalEl || !modalEl.classList.contains('show')) return;
        const inner = modalEl.querySelector('.detail-modal') || modalEl.querySelector('.modal');
        if (!inner || !inner.contains(ev.target)) closeDetailModal();
    }, true);

    document.addEventListener('keydown', function(ev){
        if (ev.key === 'Escape') {
            const modalEl = document.getElementById('detailModal');
            if (modalEl && modalEl.classList.contains('show')) closeDetailModal();
        }
    });
})();
