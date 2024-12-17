import streamlit as st
import pandas as pd
from datetime import datetime
import json
from typing import List, Dict, Union
import re
import os
from copy import deepcopy
import shutil

TEMP_FILE = "temp_config.json"
BASELINE_SPEC = "dummy_spec.json"

def check_for_temp_file():
    """Check if temporary file exists and handle user choice."""
    if os.path.exists(TEMP_FILE):
        try:
            with open(TEMP_FILE, 'r') as f:
                temp_data = json.load(f)
            
            # Initialize session state for prompt visibility if not exists
            if 'show_prompt' not in st.session_state:
                st.session_state.show_prompt = True
            
            # Only show the prompt if session state indicates we should
            if st.session_state.show_prompt:
                # Create a container for the card
                with st.container():
                    # Use columns to create padding around the card
                    col1, card_col, col2 = st.columns([1, 3, 1])
                    with card_col:
                        # The entire card content in one markdown string
                        st.markdown("""
                            <div style="
                                padding: 20px;
                                border-radius: 10px;
                                background-color: #f8f9fa;
                                border: 1px solid #dee2e6;
                                margin: 10px 0;
                            ">
                                <h4 style="color: #856404; margin-top: 0;">
                                    <span style="margin-right: 10px;">⚠️</span>
                                    Previous Session Detected
                                </h4>
                                <p style="color: #555;">
                                    Would you like to resume your previous work or start fresh?
                                </p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Place buttons inside the same column as the card
                        col3, col4 = st.columns(2)
                        with col3:
                            if st.button("📂 Load Previous Work", key="load_prev", use_container_width=True):
                                st.session_state.show_prompt = False
                                st.session_state.temp_data = temp_data
                                st.rerun()
                                
                        with col4:
                            if st.button("🆕 Start Fresh", key="start_fresh", use_container_width=True):
                                st.session_state.show_prompt = False
                                os.remove(TEMP_FILE)
                                st.session_state.temp_data = None
                                st.rerun()
            
            # Return the appropriate data based on user choice
            if not st.session_state.show_prompt:
                return st.session_state.get('temp_data')
                
            st.stop()
            
        except json.JSONDecodeError:
            os.remove(TEMP_FILE)
            return None
    return None

def save_temp_state(data: Dict):
    """Save current state to temporary file."""
    try:
        with open(TEMP_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving temporary state: {str(e)}")

def save_final_config(data: Dict):
    """Save final configuration to a new file with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"config_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        # If successful, remove the temporary file
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)
            
        return filename
    except Exception as e:
        st.error(f"Error saving configuration: {str(e)}")
        return None

def generate_quarters(start: str, end: str) -> List[str]:
    """Generate a list of quarters between start and end dates."""
    def quarter_to_date(quarter_str: str) -> datetime:
        year = int(quarter_str[:4])
        quarter = int(quarter_str[5])
        month = (quarter - 1) * 3 + 1
        return datetime(year, month, 1)
    
    start_date = quarter_to_date(start)
    end_date = quarter_to_date(end)
    
    quarters = []
    current_date = start_date
    while current_date <= end_date:
        quarter = (current_date.month - 1) // 3 + 1
        quarters.append(f"{current_date.year}Q{quarter}")
        if current_date.month >= 10:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 3, 1)
    
    return quarters

