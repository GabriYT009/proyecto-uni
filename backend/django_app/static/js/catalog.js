let products = [
    // Productos eliminados del inicio - ahora se crean en categorías específicas
];

let grid;
let search;
let searchBtn;
let sortBy;
let modal;
let mTitle;
let mImg;
let mDesc;
let mPrice;
let mClose;
let mBuy;
let viewCatalogBtn;

function render(list){
    if (!grid) grid = document.getElementById('grid');
    if (!grid) return;
    grid.innerHTML = '';
    if (!list.length) { grid.innerHTML = '<p style="color:#fff">No hay productos.</p>'; return; }
    list.forEach(p => {
        const el = document.createElement('div');
        el.className = 'card';
        el.innerHTML = `
            <img src="${p.img}" alt="${p.title}">
            <h4>${p.title}</h4>
            <small>${p.category}</small>
            <p>${p.desc}</p>
            <div class="row">
                <strong>${p.price}</strong>
                <div>
                    <button class="btn view" data-id="${p.id}">Ver</button>
                </div>
            </div>
        `;
        grid.appendChild(el);
    });
    document.querySelectorAll('.view').forEach(b=>{
        b.addEventListener('click', ()=> openDetail(Number(b.dataset.id)));
    });
}

function parsePrice(p){
    if (!p) return 0;
    const n = String(p).replace(/[^0-9.]/g,'');
    return parseFloat(n) || 0;
}

function formatPrice(v){
    if (v === null || typeof v === 'undefined') return '';
    var s = String(v).trim();
    if (s === '') return '';
    if (/^\$/.test(s)) return s;
    return '$ ' + s;
}

function applySort(list, sortVal){
    if (!sortVal) return list.slice();
    const copy = list.slice();
    if (sortVal === 'title_asc'){
        return copy.sort((a,b)=> a.title.localeCompare(b.title, 'es'));
    }
    if (sortVal === 'price_asc'){
        return copy.sort((a,b)=> parsePrice(a.price) - parsePrice(b.price));
    }
    if (sortVal === 'price_desc'){
        return copy.sort((a,b)=> parsePrice(b.price) - parsePrice(a.price));
    }
    return copy;
}

function getFilteredAndSortedProducts(){
    if (!search) search = document.getElementById('search');
    if (!sortBy) sortBy = document.getElementById('sortBy');
    const q = (search && search.value || '').toLowerCase().trim();
    const source = (window && window.products && window.products.length) ? window.products : products;
    const filtered = source.filter(p => (p.title||'').toLowerCase().includes(q) || (p.desc||'').toLowerCase().includes(q));
    const sortVal = (sortBy && sortBy.value) || '';
    return applySort(filtered, sortVal);
}

function openDetail(id){
    console.log('[home catalog.js] openDetail called', id);
    // preserve scroll and blur active element to avoid browser auto-scrolling
    const __saved_scroll = (typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0;
    try { if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur(); } catch(e){}
    if (!modal) modal = document.getElementById('detailModal');
    if (!mTitle) mTitle = document.getElementById('m-title');
    if (!mImg) mImg = document.getElementById('m-img');
    if (!mDesc) mDesc = document.getElementById('m-desc');
    if (!mPrice) mPrice = document.getElementById('m-price');
    const source = (window && window.products && window.products.length) ? window.products : products;
    const p = source.find(x=>Number(x.id)===Number(id));
    if(!p) {
        console.warn('[home catalog.js] openDetail: product not found', id);
        return;
    }
    mTitle.textContent = p.title;
    mImg.src = p.img;
    mDesc.textContent = p.desc;
    mPrice.textContent = formatPrice(p.price);
    if (modal) {
        modal.classList.add('show');
        modal.setAttribute('aria-hidden','false');
        try { modal.dataset.productId = id; } catch(e){}
        // Ensure inline styles also make the modal visible in case the template
        // includes an inline `style="display:none"` which overrides CSS rules.
        try {
            if (modal.style) {
                modal.style.display = 'flex';
                modal.style.visibility = 'visible';
                modal.style.opacity = '1';
                modal.style.zIndex = '99999';
            }
            // prevent background scroll while modal open: use overflow hidden only
            try {
                window.__home_saved_scroll = __saved_scroll;
                try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch(e){}
                // do NOT force-scroll here; rely on overflow:hidden to keep viewport
                // restoration will be attempted on close only when a numeric saved value exists
            } catch(e){}
        } catch(e){}
        console.log('[home catalog.js] modal shown, className=', modal.className, 'display=', (window.getComputedStyle? getComputedStyle(modal).display : (modal.style && modal.style.display)));
        // Do not force window scroll on open; keep current viewport position.
    } else {
        console.warn('[home catalog.js] modal element not found');
    }
}

if (!mClose) mClose = document.getElementById('m-close');
if (!mBuy) mBuy = document.getElementById('m-buy');
// defensive close/open helpers and guarded listeners
function closeModal() {
    try {
        if (modal) {
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden','true');
            try {
                if (modal.style) modal.style.display = 'none';
                // restore scroll only if a saved numeric position exists
                var saved = null;
                if (typeof window.__home_saved_scroll !== 'undefined' && window.__home_saved_scroll !== null) saved = window.__home_saved_scroll;
                if (saved === null && typeof window.__catalog_saved_scroll !== 'undefined' && window.__catalog_saved_scroll !== null) saved = window.__catalog_saved_scroll;
                if (saved === null) saved = 0;
                try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; } catch(e){}
                // Keep current viewport position on close; no forced scroll jump.
                try { delete window.__home_saved_scroll; } catch(e){}
                try { delete window.__catalog_saved_scroll; } catch(e){}
            } catch(e){}
        }
    } catch(e){ console.warn('[home catalog.js] closeModal error', e); }
}

