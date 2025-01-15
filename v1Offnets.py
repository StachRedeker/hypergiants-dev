import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, field

def load_and_prepare_datasets():
    dataset_files = [
        "daily_requests_2015Q1.csv",
        "daily_requests_2015Q2.csv",
        "daily_requests_2015Q3.csv",
    ]
    datasets = [pd.read_csv(file, delimiter=",", encoding="utf-8") for file in dataset_files]
    return datasets

@dataclass
class SimulationParameters:
    time_horizon_days: int
    avg_request_size_kb: float
    avg_num_users: int
    off_net_bandwidth_cost_per_gb: float
    on_net_bandwidth_cost_per_gb: float
    hardware_cost_off_net_per_month: float
    hardware_cost_on_net_per_month: float
    transfer_link_cost_per_gbps: float = 0.0
    sla_percentage: float = 0.0

@dataclass
class SimulationResults:
    timeline: pd.DataFrame = field(default_factory=pd.DataFrame)
    final_recommendation: str = ""
    aws_transfer_link_cost: float = 0.0
    required_bandwidth_gbps: float = 0.0

class OffNetSimulator:
    def __init__(self, params: SimulationParameters, user_data: pd.DataFrame):
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
        total_data_volume_gb = total_requests * (self.params.avg_request_size_kb / 1_048_576)  # Convert KB to GB
        requests_per_second = total_requests / (24 * 60 * 60)
        data_volume_per_second_gbps = requests_per_second * (self.params.avg_request_size_kb / 1_048_576 / 1024)

        required_bandwidth_gbps = data_volume_per_second_gbps * (self.params.sla_percentage / 100.0)
        transfer_link_cost_daily = (required_bandwidth_gbps * self.params.transfer_link_cost_per_gbps) / 30

        return required_bandwidth_gbps, transfer_link_cost_daily

    def run_simulation(self, compute_aws: bool = False) -> SimulationResults:
        # Unpack parameters
        T_days = self.params.time_horizon_days
        avg_request_size_gb = self.params.avg_request_size_kb / 1_048_576  # Convert KB to GB

        on_net_costs = []
        off_net_costs = []
        sent_requests = []
        sent_data_gb = []
        active_users = []

        for day in range(T_days):
            day_index = day % len(self.user_data)  # Repeat dataset if needed
            daily_users = self.user_data.loc[day_index, "num_users"]
            daily_requests = self.user_data.loc[day_index, "num_requests"]

            daily_data_volume = daily_requests * avg_request_size_gb

            if compute_aws:
                # Compute required bandwidth and daily transfer link cost
                required_bandwidth_gbps, daily_transfer_link_cost = self.compute_aws_bandwidth()

                # Compute on-net costs based on transfer link and hardware only
                on_net_total_cost = self.params.hardware_cost_on_net_per_month / 30 + daily_transfer_link_cost

                # Compute off-net costs normally based on bandwidth costs
                off_net_bandwidth_cost = daily_data_volume * self.params.off_net_bandwidth_cost_per_gb
                off_net_total_cost = off_net_bandwidth_cost + (self.params.hardware_cost_off_net_per_month / 30)
            else:
                # Compute costs normally for Canvas
                on_net_bandwidth_cost = daily_data_volume * self.params.on_net_bandwidth_cost_per_gb
                on_net_total_cost = on_net_bandwidth_cost + (self.params.hardware_cost_on_net_per_month / 30)
                off_net_bandwidth_cost = daily_data_volume * self.params.off_net_bandwidth_cost_per_gb
                off_net_total_cost = off_net_bandwidth_cost + (self.params.hardware_cost_off_net_per_month / 30)

            # Append metrics
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
            "Active Users": active_users
        })

        # Add rounding
        df = df.round(0).astype(int)

        # Final recommendation
        total_on_net = df["On-Net Cost"].iloc[-1]
        total_off_net = df["Off-Net Cost"].iloc[-1]
        final_recommendation = ""

        required_bandwidth_gbps, _ = 0.0, 0.0
        if compute_aws:
            required_bandwidth_gbps, transfer_link_cost = self.compute_aws_bandwidth()
            final_recommendation = (
                f"Required bandwidth: {required_bandwidth_gbps:.2f} Gbps, Transfer link cost: ${(transfer_link_cost * 30):.2f} per month."
            )
        else:
            if total_off_net < total_on_net:
                final_recommendation = "Off-net solution is more cost-effective over the time horizon."
            else:
                final_recommendation = "On-net solution remains more cost-effective over the time horizon."

        return SimulationResults(
            timeline=df,
            final_recommendation=final_recommendation,
            aws_transfer_link_cost=transfer_link_cost * 30 if compute_aws else 0.0,
            required_bandwidth_gbps=required_bandwidth_gbps,
        )

