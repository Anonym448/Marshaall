# 🚀 Guía rápida: Generar alertas y estadísticas en Marshaall

## ✅ Estado actual del sistema

Tu sistema Marshaall SIEM está **funcionando correctamente**:
- ✅ Suricata instalado (versión 7.0.3)
- ✅ Archivo EVE JSON activo (19MB, 3308 líneas)
- ✅ Todos los contenedores Docker corriendo
- ✅ API respondiendo correctamente
- ✅ Servicio de ingesta activo (211 eventos procesados)
- ✅ Frontend accesible en http://localhost

**IP de tu host WSL**: `172.31.222.5`

---

## 🎯 Método 1: Generar eventos de prueba (RÁPIDO)

### Desde WSL (Windows Host)

```bash
# Generar 100 eventos de prueba
cd /home/user/marshaall
sudo ./scripts/generar_eventos_prueba.sh 100

# Ver el resultado en tiempo real
docker logs -f marshaall-ingest --tail 20
```

**Resultado esperado**: Verás alertas de diferentes tipos (malware, escaneos, SQL injection, etc.) en el dashboard inmediatamente.

---

## 🔥 Método 2: Generar tráfico real desde Kali Linux

### Paso 1: Preparar Kali Linux

1. **Asegúrate de que Kali puede alcanzar tu host Windows**:
   ```bash
   # En Kali Linux
   ping -c 4 172.31.222.5
   ```

2. **Copia el script de ataques a Kali**:
   ```bash
   # Opción A: Desde Windows, copia el archivo
   # El archivo está en: \\wsl.localhost\Ubuntu\home\user\marshaall\scripts\kali_ataques.sh
   
   # Opción B: Descarga directamente en Kali
   # (si tienes acceso SSH al host)
   scp usuario@172.31.222.5:/home/user/marshaall/scripts/kali_ataques.sh ~/
   ```

### Paso 2: Ejecutar Ataques desde Kali

```bash
# En Kali Linux
chmod +x kali_ataques.sh
sudo ./kali_ataques.sh 172.31.222.5
```

**El script ejecutará automáticamente**:
- ✅ Escaneo de puertos con Nmap (SYN, XMAS, version detection)
- ✅ Escaneo web con Nikto
- ✅ Intentos de SQL Injection
- ✅ Múltiples conexiones SSH
- ✅ Tráfico HTTP con User-Agents sospechosos
- ✅ ICMP Flood controlado
- ✅ Escaneo SMB

### Paso 3: Verificar Alertas en el Dashboard

1. Abre tu navegador: **http://localhost**
2. Login: `admin` / `admin1234`
3. Verás las alertas en tiempo real

---

## 📊 Verificar el sistema

```bash
# Ejecutar script de verificación completa
cd /home/user/marshaall
./scripts/verificar_sistema.sh
```

---

## 🛠️ Comandos útiles

### Ver eventos en tiempo real
```bash
# Ver todas las alertas en tiempo real
wsl sudo tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"'

# Ver logs de ingesta
docker logs -f marshaall-ingest --tail 50

# Contar alertas generadas
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | wc -l
```

### Consultar la base de datos
```bash
# Conectar a MariaDB
docker exec -it marshaall-mariadb mariadb -u marshaall -p marshaall

# Dentro de MySQL:
SELECT COUNT(*) FROM events;
SELECT COUNT(*) FROM events WHERE event_type = 'alert';
SELECT signature, COUNT(*) as cnt FROM events WHERE event_type = 'alert' GROUP BY signature ORDER BY cnt DESC LIMIT 10;
```

### Generar reportes XML
```bash
# Desde el navegador, ve a la sección "Reporte XML" en el dashboard
# O usa curl:
curl -H "Authorization: Bearer <TOKEN>" \
  "http://localhost/api/reports/events.xml?range=24h" -o reporte.xml
```

---

## 🎯 Ataques manuales desde Kali (sin script)

### Escaneo Nmap
```bash
# Escaneo SYN
sudo nmap -sS -p 1-1000 172.31.222.5

# Escaneo XMAS
sudo nmap -sX -p 80,443,22 172.31.222.5

# Escaneo agresivo
sudo nmap -A -T4 172.31.222.5
```

### SQL Injection
```bash
curl "http://172.31.222.5/?id=1' OR '1'='1"
curl "http://172.31.222.5/?id=1; DROP TABLE users--"
```

### Nikto
```bash
nikto -h http://172.31.222.5
```

### Hydra (Fuerza bruta SSH)
```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://172.31.222.5 -t 4
```

---

## 🔧 Troubleshooting

### Problema: No se generan alertas

**Solución 1: Verificar que Suricata está corriendo**
```bash
wsl sudo systemctl status suricata

# Si no está corriendo:
wsl sudo systemctl start suricata
```

**Solución 2: Actualizar reglas de Suricata**
```bash
wsl sudo suricata-update
wsl sudo systemctl restart suricata
```

### Problema: El servicio de ingesta no procesa eventos

```bash
# Ver logs
docker logs marshaall-ingest --tail 100

# Reiniciar el servicio
docker restart marshaall-ingest
```

### Problema: No hay conectividad entre Kali y Host

1. **Verifica la configuración de red de la VM**:
   - Debe estar en modo **Bridge** (no NAT)
   
2. **Desactiva temporalmente el firewall de Windows**:
   ```powershell
   # En PowerShell como Administrador
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   ```

3. **Verifica IPs**:
   ```bash
   # En Kali
   ip addr show
   
   # En Windows WSL
   wsl ip addr show
   ```

---

## 📈 Estadísticas esperadas

Después de ejecutar los scripts, deberías ver en el dashboard:

- **Total de eventos**: +50 a +1000 (dependiendo de cuántos generes)
- **Alertas por severidad**:
  - Alta (1): ~30%
  - Media (2): ~40%
  - Baja (3): ~30%
- **Top firmas**:
  - ET MALWARE Possible Trojan
  - GPL SCAN nmap XMAS
  - ET SCAN Potential SSH Scan
  - ET WEB_SERVER SQL Injection Attempt
  - ET DOS ICMP Flood

---

## 🎓 Próximos pasos

1. ✅ **Generar eventos de prueba** (ya lo hiciste)
2. ✅ **Verificar dashboard** (http://localhost)
3. 🔄 **Generar tráfico real desde Kali**
4. 📊 **Crear incidentes** agrupando alertas relacionadas
5. 📄 **Exportar reportes XML** para auditoría
6. 🔍 **Usar correlación** para detectar patrones

---

## 📞 Acceso al dashboard

- **URL**: http://localhost (o http://172.31.222.5)
- **Usuario**: `admin`
- **Contraseña**: `admin1234`

---

## 📚 Documentación completa

Para más detalles, consulta:
- `docs/GUIA_GENERACION_ALERTAS.md` - Guía completa paso a paso
- `README.md` - Documentación general del proyecto

---

**¡Listo para generar alertas y estadísticas!** 🚀
