import streamlit as st
import pandas as pd

def display_results(results, compute_mode, use_tweakers_estimates, views_per_day_for_tweakers):
    st.subheader("Final Outcome")
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
            st.metric(label="Required Sustained Link Capacity (Gbps)", 
                      value=f"{results.required_bandwidth_gbps:.6f}")
        with col2:
            st.metric(label="Transfer Link Cost (\u20ac/Month)", 
                      value=f"\u20ac{results.aws_transfer_link_cost:.6f}")

    # User, Requests, and Data Volume Metrics
    st.subheader("User-Based Metrics Over Time")
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



    # Specific Metrics for Tweakers Estimates Used
    if use_tweakers_estimates == True:
        st.subheader("Hardware Usage")

        st.write("This section is visible because you use the hardware estimates based on the Tweakers.net website.")

        cores = views_per_day_for_tweakers * 0.0004092
        ram = views_per_day_for_tweakers * 0.00000155
        storage = views_per_day_for_tweakers * 0.00011284

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(label="Compute Cores", 
                      value=f"{cores:.0f}")
        with col2:
            st.metric(label="RAM (TBs)", 
                      value=f"{ram:.4f}")
        with col3:
            st.metric(label="Storage (TBs)", 
                      value=f"{storage:.4f}")

    # Display full data table
    st.subheader("Detailed Data Table")
    st.dataframe(results.timeline)
