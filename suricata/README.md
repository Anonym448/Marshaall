# Marshaall SIEM — Configuración e Integración de Suricata

## ¿Por qué la carpeta suricata/ estaba vacía?

La carpeta `suricata/` es un directorio de **configuración y scripts de apoyo** para el sistema de detección de intrusiones Suricata. El propio Suricata **se instala en el sistema operativo host** (no dentro de Docker), y escribe sus logs directamente en `/var/log/suricata/eve.json`.

El servicio `ingest` de Docker monta el directorio de logs en modo lectura:
```yaml
volumes:
  - /var/log/suricata:/data/suricata:ro
```

## Archivos en esta carpeta

| Fichero | Descripción |
|---------|-------------|
| `suricata.yaml` | Configuración principal de Suricata para Marshaall. Activa EVE JSON logging, configura interfaces de red (eth0 + lo) y tipos de eventos. |
| `local.rules` | Reglas personalizadas de Marshaall (~20 reglas): EICAR, Nmap, OpenVAS, Nessus, Nikto, Nuclei, web scanning, SSH brute-force. |
| `check_suricata.sh` | Script de verificación y gestión de Suricata. |
| `README.md` | Este archivo de documentación. |

---

## Instalación de Suricata (Ubuntu/Debian)

### Paso 1 – Instalar Suricata

```bash
# Opción A: usando el script de Marshaall
bash /home/user/marshaall/suricata/check_suricata.sh install

# Opción B: manualmente
sudo add-apt-repository -y ppa:oisf/suricata-stable
sudo apt-get update
sudo apt-get install -y suricata suricata-update
```

### Paso 2 – Instalar la configuración de Marshaall

```bash
sudo cp /home/user/marshaall/suricata/suricata.yaml /etc/suricata/suricata.yaml
```

### Paso 3 – Ajustar la interfaz de red

Edita `/etc/suricata/suricata.yaml` y cambia `eth0` por tu interfaz real:

```bash
# Ver interfaces disponibles
ip link show

# Editar configuración
sudo nano /etc/suricata/suricata.yaml
# Busca: af-packet → interface: eth0
# Cámbialo por tu interfaz real (ej: eth0, ens3, wlan0, etc.)
```

### Paso 4 – Actualizar las reglas de detección

```bash
sudo suricata-update
```

### Paso 5 – Iniciar Suricata

**En WSL2 (recomendado):**
```bash
# Usa el script de arranque de Marshaall (pcap mode, checksum disabled)
sudo bash /home/user/marshaall/scripts/start_suricata_marshaall.sh

# O manualmente:
sudo suricata --pcap=lo -c /etc/suricata/suricata.yaml -D -k none
```

> **Nota WSL2:** El modo `af-packet` tiene problemas con el ring buffer en WSL2
> ("Frame size bigger than block size"). Usa el modo `pcap` como alternativa fiable.
> Para capturar tráfico externo (eth0), tras un reinicio limpio de WSL:
> `sudo suricata -D --af-packet -k none`

**En Linux nativo / VM:**
```bash
sudo systemctl enable --now suricata

# Verificar que está en marcha
sudo systemctl status suricata
```

**Copiar reglas personalizadas:**
```bash
sudo cp /home/user/marshaall/suricata/local.rules /var/lib/suricata/rules/local.rules
```

**Ver logs en tiempo real:**
```bash
sudo tail -f /var/log/suricata/eve.json | python3 -m json.tool
```

---

## Verificación de la integración con Marshaall

### Generar alertas de prueba
```bash
# Script automatizado con 9 tipos de prueba
sudo bash /home/user/marshaall/scripts/test_alerts.sh

# O pruebas manuales individuales:
curl -A "OpenVAS" http://127.0.0.1         # Scanner OpenVAS
curl -A "Nessus" http://127.0.0.1          # Scanner Nessus
curl -A "Nikto" http://127.0.0.1           # Scanner Nikto
curl -A "Nuclei" http://127.0.0.1          # Scanner Nuclei
curl http://127.0.0.1/wp-admin             # Web scan
curl http://127.0.0.1/.env                 # Web scan
```

### Verificar alertas generadas
```bash
# Ver alertas en eve.json
sudo bash /home/user/marshaall/scripts/show_alerts.sh

# Ver alertas en la base de datos
bash /home/user/marshaall/scripts/query_db.sh

# Ver logs del ingest
docker compose logs -f ingest
```

---

## Troubleshooting

### Eve.json no existe o está vacío

1. Verificar que Suricata está activo: `sudo systemctl status suricata`
2. Verificar que la interfaz configurada en `suricata.yaml` existe: `ip link show`
3. Verificar permisos: `ls -la /var/log/suricata/`
4. Crear el directorio si no existe: `sudo mkdir -p /var/log/suricata && sudo chown suricata:suricata /var/log/suricata`

### El ingest no lee los datos

1. Verificar que el fichero `eve.json` existe: `ls -la /var/log/suricata/eve.json`
2. Verificar los logs del ingest: `docker compose logs ingest`
3. Reiniciar el servicio ingest: `docker compose restart ingest`

### Probar la detección sin tráfico real

```bash
# Crear un evento de prueba manualmente (para desarrollo)
echo '{"timestamp":"2026-02-24T22:00:00.000000+0000","flow_id":999999,"in_iface":"eth0","event_type":"alert","src_ip":"1.2.3.4","src_port":1234,"dest_ip":"192.168.1.100","dest_port":80,"proto":"TCP","alert":{"action":"allowed","gid":1,"signature_id":2100498,"rev":7,"signature":"ET TEST Known Bad Traffic","category":"Misc activity","severity":3},"app_proto":"http"}' \
  | sudo tee -a /var/log/suricata/eve.json
```

---

## Arquitectura del flujo de datos

```
   Red de tráfico
         │
         ▼
   ┌───────────┐
   │  Suricata │  ←── Analiza paquetes en tiempo real
   │  (host)   │      Aplica reglas de detección
   └───────────┘
         │
         │  /var/log/suricata/eve.json   (EVE JSON format)
         │
         ▼
   ┌───────────┐
   │  ingest   │  ←── Servicio Docker que lee el eve.json
   │ (Docker)  │      e inserta eventos en MariaDB
   └───────────┘
         │
         │  MariaDB
         │
         ▼
   ┌───────────┐
   │  backend  │  ←── API REST (Flask)
   │ (Docker)  │
   └───────────┘
         │
         │  Nginx (puerto 80)
         │
         ▼
   ┌───────────┐
   │  frontend │  ←── Dashboard Marshaall (navegador)
   │  (Nginx)  │
   └───────────┘
```
