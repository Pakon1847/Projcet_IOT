import json, time
import numpy as np
from pathlib import Path
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

MODEL_DIR = Path(__file__).parent.parent / "models"

class PM25Predictor:
    def __init__(self, use_int8=True):
        fname = "pm25_lstm_int8.tflite" if use_int8 else "pm25_lstm.tflite"
        self.interp = tflite.Interpreter(model_path=str(MODEL_DIR / fname))
        self.interp.allocate_tensors()
        self.ii = self.interp.get_input_details()[0]["index"]
        self.oi = self.interp.get_output_details()[0]["index"]
        with open(MODEL_DIR / "model_meta.json") as f:
            m = json.load(f)
        self.look_back  = m["look_back"]
        self.horizon    = m["horizon"]
        self.features   = m["features"]
        self.s_min = np.array(m["scaler_min"])
        self.s_max = np.array(m["scaler_max"])
        self.p_min = m["pm25_min"]
        self.p_max = m["pm25_max"]

    def predict(self, buffer):
        if isinstance(buffer[0], dict):
            arr = np.array([[r[f] for f in self.features] for r in buffer], dtype=np.float32)
        else:
            arr = np.array(buffer, dtype=np.float32)
        x = ((arr - self.s_min) / (self.s_max - self.s_min))[np.newaxis]
        t0 = time.perf_counter()
        self.interp.set_tensor(self.ii, x)
        self.interp.invoke()
        out = self.interp.get_tensor(self.oi)[0]
        ms = (time.perf_counter() - t0) * 1000
        forecast = (out * (self.p_max - self.p_min) + self.p_min).tolist()
        return {"forecast_ugm3": forecast, "latency_ms": round(ms, 2)}
