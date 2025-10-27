#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de base de datos (Ligas, Equipos, Jugadores) con menú interactivo.
- Fuente de verdad: CSV en data/ligas.csv, data/equipos.csv, data/jugadores.csv
- Exporta JSON para la web: data/ligas.json, data/equipos.json, data/jugadores.json
- Genera páginas estáticas por jugador: players/<slug>.html (build)
- Slugs únicos por entidad (URLs tipo ?slug= o players/<slug>.html)
- Validaciones:
  - Jugadores.rating: 40..99
  - Jugadores.position: {Arquero, Defensor, Mediocampista, Delantero}
  - birth_date: YYYY-MM-DD
  - team_id y league_id deben existir (equipos pueden quedar sin liga)
- Borrados:
  - Liga: no se borran equipos; se “desasigna” (league_id vacío)
  - Equipo: bloqueado si tiene jugadores
- Backups automáticos en backups/

Uso rápido:
  python manage_db.py            # menú interactivo
  python manage_db.py export     # exporta JSON
  python manage_db.py build      # genera páginas estáticas de jugadores
"""
import csv
import argparse
import sys
from datetime import datetime
import json
from pathlib import Path
import shutil
import re
import unicodedata

DATA_DIR = Path('data')
BACKUP_DIR = Path('backups')
PLAYERS_DIR = Path('players')
TEMPLATES_DIR = Path('templates')

LEAGUES_CSV = DATA_DIR / 'ligas.csv'
TEAMS_CSV = DATA_DIR / 'equipos.csv'
PLAYERS_CSV = DATA_DIR / 'jugadores.csv'

LEAGUES_JSON = DATA_DIR / 'ligas.json'
TEAMS_JSON = DATA_DIR / 'equipos.json'
PLAYERS_JSON = DATA_DIR / 'jugadores.json'

ALLOWED_POSITIONS = ['Arquero','Defensor','Mediocampista','Delantero']

def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    PLAYERS_DIR.mkdir(exist_ok=True)
    TEMPLATES_DIR.mkdir(exist_ok=True)

def backup_all():
    ensure_dirs()
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    paths = [LEAGUES_CSV, TEAMS_CSV, PLAYERS_CSV]
    made = []
    for p in paths:
        if p.exists():
            dst = BACKUP_DIR / f"{p.stem}_{ts}{p.suffix}"
            shutil.copy2(p, dst)
            made.append(dst)
    return made

def read_csv(path):
    if not path.exists(): return []
    with path.open(newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]

def write_csv(path, rows, headers):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k,'') for k in headers})

def next_id(rows):
    ids = [int(r['id']) for r in rows if str(r.get('id','')).isdigit()]
    return str(max(ids)+1 if ids else 1)

def slugify(s: str) -> str:
    s = (s or '').strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s).strip('-')
    s = re.sub(r'-+', '-', s)
    return s

def unique_slug(base, existing_slugs):
    s = slugify(base)
    if s == '': s = 'item'
    if s not in existing_slugs: return s
    i = 2
    while f"{s}-{i}" in existing_slugs:
        i += 1
    return f"{s}-{i}"

def valid_date(s):
    try:
        datetime.strptime(s, '%Y-%m-%d')
        return True
    except Exception:
        return False

def country_to_file(country: str) -> str:
    if not country: return 'unknown'
    s = unicodedata.normalize('NFD', country)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9\s_-]', '', s)
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s or 'unknown'

def load_all():
    leagues = read_csv(LEAGUES_CSV)
    teams = read_csv(TEAMS_CSV)
    players = read_csv(PLAYERS_CSV)
    # Normalizar
    for l in leagues:
        l['id'] = str(l.get('id','')).strip()
        l['name'] = l.get('name','').strip()
        l['country'] = l.get('country','').strip()
        l['logo'] = l.get('logo','').strip()
        l['slug'] = l.get('slug','').strip()
    for t in teams:
        t['id'] = str(t.get('id','')).strip()
        t['name'] = t.get('name','').strip()
        t['league_id'] = str(t.get('league_id','')).strip()
        t['logo'] = t.get('logo','').strip()
        t['slug'] = t.get('slug','').strip()
    for p in players:
        p['id'] = str(p.get('id','')).strip()
        p['first_name'] = p.get('first_name','').strip()
        p['last_name'] = p.get('last_name','').strip()
        p['birth_date'] = p.get('birth_date','').strip()
        p['team_id'] = str(p.get('team_id','')).strip()
        p['country'] = p.get('country','').strip()
        p['photo'] = p.get('photo','').strip()
        p['position'] = p.get('position','').strip()
        try:
            p['rating'] = int(p.get('rating', '') or 0)
        except:
            p['rating'] = 0
        p['sofifa_url'] = p.get('sofifa_url','').strip()
        p['face_video_url'] = p.get('face_video_url','').strip()
        p['slug'] = p.get('slug','').strip()
    return leagues, teams, players

def save_all(leagues, teams, players):
    write_csv(LEAGUES_CSV, leagues, ['id','name','country','logo','slug'])
    write_csv(TEAMS_CSV, teams, ['id','name','league_id','logo','slug'])
    write_csv(PLAYERS_CSV, players, ['id','first_name','last_name','birth_date','team_id','country','photo','position','rating','sofifa_url','face_video_url','slug'])

def validate(leagues, teams, players, verbose=True):
    ok = True
    league_ids = {l['id'] for l in leagues}
    team_ids = {t['id'] for t in teams}
    # Slugs únicos
    if len({l['slug'] for l in leagues if l['slug']}) != len(leagues):
        ok = False; 
        if verbose: print("Ligas: slugs duplicados")
    if len({t['slug'] for t in teams if t['slug']}) != len(teams):
        ok = False; 
        if verbose: print("Equipos: slugs duplicados")
    if len({p['slug'] for p in players if p['slug']}) != len(players):
        ok = False; 
        if verbose: print("Jugadores: slugs duplicados")
    # Referencias y campos
    for t in teams:
        if t['league_id'] and t['league_id'] not in league_ids:
            ok = False
            if verbose: print(f"Equipo {t['name']} con league_id inexistente: {t['league_id']}")
    for p in players:
        if p['team_id'] and p['team_id'] not in team_ids:
            ok = False
            if verbose: print(f"Jugador {p['first_name']} {p['last_name']} con team_id inexistente: {p['team_id']}")
        if p['position'] and p['position'] not in ALLOWED_POSITIONS:
            ok = False
            if verbose: print(f"Jugador {p['first_name']} {p['last_name']} posición inválida: {p['position']}")
        if p['rating'] and not (40 <= int(p['rating']) <= 99):
            ok = False
            if verbose: print(f"Jugador {p['first_name']} {p['last_name']} rating fuera de rango: {p['rating']}")
        if p['birth_date'] and not valid_date(p['birth_date']):
            ok = False
            if verbose: print(f"Jugador {p['first_name']} {p['last_name']} fecha inválida: {p['birth_date']}")
    if verbose:
        print("Validación OK" if ok else "Validación con problemas")
    return ok

def export_json(leagues, teams, players):
    with LEAGUES_JSON.open('w', encoding='utf-8') as f:
        json.dump(leagues, f, ensure_ascii=False, indent=2)
    with TEAMS_JSON.open('w', encoding='utf-8') as f:
        json.dump(teams, f, ensure_ascii=False, indent=2)
    with PLAYERS_JSON.open('w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=2)
    print("Exportado JSON a data/*.json")

def read_player_template():
    ensure_dirs()
    tpl_path = TEMPLATES_DIR / 'player.html'
    if tpl_path.exists():
        return tpl_path.read_text(encoding='utf-8')
    # Plantilla mínima por defecto si no existe el archivo
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <link href="https://fonts.googleapis.com/css2?family=Bungee&family=Press+Start+2P&family=Roboto:wght@400;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../style.css">
  <style>
    .layout{{display:grid;grid-template-columns:120px 1fr;gap:16px;align-items:start;margin-top:16px}}
    .photo{{width:120px;height:120px;border-radius:14px;object-fit:cover;border:1px solid rgba(255,255,255,.08)}}
    .flag{{width:24px;height:18px;object-fit:cover;border-radius:2px;margin-left:8px;vertical-align:middle}}
    .badge{{display:inline-block;border-radius:8px;padding:6px 10px;background:linear-gradient(90deg,var(--neon-cyan),var(--neon-pink));color:#071014;font-weight:700;margin-left:8px}}
    .box{{background:linear-gradient(180deg,rgba(10,10,12,.96),rgba(20,16,24,.96));border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:12px}}
    a.clean{{color:#7afcff;text-decoration:none}}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="site-header">
      <div class="brand">
        <div class="logo" aria-hidden="true"></div>
        <h1><a href="../index.html" class="clean" style="color:inherit;text-decoration:none">LAqP</a></h1>
      </div>
      <nav class="main-nav">
        <a href="../ligas.html">Ligas</a>
        <a href="../equipos.html">Equipos</a>
        <a href="../jugadores.html">Jugadores</a>
      </nav>
    </header>

    <div class="layout">
      <img class="photo" src="../{photo}" alt="{full_name}" onerror="this.src='../img/jugadores/placeholder.png'">
      <div>
        <div class="page-title" style="margin:0">{full_name}
          <span class="badge">{rating}</span>
        </div>
        <div class="box" style="margin-top:10px">
          <div><strong>Posición:</strong> {position}</div>
          <div><strong>Nacimiento:</strong> {birth_date} {age_text}</div>
          <div><strong>Equipo:</strong> {team_link}</div>
          <div><strong>Liga:</strong> {league_link}</div>
          <div><strong>País:</strong> {country} {flag_img}</div>
          <div style="margin-top:10px">{sofifa_link} {face_video_link}</div>
        </div>
      </div>
    </div>

    <footer class="site-footer">© La Araña Que Pica — Página Oficial</footer>
  </div>
</body>
</html>"""

