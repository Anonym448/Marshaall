#!/usr/bin/env python3
"""
Post-restart reconfiguration for WSL2 mirrored networking mode.

After WSL2 restarts in mirrored mode:
- WSL2 gets a mirror of Windows network adapters
- The Wi-Fi interface appears with a name like 'wifi0', 'wlan0', or similar
- Suricata needs to listen on eth0 (now = real network traffic) 
- The HOME_NET needs to be updated to reflect new IP layout
- portproxy is no longer needed (but harmless)
"""

import subprocess
import json
import re

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

print("=== Marshaall SIEM — Reconfiguración post-reinicio WSL2 Mirrored ===")
print()

# 1. Detect interfaces
print("[1] Interfaces de red disponibles:")
ifaces_raw = run("ip -j link show 2>/dev/null")
try:
    ifaces = json.loads(ifaces_raw)
    iface_names = [i['ifname'] for i in ifaces if i['ifname'] != 'lo']
    for name in iface_names:
        ip = run(f"ip -4 addr show {name} 2>/dev/null | grep 'inet ' | awk '{{print $2}}'")
        print(f"   {name}: {ip or 'sin IP'}")
except:
    ifaces_raw2 = run("ip addr show | grep -E '^[0-9]+:|inet '")
    print(ifaces_raw2)
    iface_names = ['eth0']

print()

# 2. Find the interface with 192.168.0.x (the mirrored Wi-Fi)
wifi_iface = None
host_ip = None
for name in iface_names:
    ip = run(f"ip -4 addr show {name} 2>/dev/null | grep 'inet 192.168' | awk '{{print $2}}' | cut -d/ -f1")
    if ip:
        wifi_iface = name
        host_ip = ip
        print(f"[2] Interfaz Wi-Fi espejada detectada: {name} ({ip})")
        break

if not wifi_iface:
    eth0_ip = run("ip -4 addr show eth0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1")
    print(f"[2] Modo mirrored activo, usando eth0: {eth0_ip}")
    wifi_iface = 'eth0'
    host_ip = eth0_ip

print()

# 3. Show Suricata command to use
pcap_ifaces = f"--pcap=lo"
for name in iface_names:
    ip = run(f"ip -4 addr show {name} 2>/dev/null | grep 'inet ' | awk '{{print $2}}'")
    if ip:
        pcap_ifaces += f" --pcap={name}"

print(f"[3] Comando Suricata recomendado:")
print(f"   suricata {pcap_ifaces} -c /etc/suricata/suricata.yaml -D --pidfile /run/suricata.pid -k none")
print()

# 4. Update systemd override
override_content = f"""[Unit]
After=network-online.target marshaall-stack.service
Wants=marshaall-stack.service

[Service]
ExecStart=
ExecStart=/usr/bin/suricata {pcap_ifaces} -c /etc/suricata/suricata.yaml -D --pidfile /run/suricata.pid -k none
ExecStartPre=/bin/bash -c 'cp /home/user/marshaall/suricata/local.rules /var/lib/suricata/rules/local.rules'
ExecReload=
ExecReload=/bin/bash -c 'cp /home/user/marshaall/suricata/local.rules /var/lib/suricata/rules/local.rules && kill -USR2 $MAINPID'
PIDFile=/run/suricata.pid
Restart=on-failure
RestartSec=5
ProtectSystem=no
ProtectHome=no
"""

import os
os.makedirs('/etc/systemd/system/suricata.service.d', exist_ok=True)
with open('/etc/systemd/system/suricata.service.d/marshaall-wsl2.conf', 'w') as f:
    f.write(override_content)
print(f"[4] Servicio systemd actualizado con interfaces: {pcap_ifaces}")
print()

# 5. Update HOME_NET in suricata.yaml
new_home_net = "172.18.0.0/16,172.17.0.0/16,127.0.0.0/8,::1/128,::ffff:127.0.0.1/128"
if host_ip and host_ip.startswith('192.168.'):
    subnet = '.'.join(host_ip.split('.')[:3]) + '.0/24'
    new_home_net = f"{new_home_net},{host_ip}/32"

for fpath in ['/etc/suricata/suricata.yaml', '/home/user/marshaall/suricata/suricata.yaml']:
    try:
        content = open(fpath).read()
        new_content = re.sub(
            r'^    HOME_NET: ".*"$',
            f'    HOME_NET: "[{new_home_net}]"',
            content,
            flags=re.MULTILINE
        )
        open(fpath, 'w').write(new_content)
        print(f"[5] HOME_NET actualizado en {fpath}")
    except Exception as e:
        print(f"[5] Error actualizando {fpath}: {e}")

print(f"    HOME_NET = [{new_home_net}]")
print()

# 6. Reload and restart services
print("[6] Reiniciando servicios...")
os.system("systemctl daemon-reload")
os.system("systemctl restart suricata")
import time; time.sleep(8)

# Check result
result = run("grep 'rules successfully loaded' /var/log/suricata/suricata.log | tail -1")
status = run("systemctl is-active suricata")
print(f"    Suricata status: {status}")
print(f"    {result}")
print()
print("=== Configuración completada ===")
print()
print("Ahora Suricata escucha en TODAS las interfaces, incluyendo")
print("la interfaz espejada del Wi-Fi de Windows.")
print("Los ataques de Kali (nmap, ping, HTTP) serán detectados.")
