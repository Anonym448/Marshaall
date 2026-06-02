#!/bin/bash
COUNT=$(grep -c '"event_type":"alert"' /var/log/suricata/eve.json 2>/dev/null || echo 0)
echo "Total alerts: $COUNT"
echo ""
echo "Last 20 alerts:"
grep '"event_type":"alert"' /var/log/suricata/eve.json | tail -20 | python3 -c '
import sys, json
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        a = e.get("alert", {})
        ts = e.get("timestamp", "?")[:19]
        sid = a.get("signature_id", "?")
        sig = a.get("signature", "?")
        src = e.get("src_ip", "?")
        dst = e.get("dest_ip", "?")
        proto = e.get("proto", "?")
        print(f"  {ts} SID:{sid} | {sig} | {src} -> {dst} ({proto})")
    except:
        pass
'
echo ""
echo "Last 5 eve.json entries (any type):"
tail -5 /var/log/suricata/eve.json | python3 -c '
import sys, json
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        et = e.get("event_type","?")
        ts = e.get("timestamp","?")[:19]
        src = e.get("src_ip","-")
        dst = e.get("dest_ip","-")
        dp = e.get("dest_port","-")
        http_ua = ""
        if "http" in e:
            http_ua = e["http"].get("http_user_agent","")[:40]
        print(f"  {ts} type={et} {src}:{e.get('src_port','-')} -> {dst}:{dp} ua={http_ua}")
    except:
        pass
'
echo ""
echo "fast.log last 10:"
tail -10 /var/log/suricata/fast.log 2>/dev/null