def build_player_pages(leagues, teams, players):
    ensure_dirs()
    template = read_player_template()

    league_by_id = {l['id']: l for l in leagues}
    team_by_id = {t['id']: t for t in teams}

    count = 0
    for p in players:
        full_name = f"{p['first_name']} {p['last_name']}".strip()
        # edad
        age_text = ''
        try:
            d = datetime.strptime(p['birth_date'], '%Y-%m-%d')
            now = datetime.utcnow()
            age = now.year - d.year - ((now.month, now.day) < (d.month, d.day))
            age_text = f"({age} años)"
        except Exception:
            age_text = ''

        t = team_by_id.get(p['team_id']) if p.get('team_id') else None
        l = league_by_id.get(t['league_id']) if t and t.get('league_id') else None

        team_link = f"<a class='clean' href='../equipo.html?slug={t['slug']}'>{t['name']}</a>" if t else "Sin equipo"
        league_link = f"<a class='clean' href='../liga.html?slug={l['slug']}'>{l['name']}</a>" if l else "—"

        flag_src = f"img/flags/{country_to_file(p['country'])}.png"
        flag_img = f"<img class='flag' src='../{flag_src}' alt='{p['country']}' onerror=\"this.style.display='none'\">" if p.get('country') else ''

        sofifa_link = f"<a class='clean' href='{p['sofifa_url']}' target='_blank' rel='noopener'>Ver en SoFIFA</a>" if p.get('sofifa_url') else ""
        face_video_link = f"<a class='clean' href='{p['face_video_url']}' target='_blank' rel='noopener' style='margin-left:12px'>Video de cara</a>" if p.get('face_video_url') else ""

        html = template.format(
            title=f"{full_name} — LAQP",
            full_name=full_name or "Jugador",
            rating=p.get('rating', '') or '',
            photo=p.get('photo') or 'img/jugadores/placeholder.png',
            position=p.get('position') or '-',
            birth_date=p.get('birth_date') or '',
            age_text=age_text,
            team_link=team_link,
            league_link=league_link,
            country=p.get('country') or '',
            flag_img=flag_img,
            sofifa_link=sofifa_link,
            face_video_link=face_video_link,
        )

        out_path = PLAYERS_DIR / f"{p['slug']}.html"
        out_path.write_text(html, encoding='utf-8')
        count += 1

    print(f"Generadas {count} páginas en {PLAYERS_DIR}/")

