import pandas as pd
import numpy as np
import os
import joblib
import warnings
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, matthews_corrcoef, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

warnings.filterwarnings('ignore')

DATA_FILE = "data/processed/cicids2018_cleaned.parquet"
MODELS_DIR = "models"

# Единый список признаков (белый список)
ALLOWED_FEATURES = [
    'Flow Duration', 'Tot Fwd Pkts', 'Tot Bwd Pkts',
    'TotLen Fwd Pkts', 'TotLen Bwd Pkts',
    'Fwd Pkt Len Max', 'Fwd Pkt Len Min', 'Fwd Pkt Len Mean', 'Fwd Pkt Len Std',
    'Bwd Pkt Len Max', 'Bwd Pkt Len Min', 'Bwd Pkt Len Mean', 'Bwd Pkt Len Std',
    'Pkt Len Min', 'Pkt Len Max', 'Pkt Len Mean', 'Pkt Len Std',
    'Pkt Size Avg', 'Fwd Seg Size Avg', 'Bwd Seg Size Avg',
    'Fwd Header Len', 'Bwd Header Len',
    'Down/Up Ratio', 'Fwd Act Data Pkts'
]

DROP_COLS = ['Pkt Len Var', 'Subflow Fwd Pkts', 'Subflow Bwd Pkts',
             'Subflow Fwd Byts', 'Subflow Bwd Byts', 'Fwd Seg Size Min']

def check_duplicates(df, feature_cols):
    """Проверка дубликатов и утечек в данных"""
    print(f"\n{'='*50}")
    print("ПРОВЕРКА ДУБЛИКАТОВ")
    print(f"{'='*50}")
    
    # Проверка дубликатов по всем признакам
    dup_count = df.duplicated(subset=feature_cols).sum()
    print(f"Дубликатов по признакам: {dup_count}")
    
    if dup_count > 0:
        print("⚠️  Дубликаты могут вызвать утечку данных (одинаковые примеры в train и test)")
        # Можно удалить: df = df.drop_duplicates(subset=feature_cols)
    else:
        print("✅ Дубликатов не обнаружено")

def check_feature_leakage(df, feature_cols, label_col='is_attack'):
    """Проверяем, не содержат ли признаки прямую информацию о метке"""
    print(f"\n{'='*50}")
    print("ДИАГНОСТИКА УТЕЧКИ В ПРИЗНАКАХ")
    print(f"{'='*50}")
    
    suspicious = []
    
    for col in feature_cols:
        benign_vals = df[df[label_col]==0][col].dropna().unique()
        attack_vals = df[df[label_col]==1][col].dropna().unique()
        
        # Если значения не пересекаются - полная утечка
        overlap = set(benign_vals) & set(attack_vals)
        if len(overlap) == 0 and len(benign_vals) > 0 and len(attack_vals) > 0:
            print(f"⚠️  ПОДОЗРИТЕЛЬНО: {col} не имеет пересечений между классами!")
            suspicious.append(col)
    
    if not suspicious:
        print("✅ Прямой утечки в признаках не обнаружено")
    
    return suspicious

def analyze_feature_importance(model, feature_cols):
    """Анализ важности признаков"""
    print(f"\n{'='*50}")
    print("ВАЖНОСТЬ ПРИЗНАКОВ (топ-10)")
    print(f"{'='*50}")
    
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print(importances.head(10).to_string(index=False))
    
    if importances.iloc[0]['importance'] > 0.5:
        print(f"\n⚠️  Признак {importances.iloc[0]['feature']} доминирует ({importances.iloc[0]['importance']:.1%})")

def load_and_prepare(binary=True):
    """Загрузка данных: binary=True — BENIGN vs ATTACK, иначе — типы атак."""
    print("Загрузка данных...")
    df = pd.read_parquet(DATA_FILE)
    
    if 'Timestamp' not in df.columns:
        raise ValueError("Timestamp не найден!")
    
    df = df.sort_values('Timestamp').reset_index(drop=True)
    
    label_col = 'Label'
    if label_col not in df.columns:
        possible = [c for c in df.columns if 'label' in c.lower()]
        label_col = possible[0] if possible else df.columns[-1]
    
    # Выбираем признаки
    feature_cols = [c for c in ALLOWED_FEATURES if c in df.columns and c not in DROP_COLS]
    
    if binary:
        df['is_attack'] = (df[label_col].str.upper() != 'BENIGN').astype(int)
        target_col = 'is_attack'
        print(f"Бинарная классификация: {df[target_col].value_counts().to_dict()}")
    else:
        df['attack_type'] = df[label_col].str.upper().str.strip()
        # Объединяем редкие классы
        rare_classes = df['attack_type'].value_counts()
        rare_classes = rare_classes[rare_classes < 1000].index
        df.loc[df['attack_type'].isin(rare_classes), 'attack_type'] = 'OTHER'
        target_col = 'attack_type'
        print(f"Многоклассовая классификация:\n{df[target_col].value_counts()}")
    
    return df, feature_cols, target_col

