import streamlit as st
import pandas as pd
from agents.food_search_funcs import FoodSearcher


if __name__ == "__main__":
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
            fdc_ids = fdc_results['fdcId'].dropna().tolist()
            if not fdc_ids:
                st.error("No valid FDC IDs found.")
            else:
                with st.spinner("Retrieving Nutrition Data..."):
                    nutrition_df = agent.nutrition_retrieval(fdc_ids)
                    st.subheader("📊 Nutrition Data (Raw)")
                    st.dataframe(nutrition_df)

                # Step 3: Preprocess Nutrition Data
                processed_df = agent.preprocess_nutrients(nutrition_df)
                st.subheader("📊 Preprocessed Nutrition Data (Per kcal)")
                st.dataframe(processed_df)

                # Step 4: Generate and Display Nutrition Labels with Product Images
                st.subheader("🏷️ Nutrition Labels with Product Images")
                for idx, row in fdc_results.iterrows():
                    food_name = row["food_item"]
                    description = row["description"]
                    brand_owner = row["brandOwner"]
                    food_category = row["foodCategory"]
                    fdc_id = row["fdcId"]

                    food_nutrition = processed_df[processed_df['fdcID'] == fdc_id]
                    label = agent.generate_label(food_name, food_nutrition)

                    # Retrieve product image
                    search_term = f"{description} {brand_owner}"
                    image_url = agent.search_images(food = search_term)

                    # Display Image and Label
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if image_url:
                            st.image(image_url, width=200, caption=f"{description}")
                        else:
                            st.warning("No image found.")

                    # with col2:
                    #     st.text_area(f"Nutrition Label for {food_name}", label, height=180)

                # Step 5: Option to Export Data
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Nutrition Data as CSV",
                    data=csv,
                    file_name='nutrition_data.csv',
                    mime='text/csv',
                )
    else:
        st.info("Enter food items and click 'Generate Labels' to begin.")