# Streamlit UI
def main():
    st.title("Off-Net Feasibility Calculator")

    # Load datasets
    datasets = load_and_prepare_datasets()
    dataset_names = ["2015 Q1", "2015 Q2", "2015 Q3"]

    # Mode Selection
    st.sidebar.header("Compute Mode")
    compute_mode = st.sidebar.radio("Select Compute Mode", options=["AWS", "Canvas"], index=1)

    # Sidebar inputs
    st.sidebar.header("Input Parameters")
    dataset_choice = st.sidebar.selectbox("Select Dataset", options=dataset_names)
    selected_dataset = datasets[dataset_names.index(dataset_choice)]

    time_horizon = st.sidebar.number_input("Time Horizon (days)", value=90, min_value=1)
    avg_request_size_kb = st.sidebar.number_input("Average Request Size (KB)", value=500.0, min_value=1.0)
    avg_num_users = st.sidebar.number_input("Average Number of Users", value=int(selected_dataset["num_users"].mean()), min_value=1)

    if compute_mode == "AWS":
        transfer_link_cost_per_gbps = st.sidebar.number_input("Cost per Gbps Transfer Link ($/Gbps per month)", value=1000.0)
        sla_percentage = st.sidebar.slider("SLA Percentage for Requests (%)", min_value=50, max_value=100, value=95)
        hw_cost_on_net = st.sidebar.number_input("On-Net Hardware Cost per Month ($)", value=2000.0)
        hw_cost_off_net = st.sidebar.number_input("Off-Net Hardware Cost per Month ($)", value=5000.0)
        off_net_cost_gb = st.sidebar.number_input("Off-Net Bandwidth Cost ($/GB)", value=0.05)
    else:
        on_net_cost_gb = st.sidebar.number_input("On-Net Bandwidth Cost ($/GB)", value=0.10)
        off_net_cost_gb = st.sidebar.number_input("Off-Net Bandwidth Cost ($/GB)", value=0.05)
        hw_cost_on_net = st.sidebar.number_input("On-Net Hardware Cost per Month ($)", value=2000.0)
        hw_cost_off_net = st.sidebar.number_input("Off-Net Hardware Cost per Month ($)", value=5000.0)

    if st.button("Run Simulation"):
        params = SimulationParameters(
            time_horizon_days=time_horizon,
            avg_request_size_kb=avg_request_size_kb,
            avg_num_users=avg_num_users,
            off_net_bandwidth_cost_per_gb=off_net_cost_gb,
            on_net_bandwidth_cost_per_gb=on_net_cost_gb if compute_mode == "Canvas" else 0.0,
            hardware_cost_off_net_per_month=hw_cost_off_net,
            hardware_cost_on_net_per_month=hw_cost_on_net,
            transfer_link_cost_per_gbps=transfer_link_cost_per_gbps if compute_mode == "AWS" else 0.0,
            sla_percentage=sla_percentage if compute_mode == "AWS" else 0.0,
        )

        simulator = OffNetSimulator(params, selected_dataset)
        results = simulator.run_simulation(compute_aws=(compute_mode == "AWS"))

        st.subheader("Results")
        st.write(results.final_recommendation)

        # Interactive Cost Plot
        st.line_chart(results.timeline.set_index("Day")[
            ["On-Net Cost", "Off-Net Cost"]
        ])

        # Side-by-side Plots for AWS Specific Metrics
        if compute_mode == "AWS":
            st.subheader("AWS Specific Metrics")
            col1, col2 = st.columns(2)
            with col1:
                st.write("### Required Bandwidth (Gbps)")
                st.bar_chart([results.required_bandwidth_gbps], use_container_width=True)
            with col2:
                st.write("### Transfer Link Cost ($ per Month)")
                st.bar_chart([results.aws_transfer_link_cost], use_container_width=True)

        # Side-by-side Plots for Users, Requests, and Data Volume
        st.subheader("Metrics Visualization")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("### Active Users")
            st.line_chart(results.timeline.set_index("Day")["Active Users"], use_container_width=True)

        with col2:
            st.write("### Sent Requests")
            st.line_chart(results.timeline.set_index("Day")["Sent Requests"], use_container_width=True)

        with col3:
            st.write("### Sent Data Volume (GB)")
            st.line_chart(results.timeline.set_index("Day")["Sent Data Volume (GB)"], use_container_width=True)

        st.subheader("Data Table")
        st.dataframe(results.timeline)

if __name__ == "__main__":
    main()