def export_cmd():
    leagues, teams, players = load_all()
    if not validate(leagues, teams, players, verbose=True):
        ans = input("Validación con problemas. Exportar igual? (s/N): ").strip().lower()
        if ans != 's':
            return
    export_json(leagues, teams, players)

def build_cmd():
    leagues, teams, players = load_all()
    if not validate(leagues, teams, players, verbose=True):
        ans = input("Validación con problemas. Continuar build? (s/N): ").strip().lower()
        if ans != 's':
            return
    build_player_pages(leagues, teams, players)

def prompt(msg, default=None, required=False, validator=None):
    while True:
        if default:
            val = input(f"{msg} [{default}]: ").strip()
            if val == '': val = default
        else:
            val = input(f"{msg}: ").strip()
        if required and val == '':
            print("Campo requerido.")
            continue
        if validator:
            ok, err = validator(val)
            if not ok:
                print(err); continue
        return val

def pick_from(rows, label_key='name'):
    for r in rows:
        print(f"{r['id']}: {r[label_key]}")
    return input("Ingresa id (o vacío para cancelar): ").strip()

def ensure_slug_entity(name, existing_slugs):
    return unique_slug(name, set(s for s in existing_slugs if s))

def interactive_menu():
    print("=== Gestor LAQP — Menú ===")
    actions = [
        ("Ligas: listar / buscar", menu_list_leagues),
        ("Ligas: añadir", menu_add_league),
        ("Ligas: editar", menu_edit_league),
        ("Ligas: eliminar (desasigna equipos)", menu_delete_league),
        ("Equipos: listar / buscar", menu_list_teams),
        ("Equipos: añadir", menu_add_team),
        ("Equipos: editar", menu_edit_team),
        ("Equipos: eliminar (bloquea si tiene jugadores)", menu_delete_team),
        ("Jugadores: listar / buscar", menu_list_players),
        ("Jugadores: añadir", menu_add_player),
        ("Jugadores: editar", menu_edit_player),
        ("Jugadores: eliminar", menu_delete_player),
        ("Validar base", lambda: validate(*load_all())),
        ("Exportar JSON", export_cmd),
        ("Generar páginas de jugadores (build)", build_cmd),
        ("Backup CSV", menu_backup),
        ("Salir", lambda: sys.exit(0)),
    ]
    while True:
        print()
        for i,(t,_) in enumerate(actions,1):
            print(f"{i}) {t}")
        ch = input("Opción: ").strip()
        if not ch.isdigit() or not (1 <= int(ch) <= len(actions)):
            print("Opción inválida"); continue
        try:
            actions[int(ch)-1][1]()
        except KeyboardInterrupt:
            print("\n(Cancelado)")
        except Exception as e:
            print("Error:", e)