def load_spec_file():
    """Load the specification file."""
    try:
        with open(BASELINE_SPEC, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Baseline specification ({BASELINE_SPEC}) not found!")
        return {}

def get_categories(data: Dict) -> Dict[str, List[str]]:
    """Extract categories and their variables from the data."""
    categories = {}
    for var_name, var_data in data.items():
        category = var_data["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(var_name)
    return categories
def get_changed_variables(current_data: Dict, original_data: Dict) -> set:
    """Returns a set of variable names that have changed from original state."""
    changed_vars = set()
    
    for var_name in current_data:
        curr = current_data[var_name]
        orig = original_data[var_name]

        
        # Compare each field separately and print results
        method_changed = curr["method"] != orig["method"]
        quarters_changed = curr["quarters"] != orig["quarters"]
        is_list = isinstance(curr["input"], (list, tuple))
        
        if is_list:
            input_changed = curr["input"] != orig["input"]
        else:
            input_changed = float(curr["input"]) != float(orig["input"])
        
        if (method_changed or quarters_changed or 
            (is_list and curr["input"] != orig["input"]) or
            (not is_list and float(curr["input"]) != float(orig["input"]))):
            changed_vars.add(var_name)
            
    return changed_vars

def apply_settings_to_variables(selected_vars: List[str], settings: Dict, data: Dict):
    """Apply given settings to multiple variables."""
    for var_name in selected_vars:
        data[var_name]["method"] = settings["method"]
        if settings["method"] == "single_value_fill":
            data[var_name]["input"] = settings["input"]
            data[var_name]["quarters"] = None
        else:
            data[var_name]["quarters"] = settings["quarters"]
            data[var_name]["input"] = settings["input"].copy()
    return data

def render_batch_settings(category: str, variables: List[str], key_prefix: str):
    """Render batch settings interface for multiple variables."""
    with st.expander("🔧 Batch Settings", expanded=False):
        st.write("Apply same settings to multiple variables")
        
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
                st.rerun()

def render_variable_settings(var_name: str, var_data: Dict, key_prefix: str, changed_vars: set):
    """Render settings for a single variable."""
    change_icon = "✅ " if var_name in changed_vars else ""
    
    with st.expander(f"{change_icon}{var_name}", expanded=False):
        # Create a temporary key in session state for this variable if it doesn't exist
        temp_key = f"temp_{var_name}"
        if temp_key not in st.session_state:
            st.session_state[temp_key] = {
                "method": var_data["method"],
                "input": var_data["input"],
                "quarters": var_data["quarters"]
            }
        
        st.write("Method:")
        method = st.selectbox(
            "Fill method",
            ["single_value_fill", "quarterly_values_fill"],
            key=f"{key_prefix}_method_{var_name}",
            index=0 if st.session_state[temp_key]["method"] == "single_value_fill" else 1,
            label_visibility="collapsed"
        )
        
        # Update temp state instead of main state
        st.session_state[temp_key]["method"] = method
        
        if method == "single_value_fill":
            value = st.number_input(
                "Value",
                value=float(st.session_state[temp_key]["input"]) if isinstance(st.session_state[temp_key]["input"], (int, float)) else 0,
                key=f"{key_prefix}_value_{var_name}"
            )
            
            # Update temp state
            st.session_state[temp_key]["input"] = value
            st.session_state[temp_key]["quarters"] = None
            
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
                new_quarters = f"{start_quarter}:{end_quarter}"
                
                # Update temp state
                st.session_state[temp_key]["quarters"] = new_quarters
                
                current_values = st.session_state[temp_key]["input"]
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
                
                # Update temp state
                st.session_state[temp_key]["input"] = edited_df["Value"].tolist()
            else:
                st.error("Please enter valid quarter formats (YYYYQ#)")
        
        # Add apply button
        if st.button("Apply Changes", key=f"{key_prefix}_apply_{var_name}"):
            # Update main state from temp state
            st.session_state.data[var_name]["method"] = st.session_state[temp_key]["method"]
            st.session_state.data[var_name]["input"] = st.session_state[temp_key]["input"]
            st.session_state.data[var_name]["quarters"] = st.session_state[temp_key]["quarters"]
            st.success("Changes applied successfully!")
            st.rerun()  # Rerun to update the checkmark

def main():
    st.title("Example scenario name")
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        temp_data = check_for_temp_file()
        if temp_data is not None:
            st.session_state.data = temp_data
            st.session_state.original_data = load_spec_file()
        else:
            loaded_data = load_spec_file()
            st.session_state.data = loaded_data
            st.session_state.original_data = deepcopy(loaded_data)  # Use deepcopy instead
        st.session_state.initialized = True

    # Calculate changed variables
    changed_vars = get_changed_variables(st.session_state.data, st.session_state.original_data)
    
    # Get categories
    categories = get_categories(st.session_state.data)
    
    # Create tabs for each category
    category_tabs = st.tabs(list(categories.keys()))
    
    for category, tab in zip(categories.keys(), category_tabs):
        with tab:
            st.header(category)
            
            render_batch_settings(category, categories[category], f"{category}")
            
            for var_name in categories[category]:
                render_variable_settings(
                    var_name,
                    st.session_state.data[var_name],
                    f"{category}",
                    changed_vars
                )
    
    # Auto-save to temporary file whenever data changes
    save_temp_state(st.session_state.data)
    
    # Add save/download buttons
    st.write("---")
    st.write("### Save Options")
    col1, col2 = st.columns(2)
    
    with col1:
        # Create custom colored button with CSS
        custom_css = """
            <style>
                .stButton > button {
                    background-color: #4CAF50;  /* Green background */
                    color: white;               /* White text */
                }
                
                .stButton > button:hover {
                    background-color: #45a049;  /* Darker green on hover */
                }
            </style>
        """
        st.markdown(custom_css, unsafe_allow_html=True)
        if st.button("Save Configuration"):
            filename = save_final_config(st.session_state.data)
            if filename:
                st.success(f"Successfully saved to {filename}")
                
                # Offer immediate download of saved file
                with open(filename, 'r') as f:
                    st.download_button(
                        label="Download saved configuration",
                        data=f.read(),
                        file_name=filename,
                        mime="application/json"
                    )

    # Display the resulting JSON
    st.header("Generated JSON")
    with st.expander("View JSON", expanded=False):
        st.json(st.session_state.data)

if __name__ == "__main__":
    main()