import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

def train():
    print("Загрузка данных...")
    benign = pd.read_csv("data/benign.csv")
    benign["label"] = 0  # 0 = нормальный трафик

    attack = pd.read_csv("data/attack.csv")
    attack["label"] = 1  # 1 = атака

    df = pd.concat([benign, attack], ignore_index=True)
    
    features = [
        "duration", "src_packets", "dst_packets", "src_bytes", "dst_bytes",
        "src_bytes_per_sec", "dst_bytes_per_sec", "pkt_rate"
    ]
    X = df[features]
    y = df["label"]

    print(f"Всего потоков: {len(df)}")
    print(f"Нормальных: {len(benign)}, Атак: {len(attack)}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    print("Обучение RandomForest...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=["Benign", "Attack"]))

    joblib.dump(clf, "model.pkl")
    print("Модель сохранена в model.pkl")

if __name__ == "__main__":
    train()