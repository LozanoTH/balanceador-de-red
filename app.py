import subprocess
from flask import Flask, render_template, jsonify, request, send_from_directory, Response
import os
import signal
import glob
import json
import time
import re
import threading
import socket
import hashlib
import queue
import requests as http_requests

app = Flask(__name__)

IFACE_WIFI = "wlo1"
BLOCKED_MACS = set()
ALLOWED_MACS = set()

def get_uplink_interfaces():
    # Dynamically find connected USB/Ethernet interfaces
    # Also try to connect disconnected ones that look like USB
    stdout, _ = run_cmd("nmcli -t -f DEVICE,TYPE,STATE device")
    uplinks = []
    for line in stdout.split('\n'):
        if not line: continue
        parts = line.split(':')
        if len(parts) < 3: continue
        dev, dev_type, state = parts[0], parts[1], parts[2]
        
        if dev == "enp2s0": continue # Ignore internal
        
        if dev_type == 'ethernet':
            if state == 'connected':
                uplinks.append(dev)
            elif state == 'disconnected' and (dev.startswith('enx') or dev.startswith('usb')):
                print(f"[*] Intentando conectar interfaz USB: {dev}")
                run_cmd(f"nmcli device connect {dev}")
                # Re-check after a short delay or just wait for next cycle
    return uplinks

def auto_adb_tethering():
    """Thread to automatically enable USB tethering on any connected Android device."""
    while True:
        try:
            stdout, _ = run_cmd("adb devices")
            lines = [l for l in stdout.split('\n') if l and 'List' not in l]
            for l in lines:
                parts = l.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    serial = parts[0]
                    # Check if RNDIS is already enabled (heuristic: check if an interface exists for it)
                    # For simplicity, we just send the command every 30s or if we don't see a corresponding interface
                    uplinks = get_uplink_interfaces()
                    # If no uplink matches this device (difficult to map serial to iface perfectly without more work)
                    # just try to enable it. It doesn't hurt if already on.
                    adb_cmd("svc usb setFunctions rndis", serial)
        except Exception as e:
            print(f"[!] ADB Auto-Tether Error: {e}")
        time.sleep(20)

threading.Thread(target=auto_adb_tethering, daemon=True).start()

ALLOWLIST_MODE = False
RUNNING_SERVICES = {}
BANDWIDTH_STATS = {}
PRIMARY_UPLINK = None
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def update_iptables_masquerade(iface):
    """Ensures MASQUERADE is set for the given interface and cleaned for others."""
    # We could be surgical, but flushing and re-adding for uplinks is safer in this script's context
    # Or just add it if it doesn't exist
    check, _ = run_cmd(f"sudo iptables -t nat -C POSTROUTING -o {iface} -j MASQUERADE 2>/dev/null")
    if check != "": # Error means not found
        run_cmd(f"sudo iptables -t nat -A POSTROUTING -o {iface} -j MASQUERADE")

