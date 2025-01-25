import streamlit as st
from data_loader import load_and_prepare_datasets
from models import SimulationParameters
from simulation import OffNetSimulator
import visualization

def main():
    st.title("Off-Net Costs Simulator for Hosting a Canvas Environment")
    st.caption("Author: S. Redeker | Date: January, 2025 | Affiliation: University of Twente | License: MIT")

    with st.expander("Instructions", expanded=True):
        st.write(
            """
            This tool helps the user determine the cost-effectiveness of using an off-net or on-net solution for hosting a Canvas application based on parameters such as average number of users, bandwidth costs, hardware costs, and hardware lifecycles.

            **How to use:**
            - Open the configuration parameter menu in the top left corner.
            - Select the perspective from whom you are simulating the incurred costs.
            - Input your simulation parameters or pick a predefined set of parameters.
            - Click the 'Run Simulation' button below.
            """
        )

    datasets = load_and_prepare_datasets()
    dataset_names = ["2012 Q3 - Harvard/MIT", "2012 Q4 - Harvard/MIT", "2013 Q1 - Harvard/MIT", "2013 Q2 - Harvard/MIT", "2013 Q3 - Harvard/MIT", "2015 Q1 - Canvas Network", "2015 Q2 - Canvas Network", "2015 Q3 - Canvas Network"]

    st.sidebar.title("Configuration Parameters")

    st.sidebar.header("Perspective")
    compute_mode = st.sidebar.radio("Select for whom you are interested in computing the costs.", options=["AWS", "Canvas"], index=1)

    st.sidebar.caption("The `AWS` case solves for the costs occurred by AWS and by the students' ISPs. The `Canvas` case solves an arguably more relevant problem for the costs occurred by Canvas and the University of Twente. We ignore the ISPs costs here.")

    st.sidebar.header("Short-cuts")

    if compute_mode == "Canvas":
        use_aws_bandwidth_pricing = st.sidebar.checkbox("Use AWS Bandwidth Pricing", value=False)
        st.sidebar.caption("Use the tiered pricing scheme for bandwidth from the AWS cost calculator.")
    else:
        use_aws_bandwidth_pricing = False
    use_tweakers_estimates = st.sidebar.checkbox("Use Hardware Estimates Based on Tweakers.net", value=False)
    st.sidebar.caption("Estimate hardware usage based on known hardware usage from a similar platform.")

    st.sidebar.header("Users")

    dataset_choice = st.sidebar.selectbox("Select User Behaviour Dataset", options=dataset_names)
    selected_dataset = datasets[dataset_names.index(dataset_choice)]
    avg_page_views_per_user_per_day = selected_dataset["num_requests"].sum() / selected_dataset["num_users"].sum()
    st.sidebar.caption("On average " + str(int(avg_page_views_per_user_per_day)) + " page views per user per day.")

    avg_num_users = st.sidebar.number_input("Average Number of Daily Active Users", value=10000, min_value=1)
    avg_request_size_kb = st.sidebar.number_input("Average Request/Page Size (KB)", value=500.0, min_value=1.0)

    st.sidebar.header("Simulation time")
    time_horizon = st.sidebar.number_input("Time Horizon (days)", value=3650, min_value=1)
    st.sidebar.caption("10 years by default. If you want to see the user patterns in detail, pick a smaller number, e.g. 30 days.")

    st.sidebar.header("Hardware")
    upfront_cost_on_net = upfront_cost_off_net = hw_cost_on_net = hw_cost_off_net = 0
    if use_tweakers_estimates:
        if compute_mode == "Canvas":
            upfront_cost_off_net = avg_page_views_per_user_per_day * avg_num_users * 0.105829
            hw_cost_off_net = avg_page_views_per_user_per_day * avg_num_users * 0.001613
            hw_cost_on_net = avg_page_views_per_user_per_day * avg_num_users * 0.016467
        else:  # AWS Case
            upfront_cost_on_net = avg_page_views_per_user_per_day * avg_num_users * 0.105829
            upfront_cost_off_net = avg_page_views_per_user_per_day * avg_num_users * 0.105829
            hw_cost_on_net = avg_page_views_per_user_per_day * avg_num_users * 0.001613
            hw_cost_off_net = avg_page_views_per_user_per_day * avg_num_users * 0.001613
    else:
        if compute_mode == "Canvas":
            upfront_cost_on_net = st.sidebar.number_input("Upfront Hardware Cost On-Net (\u20ac)", value=0.0)
            upfront_cost_off_net = st.sidebar.number_input("Upfront Hardware Cost Off-Net (\u20ac)", value=28000.0)
            hw_cost_on_net = st.sidebar.number_input("On-Net Hardware Cost per Month (\u20ac/month)", value=4100.0)
            hw_cost_off_net = st.sidebar.number_input("Off-Net Hardware Cost per Month (\u20ac/month)", value=400.0)
        else:
            upfront_cost_on_net = st.sidebar.number_input("Upfront Hardware Cost On-Net (\u20ac)", value=28000.0)
            upfront_cost_off_net = st.sidebar.number_input("Upfront Hardware Cost Off-Net (\u20ac)", value=28000.0)
            hw_cost_on_net = st.sidebar.number_input("On-Net Hardware Cost per Month (\u20ac/month)", value=400.0)
            hw_cost_off_net = st.sidebar.number_input("Off-Net Hardware Cost per Month (\u20ac/month)", value=400.0)
    


    hardware_life_cycle = st.sidebar.number_input("Hardware Life Cycle (Years)", value=3, min_value=1)


    st.sidebar.header("Bandwidth & Connectivity")
    if compute_mode == "AWS":
        transfer_link_cost_per_gbps = st.sidebar.number_input("Transfer Link Cost (\u20ac/Gbps per month)", value=1000.0)
        sla_percentage = st.sidebar.slider("SLA Percentage (%)", min_value=50, max_value=200, value=100)
        on_net_bandwidth_cost = 0.0  # Not relevant for AWS perspective
    else:
        if not use_aws_bandwidth_pricing:
            on_net_bandwidth_cost = st.sidebar.number_input("On-Net Bandwidth Cost (\u20ac/GB)", value=0.10)
        else:
            on_net_bandwidth_cost = 0.0  # Tiered pricing will be calculated dynamically

    off_net_cost_gb = st.sidebar.number_input("Off-Net Bandwidth Cost (\u20ac/GB)", value=0.0)
    st.sidebar.caption("If, for some reason, there is the need to connect a price to off-net bandwidth usage, that can be added here. Usually, this will be 0.")
    
    st.sidebar.header("Remaining On-Net")
    off_net_traffic_percentage = st.sidebar.slider("Percentage of On-Net Capacity Still Needed (%)", min_value=0, max_value=100, value=0)
    st.sidebar.caption("If a percentage of the existing on-net architecture still need to exist, that can be filled in here.")

    if st.button("Run Simulation"):
        params = SimulationParameters(
            time_horizon_days=time_horizon,
            avg_request_size_kb=avg_request_size_kb,
            avg_num_users=avg_num_users,
            off_net_bandwidth_cost_per_gb=off_net_cost_gb,
            on_net_bandwidth_cost_per_gb=on_net_bandwidth_cost,
            hardware_cost_off_net_per_month=hw_cost_off_net,
            hardware_cost_on_net_per_month=hw_cost_on_net,
            upfront_hardware_cost_off_net=upfront_cost_off_net,
            upfront_hardware_cost_on_net=upfront_cost_on_net,
            hardware_life_cycle_years=hardware_life_cycle,
            off_net_traffic_percentage=off_net_traffic_percentage,
            transfer_link_cost_per_gbps=transfer_link_cost_per_gbps if compute_mode == "AWS" else 0.0,
            sla_percentage=sla_percentage if compute_mode == "AWS" else 0.0,
            use_tweakers_estimates=use_tweakers_estimates,
            use_aws_bandwidth_pricing=use_aws_bandwidth_pricing,
        )

        simulator = OffNetSimulator(params, selected_dataset)
        results = simulator.run_simulation(compute_aws=(compute_mode == "AWS"))

        visualization.display_results(results, compute_mode)

if __name__ == "__main__":
    main()
