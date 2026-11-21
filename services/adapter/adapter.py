# services/adapter/adapter.py (упрощённый пример)
import pandas as pd
import httpx
import time
import glob
import os

DETECTION_URL = "http://detection-service:8001/predict"
CSV_DIR = "/app/output" # Папка, куда CICFlowMeter пишет CSV

def main():
    processed_files = set()
    while True:
        # Ищем новые CSV файлы
        csv_files = glob.glob(os.path.join(CSV_DIR, "*.csv"))
        for file in csv_files:
            if file in processed_files:
                continue
            
            print(f"Processing {file}...")
            try:
                df = pd.read_csv(file)
                for _, row in df.iterrows():
                    # Преобразуем строку в словарь, убираем ненужное
                    payload = row.to_dict()
                    # Отправляем в детектор
                    with httpx.Client() as client:
                        resp = client.post(DETECTION_URL, json=payload, timeout=2.0)
                        if resp.status_code == 200:
                            print(f"Prediction: {resp.json()}")
            except Exception as e:
                print(f"Error processing {file}: {e}")
            
            processed_files.add(file)
        
        time.sleep(5) # Проверяем папку каждые 5 секунд

if __name__ == "__main__":
    main()