try {
    if (mClose) {
        mClose.addEventListener('click', closeModal);
    }
} catch(e){ console.warn('[home catalog.js] mClose listener failed', e); }

try {
    if (modal) {
        modal.addEventListener('click', function(ev){ if (ev.target === modal) closeModal(); });
    }
} catch(e){ /* ignore */ }

try {
    if (mBuy) {
        mBuy.addEventListener('click', function(e){
                try{
                var id = window.currentProductId || (document.getElementById('detailModal') && document.getElementById('detailModal').dataset.productId);
                if (id) window.location.href = '/producto/' + id + '/comprar/';
            }catch(err){}
        });
    }
} catch(e){ console.warn('[home catalog.js] mBuy listener failed', e); }

if (!search) search = document.getElementById('search');
if (search){
    // No live filtering while the user types. Prevent Enter from triggering anything
    // so the search only runs when the user clicks the `Buscar` button.
    search.addEventListener('keydown', (e)=>{
        if (e.key === 'Enter' || e.keyCode === 13) {
            e.preventDefault();
        }
    });
}

// set default sort to price ascending if none selected
if (!sortBy) sortBy = document.getElementById('sortBy');
if (sortBy && !sortBy.value){
    sortBy.value = 'price_asc';
}

// Event listeners removed - now handled in home.js with category filtering

// When user clicks "Ver catálogo" -> reset search & sort and show all products
if (!viewCatalogBtn) viewCatalogBtn = document.getElementById('viewCatalogBtn');
if (viewCatalogBtn){
    viewCatalogBtn.addEventListener('click', (e)=>{
        e.preventDefault();
        if (search) search.value = '';
        if (sortBy) sortBy.value = 'title_asc';
        // close modal if open
        if (modal){
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden','true');
        }
        // render all products
        render(applySort(products, 'title_asc'));
        // scroll to the grid section
        const gridEl = document.getElementById('grid');
        if (gridEl && gridEl.scrollIntoView) gridEl.scrollIntoView({ behavior: 'smooth' });
    });
}

// Delegated handler for any element with `view` class (works on home and catalog)
document.addEventListener('click', function(e){
    try{
        const el = e.target && e.target.closest ? e.target.closest('.view') : null;
        if (!el) return;
        const id = el.dataset && el.dataset.id ? Number(el.dataset.id) : null;
        if (id === null) return;
        console.log('[home catalog.js] delegated view click for id', id);
        if (typeof openDetail === 'function') {
            try { openDetail(id); return; } catch(err){ console.error('[home catalog.js] openDetail threw', err); }
        }
    } catch(err){ console.error('[home catalog.js] delegated handler error', err); }
}, false);

// Expose openDetail and products to global scope for other scripts/templates
try {
    if (typeof openDetail === 'function') {

        console.log('[home catalog.js] no products array found in window or local');
    }
} catch(e){ console.warn('[home catalog.js] products exposure check failed', e); }

// Global-safe close handler for product detail modal.
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

// Ensure a page load always starts at the top (do not restore previous scroll)
try {
    window.addEventListener('load', function(){
            // Avoid forcing page to top on load.
    });
} catch(e){}

function parsePrice(p){
    if (!p) return 0;
    const n = String(p).replace(/[^0-9.]/g,'');
    return parseFloat(n) || 0;
}

