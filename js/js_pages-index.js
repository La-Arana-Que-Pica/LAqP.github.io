(async function(){
  const featuredEl = document.getElementById('featured');
  const byCatEl = document.getElementById('pagesByCat');

  // Cargar catálogo (cache-busting)
  const url = '/data/pages.json?v=' + Date.now();
  let pages = [];
  try {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error('HTTP ' + res.status + ' en ' + url);
    const j = await res.json();
    pages = Array.isArray(j.pages) ? j.pages : [];
  } catch (e) {
    console.error('[index] Error cargando', e);
    // Fallback visible (tres tarjetas demo)
    if (featuredEl) {
      featuredEl.innerHTML = [
        {
          title: 'OF última versión',
          description: 'Option File V4 — Premier League actualizada',
          href: 'pages/Descargar/descargar-v4.html',
          thumb: 'img/OF 2025 V4.png',
          cta_text: 'Descargar V4',
          target: '_self'
        },
        {
          title: 'OF complemento',
          description: 'Complemento — Kits y Escudos 2025',
          href: 'pages/Descargar/descargar-complemento.html',
          thumb: 'img/OF COMPLEMENTO.png',
          cta_text: 'Descargar complemento',
          target: '_self'
        },
        {
          title: 'Tutoriales',
          description: 'Guías de instalación y descargas',
          href: 'pages/tutoriales.html',
          thumb: 'img/OF 2025 V4.png',
          cta_text: 'Ver',
          target: '_self'
        }
      ].map((p, i) => cardHTML(p, i)).join('');
    }
    return;
  }

  // Destacadas (hasta 3)
  const featured = pages
    .filter(p => !!p.featured)
    .sort((a,b) => (a.sort_order ?? 999) - (b.sort_order ?? 999))
    .slice(0,3);

  if (featuredEl) {
    featuredEl.innerHTML = featured.length
      ? featured.map((p, i) => cardHTML(p, i)).join('')
      : '<div class="small-card"><div class="content"><div class="meta">Sin destacadas</div><p class="desc">Configurá featured en manage_pages y exportá.</p></div></div>';
  }

  // Catálogo por categorías
  const rest = pages.filter(p => !p.featured);
  const byCat = new Map();
  for (const p of rest) {
    const cat = p.category || 'Otros';
    if (!byCat.has(cat)) byCat.set(cat, []);
    byCat.get(cat).push(p);
  }

  if (byCatEl) {
    byCatEl.innerHTML = '';
    for (const [cat, items] of byCat) {
      items.sort((a,b) => (a.sort_order ?? 999) - (b.sort_order ?? 999) || (a.title || '').localeCompare(b.title || '', 'es'));
      const cards = items.map(p => `
        <div class="tarjeta-seccion">
          <div>
            <div class="icon"></div>
            <h3>${p.title || p.slug || p.href}</h3>
            <p class="desc" style="color:#cfecec">${p.description || ''}</p>
          </div>
          <a class="tarjeta-btn" href="${p.href || '#'}" ${p.target==='_blank'?'target="_blank" rel="noopener"':''}>${p.cta_text || 'Abrir'}</a>
        </div>
      `).join('');
      const group = document.createElement('div');
      group.className = 'panel-secciones';
      group.innerHTML = `
        <h2 class="page-title" style="font-size:1.1rem;margin-top:16px">${cat}</h2>
        <div class="panel-secciones">${cards}</div>
      `;
      byCatEl.appendChild(group);
    }
  }

  function cardHTML(p, i){
    return `
      <div class="small-card" role="article" aria-labelledby="mini-${i + 1}">
        <div class="thumb" style="background-image:url('${p.thumb || 'img/OF 2025 V4.png'}');" aria-hidden="true"></div>
        <div class="content">
          <div id="mini-${i + 1}" class="meta">${p.title || p.slug || 'Página'}</div>
          <p class="desc">${p.description || ''}</p>
          <a class="btn" href="${p.href || '#'}" ${p.target==='_blank'?'target="_blank" rel="noopener"':''}>${p.cta_text || 'Abrir'}</a>
        </div>
      </div>
    `;
  }
})();