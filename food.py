import streamlit as st
import pandas as pd
from agents.food_search_funcs import FoodSearcher

# App Title
st.title("🍎 AI-Powered USDA Nutrition Label Generator")

# Sidebar for API Key
api_key = "DEMO_KEY"
alpha = st.sidebar.slider("SBERT-Fuzzy Matching Weight (α)", 0.0, 1.0, 0.5, 0.05)
branded = st.sidebar.checkbox("Search Branded Foods Only", value=True)

# Initialize Agent
if api_key:
    agent = FoodSearcher(api_key)
else:
    st.warning("Please enter your USDA API key.")
    st.stop()

# Text input for user food list
food_input = st.text_area("Enter Food Items (comma-separated):")

# --- Step 1: Trigger Food Search ---
if st.button("Generate Labels"):
    if not food_input:
        st.error("Please enter at least one food item.")
    else:
        food_list = [item.strip() for item in food_input.split(",")]
        with st.spinner("Retrieving FDC IDs..."):
            fdc_results = agent.retrieve_fdc_ids(food_list, branded=branded, alpha=alpha)
            st.session_state.fdc_results = fdc_results
        st.subheader("📊 FDC ID Search Results")
        st.dataframe(fdc_results)

        fdc_ids_w_desc = fdc_results[['fdcId', 'description']].dropna()
        if fdc_ids_w_desc.empty:
            st.error("No valid FDC IDs found.")
        else:
            with st.spinner("Retrieving Nutrition Data..."):
                nutrition_df = agent.nutrition_retrieval(
                    fdc_ids_w_desc['fdcId'],
                    descriptors=fdc_ids_w_desc
                )
                st.session_state.nutrition_df = nutrition_df
            st.subheader("📊 Nutrition Data (Raw)")
            st.dataframe(nutrition_df)

# --- Step 2: Show Sliders and Nutrition Total ---
if "nutrition_df" in st.session_state:
    nutrition_df = st.session_state.nutrition_df

    st.subheader("⚖️ Adjust Ingredient Amounts")
    ingredient_weights = []
    for i, row in nutrition_df.iterrows():
        grams = st.number_input(
            label=f"Grams of {row['name']}:",
            min_value=0.0,
            value=100.0,
            key=f"grams_{i}"
        )
        ingredient_weights.append(grams)

    # Scale and display combined nutrients
    scaled = nutrition_df.copy()
    for i, grams in enumerate(ingredient_weights):
        scaled.iloc[i, :-1] *= (grams / 100)

    combined_nutrients = scaled.drop(columns='fdcID').sum().to_dict()
    st.subheader("🧮 Combined Nutrients (Weighted Total)")
    st.write(combined_nutrients)
