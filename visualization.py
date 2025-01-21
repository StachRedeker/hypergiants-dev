import streamlit as st
import pandas as pd

def display_results(results, compute_mode):
    st.subheader("Results Overview")
    st.write(results.final_recommendation)

    # Plot cumulative costs (On-Net vs Off-Net)
    st.subheader("Cost Comparison")
    st.line_chart(results.timeline.set_index("Day")[["On-Net Cost", "Off-Net Cost"]], 
                  use_container_width=True)

    # Specific Metrics for AWS Mode
    if compute_mode == "AWS":
        st.subheader("AWS Specific Metrics")
        col1, col2 = st.columns(2)

        with col1:
            st.metric(label="Required Bandwidth (Gbps)", 
                      value=f"{results.required_bandwidth_gbps:.2f}")
        with col2:
            st.metric(label="Transfer Link Cost ($/Month)", 
                      value=f"${results.aws_transfer_link_cost:.2f}")

    # User, Requests, and Data Volume Metrics
    st.subheader("Daily Metrics Over Time")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.line_chart(results.timeline.set_index("Day")["Active Users"], 
                      use_container_width=True)
        st.caption("Active Users Per Day")

    with col2:
        st.line_chart(results.timeline.set_index("Day")["Sent Requests"], 
                      use_container_width=True)
        st.caption("Number of Requests Sent Per Day")

    with col3:
        st.line_chart(results.timeline.set_index("Day")["Sent Data Volume (GB)"], 
                      use_container_width=True)
        st.caption("Data Volume Sent Per Day (GB)")

    # Display full data table
    st.subheader("Detailed Data Table")
    st.dataframe(results.timeline)

    # Highlight recommendations and summary metrics
    st.subheader("Key Metrics Summary")
    st.write(f"Total On-Net Cost: ${results.timeline['On-Net Cost'].iloc[-1]:,}")
    st.write(f"Total Off-Net Cost: ${results.timeline['Off-Net Cost'].iloc[-1]:,}")
