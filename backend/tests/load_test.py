import time
import requests
import threading
import random

# URL de la API (ajustar si es necesario)
API_URL = "http://localhost:5000/api/events/ingest"

def simulate_ingest(thread_id):
    """Simula el envío de alertas concurrentes."""
    for i in range(50):
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": "alert",
            "src_ip": f"192.168.1.{random.randint(1, 254)}",
            "dest_ip": "10.0.0.15",
            "proto": "TCP",
            "alert": {
                "action": "allowed",
                "category": "Potentially Bad Traffic",
                "signature": f"Load Test Signature {random.randint(1, 5)}",
                "severity": random.randint(1, 3)
            }
        }
        try:
            r = requests.post(API_URL, json=data, timeout=5)
            # Solo imprimimos cada 10 para no saturar la consola
            if (i + 1) % 10 == 0:
                print(f"[Thread {thread_id}] Sent {i+1} alerts. Last status: {r.status_code}")
        except Exception as e:
            print(f"[Thread {thread_id}] Error: {e}")
        time.sleep(random.uniform(0.05, 0.2))

if __name__ == "__main__":
    threads = []
    num_threads = 10
    alerts_per_thread = 50
    
    print(f"🚀 Iniciando test de carga: {num_threads} hilos x {alerts_per_thread} alertas...")
    start_time = time.time()
    
    for i in range(num_threads):
        t = threading.Thread(target=simulate_ingest, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    
    end_time = time.time()
    total_alerts = num_threads * alerts_per_thread
    print("-" * 50)
    print(f"✅ Test finalizado!")
    print(f"📊 Total alertas enviadas: {total_alerts}")
    print(f"⏱️ Tiempo total: {end_time - start_time:.2f} segundos")
    print(f"⚡ Rendimiento: {total_alerts / (end_time - start_time):.2f} alertas/seg")
    print("-" * 50)
