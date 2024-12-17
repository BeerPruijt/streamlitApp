import streamlit as st
import pandas as pd
from datetime import datetime
import json
from typing import List, Dict, Union
import re
import os

# [Previous helper functions remain the same: generate_quarters, get_default_data, load_spec_file, get_categories]
# ... 

def apply_settings_to_variables(selected_vars: List[str], settings: Dict, data: Dict):
    """Apply given settings to multiple variables."""
    for var_name in selected_vars:
        data[var_name]["method"] = settings["method"]
        if settings["method"] == "single_value_fill":
            data[var_name]["input"] = settings["input"]
            data[var_name]["quarters"] = None
        else:
            data[var_name]["quarters"] = settings["quarters"]
            data[var_name]["input"] = settings["input"].copy()  # Create a copy of the list
    return data

def render_batch_settings(category: str, variables: List[str], key_prefix: str):
    """Render batch settings interface for multiple variables."""
    with st.expander("🔧 Batch Settings", expanded=False):
        st.write("Apply same settings to multiple variables")
        
        # Multi-select for variables
        selected_vars = st.multiselect(
            "Select Variables",
            variables,
            key=f"{key_prefix}_batch_select"
        )
        
        if selected_vars:
            method = st.selectbox(
                "Method",
                ["single_value_fill", "quarterly_values_fill"],
                key=f"{key_prefix}_batch_method"
            )
            
            settings = {
                "method": method
            }
            
            if method == "single_value_fill":
                value = st.number_input(
                    "Value",
                    value=0.0,
                    key=f"{key_prefix}_batch_value"
                )
                settings["input"] = value
                settings["quarters"] = None
                
            else:  # quarterly_values_fill
                col1, col2 = st.columns(2)
                with col1:
                    start_quarter = st.text_input(
                        "Start Quarter (YYYYQ#)",
                        value="2024Q1",
                        key=f"{key_prefix}_batch_start",
                        help="Format: YYYYQ# (e.g., 2024Q1)"
                    )
                with col2:
                    end_quarter = st.text_input(
                        "End Quarter (YYYYQ#)",
                        value="2027Q4",
                        key=f"{key_prefix}_batch_end",
                        help="Format: YYYYQ# (e.g., 2027Q4)"
                    )
                
                if re.match(r"^\d{4}Q[1-4]$", start_quarter) and re.match(r"^\d{4}Q[1-4]$", end_quarter):
                    quarters = generate_quarters(start_quarter, end_quarter)
                    settings["quarters"] = f"{start_quarter}:{end_quarter}"
                    
                    df = pd.DataFrame({
                        "Quarter": quarters,
                        "Value": [0] * len(quarters)
                    })
                    
                    edited_df = st.data_editor(
                        df,
                        key=f"{key_prefix}_batch_editor",
                        hide_index=True,
                        num_rows="fixed"
                    )
                    
                    settings["input"] = edited_df["Value"].tolist()
                else:
                    st.error("Please enter valid quarter formats (YYYYQ#)")
                    return
            
            if st.button("Apply Settings to Selected Variables", key=f"{key_prefix}_batch_apply"):
                st.session_state.data = apply_settings_to_variables(
                    selected_vars,
                    settings,
                    st.session_state.data
                )
                st.success(f"Applied settings to {len(selected_vars)} variables")

def render_variable_settings(var_name: str, var_data: Dict, key_prefix: str):
    """Render settings for a single variable."""
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.write(f"**{var_name}**")
    
    with col2:
        method = st.selectbox(
            "Method",
            ["single_value_fill", "quarterly_values_fill"],
            key=f"{key_prefix}_method_{var_name}",
            index=0 if var_data["method"] == "single_value_fill" else 1
        )
    
    # Update the method in the data
    st.session_state.data[var_name]["method"] = method
    
    # Indented settings based on method
    with st.container():
        st.markdown("   ")  # Add some spacing
        if method == "single_value_fill":
            value = st.number_input(
                "Value",
                value=float(var_data["input"]) if isinstance(var_data["input"], (int, float)) else 0,
                key=f"{key_prefix}_value_{var_name}"
            )
            st.session_state.data[var_name]["input"] = value
            st.session_state.data[var_name]["quarters"] = None
            
        else:  # quarterly_values_fill
            col1, col2 = st.columns(2)
            with col1:
                start_quarter = st.text_input(
                    "Start Quarter (YYYYQ#)",
                    value="2024Q1",
                    key=f"{key_prefix}_start_{var_name}",
                    help="Format: YYYYQ# (e.g., 2024Q1)"
                )
            with col2:
                end_quarter = st.text_input(
                    "End Quarter (YYYYQ#)",
                    value="2027Q4",
                    key=f"{key_prefix}_end_{var_name}",
                    help="Format: YYYYQ# (e.g., 2027Q4)"
                )
            
            if re.match(r"^\d{4}Q[1-4]$", start_quarter) and re.match(r"^\d{4}Q[1-4]$", end_quarter):
                quarters = generate_quarters(start_quarter, end_quarter)
                st.session_state.data[var_name]["quarters"] = f"{start_quarter}:{end_quarter}"
                
                current_values = st.session_state.data[var_name]["input"]
                if not isinstance(current_values, list) or len(current_values) != len(quarters):
                    current_values = [0] * len(quarters)
                
                df = pd.DataFrame({
                    "Quarter": quarters,
                    "Value": current_values
                })
                
                edited_df = st.data_editor(
                    df,
                    key=f"{key_prefix}_editor_{var_name}",
                    hide_index=True,
                    num_rows="fixed"
                )
                
                st.session_state.data[var_name]["input"] = edited_df["Value"].tolist()
            else:
                st.error("Please enter valid quarter formats (YYYYQ#)")
    
    st.divider()

def main():
    st.title("Categorized JSON Configuration Editor")
    
    # Initialize session state with data from file or default data
    if 'data' not in st.session_state:
        st.session_state.data = load_spec_file()
    
    # Get categories
    categories = get_categories(st.session_state.data)
    
    # Create tabs for each category
    category_tabs = st.tabs(list(categories.keys()))
    
    for category, tab in zip(categories.keys(), category_tabs):
        with tab:
            st.header(category)
            
            # Add batch settings at the top of each category
            render_batch_settings(category, categories[category], f"{category}")
            
            # Create expander for individual variable settings
            with st.expander("Individual Variable Settings", expanded=True):
                for var_name in categories[category]:
                    render_variable_settings(
                        var_name,
                        st.session_state.data[var_name],
                        f"{category}"
                    )
    
    # Display the resulting JSON
    st.header("Generated JSON")
    st.json(st.session_state.data)
    
    # Add download buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download JSON"):
            json_str = json.dumps(st.session_state.data, indent=2)
            st.download_button(
                label="Download JSON file",
                data=json_str,
                file_name="config.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("Save as dummy_spec.json"):
            try:
                with open("dummy_spec.json", "w") as f:
                    json.dump(st.session_state.data, f, indent=2)
                st.success("Successfully saved to dummy_spec.json")
            except Exception as e:
                st.error(f"Error saving file: {str(e)}")

if __name__ == "__main__":
    main()