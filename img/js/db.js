// Utilidades compartidas para la base de datos (fetch, mapas, helpers)
window.DB = (function(){
  const cache = {};

  function slugify(str){
    if(!str) return '';
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g,'')
      .toLowerCase().trim()
      .replace(/[^a-z0-9\s-]/g,'')
      .replace(/\s+/g,'-')
      .replace(/-+/g,'-');
  }

  // Para banderas: nombre_del_pais.png (sin acentos, espacios -> _, minúsculas)
  function countryToFile(country){
    if(!country) return 'unknown';
    const s = country.normalize('NFD').replace(/[\u0300-\u036f]/g,'')
      .toLowerCase().trim()
      .replace(/[^a-z0-9\s_-]/g,'')
      .replace(/\s+/g,'_')
      .replace(/_+/g,'_');
    return s || 'unknown';
  }

  function countryFlagSrc(country){
    return `img/flags/${countryToFile(country)}.png`;
  }

  function ageFromBirthDate(dateStr){
    if(!dateStr) return NaN;
    const d = new Date(dateStr+'T00:00:00Z');
    if(isNaN(d.getTime())) return NaN;
    const now = new Date();
    let age = now.getUTCFullYear() - d.getUTCFullYear();
    const m = now.getUTCMonth() - d.getUTCMonth();
    if(m < 0 || (m === 0 && now.getUTCDate() < d.getUTCDate())) age--;
    return age;
  }

  function getParam(name){
    const u = new URL(window.location.href);
    return u.searchParams.get(name);
  }

  function debounce(fn, ms){ let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn.apply(null,args),ms); }; }

  async function fetchJSON(path){
    if(cache[path]) return cache[path];
    const r = await fetch(path, { cache: 'no-store' });
    if(!r.ok) throw new Error('No se pudo cargar '+path);
    const j = await r.json();
    cache[path] = j;
    return j;
  }

  async function load(opts){
    const out = {};
    const promises = [];
    if(opts.leagues){ promises.push(fetchJSON('data/ligas.json').then(v=> out.leagues=v)); }
    if(opts.teams){ promises.push(fetchJSON('data/equipos.json').then(v=> out.teams=v)); }
    if(opts.players){ promises.push(fetchJSON('data/jugadores.json').then(v=> out.players=v)); }
    await Promise.all(promises);

    // Mapas útiles
    const maps = { leagueById:{}, teamById:{}, leagueBySlug:{}, teamBySlug:{}, playerBySlug:{} };
    if(out.leagues){
      for(const l of out.leagues){ maps.leagueById[l.id]=l; maps.leagueBySlug[l.slug]=l; }
    }
    if(out.teams){
      for(const t of out.teams){ maps.teamById[t.id]=t; maps.teamBySlug[t.slug]=t; }
    }
    if(out.players){
      for(const p of out.players){ maps.playerBySlug[p.slug]=p; }
    }
    out.maps = maps;
    return out;
  }

  return { slugify, countryFlagSrc, ageFromBirthDate, getParam, debounce, load };
})();