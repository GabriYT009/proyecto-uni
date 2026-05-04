let products = [];

let grid;
let search;
let sortBy;
let modal;
let mTitle;
let mImg;
let mDesc;
let mPrice;
let mClose;
let mBuy;
let viewCatalogBtn;

function getProductsSource() {
    return (window && window.products && window.products.length) ? window.products : products;
}

function parsePrice(value) {
    if (!value) return 0;
    const normalized = String(value).replace(/[^0-9.]/g, '');
    return parseFloat(normalized) || 0;
}

function formatPrice(value) {
    if (value === null || typeof value === 'undefined') return '';
    const normalized = String(value).trim();
    if (!normalized) return '';
    return /^\$/.test(normalized) ? normalized : '$ ' + normalized;
}

function applySort(list, sortValue) {
    if (!sortValue) return list.slice();
    const copy = list.slice();

    if (sortValue === 'title_asc') {
        return copy.sort((left, right) => left.title.localeCompare(right.title, 'es'));
    }
    if (sortValue === 'price_asc') {
        return copy.sort((left, right) => parsePrice(left.price) - parsePrice(right.price));
    }
    if (sortValue === 'price_desc') {
        return copy.sort((left, right) => parsePrice(right.price) - parsePrice(left.price));
    }
    return copy;
}

