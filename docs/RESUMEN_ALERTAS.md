# 📊 Resumen: Generación de alertas y estadísticas - Marshaall SIEM

## ✅ Estado del sistema (verificado)

```
╔════════════════════════════════════════════════════════════╗
║  🎯 MARSHAALL SIEM - SISTEMA OPERATIVO                    ║
╚════════════════════════════════════════════════════════════╝

✅ Suricata 7.0.3          → Instalado y generando eventos
✅ EVE JSON (19MB)          → 3,308 líneas de eventos
✅ Docker Containers (4/4)  → Todos corriendo
✅ API REST                 → Respondiendo OK
✅ Base de Datos            → 254 eventos procesados
✅ Servicio Ingesta         → Activo (procesando en tiempo real)
✅ Frontend                 → Accesible en http://localhost

IP del Host WSL: 172.31.222.5
```

---

## 🚀 Dos métodos para generar alertas

### 📝 Método 1: Eventos de prueba (RÁPIDO - 2 minutos)

**Desde WSL (tu máquina Windows):**

```bash
cd /home/user/marshaall
sudo ./scripts/generar_eventos_prueba.sh 100
```

**¿Qué hace?**
- Genera 100 eventos sintéticos (70% alertas, 30% flows)
- Los inyecta directamente en `/var/log/suricata/eve.json`
- El servicio de ingesta los procesa automáticamente
- Aparecen en el dashboard en ~30 segundos

**Tipos de alertas generadas:**
- 🔴 ET MALWARE Possible Trojan (Severidad Alta)
- 🟠 GPL SCAN nmap XMAS (Severidad Media)
- 🟠 ET SCAN Potential SSH Scan (Severidad Media)
- 🔴 ET WEB_SERVER SQL Injection Attempt (Severidad Alta)
- 🟡 ET POLICY Suspicious User-Agent (Severidad Baja)
- 🔴 ET MALWARE Ransomware Activity Detected (Severidad Alta)

---

### 🔥 Método 2: Tráfico real desde Kali Linux (REALISTA - 10 minutos)

**Requisitos:**
- Máquina virtual Kali Linux
- Conectividad de red entre Kali y tu host Windows

#### Paso 1: Verificar Conectividad

```bash
# En Kali Linux
ping -c 4 172.31.222.5
```

Si no hay respuesta:
1. Cambia la red de la VM a modo **Bridge** (no NAT)
2. Desactiva temporalmente el firewall de Windows

#### Paso 2: Copiar Script a Kali

**Opción A: Manualmente**
1. En Windows, ve a: `\\wsl.localhost\Ubuntu\home\user\marshaall\scripts\kali_ataques.sh`
2. Copia el archivo a Kali (USB, red compartida, etc.)

**Opción B: Por SSH (si tienes acceso)**
```bash
# En Kali
scp usuario@172.31.222.5:/home/user/marshaall/scripts/kali_ataques.sh ~/
```

#### Paso 3: Ejecutar Ataques

```bash
# En Kali Linux
chmod +x kali_ataques.sh
sudo ./kali_ataques.sh 172.31.222.5
```

**El script ejecutará automáticamente:**

| Ataque | Herramienta | Alertas Generadas |
|--------|-------------|-------------------|
| Escaneo de puertos | Nmap | GPL SCAN nmap, ET SCAN |
| Escaneo web | Nikto | ET SCAN Nikto |
| SQL Injection | curl | ET WEB_SERVER SQL Injection |
| Fuerza bruta SSH | ssh | ET SCAN Potential SSH Scan |
| User-Agents sospechosos | curl | ET POLICY Suspicious User-Agent |
| ICMP Flood | ping | ET DOS ICMP Flood |
| Escaneo SMB | smbclient | ET SCAN SMB Enumeration |

---

## 📊 Visualizar estadísticas en el dashboard

### Acceso

```
URL: http://localhost
Usuario: admin
Contraseña: admin1234
```

