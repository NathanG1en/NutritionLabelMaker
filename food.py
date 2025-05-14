import streamlit as st
import pandas as pd
from agents.food_search_funcs import FoodSearcher

# App Title
st.title("🍎 AI-Powered USDA Nutrition Label Generator")

# Sidebar for API Key
# api_key = st.sidebar.text_input("Enter USDA API Key", type="password")
api_key = "DEMO_KEY"

# Alpha slider for SBERT-Fuzzy Matching
alpha = st.sidebar.slider("SBERT-Fuzzy Matching Weight (α)", 0.0, 1.0, 0.5, 0.05)

# Initialize FoodSearchAgent
if api_key:
    agent = FoodSearcher(api_key)
else:
    st.warning("Please enter your USDA API key.")
    st.stop()

# Food Input
food_input = st.text_area("Enter Food Items (comma-separated):")
branded = st.sidebar.checkbox("Search Branded Foods Only", value=True)

if st.button("Generate Labels"):
    if not food_input:
        st.error("Please enter at least one food item.")
    else:
        food_list = [item.strip() for item in food_input.split(",")]

        # Step 1: Retrieve FDC IDs with Hybrid Matching
        with st.spinner("Retrieving FDC IDs..."):
            fdc_results = agent.retrieve_fdc_ids(food_list, branded=branded, alpha=alpha)
            st.subheader("📊 FDC ID Search Results")
            st.dataframe(fdc_results)

        # Step 2: Retrieve Nutrition Data
        fdc_ids_w_desc = fdc_results[['fdcId', 'description']].dropna(subset=['fdcId', 'description'])
        if fdc_ids_w_desc.empty:
            st.error("No valid FDC IDs found.")
        else:
            with st.spinner("Retrieving Nutrition Data..."):
                nutrition_df = agent.nutrition_retrieval(
                    fdc_ids_w_desc['fdcId'],
                    description=fdc_ids_w_desc['description']
                )
                st.subheader("📊 Nutrition Data (Raw)")
                st.dataframe(nutrition_df)

# Allow user to specify weights
ingredient_weights = []
for i, row in nutrition_df.iterrows():
    grams = st.number_input(
        label=f"Grams of {row['name']}:",
        min_value=0.0,
        value=100.0,
        key=f"grams_{i}"  # ensures uniqueness
    )
    ingredient_weights.append(grams)


# Combine all into a single scaled nutrition row
scaled = nutrition_df.copy()
for i, grams in enumerate(ingredient_weights):
    scaled.iloc[i, :-1] *= (grams / 100)  # scale all nutrient columns except fdcID

combined_nutrients = scaled.drop(columns='fdcID').sum().to_dict()
