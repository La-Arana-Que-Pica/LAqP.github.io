#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
manage_db.py — Herramienta CLI + menú interactivo para administrar db.csv
- Si se ejecuta sin argumentos (o con --interactive) abre un menú amigable.
- Conserva las acciones básicas (list, add, update, delete, validate, export) como subcomandos
  para usuarios avanzados.

Coloca este archivo en la misma carpeta que db.csv (o ajusta CSV_PATH).
"""
import csv
import argparse
import sys
from datetime import datetime
import json
from pathlib import Path
import shutil

CSV_PATH = Path('db.csv')
BACKUP_DIR = Path('backups')
HEADERS = ['id','team_name','league','country','added_date','notes','logo','link']
PAGE_SIZE = 10

# -----------------------
# Utilidades de fichero
# -----------------------
def ensure_backup_dir():
    BACKUP_DIR.mkdir(exist_ok=True)

def backup_csv():
    """Crear copia de seguridad con timestamp y devolver la ruta creada."""
    if not CSV_PATH.exists():
        return None
    ensure_backup_dir()
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    target = BACKUP_DIR / f"db_backup_{ts}.csv"
    shutil.copy2(CSV_PATH, target)
    return target

def read_rows():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]
    return rows

def write_rows(rows):
    # asegura que las cabeceras estén en orden consistente
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k,'') for k in HEADERS})

def next_id(rows):
    ids = [int(r.get('id') or 0) for r in rows if str(r.get('id') or '').isdigit()]
    return str(max(ids)+1 if ids else 1)

# -----------------------
# Validación
# -----------------------
def validate_rows(rows):
    problems = []
    for r in rows:
        if not r.get('team_name'):
            problems.append((r.get('id'), 'team_name faltante'))
        if not r.get('league'):
            problems.append((r.get('id'), 'league faltante'))
        d = r.get('added_date','')
        if d:
            try:
                datetime.strptime(d, '%Y-%m-%d')
            except Exception:
                problems.append((r.get('id'), f'added_date inválida: {d}'))
    return problems

# -----------------------
# Presentación en consola
# -----------------------
def format_row_for_table(r):
    # crea una versión corta para visualización
    return {
        'id': r.get('id',''),
        'team': r.get('team_name','')[:40],
        'league': r.get('league','')[:25],
        'country': r.get('country','')[:20],
        'date': r.get('added_date',''),
        'notes': (r.get('notes','')[:40] + ('...' if len(r.get('notes',''))>40 else '')),
    }

def print_table(rows, page=None):
    if not rows:
        print("(sin registros)")
        return
    formatted = [format_row_for_table(r) for r in rows]
    cols = ['id','team','league','country','date','notes']
    widths = {c: max(len(c), max((len(str(item[c])) for item in formatted), default=0)) for c in cols}
    sep = '  '
    header = sep.join(c.upper().ljust(widths[c]) for c in cols)
    print(header)
    print('-' * len(header))
    start = 0
    end = len(formatted)
    if page is not None:
        start = page * PAGE_SIZE
        end = min((page+1)*PAGE_SIZE, len(formatted))
    for item in formatted[start:end]:
        line = sep.join(str(item[c]).ljust(widths[c]) for c in cols)
        print(line)
    if page is not None:
        print(f"-- mostrando {start+1}-{end} de {len(formatted)} --")

def input_with_default(prompt, default):
    if default:
        res = input(f"{prompt} [{default}]: ").strip()
    else:
        res = input(f"{prompt}: ").strip()
    return res if res != '' else default

# -----------------------
# Operaciones CRUD
# -----------------------
def list_cmd(args):
    rows = read_rows()
    if not rows:
        print("No hay registros.")
        return
    page = 0
    while True:
        print_table(rows, page)
        if (page+1)*PAGE_SIZE >= len(rows):
            break
        choice = input("Presiona Enter para ver más, 'q' para salir, o 'n' para siguiente: ").strip().lower()
        if choice == 'q':
            break
        page += 1

def add_cmd_interactive():
    print("Añadir nuevo registro. Rellena los campos (ENTER para valores por defecto / mantener vacío).")
    team = ''
    while not team:
        team = input("Nombre del equipo (requerido): ").strip()
        if not team:
            print("El nombre del equipo es obligatorio.")
    league = ''
    while not league:
        league = input("Liga (requerido): ").strip()
        if not league:
            print("La liga es obligatoria.")
    country = ''
    while not country:
        country = input("País (requerido): ").strip()
        if not country:
            print("El país es obligatorio.")
    date = input_with_default("Fecha (YYYY-MM-DD)", datetime.utcnow().strftime('%Y-%m-%d'))
    # validar fecha simple
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except Exception:
        print("Fecha inválida. Se usará la fecha actual.")
        date = datetime.utcnow().strftime('%Y-%m-%d')
    notes = input("Notas (opcional): ").strip()
    logo = input("Ruta logo (opcional, ej. img/logos/x.png): ").strip()
    link = input("Enlace (opcional): ").strip()

    rows = read_rows()
    new = {
        'id': next_id(rows),
        'team_name': team,
        'league': league,
        'country': country,
        'added_date': date,
        'notes': notes,
        'logo': logo,
        'link': link,
    }
    print("\nResumen del nuevo registro:")
    print(json.dumps(new, ensure_ascii=False, indent=2))
    ok = input("Confirmar guardado? (s/N): ").strip().lower()
    if ok != 's':
        print("Cancelado.")
        return
    b = backup_csv()
    if b:
        print(f"Copia de seguridad creada: {b}")
    rows.append(new)
    write_rows(rows)
    print("Registro añadido con id", new['id'])

def find_index(rows, idv):
    for i,r in enumerate(rows):
        if str(r.get('id')) == str(idv):
            return i
    return None

def update_cmd_interactive():
    rows = read_rows()
    if not rows:
        print("No hay registros para actualizar.")
        return
    idv = input("Introduce el id a actualizar (o deja vacío para buscar por nombre): ").strip()
    idx = None
    if idv:
        idx = find_index(rows, idv)
        if idx is None:
            print("Id no encontrado.")
            return
    else:
        q = input("Buscar nombre (texto): ").strip().lower()
        matches = [r for r in rows if q in (r.get('team_name','').lower())]
        if not matches:
            print("No se encontraron coincidencias.")
            return
        print("Coincidencias:")
        print_table(matches)
        idv = input("Introduce el id exacto de la fila que deseas actualizar: ").strip()
        idx = find_index(rows, idv)
        if idx is None:
            print("Id no encontrado.")
            return

    r = rows[idx]
    print("Valores actuales (ENTER para mantener):")
    team = input_with_default("Nombre del equipo", r.get('team_name',''))
    league = input_with_default("Liga", r.get('league',''))
    country = input_with_default("País", r.get('country',''))
    date = input_with_default("Fecha (YYYY-MM-DD)", r.get('added_date', datetime.utcnow().strftime('%Y-%m-%d')))
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except Exception:
        print("Fecha inválida, se mantiene la original.")
        date = r.get('added_date','')
    notes = input_with_default("Notas", r.get('notes',''))
    logo = input_with_default("Logo", r.get('logo',''))
    link = input_with_default("Enlace", r.get('link',''))

    updated = {
        'id': r.get('id'),
        'team_name': team,
        'league': league,
        'country': country,
        'added_date': date,
        'notes': notes,
        'logo': logo,
        'link': link,
    }
    print("\nRegistro resultante:")
    print(json.dumps(updated, ensure_ascii=False, indent=2))
    ok = input("Confirmar actualización? (s/N): ").strip().lower()
    if ok != 's':
        print("Cancelado.")
        return
    b = backup_csv()
    if b:
        print(f"Copia de seguridad creada: {b}")
    rows[idx] = updated
    write_rows(rows)
    print("Registro actualizado:", updated['id'])

def delete_cmd_interactive():
    rows = read_rows()
    if not rows:
        print("No hay registros para eliminar.")
        return
    idv = input("Introduce el id a eliminar (o deja vacío para buscar por nombre): ").strip()
    idx = None
    if idv:
        idx = find_index(rows, idv)
        if idx is None:
            print("Id no encontrado.")
            return
    else:
        q = input("Buscar nombre (texto): ").strip().lower()
        matches = [r for r in rows if q in (r.get('team_name','').lower())]
        if not matches:
            print("No se encontraron coincidencias.")
            return
        print("Coincidencias:")
        print_table(matches)
        idv = input("Introduce el id exacto de la fila que deseas eliminar: ").strip()
        idx = find_index(rows, idv)
        if idx is None:
            print("Id no encontrado.")
            return

    r = rows[idx]
    print("Registro a eliminar:")
    print(json.dumps(r, ensure_ascii=False, indent=2))
    ok = input("Confirmar eliminación? ESTA ACCIÓN NO SE PUEDE DESHACER. (s/N): ").strip().lower()
    if ok != 's':
        print("Cancelado.")
        return
    b = backup_csv()
    if b:
        print(f"Copia de seguridad creada: {b}")
    removed = rows.pop(idx)
    write_rows(rows)
    print("Registro eliminado:", removed.get('id'))

def validate_cmd(args):
    rows = read_rows()
    problems = validate_rows(rows)
    if not problems:
        print("Validación OK — no issues found.")
    else:
        print("Problemas encontrados:")
        for p in problems:
            print("-", p[0], p[1])

def export_cmd(args):
    rows = read_rows()
    out = args.json if args.json else 'out.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("Exportado a", out)

# -----------------------
# Menú interactivo
# -----------------------
def interactive_menu():
    MENU = [
        ("Listar registros", lambda: list_cmd(None)),
        ("Buscar por texto", interactive_search),
        ("Añadir registro", add_cmd_interactive),
        ("Actualizar registro", update_cmd_interactive),
        ("Eliminar registro", delete_cmd_interactive),
        ("Validar CSV", lambda: validate_cmd(None)),
        ("Exportar a JSON", interactive_export),
        ("Crear copia de seguridad manual", interactive_backup),
        ("Salir", lambda: sys.exit(0)),
    ]
    print("=== Gestor de db.csv — Menú interactivo ===")
    while True:
        for i,(label,_) in enumerate(MENU, start=1):
            print(f"{i}) {label}")
        try:
            choice = input("Selecciona una opción (número): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print("Salida.")
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(MENU):
            print("Opción no válida.")
            continue
        idx = int(choice)-1
        try:
            MENU[idx][1]()
        except Exception as e:
            print("Error ejecutando la acción:", e)
        input("\n(ENTER para volver al menú)")

# -----------------------
# Funciones auxiliares del menú (search, export, backup)
# -----------------------
def interactive_search():
    q = input("Texto a buscar (nombre/liga/país/notas): ").strip().lower()
    if not q:
        print("Nada que buscar.")
        return
    rows = read_rows()
    matches = [r for r in rows if q in (r.get('team_name','').lower() + " " + r.get('league','').lower() + " " + r.get('country','').lower() + " " + r.get('notes','').lower())]
    if not matches:
        print("No hay coincidencias.")
        return
    print_table(matches)

def interactive_export():
    out = input_with_default("Nombre de archivo JSON de salida", "out.json")
    args = argparse.Namespace(json=out)
    export_cmd(args)

def interactive_backup():
    b = backup_csv()
    if b:
        print("Copia creada:", b)
    else:
        print("No existe db.csv para copiar.")

# -----------------------
# Soporte de comandos clásicos por línea
# -----------------------
def build_arg_parser():
    parser = argparse.ArgumentParser(description='Administrar db.csv (menu interactivo si se ejecuta sin subcomando)')
    parser.add_argument('--interactive', action='store_true', help='Abrir menú interactivo')
    sub = parser.add_subparsers(dest='cmd')

    sub.add_parser('list')
    p_add = sub.add_parser('add')
    p_add.add_argument('--team', required=False)
    p_add.add_argument('--league', required=False)
    p_add.add_argument('--country', required=False)
    p_add.add_argument('--date')
    p_add.add_argument('--notes')
    p_add.add_argument('--logo')
    p_add.add_argument('--link')

    p_up = sub.add_parser('update')
    p_up.add_argument('--id', required=True)
    p_up.add_argument('--team')
    p_up.add_argument('--league')
    p_up.add_argument('--country')
    p_up.add_argument('--date')
    p_up.add_argument('--notes')
    p_up.add_argument('--logo')
    p_up.add_argument('--link')

    p_del = sub.add_parser('delete')
    p_del.add_argument('--id', required=True)

    sub.add_parser('validate')
    p_exp = sub.add_parser('export')
    p_exp.add_argument('--json', required=False)

    return parser

def cmd_add_from_args(args):
    if not (args.team and args.league and args.country):
        print("Para add vía CLI debes pasar --team, --league y --country (usa el modo interactivo para prompts).")
        return
    rows = read_rows()
    new = {
        'id': next_id(rows),
        'team_name': args.team,
        'league': args.league,
        'country': args.country,
        'added_date': args.date or datetime.utcnow().strftime('%Y-%m-%d'),
        'notes': args.notes or '',
        'logo': args.logo or '',
        'link': args.link or '',
    }
    b = backup_csv()
    if b:
        print("Backup:", b)
    rows.append(new)
    write_rows(rows)
    print("Registro añadido con id", new['id'])

def cmd_update_from_args(args):
    rows = read_rows()
    idx = find_index(rows, args.id)
    if idx is None:
        print("Id no encontrado.")
        return
    r = rows[idx]
    for k in ['team','league','country','date','notes','logo','link']:
        val = getattr(args, k)
        if val is not None:
            keymap = {'team':'team_name','date':'added_date'}
            r[keymap.get(k,k)] = val
    b = backup_csv()
    if b:
        print("Backup:", b)
    rows[idx] = r
    write_rows(rows)
    print("Registro actualizado:", r['id'])

def cmd_delete_from_args(args):
    rows = read_rows()
    idx = find_index(rows, args.id)
    if idx is None:
        print("Id no encontrado.")
        return
    b = backup_csv()
    if b:
        print("Backup:", b)
    removed = rows.pop(idx)
    write_rows(rows)
    print("Registro eliminado:", removed.get('id'))

# -----------------------
# Main
# -----------------------
def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    # si se solicita interactivo explícito o no se pasan subcomandos -> menú
    if args.interactive or args.cmd is None:
        interactive_menu()
        return

    # comandos por línea
    if args.cmd == 'list':
        list_cmd(args)
    elif args.cmd == 'add':
        cmd_add_from_args(args)
    elif args.cmd == 'update':
        cmd_update_from_args(args)
    elif args.cmd == 'delete':
        cmd_delete_from_args(args)
    elif args.cmd == 'validate':
        validate_cmd(args)
    elif args.cmd == 'export':
        export_cmd(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()