# --- Ligas ---
def menu_list_leagues():
    leagues, _, _ = load_all()
    q = input("Buscar (nombre/país, vacío para listar todo): ").strip().lower()
    rows = [l for l in leagues if q in (l['name']+' '+l['country']).lower()] if q else leagues
    rows = sorted(rows, key=lambda l: l['name'])
    for l in rows:
        print(f"{l['id']}: {l['name']} — {l['country']} (slug: {l['slug']})")

def menu_add_league():
    leagues, _, _ = load_all()
    name = prompt("Nombre de liga", required=True)
    country = prompt("País", required=True)
    logo = prompt("Ruta logo (img/ligas/...)", default="img/ligas/placeholder.png")
    slug = ensure_slug_entity(name, [l['slug'] for l in leagues])
    l = {'id': next_id(leagues), 'name': name, 'country': country, 'logo': logo, 'slug': slug}
    backup_all()
    leagues.append(l)
    save_all(leagues, *load_all()[1:])
    print("Liga añadida:", l['id'], l['name'])

def menu_edit_league():
    leagues, teams, players = load_all()
    lid = pick_from(sorted(leagues, key=lambda l:l['name']))
    if not lid: return
    l = next((x for x in leagues if x['id']==lid), None)
    if not l: print("No encontrada"); return
    name = prompt("Nombre", default=l['name'], required=True)
    country = prompt("País", default=l['country'], required=True)
    logo = prompt("Logo", default=l['logo'] or "img/ligas/placeholder.png")
    if name != l['name']:
        l['slug'] = ensure_slug_entity(name, [x['slug'] for x in leagues if x['id']!=l['id']])
    l['name']=name; l['country']=country; l['logo']=logo
    backup_all()
    save_all(leagues, teams, players)
    print("Liga actualizada.")

