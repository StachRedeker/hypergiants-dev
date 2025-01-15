import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass, field

@dataclass
class SimulationParameters:
    time_horizon_months: int
    base_user_count: int
    monthly_user_growth_rate: float  # e.g., 0.05 for 5% growth per month
    on_net_bandwidth_cost_per_gb: float
    off_net_bandwidth_cost_per_gb: float
    hardware_cost_off_net_per_month: float
    hardware_cost_on_net_per_month: float
    avg_usage_per_user_gb_per_month: float
    performance_requirement_improvement: float  # e.g., fraction of traffic that benefits

@dataclass
class SimulationResults:
    timeline: pd.DataFrame = field(default_factory=pd.DataFrame)
    break_even_month: int = None
    final_recommendation: str = ""

class OffNetSimulator:
    def __init__(self, params: SimulationParameters):
        self.params = params

    def run_simulation(self) -> SimulationResults:
        # Unpack parameters
        T = self.params.time_horizon_months
        user_count = self.params.base_user_count
        growth_rate = self.params.monthly_user_growth_rate

        on_net_costs = []
        off_net_costs = []

        for month in range(T):
            # Compute current user count
            current_users = user_count * ((1 + growth_rate) ** month)
            
            # Compute total usage in GB per month
            total_usage = current_users * self.params.avg_usage_per_user_gb_per_month
            
            # Compute on-net costs
            on_net_bandwidth_cost = total_usage * self.params.on_net_bandwidth_cost_per_gb
            on_net_total_cost = on_net_bandwidth_cost + self.params.hardware_cost_on_net_per_month
            
            # Compute off-net costs
            off_net_bandwidth_cost = total_usage * self.params.off_net_bandwidth_cost_per_gb
            off_net_total_cost = off_net_bandwidth_cost + self.params.hardware_cost_off_net_per_month
            
            on_net_costs.append(on_net_total_cost)
            off_net_costs.append(off_net_total_cost)

        df = pd.DataFrame({
            'Month': range(1, T+1),
            'On-Net Cost': on_net_costs,
            'Off-Net Cost': off_net_costs
        })
        
        # Determine break-even month if any
        diff = df['On-Net Cost'] - df['Off-Net Cost']
        if (diff < 0).any():
            break_even = df.loc[diff < 0, 'Month'].iloc[0]
            final_recommendation = f"Off-net solution becomes cheaper starting month {break_even}"
        else:
            break_even = None
            final_recommendation = "Off-net solution never becomes cheaper within the given time horizon."
        
        return SimulationResults(timeline=df, break_even_month=break_even, final_recommendation=final_recommendation)

# Streamlit UI
def main():
    st.title("Off-Net Server Deployment Viability Calculator")

    st.sidebar.header("Input Parameters")
    time_horizon = st.sidebar.number_input("Time Horizon (months)", value=24, min_value=1)
    base_user_count = st.sidebar.number_input("Initial User Count", value=10000, min_value=1)
    monthly_growth = st.sidebar.slider("Monthly User Growth Rate (%)", min_value=0.0, max_value=100.0, value=5.0)
    on_net_cost_gb = st.sidebar.number_input("On-Net Bandwidth Cost ($/GB)", value=0.10)
    off_net_cost_gb = st.sidebar.number_input("Off-Net Bandwidth Cost ($/GB)", value=0.05)
    hw_cost_on_net = st.sidebar.number_input("On-Net Hardware Cost per Month ($)", value=2000.0)
    hw_cost_off_net = st.sidebar.number_input("Off-Net Hardware Cost per Month ($)", value=5000.0)
    avg_usage = st.sidebar.number_input("Avg Usage per User per Month (GB)", value=2.0)

    # Additional fields, e.g., performance or region specifics could be added
    performance_req = st.sidebar.slider("Performance Improvement Factor", min_value=0.0, max_value=1.0, value=0.5)

    if st.button("Run Simulation"):
        params = SimulationParameters(
            time_horizon_months=time_horizon,
            base_user_count=base_user_count,
            monthly_user_growth_rate=monthly_growth / 100.0,
            on_net_bandwidth_cost_per_gb=on_net_cost_gb,
            off_net_bandwidth_cost_per_gb=off_net_cost_gb,
            hardware_cost_off_net_per_month=hw_cost_off_net,
            hardware_cost_on_net_per_month=hw_cost_on_net,
            avg_usage_per_user_gb_per_month=avg_usage,
            performance_requirement_improvement=performance_req
        )

        simulator = OffNetSimulator(params)
        results = simulator.run_simulation()

        st.subheader("Results")
        st.write(results.final_recommendation)
        st.line_chart(results.timeline[['On-Net Cost', 'Off-Net Cost']])

        st.subheader("Data Table")
        st.dataframe(results.timeline)

        if results.break_even_month:
            st.write(f"The off-net option becomes more cost-effective starting month {results.break_even_month}.")
        else:
            st.write("No break-even point within the given timeframe.")

if __name__ == "__main__":
    main()

