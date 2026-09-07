"""Verificacion defensiva: comprueba si las tablas sensibles siguen siendo
legibles con la clave PUBLICA de Supabase.

Uso:
    cp ../.env.example ../.env   # y rellenar valores
    python verificar_rls.py

Si RLS esta bien configurado, las tablas sensibles deben devolver 0 filas / error
al consultarlas con la publishable key. Este script NO extrae datos: solo cuenta.
"""

import os
import sys

import httpx
from dotenv import load_dotenv

# Busca el .env en este directorio o en el padre.
for ruta in (".env", os.path.join("..", ".env")):
    if os.path.exists(ruta):
        load_dotenv(ruta)
        break

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")

if not URL or not KEY:
    sys.exit("Falta SUPABASE_URL o SUPABASE_KEY. Copia .env.example a .env y rellenalo.")

TABLAS_SENSIBLES = ["estudiante", "observacion"]

headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Prefer": "count=exact"}


def filas_visibles(tabla: str) -> int | None:
    """Devuelve el numero de filas visibles con la clave publica, o None si no se puede leer."""
    r = httpx.get(f"{URL}/rest/v1/{tabla}?select=*&limit=1", headers=headers, timeout=20)
    if r.status_code in (200, 206):
        total = r.headers.get("content-range", "*/?").split("/")[-1]
        try:
            return int(total)
        except ValueError:
            return len(r.json())
    return None  # bloqueado (401/403/404)


def main() -> None:
    print(f"Verificando {URL}\n")
    fuga = False
    for tabla in TABLAS_SENSIBLES:
        n = filas_visibles(tabla)
        if n is None:
            print(f"  [OK ] {tabla:14} -> no legible con la clave publica (protegido)")
        elif n == 0:
            print(f"  [OK ] {tabla:14} -> 0 filas visibles (protegido o vacio)")
        else:
            print(f"  [!!!] {tabla:14} -> {n} filas EXPUESTAS con la clave publica")
            fuga = True

    print()
    if fuga:
        print("RESULTADO: VULNERABLE. Aplica RLS (ver el informe). ")
        sys.exit(1)
    print("RESULTADO: sin exposicion detectada con la clave publica.")


if __name__ == "__main__":
    main()
