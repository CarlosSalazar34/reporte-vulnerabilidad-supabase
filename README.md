# Reporte de vulnerabilidad — Exposición de datos en Supabase

Evaluación de seguridad **autorizada** sobre un sistema académico propio.
Documenta cómo una credencial pública mal protegida (sin RLS) permitió leer datos
personales de estudiantes, y cómo remediarlo.

> ⚠️ **Uso defensivo.** Realizado sobre un sistema propio, con fines educativos y de
> corrección. Los datos personales del informe están **enmascarados**. No se modificó
> ni se exfiltró información.

## Sistema evaluado

Proceso de inscripciones de Ingeniería Informática — Escuela de Ingeniería
Informática, UCAB (Caracas):
<https://ingenieria.ucab.edu.ve/informatica/la-escuela/caracas/procesos-academicos/ingenieria-informatica/inscripciones/>

## Contenido

| Archivo | Descripción |
|---|---|
| [`INFORME_VULNERABILIDAD_SUPABASE.md`](./INFORME_VULNERABILIDAD_SUPABASE.md) | Informe técnico completo: hallazgo, cadena de acceso, impacto y remediación |
| [`poc/verificar_rls.py`](./poc/verificar_rls.py) | Script para **comprobar si la fuga sigue abierta** (verificación defensiva) |
| [`.env.example`](./.env.example) | Plantilla de variables de entorno (el `.env` real no se sube) |

## Resumen

- **Clasificación:** Broken Access Control (OWASP A01:2021)
- **Severidad:** ALTA
- **Causa raíz:** tablas con datos sensibles **sin Row Level Security (RLS)**, legibles
  con la *publishable key* (que por diseño es pública y viaja al frontend).
- **Impacto:** lectura de ~987 registros de estudiantes (cédula, nombre, correo,
  promedio) con solo la clave pública y peticiones HTTP estándar.

## Cómo verificar que quedó corregido

```bash
python -m pip install supabase python-dotenv
cp .env.example .env      # rellena con tu URL y publishable key
python poc/verificar_rls.py
```

Si la remediación (activar RLS) está aplicada, el script debe reportar que las tablas
sensibles **ya no son legibles** con la clave pública.

## Remediación (resumen)

1. `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` en todas las tablas sensibles.
2. Revocar acceso al rol `anon`; crear políticas explícitas solo para usuarios
   autenticados.
3. Mover la lógica que requiera saltarse RLS a un backend con la `service_role` key
   (nunca en el frontend).
4. Rotar las claves del proyecto.

Ver el [informe completo](./INFORME_VULNERABILIDAD_SUPABASE.md) para el detalle y el SQL.
