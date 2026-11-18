from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from app.team_pv.runtime import (
    DataRepository,
    FeatureEngineer,
    HanPVConfig,
    PVDataProcessor,
    StandardScaler1D,
    TFTPVModel,
    masked_mape,
    save_package,
)


class PVForecastDataset(Dataset):
    def __init__(
        self,
        frame: pd.DataFrame,
        encoder_features: list[str],
        config: HanPVConfig,
        encoder_scaler: StandardScaler1D | None = None,
        target_scaler: StandardScaler1D | None = None,
        fit_scalers: bool = False,
    ) -> None:
        self.frame = frame.reset_index(drop=True).copy()
        self.encoder_features = encoder_features
        self.config = config
        enc_values = self.frame[encoder_features].to_numpy(dtype=np.float32)
        target_values = self.frame[["pv_norm"]].to_numpy(dtype=np.float32)
        self.encoder_scaler = encoder_scaler or StandardScaler1D()
        self.target_scaler = target_scaler or StandardScaler1D()
        if fit_scalers:
            self.encoder_scaler.fit(enc_values)
            self.target_scaler.fit(target_values)
        self.encoder_array = self.encoder_scaler.transform(enc_values).astype(np.float32)
        self.target_array = target_values.astype(np.float32)
        self.target_scaled = self.target_scaler.transform(target_values).astype(np.float32)
        self.timestamp_array = self.frame["시각"].to_numpy()
        min_start = max(config.encoder_length, config.decoder_length)
        max_start = len(self.frame) - config.prediction_length + 1
        self.start_indices = list(range(min_start, max_start))

    def __len__(self) -> int:
        return len(self.start_indices)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor | int]:
        start = self.start_indices[idx]
        enc_start = start - self.config.encoder_length
        dec_start = start - self.config.decoder_length
        pred_end = start + self.config.prediction_length
        return {
            "encoder_x": torch.tensor(self.encoder_array[enc_start:start], dtype=torch.float32),
            "decoder_pv": torch.tensor(self.target_scaled[dec_start:start], dtype=torch.float32),
            "decoder_weather": torch.tensor(self.encoder_array[start:pred_end], dtype=torch.float32),
            "target_y": torch.tensor(self.target_scaled[start:pred_end], dtype=torch.float32),
            "target_y_raw": torch.tensor(self.target_array[start:pred_end], dtype=torch.float32),
            "pv_max": torch.tensor(float(self.frame["pv_max"].iloc[start]), dtype=torch.float32),
            "start_index": start,
        }


