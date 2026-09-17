# EstampaFlow

**Tus pedidos personalizados, bajo control.**

EstampaFlow es un SaaS multiempresa para emprendimientos chilenos de estampado, sublimación, impresión y productos personalizados. El repositorio contiene la base SaaS y la administración interna de la **Fase 2**.

## Estado de la Fase 1

Incluye:

- Docker Compose con PostgreSQL, Django y React.
- Registro transaccional de empresa y propietario.
- Inicio, cierre y renovación de sesión con JWT en cookies `HttpOnly`.
- Recuperación de contraseña con respuesta que no revela si una cuenta existe.
- Perfil y cambio de contraseña.
- Empresas, configuración regional para Chile y roles propietario/colaborador.
- Administración del equipo por propietarios.
- Aislamiento multiempresa aplicado en el backend y cubierto por pruebas.
- API versionada, esquema OpenAPI y Swagger.
- Interfaz responsive en español y estructura preparada para PWA.
- Comando de datos de demostración de la Fase 1.

El marketplace y las cotizaciones aparecen en las fases siguientes descritas en el roadmap.

## Estado de la Fase 2

- Clientes con búsqueda, datos chilenos y archivado cuando tienen historial.
- Categorías, productos, variantes flexibles, precios, stock y opciones de personalización.
- Pedidos correlativos por empresa, identificador público UUID, ítems personalizados y estados.
- Cálculo servidor de subtotal, descuento, despacho, total, pagos y saldo.
- Historial inmutable de cambios de estado.
- Pagos manuales, anulación lógica y prevención de sobrepagos.
- Dashboard con métricas operativas y montos mensuales.
- Tablero de producción horizontal con cambios rápidos de estado.
- API con búsqueda, filtros, ordenamiento y paginación.
- Interfaz responsive para clientes, productos, pedidos, pagos y producción.

## Estado de la Fase 3

- Tienda pública por empresa en `/tienda/<slug>`.
- Identidad visual con logo, banner y colores configurables.
- Catálogo público con búsqueda y filtro por categoría.
- Ficha de producto, variantes, cantidad mínima y plazo estimado.
- Solicitud directa como invitado, creada como pedido de origen `public_store`.
- Precio, empresa y variante validados siempre en el servidor.
- Rate limiting para solicitudes públicas y respuesta sin datos privados.
- Control del propietario para publicar u ocultar la tienda.

## Estado de la Fase 4

- Home público con buscador principal “¿Qué quieres personalizar?”.
- Productos y emprendimientos destacados con posición y vigencia administrables.
- Filtros por categoría, región, modalidad de precio y tipo de entrega.
- Productos recientes y etiquetas de producción rápida.
- Moderación de productos con estados pendiente, aprobado, rechazado y oculto.
- Campos de moderación y destaque protegidos contra cambios desde cuentas de empresa.
- Navegación directa desde el marketplace hacia cada tienda y producto.

## Estado de la Fase 5

- Solicitud pública general de cotización con identificador UUID seguro.
- Coincidencias determinísticas por categoría, producto, región, entrega y capacidad.
- Máximo configurable de empresas seleccionadas y exclusión de empresas no verificadas.
- Datos de contacto ocultos antes de aceptar una propuesta.
- Propuestas privadas: cada empresa solo ve sus propios precios y conversaciones.
- Comparación pública de precio, entrega, plazo, abono y condiciones.
- Mensajería asociada a cada propuesta mediante actualización periódica.
- Aceptación transaccional: bloquea doble aceptación, rechaza alternativas y crea el pedido ganador.
- Datos demo con una solicitud y dos propuestas.

## Estado de la Fase 6

