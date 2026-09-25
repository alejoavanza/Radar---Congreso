# Radar Plus: historial social, piloto sin contrataciones

## Alcance implementado

- Pestaña Plus en la aplicación existente; reutiliza el directorio de Cámara y Senado, con su fecha de revisión visible.
- Periodos: 7 días inclusivos; 1, 3, 6 y 12 meses calendario con ajuste de fin de mes. Corte America/Bogota.
- Gráfico de total y cinco gráficos por plataforma. Seguidores/suscriptores, visualizaciones, interacciones, publicaciones, impresiones y alcance.
- Importación CSV UTF-8 validada; máximo 2 MB y 20.000 filas. Plantilla por congresista, tabla de fuentes, exportación íntegra y borrado de la carga.
- Registros exclusivamente aportados por el usuario. No hay muestras ficticias ni cifras extraídas de recuerdos de conversaciones.

## Estado del piloto

El piloto está disponible sin cobro y se identifica como tal. **No es todavía una suscripción Plus ni una integración OAuth.** No hay nuevos servicios contratados, consultas a APIs de redes, cobros, almacenamiento en servidor, tareas programadas ni credenciales nuevas.

El servidor valida el archivo y devuelve registros normalizados con `Cache-Control: no-store, private`. El navegador los mantiene solamente en memoria de la pestaña, no en localStorage. Recargar o cerrar descarta los datos; la UI avisa y permite exportarlos. Los registros anteriores a 12 meses no entran en la carga. Una importación inválida conserva la anterior. Los datos no se publican en el repositorio.

## Contrato de datos

Columnas: `member_id,platform,account,date,followers,views,interactions,posts,impressions,reach,source`.

`member_id`: identificador del directorio. `platform`: instagram, facebook, tiktok, youtube o x. `account`: identificador estable de la cuenta, no contraseña ni token. `date`: AAAA-MM-DD, corte colombiano. `source`: enlace HTTPS a la fuente; no se descarga por el servidor. Una fila por persona/red/día y una cuenta por persona/red dentro de una importación. Se rechazan duplicados y cambios de cuenta para evitar crecimiento espurio. Las métricas desconocidas se dejan vacías; cero se usa sólo para una medición de cero.

Seguidores es un saldo al cierre de la fecha. Las restantes métricas son valores correspondientes exclusivamente a ese día. No importar acumulados de visualizaciones ni exportaciones con ventanas superpuestas como si fueran valores diarios. Las exportaciones de cada red requieren normalización a este contrato. Registrar las definiciones de métricas y su zona horaria será obligatorio en los futuros adaptadores.

Los puntos no se interpolan. El total sólo existe en fechas con valores de todas las redes seleccionadas, con la misma selección para toda la serie. No se arrastran saldos antiguos ni se mezclan cohortes. El alcance nunca se suma. Crecimiento sólo entre observaciones de seguidores, con fechas explícitas y porcentaje N/D si el saldo inicial es cero. La suma de seguidores no mide personas únicas, y las vistas/interacciones tienen definiciones diferentes entre plataformas.

El CSV aportado no demuestra autenticidad, consentimiento ni propiedad de la cuenta. Se rotula como importado, no verificado. No incluir estos datos en rankings públicos ni decisiones comerciales automáticas.

## Piezas para descargar y compartir

El generador produce PNG en 1080 × 1350, 1600 × 900 y 1080 × 1920 con estilos claro/oscuro. Ofrece comparativo de redes seleccionadas, total e individuales. Usa el periodo, persona y métrica activos; no trae datos nuevos ni reutiliza cifras de otro perfil.

El comparativo de seguidores puede usar cifras reales o índice base 100, únicamente desde la primera fecha común con saldo positivo en todas las redes seleccionadas. No se normaliza cada red en una fecha diferente. Las cifras finales y porcentajes conservan las fechas observadas. Líneas discontinuas unen puntos medidos y el pie aclara los huecos. Cero se conserva; ausencia no se sustituye por cero.

Las piezas muestran nombre, periodo, métrica, redes, número de observaciones, fechas, origen importado no verificado y dominios de las fuentes. No presentan impacto legislativo, influencia ni votos. Se pueden descargar y acompañar del texto copiable. Web Share utiliza un archivo preparado antes del clic para conservar la activación de usuario en iOS. Cuando el navegador no soporta compartir archivos, se ofrece descarga manual. Cancelar el menú no publica nada. Radar no confirma publicaciones hechas por aplicaciones externas ni envía archivos automáticamente a ninguna cuenta.

Cambiar persona, métrica, rango, archivo o diseño invalida la imagen previa. El diálogo es nativo, admite Escape y presenta una vista previa antes de compartir. La imagen se genera en el dispositivo y no se almacena ni publica en el servidor.

## Pendientes para Plus operativo

1. Identidad, membresía Plus y autorización por equipo comprobadas en servidor. El piloto actual no da acceso a ningún dato almacenado de otra persona.
2. Base de datos duradera y aislamiento por equipo; cifrado de credenciales, revocación y eliminación. No usar disco efímero de Vercel como historial compartido.
3. Registrar aplicaciones con cada plataforma, permisos de lectura, revisión y OAuth; probar con las cuentas de Alejandro. No activar X u otro servicio facturable sin autorización expresa.
4. Adaptadores que normalicen métricas, periodos, zona horaria y fuentes; importación histórica sólo donde la API o exportación la proporcione.
5. Capturas periódicas idempotentes con origen, fecha de observación, vigencia de cuenta y estado de cobertura; presupuesto cero por defecto.
6. Verificar vigencia del directorio oficial y asociación de cada cuenta. El listado actual conserva la fecha de revisión existente; no constituye un padrón verificado a la fecha de despliegue.
7. Presencia web sigue en Radar/Comparativos; no hay histórico de doce meses ni índice compuesto. Definir pesos y datos comparables antes de introducir un índice.

La versión nativa empaquetada conserva sus archivos existentes. Este cambio se entrega en web/PWA; llevar la nueva interfaz a los binarios iOS/Android requerirá sincronizar y compilar en la rama móvil, sin confundirlo con una actualización automática del binario instalado.

## Verificación

`python -m unittest discover -s tests -p 'test_*.py'`

`node --test tests/*.test.cjs`

Prueba de navegador: abrir Plus, importar un CSV de prueba identificado como sintético, recorrer los cinco periodos y seis métricas, cambiar congresista/redes, verificar total incompleto N/D, importar CSV inválido sin perder la carga, exportar y borrar. Revisar anchos móvil y escritorio y navegación a Radar/Comparativos. No publicar los datos sintéticos.
