from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np

app = FastAPI()
# Загружаем лучшую модель (например, CatBoost)
model = joblib.load("models/catboost_cicids.pkl")

# Список признаков, на которых обучалась модель (нужно сохранить при обучении!)
FEATURE_COLS = [...] # Список 80+ названий колонок

class FlowFeatures(BaseModel):
    # Здесь должны быть все 80+ полей, но для простоты используем dict
    # В реальности лучше сгенерировать Pydantic-модель динамически из списка
    pass

@app.post("/predict")
async def predict(flow: dict):
    # Преобразуем в DataFrame, чтобы сохранить порядок колонок
    df = pd.DataFrame([flow])
    # Оставляем только нужные колонки и заполняем пропуски
    X = df.reindex(columns=FEATURE_COLS, fill_value=0)
    # Предсказание
    pred = model.predict(X)[0]
    proba = model.predict_proba(X)[0].max()
    return {"label": int(pred), "confidence": float(proba)}