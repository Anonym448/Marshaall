# Marshaall SIEM — Diagrama de arquitectura de red interna

## Diagrama completo

> Este diagrama muestra todos los contenedores Docker, el componente nativo Suricata,
> las comunicaciones entre servicios (protocolos y puertos), los volúmenes de persistencia
> y la conexión con la red local del cliente.

```mermaid
graph TB
    subgraph HOST["🖥️ Host — Ubuntu Server / WSL2"]
        direction TB

        SURICATA["🛡️ Suricata 7.x\n\nNativo en host\nCaptura: --pcap=interfaz"]
        EVE[("📄 /var/log/suricata/eve.json")]
        SURICATA -->|"escribe eventos JSON"| EVE

        subgraph DOCKER["🐳 Docker Compose — 5 contenedores"]
            direction TB

            subgraph NET["Red interna: backend_net — bridge aislada"]
                direction LR

                subgraph INGEST_BOX["marshaall-ingest"]
                    INGEST["⚙️ Ingest\nPython 3.12-slim\nTail eve.json\nDeduplicación por flow_id"]
                end

                subgraph DB_BOX["marshaall-mariadb"]
                    MARIADB[("🗄️ MariaDB 11\nPuerto 3306\nCharset utf8mb4")]
                end

                subgraph BACKEND_BOX["marshaall-backend"]
                    BACKEND["🔧 Backend\nFlask 3.0 + Gunicorn\nAPI REST :8000\n33 endpoints\nReportes PDF/XML/CSV"]
                end

                subgraph NGINX_BOX["marshaall-nginx"]
                    NGINX["🌐 Nginx Alpine\nReverse Proxy\nFrontend estático\nProxy /api/* → :8000"]
                end

                subgraph MAIL_BOX["marshaall-mailpit"]
                    MAILPIT["📧 Mailpit\nSMTP :1025\nWeb UI :8025\nBandeja de pruebas"]
                end
            end
        end
    end

    subgraph EXTERNAL["🌍 Red local del cliente — LAN"]
        SWITCH["🔀 Switch de red\nPort mirroring / TAP"]
        BROWSER["💻 Navegador\nAnalista de seguridad"]
    end

    %% === FLUJO DE TRÁFICO DE RED ===
    SWITCH -->|"tráfico espejado\n(capa 2)"| SURICATA

    %% === FLUJO INTERNO ENTRE SERVICIOS ===
    EVE -->|"bind mount\n/data/suricata:ro"| INGEST
    INGEST -->|"INSERT events\nPyMySQL → :3306"| MARIADB
    INGEST -->|"POST /api/notify-alert\nHTTP → :8000\nHeader: X-Internal-Secret"| BACKEND
    BACKEND -->|"SELECT / INSERT\nPyMySQL → :3306"| MARIADB
    BACKEND -->|"SMTP → :1025\nAlertas tiempo real\nReportes diarios"| MAILPIT
    NGINX -->|"proxy_pass\nHTTP → :8000\nRutas: /api/*"| BACKEND

    %% === ACCESO EXTERNO ===
    BROWSER -->|"HTTP :80\nDashboard + API"| NGINX

    %% === VOLÚMENES DE PERSISTENCIA ===
    MARIADB -.->|"Docker volume\ndb_data"| DB_VOL[("💾 db_data\n/var/lib/mysql")]
    INGEST -.->|"Docker volume\ningest_state"| STATE_VOL[("💾 ingest_state\noffset.txt")]

    %% === ESTILOS ===
    classDef host fill:#1a1a2e,stroke:#16213e,color:#e2e8f4
    classDef docker fill:#0d1b2a,stroke:#1b263b,color:#e2e8f4
    classDef service fill:#1b263b,stroke:#3b82f6,color:#e2e8f4,stroke-width:2px
    classDef db fill:#1b263b,stroke:#22c55e,color:#e2e8f4,stroke-width:2px
    classDef external fill:#0f172a,stroke:#f59e0b,color:#e2e8f4
    classDef volume fill:#111827,stroke:#6b7280,color:#94a3b8,stroke-dasharray:5 5

    class HOST host
    class DOCKER docker
    class INGEST,BACKEND,NGINX,MAILPIT,SURICATA service
    class MARIADB db
    class SWITCH,BROWSER external
    class DB_VOL,STATE_VOL,EVE volume
```

---

## Tabla de comunicaciones entre servicios

| Origen | Destino | Protocolo | Puerto | Ruta / Acción |
|---|---|---|---|---|
| Switch de red | Suricata (nativo) | Ethernet L2 | — | Tráfico espejado (port mirroring) |
| Suricata | Disco (`eve.json`) | Fichero | — | Escritura continua de eventos JSON |
| `marshaall-ingest` | `marshaall-mariadb` | MySQL | 3306 | `INSERT INTO events (...)` |
| `marshaall-ingest` | `marshaall-backend` | HTTP POST | 8000 | `/api/notify-alert` + `X-Internal-Secret` |
| `marshaall-backend` | `marshaall-mariadb` | MySQL | 3306 | `SELECT`, `INSERT`, `UPDATE` |
| `marshaall-backend` | `marshaall-mailpit` | SMTP | 1025 | Alertas en tiempo real + reportes diarios |
| `marshaall-nginx` | `marshaall-backend` | HTTP | 8000 | `proxy_pass` para rutas `/api/*` |
| Navegador (LAN) | `marshaall-nginx` | HTTP | **80** | Panel web + API REST |
| Navegador (LAN) | `marshaall-mailpit` | HTTP | **8025** | Interfaz web de correos |

## Puertos expuestos al host

| Servicio | Puerto host | Puerto contenedor | Uso |
|---|---|---|---|
| `marshaall-nginx` | **80** | 80 | Panel web + API REST |
| `marshaall-mailpit` | **8025** | 8025 | Interfaz web de Mailpit |
| `marshaall-mailpit` | **1025** | 1025 | Puerto SMTP de pruebas |

## Volúmenes de persistencia

| Nombre | Tipo | Ruta en contenedor | Función |
|---|---|---|---|
| `db_data` | Docker named volume | `/var/lib/mysql` | Datos de MariaDB |
| `ingest_state` | Docker named volume | `/state/` | Offset de lectura de `eve.json` |
| `/var/log/suricata` | Bind mount (read-only) | `/data/suricata/` | Fichero `eve.json` |
| `./frontend` | Bind mount (read-only) | `/usr/share/nginx/html/` | Frontend estático |
| `./nginx/default.conf` | Bind mount (read-only) | `/etc/nginx/conf.d/default.conf` | Config de Nginx |
| `./db/init` | Bind mount (read-only) | `/docker-entrypoint-initdb.d/` | Scripts SQL iniciales |
| `./frontend/imagenes` | Bind mount (read-only) | `/usr/share/nginx/html/imagenes/` | Logo para reportes |

## Dependencias de arranque (depends_on)

```
mariadb (arranca primero)
  ├── ingest (espera a mariadb)
  └── backend (espera a mariadb)
        └── nginx (espera a backend)

mailpit (independiente, sin dependencias)
```

## Red Docker

| Propiedad | Valor |
|---|---|
| Nombre | `backend_net` |
| Driver | `bridge` (por defecto) |
| Resolución DNS | Automática por nombre de servicio |
| Aislamiento | Completamente aislada del host — solo Nginx expone `:80` |