def menu_delete_league():
    leagues, teams, players = load_all()
    lid = pick_from(sorted(leagues, key=lambda l:l['name']))
    if not lid: return
    l = next((x for x in leagues if x['id']==lid), None)
    if not l: print("No encontrada"); return
    print(f"Eliminará la liga '{l['name']}' y desasignará {sum(1 for t in teams if t['league_id']==lid)} equipos.")
    if input("Confirmar? (s/N): ").strip().lower()!='s': return
    backup_all()
    leagues = [x for x in leagues if x['id']!=lid]
    for t in teams:
        if t['league_id']==lid:
            t['league_id']=''
    save_all(leagues, teams, players)
    print("Liga eliminada y equipos desasignados.")

# --- Equipos ---
def menu_list_teams():
    leagues, teams, _ = load_all()
    lid_name = {l['id']:l['name'] for l in leagues}
    q = input("Buscar (nombre, vacío para todo): ").strip().lower()
    rows = [t for t in teams if q in t['name'].lower()] if q else teams
    for t in sorted(rows, key=lambda t:t['name']):
        print(f"{t['id']}: {t['name']} — {lid_name.get(t['league_id'],'Sin liga')} (slug: {t['slug']})")

def menu_add_team():
    leagues, teams, players = load_all()
    name = prompt("Nombre de equipo", required=True)
    print("Liga (opcional):")
    lid = pick_from(sorted(leagues, key=lambda l:l['name'])) or ''
    logo = prompt("Ruta logo (img/equipos/...)", default="img/equipos/placeholder.png")
    slug = ensure_slug_entity(name, [t['slug'] for t in teams])
    t = {'id': next_id(teams), 'name': name, 'league_id': lid, 'logo': logo, 'slug': slug}
    backup_all()
    teams.append(t)
    save_all(leagues, teams, players)
    print("Equipo añadido:", t['id'], t['name'])

def menu_edit_team():
    leagues, teams, players = load_all()
    tid = pick_from(sorted(teams, key=lambda t:t['name']))
    if not tid: return
    t = next((x for x in teams if x['id']==tid), None)
    if not t: print("No encontrado"); return
    name = prompt("Nombre", default=t['name'], required=True)
    print("Seleccionar liga (opcional):")
    lid = pick_from(sorted(leagues, key=lambda l:l['name'])) or ''
    logo = prompt("Logo", default=t['logo'] or "img/equipos/placeholder.png")
    if name != t['name']:
        t['slug'] = ensure_slug_entity(name, [x['slug'] for x in teams if x['id']!=t['id']])
    t['name']=name; t['league_id']=lid; t['logo']=logo
    backup_all()
    save_all(leagues, teams, players)
    print("Equipo actualizado.")

