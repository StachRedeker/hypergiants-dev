from dataclasses import dataclass, field
import pandas as pd

@dataclass
class SimulationParameters:
    time_horizon_days: int
    avg_request_size_kb: float
    avg_num_users: int
    off_net_bandwidth_cost_per_gb: float
    on_net_bandwidth_cost_per_gb: float = 0.0
    hardware_cost_off_net_per_month: float = 0.0
    hardware_cost_on_net_per_month: float = 0.0
    upfront_hardware_cost_off_net: float = 0.0  # New
    upfront_hardware_cost_on_net: float = 0.0   # New
    hardware_life_cycle_years: int = 5          # New
    transfer_link_cost_per_gbps: float = 0.0
    sla_percentage: float = 0.0
    off_net_traffic_percentage: float = 100.0
    use_aws_bandwidth_pricing: bool = False  # Switch for AWS pricing
    use_tweakers_estimates: bool = False  # Switch for Tweakers estimates

@dataclass
class SimulationResults:
    timeline: pd.DataFrame = field(default_factory=pd.DataFrame)
    final_recommendation: str = ""
    aws_transfer_link_cost: float = 0.0
    required_bandwidth_gbps: float = 0.0