function render(list) {
    if (!grid) grid = document.getElementById('grid');
    if (!grid) return;

    grid.innerHTML = '';
    if (!list.length) {
        grid.innerHTML = '<p style="color:#fff">No hay productos.</p>';
        return;
    }

    list.forEach((product) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <img src="${product.img}" alt="${product.title}" class="view" data-id="${product.id}">
            <h4 class="view" data-id="${product.id}">${product.title}</h4>
            <small>${product.category || ''}</small>
            <p>${product.desc || ''}</p>
            <div class="row">
                <strong>${formatPrice(product.price)}</strong>
            </div>
        `;
        grid.appendChild(card);
    });
}

function closeModal() {
    if (!modal) modal = document.getElementById('detailModal');
    if (!modal) return;

    modal.classList.remove('show');
    modal.setAttribute('aria-hidden', 'true');
    if (modal.style) modal.style.display = 'none';
}

function openDetail(id) {
    console.log('[home catalog.js] openDetail called', id);

    if (!modal) modal = document.getElementById('detailModal');
    if (!mTitle) mTitle = document.getElementById('m-title');
    if (!mImg) mImg = document.getElementById('m-img');
    if (!mDesc) mDesc = document.getElementById('m-desc');
    if (!mPrice) mPrice = document.getElementById('m-price');

    const product = getProductsSource().find((item) => Number(item.id) === Number(id));
    if (!product || !modal) {
        console.warn('[home catalog.js] openDetail: product or modal not found', id);
        return;
    }

    const productCategory = String(product.category || product.Categoria || '').trim();
    const normalizedCategory = productCategory
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase();
    if (normalizedCategory === 'camisas' || normalizedCategory === 'tazas' || normalizedCategory === 'sublimacion') {
        window.location.href = '/producto/' + id + '/camisas/';
        return;
    }

    mTitle.textContent = product.title || '';
    mImg.src = product.img || '/static/assets/img/logo.png';
    mImg.onerror = function() {
        this.onerror = null;
        this.src = '/static/assets/img/logo.png';
    };
    mDesc.textContent = product.desc || '';
    mPrice.textContent = formatPrice(product.price);

    modal.dataset.productId = String(id);
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');
    if (modal.style) {
        modal.style.display = 'flex';
        modal.style.visibility = 'visible';
        modal.style.opacity = '1';
        modal.style.zIndex = '99999';
    }

    window.currentProductId = String(id);
    console.log('[home catalog.js] modal shown, className=', modal.className, 'display=', window.getComputedStyle ? getComputedStyle(modal).display : modal.style.display);
}

function bindStaticProducts() {
    const serverProducts = getProductsSource();
    if (!serverProducts.length) {
        console.log('[home catalog.js] no products array found in window or local');
        return;
    }

    document.addEventListener('DOMContentLoaded', function() {
        serverProducts.forEach((product) => {
            const elements = document.querySelectorAll('[data-id="' + product.id + '"]');
            elements.forEach((element) => {
                if (!element.classList.contains('view')) element.classList.add('view');
                if (!element.dataset.title) element.dataset.title = product.title || '';
                if (!element.dataset.img) element.dataset.img = product.img || '';
                if (!element.dataset.desc) element.dataset.desc = product.desc || '';
                if (!element.dataset.price) element.dataset.price = product.price || '';
            });
        });
        console.log('[home catalog.js] bound', serverProducts.length, 'products to DOM');
    });
}

if (!search) search = document.getElementById('search');
if (search) {
    search.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.keyCode === 13) {
            event.preventDefault();
        }
    });
}

if (!sortBy) sortBy = document.getElementById('sortBy');
if (sortBy && !sortBy.value) {
    sortBy.value = 'price_asc';
}

if (!viewCatalogBtn) viewCatalogBtn = document.getElementById('viewCatalogBtn');
if (viewCatalogBtn) {
    viewCatalogBtn.addEventListener('click', function(event) {
        event.preventDefault();
        if (search) search.value = '';
        if (sortBy) sortBy.value = 'title_asc';
        closeModal();
        render(applySort(getProductsSource(), 'title_asc'));
        const gridElement = document.getElementById('grid');
        if (gridElement && gridElement.scrollIntoView) {
            gridElement.scrollIntoView({ behavior: 'smooth' });
        }
    });
}

document.addEventListener('click', function(event) {
    const trigger = event.target && event.target.closest ? event.target.closest('.view, .card[data-id]') : null;
    if (!trigger) return;

    const idFromTrigger = trigger.dataset && trigger.dataset.id ? Number(trigger.dataset.id) : null;
    const parentCard = trigger.closest ? trigger.closest('.card[data-id]') : null;
    const idFromCard = parentCard && parentCard.dataset && parentCard.dataset.id ? Number(parentCard.dataset.id) : null;
    const id = Number.isFinite(idFromTrigger) ? idFromTrigger : (Number.isFinite(idFromCard) ? idFromCard : null);
    if (id === null) return;

    event.preventDefault();
    event.stopPropagation();
    console.log('[home catalog.js] delegated view click for id', id);
    openDetail(id);
}, true);

document.addEventListener('keydown', function(event) {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const trigger = event.target && event.target.closest ? event.target.closest('.card[data-id], .view[data-id]') : null;
    if (!trigger) return;

    const id = trigger.dataset && trigger.dataset.id ? Number(trigger.dataset.id) : null;
    if (!Number.isFinite(id)) return;

    event.preventDefault();
    openDetail(id);
}, true);

(function bindModalClose() {
    if (window.__detailModalGlobalCloseBound) return;
    window.__detailModalGlobalCloseBound = true;

    document.addEventListener('click', function(event) {
        if (event.target && event.target.closest && event.target.closest('.view, .card[data-id]')) return;

        const modalElement = document.getElementById('detailModal');
        if (!modalElement || !modalElement.classList.contains('show')) return;

        const inner = modalElement.querySelector('.detail-modal') || modalElement.querySelector('.modal');
        if (event.target === modalElement || (inner && !inner.contains(event.target))) {
            closeModal();
        }
    }, true);

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });
})();

if (!mClose) mClose = document.getElementById('m-close');
if (mClose) {
    mClose.addEventListener('click', function(event) {
        event.preventDefault();
        closeModal();
    });
}

if (!mBuy) mBuy = document.getElementById('m-buy');
if (mBuy) {
    mBuy.addEventListener('click', function(event) {
        event.preventDefault();
        const id = window.currentProductId || (document.getElementById('detailModal') && document.getElementById('detailModal').dataset.productId);
        if (id) window.location.href = '/producto/' + id + '/comprar/';
    });
}

try {
    if (typeof openDetail === 'function') {
        window.openDetail = openDetail;
        console.log('[home catalog.js] exposed openDetail on window');
    }

    if (window.products && window.products.length) {
        console.log('[home catalog.js] window.products present, length=', window.products.length);
    } else if (products && products.length) {
        window.products = products;
        console.log('[home catalog.js] set window.products from local products, length=', products.length);
    } else {
        console.log('[home catalog.js] no products array found in window or local');
    }
} catch (error) {
    console.warn('[home catalog.js] initialization warning', error);
}

bindStaticProducts();