def menu_delete_team():
    leagues, teams, players = load_all()
    tid = pick_from(sorted(teams, key=lambda t:t['name']))
    if not tid: return
    t = next((x for x in teams if x['id']==tid), None)
    if not t: print("No encontrado"); return
    cnt = sum(1 for p in players if p['team_id']==tid)
    if cnt>0:
        print(f"Bloqueado: el equipo tiene {cnt} jugadores. Reasigna o elimina jugadores antes.")
        return
    if input(f"Confirmar eliminación de '{t['name']}'? (s/N): ").strip().lower()!='s': return
    backup_all()
    teams = [x for x in teams if x['id']!=tid]
    save_all(leagues, teams, players)
    print("Equipo eliminado.")

# --- Jugadores ---
def menu_list_players():
    leagues, teams, players = load_all()
    team_name = {t['id']:t['name'] for t in teams}
    q = input("Buscar (nombre/apellido, vacío para todo): ").strip().lower()
    rows = [p for p in players if q in (p['first_name']+' '+p['last_name']).lower()] if q else players
    rows = sorted(rows, key=lambda p:(-int(p['rating'] or 0), p['last_name'], p['first_name']))
    for p in rows[:200]:
        print(f"{p['id']}: {p['first_name']} {p['last_name']} — {team_name.get(p['team_id'],'Sin equipo')} — {p['position']} — {p['rating']} (slug: {p['slug']})")
    if len(rows)>200: print(f"... {len(rows)-200} más")

def menu_add_player():
    leagues, teams, players = load_all()
    first = prompt("Nombre", required=True)
    last = prompt("Apellido", required=True)
    birth = prompt("Fecha nacimiento (YYYY-MM-DD)", required=True, validator=lambda v: (valid_date(v),"Fecha inválida (YYYY-MM-DD)"))
    print("Elegir equipo (opcional):")
    tid = pick_from(sorted(teams, key=lambda t:t['name'])) or ''
    country = prompt("País (para bandera img/flags/nombre_del_pais.png)", required=True)
    photo = prompt("Foto (img/jugadores/...)", default="img/jugadores/placeholder.png")
    def val_pos(v): return (v in ALLOWED_POSITIONS, f"Posición inválida. Usa: {', '.join(ALLOWED_POSITIONS)}")
    position = prompt(f"Posición {ALLOWED_POSITIONS}", required=True, validator=val_pos)
    def val_rating(v):
        try:
            n=int(v); return (40<=n<=99, "Rating debe estar entre 40 y 99")
        except: return (False, "Rating numérico 40..99")
    rating = int(prompt("Rating (40-99)", required=True, validator=val_rating))
    sofifa = prompt("URL SoFIFA (opcional)", default="")
    face_video = prompt("URL Video de cara (opcional)", default="")
    slug = ensure_slug_entity(f"{first} {last}", [x['slug'] for x in players])
    p = {'id': next_id(players),'first_name':first,'last_name':last,'birth_date':birth,'team_id':tid,'country':country,'photo':photo,'position':position,'rating':rating,'sofifa_url':sofifa,'face_video_url':face_video,'slug':slug}
    backup_all()
    players.append(p)
    save_all(leagues, teams, players)
    print("Jugador añadido:", p['id'], first, last)

