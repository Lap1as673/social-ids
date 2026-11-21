import asyncio
import time
import httpx
from collections import defaultdict
from scapy.all import AsyncSniffer, IP, TCP, UDP

from features import Flow

# Куда отправлять признаки (в будущем detection-service)
DETECTION_URL = "http://detection-service:8001/predict"
TARGET_PORT = 8000

# Хранилище активных потоков
active_flows: dict[tuple, Flow] = {}

def process_packet(packet):
    """Callback-функция для каждого пакета."""
    if not packet.haslayer(IP):
        return
    
    ip_layer = packet[IP]
    
    # Интересует только TCP/UDP, идущий к target-site (порт 8000) или от него
    if packet.haslayer(TCP):
        proto = 6
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport
    elif packet.haslayer(UDP):
        proto = 17
        src_port = packet[UDP].sport
        dst_port = packet[UDP].dport
    else:
        return

    # Определяем направление (fwd = к target-site, bwd = от target-site)
    if dst_port == TARGET_PORT:
        direction = "fwd"
        key = (ip_layer.src, ip_layer.dst, src_port, dst_port, proto)
    elif src_port == TARGET_PORT:
        direction = "bwd"
        # Для bwd-пакетов ключ тот же, что и для fwd (клиент-сервер)
        key = (ip_layer.dst, ip_layer.src, dst_port, src_port, proto)
    else:
        return # Игнорируем трафик не к target-site

    # Создаём или обновляем поток
    if key not in active_flows:
        active_flows[key] = Flow(
            src_ip=key[0], dst_ip=key[1],
            src_port=key[2], dst_port=key[3],
            proto=key[4]
        )
    
    active_flows[key].add_packet(packet, direction)


async def flush_finished_flows():
    """Периодически проверяет завершённые потоки и отправляет их."""
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(2.0) # Проверяем раз в 2 секунды
            
            finished_keys = [
                k for k, flow in active_flows.items() 
                if flow.is_finished(timeout=5.0)
            ]
            
            for k in finished_keys:
                flow = active_flows.pop(k)
                features = flow.to_features()
                
                print(f"📦 Flow finished: {features['src_ip']}:{features['src_port']} -> "
                      f"duration={features['duration']}s, "
                      f"pkts={features['src_packets']+features['dst_packets']}")
                
                # Отправляем в детектор (в будущем)
                try:
                    # Пока закомментируем, так как detection-service ещё нет
                    # await client.post(DETECTION_URL, json=features, timeout=1.0)
                    pass
                except Exception:
                    pass


async def main():
    print("🚀 Starting Flow Collector...")
    print(f"👀 Sniffing traffic on port {TARGET_PORT}")
    
    # Запускаем фоновую задачу по отправке потоков
    asyncio.create_task(flush_finished_flows())
    
    # Запускаем сниффер (в отдельном потоке)
    sniffer = AsyncSniffer(
        filter=f"tcp port {TARGET_PORT} or udp port {TARGET_PORT}",
        prn=process_packet,
        store=False
    )
    sniffer.start()
    
    try:
        # Бесконечный цикл, чтобы скрипт не завершился
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        sniffer.stop()

if __name__ == "__main__":
    asyncio.run(main())