def smart_uplink_switcher():
    global PRIMARY_UPLINK
    last_switch_time = 0
    round_robin_idx = 0
    
    while True:
        try:
            uplinks = get_uplink_interfaces()
            if not uplinks:
                PRIMARY_UPLINK = None
                time.sleep(5)
                continue

            scores = {}
            available = []
            
            for iface in uplinks:
                # Check if interface has an IP
                ip_check, _ = run_cmd(f"ip -4 addr show {iface} | grep 'inet '")
                if not ip_check: 
                    # Try to get DHCP if it's connected but no IP
                    run_cmd(f"sudo dhclient {iface} -v --timeout 5 2>/dev/null")
                    ip_check, _ = run_cmd(f"ip -4 addr show {iface} | grep 'inet '")
                    if not ip_check: continue
                
                # Identify phone serial for RSSI
                serial = None
                # Try to find serial in sysfs
                serial_glob = glob.glob(f"/sys/class/net/{iface}/device/../serial")
                if serial_glob:
                    with open(serial_glob[0]) as f:
                        serial = f.read().strip()
                
                # Get RSSI (Signal strength) via adb
                rssi = -70 # Default decent signal
                if serial:
                    rssi_out, _ = adb_cmd("dumpsys wifi | grep 'lastRssi:' | awk '{print $2}'", serial)
                    if rssi_out and rssi_out.strip().replace("-","").isdigit():
                        rssi = int(rssi_out)
                
                # Check latency
                lat_out, _ = run_cmd(f"ping -I {iface} -c 1 -W 1 8.8.8.8 | grep 'time=' | awk -F'time=' '{{print $2}}' | cut -d' ' -f1")
                latency = float(lat_out) if lat_out and lat_out.replace(".","").isdigit() else 999
                
                # Score calculation
                score = (rssi + 100) * 2 - (latency / 10)
                scores[iface] = score
                available.append(iface)
                
                # Ensure MASQUERADE for all available uplinks
                update_iptables_masquerade(iface)
            
            if not available:
                time.sleep(5)
                continue

            # Sort by score to get the best consistently
            available.sort(key=lambda x: scores.get(x, 0), reverse=True)
            best_iface = available[0]
            
            # If scores are close (difference < 8), enable Round Robin
            is_balanced = len(available) > 1 and abs(scores[available[0]] - scores[available[1]]) < 8
            
            now = time.time()
            target = best_iface
            
            if is_balanced:
                if now - last_switch_time > 60:
                    round_robin_idx = (round_robin_idx + 1) % len(available)
                    target = available[round_robin_idx]
                    last_switch_time = now
                else:
                    target = PRIMARY_UPLINK if PRIMARY_UPLINK in available else available[0]
            else:
                target = best_iface

            if target != PRIMARY_UPLINK:
                # Find gateway
                gw, _ = run_cmd(f"ip route show dev {target} | grep 'default via' | awk '{{print $3}}'")
                if not gw:
                    gw, _ = run_cmd(f"ip route show dev {target} | grep -v 'default' | awk '/scope link/ {{print $1}}' | cut -d/ -f1 | head -1")
                    # In many tethering cases, the GW is .1 of the network
                    if gw and gw.endswith('.0'): gw = gw[:-1] + '1'

                if gw:
                    print(f"[*] Switching default route to {target} via {gw} (Score: {scores.get(target, 0):.1f})")
                    run_cmd(f"sudo ip route del default 2>/dev/null")
                    run_cmd(f"sudo ip route add default via {gw} dev {target} metric 50")
                    PRIMARY_UPLINK = target
                    
        except Exception as e:
            print(f"[!] Switcher Error: {e}")
        time.sleep(10)

threading.Thread(target=smart_uplink_switcher, daemon=True).start()

LOG_FILE = "/var/log/syslog"

SCRIPTS = {
    "MDB App": "/home/lozano/mdb/app.py",
    "FTP Server": "/home/lozano/mdb/ftp_server.py",
    "Telegram Bot": "/home/lozano/mdb/telegram_bot.py",
    "SSH Server": "SERVICE:ssh"
}
PYTHON_BIN = "/home/lozano/mdb/.venv/bin/python3"
VIDEO_DIR = os.path.join(os.path.dirname(__file__), "videos")

def load_config():
    global ALLOWED_MACS, ALLOWLIST_MODE
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
                ALLOWED_MACS = set(cfg.get("allowed_macs", []))
                ALLOWLIST_MODE = cfg.get("allowlist_mode", False)
        except: pass

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "allowed_macs": list(ALLOWED_MACS),
            "allowlist_mode": ALLOWLIST_MODE
        }, f, indent=2)

load_config()

def run_cmd(cmd, timeout=15):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1
    except Exception as e:
        return str(e), 1

BANNER = r"""
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
"""