function formatPrice(v){
    if (v === null || typeof v === 'undefined') return '';
    var s = String(v).trim();
    if (s === '') return '';
    if (/^\$/.test(s)) return s;
    return '$ ' + s;
}

function applySort(list, sortVal){
    if (!sortVal) return list.slice();
    const copy = list.slice();
    if (sortVal === 'title_asc'){
        return copy.sort((a,b)=> a.title.localeCompare(b.title, 'es'));
    }
    if (sortVal === 'price_asc'){
        return copy.sort((a,b)=> parsePrice(a.price) - parsePrice(b.price));
    }
    if (sortVal === 'price_desc'){
        return copy.sort((a,b)=> parsePrice(b.price) - parsePrice(a.price));
    }
    return copy;
}

function getFilteredAndSortedProducts(){
    if (!search) search = document.getElementById('search');
    if (!sortBy) sortBy = document.getElementById('sortBy');
    const q = (search && search.value || '').toLowerCase().trim();
    const source = (window && window.products && window.products.length) ? window.products : products;
    const filtered = source.filter(p => (p.title||'').toLowerCase().includes(q) || (p.desc||'').toLowerCase().includes(q));
    const sortVal = (sortBy && sortBy.value) || '';
    return applySort(filtered, sortVal);
}

function openDetail(id){
    console.log('[home catalog.js] openDetail called', id);
    // preserve scroll and blur active element to avoid browser auto-scrolling
    const __saved_scroll = (typeof window.scrollY !== 'undefined') ? window.scrollY : (document.documentElement && document.documentElement.scrollTop) || document.body.scrollTop || 0;
    try { if (document.activeElement && typeof document.activeElement.blur === 'function') document.activeElement.blur(); } catch(e){}
    if (!modal) modal = document.getElementById('detailModal');
    if (!mTitle) mTitle = document.getElementById('m-title');
    if (!mImg) mImg = document.getElementById('m-img');
    if (!mDesc) mDesc = document.getElementById('m-desc');
    if (!mPrice) mPrice = document.getElementById('m-price');
    const source = (window && window.products && window.products.length) ? window.products : products;
    const p = source.find(x=>Number(x.id)===Number(id));
    if(!p) {
        console.warn('[home catalog.js] openDetail: product not found', id);
        return;
    }
    mTitle.textContent = p.title;
    mImg.src = p.img;
    mDesc.textContent = p.desc;
    mPrice.textContent = formatPrice(p.price);
    if (modal) {
        modal.classList.add('show');
        modal.setAttribute('aria-hidden','false');
        try { modal.dataset.productId = id; } catch(e){}
        // Ensure inline styles also make the modal visible in case the template
        // includes an inline `style="display:none"` which overrides CSS rules.
        try {
            if (modal.style) {
                modal.style.display = 'flex';
                modal.style.visibility = 'visible';
                modal.style.opacity = '1';
                modal.style.zIndex = '99999';
            }
            // prevent background scroll while modal open: use overflow hidden only
            try {
                window.__home_saved_scroll = __saved_scroll;
                try {
                    // avoid layout shift when hiding scrollbar by adding equivalent padding
                    const sb = window.innerWidth - document.documentElement.clientWidth;
                    if (sb > 0) {
                        try { document.documentElement.style.paddingRight = sb + 'px'; document.body.style.paddingRight = sb + 'px'; } catch(e){}
                    }
                    try { document.documentElement.style.overflow = 'hidden'; document.body.style.overflow = 'hidden'; } catch(e){}
                } catch(e){}
                // do NOT force-scroll here; rely on overflow:hidden to keep viewport
                // restoration will be attempted on close only when a numeric saved value exists
            } catch(e){}
        } catch(e){}
        console.log('[home catalog.js] modal shown, className=', modal.className, 'display=', (window.getComputedStyle? getComputedStyle(modal).display : (modal.style && modal.style.display)));
        // Always center the inner dialog for consistent UX
        try {
            const inner = modal.querySelector('.detail-modal');
            if (inner && inner.style) {
                try { inner.style.position = 'fixed'; } catch(e){}
                try { inner.style.left = '50%'; } catch(e){}
                try { inner.style.top = '50%'; } catch(e){}
                try { inner.style.transform = 'translate(-50%, -50%)'; } catch(e){}
                try { inner.style.margin = '0'; } catch(e){}
                try { inner.style.maxWidth = Math.min(900, window.innerWidth - 32) + 'px'; } catch(e){}
                try { inner.style.zIndex = '100000'; } catch(e){}
                try { inner.style.animation = 'none'; inner.style.opacity = '1'; } catch(e){}
            }
        } catch(e){}
    } else {
        console.warn('[home catalog.js] modal element not found');
    }
}

