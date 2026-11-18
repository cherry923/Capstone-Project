"""
EVCS Runtime Module for FastAPI Inference

이 파일은 학습 노트북에서 학습/평가/저장 실행 코드를 제외하고,
FastAPI 서버에서 모델을 로드하고 추론하는 데 필요한 런타임 정의만 포함합니다.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal

import numpy as np
import pandas as pd
import pulp

import gymnasium as gym
from gymnasium import spaces

from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal


SEED = 42
random.seed(SEED)
np.random.seed(SEED)

UpperAlgo = Literal["DEFAULT", "MILP", "SAC", "PI_SAC", "PI_SAC_FULL"]
LowerAlgo = Literal["DEFAULT", "SAC", "PI_SAC", "PI_SAC_FULL"]
DataMode = Literal["synthetic", "real"]


@dataclass
class StationConfig:
    pv_capacity_kwh: float = 100.0
    ess_capacity_kwh: float = 998.0
    ess_max_ratio: float = 0.10
    soc_min: float = 0.10
    soc_max: float = 0.90
    vmax_kwh: float = 1200.0
    peak_limit_kwh: float = 450.0


@dataclass
class SystemConfig:
    n_station: int = 3
    horizon: int = 24
    tou_low: float = 84.5
    tou_mid: float = 111.9
    tou_high: float = 174.0
    share_abs_max_kwh: float = 120.0
    share_transfer_cost: float = 0.03


@dataclass
class SACParams:
    learning_rate: float = 1e-4
    buffer_size: int = 10_000
    batch_size: int = 256
    gamma: float = 0.99
    tau: float = 0.05
    train_freq: int = 1
    gradient_steps: int = 1
    total_timesteps_lower: int = 10_000
    total_timesteps_upper: int = 10_000
    verbose: int = 1


@dataclass
class PILagrangianParams:
    lambda_init: List[float] = field(default_factory=lambda: [50.0, 50.0])
    kp: float = 0.4
    ki: float = 0.005
    i_max: float = 30.0
    lambda_decay: float = 0.999
    lambda_max: List[float] = field(default_factory=lambda: [3000.0, 3000.0])
    epsilon: List[float] = field(default_factory=lambda: [0.0, 0.0])


@dataclass
class ExperimentConfig:
    upper_algo: UpperAlgo = "MILP"
    lower_algo: LowerAlgo = "PI_SAC"
    data_mode: DataMode = "synthetic"
    real_data_path: str = "/content/real_evcs_data.csv"
    use_independent_lower_agents: bool = True
    bad_prediction_eval: bool = True
    reward_grid_weight: float = 1.0
    reward_self_weight: float = 0.3
    reward_loss_weight: float = 0.2
    model_dir: str = "./models"
    result_dir: str = "./results"


ST_CFG = StationConfig()
SYS_CFG = SystemConfig()
SAC_CFG = SACParams()
PI_CFG = PILagrangianParams()
EXP_CFG = ExperimentConfig()


def generate_tou_24() -> np.ndarray:
    tou = np.full(24, SYS_CFG.tou_low, dtype=np.float32)
    tou[7:12] = SYS_CFG.tou_mid
    tou[18:21] = SYS_CFG.tou_mid
    tou[12:18] = SYS_CFG.tou_high
    return tou


def generate_pv_forecast(scale: float = 1.0, noise: float = 0.03) -> np.ndarray:
    hours = np.arange(24)
    solar_shape = np.maximum(0.0, np.sin((hours - 6) / 12 * np.pi))
    pv = ST_CFG.pv_capacity_kwh * solar_shape * scale
    pv *= 1.0 + np.random.normal(0, noise, size=24)
    return np.clip(pv, 0.0, ST_CFG.pv_capacity_kwh * 1.3).astype(np.float32)


def generate_ev_demand_forecast(num_ev_mean: int = 36, num_ev_std: int = 5, charger_power_limit_kw: float = 100.0) -> np.ndarray:
    n_ev = max(5, int(np.random.normal(num_ev_mean, num_ev_std)))
    start_mu, start_sigma = 13.85, 4.99
    duration_scale_min, amount_scale_kwh = 45.32, 23.02
    minute_load = np.zeros(24 * 60, dtype=np.float32)
    for _ in range(n_ev):
        start_hour = np.clip(np.random.normal(start_mu, start_sigma), 0, 23.99)
        start_min = int(start_hour * 60)
        duration_min = max(10.0, np.random.rayleigh(duration_scale_min))
        amount_kwh = max(2.0, np.random.rayleigh(amount_scale_kwh))
        power_kw = amount_kwh / (duration_min / 60.0)
        retry = 0
        while power_kw > charger_power_limit_kw and retry < 10:
            duration_min = max(10.0, np.random.rayleigh(duration_scale_min))
            amount_kwh = max(2.0, np.random.rayleigh(amount_scale_kwh))
            power_kw = amount_kwh / (duration_min / 60.0)
            retry += 1
        power_kw = min(power_kw, charger_power_limit_kw)
        end_min = min(24 * 60, start_min + int(duration_min))
        if end_min > start_min:
            minute_load[start_min:end_min] += power_kw / 60.0
    hourly = minute_load.reshape(24, 60).sum(axis=1)
    return np.clip(hourly, 0.0, ST_CFG.vmax_kwh).astype(np.float32)


def build_3station_day_synthetic(bad_prediction: bool = False) -> Dict:
    tou = generate_tou_24()
    station_scales = [{"pv": 1.00, "demand": 1.00}, {"pv": 0.85, "demand": 1.10}, {"pv": 1.20, "demand": 0.90}]
    stations = []
    for scale in station_scales:
        pv_forecast = generate_pv_forecast(scale=scale["pv"])
        demand_forecast = generate_ev_demand_forecast() * scale["demand"]
        pv_noise = 0.45 if bad_prediction else 0.08
        demand_noise = 0.55 if bad_prediction else 0.10
        pv_actual = np.clip(pv_forecast * (1.0 + np.random.normal(0, pv_noise, size=24)), 0.0, ST_CFG.pv_capacity_kwh * 1.5).astype(np.float32)
        demand_actual = np.clip(demand_forecast * (1.0 + np.random.normal(0, demand_noise, size=24)), 0.0, ST_CFG.vmax_kwh).astype(np.float32)
        stations.append({"pv_forecast": pv_forecast.astype(np.float32), "demand_forecast": demand_forecast.astype(np.float32), "pv_actual": pv_actual, "demand_actual": demand_actual})
    init_soc = np.random.uniform(ST_CFG.soc_min + 0.05, ST_CFG.soc_max - 0.05, size=SYS_CFG.n_station).astype(np.float32)
    return {"tou": tou, "stations": stations, "init_soc": init_soc, "date": "synthetic_day"}


REAL_DF = None
REAL_VALID_DATES = None
REAL_VALID_DATES_KEY = None


def load_real_dataset(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required_cols = {"date", "station", "hour", "pv_forecast", "demand_forecast", "pv_actual", "demand_actual", "tou"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"실제 데이터 CSV에 누락된 컬럼이 있습니다: {missing}")
    df = df.copy()
    df["station"] = df["station"].astype(int)
    df["hour"] = df["hour"].astype(int)
    for col in ("pv_forecast", "demand_forecast", "pv_actual", "demand_actual", "tou", "demand_p90"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).clip(lower=0.0)
    if "demand_p90" in df.columns:
        df["demand_p90"] = np.maximum(df["demand_p90"].to_numpy(dtype=float), df["demand_forecast"].to_numpy(dtype=float))
    return df.sort_values(["date", "station", "hour"]).reset_index(drop=True)


def get_valid_real_dates(df: pd.DataFrame) -> List[str]:
    global REAL_VALID_DATES, REAL_VALID_DATES_KEY
    cache_key = (id(df), SYS_CFG.n_station, SYS_CFG.horizon)
    if REAL_VALID_DATES_KEY == cache_key and REAL_VALID_DATES is not None:
        return REAL_VALID_DATES

    valid_dates = []
    for d in df["date"].unique():
        day = df[df["date"] == d]
        ok = True
        for i in range(SYS_CFG.n_station):
            dfi = day[day["station"] == i]
            if len(dfi) != SYS_CFG.horizon or set(dfi["hour"].tolist()) != set(range(SYS_CFG.horizon)):
                ok = False
                break
        if ok:
            valid_dates.append(d)
    REAL_VALID_DATES = valid_dates
    REAL_VALID_DATES_KEY = cache_key
    return valid_dates


def build_3station_day_real(df: pd.DataFrame, date: Optional[str] = None) -> Dict:
    if date is None:
        valid_dates = get_valid_real_dates(df)
        if not valid_dates:
            raise ValueError("24시간 × 3개 충전소가 모두 존재하는 유효 날짜가 없습니다.")
        date = random.choice(valid_dates)
    day = df[df["date"] == date].copy()
    stations = []
    for i in range(SYS_CFG.n_station):
        dfi = day[day["station"] == i].sort_values("hour")
        if len(dfi) != SYS_CFG.horizon:
            raise ValueError(f"date={date}, station={i} 데이터가 {SYS_CFG.horizon}개가 아닙니다.")
        station = {
            "pv_forecast": dfi["pv_forecast"].to_numpy(dtype=np.float32),
            "demand_forecast": dfi["demand_forecast"].to_numpy(dtype=np.float32),
            "pv_actual": dfi["pv_actual"].to_numpy(dtype=np.float32),
            "demand_actual": dfi["demand_actual"].to_numpy(dtype=np.float32),
        }
        if "demand_p90" in dfi.columns:
            station["demand_p90"] = dfi["demand_p90"].to_numpy(dtype=np.float32)
        stations.append(station)
    tou = day[day["station"] == 0].sort_values("hour")["tou"].to_numpy(dtype=np.float32)
    init_soc = np.random.uniform(ST_CFG.soc_min + 0.05, ST_CFG.soc_max - 0.05, size=SYS_CFG.n_station).astype(np.float32)
    return {"tou": tou, "stations": stations, "init_soc": init_soc, "date": date}


def build_day(bad_prediction: bool = False, date: Optional[str] = None) -> Dict:
    global REAL_DF
    if EXP_CFG.data_mode == "synthetic":
        return build_3station_day_synthetic(bad_prediction=bad_prediction)
    if EXP_CFG.data_mode == "real":
        if REAL_DF is None:
            REAL_DF = load_real_dataset(EXP_CFG.real_data_path)
        return build_3station_day_real(REAL_DF, date=date)
    raise ValueError(f"지원하지 않는 data_mode입니다: {EXP_CFG.data_mode}")


def project_share(raw_share: np.ndarray, share_max: float) -> np.ndarray:
    share = np.asarray(raw_share, dtype=np.float32)
    share = share - np.mean(share)
    share = np.clip(share, -share_max, share_max)
    share = share - np.mean(share)
    return share.astype(np.float32)


def station_flow(soc: float, pv_t: float, demand_t: float, tou_t: float, share_t_i: float, action: np.ndarray, cfg: Optional["StationConfig"] = None) -> Dict[str, float]:
    # cfg lets the regional_virtual_hub scenario inject scaled station spec without
    # mutating the global ST_CFG (which would race under FastAPI). Defaults to ST_CFG.
    cfg = cfg if cfg is not None else ST_CFG
    a_ess = float(np.clip(action[0], -cfg.ess_max_ratio, cfg.ess_max_ratio))
    a_pv = float(np.clip(action[1], 0.0, 1.0))
    e_t = a_ess * cfg.ess_capacity_kwh
    soc_raw = soc + a_ess
    soc_violation = 0.0
    if soc_raw > cfg.soc_max:
        soc_violation = (soc_raw - cfg.soc_max) * cfg.ess_capacity_kwh
    elif soc_raw < cfg.soc_min:
        soc_violation = (cfg.soc_min - soc_raw) * cfg.ess_capacity_kwh
    next_soc = float(np.clip(soc_raw, cfg.soc_min, cfg.soc_max))
    received = max(0.0, share_t_i)
    exported = max(0.0, -share_t_i)
    internal_demand = max(0.0, demand_t - received) + exported
    e_ev = v_pv = g_ev = e_pv = g_ess = loss = 0.0
    if a_pv < 0.5:
        e_ev = min(max(0.0, -e_t), internal_demand)
        v_pv = min(pv_t, max(0.0, internal_demand - e_ev))
        g_ev = max(0.0, internal_demand - e_ev - v_pv)
        e_pv = min(max(0.0, e_t), max(0.0, pv_t - v_pv))
        g_ess = max(0.0, max(0.0, e_t) - e_pv)
        loss = max(0.0, pv_t - v_pv - e_pv) + max(0.0, max(0.0, -e_t) - e_ev)
    elif a_pv >= 0.5 and e_t >= 0.0:
        e_pv = min(pv_t, max(0.0, e_t))
        g_ess = max(0.0, max(0.0, e_t) - e_pv)
        v_pv = min(max(0.0, pv_t - e_pv), internal_demand)
        g_ev = max(0.0, internal_demand - v_pv)
        loss = max(0.0, pv_t - e_pv - v_pv)
    else:
        e_ev = min(max(0.0, -e_t), internal_demand)
        g_ev = max(0.0, internal_demand - e_ev)
        loss = pv_t + max(0.0, max(0.0, -e_t) - e_ev)
    grid_total = g_ev + g_ess
    self_supply = e_ev + e_pv + v_pv
    peak_violation = max(0.0, grid_total - cfg.peak_limit_kwh)
    grid_cost = grid_total * tou_t
    share_cost = abs(share_t_i) * SYS_CFG.share_transfer_cost * tou_t
    objective_reward = (-EXP_CFG.reward_grid_weight * grid_cost / 10000.0 + EXP_CFG.reward_self_weight * self_supply / 100.0 - EXP_CFG.reward_loss_weight * loss / 100.0 - share_cost / 10000.0)
    # PI-Lagrangian constraint normalization (Codex P0, single-station 교훈 이식):
    # 고정 /100 대신 물리 스케일로 정규화해야 두 constraint(peak/SoC)가 같은 크기로 학습됨.
    # peak_viol는 peak_limit, soc_viol는 ESS 1-step power로 정규화.
    _peak_norm = max(1e-6, cfg.peak_limit_kwh)
    _soc_norm = max(1e-6, cfg.ess_max_ratio * cfg.ess_capacity_kwh)
    constraints = np.array([peak_violation / _peak_norm, soc_violation / _soc_norm], dtype=np.float32)
    return {
        "next_soc": next_soc, "grid_total_kwh": float(grid_total), "grid_cost": float(grid_cost),
        "self_supply_kwh": float(self_supply), "loss_kwh": float(loss), "peak_violation": float(peak_violation),
        "soc_violation": float(soc_violation), "objective_reward": float(objective_reward),
        "constraints": constraints, "a_ess": float(a_ess), "a_pv": float(a_pv), "internal_demand": float(internal_demand),
    }


class PILagrangianController:
    def __init__(self, pi_cfg: PILagrangianParams):
        self.pi_cfg = pi_cfg
        self.lam = np.array(pi_cfg.lambda_init, dtype=np.float32)
        self.integral = np.zeros_like(self.lam, dtype=np.float32)
    def penalty(self, constraints: np.ndarray) -> float:
        return float(np.dot(self.lam, constraints))
    def update(self, constraints_batch: np.ndarray):
        c = np.asarray(constraints_batch, dtype=np.float32)
        avg_c = c if c.ndim == 1 else c.mean(axis=0)
        eps = np.array(self.pi_cfg.epsilon, dtype=np.float32)
        error = np.maximum(0.0, avg_c - eps)
        self.integral += error
        self.integral = np.clip(self.integral, -self.pi_cfg.i_max, self.pi_cfg.i_max)
        lam_max = np.array(self.pi_cfg.lambda_max, dtype=np.float32)
        self.lam = self.pi_cfg.lambda_decay * self.lam + self.pi_cfg.kp * error + self.pi_cfg.ki * self.integral
        self.lam = np.clip(self.lam, 0.0, lam_max)
    def get_lambda(self) -> np.ndarray:
        return self.lam.copy()


class PILagrangianCallback(BaseCallback):
    def __init__(self, pi_controller: PILagrangianController, update_interval: int = 128, verbose: int = 0):
        super().__init__(verbose)
        self.pi_controller = pi_controller
        self.update_interval = update_interval
        self.buffer = []
    def _on_step(self) -> bool:
        infos = self.locals.get("infos", [])
        for info in infos:
            if "constraints" in info:
                self.buffer.append(info["constraints"])
        if len(self.buffer) >= self.update_interval:
            batch = np.stack(self.buffer, axis=0)
            self.pi_controller.update(batch)
            self.buffer = []
        return True


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class MLP(nn.Module):
    def __init__(self, input_dim, output_dim, hidden=(256, 256)):
        super().__init__()
        layers = []
        last_dim = input_dim
        for h in hidden:
            layers.append(nn.Linear(last_dim, h))
            layers.append(nn.ReLU())
            last_dim = h
        layers.append(nn.Linear(last_dim, output_dim))
        self.net = nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x)


class SeqLSTMEncoder(nn.Module):
    """obs 꼬리의 과거 history(flat)를 시퀀스로 reshape해 LSTM으로 인코딩.

    single_station_env가 obs 끝에 [pv_hist(L), load_hist(L)] = seq_feat*L 를 붙인다.
    reshape(seq_feat, L).permute → (L, seq_feat) 시계열로 만들어 LSTM의 마지막 hidden을 반환.
    static(앞부분)과 concat해 기존 MLP backbone에 넣는다. (논문 LSTM 인코더 근사)
    """
    def __init__(self, seq_len, seq_feat, lstm_hidden):
        super().__init__()
        self.seq_len = seq_len
        self.seq_feat = seq_feat
        self.lstm_hidden = lstm_hidden
        self.lstm = nn.LSTM(seq_feat, lstm_hidden, batch_first=True)

    def split(self, obs):
        seq_dim = self.seq_len * self.seq_feat
        static = obs[:, :-seq_dim]
        seq_flat = obs[:, -seq_dim:]
        seq = seq_flat.reshape(seq_flat.shape[0], self.seq_feat, self.seq_len).permute(0, 2, 1)
        out, _ = self.lstm(seq)
        return torch.cat([static, out[:, -1, :]], dim=-1)

    @property
    def out_dim_delta(self):
        # static + lstm_hidden 으로 바뀌는 backbone 입력차원 보정용
        return self.lstm_hidden - self.seq_len * self.seq_feat


class FullPISACActor(nn.Module):
    def __init__(self, obs_dim, action_dim, action_low, action_high, hidden=(256, 256), log_std_min=-20, log_std_max=2, soc_index=1, use_soc_variance_scaling=True, beta=1.0, deadzone=0.2, lstm_seq_len=0, lstm_seq_feat=2, lstm_hidden=64):
        super().__init__()
        self.lstm_enc = None
        backbone_in = obs_dim
        if lstm_seq_len > 0:
            self.lstm_enc = SeqLSTMEncoder(lstm_seq_len, lstm_seq_feat, lstm_hidden)
            backbone_in = obs_dim + self.lstm_enc.out_dim_delta
        self.backbone = MLP(backbone_in, hidden[-1], hidden[:-1])
        self.mu_layer = nn.Linear(hidden[-1], action_dim)
        self.log_std_layer = nn.Linear(hidden[-1], action_dim)
        self.register_buffer("action_low", torch.tensor(action_low, dtype=torch.float32))
        self.register_buffer("action_high", torch.tensor(action_high, dtype=torch.float32))
        self.log_std_min = log_std_min
        self.log_std_max = log_std_max
        self.soc_index = soc_index
        self.use_soc_variance_scaling = use_soc_variance_scaling
        self.beta = beta
        self.deadzone = deadzone
    def _scale_action(self, tanh_action):
        return self.action_low + (tanh_action + 1.0) * 0.5 * (self.action_high - self.action_low)
    def forward(self, obs):
        feat = self.lstm_enc.split(obs) if self.lstm_enc is not None else obs
        h = self.backbone(feat)
        mu = self.mu_layer(h)
        log_std = self.log_std_layer(h)
        log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
        if self.use_soc_variance_scaling:
            soc = obs[:, self.soc_index:self.soc_index + 1]
            kappa = 1.0 + self.beta * torch.clamp(torch.abs(soc - 0.5) - self.deadzone, min=0.0)
            log_std = log_std + torch.log(kappa)
        return mu, log_std
    def sample(self, obs):
        mu, log_std = self.forward(obs)
        std = torch.exp(log_std)
        dist = Normal(mu, std)
        z = dist.rsample()
        tanh_action = torch.tanh(z)
        action = self._scale_action(tanh_action)
        log_prob = dist.log_prob(z) - torch.log(1.0 - tanh_action.pow(2) + 1e-6)
        log_prob = log_prob.sum(dim=-1, keepdim=True)
        return action, log_prob
    def deterministic(self, obs):
        mu, _ = self.forward(obs)
        tanh_action = torch.tanh(mu)
        return self._scale_action(tanh_action)


class FullPISACCritic(nn.Module):
    def __init__(self, obs_dim, action_dim, output_dim=1, hidden=(256, 256), lstm_seq_len=0, lstm_seq_feat=2, lstm_hidden=64):
        super().__init__()
        self.lstm_enc = None
        feat_dim = obs_dim
        if lstm_seq_len > 0:
            self.lstm_enc = SeqLSTMEncoder(lstm_seq_len, lstm_seq_feat, lstm_hidden)
            feat_dim = obs_dim + self.lstm_enc.out_dim_delta
        self.q = MLP(feat_dim + action_dim, output_dim, hidden)
    def forward(self, obs, action):
        feat = self.lstm_enc.split(obs) if self.lstm_enc is not None else obs
        return self.q(torch.cat([feat, action], dim=-1))


class FullPISAC:
    def __init__(self, env, obs_dim, action_dim, action_low, action_high, cost_dim=2, hidden=(256, 256), gamma=0.99, tau=0.005, actor_lr=2e-4, critic_lr=2e-4, cost_critic_lr=2e-4, alpha_lr=2e-4, batch_size=256, buffer_size=100_000, learning_starts=1000, target_entropy=None, pi_cfg: PILagrangianParams = PI_CFG, use_soc_variance_scaling=True, soc_index=1, verbose=1, lstm_seq_len=0, lstm_seq_feat=2, lstm_hidden=64):
        self.env = env
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.cost_dim = cost_dim
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        self.learning_starts = learning_starts
        self.verbose = verbose
        self.pi_controller = PILagrangianController(pi_cfg)
        _lk = dict(lstm_seq_len=lstm_seq_len, lstm_seq_feat=lstm_seq_feat, lstm_hidden=lstm_hidden)
        self.actor = FullPISACActor(obs_dim, action_dim, action_low, action_high, hidden, use_soc_variance_scaling=use_soc_variance_scaling, soc_index=soc_index, **_lk).to(DEVICE)
        self.q1 = FullPISACCritic(obs_dim, action_dim, 1, hidden, **_lk).to(DEVICE)
        self.q2 = FullPISACCritic(obs_dim, action_dim, 1, hidden, **_lk).to(DEVICE)
        self.q1_targ = FullPISACCritic(obs_dim, action_dim, 1, hidden, **_lk).to(DEVICE)
        self.q2_targ = FullPISACCritic(obs_dim, action_dim, 1, hidden, **_lk).to(DEVICE)
        self.cost_critic = FullPISACCritic(obs_dim, action_dim, cost_dim, hidden, **_lk).to(DEVICE)
        self.cost_critic_targ = FullPISACCritic(obs_dim, action_dim, cost_dim, hidden, **_lk).to(DEVICE)
        self.q1_targ.load_state_dict(self.q1.state_dict())
        self.q2_targ.load_state_dict(self.q2.state_dict())
        self.cost_critic_targ.load_state_dict(self.cost_critic.state_dict())
        self.log_alpha = torch.tensor(np.log(0.2), dtype=torch.float32, device=DEVICE, requires_grad=True)
    def predict(self, obs, deterministic=True):
        obs_arr = np.asarray(obs, dtype=np.float32).reshape(1, -1)
        obs_t = torch.tensor(obs_arr, dtype=torch.float32, device=DEVICE)
        with torch.no_grad():
            action = self.actor.deterministic(obs_t) if deterministic else self.actor.sample(obs_t)[0]
        return action.cpu().numpy()[0], None
    def load(self, path: str):
        payload = torch.load(path, map_location=DEVICE, weights_only=False)
        self.actor.load_state_dict(payload["actor"])
        self.q1.load_state_dict(payload["q1"])
        self.q2.load_state_dict(payload["q2"])
        self.q1_targ.load_state_dict(payload["q1_targ"])
        self.q2_targ.load_state_dict(payload["q2_targ"])
        self.cost_critic.load_state_dict(payload["cost_critic"])
        self.cost_critic_targ.load_state_dict(payload["cost_critic_targ"])
        with torch.no_grad():
            self.log_alpha.copy_(torch.tensor(payload["log_alpha"], dtype=torch.float32, device=DEVICE))
        self.pi_controller.lam = payload["lambda"]
        self.pi_controller.integral = payload["integral"]
        return self
    def save(self, path: str):
        raise NotImplementedError("Runtime module is for inference only.")


class UpperMILPPlanner:
    def plan(self, day_data: Dict) -> np.ndarray:
        n, T = SYS_CFG.n_station, SYS_CFG.horizon
        tou = day_data["tou"]
        pv_f = np.stack([day_data["stations"][i]["pv_forecast"] for i in range(n)], axis=0)
        dm_f = np.stack([day_data["stations"][i]["demand_forecast"] for i in range(n)], axis=0)
        prob = pulp.LpProblem("upper_milp_share_plan", pulp.LpMinimize)
        share = pulp.LpVariable.dicts("share", ((t, i) for t in range(T) for i in range(n)), lowBound=-SYS_CFG.share_abs_max_kwh, upBound=SYS_CFG.share_abs_max_kwh, cat="Continuous")
        grid = pulp.LpVariable.dicts("grid", ((t, i) for t in range(T) for i in range(n)), lowBound=0.0, cat="Continuous")
        share_abs = pulp.LpVariable.dicts("share_abs", ((t, i) for t in range(T) for i in range(n)), lowBound=0.0, cat="Continuous")
        prob += pulp.lpSum(tou[t] * grid[(t, i)] + SYS_CFG.share_transfer_cost * tou[t] * share_abs[(t, i)] for t in range(T) for i in range(n))
        for t in range(T):
            prob += pulp.lpSum(share[(t, i)] for i in range(n)) == 0.0
            for i in range(n):
                prob += share_abs[(t, i)] >= share[(t, i)]
                prob += share_abs[(t, i)] >= -share[(t, i)]
                prob += grid[(t, i)] + pv_f[i, t] + share[(t, i)] >= dm_f[i, t]
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[prob.status] != "Optimal":
            raise RuntimeError(f"MILP failed: {pulp.LpStatus[prob.status]}")
        plan = np.zeros((T, n), dtype=np.float32)
        for t in range(T):
            for i in range(n):
                plan[t, i] = float(share[(t, i)].value())
        return plan


class DefaultUpperPlanner:
    def plan(self, day_data: Dict) -> np.ndarray:
        return np.zeros((SYS_CFG.horizon, SYS_CFG.n_station), dtype=np.float32)
    def predict(self, obs, deterministic=True):
        return np.zeros(SYS_CFG.n_station, dtype=np.float32), None


class DefaultLowerAgent:
    def predict(self, obs, deterministic=True):
        return np.array([0.0, 0.0], dtype=np.float32), None
    def learn(self, total_timesteps: int = 0):
        return self
    def save(self, path: str):
        pass


class LowerStationEnv(gym.Env):
    metadata = {"render_modes": []}
    def __init__(self, station_idx: Optional[int] = None, upper_planner: Optional[UpperMILPPlanner] = None, pi_controller: Optional[PILagrangianController] = None, bad_prediction: bool = False):
        super().__init__()
        self.station_idx_fixed = station_idx
        self.upper_planner = upper_planner
        self.pi_controller = pi_controller
        self.bad_prediction = bad_prediction
        self.action_space = spaces.Box(low=np.array([-ST_CFG.ess_max_ratio, 0.0], dtype=np.float32), high=np.array([ST_CFG.ess_max_ratio, 1.0], dtype=np.float32), dtype=np.float32)
        self.observation_space = spaces.Box(low=np.array([0, 0, 0, 0, 0, -1], dtype=np.float32), high=np.array([1, 1, 2, 2, 2, 1], dtype=np.float32), dtype=np.float32)
        self.day_data = None
        self.share_plan = None
        self.station_idx = 0
        self.t = 0
        self.soc = 0.5
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.day_data = build_day(bad_prediction=self.bad_prediction)
        self.share_plan = np.zeros((SYS_CFG.horizon, SYS_CFG.n_station), dtype=np.float32) if self.upper_planner is None else self.upper_planner.plan(self.day_data)
        self.station_idx = random.randint(0, SYS_CFG.n_station - 1) if self.station_idx_fixed is None else self.station_idx_fixed
        self.t = 0
        self.soc = float(self.day_data["init_soc"][self.station_idx])
        return self._get_obs(), {}
    def _get_obs(self):
        s = self.day_data["stations"][self.station_idx]
        return np.nan_to_num(np.array([self.t / 23.0, self.soc, s["pv_actual"][self.t] / ST_CFG.pv_capacity_kwh, s["demand_actual"][self.t] / ST_CFG.vmax_kwh, self.day_data["tou"][self.t] / SYS_CFG.tou_high, self.share_plan[self.t, self.station_idx] / SYS_CFG.share_abs_max_kwh], dtype=np.float32))
    def step(self, action):
        s = self.day_data["stations"][self.station_idx]
        flow = station_flow(self.soc, float(s["pv_actual"][self.t]), float(s["demand_actual"][self.t]), float(self.day_data["tou"][self.t]), float(self.share_plan[self.t, self.station_idx]), action)
        objective_reward = flow["objective_reward"]
        constraints = flow["constraints"]
        reward = objective_reward if self.pi_controller is None else objective_reward - self.pi_controller.penalty(constraints)
        self.soc = flow["next_soc"]
        self.t += 1
        terminated = self.t >= SYS_CFG.horizon
        obs = np.zeros(self.observation_space.shape, dtype=np.float32) if terminated else self._get_obs()
        info = {"objective_reward": objective_reward, "constraints": constraints, "grid_cost": flow["grid_cost"], "grid_total_kwh": flow["grid_total_kwh"], "loss_kwh": flow["loss_kwh"], "peak_violation": flow["peak_violation"], "soc_violation": flow["soc_violation"], "lambda": self.pi_controller.get_lambda() if self.pi_controller else np.zeros(2)}
        return obs, float(reward), terminated, False, info


class UpperPlannerEnv(gym.Env):
    metadata = {"render_modes": []}
    def __init__(self, lower_agents: Optional[List[SAC]] = None, pi_controller: Optional[PILagrangianController] = None, bad_prediction: bool = False):
        super().__init__()
        self.lower_agents = lower_agents
        self.pi_controller = pi_controller
        self.bad_prediction = bad_prediction
        self.action_space = spaces.Box(low=np.array([-1.0] * SYS_CFG.n_station, dtype=np.float32), high=np.array([1.0] * SYS_CFG.n_station, dtype=np.float32), dtype=np.float32)
        self.observation_space = spaces.Box(low=np.array([0, 0, 0, 0, 0, 0, 0], dtype=np.float32), high=np.array([1, 5, 5, 2, 1, 1, 1], dtype=np.float32), dtype=np.float32)
        self.day_data = None
        self.soc = None
        self.t = 0
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.day_data = build_day(bad_prediction=self.bad_prediction)
        self.soc = self.day_data["init_soc"].copy()
        self.t = 0
        return self._get_obs(), {}
    def _get_obs(self):
        total_pv = sum(self.day_data["stations"][i]["pv_actual"][self.t] for i in range(SYS_CFG.n_station))
        total_dm = sum(self.day_data["stations"][i]["demand_actual"][self.t] for i in range(SYS_CFG.n_station))
        return np.nan_to_num(np.array([self.t / 23.0, total_pv / (ST_CFG.pv_capacity_kwh * SYS_CFG.n_station), total_dm / (ST_CFG.vmax_kwh * SYS_CFG.n_station), self.day_data["tou"][self.t] / SYS_CFG.tou_high, self.soc[0], self.soc[1], self.soc[2]], dtype=np.float32))
    def _lower_obs(self, station_idx: int, share_i: float):
        s = self.day_data["stations"][station_idx]
        return np.array([self.t / 23.0, self.soc[station_idx], s["pv_actual"][self.t] / ST_CFG.pv_capacity_kwh, s["demand_actual"][self.t] / ST_CFG.vmax_kwh, self.day_data["tou"][self.t] / SYS_CFG.tou_high, share_i / SYS_CFG.share_abs_max_kwh], dtype=np.float32)
    def _rule_lower_action(self, station_idx: int):
        soc = self.soc[station_idx]
        tou = self.day_data["tou"][self.t]
        if tou >= SYS_CFG.tou_high and soc > 0.25:
            return np.array([-0.05, 0.2], dtype=np.float32)
        if tou <= SYS_CFG.tou_low and soc < 0.75:
            return np.array([0.05, 0.7], dtype=np.float32)
        return np.array([0.0, 0.2], dtype=np.float32)
    def step(self, raw_action):
        share = project_share(np.asarray(raw_action) * SYS_CFG.share_abs_max_kwh, SYS_CFG.share_abs_max_kwh)
        total_objective_reward = total_grid_cost = total_grid_kwh = total_loss = total_peak_violation = total_soc_violation = 0.0
        for i in range(SYS_CFG.n_station):
            s = self.day_data["stations"][i]
            if self.lower_agents is None:
                lower_action = self._rule_lower_action(i)
            else:
                lower_obs = self._lower_obs(i, share[i])
                agent = self.lower_agents[i] if len(self.lower_agents) > 1 else self.lower_agents[0]
                lower_action, _ = agent.predict(lower_obs, deterministic=True)
            flow = station_flow(float(self.soc[i]), float(s["pv_actual"][self.t]), float(s["demand_actual"][self.t]), float(self.day_data["tou"][self.t]), float(share[i]), lower_action)
            self.soc[i] = flow["next_soc"]
            total_objective_reward += flow["objective_reward"]
            total_grid_cost += flow["grid_cost"]
            total_grid_kwh += flow["grid_total_kwh"]
            total_loss += flow["loss_kwh"]
            total_peak_violation += flow["peak_violation"]
            total_soc_violation += flow["soc_violation"]
        constraints = np.array([total_peak_violation / 100.0, total_soc_violation / 100.0], dtype=np.float32)
        reward = total_objective_reward if self.pi_controller is None else total_objective_reward - self.pi_controller.penalty(constraints)
        self.t += 1
        terminated = self.t >= SYS_CFG.horizon
        obs = np.zeros(self.observation_space.shape, dtype=np.float32) if terminated else self._get_obs()
        info = {"objective_reward": total_objective_reward, "constraints": constraints, "grid_cost": total_grid_cost, "grid_total_kwh": total_grid_kwh, "loss_kwh": total_loss, "peak_violation": total_peak_violation, "soc_violation": total_soc_violation, "share": share, "lambda": self.pi_controller.get_lambda() if self.pi_controller else np.zeros(2)}
        return obs, float(reward), terminated, False, info


def make_full_pi_sac_model(env, name: str) -> FullPISAC:
    obs_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    action_low = env.action_space.low
    action_high = env.action_space.high
    return FullPISAC(env=env, obs_dim=obs_dim, action_dim=action_dim, action_low=action_low, action_high=action_high, cost_dim=2, hidden=(256, 256), gamma=SAC_CFG.gamma, tau=0.005, actor_lr=2e-4, critic_lr=2e-4, cost_critic_lr=2e-4, alpha_lr=2e-4, batch_size=SAC_CFG.batch_size, buffer_size=SAC_CFG.buffer_size, learning_starts=1000, pi_cfg=PI_CFG, use_soc_variance_scaling=True, verbose=SAC_CFG.verbose)
