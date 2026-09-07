# Informe de vulnerabilidad — Exposición de datos en Supabase

**Sistema afectado:** Base de datos académica en Supabase (proyecto `zmvecicbbxbpuhbnexiz`)
**Fecha del hallazgo:** 2026-09-07
**Clasificación:** Exposición de datos sensibles / Control de acceso insuficiente (Broken Access Control)
**Severidad:** **ALTA** (Crítica si la tabla `estudiante` contiene PII real de personas identificables)
**Estado:** Documentado para remediación — prueba de concepto autorizada por el propietario del sistema

> **Nota de alcance.** Este ejercicio se realizó sobre un sistema propio y con fines
> exclusivamente defensivos: demostrar el impacto y la vía de acceso para poder
> corregir la configuración. Todos los datos personales observados se presentan aquí
> **enmascarados**. No se modificó ni se exfiltró información.

---

## 1. Resumen ejecutivo

Con **una sola credencial pública** (la *publishable key* de Supabase, del tipo
`sb_publishable_...`) — visible en el código del cliente / una captura de pantalla —
fue posible conectarse directamente a la API REST del proyecto desde una máquina
externa y **leer el contenido completo de varias tablas**, incluyendo una tabla de
estudiantes con **987 registros** de datos personales: cédula, nombre completo,
correo institucional, género y promedio académico.

La causa raíz **no es que la clave sea pública** (por diseño lo es), sino que las
tablas con datos sensibles **no tienen políticas de Row Level Security (RLS) que
restrinjan la lectura anónima**. En Supabase, la *publishable/anon key* solo debe
poder ver lo que las políticas RLS permitan; aquí no había ninguna barrera.

**Riesgo principal:** cualquiera que obtenga la clave pública (está incrustada en el
frontend, por lo que es trivialmente accesible) puede descargar la base de datos de
estudiantes.

---

## 2. Datos expuestos (verificado)

| Tabla | Filas | Sensibilidad | Contenido |
|---|---|---|---|
| `estudiante` | **987** | 🔴 Alta (PII) | cédula, nombre, correo, género, promedio, créditos, carrera |
| `observacion` | **887** | 🟠 Media-Alta | casos administrativos: comentarios, responsables, fechas |
| `materia` | 288 | 🟡 Baja | catálogo de materias (dato no personal) |
| `materia_carrera` | 132 | 🟡 Baja | relación materia–carrera |
| `semestre` | 8 | 🟡 Baja | periodos académicos |
| `carrera` | 0 | — | vacía o protegida por RLS |
| `profiles` | 0 | — | vacía o protegida por RLS |
| `seccion` | 0 | — | vacía o protegida por RLS |
| `proyeccion` | 0 | — | vacía o protegida por RLS |
| `audit_logs` | 0 | — | vacía o protegida por RLS |

### Ejemplo de registro expuesto (enmascarado)

Columnas reales de `estudiante`:
`est_id, est_cedula, est_nombre, est_ubic_sem, est_cumplimiento, est_promedio,
est_creditos_acum, est_cod_campus, est_genero, est_correo, est_car_id_fk`

```json
{
  "est_id": 8303,
  "est_cedula": "297*****9",
  "est_nombre": "Z***** H*******, Carlos J*****",
  "est_promedio": 17.11,
  "est_creditos_acum": 42,
  "est_genero": "M",
  "est_correo": "c*******.26@est.****.edu.**",
  "est_car_id_fk": 1
}
```

> El hecho de poder correlacionar **cédula + nombre + correo + rendimiento académico**
> de ~987 personas constituye una fuga de datos personales con potenciales
> implicaciones legales (protección de datos) y de reputación institucional.

---

## 3. Cómo se accedió a la información (cadena de ataque)

### Paso 0 — Obtención de la credencial
La *publishable key* y la URL del proyecto estaban visibles en el cliente:

```
supabaseUrl:  https://zmvecicbbxbpuhbnexiz.supabase.co
supabaseKey:  sb_publishable_tLbqOISGtoE-_0lEsqxuXQ_YYRaT59G
```

Este tipo de clave **siempre viaja al navegador** del usuario final (está embebida en
el JavaScript del frontend), por lo que debe considerarse **pública y conocida por
cualquier atacante**. Su seguridad depende **enteramente** de las políticas RLS del
servidor.

### Paso 1 — Conexión directa a la API REST
Supabase expone automáticamente cada tabla vía PostgREST en `/rest/v1/<tabla>`.
Bastó una petición HTTP autenticada con la clave pública:

```bash
curl "https://zmvecicbbxbpuhbnexiz.supabase.co/rest/v1/estudiante?select=*&limit=1" \
  -H "apikey: sb_publishable_..." \
  -H "Authorization: Bearer sb_publishable_..."
```

Como la tabla no tenía RLS que bloqueara al rol anónimo, la respuesta devolvió los
datos directamente.

### Paso 2 — Enumeración del esquema (fuga por mensajes de error)
El listado directo del esquema (`GET /rest/v1/`) sí estaba bloqueado para la clave
pública (`401: Only secret API keys can be used for this endpoint`). Sin embargo,
PostgREST **filtra nombres de tablas reales en el campo `hint`** de sus mensajes de
error cuando se consulta una tabla inexistente:

```json
{
  "code": "PGRST205",
  "message": "Could not find the table 'public.usuarios' in the schema cache",
  "hint": "Perhaps you meant the table 'public.seccion'"
}
```

Consultando nombres inexistentes de forma iterativa, el servidor fue **revelando los
nombres reales** de las tablas (`seccion` → `observacion` → `semestre` → `estudiante`
→ `materia` → ...). Esto permite reconstruir el esquema sin necesidad de la clave
secreta.

### Paso 3 — Extracción y conteo
Con los nombres reales confirmados, se leyeron las filas y se obtuvo el conteo exacto
usando la cabecera `Prefer: count=exact` (PostgREST responde `HTTP 206` con el total
en `Content-Range`):

```bash
curl "https://.../rest/v1/estudiante?select=*" \
  -H "apikey: sb_publishable_..." \
  -H "Prefer: count=exact" -I
# -> Content-Range: 0-987/987
```

**Tiempo total del compromiso:** minutos. **Herramientas:** solo `curl`/cliente HTTP
estándar. **Requisitos previos:** únicamente la clave pública.

---

## 4. Causa raíz

1. **RLS deshabilitado o sin políticas restrictivas** en tablas con datos sensibles
   (`estudiante`, `observacion`, `materia`, etc.). El rol anónimo puede leerlas.
2. **Confianza equivocada en la clave pública como si fuera secreta.** La
   *publishable key* no protege nada por sí sola; es identificación, no autorización.
3. **Fuga de esquema por mensajes de error** de PostgREST (`hint`), que facilita el
   reconocimiento aun sin acceso al endpoint de introspección.

---

## 5. Remediación recomendada

### 5.1 Prioridad inmediata — Activar y configurar RLS

Para **cada** tabla con datos sensibles:

```sql
-- 1) Activar RLS (bloquea TODO acceso hasta que exista una política que lo permita)
ALTER TABLE public.estudiante ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.observacion ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.materia ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.materia_carrera ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.semestre ENABLE ROW LEVEL SECURITY;
-- ...repetir para todas las tablas del esquema public

-- 2) Revocar cualquier acceso al rol anónimo (defensa en profundidad)
REVOKE ALL ON public.estudiante FROM anon;
REVOKE ALL ON public.observacion FROM anon;
```

Con RLS activado y **sin** políticas para `anon`, la clave pública deja de poder leer
la tabla. El acceso legítimo debe ir a través de usuarios autenticados con una
política explícita, por ejemplo:

```sql
-- Ejemplo: un estudiante solo puede ver SU propio registro
CREATE POLICY "estudiante_ve_su_registro"
  ON public.estudiante
  FOR SELECT
  TO authenticated
  USING ( est_correo = auth.jwt() ->> 'email' );

-- Ejemplo: solo personal administrativo (rol en el JWT) ve todo
CREATE POLICY "admin_ve_todo"
  ON public.estudiante
  FOR SELECT
  TO authenticated
  USING ( (auth.jwt() ->> 'role') = 'admin' );
```

> **Verificación:** tras aplicar RLS, repetir el `curl` del Paso 1 con la clave
> pública debe devolver `[]` (o error), no los datos.

### 5.2 Rotar la clave y mover la lógica sensible al servidor
- Si alguna operación necesita saltarse RLS, hacerla en un **backend** (o *Edge
  Function*) usando la **`service_role` key**, que **nunca** debe salir del servidor
  ni incrustarse en el frontend.
- Rotar/regenerar las claves del proyecto si se sospecha uso indebido.

### 5.3 Reducir la superficie
- Mover tablas que no deban exponerse a un esquema **fuera** de `public` (p. ej.
  `private`) que no esté publicado por la API REST.
- Exponer solo **vistas** con las columnas mínimas necesarias, en lugar de las tablas
  completas.

### 5.4 Datos personales
- Minimizar columnas: evitar exponer cédula/correo juntos donde no sea imprescindible.
- Considerar cifrado a nivel de columna para identificadores nacionales.
- Registrar y auditar accesos (la tabla `audit_logs` sugiere que ya existe intención
  de esto — conviene poblarla y protegerla).

---

## 6. Checklist de verificación post-remediación

- [ ] `ENABLE ROW LEVEL SECURITY` en todas las tablas de `public`.
- [ ] Ninguna política otorga `SELECT` al rol `anon` sobre datos personales.
- [ ] `GET /rest/v1/estudiante` con la *publishable key* devuelve vacío/401.
- [ ] La `service_role` key no aparece en ningún bundle del frontend ni repositorio.
- [ ] Tablas sensibles movidas fuera de `public` o expuestas solo vía vistas mínimas.
- [ ] Claves rotadas.
- [ ] Prueba de regresión: un usuario autenticado solo ve lo que le corresponde.

---

## 7. Referencias

- Supabase — Row Level Security: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase — API Keys (publishable vs. secret / service_role): https://supabase.com/docs/guides/api/api-keys
- PostgREST — Schema & error responses: https://postgrest.org/en/stable/references/errors.html
- OWASP — A01:2021 Broken Access Control: https://owasp.org/Top10/A01_2021-Broken_Access_Control/

---

*Documento generado como parte de una evaluación de seguridad autorizada sobre un
sistema propio. Uso exclusivamente defensivo.*
