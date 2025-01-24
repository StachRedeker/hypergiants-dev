import pandas as pd
import numpy as np
from models import SimulationResults

class OffNetSimulator:
    def __init__(self, params, user_data):
        self.params = params
        self.user_data = user_data
        self.adjust_dataset()

    def adjust_dataset(self):
        current_avg_users = self.user_data["num_users"].mean()
        adjustment_factor = self.params.avg_num_users / current_avg_users
        self.user_data["num_users"] *= adjustment_factor
        self.user_data["num_requests"] *= adjustment_factor

    def compute_aws_bandwidth(self):
        total_requests = self.user_data["num_requests"].sum()
        requests_per_second = total_requests / (24 * 60 * 60)
        data_volume_per_second_gbps = requests_per_second * (self.params.avg_request_size_kb / 1_048_576 / 1024)
        required_bandwidth_gbps = data_volume_per_second_gbps * (self.params.sla_percentage / 100.0)
        transfer_link_cost_daily = (required_bandwidth_gbps * self.params.transfer_link_cost_per_gbps) / 30
        return required_bandwidth_gbps, transfer_link_cost_daily

    def calculate_tiered_aws_cost(self, monthly_data_tb):
        cost = 0.0
        if monthly_data_tb > 150:
            cost += (monthly_data_tb - 150) * 0.05
            monthly_data_tb = 150
        if monthly_data_tb > 50:
            cost += (monthly_data_tb - 50) * 0.07
            monthly_data_tb = 50
        if monthly_data_tb > 10:
            cost += (monthly_data_tb - 10) * 0.085
            monthly_data_tb = 10
        cost += monthly_data_tb * 0.09
        return cost

    def run_simulation(self, compute_aws=False) -> SimulationResults:
        T_days = self.params.time_horizon_days
        avg_request_size_gb = self.params.avg_request_size_kb / 1_048_576  # Convert KB to GB
        hardware_life_cycle_days = self.params.hardware_life_cycle_years * 365

        on_net_costs = []
        off_net_costs = []
        sent_requests = []
        sent_data_gb = []
        active_users = []

        required_bandwidth_gbps = 0.0
        transfer_link_cost = 0.0

        for day in range(T_days):
            day_index = day % len(self.user_data)  # Cycle through dataset
            daily_users = self.user_data.loc[day_index, "num_users"]
            daily_requests = self.user_data.loc[day_index, "num_requests"]
            daily_data_volume = daily_requests * avg_request_size_gb

            if compute_aws:
                required_bandwidth_gbps, daily_transfer_link_cost = self.compute_aws_bandwidth()
                on_net_total_cost = self.params.hardware_cost_on_net_per_month / 30 + daily_transfer_link_cost
                off_net_bandwidth_cost = daily_data_volume * self.params.off_net_bandwidth_cost_per_gb
                off_net_total_cost = off_net_bandwidth_cost + (self.params.hardware_cost_off_net_per_month / 30)
            else:
                if self.params.use_aws_bandwidth_pricing:
                    total_monthly_data_tb = daily_data_volume * 30 / 1024  # Convert GB to TB
                    on_net_bandwidth_cost = self.calculate_tiered_aws_cost(total_monthly_data_tb) / (30 * 1024) * daily_data_volume
                else:
                    on_net_bandwidth_cost = daily_data_volume * self.params.on_net_bandwidth_cost_per_gb

                on_net_total_cost = on_net_bandwidth_cost + self.params.hardware_cost_on_net_per_month / 30
                off_net_bandwidth_cost = daily_data_volume * self.params.off_net_bandwidth_cost_per_gb
                off_net_total_cost = off_net_bandwidth_cost + self.params.hardware_cost_off_net_per_month / 30

            # Add lifecycle hardware costs
            if (day % hardware_life_cycle_days) == 0:
                on_net_total_cost += self.params.upfront_hardware_cost_on_net
                off_net_total_cost += self.params.upfront_hardware_cost_off_net

            # Adjust transfer link costs for AWS perspective
            if compute_aws:
                on_net_total_cost += daily_transfer_link_cost

            # Adjust off-net costs based on traffic percentage
            off_net_total_cost += (self.params.off_net_traffic_percentage / 100.0) * on_net_total_cost

            # Append daily metrics
            on_net_costs.append(on_net_total_cost)
            off_net_costs.append(off_net_total_cost)
            sent_requests.append(daily_requests)
            sent_data_gb.append(daily_data_volume)
            active_users.append(daily_users)

        df = pd.DataFrame({
            "Day": range(1, T_days + 1),
            "On-Net Cost": np.cumsum(on_net_costs),
            "Off-Net Cost": np.cumsum(off_net_costs),
            "Sent Requests": sent_requests,
            "Sent Data Volume (GB)": sent_data_gb,
            "Active Users": active_users,
        })

        total_on_net = df["On-Net Cost"].iloc[-1]
        total_off_net = df["Off-Net Cost"].iloc[-1]

        if compute_aws:
            transfer_link_cost = required_bandwidth_gbps * self.params.transfer_link_cost_per_gbps
            recommendation = (
                "At the end of the simulated time frame, the off-net solution is more cost-effective."
                if total_off_net < total_on_net else
                "At the end of the simulated time frame, the on-net solution is more cost-effective."
            )
        else:
            recommendation = (
                "At the end of the simulated time frame, the off-net solution is more cost-effective."
                if total_off_net < total_on_net else
                "At the end of the simulated time frame, the on-net solution is more cost-effective."
            )

        return SimulationResults(
            timeline=df,
            final_recommendation=recommendation,
            aws_transfer_link_cost=transfer_link_cost,
            required_bandwidth_gbps=required_bandwidth_gbps,
        )
