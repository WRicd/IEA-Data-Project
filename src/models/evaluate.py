import numpy as np


def regression_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err))) if len(y_true) else 0.0
    rmse = float(np.sqrt(np.mean(err**2))) if len(y_true) else 0.0
    denom = np.where(np.abs(y_true) < 1e-9, np.nan, np.abs(y_true))
    mape = float(np.nanmean(np.abs(err) / denom) * 100) if len(y_true) else 0.0
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return {"MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}