def train_binary(df, feature_cols, target_col):
    """Обучение бинарных моделей (RF, LightGBM, CatBoost)."""
    print(f"\n{'='*50}")
    print("БИНАРНАЯ КЛАССИФИКАЦИЯ (Benign vs Attack)")
    print(f"{'='*50}")
    
    # --- УДАЛЯЕМ ДУБЛИКАТЫ ---
    initial_len = len(df)
    df = df.drop_duplicates(subset=feature_cols)
    print(f"Удалено дубликатов: {initial_len - len(df)} (осталось {len(df)})")
    
    X = df[feature_cols].values
    y = df[target_col].values

    """Обучение бинарных моделей (RF, LightGBM, CatBoost)."""
    print(f"\n{'='*50}")
    print("БИНАРНАЯ КЛАССИФИКАЦИЯ (Benign vs Attack)")
    print(f"{'='*50}")
    
    X = df[feature_cols].values
    y = df[target_col].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")
    
    results = {}
    
    # 1. Random Forest
    print(f"\n{'='*50}\nОбучение RandomForest...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1, class_weight='balanced')
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    rf_f1 = f1_score(y_test, y_pred, average='macro')
    rf_mcc = matthews_corrcoef(y_test, y_pred)
    print(f"Macro-F1: {rf_f1:.4f} | MCC: {rf_mcc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['Benign', 'Attack']))
    analyze_feature_importance(rf, feature_cols)
    joblib.dump(rf, os.path.join(MODELS_DIR, "randomforest_cicids.pkl"))
    results['RandomForest'] = (rf_f1, rf_mcc)
    
    # 2. LightGBM
    print(f"\n{'='*50}\nОбучение LightGBM...")
    lgbm = LGBMClassifier(n_estimators=100, random_state=42, n_jobs=-1, class_weight='balanced', verbosity=-1)
    lgbm.fit(X_train, y_train)
    y_pred = lgbm.predict(X_test)
    lgbm_f1 = f1_score(y_test, y_pred, average='macro')
    lgbm_mcc = matthews_corrcoef(y_test, y_pred)
    print(f"Macro-F1: {lgbm_f1:.4f} | MCC: {lgbm_mcc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['Benign', 'Attack']))
    joblib.dump(lgbm, os.path.join(MODELS_DIR, "lightgbm_cicids.pkl"))
    results['LightGBM'] = (lgbm_f1, lgbm_mcc)
    
    # 3. CatBoost
    print(f"\n{'='*50}\nОбучение CatBoost...")
    cat = CatBoostClassifier(iterations=100, random_seed=42, verbose=False, auto_class_weights='Balanced')
    cat.fit(X_train, y_train)
    y_pred = cat.predict(X_test)
    cat_f1 = f1_score(y_test, y_pred, average='macro')
    cat_mcc = matthews_corrcoef(y_test, y_pred)
    print(f"Macro-F1: {cat_f1:.4f} | MCC: {cat_mcc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['Benign', 'Attack']))
    joblib.dump(cat, os.path.join(MODELS_DIR, "catboost_cicids.pkl"))
    results['CatBoost'] = (cat_f1, cat_mcc)
    
    # Итог
    print(f"\n{'='*50}\nИТОГОВОЕ СРАВНЕНИЕ (бинарная):")
    print(f"{'Модель':<15} {'Macro-F1':<12} {'MCC':<12}")
    for name, (f1, mcc) in results.items():
        print(f"{name:<15} {f1:<12.4f} {mcc:<12.4f}")

def train_multiclass(df, feature_cols, target_col):
    """Обучение многоклассовой модели (RandomForest)."""
    print(f"\n{'='*50}")
    print("МНОГОКЛАССОВАЯ КЛАССИФИКАЦИЯ (типы атак)")
    print(f"{'='*50}")
    
    # --- УДАЛЯЕМ ДУБЛИКАТЫ ---
    initial_len = len(df)
    df = df.drop_duplicates(subset=feature_cols)
    print(f"Удалено дубликатов: {initial_len - len(df)} (осталось {len(df)})")
    
    X = df[feature_cols].values
    y = df[target_col].values

    """Обучение многоклассовой модели (RandomForest)."""
    print(f"\n{'='*50}")
    print("МНОГОКЛАССОВАЯ КЛАССИФИКАЦИЯ (типы атак)")
    print(f"{'='*50}")
    
    X = df[feature_cols].values
    y = df[target_col].values
    
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    print(f"Классы: {le.classes_}")
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")
    
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1, class_weight='balanced')
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    
    macro_f1 = f1_score(y_test, y_pred, average='macro')
    print(f"\nMacro-F1: {macro_f1:.4f}")
    print(classification_report(y_test, y_pred, target_names=le.classes_))
    
    cm = confusion_matrix(y_test, y_pred)
    print(f"\nConfusion Matrix (строки = истинные, столбцы = предсказанные):")
    print(f"Классы: {le.classes_}")
    print(cm)
    
    joblib.dump(model, os.path.join(MODELS_DIR, "rf_multiclass.pkl"))
    joblib.dump(le, os.path.join(MODELS_DIR, "label_encoder.pkl"))
    
    return macro_f1

if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    # 1. Бинарная классификация
    df_bin, feature_cols, target_bin = load_and_prepare(binary=True)
    check_duplicates(df_bin, feature_cols)
    check_feature_leakage(df_bin, feature_cols, target_bin)
    
    # Сохраняем признаки
    with open(os.path.join(MODELS_DIR, "feature_cols.txt"), "w") as f:
        for col in feature_cols:
            f.write(f"{col}\n")
    
    train_binary(df_bin, feature_cols, target_bin)
    
    # 2. Многоклассовая классификация
    print("\n" + "="*50)
    print("ПЕРЕХОД К МНОГОКЛАССОВОЙ КЛАССИФИКАЦИИ")
    print("="*50)
    df_multi, _, target_multi = load_and_prepare(binary=False)
    train_multiclass(df_multi, feature_cols, target_multi)