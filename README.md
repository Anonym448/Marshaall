# 🛡️ Marshaall SIEM

Plataforma SIEM para visibilidad y detección de amenazas en tiempo real mediante Suricata, Flask y MariaDB.

## 🌟 Características principales

- **Detección en Tiempo Real**: Análisis continuo de tráfico mediante Suricata IDS/IPS.
- **Dashboard Interactivo**: Frontend en Vanilla JS para visualización de alertas, estadísticas e incidentes.
- **Backend Robusto**: Desarrollado en Python con Flask para proporcionar una API REST eficiente.
- **Arquitectura en Contenedores**: Orquestación sencilla con Docker Compose que incluye base de datos (MariaDB), ingesta de logs y backend.
- **Alertas y Notificaciones**: Notificaciones por correo electrónico y reportes diarios integrados.

## 🏗️ Arquitectura

Marshaall está compuesto por varios componentes clave:

- **Suricata**: Motor de IDS/IPS (ejecutado nativamente) que monitoriza el tráfico y genera alertas.
- **Ingestor (`ingest/`)**: Servicio en Python que parsea el archivo `eve.json` de Suricata y almacena las alertas en la base de datos MariaDB.
- **Backend API (`backend/`)**: Servidor Flask que expone la información para el dashboard web y maneja la gestión de incidentes y notificaciones.
- **Frontend (`frontend/`)**: Aplicación web estática que consume la API del backend para presentar una interfaz intuitiva al usuario.
- **Nginx & Mailpit**: Servidor proxy inverso para HTTPS y herramienta de testing de emails, respectivamente.

## 🚀 Inicio rápido

Para desplegar la infraestructura utilizando Docker:

```bash
# Iniciar los servicios con Docker Compose
docker-compose up -d

# Para consultar los logs del backend o ingestor:
docker logs marshaall-backend -f
docker logs marshaall-ingest -f
```

## 📚 Documentación

Para información detallada sobre el uso, generación de alertas, y testing, consulta nuestra [Documentación Oficial (Directorio `docs/`)](./docs/README.md). Encontrarás:

- [Quickstart de Alertas](./docs/QUICKSTART_ALERTAS.md)
- [Guía de Generación de Alertas](./docs/GUIA_GENERACION_ALERTAS.md)
- [Testing de Emails](./docs/GUIA_TESTING_EMAILS.md)
- [Arquitectura de Red](./docs/ARQUITECTURA_RED.md)

## 🛠️ Scripts útiles

Dentro de la carpeta `scripts/` dispones de herramientas para interactuar con la plataforma:

- `generar_eventos_prueba.sh`: Para poblar el sistema con datos sintéticos.
- `verificar_sistema.sh`: Verifica que todos los servicios y contenedores están funcionando correctamente.
- `kali_ataques.sh`: Script para simular ataques desde una máquina Kali Linux.

---
**Desarrollado por el equipo Marshaall**
