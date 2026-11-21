import time
from dataclasses import dataclass, field

# Размер заголовков для расчёта payload (приблизительно)
TCP_HDR = 20
IP_HDR = 20
ETH_HDR = 14

@dataclass
class Flow:
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    proto: int
    start_time: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    # Счётчики
    src_packets: int = 0
    dst_packets: int = 0
    src_bytes: int = 0
    dst_bytes: int = 0
    
    # TCP флаги (для определения начала/конца)
    syn_seen: bool = False
    fin_seen: bool = False
    rst_seen: bool = False

    def add_packet(self, packet, direction: str):
        """direction: 'fwd' (клиент->сервер) или 'bwd' (сервер->клиент)."""
        self.last_seen = time.time()
        pkt_len = len(packet)
        
        if direction == 'fwd':
            self.src_packets += 1
            self.src_bytes += pkt_len
        else:
            self.dst_packets += 1
            self.dst_bytes += pkt_len
            
        # Проверка TCP флагов
        if packet.haslayer('TCP'):
            flags = packet['TCP'].flags
            if flags & 0x02: # SYN
                self.syn_seen = True
            if flags & 0x01: # FIN
                self.fin_seen = True
            if flags & 0x04: # RST
                self.rst_seen = True

    def is_finished(self, timeout: float = 5.0) -> bool:
        """Поток завершён, если видели FIN/RST или прошло timeout секунд."""
        if self.fin_seen or self.rst_seen:
            return True
        return (time.time() - self.last_seen) > timeout

    def to_features(self) -> dict:
        """Возвращает словарь с признаками для ML."""
        duration = max(0.001, self.last_seen - self.start_time) # чтобы не делить на 0
        return {
            "src_ip": self.src_ip,
            "dst_ip": self.dst_ip,
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "protocol": self.proto,
            "duration": round(duration, 3),
            "src_packets": self.src_packets,
            "dst_packets": self.dst_packets,
            "src_bytes": self.src_bytes,
            "dst_bytes": self.dst_bytes,
            # Производные признаки
            "src_bytes_per_sec": round(self.src_bytes / duration, 2),
            "dst_bytes_per_sec": round(self.dst_bytes / duration, 2),
            "pkt_rate": round((self.src_packets + self.dst_packets) / duration, 2),
        }