def setup_hotspot(ssid=None, password=None):
    print(BANNER)
    if not ssid:
        ssid_out, _ = run_cmd("nmcli -t -f 802-11-wireless.ssid connection show Hotspot | cut -d: -f2")
        ssid = ssid_out if ssid_out else "PC_Host_Server"
    if not password:
        pass_out, _ = run_cmd("sudo nmcli -s -g 802-11-wireless-security.psk connection show Hotspot")
        password = pass_out if pass_out else "server1234"
    print(f"[*] Iniciando Hotspot: SSID={ssid}")
    
    # Basic configuration
    cmds = [
        f"sudo nmcli connection modify Hotspot wifi-sec.key-mgmt wpa-psk 802-11-wireless.ssid '{ssid}' 802-11-wireless-security.psk '{password}'",
        f"sudo nmcli connection modify Hotspot ipv4.addresses 192.168.1.1/24 ipv4.method shared ipv4.dns '94.140.14.14 94.140.15.15' ipv4.ignore-auto-dns yes",
        f"sudo nmcli connection up Hotspot",
    ]
    
    # Security: Manage client access
    # We allow DNS (53) and DHCP (67) for the clients to work.
    # We removed the DROP rules for 80, 22, and 8888 so you can access the panel via 192.168.1.1
    security_cmds = [
        f"sudo iptables -F INPUT", # Clear to avoid duplicates
        f"sudo iptables -I INPUT -i {IFACE_WIFI} -p udp --dport 53 -j ACCEPT",
        f"sudo iptables -I INPUT -i {IFACE_WIFI} -p udp --dport 67:68 -j ACCEPT",
        
        # Isolation from the external internal network (192.168.0.1, etc.)
        # Still blocking access to other private IP ranges
        f"sudo iptables -I FORWARD -i {IFACE_WIFI} -d 192.168.0.0/16 -j DROP",
        f"sudo iptables -I FORWARD -i {IFACE_WIFI} -d 10.0.0.0/8 -j DROP",
        f"sudo iptables -I FORWARD -i {IFACE_WIFI} -d 172.16.0.0/12 -j DROP",
        
        # Re-allow 1.1 specifically so the rule above doesn't block its own network if it overlaps
        f"sudo iptables -I FORWARD -i {IFACE_WIFI} -d 192.168.1.1 -j ACCEPT",
        
        f"sudo iptables -P FORWARD ACCEPT",
    ]
    cmds.extend(security_cmds)
    
    uplinks = get_uplink_interfaces()
    for iface in uplinks:
        cmds.append(f"sudo iptables -t nat -A POSTROUTING -o {iface} -j MASQUERADE")
    
    for c in cmds:
        stdout, code = run_cmd(c)
        if code != 0:
            print(f"[!] Error: {stdout}")
        else:
            print(f"[+] OK: {c[:50]}...")

def get_client_hostname(ip):
    host, _ = run_cmd(f"nmcli -t -f IP4.DNS1 device show {IFACE_WIFI} 2>/dev/null | head -1")
    name, _ = run_cmd(f"nslookup {ip} 2>/dev/null | grep 'name =' | awk '{{print $NF}}' | tr -d '.'")
    if name:
        return name
    host_out, _ = run_cmd(f"ip neigh show | grep {ip} | grep -o 'REACHABLE\\|STALE\\|DELAY\\|PROBE'")
    return ""

def get_traffic_stats():
    stats = {}
    out, _ = run_cmd("sudo iptables -L FORWARD -v -n -x 2>/dev/null | tail -n +3")
    for line in out.split('\n'):
        if 'MAC' in line:
            parts = line.split()
            mac = parts[-1] if ':' in parts[-1] else ''
            if mac:
                pkts = parts[0]
                bytes_s = parts[1]
                if mac not in stats:
                    stats[mac] = {"pkts": 0, "bytes": 0}
                stats[mac]["pkts"] += int(pkts)
                stats[mac]["bytes"] += int(bytes_s)
    return stats

def collect_bandwidth():
    while True:
        try:
            stats = get_traffic_stats()
            now = time.time()
            for mac, s in stats.items():
                if mac in BANDWIDTH_STATS:
                    elapsed = now - BANDWIDTH_STATS[mac]["time"]
                    if elapsed > 0:
                        BANDWIDTH_STATS[mac]["speed"] = (s["bytes"] - BANDWIDTH_STATS[mac]["bytes"]) / elapsed
                else:
                    BANDWIDTH_STATS[mac] = {"speed": 0, "bytes": 0, "pkts": 0, "time": now}
                BANDWIDTH_STATS[mac]["bytes"] = s["bytes"]
                BANDWIDTH_STATS[mac]["pkts"] = s["pkts"]
                BANDWIDTH_STATS[mac]["time"] = now
            for mac in list(BANDWIDTH_STATS.keys()):
                if mac not in stats:
                    BANDWIDTH_STATS[mac]["speed"] = 0
        except: pass
        time.sleep(2)

bw_thread = threading.Thread(target=collect_bandwidth, daemon=True)
bw_thread.start()

# ─── WEB BOOSTER (Caching Proxy) ───────────────────────────────────────