def menu_edit_player():
    leagues, teams, players = load_all()
    q = input("Buscar jugador (texto, vacío para listar): ").strip().lower()
    rows = [p for p in players if q in (p['first_name']+' '+p['last_name']).lower()] if q else players
    rows = sorted(rows, key=lambda p:(p['last_name'], p['first_name']))
    for p in rows[:100]:
        print(f"{p['id']}: {p['first_name']} {p['last_name']}")
    pid = input("Id a editar: ").strip()
    if not pid: return
    p = next((x for x in players if x['id']==pid), None)
    if not p: print("No encontrado"); return

    first = prompt("Nombre", default=p['first_name'], required=True)
    last = prompt("Apellido", default=p['last_name'], required=True)
    birth = prompt("Fecha (YYYY-MM-DD)", default=p['birth_date'] or '', required=True, validator=lambda v: (valid_date(v),"Fecha inválida"))
    print("Elegir equipo (opcional):")
    tid = pick_from(sorted(teams, key=lambda t:t['name'])) or ''
    country = prompt("País", default=p['country'] or '', required=True)
    photo = prompt("Foto", default=p['photo'] or "img/jugadores/placeholder.png")
    def val_pos(v): return (v in ALLOWED_POSITIONS, f"Posición inválida. Usa: {', '.join(ALLOWED_POSITIONS)}")
    position = prompt("Posición", default=p['position'] or '', required=True, validator=val_pos)
    def val_rating(v):
        try:
            n=int(v); return (40<=n<=99, "Rating 40..99")
        except: return (False, "Rating numérico 40..99")
    rating = int(prompt("Rating (40-99)", default=str(p['rating'] or 40), required=True, validator=val_rating))
    sofifa = prompt("URL SoFIFA", default=p.get('sofifa_url',''))
    face_video = prompt("URL Video de cara", default=p.get('face_video_url',''))

    if first!=p['first_name'] or last!=p['last_name']:
        p['slug'] = ensure_slug_entity(f"{first} {last}", [x['slug'] for x in players if x['id']!=p['id']])
    p.update({'first_name':first,'last_name':last,'birth_date':birth,'team_id':tid,'country':country,'photo':photo,'position':position,'rating':rating,'sofifa_url':sofifa,'face_video_url':face_video})
    backup_all()
    save_all(leagues, teams, players)
    print("Jugador actualizado.")

def menu_delete_player():
    leagues, teams, players = load_all()
    q = input("Buscar (texto, vacío para listar): ").strip().lower()
    rows = [p for p in players if q in (p['first_name']+' '+p['last_name']).lower()] if q else players
    for p in rows[:100]:
        print(f"{p['id']}: {p['first_name']} {p['last_name']}")
    pid = input("Id a eliminar: ").strip()
    if not pid: return
    p = next((x for x in players if x['id']==pid), None)
    if not p: print("No encontrado"); return
    if input(f"Confirmar eliminación de {p['first_name']} {p['last_name']}? (s/N): ").strip().lower()!='s': return
    backup_all()
    players = [x for x in players if x['id']!=pid]
    save_all(leagues, teams, players)
    print("Jugador eliminado.")

# --- Meta ---
def menu_backup():
    made = backup_all()
    if not made: print("Nada que copiar (CSV no existentes).")
    else:
        for p in made: print("Backup:", p)

def build_arg_parser():
    p = argparse.ArgumentParser(description="Gestor LAQP (interactivo por defecto).")
    sub = p.add_subparsers(dest='cmd')
    sub.add_parser('export')
    sub.add_parser('validate')
    sub.add_parser('build')
    return p

def ensure_csv_headers():
    ensure_dirs()
    if not LEAGUES_CSV.exists():
        write_csv(LEAGUES_CSV, [], ['id','name','country','logo','slug'])
    if not TEAMS_CSV.exists():
        write_csv(TEAMS_CSV, [], ['id','name','league_id','logo','slug'])
    if not PLAYERS_CSV.exists():
        write_csv(PLAYERS_CSV, [], ['id','first_name','last_name','birth_date','team_id','country','photo','position','rating','sofifa_url','face_video_url','slug'])

def main():
    ensure_csv_headers()
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.cmd:
        interactive_menu()
        return
    if args.cmd=='export':
        export_cmd()
    elif args.cmd=='validate':
        validate(*load_all())
    elif args.cmd=='build':
        build_cmd()
    else:
        parser.print_help()

if __name__ == '__main__':
    main()