# 🎓 Guía Completa de Uso - Router Pro Manager

## 📖 Índice
1. [Primeros Pasos](#primeros-pasos)
2. [Configuración Inicial](#configuración-inicial)
3. [Ejemplos Prácticos](#ejemplos-prácticos)
4. [Troubleshooting Avanzado](#troubleshooting-avanzado)
5. [Optimizaciones](#optimizaciones)
6. [Preguntas Frecuentes](#preguntas-frecuentes)

---

## 🚀 Primeros Pasos

### ¿Qué necesito para empezar?

**Mínimo requerido:**
- Computadora con Linux
- Interfaz WiFi (USB o integrada)
- Python 3.6+
- Acceso sudo

**Óptimo:**
- 2+ interfases de red (WiFi + Ethernet o 2 USB)
- 1+ teléfono Android con USB
- Conexión a internet estable

### Verificación Rápida de Sistema

```bash
# 1. ¿Linux?
uname -s  # Debe decir Linux

# 2. ¿Python 3?
python3 --version  # 3.6+ OK

# 3. ¿NetworkManager?
systemctl status NetworkManager

# 4. ¿sudo sin contraseña configurado?
sudo -l | grep NOPASSWD

# 5. ¿WiFi disponible?
iwconfig

# 6. ¿ADB (si usarás Android)?
adb --version
```

---

## ⚙️ Configuración Inicial

### Paso 1: Identificar tu Interfaz WiFi

```bash
# Método 1: iwconfig (directa)
iwconfig
# Output esperado:
# wlo1      IEEE 802.11bgn  ESSID:off
# wlan0     IEEE 802.11bgn  ESSID:off

# Método 2: ip link
ip link show | grep -E "^[0-9]+: (wl|en|eth|usb)"

# Método 3: ls /sys/class/net
ls /sys/class/net/ | grep -E "^(wl|eth|en|usb)"
```

**Guardar el nombre:** será `wlo1`, `wlan0`, `eth0`, etc.

### Paso 2: Actualizar Configuración

```bash
# Editar app.py
nano app.py

# Buscar línea 17:
IFACE_WIFI = "wlo1"  # ← Cambiar a tu interfaz

# Guardar: Ctrl+O, Enter, Ctrl+X
```

### Paso 3: Configurar Sudoers (SIN CONTRASEÑA)

```bash
# CUIDADO: Solo autoriza comandos específicos
sudo visudo

# Añadir al final del archivo:
# ========================
# Permitir iptables sin contraseña
ALL ALL=(ALL) NOPASSWD: /sbin/iptables
ALL ALL=(ALL) NOPASSWD: /sbin/ip
ALL ALL=(ALL) NOPASSWD: /usr/bin/nmcli
ALL ALL=(ALL) NOPASSWD: /sbin/dhclient
ALL ALL=(ALL) NOPASSWD: /bin/systemctl

# Guardar: Ctrl+O, Enter, Ctrl+X
```

**Verificar:**
```bash
sudo iptables -L > /dev/null && echo "OK"
```

### Paso 4: Crear Conexión WiFi en NetworkManager

```bash
# Ver conexiones existentes
nmcli connection show

# Si no existe "Hotspot", crearla:
sudo nmcli connection add \
    type wifi \
    ifname wlo1 \
    con-name Hotspot \
    wifi-sec.key-mgmt wpa-psk \
    autoconnect no

# Verificar
nmcli connection show Hotspot
```

### Paso 5: Instalar Dependencias

```bash
cd /home/lozano/router
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Verificar Flask
python3 -c "import flask; print(flask.__version__)"
```

### Paso 6: Primer Arranque

```bash
# SIN sudo (si sudoers está bien configurado):
python3 app.py

# CON sudo (alternativa):
sudo python3 app.py

# Debería salir el BANNER y escuchar en http://0.0.0.0:80
# En navegador: http://localhost o http://192.168.1.1
```

---

## 💡 Ejemplos Prácticos

### Ejemplo 1: Setup Básico - WiFi Compartido

**Objetivo:** Compartir internet con 3 dispositivos

**Pasos:**

```bash
# 1. Iniciar app
python3 app.py

# 2. Abrir navegador en http://localhost
# 3. Ir a pestaña "WiFi"
# 4. Cambiar SSID: "Mi Red Compartida"
# 5. Cambiar Contraseña: "contraseña123"
# 6. Haz clic en "Aplicar Cambios"

# 7. Verificar en otro dispositivo
nmcli device wifi list | grep "Mi Red Compartida"

# 8. Conectar desde el dispositivo
# Wifi → Mi Red Compartida → contraseña123
```

**Verificación:**
- En pestaña "WiFi" debe aparecer "1 Equipos"
- En pestaña "Equipos" verás el dispositivo con su IP
- En "Topología" se conectan automáticamente las líneas

---

### Ejemplo 2: Multi-Uplink - Tethering desde 2 Teléfonos

**Objetivo:** Usar dos teléfonos Android para redundancia

**Setup Hardware:**
- Teléfono 1 (USB Port 1) → Tethering RNDIS
- Teléfono 2 (USB Port 2) → Tethering RNDIS
- Computadora WiFi comparte ambas conexiones

**Pasos:**

```bash
# 1. Conectar teléfono 1
# → El app detecta automáticamente (auto_adb_tethering)
# → Activa RNDIS
# → Crea interfaz usb0 o enx...

# 2. Conectar teléfono 2
# → Repite proceso anterior
# → Crea otra interfaz

# 3. Verificar interfaces
ip link show | grep -E "usb0|enx"

# 4. En pestaña Android:
# - Verás ambos teléfonos listados
# - Estado: "conectado"

# 5. Topología muestra:
# 📱 Phone 1 (USB) → 🖥️ Router → 👥 Clientes
# 📱 Phone 2 (USB) → ↗️      ↖️ → Internet
```

**Smart Switching en acción:**

```
Cada 10 segundos:
- Phone 1: RSSI -55, Latency 40ms → Score: 99
- Phone 2: RSSI -70, Latency 100ms → Score: 30
→ Usa Phone 1 como principal

Si Phone 1 cae:
- Score = null
- Automáticamente cambia a Phone 2
- Los clientes WiFi NO notan el cambio
```

---

### Ejemplo 3: Control de Acceso - Whitelist

**Objetivo:** Solo permitir 2 dispositivos específicos

**Pasos:**

```bash
# 1. Obtener MACs de dispositivos permitidos
# En pestaña "Equipos":
# - Conectar Dispositivo A
# - Copiar su MAC (ej: aa:bb:cc:dd:ee:01)
# - Conectar Dispositivo B
# - Copiar su MAC (ej: aa:bb:cc:dd:ee:02)

# 2. Permitir vía API o UI
curl -X POST http://localhost/allow \
  -H "Content-Type: application/json" \
  -d '{"mac": "aa:bb:cc:dd:ee:01"}'

curl -X POST http://localhost/allow \
  -H "Content-Type: application/json" \
  -d '{"mac": "aa:bb:cc:dd:ee:02"}'

# 3. Activar modo allowlist
curl -X POST http://localhost/allowlist-toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'

# 4. Verificar config.json
cat config.json
# Output:
# {
#   "allowed_macs": [
#     "aa:bb:cc:dd:ee:01",
#     "aa:bb:cc:dd:ee:02"
#   ],
#   "allowlist_mode": true
# }

# 5. Intentar conectar con otro dispositivo
# → Podría conectarse a WiFi pero NO habrá internet
```

**Implementación Técnica:**
```python
# TODO: El código actual NO implementa el bloqueo en tiempo real
# Se necesita agregar en /status:
if ALLOWLIST_MODE and mac not in ALLOWED_MACS:
    # Bloquear con iptables
    run_cmd(f"sudo iptables -I FORWARD -m mac --mac-source {mac} -j DROP")
```

---

### Ejemplo 4: Port Forwarding - Servidor Local

**Objetivo:** Exponer servidor local en puerto personalizado

**Setup:** 
- Servidor web local en puerto 8000
- Clientes acceden a router:9000
- Se redirecciona a localhost:8000

**Pasos:**

```bash
# 1. Iniciar servidor local
python3 -m http.server 8000
# Escucha en http://localhost:8000

# 2. Configurar forwarding
curl -X POST http://localhost/port-forward \
  -H "Content-Type: application/json" \
  -d '{
    "ext": "9000",
    "ip": "192.168.1.1",
    "int": "8000"
  }'

# 3. Verificar
curl -X GET http://localhost/port-forward-list
# Output:
# [{"ext": "9000", "ip": "192.168.1.1", "int": "8000"}]

# 4. Desde cliente WiFi (ej 192.168.1.100):
curl http://192.168.1.1:9000
# → Accede al servidor local

# 5. Para eliminar:
curl -X POST http://localhost/port-forward-delete \
  -H "Content-Type: application/json" \
  -d '{"ext": "9000"}'
```

**iptables Behind:**
```bash
# Entrada (WAN → LAN)
iptables -t nat -A PREROUTING -p tcp --dport 9000 \
  -j DNAT --to-destination 192.168.1.1:8000

# Salida permitida
iptables -A FORWARD -p tcp -d 192.168.1.1 --dport 8000 \
  -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT
```

---

### Ejemplo 5: Web Booster - Caché de Contenido

**Objetivo:** Acelerar navegación con caché proxy

**Setup:**
```bash
# 1. Activar Booster en pestaña "Booster"
# - Haz clic en "Activar"
# - Verifica que sea azul (enabled)

# 2. Configurar navegador del cliente para usar proxy:
# Firefox:
#   Preferencias → Red → Proxy Manual
#   HTTP: 192.168.1.1
#   Puerto: 8888
#
# Chrome: 
#   Ajustes → Configuración avanzada → Sistema → Proxy
#   Manual:
#   HTTP: 192.168.1.1:8888

# 3. Navegar normalmente
# Primera visita a google.com:
#   - Descarga desde internet
#   - Caché: MISS
#   - Bytes saved: 0
#
# Segunda visita (dentro de 3600s):
#   - Sirve desde caché local
#   - Caché: HIT
#   - Bytes saved: +50KB

# 4. Ver estadísticas
curl -X GET http://localhost/booster/status
# Output:
# {
#   "enabled": true,
#   "cache_items": 12,
#   "hits": 45,
#   "hit_ratio": 82.5,
#   "bytes_saved": 5242880
# }

# 5. Limpiar caché
curl -X POST http://localhost/booster/clear
```

**Optimización de HTML:**
```
Antes: <div><!-- comentario --><p>  Texto  </p></div>
Después: <div><p> Texto </p></div>
Ahorro: ~15% para HTML típico
```

---

## 🔧 Troubleshooting Avanzado

### Problema: Clientes Conectados pero Sin Internet

**Síntomas:**
- WiFi conecta correctamente
- Asigna IP (ej: 192.168.1.100)
- Ping a gateway (192.168.1.1) OK
- Pero no puede acceder a internet (no resuelve DNS, no ping a 8.8.8.8)

**Investigación:**

```bash
# 1. Verificar que hay uplink activo
ip route show default
# Debe haber una línea "default via X.X.X.X dev <interface>"

# 2. Verificar MASQUERADE
sudo iptables -t nat -L POSTROUTING -v
# Buscar línea con "MASQUERADE"
# Si no está, es el problema

# 3. Verificar Forward policy
sudo iptables -P FORWARD
# Debe ser "ACCEPT" (no "DROP")

# 4. Probar conexión interna
sudo iptables -L FORWARD -v
# Ver bytes en forward rules (si > 0, hay tráfico pasando)

# 5. Tracear conexión
tcpdump -i wlo1 -n "port 80"
# En cliente: curl http://8.8.8.8:80
# Ver si hay tráfico capturado
```

**Solución Paso a Paso:**

```bash
# Opción A: MASQUERADE falta
sudo iptables -t nat -A POSTROUTING -o <uplink_iface> -j MASQUERADE
# Donde <uplink_iface> es (ej: usb0, eth0, enp0s31f6)

# Opción B: Forward DROP
sudo iptables -P FORWARD ACCEPT

# Opción C: Forward rules muy restrictivas
sudo iptables -F FORWARD  # ⚠️ Cuidado: borra todo
sudo iptables -P FORWARD ACCEPT
sudo iptables -I FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
sudo iptables -I FORWARD -m state --state NEW -j DROP

# Opción D: Sin uplink conectado
ip route show default  # ¿Hay default route?
ping -c 1 8.8.8.8      # ¿Responde?

# Persistir cambios
sudo iptables-save > /etc/iptables/rules.v4
sudo systemctl restart iptables-persistent
```

---

### Problema: ADB - Dispositivos No Aparecen

**Síntomas:**
- `adb devices` retorna lista vacía
- En pestaña Android no hay dispositivos
- Comando manual funciona pero app no lo detecta

**Investigación:**

```bash
# 1. Verificar ADB server
adb start-server
adb devices -l
# Listar todos

# 2. Verificar teléfono conectado
lsusb | grep -i phone  # o android, samsung, etc
# Debe mostrar algo como:
# Bus 001 Device 003: ID 2717:ff80 Xiaomi Inc.

# 3. Habilitar Depuración USB en teléfono
# Ajustes → Desarrollador → Depuración USB (ON)
# Si no hay "Desarrollador":
#   Ir a Ajustes → Acerca del Teléfono
#   Tocar "Número de Compilación" 7 veces
#   Volver a Ajustes → Desarrollador

# 4. Autorizar conexión
# En teléfono debería aparecer:
# "¿Permitir depuración USB?"
# Marcar "Siempre confiar en este dispositivo"
# Tocar OK

# 5. Verificar de nuevo
adb devices
# Debe mostrar: <SERIAL> device (no "unauthorized")
```

**Solución:**

```bash
# Si aún no funciona:
adb kill-server
sleep 2
adb start-server

# Desconectar USB
# Esperar 5 segundos
# Reconectar USB
# En teléfono confirmar depuración

adb devices
# ¿OK?

# Si sigue fallando:
# Reinstalar drivers (Linux)
sudo apt-get install --reinstall adb usbutils libmtp-dev
sudo usermod -a -G plugdev $USER
newgrp plugdev
```

---

### Problema: Smart Uplink Switcher No Cambia de Interfaz

**Síntomas:**
- Multiple uplinks conectados
- Pero siempre usa el mismo (incluso si cae)
- No ve alternativas

**Investigación:**

```bash
# 1. Verificar interfaces disponibles
ip link show
# Buscar estado "UP" en interfaces

# 2. Verificar IP asignada
ip addr show
# Cada interfaz debe tener "inet X.X.X.X"

# 3. Ver logs del app
# En terminal donde corre: ver mensajes "[*] Switcher"

# 4. Verificar DHCP funciona
sudo dhclient <interface> -v --timeout 5
# Debe asignar IP

# 5. Verificar ping (latencia)
ping -I <interface> -c 1 8.8.8.8 -W 1
# Debe retornar o "timeout"

# 6. Verificar RSSI (solo para tethering Android)
adb shell "dumpsys wifi | grep 'lastRssi:'"
# Debe retornar un número negativo (ej -45)
```

**Solución:**

```bash
# Asegurar DHCP en interfaz
sudo dhclient <interface> -v --timeout 10

# Verificar ruta por defecto
ip route show default
# Debe cambiar después de 10 segundos

# Ver logs más detallados
# Editar app.py línea 164:
print(f"[*] Switching... available={available}, scores={scores}")

# Reiniciar app
sudo python3 app.py
```

---

### Problema: Booster Cache No Guarda

**Síntomas:**
- Booster activado
- Cache items = 0
- Siempre MISS

**Investigación:**

```bash
# 1. Verificar permisos directorio
ls -la /tmp/booster_cache/
# Debe tener permisos "drwxr-xr-x" 

# 2. Probar escritura
touch /tmp/booster_cache/test.txt
# ¿OK?

# 3. Verificar proxy está escuchando
sudo netstat -tuln | grep 8888
# Debe mostrar "LISTEN 0.0.0.0:8888"

# 4. Probar descarga manual
curl -v http://8.8.8.8 2>&1 | head
# Ver en output:
# X-Cache: HIT o MISS
# X-Proxy: RouterBooster

# 5. Ver caché en disco
ls -la /tmp/booster_cache/ | wc -l
# Cuántos archivos hay?
```

**Solución:**

```bash
# Verificar socket activo
ps aux | grep booster_proxy_server
# ¿Aparece?

# Reiniciar
sudo python3 app.py

# Probar desde cliente
# 1. En Firefox: Preferencias → Proxy Manual
#    HTTP Proxy: 192.168.1.1
#    Puerto: 8888
# 2. Acceder a http://example.com
# 3. En app: GET /booster/status
# 4. Ver hits > 0?

# Limpiar cache anterior
curl -X POST http://localhost/booster/clear

# Configurar timeout más largo
# Editar app.py línea 330:
BOOSTER_TTL = 7200  # 2 horas
```

---

## 🎯 Optimizaciones

### Optimización 1: Reducir Latencia de Switching

**Problema actual:** 10 segundos entre checks

**Solución - Editar app.py:**

```python
# Línea 171: cambiar sleep de 10 a 5 segundos
time.sleep(5)  # Más rápido pero consume más CPU

# Línea 61: cambiar sleep de 20 a 10
time.sleep(10)  # ADB checks más frecuente
```

**Trade-off:** CPU ↑10%, Latencia ↓5s

---

### Optimización 2: Caché Compresión Gzip

**Agregar compresión al Booster:**

```python
# Editar app.py línea 346 (función booster_optimize):
import gzip

def booster_optimize(data, ct):
    if "text/html" in ct:
        data = re.sub(b"<!--.*?-->", b"", data, flags=re.DOTALL)
        data = re.sub(b"\\s+", b" ", data)
        # Agregar gzip
        data = gzip.compress(data, compresslevel=6)
    return data
```

**Beneficio:** 70% menos bytes en caché

---

### Optimización 3: Persistencia de Estadísticas

**Guardar stats a disco:**

```python
import json

def save_bandwidth_stats():
    """Guardar estadísticas cada hora"""
    while True:
        time.sleep(3600)
        with open("bandwidth_stats.json", "w") as f:
            json.dump(BANDWIDTH_STATS, f, indent=2, default=str)

threading.Thread(target=save_bandwidth_stats, daemon=True).start()
```

---

### Optimización 4: Límite de Clientes por MAC

**Evitar consumo por cliente:**

```python
# Agregar al inicio
MAX_CLIENTS = 10

# En /status, limitar:
clients = clients[:MAX_CLIENTS]
```

---

## ❓ Preguntas Frecuentes

### Q: ¿Puedo usar esto sin WiFi, solo Ethernet?

**A:** Sí, pero necesitas:
1. 2 puertos Ethernet (1 WAN, 1 para red interna)
2. Cambiar en app.py:
   ```python
   IFACE_WIFI = "eth1"  # Tu segundo puerto
   ```
3. O usar virtual bridge (más complejo)

---

### Q: ¿Funciona con IPv6?

**A:** No, actualmente solo IPv4.

Para agregar IPv6:
```python
# app.py línea 98
ip -6 addr show {iface}  # Verificar IPv6
# Agregar rutas IPv6 similares
ip -6 route add default via {ipv6_gw} dev {iface}
```

---

### Q: ¿Cuántos clientes soporta?

**A:** Teóricamente ilimitado, pero:
- 50 clientes: sin problemas
- 100+ clientes: considera limitar con iptables
- Ancho de banda total: depende de uplink

---

### Q: ¿Puedo acceder desde internet?

**A:** ⚠️ NO recomendado sin protección:
```bash
# Para exponer (SOLO CON VPN):
# Opción 1: Usar ngrok
ngrok http 80

# Opción 2: Usar Wireguard
# https://www.wireguard.com/

# NUNCA exponer puertos directamente a internet
```

---

### Q: ¿Cómo monitorear en tiempo real?

**A:** Usar WebSocket en lugar de polling:

```python
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    while True:
        emit('status_update', get_status_data())
        time.sleep(1)
```

---

### Q: ¿Puedo usar DNS personalizado?

**A:** Sí, editar app.py línea 240:

```python
"ipv4.dns '1.1.1.1 1.0.0.1'"  # Cloudflare
# o
"ipv4.dns '8.8.8.8 8.8.4.4'"  # Google
# o
"ipv4.dns '208.67.222.222 208.67.220.220'"  # OpenDNS
```

---

### Q: ¿Se reinicia solo en caso de crash?

**A:** No, pero puedes agregar:

```bash
# Crear script systemd
sudo tee /etc/systemd/system/router-pro.service > /dev/null <<EOF
[Unit]
Description=Router Pro Manager
After=network.target

[Service]
Type=simple
User=lozano
WorkingDirectory=/home/lozano/router
ExecStart=/home/lozano/router/venv/bin/python3 app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable router-pro
sudo systemctl start router-pro
```

---

### Q: ¿Cómo debuggear errores?

**A:** Activar modo debug:

```python
# app.py línea 748:
app.run(
    host='0.0.0.0',
    port=80,
    debug=True,  # ← Ya está
    threaded=True,
    use_reloader=False  # ← Agregar esto
)
```

También revisar stderr:
```bash
python3 app.py 2>&1 | tee router.log
```

---

**Última actualización:** Junio 2026
**Versión:** 1.0.0 - Guía Completa
