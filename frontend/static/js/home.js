// home.js - JavaScript para categorías y filtrado en la página home
let currentCategory = '';

function populateCategories(){
    const cats = Array.from(new Set(products.map(p=>p.category).filter(Boolean))).sort((a,b)=> a.localeCompare(b,'es'));
    const container = document.getElementById('sidebarCategories');
    if(!container) return;
    container.innerHTML = '';
    const allBtn = document.createElement('button');
    allBtn.className = 'category-item active';
    allBtn.dataset.cat = '';
    allBtn.textContent = 'Todos';
    container.appendChild(allBtn);
    cats.forEach(c=>{
        const b = document.createElement('button');
        b.className = 'category-item';
        b.dataset.cat = c;
        b.textContent = c;
        container.appendChild(b);
    });

    container.querySelectorAll('.category-item').forEach(b=>{
        b.addEventListener('click', ()=>{
            container.querySelectorAll('.category-item').forEach(x=>x.classList.remove('active'));
            b.classList.add('active');
            currentCategory = b.dataset.cat || '';
            applyFilters();
        });
    });
}

function applyFilters(){
    let list = products.slice();
    const q = (search && search.value || '').toLowerCase().trim();
    if (currentCategory) list = list.filter(p=>p.category === currentCategory);
    if (q) list = list.filter(p=> p.title.toLowerCase().includes(q) || p.desc.toLowerCase().includes(q));
    const sortVal = (sortBy && sortBy.value) || '';
    render(applySort(list, sortVal));
}

// Conectar controles de búsqueda y orden para usar el nuevo flujo de filtros
document.addEventListener('DOMContentLoaded', ()=>{
    populateCategories();
    const sBtn = document.getElementById('searchBtn');
    if (sBtn) sBtn.addEventListener('click', applyFilters);
    if (sortBy) sortBy.addEventListener('change', applyFilters);
    // Render inicial
    applyFilters();
});