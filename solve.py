# 'sbClient' es la variable que se pega al inspeccionar la pagina y te da los datos de la base de
# datos y las credenciales.

import os

from colorama import Fore as color
from colorama import init
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()
init(autoreset=True)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLAS = [
    "estudiante",
    "materia",
    "materia_carrera",
    "observacion",
    "semestre",
    "carrera",
    "profiles",
]


def resumen() -> None:
    print(f"Conectado a {SUPABASE_URL}\n")
    for tabla in TABLAS:
        resp = supabase.table(tabla).select("*", count="exact").limit(0).execute()
        print(f"  {tabla:16} filas={resp.count}")


def tabla_bonita(filas: list[dict], titulo: str = "") -> None:
    """Imprime una lista de dicts como una tabla con bordes Unicode."""
    if not filas:
        print(color.YELLOW + "  (sin datos)")
        return

    # Columnas en el orden en que aparecen en la primera fila
    columnas = list(filas[0].keys())

    def celda(v) -> str:
        return "" if v is None else str(v)

    # Ancho de cada columna = max(encabezado, valores)
    anchos = {
        c: max(len(c), *(len(celda(f.get(c))) for f in filas)) for c in columnas
    }

    def linea(izq: str, med: str, der: str) -> str:
        return izq + med.join("─" * (anchos[c] + 2) for c in columnas) + der

    def fila_txt(valores) -> str:
        return "│" + "│".join(f" {v:<{anchos[c]}} " for c, v in zip(columnas, valores)) + "│"

    if titulo:
        print(color.CYAN + f"\n{titulo}")

    print(color.CYAN + linea("┌", "┬", "┐"))
    print(color.CYAN + fila_txt(columnas))
    print(color.CYAN + linea("├", "┼", "┤"))
    for f in filas:
        print(color.GREEN + fila_txt([celda(f.get(c)) for c in columnas]))
    print(color.CYAN + linea("└", "┴", "┘"))
    print(color.WHITE + f"  {len(filas)} fila(s)")


if __name__ == "__main__":
    resumen()

    est = supabase.table("estudiante").select("*").execute()
    tabla_bonita(est.data, titulo="Tabla: estudiante")
