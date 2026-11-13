# EDÉN - Asistente Empresarial Inteligente

## Descripción General

EDÉN es una aplicación full-stack diseñada para empresas de servicios técnicos (instalaciones, mantenimiento y obras). Permite gestionar cotizaciones, proyectos, control de costos, tareas operativas y administración financiera mediante un asistente empresarial inteligente. Cuenta con un frontend SPA en React 18 y Vite, un backend API en FastAPI con autenticación JWT y persistencia en PostgreSQL o SQLite, y un servidor web Nginx que sirve la SPA y proxya la API.

---

## Contenido del Proyecto

- **api/**: Código backend FastAPI.
- **src/**: Código frontend React.
- **docker-compose.yml**: Orquestación de servicios (db, api, web).
- **web.Dockerfile**: Construcción y despliegue del frontend con Nginx.
- **nginx.conf**: Configuración Nginx para SPA y proxy API.
- **package.json** y **vite.config.js**: Configuración frontend.
- **README.md**: Esta documentación.

---

## Desarrollo Local

### Requisitos Previos

- Docker y Docker Compose instalados.
- Node.js (v18+) y npm para desarrollo frontend local.

### Levantar la Aplicación con Docker Compose

1. Clonar el repositorio:

```bash
git clone <url-del-repositorio>
cd <directorio-del-proyecto>
```

2. Construir y levantar los servicios:

```bash
docker-compose up --build
```

3. Acceder a la aplicación frontend en:

```
http://localhost:8080
```

4. La API estará disponible en:

```
http://localhost:8080/api
```

### Desarrollo Frontend Local (sin Docker)

1. Entrar en la carpeta frontend:

```bash
cd src
```

2. Instalar dependencias:

```bash
npm install
```

3. Ejecutar servidor de desarrollo:

```bash
npm run dev
```

4. Abrir en el navegador:

```
http://localhost:5173
```

> El frontend se conecta automáticamente a la API en `/api` cuando está disponible. Si la API no responde, usa datos de ejemplo como respaldo.

### Desarrollo Backend Local (sin Docker)

1. Entrar en la carpeta api:

```bash
cd api
```

2. Crear y activar entorno virtual:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Instalar dependencias:

```bash
pip install -r requirements.txt
```

4. Ejecutar servidor FastAPI:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. La API estará disponible en:

```
http://localhost:8000/api
```

---

## Usuarios de Prueba

Para facilitar pruebas, se incluyen estos usuarios de ejemplo:

| Usuario   | Contraseña | Descripción                  |
| --------- | ---------- | ----------------------------|
| admin     | admin123   | Usuario administrador        |
| tecnico1  | tecnico123 | Usuario técnico              |
| cliente1  | cliente123 | Usuario cliente              |

> Puede registrar nuevos usuarios desde la pantalla de registro.

---

## Autenticación

- El sistema usa JWT para autenticación.
- El token se guarda en `localStorage` bajo la clave `token`.
- Cada petición a `/api` incluye el header `Authorization: Bearer <token>`.
- Rutas protegidas requieren autenticación.
- Endpoints públicos: `/api/auth/register`, `/api/auth/login`, `/api/health`.

---

## Rutas API Principales

- `POST /api/auth/register` — Registro de usuario (form-urlencoded).
- `POST /api/auth/login` — Login (form-urlencoded).
- `GET /api/auth/me` — Información del usuario autenticado.
- CRUD y lógica de negocio bajo `/api/*` protegidos por JWT.
- `GET /api/health` — Estado del servicio (sin autenticación).

---

## Despliegue en Dokploy

Para desplegar EDÉN en Dokploy, siga estos pasos:

1. Suba el proyecto a un repositorio Git accesible para Dokploy.

2. Configure Dokploy para usar Docker Compose y despliegue desde el archivo `docker-compose.yml` en la raíz del proyecto.

3. Asigne el dominio deseado al puerto **8080** del servicio `web` para que la SPA sea accesible públicamente.

4. Variables de entorno necesarias para el servicio `api`:

   - `AUTH_SECRET`: Clave secreta para firmar JWT (debe ser segura y secreta).
   - `DATABASE_URL`: URL de conexión a la base de datos PostgreSQL. Ejemplo:

     ```
     postgresql+psycopg://studio:studio@db:5432/producto
     ```

   Dokploy debe gestionar el servicio `db` (PostgreSQL) con las credenciales indicadas o usar un servicio externo compatible.

5. El servicio `web` sirve la SPA en el puerto 80 interno, mapeado a 8080 externo para Dokploy.

6. El servicio `api` escucha en el puerto 8000 interno y depende de que la base de datos esté lista.

7. El servicio `db` es PostgreSQL 16-alpine con volumen persistente y healthcheck.

---

## Notas Importantes

- El backend intenta conectarse a PostgreSQL; si falla, usa SQLite local `./app.db` para no detener el arranque.

- El frontend no usa librerías externas para rutas ni UI, solo React y CSS propios.

- La SPA usa fetch con manejo de errores para usar datos de ejemplo si la API no responde.

- Nginx está configurado para servir la SPA y proxear `/api` al backend.

---

## Contacto

Para dudas o soporte, contactar con el equipo de desarrollo de YERUZZA STUDIO.

---

¡Gracias por usar EDÉN, su asistente empresarial inteligente!