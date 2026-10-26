[![Licencia](https://img.shields.io/github/license/LozanoTH/balanceador-de-red)](LICENSE)
[![Lenguaje](https://img.shields.io/github/languages/top/LozanoTH/balanceador-de-red)](https://github.com/LozanoTH/balanceador-de-red)

#  Router Pro Manager

```text
  ██▀███   ▒█████   █    ██ ▄▄▄█████▓▓█████  ██▀███  
 ▓██ ▒ ██▒▒██▒  ██▒ ██  ▓██▒▓  ██▒ ▓▒▓█   ▀ ▓██ ▒ ██▒
 ▓██ ░▄█ ▒▒██░  ██▒▓██  ▒██░▒ ▓██░ ▒░▒███   ▓██ ░▄█ ▒
 ▒██▀▀█▄  ▒██   ██░▓▓█  ░██░░ ▓██▓ ░ ▒▓█  ▄ ▒██▀▀█▄  
 ░██▓ ▒██▒░ ████▓▒░▒▒█████▓   ▒██▒ ░ ░▒████▒░██▓ ▒██▒
 ░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░▒▓▒ ▒ ▒   ▒ ░░   ░░ ▒░ ░░ ▒▓ ░▒▓░
   ░▒ ░ ▒░  ░ ░ ▒ ▒░ ░░▒░ ░ ░     ░     ░ ░  ░  ░▒ ░ ▒░
   ░░   ░ ░ ░ ░ ░ ▒   ░░░ ░ ░   ░         ░     ░░   ░ 
    ░         ░ ░     ░                 ░  ░   ░     
        HOTSPOT MANAGER - ADGUARD DNS ENABLED
```

Un gestor de router avanzado basado en Flask que convierte tu PC en un servidor de hotspot inteligente con capacidades de control de tráfico, gestión de dispositivos Android vía ADB, caché acelerador web y enrutamiento multi-interfaz automático.

---

##  Tabla de Contenidos

- [Características Principales](#características-principales)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Uso](#uso)
- [Interfaz Dashboard](#interfaz-dashboard)
- [Funcionalidades Detalladas](#funcionalidades-detalladas)
- [API REST](#api-rest)
- [Multimedia y Streaming](#multimedia-y-streaming)
- [Solución de Problemas](#solución-de-problemas)
- [Arquitectura](#arquitectura)

---

##  Características Principales

###  Gestión de Hotspot
- **Punto de acceso WiFi** configurable con SSID y contraseña personalizables
- **DNS AdGuard** integrado (94.140.14.14 | 94.140.15.15) para bloqueo de anuncios
- **Seguridad de red** con iptables automático
- **Rango privado**: 192.168.1.0/24 con puerta de enlace 192.168.1.1

###  Soporte Multi-Uplink (Múltiples Interfaces WAN)
- **Detección automática** de interfaces USB/Ethernet conectadas
- **Smart Uplink Switcher**: selecciona la mejor conexión basada en:
  - Señal RSSI (fuerza de señal WiFi)
  - Latencia (ping a 8.8.8.8)
  - Round-robin cuando las conexiones están equilibradas
- **Auto-tethering Android**: activa automáticamente RNDIS en dispositivos conectados por USB
- **Failover automático** cuando falla la conexión principal

###  Control Android vía ADB
- **Gestión de dispositivos**: descubre y controla múltiples teléfonos
- **Información del dispositivo**: modelo, versión, SDK, batería, temperatura
- **USB Tethering automático**: enciende/apaga con un click
- **Control remoto**: despierta, bloquea el dispositivo desde la interfaz web
- **Monitor de batería**: seguimiento en tiempo real de nivel, temperatura y estado

###  Gestión de Clientes
- **Lista en tiempo real** de dispositivos conectados
- **IP y MAC address** de cada cliente
- **Estadísticas de ancho de banda**: velocidad actual y bytes totales
- **Bloqueo/desbloqueo** granular por MAC
- **Modo allowlist**: solo permite MACs autorizadas (whitelist)

###  Web Booster (Caché Proxy)
- **Proxy HTTP** en puerto 8888
- **Caché de contenido** con compresión automática
- **Optimización HTML**: elimina comentarios y espacios extra
- **TTL configurable** (3600s por defecto)
- **Estadísticas**: ratio de hits, bytes ahorrados

###  Herramientas de Red
- **Speed Test**: prueba de latencia a 8.8.8.8 (ping 4 paquetes)
- **Port Forwarding**: redirección de puertos con iptables
- **Logs en tiempo real**: visualiza eventos del sistema
- **Gestión de servicios**: SSH, FTP, bot de Telegram, app MDB

---

##  Requisitos Previos

### Software
```bash
# Sistema operativo
Linux (Debian/Ubuntu recomendado)

# Paquetes del sistema
sudo apt-get update
sudo apt-get install -y \
    network-manager \
    dnsmasq \
    iptables \
    python3-pip \
    python3-venv \
    adb \
    curl \
    net-tools \
    iw

# Verificar servicios
sudo systemctl status NetworkManager
sudo systemctl status dnsmasq
```

### Hardware
- **WiFi USB**: interfaz inalámbrica compatible con modo AP (recomendado: TP-Link, Realtek)
- **Uplinks**: puertos Ethernet o tethering USB desde teléfonos Android
- **RAM**: mínimo 256MB (512MB recomendado)
- **CPU**: cualquier procesador moderno

### Permisos
```bash
# El script necesita acceso sudo sin contraseña para ciertos comandos
# Agregar al sudoers (CUIDADO - solo para comandos específicos):
sudo visudo

# Agregar estas líneas:
ALL ALL=(ALL) NOPASSWD: /sbin/iptables
ALL ALL=(ALL) NOPASSWD: /sbin/ip
ALL ALL=(ALL) NOPASSWD: /sbin/dhclient
ALL ALL=(ALL) NOPASSWD: /usr/bin/nmcli
ALL ALL=(ALL) NOPASSWD: /bin/systemctl
```

---

##  Instalación

### 1. Clonar/Descargar el Repositorio
```bash
git clone <repo-url> /home/lozano/router
cd /home/lozano/router
```

### 2. Crear Entorno Virtual
```bash
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
# o en Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Verificar Dependencias de Sistema
```bash
# Verificar NetworkManager
nmcli --version

# Verificar ADB
adb version

# Verificar iptables
sudo iptables --version
```

### 5. Crear Conexión Hotspot en NetworkManager
```bash
# Crear conexión hotspot (si no existe)
sudo nmcli connection add type wifi \
    ifname wlo1 \
    con-name Hotspot \
    autoconnect no

# O editar manualmente
sudo nmcli connection edit Hotspot
```

### 6. Permitir que iptables persista entre reinicios (opcional)
```bash
sudo apt-get install iptables-persistent
sudo systemctl enable iptables-persistent
sudo iptables-save > /etc/iptables/rules.v4
```

---

##  Configuración

### Variables de Configuración (app.py)

```python
# Línea 17: Interfaz WiFi principal
IFACE_WIFI = "wlo1"  # Cambiar según tu sistema (iwconfig para listar)

# Línea 175: Archivo de logs
LOG_FILE = "/var/log/syslog"

# Línea 177-182: Scripts/servicios
SCRIPTS = {
    "MDB App": "/home/lozano/mdb/app.py",
    "FTP Server": "/home/lozano/mdb/ftp_server.py",
    "Telegram Bot": "/home/lozano/mdb/telegram_bot.py",
    "SSH Server": "SERVICE:ssh"
}

# Línea 328-330: Configuración Web Booster
BOOSTER_PORT = 8888
BOOSTER_TTL = 3600  # Tiempo de caché en segundos
BOOSTER_CACHE_DIR = "/tmp/booster_cache"

# Línea 240: DNS y DHCP
"ipv4.dns '94.140.14.14 94.140.15.15'"  # Cambiar para otro DNS
"ipv4.addresses 192.168.1.1/24"         # Cambiar rango si hay conflictos
```

### config.json (Se crea automáticamente)
```json
{
  "allowed_macs": ["aa:bb:cc:dd:ee:ff"],
  "allowlist_mode": false
}
```

### Detectar Interfaz WiFi
```bash
# Listar interfaces de red
ip link show
iwconfig

# Buscar la interfaz WiFi
iwconfig | grep -i wifi

# Actualizar en app.py con el nombre correcto (ej: wlan0, wlo1, etc)
```

---

##  Uso

### Iniciar la Aplicación

```bash
# Con la aplicación ejecutándose (require sudo para iptables)
sudo python3 app.py

# O con permisos adecuados:
python3 app.py

# La aplicación estará disponible en:
# http://localhost
# http://192.168.1.1 (desde otro dispositivo en la red)
```

---

##  Interfaz Dashboard

El dashboard web es una Single Page Application (SPA) moderna con actualizaciones en tiempo real y una topología visual interactiva.

###  Pestaña WiFi
- Configuración de SSID y Contraseña.
- Botones de encendido/apagado rápido.
- Estadísticas en vivo: Canal, Frecuencia y número de equipos conectados.

###  Pestaña Android
- Detección automática de dispositivos vía ADB.
- **Gráficos de Batería**: Visualiza nivel, temperatura y estado de carga.
- **Controles Remotos**: Botones para despertar pantalla, bloquear y activar/desactivar USB Tethering.
- **Información Técnica**: Modelo, versión de Android, SDK e IP.

###  Pestaña Equipos
- Lista detallada de clientes: Hostname, IP y MAC.
- **Velocímetro en vivo**: Muestra el ancho de banda consumido por cada dispositivo en tiempo real.
- Gestión de acceso (Bloqueo/Desbloqueo).

###  Pestaña Booster
- Switch de activación del acelerador web.
- Estadísticas de ahorro: número de archivos en caché, hit ratio y bytes ahorrados.
- Botón para limpiar caché instantáneamente.

###  Pestaña Herramientas (Herramientas)
- **Speed Test**: Mide la latencia actual a los servidores de Google (8.8.8.8).
- **Consola de Logs**: Visualiza los últimos eventos del sistema (`/var/log/syslog`) directamente en el navegador.

---

##  Funcionalidades Detalladas

###  Smart Uplink Switcher (Línea 79-173)

**Comportamiento:**
1. **Cada 10 segundos** revisa todas las interfaces de red disponibles
2. **Para cada interfaz**:
   - Verifica si tiene IP configurada
   - Si no tiene IP, solicita una mediante DHCP
   - Obtiene señal RSSI vía ADB (si es tethering Android)
   - Mide latencia con ping a 8.8.8.8
3. **Calcula puntuación**:
   ```
   score = (RSSI + 100) * 2 - (latency / 10)
   ```
   Favorece: alta señal, baja latencia
4. **Elige la mejor**:
   - Si diferencia > 8 puntos: usa la mejor
   - Si diferencia < 8 puntos: activa round-robin cada 60s
5. **Actualiza rutas**: cambia la puerta de enlace por defecto a la mejor interfaz

**Ejemplo:**
```
Phone 1 (RSSI -45, latencia 30ms): score = (55)*2 - 3 = 107
Phone 2 (RSSI -70, latencia 100ms): score = (30)*2 - 10 = 50
→ Selecciona Phone 1
```

###  Auto ADB Tethering (Línea 43-63)

**Cada 20 segundos:**
1. Ejecuta `adb devices` para encontrar teléfonos
2. Para cada dispositivo conectado:
   - Envía comando: `adb -s <serial> shell svc usb setFunctions rndis`
   - Activa automáticamente USB RNDIS (red compartida)
3. El sistema detecta automáticamente la nueva interfaz

**Ventaja:** No necesitas activar tethering manualmente

###  Seguridad de Red (Línea 237-275)

**Configuración de iptables:**
```bash
# Input: permite DNS y DHCP desde clientes WiFi
iptables -I INPUT -i wlo1 -p udp --dport 53 -j ACCEPT    # DNS
iptables -I INPUT -i wlo1 -p udp --dport 67:68 -j ACCEPT # DHCP

# Forward: aislamiento de redes privadas (clients no pueden acceder a LAN interna)
iptables -I FORWARD -i wlo1 -d 192.168.0.0/16 -j DROP    # Clase C privada
iptables -I FORWARD -i wlo1 -d 10.0.0.0/8 -j DROP        # Clase A privada
iptables -I FORWARD -i wlo1 -d 172.16.0.0/12 -j DROP     # Clase B privada

# Excepción: permite acceso a la puerta de enlace misma
iptables -I FORWARD -i wlo1 -d 192.168.1.1 -j ACCEPT

# NAT: masquerade para salida a internet
iptables -t nat -A POSTROUTING -o <uplink> -j MASQUERADE
```

**Resultado:** Los clientes pueden acceder a internet pero no a la red interna

###  Estadísticas de Ancho de Banda (Línea 284-322)

**Thread recolector (cada 2 segundos):**
1. Analiza `iptables -L FORWARD -v` para extraer bytes/packets por MAC
2. Calcula velocidad en MB/s:
   ```
   speed = (bytes_actuales - bytes_anteriores) / tiempo_transcurrido
   ```
3. Almacena en `BANDWIDTH_STATS` para mostrar en UI

**Dato importante:** Solo registra MACs en las reglas FORWARD de iptables

###  Web Booster Proxy (Línea 324-425)

**Flujo de solicitud HTTP:**

```
Cliente → :8888 → Router → booster_handle_http()
   ↓
Verifica si URL está en caché
   ↓
SI → Retorna con header "X-Cache: HIT" (rápido)
   ↓
NO → Descarga desde internet
   ↓
Optimiza (quita comentarios HTML)
   ↓
Almacena en caché con TTL
   ↓
Retorna con header "X-Cache: MISS"
```

**Cache Storage:**
```
/tmp/booster_cache/
├── sha1(url1).cache
├── sha1(url2).cache
└── ...
```

Archivo de caché:
```
{Línea 1: JSON con metadata}
{Resto: contenido binario}
```

---

##  API REST

### Status y Configuración

#### GET /status
Retorna estado completo del sistema
```json
{
  "active": true,
  "ssid": "PC_Host_Server",
  "password": "server1234",
  "wan_ok": true,
  "channel": "6",
  "frequency": "2437 MHz",
  "clients": [
    {
      "ip": "192.168.1.100",
      "mac": "aa:bb:cc:dd:ee:ff",
      "hostname": "mobile",
      "speed": 1250000,
      "total_bytes": 524288000
    }
  ],
  "blocked": ["aa:bb:cc:dd:ee:00"],
  "allowed": ["aa:bb:cc:dd:ee:ff"],
  "allowlist": false,
  "services": {
    "MDB App": true,
    "FTP Server": false,
    "Telegram Bot": true,
    "SSH Server": true
  },
  "uplinks": [
    {
      "name": "Phone (P2S0)",
      "active": true,
      "primary": true
    }
  ]
}
```

### Gestión de WiFi

#### POST /start
Inicia hotspot
```json
{
  "ssid": "Mi Red",
  "password": "contraseña123"
}
```

#### POST /stop
Detiene hotspot (sin parámetros)

### Control de Clientes

#### POST /block
Bloquea un cliente por MAC
```json
{
  "mac": "aa:bb:cc:dd:ee:ff"
}
```

#### POST /unblock
Desbloquea un cliente por MAC

#### POST /allow
Añade MAC a lista blanca
```json
{
  "mac": "aa:bb:cc:dd:ee:ff"
}
```

#### POST /disallow
Remove MAC de lista blanca

#### POST /allowlist-toggle
Activa/desactiva modo allowlist (solo clientes permitidos)
```json
{
  "enabled": true
}
```

### Port Forwarding

#### POST /port-forward
Redirecciona un puerto
```json
{
  "ext": "8080",
  "ip": "192.168.1.100",
  "int": "80"
}
```
Redirecciona: `router:8080` → `192.168.1.100:80`

#### GET /port-forward-list
Lista todas las redirecciones activas

#### POST /port-forward-delete
Elimina una redirección
```json
{
  "ext": "8080"
}
```

### Servicios

#### POST /service/toggle
Inicia/detiene un servicio
```json
{
  "name": "SSH Server"
}
```
Válidos: "MDB App", "FTP Server", "Telegram Bot", "SSH Server"

### Android ADB

#### GET /android/devices
Lista dispositivos Android conectados
```json
[
  {
    "id": "emulator-5554",
    "status": "conectado"
  },
  {
    "id": "RFCT11D5W99",
    "status": "offline"
  }
]
```

#### GET /android/info?serial=RFCT11D5W99
Información del dispositivo
```json
{
  "model": "Xiaomi Redmi Note 9",
  "version": "11",
  "sdk": "30",
  "battery": "85",
  "temperature": "38.5°C",
  "ip": "192.168.1.105"
}
```

#### GET /android/battery?serial=RFCT11D5W99
Estado de batería
```json
{
  "level": 85,
  "temperature": "38.5°C",
  "status": "Charging"
}
```

#### POST /android/usb-tether?serial=RFCT11D5W99
Activa/desactiva USB tethering
```json
{
  "action": "on"
}
```

#### POST /android/wake?serial=RFCT11D5W99
Despierta el dispositivo

#### POST /android/lock?serial=RFCT11D5W99
Bloquea el dispositivo

### Speed Test y Diagnóstico

#### POST /speed-test
Prueba de latencia
```json
{
  "reachable": 4,
  "latency_ms": "25.5"
}
```

#### GET /logs?lines=50
Obtiene logs del sistema
```json
{
  "logs": ["log line 1", "log line 2", ...]
}
```

### Web Booster

#### GET /booster/status
Estado del caché
```json
{
  "enabled": true,
  "transparent": false,
  "cache_items": 42,
  "hits": 1523,
  "hit_ratio": 87.5,
  "bytes_saved": 524288000
}
```

#### POST /booster/toggle
Activa/desactiva booster
```json
{
  "enabled": true
}
```

#### POST /booster/clear
Limpia la caché

---

##  Multimedia y Streaming

Router Pro Manager permite servir contenido multimedia directamente desde el almacenamiento local a los clientes conectados.

###  Almacenamiento
- Carpeta predeterminada: `./videos/`
- Formatos soportados: `.mp4` (H.264 recomendado)

###  Endpoints Multimedia

#### GET /videos
Lista todos los videos disponibles en el servidor.
- **Respuesta**: Array de objetos con `name`, `size` y `url`.

#### GET /video/<filename>
Sirve el archivo de video solicitado. Soporta streaming mediante HTTP Range requests (nativo de Flask/Werkzeug).

**Uso desde un cliente:**
```html
<video controls>
  <source src="http://192.168.1.1/video/mi_pelicula.mp4" type="video/mp4">
</video>
```

---

##  Solución de Problemas

### 1. "Permission denied" al ejecutar

**Problema:** `iptables: Permission denied`

**Solución:**
```bash
# Opción 1: Ejecutar con sudo
sudo python3 app.py

# Opción 2: Configurar sudoers sin contraseña
sudo visudo
# Añadir línea: ALL ALL=(ALL) NOPASSWD: /sbin/iptables
```

### 2. Interfaz WiFi no encontrada

**Problema:** El hotspot no se crea

**Solución:**
```bash
# Encontrar la interfaz correcta
iwconfig
ip link show

# Actualizar IFACE_WIFI en app.py (línea 17)
IFACE_WIFI = "tu_interfaz_aqui"

# Crear conexión NetworkManager si no existe
sudo nmcli connection add type wifi ifname <tu_interfaz> con-name Hotspot autoconnect no
```

### 3. Clientes sin acceso a internet

**Problema:** Connected pero sin navegación

**Solución:**
```bash
# Verificar MASQUERADE en iptables
sudo iptables -t nat -L POSTROUTING -v

# Si no hay MASQUERADE:
sudo iptables -t nat -A POSTROUTING -o <uplink_interface> -j MASQUERADE

# Verificar que Forward ACCEPT:
sudo iptables -P FORWARD ACCEPT
sudo iptables -L FORWARD -v
```

### 4. ADB: "No devices found"

**Problema:** Los teléfonos no aparecen

**Solución:**
```bash
# Reiniciar servidor ADB
adb kill-server
adb start-server

# Verificar conectividad
adb devices

# Autorizar dispositivo (confirmación en pantalla del teléfono)
# En algunos teléfonos: Ajustes > Desarrollo > Depuración USB

# Si sigue sin funcionar, reinstalar drivers
# Windows: https://developer.android.com/studio/run/win-usb
# Linux: sudo apt-get install adb libmtp-dev
```

### 5. Booster no funciona

**Problema:** Cache hits = 0

**Solución:**
```bash
# Verificar que proxy está escuchando
sudo netstat -tuln | grep 8888
sudo lsof -i :8888

# Verificar permisos en /tmp
ls -la /tmp/booster_cache/

# Configurar navegador para usar proxy
# Firefox: Ajustes > Red > Proxy manual
# IP: 192.168.1.1, Puerto: 8888

# Limpiar y reiniciar
curl http://192.168.1.1/booster/clear
```

### 6. Logs vacíos

**Problema:** No se muestran logs

**Solución:**
```bash
# Verificar path en app.py
tail /var/log/syslog

# O cambiar a otro archivo si syslog no existe
# Actualizar LINE 175 en app.py:
LOG_FILE = "/var/log/kern.log"  # o /var/log/dmesg

# Verificar permisos
ls -la /var/log/syslog
sudo chmod 644 /var/log/syslog
```

---

##  Arquitectura

### Estructura del Código

```
app.py
├── Threads (Daemon)
│   ├── auto_adb_tethering()        → Auto-detección USB tethering
│   ├── smart_uplink_switcher()     → Selección inteligente de uplink
│   ├── collect_bandwidth()         → Estadísticas de ancho de banda
│   └── booster_proxy_server()      → Proxy HTTP caché
│
├── Módulos de Comando
│   ├── run_cmd()                   → Ejecuta comandos shell
│   ├── adb_cmd()                   → Ejecuta comandos ADB
│   └── get_uplink_interfaces()     → Detecta uplinks disponibles
│
├── Rutas Flask (API REST)
│   ├── GET /status                 → Estado general
│   ├── POST /start, /stop          → Control hotspot
│   ├── POST /block, /unblock       → Control de acceso
│   ├── POST /service/toggle        → Gestión de servicios
│   ├── GET /android/devices        → Listado de dispositivos
│   ├── POST /android/*             → Control Android
│   ├── POST /port-forward*         → Port forwarding
│   ├── POST /speed-test            → Speed test
│   ├── GET /logs                   → Logs del sistema
│   ├── GET /videos                 → Listado multimedia
│   ├── GET /booster/*              → Caché booster
│   └── /video/<filename>           → Streaming
│
└── Frontend (HTML/CSS/JS)
    ├── index.html                  → Interfaz única
    ├── Topología SVG               → Diagrama de red
    ├── Pestañas                    → WiFi, Android, Equipos, Booster, Herramientas
    └── WebSocket/Polling           → Actualización en tiempo real
```

### Flujo de Ejecución Principales

#### 1. Arranque (app.py:746-748)
```python
if __name__ == '__main__':
    setup_hotspot()              # Configura hotspot inicial
    app.run(...)                 # Inicia servidor Flask
```

#### 2. Setup Hotspot (app.py:227-274)
```
1. Obtiene SSID/contraseña
2. Configura NetworkManager
3. Configura DNS a AdGuard
4. Limpia y configura iptables
5. Activa MASQUERADE para uplinks
```

#### 3. Cambio de Uplink (app.py:79-173)
```
Cada 10 segundos:
1. Obtiene lista de interfaces
2. Valida IP en cada una
3. Calcula score (RSSI + latencia)
4. Selecciona mejor o activa round-robin
5. Actualiza ruta por defecto
```

#### 4. Ancho de Banda (app.py:300-319)
```
Cada 2 segundos:
1. Lee iptables FORWARD -v
2. Extrae bytes/packets por MAC
3. Calcula velocidad instantánea
4. Almacena en BANDWIDTH_STATS
```

### Dependencias Externas

| Comando | Propósito | Alternativa |
|---------|-----------|------------|
| `nmcli` | NetworkManager CLI | ip commands (menos flexible) |
| `iptables` | Firewall y NAT | nftables (más moderno) |
| `adb` | Control Android | socket directo (imposible) |
| `ip` | Config de red | ifconfig (deprecated) |
| `ping` | Test de conectividad | curl -I (menos preciso) |
| `nslookup` | Resolver DNS | dig (requiere más setup) |
| `iw` | WiFi info | iwconfig (deprecated) |
| `systemctl` | Gestión de servicios | service (deprecated) |

---

##  Optimizaciones y Mejoras Futuras

### Mejoras Implementadas
 Auto-detection de uplinks
 Smart switching basado en RSSI + latencia
 ADB auto-tethering
 Web caché proxy
 Control granular de clientes
 Topología SVG en tiempo real

### Mejoras Sugeridas
- [ ] WebSocket para actualización en vivo (vs polling)
- [ ] Persistencia de estadísticas en base de datos
- [ ] Dashboard de monitoreo 24/7
- [ ] Alertas via telegram/email
- [ ] Control de QoS (Calidad de Servicio)
- [ ] Configuración de firewall avanzada
- [ ] Modo transparent proxy (no requiere config en cliente)
- [ ] Soporte para IPv6
- [ ] Respaldo automático de configuración

---

##  Licencia

MIT License - Siéntete libre de usar, modificar y distribuir

---

##  Autor

**Lozano** - Desarrollador

---

##  Soporte

Para reportar bugs o sugerir features:
1. Crear un issue en GitHub
2. Incluir: `uname -a`, `nmcli --version`, `python --version`
3. Adjuntar logs: `tail -50 /var/log/syslog`

---

##  Seguridad

 **IMPORTANTE:**
- Este script ejecuta comandos con `sudo`. Asegurate de entender cada uno antes de usar
- NO expongas este servicio a internet públicamente sin VPN/firewall
- Los clientes conectados pueden:
  - Acceder a internet mediante tu conexión
  - Conectarse entre ellos (si no hay aislamiento VLAN)
  - Impactar tu ancho de banda

---

##  Ejemplos de Uso

### Caso 1: Compartir Internet con Múltiples Teléfonos
```
1. Conecta 2+ teléfonos por USB
2. El app detecta automáticamente tethering
3. El Smart Switcher elige la mejor conexión
4. Clientes se conectan al WiFi
5. Internet se comparte automáticamente
```

### Caso 2: Control de Ancho de Banda
```
1. Ver velocidad en tiempo real de cada cliente
2. Bloquear cliente abusivo
3. Permitir solo clientes autorizados en modo allowlist
4. Redirigir puerto 80 a servidor local
```

### Caso 3: Análisis de Red
```
1. Ejecutar speed test
2. Ver logs del sistema
3. Activar caché proxy para optimizar
4. Monitorear dispositivos Android
```

---

##  Referencias

- [NetworkManager CLI](https://networkmanager.dev/)
- [iptables manual](https://linux.die.net/man/8/iptables)
- [Android ADB](https://developer.android.com/studio/command-line/adb)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [AdGuard DNS](https://adguard.com/en/adguard-dns/overview.html)

---

**Última actualización:** Junio 2026
**Versión:** 1.0.0
**Estado:** Producción 
