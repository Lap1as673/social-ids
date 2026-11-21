import pandas as pd
import numpy as np
import os
import glob

DATA_DIR = "/home/laplas/Документы/Project/social-ids/services/ml/data/raw"
OUTPUT_FILE = "/home/laplas/Документы/Project/social-ids/services/ml/data/processed/cicids2018_cleaned.parquet"

def clean_cicids(df: pd.DataFrame) -> pd.DataFrame:
    print(f"Исходный размер: {df.shape}")
    
    # 1. Заменяем inf и NaN
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    # 2. Удаляем отрицательные Flow Duration
    if 'Flow Duration' in df.columns:
        neg_mask = df['Flow Duration'] < 0
        print(f"Строк с отрицательным Flow Duration: {neg_mask.sum()}")
        df = df[~neg_mask]
    
    # 3. Удаляем дубликаты (СОХРАНЯЯ Timestamp для сплита!)
    df = df.drop_duplicates()
    
    # 4. Удаляем вшитые заголовки
    for col in df.columns:
        if df[col].dtype == 'object':
            header_mask = df[col] == col
            if header_mask.any():
                print(f"Найдены вшитые заголовки в колонке {col}: {header_mask.sum()}")
                df = df[~header_mask]
    
    # 5. Удаляем константные признаки (неинформативные)
    nunique = df.nunique()
    cols_to_drop = nunique[nunique <= 1].index.tolist()
    if cols_to_drop:
        print(f"Удаляем константные колонки: {cols_to_drop}")
        df = df.drop(columns=cols_to_drop)
    
    print(f"Размер после очистки: {df.shape}")
    return df

def main():
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not csv_files:
        print(f"CSV файлы не найдены в {DATA_DIR}")
        return
    
    dfs = []
    for f in csv_files:
        print(f"Загрузка {os.path.basename(f)}...")
        df = pd.read_csv(f, low_memory=False)
        df.columns = df.columns.str.strip()
        
        # Парсим Timestamp если есть
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        
        dfs.append(df)
    
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Сортируем по времени СРАЗУ (важно для TimeSeriesSplit)
    if 'Timestamp' in full_df.columns:
        full_df = full_df.sort_values('Timestamp').reset_index(drop=True)
        print(f"Период данных: {full_df['Timestamp'].min()} — {full_df['Timestamp'].max()}")
    
    cleaned_df = clean_cicids(full_df)
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    cleaned_df.to_parquet(OUTPUT_FILE, index=False)
    print(f"Сохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()