BOOSTER_CACHE_DIR = "/tmp/booster_cache"
BOOSTER_ENABLED = False
BOOSTER_PORT = 8888
BOOSTER_TRANSPARENT = False
BOOSTER_TTL = 3600
os.makedirs(BOOSTER_CACHE_DIR, exist_ok=True)

BOOSTER_STATS = {"hits": 0, "misses": 0, "bytes_saved": 0}

def booster_get_cache_path(url):
    h = hashlib.sha1(url.encode()).hexdigest()
    return os.path.join(BOOSTER_CACHE_DIR, h)

def booster_fetch_url(url):
    try:
        resp = http_requests.get(url, timeout=10, stream=True)
        return resp.content, resp.headers.get("Content-Type", "application/octet-stream"), resp.status_code
    except:
        return b"", "text/plain", 502

def booster_optimize(data, ct):
    if "text/html" in ct:
        # Simple optimization: remove comments and extra whitespace
        data = re.sub(b"<!--.*?-->", b"", data, flags=re.DOTALL)
        data = re.sub(b"\\s+", b" ", data)
    return data

def booster_set_cached(url, data, ct, status):
    path = booster_get_cache_path(url)
    with open(path, "wb") as f:
        f.write(json.dumps({"ct": ct, "status": status, "time": time.time()}).encode() + b"\n" + data)

def booster_get_cached(url):
    path = booster_get_cache_path(url)
    if not os.path.exists(path): return None
    try:
        with open(path, "rb") as f:
            meta_line = f.readline()
            meta = json.loads(meta_line)
            if time.time() - meta["time"] > BOOSTER_TTL:
                return None
            return f.read(), meta["ct"], meta["status"]
    except: return None

def booster_handle_http(conn):
    try:
        req = conn.recv(8192).decode(errors="ignore")
        if not req: return
        lines = req.split("\r\n")
        if not lines: return
        parts = lines[0].split()
        if len(parts) < 2: return
        method, target = parts[0], parts[1]
        
        if method == "GET" and target.startswith("http"):
            cached = booster_get_cached(target)
            if cached:
                data, ct, status = cached
                BOOSTER_STATS["hits"] += 1
                BOOSTER_STATS["bytes_saved"] += len(data)
                resp = f"HTTP/1.1 {status} OK\r\nContent-Type: {ct}\r\nContent-Length: {len(data)}\r\nX-Cache: HIT\r\nX-Proxy: RouterBooster\r\n\r\n".encode()
                conn.sendall(resp + data)
                return
            
            BOOSTER_STATS["misses"] += 1
            data, ct, status = booster_fetch_url(target)
            if BOOSTER_ENABLED and status == 200:
                opt = booster_optimize(data, ct)
                booster_set_cached(target, opt, ct, status)
                data = opt
            status_text = {200: "OK", 302: "Found", 404: "Not Found", 502: "Bad Gateway"}.get(status, "OK")
            resp = f"HTTP/1.1 {status} {status_text}\r\nContent-Type: {ct}\r\nContent-Length: {len(data)}\r\nX-Cache: MISS\r\nX-Proxy: RouterBooster\r\n\r\n".encode()
            conn.sendall(resp + data)
        else:
            conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
    except: pass
    finally:
        try: conn.close()
        except: pass

def booster_proxy_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", BOOSTER_PORT))
    server.listen(200)
    server.settimeout(1.0)
    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=booster_handle_http, args=(conn,), daemon=True).start()
        except socket.timeout: continue
        except: break

booster_thread = threading.Thread(target=booster_proxy_server, daemon=True)
booster_thread.start()