- Archivos de pedido clasificados como referencia, borrador, diseño final, comprobante o producto terminado.
- Validación por extensión, MIME, firma binaria y límite de 10 MB.
- Descargas privadas aisladas por empresa.
- Enlaces de aprobación UUID revocables y con vencimiento.
- Revisión pública de diseños, aprobación y solicitudes de cambio.
- Registro inmutable de persona, comentario, fecha, IP e historial de estados.
- Ficha de producción PDF descargable por pedido.
- Panel responsive para cargar archivos y crear enlaces de aprobación.
- Mensajería de propuestas preparada con actualización periódica.
- Plantillas de WhatsApp configurables y accesos rápidos por pedido.
- Correos transaccionales para solicitudes, propuestas, diseños y notificaciones internas, con transporte SMTP configurable.
- Galería multiimagen y opciones flexibles de personalización por producto, incluidos archivos protegidos en pedidos públicos.
- Catálogo local de las 16 regiones y 346 comunas de Chile, expuesto por API y validado en el backend para evitar combinaciones inconsistentes.
- Superadministración de usuarios, asignación de planes, estado de suscripciones y moderación de solicitudes sin revelar datos privados del cliente.
- Panel React exclusivo para superadministradores con métricas globales, gestión de empresas y moderación de productos públicos.
- Auditoría persistente de pedidos, pagos, archivos, diseños, propuestas y acciones de moderación, visible como actividad reciente en el panel de plataforma.
- Notificaciones internas por usuario y empresa para pedidos públicos, cotizaciones compatibles, propuestas aceptadas y respuestas de diseño.
- Administración de empresas y productos destacados desde el panel de plataforma, con posición, vigencia, motivo y modalidad pagada preparados en el modelo.
- Reportes privados por período con ventas, pagos, saldos, ticket promedio, pedidos por estado y productos más vendidos.
- Consumo del plan visible por empresa y editor exclusivo del superadministrador para precios y límites configurables.
- Centro de documentos con fichas de producción, propuestas comerciales y comprobantes de pago en PDF.
- Solicitudes públicas protegidas por un token de acceso independiente del identificador visible; leer, conversar o aceptar requiere el enlace privado completo.
- Adjuntos de cotización validados por extensión, MIME y firma; los archivos del cliente solo llegan a empresas seleccionadas y los de propuesta quedan privados por empresa.
- Normalización y validación en backend para teléfonos chilenos y RUT, aplicada aunque el formulario sea omitido mediante llamadas directas a la API.

## Arquitectura

```text
Navegador React ── cookies JWT + CSRF ──> API Django REST ──> PostgreSQL
                                            │
                              membresía autenticada → empresa
                                            │
                              consultas siempre filtradas por empresa
```

El modelo `BusinessMembership` relaciona usuarios y empresas y contiene el rol. Los endpoints privados resuelven la empresa desde la membresía autenticada; nunca aceptan `business_id` como autoridad. Los superadministradores usan las capacidades nativas de Django Admin. Los archivos se guardan localmente bajo `MEDIA_ROOT`; los campos `ImageField` permiten migrar más tarde a un storage S3 sin cambiar los modelos.

## Inicio rápido con Docker

1. Copia `.env.example` como `.env` y cambia las claves de ejemplo.
2. Inicia los servicios:

   ```bash
   docker compose up --build
   ```

3. Abre:

   - Aplicación: <http://localhost:5173>
   - API: <http://localhost:8000/api/v1/>
   - Swagger: <http://localhost:8000/api/docs/>
   - Administración Django: <http://localhost:8000/admin/>

Las migraciones se ejecutan automáticamente al iniciar el backend.

## Variables de entorno

| Variable | Uso |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Base de datos local |
| `DATABASE_URL` | Conexión del backend a PostgreSQL |
| `DJANGO_SECRET_KEY` | Firma criptográfica; debe ser larga y privada |
| `DJANGO_DEBUG` | Solo `true` durante desarrollo |
| `DJANGO_ALLOWED_HOSTS` | Hosts admitidos por Django |
| `CORS_ALLOWED_ORIGINS` | Orígenes autorizados para el navegador |
| `CSRF_TRUSTED_ORIGINS` | Orígenes confiables para solicitudes mutables |
| `JWT_COOKIE_SECURE` | Usar `true` bajo HTTPS en producción |
| `VITE_API_URL` | URL pública de la API para React |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT` | Transporte de correo; consola durante desarrollo |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Credenciales SMTP, solo en `.env` |
| `DEFAULT_FROM_EMAIL` | Remitente de las notificaciones |
| `STORAGE_BACKEND` | `local` en desarrollo o `s3` en producción |
| `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME` | Bucket privado y región del almacenamiento |
| `AWS_S3_ENDPOINT_URL` | Endpoint opcional para proveedores compatibles con S3 |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Credenciales del almacenamiento, solo en `.env` o secretos del entorno |
| `AWS_QUERYSTRING_EXPIRE` | Duración de las URLs firmadas; 900 segundos por defecto |
| `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_COOKIE_SECURE` | Deben ser `true` detrás de HTTPS en producción |
| `DJANGO_HSTS_SECONDS` | HSTS; habilitar después de confirmar HTTPS en todo el dominio |

## Comandos de desarrollo

```bash
# Pruebas
docker compose run --rm backend pytest