if (!mClose) mClose = document.getElementById('m-close');
if (!mBuy) mBuy = document.getElementById('m-buy');
// defensive close/open helpers and guarded listeners
function closeModal() {
    try {
        if (modal) {
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden','true');
            try {
                if (modal.style) modal.style.display = 'none';
                // restore scroll only if a saved numeric position exists
                var saved = null;
                if (typeof window.__home_saved_scroll !== 'undefined' && window.__home_saved_scroll !== null) saved = window.__home_saved_scroll;
                if (saved === null && typeof window.__catalog_saved_scroll !== 'undefined' && window.__catalog_saved_scroll !== null) saved = window.__catalog_saved_scroll;
                try { document.documentElement.style.overflow = ''; document.body.style.overflow = ''; document.documentElement.style.paddingRight = ''; document.body.style.paddingRight = ''; } catch(e){}
                // Keep current viewport position on close; no forced scroll jump.
                try { delete window.__home_saved_scroll; } catch(e){}
                try { delete window.__catalog_saved_scroll; } catch(e){}
            } catch(e){}
        }
    } catch(e){ console.warn('[home catalog.js] closeModal error', e); }
}

try {
    if (mClose) {
        mClose.addEventListener('click', closeModal);
    }
} catch(e){ console.warn('[home catalog.js] mClose listener failed', e); }

try {
    if (modal) {
        modal.addEventListener('click', function(ev){ if (ev.target === modal) closeModal(); });
    }
} catch(e){ /* ignore */ }

// removed legacy blocking alert for mBuy; fallback handled elsewhere in templates/static

if (!search) search = document.getElementById('search');
if (search){
    // No live filtering while the user types. Prevent Enter from triggering anything
    // so the search only runs when the user clicks the `Buscar` button.
    search.addEventListener('keydown', (e)=>{
        if (e.key === 'Enter' || e.keyCode === 13) {
            e.preventDefault();
        }
    });
}

// set default sort to price ascending if none selected
if (!sortBy) sortBy = document.getElementById('sortBy');
if (sortBy && !sortBy.value){
    sortBy.value = 'price_asc';
}

// Event listeners removed - now handled in home.js with category filtering

// When user clicks "Ver catálogo" -> reset search & sort and show all products
if (!viewCatalogBtn) viewCatalogBtn = document.getElementById('viewCatalogBtn');
if (viewCatalogBtn){
    viewCatalogBtn.addEventListener('click', (e)=>{
        e.preventDefault();
        if (search) search.value = '';
        if (sortBy) sortBy.value = 'title_asc';
        // close modal if open
        if (modal){
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden','true');
        }
        // render all products
        render(applySort(products, 'title_asc'));
        // scroll to the grid section
        const gridEl = document.getElementById('grid');
        if (gridEl && gridEl.scrollIntoView) gridEl.scrollIntoView({ behavior: 'smooth' });
    });
}

// Delegated handler for any element with `view` class (works on home and catalog)
document.addEventListener('click', function(e){
    try{
        const el = e.target && e.target.closest ? e.target.closest('.view') : null;
        if (!el) return;
        const id = el.dataset && el.dataset.id ? Number(el.dataset.id) : null;
        if (id === null) return;
        console.log('[home catalog.js] delegated view click for id', id);
        if (typeof openDetail === 'function') {
            try { openDetail(id); return; } catch(err){ console.error('[home catalog.js] openDetail threw', err); }
        }
    } catch(err){ console.error('[home catalog.js] delegated handler error', err); }
}, false);

// Expose openDetail and products to global scope for other scripts/templates
try {
    if (typeof openDetail === 'function') {
        window.openDetail = openDetail;
        console.log('[home catalog.js] exposed openDetail on window');
    }
} catch(e){ console.warn('[home catalog.js] cannot expose openDetail', e); }

try {
    // If server-side provided products exist, prefer them
    if (window.products && window.products.length) {
        console.log('[home catalog.js] window.products present, length=', window.products.length);
    } else if (products && products.length) {
        window.products = products;
        console.log('[home catalog.js] set window.products from local products, length=', products.length);
    } else {
        console.log('[home catalog.js] no products array found in window or local');
    }
} catch(e){ console.warn('[home catalog.js] products exposure check failed', e); }