def booster_setup_iptables(enable=True):
    # This needs logic for all uplinks, but booster usually targets client traffic
    pass

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/status')
def status():
    stdout, _ = run_cmd(f"nmcli connection show --active | grep -E 'Hotspot|wifi'")
    active_hotspot = "Hotspot" in stdout or "wifi" in stdout
    ssid_out, _ = run_cmd("nmcli -t -f 802-11-wireless.ssid connection show Hotspot | cut -d: -f2")
    pass_out, _ = run_cmd("sudo nmcli -s -g 802-11-wireless-security.psk connection show Hotspot")
    real_ssid = ssid_out if ssid_out else "PC_Host_Server"
    real_pass = pass_out if pass_out else "server1234"

    # WAN status
    wan_out, _ = run_cmd("ping -c 1 -W 2 8.8.8.8 2>/dev/null | grep '1 received'")
    wan_ok = "received" in wan_out

    # Channel info
    channel_out, _ = run_cmd(f"iw dev {IFACE_WIFI} info 2>/dev/null | grep channel | awk '{{print $2}}'")
    freq_out, _ = run_cmd(f"iw dev {IFACE_WIFI} info 2>/dev/null | grep channel | awk '{{print $4}}'")

    # Clientes
    clients_out, _ = run_cmd(f"ip neigh show dev {IFACE_WIFI}")
    clients = []
    for line in clients_out.split('\n'):
        if "lladdr" in line:
            parts = line.split()
            try:
                ip = parts[0]
                mac_idx = parts.index("lladdr") + 1
                mac = parts[mac_idx]
                if mac and ip != "192.168.1.1":
                    hostname = get_client_hostname(ip)
                    bw = BANDWIDTH_STATS.get(mac, {"speed": 0, "bytes": 0})
                    clients.append({
                        "ip": ip, "mac": mac,
                        "hostname": hostname,
                        "speed": round(bw["speed"]),
                        "total_bytes": bw["bytes"]
                    })
            except: continue

    # Servicios
    services_status = {}
    for name, path in SCRIPTS.items():
        if path.startswith("SERVICE:"):
            service_name = path.split(":")[1]
            sout, _ = run_cmd(f"systemctl is-active {service_name}")
            services_status[name] = (sout == "active")
        else:
            proc = RUNNING_SERVICES.get(name)
            services_status[name] = proc is not None and proc.poll() is None

    # Uplinks status (Phones)
    uplinks = []
    default_iface, _ = run_cmd("ip route show default | head -1 | awk '{print $5}'")
    uplink_ifaces = get_uplink_interfaces()
    
    for iface in uplink_ifaces:
        up_check, _ = run_cmd(f"ip addr show {iface} 2>/dev/null | grep 'inet '")
        is_active = bool(up_check)
        is_primary = (iface == default_iface)
        uplinks.append({
            "name": f"Phone ({iface[-4:].upper()})", 
            "active": is_active,
            "primary": is_primary
        })

    return jsonify({
        "active": active_hotspot,
        "ssid": real_ssid,
        "password": real_pass,
        "wan_ok": wan_ok,
        "channel": channel_out or "?",
        "frequency": freq_out or "?",
        "clients": clients,
        "blocked": list(BLOCKED_MACS),
        "allowed": list(ALLOWED_MACS),
        "allowlist": ALLOWLIST_MODE,
        "services": services_status,
        "uplinks": uplinks
    })

@app.route('/service/toggle', methods=['POST'])
def toggle_service():
    name = request.json.get('name')
    if name not in SCRIPTS: return jsonify({"error": "Unknown service"}), 400
    path = SCRIPTS[name]
    if path.startswith("SERVICE:"):
        service_name = path.split(":")[1]
        sout, _ = run_cmd(f"systemctl is-active {service_name}")
        action = "stop" if sout == "active" else "start"
        run_cmd(f"sudo systemctl {action} {service_name}")
        return jsonify({"message": f"{name} {action}ed"})
    
    proc = RUNNING_SERVICES.get(name)
    if proc and proc.poll() is None:
        proc.terminate()
        RUNNING_SERVICES[name] = None
        return jsonify({"message": f"{name} stopped"})
    else:
        new_proc = subprocess.Popen([PYTHON_BIN, path])
        RUNNING_SERVICES[name] = new_proc
        return jsonify({"message": f"{name} started"})

@app.route('/block', methods=['POST'])
def block_mac():
    mac = request.json.get('mac')
    BLOCKED_MACS.add(mac)
    run_cmd(f"sudo iptables -I FORWARD -m mac --mac-source {mac} -j DROP")
    return jsonify({"message": f"MAC {mac} bloqueada"})

@app.route('/unblock', methods=['POST'])
def unblock_mac():
    mac = request.json.get('mac')
    if mac in BLOCKED_MACS: BLOCKED_MACS.remove(mac)
    run_cmd(f"sudo iptables -D FORWARD -m mac --mac-source {mac} -j DROP")
    return jsonify({"message": f"MAC {mac} desbloqueada"})