### Secciones del Dashboard

#### 1. **Panel Principal** (`#dashboard`)
- 📈 **Tarjetas de resumen**:
  - Total de eventos
  - Total de alertas
  - Alertas abiertas
  - Incidentes abiertos
  - Eventos últimas 24h
- 📊 **Gráfico de barras apiladas**: Eventos por minuto (por severidad)
- 📋 **Tabla**: 10 alertas más recientes

#### 2. **Alertas** (`#alerts`)
- Tabla paginada con todas las alertas
- Filtros:
  - Por severidad (Alta/Media/Baja)
  - Por estado (Nueva/Investigación/Cerrada)
  - Por rango de fechas
  - Búsqueda libre (IPs, firmas)
- Click en una alerta → Ver detalles completos

#### 3. **Eventos** (`#events`)
- Todos los eventos (no solo alertas)
- Gráfico temporal
- Tabla paginada

#### 4. **Incidentes** (`#incidents`)
- Crear incidentes agrupando alertas relacionadas
- Asignar severidad y etiquetas
- Comentarios y seguimiento

#### 5. **Correlación** (`#correlation`)
- Sugerencias automáticas de alertas relacionadas
- Agrupar por firma + IP origen
- Crear incidentes con un click

#### 6. **Reportes XML**
- Selector de rango temporal (1h, 6h, 24h, 7d, 30d)
- Descarga XML con estilos profesionales
- Logo de Marshaall incluido

---

## 🛠️ Comandos útiles

### Ver eventos en tiempo real

```bash
# Ver todas las alertas
wsl sudo tail -f /var/log/suricata/eve.json | grep '"event_type":"alert"'

# Ver logs de ingesta
docker logs -f marshaall-ingest --tail 50

# Contar alertas
wsl grep '"event_type":"alert"' /var/log/suricata/eve.json | wc -l
```

### Consultar base de datos

```bash
# Conectar a MariaDB
docker exec -it marshaall-mariadb mariadb -u marshaall -p
# Password: (el que tengas en .env, por defecto marshaall123)

# Dentro de MySQL:
USE marshaall;
SELECT COUNT(*) FROM events;
SELECT COUNT(*) FROM events WHERE event_type = 'alert';
SELECT signature, COUNT(*) as cnt FROM events 
WHERE event_type = 'alert' 
GROUP BY signature 
ORDER BY cnt DESC 
LIMIT 10;
```

### Verificar sistema completo

```bash
cd /home/user/marshaall
./scripts/verificar_sistema.sh
```

---

## 📈 Estadísticas esperadas

Después de ejecutar los scripts, deberías ver:

### Con 100 Eventos de Prueba:
- **Total de eventos**: ~100
- **Alertas**: ~70 (70% del total)
- **Flows**: ~30 (30% del total)
- **Distribución por severidad**:
  - 🔴 Alta (1): ~25 alertas
  - 🟠 Media (2): ~30 alertas
  - 🟡 Baja (3): ~15 alertas

### Con Ataques desde Kali:
- **Total de eventos**: 200-500 (depende de la duración)
- **Alertas**: 50-150
- **Top 5 firmas más comunes**:
  1. GPL SCAN nmap XMAS
  2. ET SCAN Potential SSH Scan
  3. ET POLICY Suspicious User-Agent
  4. ET WEB_SERVER SQL Injection Attempt
  5. ET DOS ICMP Flood

---

## 🎯 Flujo de trabajo completo

