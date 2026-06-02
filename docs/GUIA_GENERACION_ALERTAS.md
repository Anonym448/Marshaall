# 🚨 Guía completa: Generación de alertas y estadísticas en Marshaall

## 📋 Tabla de contenidos
1. [Introducción](#introducción)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Método 1: Generar Tráfico desde Kali Linux](#método-1-generar-tráfico-desde-kali-linux)
4. [Método 2: Generar Eventos de Prueba Manualmente](#método-2-generar-eventos-de-prueba-manualmente)
5. [Verificar Alertas en el Dashboard](#verificar-alertas-en-el-dashboard)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Introducción

Este documento te guiará paso a paso para generar alertas y registros en tu sistema Marshaall SIEM, permitiéndote visualizar estadísticas y probar todas las funcionalidades del dashboard.

### ¿Cómo funciona el flujo de datos?

```
Kali Linux (Atacante) 
    ↓ (tráfico malicioso)
Windows Host / WSL (Víctima)
    ↓ (captura de red)
Suricata (IDS/IPS)
    ↓ (genera eve.json)
Servicio Ingest
    ↓ (parsea y almacena)
MariaDB
    ↓ (consultas)
Backend API
    ↓ (visualización)
Frontend Dashboard
```

---

## 🏗️ Arquitectura del sistema

### Componentes Actuales

- **Suricata**: `/usr/bin/suricata` - Instalado en WSL Ubuntu
- **Logs**: `/var/log/suricata/eve.json` - Archivo EVE JSON con eventos
- **Docker Compose**: 4 contenedores activos
  - `marshaall-mariadb`: Base de datos
  - `marshaall-ingest`: Servicio de ingesta de eventos
  - `marshaall-backend`: API REST
  - `marshaall-nginx`: Proxy reverso + frontend

---

## 🔥 Método 1: Generar tráfico desde Kali Linux

### Paso 1.1: Configurar red entre Kali y host

#### Opción A: Kali en VirtualBox/VMware (Red Bridged)

1. **En Kali Linux**, verifica tu IP:
```bash
ip addr show
# Anota tu IP, por ejemplo: 192.168.1.50
```

2. **En Windows Host**, verifica tu IP:
```powershell
ipconfig
# Anota tu IP en la misma red, por ejemplo: 192.168.1.100
```

3. **Prueba conectividad** desde Kali:
```bash
ping -c 4 192.168.1.100
```

#### Opción B: Kali en VirtualBox (Red NAT + Port Forwarding)

Si Kali está en NAT, necesitas configurar port forwarding o cambiar a modo Bridge.

**Cambiar a Bridge en VirtualBox:**
1. Apaga la VM de Kali
2. Configuración → Red → Adaptador 1
3. Conectado a: **Adaptador puente**
4. Enciende la VM

---

### Paso 1.2: Verificar interfaz de red en Suricata

1. **En WSL**, verifica qué interfaces tiene Suricata configuradas:
```bash
wsl sudo suricata --list-runmodes
wsl sudo suricata --build-info | grep -i interface
```

2. **Verifica la configuración de Suricata**:
```bash
wsl sudo cat /etc/suricata/suricata.yaml | grep -A 5 "af-packet:"
```

3. **Identifica la interfaz de red activa**:
```bash
wsl ip link show
# Busca la interfaz principal, usualmente 'eth0' o 'ens33'
```

4. **Si Suricata no está escuchando en la interfaz correcta**, edita la configuración:
```bash
wsl sudo nano /etc/suricata/suricata.yaml
```

Busca la sección `af-packet` y asegúrate de que esté configurada para tu interfaz:
```yaml
af-packet:
  - interface: eth0  # Cambia esto a tu interfaz
    cluster-id: 99
    cluster-type: cluster_flow
    defrag: yes
```

5. **Reinicia Suricata**:
```bash
wsl sudo systemctl restart suricata
# O si no usa systemd:
wsl sudo killall suricata
wsl sudo suricata -c /etc/suricata/suricata.yaml -i eth0 -D
```

---

### Paso 1.3: Generar tráfico malicioso desde Kali

#### 🎯 Ataque 1: Escaneo de Puertos con Nmap

```bash
# En Kali Linux
# Reemplaza 192.168.1.100 con la IP de tu Windows Host

# Escaneo SYN (genera alertas "GPL SCAN nmap")
sudo nmap -sS 192.168.1.100

# Escaneo completo de puertos
sudo nmap -p- 192.168.1.100

# Escaneo con detección de OS
sudo nmap -O 192.168.1.100

# Escaneo agresivo (genera múltiples alertas)
sudo nmap -A -T4 192.168.1.100
```

**Alertas esperadas:**
- `GPL SCAN nmap XMAS`
- `GPL SCAN nmap fingerprint attempt`
- `ET SCAN Potential SSH Scan`

---

#### 🎯 Ataque 2: Fuerza Bruta SSH

```bash
# En Kali Linux
# Asegúrate de que el host tenga SSH habilitado

# Instalar hydra si no lo tienes
sudo apt-get install hydra -y

# Crear lista de usuarios
echo -e "admin\nroot\nuser\ntest" > users.txt

# Crear lista de contraseñas
echo -e "password\n123456\nadmin\ntest" > passwords.txt

# Ataque de fuerza bruta
hydra -L users.txt -P passwords.txt ssh://192.168.1.100 -t 4
```

**Alertas esperadas:**
- `ET SCAN Potential SSH Scan`
- `GPL SSH brute force login attempt`

---

#### 🎯 Ataque 3: SQL Injection (Simulado)

```bash
# En Kali Linux
# Instalar sqlmap si no lo tienes
sudo apt-get install sqlmap -y

# Si tienes un servidor web en el host:
sqlmap -u "http://192.168.1.100/page.php?id=1" --batch --risk=3 --level=5

# O simplemente genera tráfico HTTP sospechoso:
curl "http://192.168.1.100/?id=1' OR '1'='1"
curl "http://192.168.1.100/?id=1; DROP TABLE users--"
```

**Alertas esperadas:**
- `ET WEB_SERVER SQL Injection Attempt`
- `ET ATTACK_RESPONSE SQL Error Message`

---

#### 🎯 Ataque 4: Escaneo de Vulnerabilidades con Nikto

```bash
# En Kali Linux
sudo apt-get install nikto -y

# Escaneo de vulnerabilidades web
nikto -h http://192.168.1.100
```

**Alertas esperadas:**
- `ET SCAN Nikto Scan in Progress`
- `ET WEB_SERVER Suspicious User-Agent`

---

#### 🎯 Ataque 5: Metasploit (Simulación de Exploit)

```bash
# En Kali Linux
msfconsole

# Dentro de Metasploit:
use auxiliary/scanner/portscan/tcp
set RHOSTS 192.168.1.100
set PORTS 1-1000
run

# Escaneo de SMB
use auxiliary/scanner/smb/smb_version
set RHOSTS 192.168.1.100
run
```

---

#### 🎯 Ataque 6: Tráfico ICMP Flood (DoS Simulado)

```bash
# En Kali Linux
# CUIDADO: Esto puede saturar la red

# Ping flood (requiere root)
sudo hping3 -1 --flood 192.168.1.100

# O un ping más controlado:
ping -f -c 1000 192.168.1.100
```

**Alertas esperadas:**
- `ET DOS ICMP Flood`
- `GPL ICMP_INFO PING *NIX`

---

#### 🎯 Ataque 7: Descarga de Malware Simulado (EICAR Test File)

```bash
# En Kali Linux
# Descarga el archivo de prueba EICAR (NO es malware real, es un archivo de prueba)

# Desde Kali, intenta descargar a través del host:
wget http://192.168.1.100/eicar.com

# O genera tráfico HTTP con el patrón EICAR:
curl -A "X5O!P%@AP[4\PZX54(P^)7CC)7}\$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!\$H+H*" http://192.168.1.100
```

---

### Paso 1.4: Verificar que Suricata Está Capturando

```bash
# En WSL
# Ver los últimos eventos en tiempo real:
wsl sudo tail -f /var/log/suricata/eve.json

# Contar eventos de tipo "alert":
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | wc -l

# Ver las últimas 5 alertas:
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | tail -5 | jq .
```

---

## 📝 Método 2: Generar eventos de prueba manualmente

Si no puedes generar tráfico real desde Kali, puedes inyectar eventos directamente en el archivo EVE JSON.

### Paso 2.1: Crear Archivo de Eventos de Prueba

```bash
# En WSL
cat > /tmp/eventos_prueba.json << 'EOF'
{"timestamp":"2026-02-16T22:00:00.000000+0100","event_type":"alert","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":44123,"dest_port":443,"proto":"TCP","flow_id":12345678,"alert":{"signature":"ET MALWARE Possible Trojan","category":"A Network Trojan was Detected","severity":1}}
{"timestamp":"2026-02-16T22:00:05.000000+0100","event_type":"alert","src_ip":"10.0.0.5","dest_ip":"192.168.1.100","src_port":80,"dest_port":52100,"proto":"TCP","flow_id":87654321,"alert":{"signature":"GPL SCAN nmap XMAS","category":"Attempted Information Leak","severity":2}}
{"timestamp":"2026-02-16T22:00:10.000000+0100","event_type":"alert","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":22,"dest_port":12345,"proto":"TCP","flow_id":11111111,"alert":{"signature":"ET SCAN Potential SSH Scan","category":"Attempted Information Leak","severity":2}}
{"timestamp":"2026-02-16T22:00:15.000000+0100","event_type":"alert","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":80,"dest_port":54321,"proto":"TCP","flow_id":22222222,"alert":{"signature":"ET WEB_SERVER SQL Injection Attempt","category":"Web Application Attack","severity":1}}
{"timestamp":"2026-02-16T22:00:20.000000+0100","event_type":"flow","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":44123,"dest_port":443,"proto":"TCP","flow_id":12345678}
{"timestamp":"2026-02-16T22:00:25.000000+0100","event_type":"alert","src_ip":"10.0.0.5","dest_ip":"192.168.1.100","src_port":443,"dest_port":52200,"proto":"TCP","flow_id":33333333,"alert":{"signature":"ET POLICY Suspicious User-Agent","category":"Potentially Bad Traffic","severity":3}}
{"timestamp":"2026-02-16T22:00:30.000000+0100","event_type":"alert","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":1234,"dest_port":445,"proto":"TCP","flow_id":44444444,"alert":{"signature":"ET EXPLOIT SMB Vulnerability","category":"Attempted Administrator Privilege Gain","severity":1}}
{"timestamp":"2026-02-16T22:00:35.000000+0100","event_type":"alert","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":5555,"dest_port":80,"proto":"TCP","flow_id":55555555,"alert":{"signature":"ET DOS ICMP Flood","category":"Denial of Service","severity":2}}
{"timestamp":"2026-02-16T22:00:40.000000+0100","event_type":"dns","src_ip":"192.168.1.50","dest_ip":"8.8.8.8","src_port":53123,"dest_port":53,"proto":"UDP","flow_id":66666666}
{"timestamp":"2026-02-16T22:00:45.000000+0100","event_type":"alert","src_ip":"192.168.1.50","dest_ip":"10.0.0.1","src_port":8080,"dest_port":443,"proto":"TCP","flow_id":77777777,"alert":{"signature":"ET MALWARE Ransomware Activity Detected","category":"A Network Trojan was Detected","severity":1}}
EOF
```

### Paso 2.2: Inyectar Eventos en el Archivo EVE JSON

```bash
# OPCIÓN A: Añadir al final del archivo actual (RECOMENDADO)
wsl sudo cat /tmp/eventos_prueba.json >> /var/log/suricata/eve.json

# OPCIÓN B: Reemplazar todo el archivo (CUIDADO: borra eventos existentes)
# wsl sudo cp /tmp/eventos_prueba.json /var/log/suricata/eve.json
```

### Paso 2.3: Verificar que el Servicio de Ingesta los Procesa

```bash
# Ver logs del contenedor de ingesta
docker logs -f marshaall-ingest --tail 50
```

Deberías ver algo como:
```
[ingest] 2026-02-16 22:01:00 INFO Batch: +10 insertados (total: 150, dupes: 5, errores: 0)
```

---

## 📊 Verificar alertas en el dashboard

### Paso 3.1: Acceder al Dashboard

1. Abre tu navegador en: **http://localhost**
2. Inicia sesión con:
   - **Usuario**: `admin`
   - **Contraseña**: `admin1234`

### Paso 3.2: Verificar Estadísticas

1. **Panel Principal (`#dashboard`)**:
   - Verás tarjetas con:
     - Total de eventos
     - Total de alertas
     - Alertas abiertas
     - Incidentes abiertos
     - Eventos últimas 24h
   - Gráfico de barras apiladas "Eventos por minuto"
   - Tabla con las 10 alertas más recientes

2. **Alertas (`#alerts`)**:
   - Tabla paginada con todas las alertas
   - Filtros por severidad, estado, búsqueda
   - Click en una fila para ver detalles

3. **Eventos (`#events`)**:
   - Todos los eventos (no solo alertas)
   - Gráfico temporal

4. **Estado (`#health`)**:
   - Estado de API, BD, ingesta
   - Último evento recibido
   - Lag en segundos

### Paso 3.3: Generar Reporte XML

1. En el dashboard, ve a la tarjeta **"Reporte XML"**
2. Selecciona el rango (1h, 6h, 24h, 7d, 30d)
3. Click en **"Descargar Reporte"**
4. Se descargará un archivo XML con estilos profesionales

---

## 🔧 Troubleshooting

### Problema 1: No se generan alertas

**Diagnóstico:**
```bash
# Verificar que Suricata está corriendo
wsl sudo systemctl status suricata

# Ver logs de Suricata
wsl sudo tail -100 /var/log/suricata/suricata.log

# Verificar reglas cargadas
wsl sudo suricata-update list-enabled-sources
```

**Solución:**
```bash
# Actualizar reglas de Suricata
wsl sudo suricata-update

# Reiniciar Suricata
wsl sudo systemctl restart suricata
```

---

### Problema 2: El servicio de ingesta no procesa eventos

**Diagnóstico:**
```bash
# Ver logs del contenedor
docker logs marshaall-ingest --tail 100

# Verificar que el volumen está montado correctamente
docker inspect marshaall-ingest | grep -A 10 Mounts
```

**Solución:**
```bash
# Reiniciar el contenedor de ingesta
docker restart marshaall-ingest

# Verificar permisos del archivo EVE JSON
wsl sudo chmod 644 /var/log/suricata/eve.json
```

---

### Problema 3: No hay conectividad entre Kali y Host

**Diagnóstico:**
```bash
# En Kali
ping -c 4 <IP_DEL_HOST>

# En Windows
ping <IP_DE_KALI>
```

**Solución:**
1. Verifica que ambas máquinas estén en la misma red
2. Desactiva temporalmente el firewall de Windows:
   ```powershell
   # En PowerShell como Administrador
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   ```
3. Verifica la configuración de red de la VM (Bridge vs NAT)

---

### Problema 4: Suricata no captura tráfico

**Diagnóstico:**
```bash
# Verificar interfaz de red
wsl ip link show

# Verificar configuración de Suricata
wsl sudo cat /etc/suricata/suricata.yaml | grep -A 5 "af-packet"
```

**Solución:**
```bash
# Editar configuración
wsl sudo nano /etc/suricata/suricata.yaml

# Buscar y modificar la interfaz:
# af-packet:
#   - interface: eth0  # Cambia a tu interfaz

# Reiniciar
wsl sudo systemctl restart suricata
```

---

## 📈 Ejemplos de comandos útiles

### Ver estadísticas en tiempo real

```bash
# Eventos por tipo
wsl jq -r '.event_type' /var/log/suricata/eve.json | sort | uniq -c

# Top 10 firmas de alertas
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | jq -r '.alert.signature' | sort | uniq -c | sort -rn | head -10

# IPs más atacadas
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | jq -r '.dest_ip' | sort | uniq -c | sort -rn | head -10

# IPs atacantes
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | jq -r '.src_ip' | sort | uniq -c | sort -rn | head -10
```

### Consultas SQL directas

```bash
# Conectar a la base de datos
docker exec -it marshaall-mariadb mysql -u marshaall -p marshaall

# Dentro de MySQL:
SELECT COUNT(*) FROM events;
SELECT COUNT(*) FROM events WHERE event_type = 'alert';
SELECT signature, COUNT(*) as cnt FROM events WHERE event_type = 'alert' GROUP BY signature ORDER BY cnt DESC LIMIT 10;
```

---

## 🎓 Resumen de comandos rápidos

### Generar 100 alertas rápidamente desde Kali:

```bash
# Escaneo masivo
for i in {1..100}; do sudo nmap -sS -p 1-100 192.168.1.100 & done

# Ping flood controlado
for i in {1..100}; do ping -c 10 192.168.1.100 & done
```

### Inyectar 1000 eventos de prueba:

```bash
# Generar eventos en bucle
for i in {1..1000}; do
  echo "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%S.%6N%z)\",\"event_type\":\"alert\",\"src_ip\":\"192.168.1.$((RANDOM%255))\",\"dest_ip\":\"10.0.0.$((RANDOM%255))\",\"src_port\":$((RANDOM%65535)),\"dest_port\":$((RANDOM%65535)),\"proto\":\"TCP\",\"flow_id\":$((RANDOM*RANDOM)),\"alert\":{\"signature\":\"ET TEST Alert $i\",\"category\":\"Test Category\",\"severity\":$((RANDOM%3+1))}}" >> /tmp/bulk_events.json
done

wsl sudo cat /tmp/bulk_events.json >> /var/log/suricata/eve.json
```

---

## ✅ Checklist de verificación

- [ ] Suricata está instalado y corriendo
- [ ] El archivo `/var/log/suricata/eve.json` existe y se está actualizando
- [ ] Los contenedores Docker están activos (`docker compose ps`)
- [ ] El servicio de ingesta está procesando eventos (`docker logs marshaall-ingest`)
- [ ] Puedo acceder al dashboard en `http://localhost`
- [ ] Veo eventos en la tabla del dashboard
- [ ] Puedo generar tráfico desde Kali hacia el host
- [ ] Las alertas aparecen en el dashboard después de generar tráfico

---

## 🎯 Próximos pasos

1. **Personalizar reglas de Suricata**: Crea tus propias reglas en `/etc/suricata/rules/local.rules`
2. **Configurar correlación**: Usa el endpoint `/api/correlation/suggestions` para agrupar alertas
3. **Crear incidentes**: Agrupa alertas relacionadas en incidentes
4. **Exportar reportes**: Genera reportes XML periódicos para auditoría

---

¡Listo! Ahora tienes todo lo necesario para generar alertas y visualizar estadísticas en tu SIEM Marshaall. 🚀