@app.route('/allow', methods=['POST'])
def allow_mac():
    mac = request.json.get('mac')
    ALLOWED_MACS.add(mac)
    save_config()
    return jsonify({"message": f"MAC {mac} permitida"})

@app.route('/disallow', methods=['POST'])
def disallow_mac():
    mac = request.json.get('mac')
    if mac in ALLOWED_MACS: ALLOWED_MACS.remove(mac)
    save_config()
    return jsonify({"message": f"MAC {mac} eliminada de permitidos"})

@app.route('/allowlist-toggle', methods=['POST'])
def toggle_allowlist():
    global ALLOWLIST_MODE
    ALLOWLIST_MODE = request.json.get('enabled')
    save_config()
    return jsonify({"message": f"Modo allowlist {'activado' if ALLOWLIST_MODE else 'desactivado'}"})

@app.route('/port-forward', methods=['POST'])
def port_forward():
    data = request.json
    run_cmd(f"sudo iptables -t nat -A PREROUTING -p tcp --dport {data['ext']} -j DNAT --to-destination {data['ip']}:{data['int']}")
    run_cmd(f"sudo iptables -A FORWARD -p tcp -d {data['ip']} --dport {data['int']} -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT")
    return jsonify({"message": "Puerto abierto"})

@app.route('/port-forward-list')
def list_port_forwards():
    stdout, _ = run_cmd("sudo iptables -t nat -L PREROUTING -n --line-numbers 2>/dev/null")
    rules = []
    for line in stdout.split('\n'):
        if "DNAT" in line:
            parts = line.split()
            ext_port = ""
            dest_ip = ""
            dest_port = ""
            for i, p in enumerate(parts):
                if p.startswith("dpt:"): ext_port = p.split(":")[1]
                if p.startswith("to:"):
                    dst = p.split(":")[1]
                    if ":" in dst: dest_ip, dest_port = dst.rsplit(":", 1)
                    else: dest_ip = dst
            rules.append({"ext": ext_port, "ip": dest_ip, "int": dest_port})
    return jsonify(rules)

@app.route('/port-forward-delete', methods=['POST'])
def delete_port_forward():
    ext = request.json.get('ext')
    run_cmd(f"sudo iptables -t nat -D PREROUTING -p tcp --dport {ext} -j DNAT 2>/dev/null")
    return jsonify({"message": f"Regla {ext} eliminada"})

@app.route('/speed-test', methods=['POST'])
def speed_test():
    out, _ = run_cmd("ping -c 4 8.8.8.8")
    reachable = out.count("64 bytes from")
    latency = "0"
    if "avg" in out:
        latency = out.split("/")[-3]
    return jsonify({"reachable": reachable, "latency_ms": latency})

@app.route('/logs')
def get_logs():
    lines = request.args.get('lines', 50)
    out, _ = run_cmd(f"tail -n {lines} {LOG_FILE}")
    return jsonify({"logs": out.split('\n')})

@app.route('/videos')
def list_videos():
    if not os.path.isdir(VIDEO_DIR): return jsonify([])
    files = sorted(glob.glob(os.path.join(VIDEO_DIR, "*.[mM][pP]4")))
    result = []
    for f in files:
        name = os.path.basename(f)
        size = os.path.getsize(f)
        result.append({"name": name, "size": size, "url": f"/video/{name}"})
    return jsonify(result)

@app.route('/video/<path:filename>')
def serve_video(filename):
    return send_from_directory(VIDEO_DIR, filename)

# ─── Control Android vía ADB ──────────────────────────────────────────

ADB_AUTHORIZED = False

def adb_cmd(cmd, serial=None):
    prefix = f"adb -s {serial} " if serial else "adb "
    full_cmd = f"{prefix}shell \"{cmd}\""
    out, code = run_cmd(full_cmd, timeout=10)
    print(f"[ADB] {full_cmd} -> Code: {code}")
    if out: print(f"[ADB] Output: {out[:100]}")
    if "unauthorized" in out.lower() or "no devices" in out.lower():
        global ADB_AUTHORIZED
        ADB_AUTHORIZED = False
    return out, code

