import streamlit as st
from data_loader import load_and_prepare_datasets
from models import SimulationParameters
from simulation import OffNetSimulator
import visualization

def main():
    st.title("Off-Net Feasibility Calculator")

    datasets = load_and_prepare_datasets()
    dataset_names = ["2015 Q1", "2015 Q2", "2015 Q3"]

    st.sidebar.header("Compute Mode")
    compute_mode = st.sidebar.radio("Select Compute Mode", options=["AWS", "Canvas"], index=1)

    st.sidebar.header("Input Parameters")
    dataset_choice = st.sidebar.selectbox("Select Dataset", options=dataset_names)
    selected_dataset = datasets[dataset_names.index(dataset_choice)]

    time_horizon = st.sidebar.number_input("Time Horizon (days)", value=90, min_value=1)
    avg_request_size_kb = st.sidebar.number_input("Average Request Size (KB)", value=500.0, min_value=1.0)
    avg_num_users = st.sidebar.number_input("Average Number of Users", value=int(selected_dataset["num_users"].mean()), min_value=1)

    if compute_mode == "AWS":
        transfer_link_cost_per_gbps = st.sidebar.number_input("Cost per Gbps Transfer Link ($/Gbps per month)", value=1000.0)
        sla_percentage = st.sidebar.slider("SLA Percentage for Requests (%)", min_value=50, max_value=100, value=95)
    else:
        on_net_cost_gb = st.sidebar.number_input("On-Net Bandwidth Cost ($/GB)", value=0.10)

    hw_cost_on_net = st.sidebar.number_input("On-Net Hardware Cost per Month ($)", value=2000.0)
    hw_cost_off_net = st.sidebar.number_input("Off-Net Hardware Cost per Month ($)", value=5000.0)
    off_net_cost_gb = st.sidebar.number_input("Off-Net Bandwidth Cost ($/GB)", value=0.05)

    upfront_cost_on_net = st.sidebar.number_input("Upfront Hardware Cost On-Net ($)", value=10000.0)
    upfront_cost_off_net = st.sidebar.number_input("Upfront Hardware Cost Off-Net ($)", value=20000.0)
    hardware_life_cycle = st.sidebar.number_input("Hardware Life Cycle (Years)", value=5, min_value=1)

    if st.button("Run Simulation"):
        params = SimulationParameters(
            time_horizon_days=time_horizon,
            avg_request_size_kb=avg_request_size_kb,
            avg_num_users=avg_num_users,
            off_net_bandwidth_cost_per_gb=off_net_cost_gb,
            on_net_bandwidth_cost_per_gb=on_net_cost_gb if compute_mode == "Canvas" else 0.0,
            hardware_cost_off_net_per_month=hw_cost_off_net,
            hardware_cost_on_net_per_month=hw_cost_on_net,
            upfront_hardware_cost_off_net=upfront_cost_off_net,
            upfront_hardware_cost_on_net=upfront_cost_on_net,
            hardware_life_cycle_years=hardware_life_cycle,
            transfer_link_cost_per_gbps=transfer_link_cost_per_gbps if compute_mode == "AWS" else 0.0,
            sla_percentage=sla_percentage if compute_mode == "AWS" else 0.0,
        )

        simulator = OffNetSimulator(params, selected_dataset)
        results = simulator.run_simulation(compute_aws=(compute_mode == "AWS"))

        visualization.display_results(results, compute_mode)

if __name__ == "__main__":
    main()

