/* Utilidades de datos para LAqP: carga JSON, helpers y mapas en memoria */
window.DB = (function(){
  const log = (...a)=>console.log('[DB]', ...a);

  function normPath(s){
    if(!s) return '';
    return (''+s).replace(/\\\\/g,'/').replace(/\\/g,'/');
  }

  function countryLabel(s){
    if(!s) return '';
    let x = normPath(''+s).trim();
    if(x.includes('/')) x = x.split('/').pop();
    x = x.replace(/\.(png|jpg|jpeg)$/i,'').replace(/[_-]+/g,' ');
    return x.length<=3 ? x.toUpperCase() : x.split(' ').map(w=>w? (w[0].toUpperCase()+w.slice(1)) : w).join(' ');
  }

  function countryFlagSrc(input){
    if(!input) return 'img/flags/unknown.png';
    const s = normPath(''+input).trim();
    if(/\.(png|jpg|jpeg)$/i.test(s)){
      const cleaned = s.replace(/^\.?\/*/,''); 
      return cleaned.startsWith('img/') ? cleaned : `img/${cleaned}`;
    }
    const file = s.normalize('NFD').replace(/[\u0300-\u036f]/g,'')
      .toLowerCase().trim().replace(/[^a-z0-9\s_-]/g,'').replace(/\s+/g,'_').replace(/_+/g,'_') || 'unknown';
    return `img/flags/${file}.png`;
  }

  // Acepta 'YYYY-MM-DD' o 'DD/MM/YYYY'
  function ageFromBirthDate(s){
    if(!s) return NaN;
    const str = (''+s).trim();
    let d;
    let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str);
    if(m){ d = new Date(Number(m[1]), Number(m[2])-1, Number(m[3])); }
    else {
      m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(str);
      if(m){ d = new Date(Number(m[3]), Number(m[2])-1, Number(m[1])); }
    }
    if(!d || Number.isNaN(d.getTime())) return NaN;
    const now = new Date();
    let age = now.getFullYear() - d.getFullYear();
    const md = now.getMonth() - d.getMonth();
    if(md<0 || (md===0 && now.getDate()<d.getDate())) age--;
    return age;
  }

  async function fetchJsonMulti(paths){
    let lastError;
    for(const p of paths){
      try{
        const res = await fetch(p, {cache:'no-store', headers:{'Accept':'application/json'}});
        if(!res.ok){ lastError = new Error(`HTTP ${res.status} al cargar ${p}`); continue; }
        return await res.json();
      }catch(e){ lastError = e; }
    }
    throw lastError || new Error('No se pudo cargar JSON');
  }

  async function load({leagues=false, teams=false, players=false}={}){
    const base = location.pathname.replace(/[^/]+$/,'');
    const rel = (file)=>[`data/${file}`, `${base}data/${file}`, `./data/${file}`, `/data/${file}`, `../data/${file}`, `${base}../data/${file}`];
    const out={};
    if(leagues){ out.leagues = await fetchJsonMulti(rel('ligas.json')); }
    if(teams){ out.teams = await fetchJsonMulti(rel('equipos.json')); }
    if(players){ out.players = await fetchJsonMulti(rel('jugadores.json')); }
    const maps = {};
    if(out.leagues){ maps.leagueById = Object.fromEntries(out.leagues.map(l=>[String(l.id), l])); maps.leagueBySlug = Object.fromEntries(out.leagues.map(l=>[l.slug, l])); }
    if(out.teams){ maps.teamById = Object.fromEntries(out.teams.map(t=>[String(t.id), t])); maps.teamBySlug = Object.fromEntries(out.teams.map(t=>[t.slug, t])); }
    if(out.players){ maps.playerById = Object.fromEntries(out.players.map(p=>[String(p.id), p])); maps.playerBySlug = Object.fromEntries(out.players.map(p=>[p.slug, p])); }
    out.maps = maps;
    log('Cargado', {leagues: out.leagues?.length||0, teams: out.teams?.length||0, players: out.players?.length||0});
    return out;
  }

  function getParam(name){ return new URL(location.href).searchParams.get(name); }
  function debounce(fn, wait=150){ let t=null; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), wait); }; }

  return { load, getParam, debounce, ageFromBirthDate, countryFlagSrc, normPath, countryLabel };
})();