@app.route('/android/devices')
def android_devices():
    run_cmd("adb start-server 2>/dev/null")
    stdout, _ = run_cmd("adb devices")
    lines = [l for l in stdout.split('\n') if l and 'List' not in l]
    devices = []
    for l in lines:
        parts = l.split()
        if len(parts) >= 2:
            status = "conectado" if parts[1] == 'device' else parts[1]
            devices.append({"id": parts[0], "status": status})
    global ADB_AUTHORIZED
    ADB_AUTHORIZED = any(d["status"] == "conectado" for d in devices)
    return jsonify(devices)

@app.route('/android/info')
def android_info():
    serial = request.args.get('serial')
    model, _ = adb_cmd("getprop ro.product.model", serial)
    version, _ = adb_cmd("getprop ro.build.version.release", serial)
    sdk, _ = adb_cmd("getprop ro.build.version.sdk", serial)
    batt, _ = adb_cmd("dumpsys battery | grep 'level:' | awk '{print $2}'", serial)
    temp, _ = adb_cmd("dumpsys battery | grep 'temperature:' | awk '{print $2}'", serial)
    ip, _ = adb_cmd("ip -4 addr show wlan0 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1", serial)
    return jsonify({
        "model": model or "Unknown",
        "version": version or "?",
        "sdk": sdk or "?",
        "battery": batt or "?",
        "temperature": temp or "?",
        "ip": ip or "No IP"
    })

@app.route('/android/battery')
def android_battery():
    serial = request.args.get('serial')
    level, _ = adb_cmd("dumpsys battery | grep 'level:' | awk '{print $2}'", serial)
    temp, _ = adb_cmd("dumpsys battery | grep 'temperature:' | awk '{print $2}'", serial)
    st_code, _ = adb_cmd("dumpsys battery | grep 'status:' | awk '{print $2}'", serial)
    status_map = {"1": "Unknown", "2": "Charging", "3": "Discharging", "4": "Not charging", "5": "Full"}
    status = status_map.get(st_code, "Unknown")
    temp_c = int(temp) / 10 if temp and temp.isdigit() else 0
    return jsonify({
        "level": int(level) if level and level.isdigit() else 0,
        "temperature": f"{temp_c:.1f}°C",
        "status": status
    })

@app.route('/android/usb-tether', methods=['POST'])
def android_usb_tether():
    serial = request.args.get('serial')
    action = request.json.get('action', 'on')
    cmd = "svc usb setFunctions rndis" if action == 'on' else "svc usb setFunctions"
    adb_cmd(cmd, serial)
    return jsonify({"message": f"USB Tethering {action}", "success": True})

@app.route('/android/wake', methods=['POST'])
def android_wake():
    serial = request.args.get('serial')
    adb_cmd("input keyevent 224", serial)
    time.sleep(0.3)
    adb_cmd("input keyevent 82", serial)
    return jsonify({"message": "Woke up and unlocked"})

@app.route('/android/lock', methods=['POST'])
def android_lock():
    serial = request.args.get('serial')
    adb_cmd("input keyevent 223", serial)
    return jsonify({"message": "Locked"})

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    setup_hotspot(data.get('ssid'), data.get('password'))
    return jsonify({"message": "Started"})

@app.route('/stop', methods=['POST'])
def stop():
    run_cmd("sudo nmcli connection down Hotspot")
    return jsonify({"message": "Stopped"})

@app.route('/booster/status')
def booster_status():
    return jsonify({
        "enabled": BOOSTER_ENABLED,
        "transparent": BOOSTER_TRANSPARENT,
        "cache_items": len(os.listdir(BOOSTER_CACHE_DIR)),
        "hits": BOOSTER_STATS["hits"],
        "hit_ratio": round(BOOSTER_STATS["hits"] / (BOOSTER_STATS["hits"] + BOOSTER_STATS["misses"] + 1) * 100, 1),
        "bytes_saved": BOOSTER_STATS["bytes_saved"]
    })

@app.route('/booster/toggle', methods=['POST'])
def booster_toggle():
    global BOOSTER_ENABLED
    BOOSTER_ENABLED = request.json.get('enabled')
    return jsonify({"message": f"Booster {'enabled' if BOOSTER_ENABLED else 'disabled'}"})

@app.route('/booster/clear', methods=['POST'])
def booster_clear():
    for f in glob.glob(os.path.join(BOOSTER_CACHE_DIR, "*")): os.remove(f)
    return jsonify({"message": "Cache cleared"})

if __name__ == '__main__':
    setup_hotspot()
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