# Validar modelos y crear migraciones futuras
docker compose run --rm backend python manage.py makemigrations --check --dry-run

# Datos de demostración
docker compose run --rm backend python manage.py seed_demo

# Compilar frontend
docker compose run --rm frontend npm run build
```

GitHub Actions ejecuta migraciones, las pruebas del backend, la validación de OpenAPI y la compilación del frontend en cada push a `main` y en cada pull request. Swagger documenta la cookie HttpOnly `access_token` como `cookieJWT` y el encabezado CSRF requerido para escrituras.

## Credenciales de demostración

Se crean solo al ejecutar `seed_demo`:

| Tipo | Correo | Contraseña |
|---|---|---|
| Superadministrador | `admin@estampaflow.local` | `Demo-Admin-2026` |
| Propietario | `aurora@demo.cl` | `Demo-Owner-2026` |
| Colaborador | `equipo@aurora.demo.cl` | `Demo-Team-2026` |

Estas credenciales son exclusivamente locales. El comando no se ejecuta automáticamente.

## Decisiones técnicas

- **JWT en cookies HttpOnly:** limita la exposición de tokens a scripts; las escrituras además requieren CSRF.
- **Una membresía activa por contexto en esta fase:** el modelo permite varias membresías, y una selección explícita de empresa se agregará cuando el producto necesite usuarios multiempresa.
- **Registro activa la empresa:** permite probar el recorrido completo en el MVP. La moderación `pending/active/suspended/rejected` ya existe para aplicar aprobación cuando entre el panel de plataforma.
- **Redis diferido:** no hay tareas en segundo plano en la Fase 1; se agregará junto con notificaciones.
- **Planes configurables:** los límites viven en la base de datos y el backend valida pedidos mensuales, productos públicos, usuarios y respuestas a cotizaciones. El almacenamiento queda preparado como límite configurable.
- **PWA preparada:** el frontend incluye manifiesto instalable y un service worker básico para cargar la interfaz cuando falla la red.
- **Archivos locales o S3:** desarrollo usa el volumen local. Con `STORAGE_BACKEND=s3`, Django guarda archivos en un bucket privado y genera URLs firmadas con vencimiento.

## Roadmap

1. **Base SaaS (completa):** autenticación, empresas, roles y aislamiento.
2. **Administración interna (completa):** clientes, catálogo, pedidos, pagos, dashboard y producción.
3. **Tiendas públicas (completa):** tienda, catálogo y solicitudes directas.
4. **Marketplace (completa):** búsqueda, filtros, destacados y moderación.
5. **Cotizaciones (completa):** coincidencias, propuestas, conversación y aceptación atómica.
6. **Diseños y comunicación (completa):** archivos privados, aprobación, PDFs, WhatsApp configurable y correo preparado para SMTP.
7. **Estabilización (completa):** planes y límites, endurecimiento de enlaces públicos, PWA, rendimiento, seeds integrales y documentación final.

El panel de plataforma está disponible en `/plataforma` al ingresar con una cuenta superadministradora.

Fuera del MVP: aplicación nativa, editor gráfico avanzado, facturación SII, pagos en línea, comisiones automáticas, API oficial de WhatsApp, despachos automáticos, WebSockets, IA, sistema completo de calificaciones y dominios personalizados funcionales.