class ModelTrainer:
    def __init__(self, config: HanPVConfig, encoder_features: list[str]) -> None:
        self.config = config
        self.encoder_features = encoder_features
        if config.decoder_length < config.prediction_length:
            raise ValueError("decoder_length must be >= prediction_length")

    def build_datasets(self, frame: pd.DataFrame) -> tuple[PVForecastDataset, PVForecastDataset]:
        frame = frame.copy()
        frame["시각"] = pd.to_datetime(frame["시각"])
        frame = frame.sort_values("시각").reset_index(drop=True)
        train_frame = frame[frame["시각"] < pd.Timestamp(self.config.train_end)].copy()
        test_frame_only = frame[
            (frame["시각"] >= pd.Timestamp(self.config.test_start))
            & (frame["시각"] < pd.Timestamp(self.config.test_end))
        ].copy()
        if train_frame.empty:
            raise ValueError("train frame is empty")
        if test_frame_only.empty:
            raise ValueError("test frame is empty")

        context_frame = train_frame.tail(self.config.encoder_length + self.config.decoder_length).copy()
        valid_frame = pd.concat([context_frame, test_frame_only], ignore_index=True)
        print("train range:", train_frame["시각"].min(), "~", train_frame["시각"].max(), flush=True)
        print("valid/test range:", test_frame_only["시각"].min(), "~", test_frame_only["시각"].max(), flush=True)
        print("train rows:", len(train_frame), flush=True)
        print("valid rows with context:", len(valid_frame), flush=True)
        print("pure test rows:", len(test_frame_only), flush=True)

        encoder_scaler = StandardScaler1D()
        target_scaler = StandardScaler1D()
        train_ds = PVForecastDataset(
            train_frame,
            self.encoder_features,
            self.config,
            encoder_scaler=encoder_scaler,
            target_scaler=target_scaler,
            fit_scalers=True,
        )
        valid_ds = PVForecastDataset(
            valid_frame,
            self.encoder_features,
            self.config,
            encoder_scaler=train_ds.encoder_scaler,
            target_scaler=train_ds.target_scaler,
            fit_scalers=False,
        )
        if len(train_ds) == 0 or len(valid_ds) == 0:
            raise ValueError("dataset has no samples")
        return train_ds, valid_ds

    def train(self, frame: pd.DataFrame) -> tuple[nn.Module, dict[str, float], pd.DataFrame, PVForecastDataset]:
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)
        train_ds, valid_ds = self.build_datasets(frame)
        train_loader = DataLoader(train_ds, batch_size=self.config.batch_size, shuffle=True)
        valid_loader = DataLoader(valid_ds, batch_size=self.config.batch_size, shuffle=False)
        model = TFTPVModel(
            encoder_input_size=len(self.encoder_features),
            hidden_size=self.config.hidden_size,
            lstm_layers=self.config.lstm_layers,
            attention_heads=self.config.attention_heads,
            dropout=self.config.dropout,
            prediction_length=self.config.prediction_length,
        )
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = model.to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)
        loss_fn = nn.SmoothL1Loss()
        best_state: dict[str, torch.Tensor] | None = None
        best_valid_loss = float("inf")
        patience = 5
        wait = 0

        for epoch in range(1, self.config.max_epochs + 1):
            model.train()
            train_losses = []
            for batch in train_loader:
                optimizer.zero_grad()
                pred = model(
                    batch["encoder_x"].to(device),
                    batch["decoder_pv"].to(device),
                    batch["decoder_weather"].to(device),
                )
                loss = loss_fn(pred, batch["target_y"].to(device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(float(loss.item()))

            model.eval()
            valid_losses = []
            with torch.no_grad():
                for batch in valid_loader:
                    pred = model(
                        batch["encoder_x"].to(device),
                        batch["decoder_pv"].to(device),
                        batch["decoder_weather"].to(device),
                    )
                    loss = loss_fn(pred, batch["target_y"].to(device))
                    valid_losses.append(float(loss.item()))

            train_loss = float(np.mean(train_losses))
            valid_loss = float(np.mean(valid_losses))
            print(f"epoch={epoch:03d} train_loss={train_loss:.6f} valid_loss={valid_loss:.6f}", flush=True)
            if valid_loss < best_valid_loss:
                best_valid_loss = valid_loss
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                wait = 0
            else:
                wait += 1
                if wait >= patience:
                    print("Early stopping triggered.", flush=True)
                    break

        if best_state is None:
            raise RuntimeError("training failed")
        model.load_state_dict(best_state)
        pred_df = self.predict_validation(model, valid_ds)
        pred_df["시각"] = pd.to_datetime(pred_df["시각"])
        pred_df = pred_df[
            (pred_df["시각"] >= self.config.test_start)
            & (pred_df["시각"] < self.config.test_end)
        ].reset_index(drop=True)
        metrics = self.evaluate(pred_df)
        return model, metrics, pred_df, train_ds

    def predict_validation(self, model: nn.Module, dataset: PVForecastDataset) -> pd.DataFrame:
        device = next(model.parameters()).device
        model.eval()
        loader = DataLoader(dataset, batch_size=self.config.batch_size, shuffle=False)
        records: list[pd.DataFrame] = []
        with torch.no_grad():
            for batch in loader:
                pred_scaled = model(
                    batch["encoder_x"].to(device),
                    batch["decoder_pv"].to(device),
                    batch["decoder_weather"].to(device),
                ).cpu()
                batch_size = pred_scaled.shape[0]
                pred_scaled_np = pred_scaled.numpy().reshape(-1, 1)
                pred_norm = dataset.target_scaler.inverse_transform(pred_scaled_np).reshape(batch_size, -1)
                actual_norm = batch["target_y_raw"].numpy().reshape(batch_size, -1)
                pv_max = batch["pv_max"].numpy().reshape(-1)
                start_indices = batch["start_index"].numpy().tolist()
                for row_idx, start_index in enumerate(start_indices):
                    timestamps = dataset.timestamp_array[start_index:start_index + self.config.prediction_length]
                    actual_mwh = actual_norm[row_idx] * pv_max[row_idx]
                    pred_mwh = np.clip(pred_norm[row_idx], 0.0, None) * pv_max[row_idx]
                    records.append(
                        pd.DataFrame(
                            {
                                "시각": pd.to_datetime(timestamps),
                                "실제값(MWh)": actual_mwh,
                                "예측값(MWh)": pred_mwh,
                                "sample_start_index": start_index,
                            }
                        )
                    )
        pred_df = pd.concat(records, ignore_index=True)
        return (
            pred_df.sort_values(["시각", "sample_start_index"])
            .drop_duplicates(subset=["시각"], keep="last")
            .reset_index(drop=True)
        )

    def evaluate(self, pred_df: pd.DataFrame) -> dict[str, float]:
        y_true = pred_df["실제값(MWh)"].to_numpy(dtype=float)
        y_pred = pred_df["예측값(MWh)"].to_numpy(dtype=float)
        daytime = pred_df[pd.to_datetime(pred_df["시각"]).dt.hour.between(6, 18)]
        y_true_day = daytime["실제값(MWh)"].to_numpy(dtype=float)
        y_pred_day = daytime["예측값(MWh)"].to_numpy(dtype=float)
        return {
            "mae_mwh": float(np.mean(np.abs(y_true - y_pred))),
            "rmse_mwh": float(np.sqrt(np.mean((y_true - y_pred) ** 2))),
            "mape_percent": masked_mape(y_true, y_pred),
            "daytime_mae_mwh": float(np.mean(np.abs(y_true_day - y_pred_day))),
            "daytime_rmse_mwh": float(np.sqrt(np.mean((y_true_day - y_pred_day) ** 2))),
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pv-csv", required=True)
    parser.add_argument("--weather-csv", required=True)
    parser.add_argument("--output-dir", default="models/han_tft_pv_incheon_20250506")
    parser.add_argument("--epochs", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = HanPVConfig(max_epochs=args.epochs)
    repo = DataRepository(config)
    pv_df = repo.load_pv_data(args.pv_csv)
    weather_df = repo.load_weather_data(args.weather_csv)
    merged = PVDataProcessor().merge_and_clean(pv_df, weather_df)
    print("merged length:", len(merged), flush=True)
    print(merged.head(), flush=True)
    print(merged.isna().sum(), flush=True)
    feature_engineer = FeatureEngineer()
    frame = feature_engineer.build_training_frame(merged)
    trainer = ModelTrainer(config, feature_engineer.encoder_features)
    model, metrics, pred_df, train_ds = trainer.train(frame)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_dir / "training_frame.csv", index=False, encoding="utf-8-sig")
    pred_df.to_csv(output_dir / "tft_predictions.csv", index=False, encoding="utf-8-sig")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "metrics.txt").write_text(
        "\n".join([f"{key}={value:.6f}" for key, value in metrics.items()]),
        encoding="utf-8",
    )
    save_package(
        output_dir,
        config,
        model.cpu(),
        train_ds.encoder_scaler,
        train_ds.target_scaler,
        metrics,
        pv_max=float(frame["pv_max"].iloc[0]),
        source_files={"pv_csv": str(Path(args.pv_csv).resolve()), "weather_csv": str(Path(args.weather_csv).resolve())},
    )
    print("metrics:", metrics, flush=True)
    print("package:", output_dir.resolve(), flush=True)


if __name__ == "__main__":
    main()
