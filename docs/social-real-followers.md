# Plus Redes: observaciones públicas, primera fase

## Qué cambia

La pantalla pública deja de cargar el piloto de CSV y sus ejemplos. Usa el directorio compartido de Radar para seleccionar una persona y consulta `/api/social/followers`. Sin una fuente habilitada o una cuenta corroborada muestra «Sin medición disponible», nunca una cifra de sustitución ni cero.

El importador y sus pruebas históricas se conservan para compatibilidad, pero la pantalla pública no los ejecuta. Los datos sintéticos existen exclusivamente en pruebas locales/CI y no se escriben en el registro público de cuentas ni en una base de producción.

## Alcance real

- Adaptador implementado: YouTube Data API `channels.list(part=statistics, id=...)`.
- Pendientes: adaptadores y permisos de Instagram, Facebook, TikTok y X. No hay consulta automática universal ni contratación de proveedores.
- Descubrimiento: enlaces encontrados en la ficha institucional del directorio, con hosts y tamaño de respuesta restringidos, sin seguir redirecciones ni sortear bloqueos. Son candidatos, no identidades aprobadas. También se ofrece un enlace que abre una búsqueda web; esa búsqueda no ejecuta mediciones dentro de Radar.
- Historial: adaptador opcional de Supabase y migración SQL incluidos; no crean ni contratan una base. Sin configuración no hay historial duradero, ni se usa `/tmp` como sustituto.
- No hay recolección diaria automática activa. Las observaciones se obtienen a petición del usuario. Programar un recolector requiere resolver primero credenciales, registro, conservación y capacidad.

## Activar la primera fuente sin exponer secretos

1. En un proyecto administrado por Táctika, habilitar YouTube Data API v3 y crear una clave restringida a esa API, con cuotas adecuadas. No incluir la clave en GitHub, HTML, aplicaciones móviles, CSV ni mensajes del chat.
2. El administrador debe configurar `YOUTUBE_API_KEY` como variable secreta del servidor Vercel y desplegar de nuevo. Esta integración no activa facturación ni compra cuotas.
3. Corroborar el canal exacto de cada persona y registrar su identificador permanente `UC...` en `social_accounts.json`. Cada entrada requiere `member_id`, `platform`, `account_id`, `status: reviewed`, `evidence_url` y `reviewed_at` (ISO 8601 con zona). El identificador debe corresponder al directorio. Una cuenta encontrada por nombre o un enlace de la cabecera institucional no bastan.
4. Las revisiones caducan a los 30 días, evitando presentar una vinculación obsoleta como actual. Dos cuentas aprobadas para la misma persona/red se tratan como ambiguas, no se escoge la primera.
5. Comprobar `/api/social/status` y efectuar una consulta real: una variable presente no demuestra que la clave tenga acceso. Las respuestas 403/429, un canal inexistente o un conteo oculto siguen siendo «sin medición».

El registro empieza vacío deliberadamente: no se inventan identificadores para que una prueba aparente funcionar.

## Conservación central opcional

Usar solamente un proyecto Supabase elegido por el administrador, sin aceptar servicios de pago. Aplicar `migrations/001_follower_snapshots.sql`, configurar y verificar la limpieza horaria con pg_cron, y revisar la retención de respaldos antes de habilitar el almacenamiento. Las credenciales son `SOCIAL_SUPABASE_URL` y `SOCIAL_SUPABASE_SERVICE_KEY`, exclusivamente en Vercel. La clave de servicio nunca se entrega al cliente.

La tabla tiene RLS, sin acceso de anon/authenticated. Sólo el backend ejecuta las funciones específicas de lectura/escritura. Se conserva el primer registro por persona, red, cuenta y fecha UTC. Una consulta repetida no renueva su fecha. Un fallo de fuente no crea un cero. La API omite registros ajenos, futuros, vencidos o sin procedencia oficial; el SQL elimina los vencidos al leer/escribir y el trabajo horario debe borrarlos incluso cuando nadie consulta.

Los registros públicos de YouTube caducan a los 29 días, con margen frente al límite de 30. No mantener copias, exportaciones o respaldos que eludan ese vencimiento. Las pruebas SQL se ejecutan sólo en una base desechable de CI; no acreditan que la base de producción esté configurada.

## Fechas, precisión y crecimiento

YouTube entrega `subscriberCount` redondeado hacia abajo a tres cifras significativas. Radar muestra el valor devuelto, su fuente, cuenta y fecha de obtención. Reutiliza respuestas hasta 15 minutos sin alterar el sello temporal; esta caché no constituye historial.

La vista permite revisar observaciones de las últimas 24 horas, 7 o 28 días; no atribuye al pasado un dato obtenido hoy ni rellena huecos. Esta primera fase muestra conteos fechados, pero no genera porcentajes, índices o métricas derivadas de YouTube hasta resolver la revisión y permisos aplicables. No promete un año de historial ni suma redes como personas únicas.

Referencias oficiales consultadas al diseñar la integración:
- https://developers.google.com/youtube/v3/docs/channels/list
- https://developers.google.com/youtube/v3/docs/channels
- https://developers.google.com/youtube/terms/developer-policies

## Web, iOS y Android

La pantalla web/PWA comparte diseño y endpoints. Se prueba con Chromium/perfil Android y WebKit/perfil iPhone, no con teléfonos físicos. El código nativo del PR #21 empaqueta recursos locales: requiere incorporar esta revisión, revisar la lista de scripts, permitir GET `/api/social/status` y POST `/api/social/followers` y `/api/social/discover` en su transporte restringido, y verificar navegación de regreso desde Plus. Nunca sustituir esta revisión por permitir URLs arbitrarias en el puente nativo.

No se han actualizado binarios nativos ni enviado versiones a App Store o Google Play como parte de este cambio.
