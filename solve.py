# 'sbClient' es la variable que se pega al inspeccionar la pagina y te da los datos de la base de
# datos y las credenciales.

import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

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


if __name__ == "__main__":
    resumen()

    est = supabase.table("estudiante").select("est_nombre, est_promedio").execute()
    for fila in est.data:
        print(fila)
