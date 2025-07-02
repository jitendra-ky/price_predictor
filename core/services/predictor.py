import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import os
from django.conf import settings
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
from tensorflow.keras.models import load_model

class StockPredictor:
    def __init__(self, ticker, model_path=None, seq_len=60):
        self.ticker = ticker.upper()
        self.seq_len = seq_len
        self.model_path = model_path or settings.MODEL_PATH
        self.scaler = MinMaxScaler()
        self.model = None
        self.df = None

    def fetch_data(self):
        # Download last 10 years of OHLCV data
        self.df = yf.download(self.ticker, period="10y", progress=False)
        if self.df.empty:
            raise ValueError(f"No data found for ticker {self.ticker}")
        return self.df

    def preprocess(self):
        prices = self.df[['Close']].values
        scaled = self.scaler.fit_transform(prices)
        
        # Create sequences
        X, y = [], []
        for i in range(self.seq_len, len(scaled)):
            X.append(scaled[i - self.seq_len:i])
            y.append(scaled[i])
        X = np.array(X).reshape(-1, self.seq_len, 1)
        y = np.array(y)
        return X, y

    def load_model(self):
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        self.model = load_model(self.model_path)

    def predict(self, X):
        # Predict all data
        y_pred_scaled = self.model.predict(X, verbose=0)
        y_pred = self.scaler.inverse_transform(y_pred_scaled)
        return y_pred

    def calculate_metrics(self, y_true, y_pred):
        y_true_inv = self.scaler.inverse_transform(y_true)
        mse = mean_squared_error(y_true_inv, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_true_inv, y_pred)
        return mse, rmse, r2

    def predict_next_day(self, X):
        last_seq = X[-1].reshape(1, self.seq_len, 1)
        pred_scaled = self.model.predict(last_seq, verbose=0)
        pred_price = self.scaler.inverse_transform(pred_scaled)[0][0]
        return float(pred_price)

    def save_plot(self, filename, fig):
        media_root = settings.MEDIA_ROOT
        plots_dir = os.path.join(media_root, "plots")
        os.makedirs(plots_dir, exist_ok=True)
        path = os.path.join(plots_dir, filename)
        fig.savefig(path)
        plt.close(fig)
        return f"/media/plots/{filename}"

    def generate_plots(self, y_actual, y_pred):
        # Plot 1: Price history
        fig1, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(self.df['Close'])
        ax1.set_title(f"{self.ticker} Closing Price History")
        path1 = self.save_plot(f"{self.ticker}_history.png", fig1)

        # Plot 2: Actual vs predicted
        y_actual_inv = self.scaler.inverse_transform(y_actual)
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(y_actual_inv, label="Actual")
        ax2.plot(y_pred, label="Predicted")
        ax2.legend()
        ax2.set_title("Actual vs Predicted Prices")
        path2 = self.save_plot(f"{self.ticker}_pred_vs_actual.png", fig2)

        return [path1, path2]

    def run(self):
        self.fetch_data()
        X, y = self.preprocess()
        self.load_model()
        y_pred = self.predict(X)
        mse, rmse, r2 = self.calculate_metrics(y, y_pred)
        next_day_price = self.predict_next_day(X)
        plot_urls = self.generate_plots(y, y_pred)

        return {
            "ticker": self.ticker,
            "next_day_price": round(next_day_price, 2),
            "mse": round(mse, 3),
            "rmse": round(rmse, 3),
            "r2": round(r2, 3),
            "plot_urls": plot_urls,
        }