```
┌─────────────────────────────────────────────────────────────┐
│  1. GENERAR TRÁFICO                                         │
│     • Método 1: Script de eventos de prueba (rápido)       │
│     • Método 2: Ataques desde Kali (realista)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. SURICATA CAPTURA Y ANALIZA                              │
│     • Genera eventos en /var/log/suricata/eve.json          │
│     • Aplica reglas de detección                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. SERVICIO DE INGESTA PROCESA                             │
│     • Lee eve.json en tiempo real                           │
│     • Parsea JSON y normaliza campos                        │
│     • Inserta en MariaDB                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. API REST EXPONE DATOS                                   │
│     • Endpoints para alertas, eventos, estadísticas         │
│     • Filtros, paginación, búsqueda                         │
│     • Generación de reportes XML                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  5. FRONTEND VISUALIZA                                      │
│     • Dashboard con gráficos (Chart.js)                     │
│     • Tablas interactivas                                   │
│     • Gestión de incidentes                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### ❌ Problema: No se generan alertas

**Diagnóstico:**
```bash
wsl sudo systemctl status suricata
wsl sudo tail -100 /var/log/suricata/suricata.log
```

**Solución:**
```bash
# Actualizar reglas
wsl sudo suricata-update

# Reiniciar Suricata
wsl sudo systemctl restart suricata
```

---

### ❌ Problema: El servicio de ingesta no procesa eventos

**Diagnóstico:**
```bash
docker logs marshaall-ingest --tail 100
docker inspect marshaall-ingest | grep -A 10 Mounts
```

**Solución:**
```bash
# Reiniciar contenedor
docker restart marshaall-ingest

# Verificar permisos
wsl sudo chmod 644 /var/log/suricata/eve.json
```

---

### ❌ Problema: No hay conectividad Kali ↔ Host

**Diagnóstico:**
```bash
# En Kali
ping -c 4 172.31.222.5

# En Windows
ping <IP_DE_KALI>
```

**Solución:**
1. Cambia la red de la VM a **Bridge**
2. Desactiva el firewall de Windows temporalmente:
   ```powershell
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   ```
3. Verifica que ambas máquinas estén en la misma subred

---

## 📚 Archivos creados

```
marshaall/
├── docs/
│   ├── GUIA_GENERACION_ALERTAS.md     ← Guía completa paso a paso
│   ├── QUICKSTART_ALERTAS.md          ← Guía rápida
│   └── RESUMEN_ALERTAS.md             ← Este archivo
├── scripts/
│   ├── generar_eventos_prueba.sh      ← Script para generar eventos
│   ├── kali_ataques.sh                ← Script para ejecutar desde Kali
│   └── verificar_sistema.sh           ← Script de verificación
```

---

## ✅ Checklist de verificación

- [x] Suricata instalado y corriendo
- [x] Archivo EVE JSON existe y se actualiza
- [x] Contenedores Docker activos
- [x] Servicio de ingesta procesando eventos
- [x] Dashboard accesible en http://localhost
- [ ] Eventos de prueba generados
- [ ] Conectividad Kali ↔ Host verificada
- [ ] Ataques desde Kali ejecutados
- [ ] Alertas visibles en el dashboard
- [ ] Reportes XML generados

---

## 🎓 Próximos pasos

1. ✅ **Generar eventos** → Ya tienes los scripts listos
2. 📊 **Visualizar en dashboard** → http://localhost
3. 🔍 **Explorar correlación** → Agrupar alertas relacionadas
4. 📝 **Crear incidentes** → Gestionar casos de seguridad
5. 📄 **Exportar reportes** → XML con estilos profesionales
6. 🎯 **Personalizar reglas** → Crear tus propias reglas en Suricata

---

## 📞 Soporte

Si tienes problemas:

1. **Ejecuta el script de verificación**:
   ```bash
   ./scripts/verificar_sistema.sh
   ```

2. **Revisa los logs**:
   ```bash
   docker logs marshaall-ingest --tail 100
   wsl sudo tail -100 /var/log/suricata/suricata.log
   ```

3. **Consulta la documentación completa**:
   - `docs/GUIA_GENERACION_ALERTAS.md`
   - `README.md`

---

**¡Sistema listo para generar y visualizar alertas!** 🚀🔒

Dashboard: http://localhost (admin / admin1234)
