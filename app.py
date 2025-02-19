from agents.food_search_agent import FoodSearchAgent

# Initialize agent
api_key = "DEMO_KEY"
agent = FoodSearchAgent(api_key)

# Food list to search
food_list = [
    "bob's red mill natural foods gluten free all purpose flour",
    "wild roots omega powerhouse trail mix"
]

# Retrieve FDC IDs with SBERT + Fuzzy Hybrid Matching
results = agent.retrieve_fdc_ids(food_list, branded=True, alpha=0.7)
print(results)

#
# #             # Step 5: Option to Export Data
# #             csv = processed_df.to_csv(index=False).encode('utf-8')
# #             st.download_button(
# #                 label="📥 Download Nutrition Data as CSV",
# #                 data=csv,
# #                 file_name='nutrition_data.csv',
# #                 mime='text/csv',
# #             )
# # else:
# #     st.info("Enter food items and click 'Generate Labels' to begin.")
#
# import streamlit as st
# import pandas as pd
# from agents.food_search_agent import FoodSearchAgent
#
# # App Title
# st.title("🍎 AI-Powered USDA Nutrition Label Generator")
#
# # Sidebar for API Key
# # api_key = st.sidebar.text_input("Enter USDA API Key", type="password")
# api_key = "DEMO_KEY"
# # Initialize FoodSearchAgent
# if api_key:
#     agent = FoodSearchAgent(api_key)
# else:
#     st.warning("Please enter your USDA API key.")
#     st.stop()
#
# # Food Input
# food_input = st.text_area("Enter Food Items (comma-separated):")
# branded = st.sidebar.checkbox("Search Branded Foods Only", value=True)
#
# if st.button("Generate Labels"):
#     if not food_input:
#         st.error("Please enter at least one food item.")
#     else:
#         food_list = [item.strip() for item in food_input.split(",")]
#
#         # Step 1: Retrieve FDC IDs
#         with st.spinner("Retrieving FDC IDs..."):
#             fdc_results = agent.retrieve_fdc_ids(food_list, branded=branded)
#             st.subheader("📊 FDC ID Search Results")
#             st.dataframe(fdc_results)
#
#         # Step 2: Retrieve Nutrition Data
#         fdc_ids = fdc_results['fdcId'].dropna().tolist()
#         if not fdc_ids:
#             st.error("No valid FDC IDs found.")
#         else:
#             with st.spinner("Retrieving Nutrition Data..."):
#                 nutrition_df = agent.nutrition_retrieval(fdc_ids)
#                 st.subheader("📊 Nutrition Data")
#                 st.dataframe(nutrition_df)
#
#             # Step 3: Preprocess Nutrition Data
#             processed_df = agent.preprocess_nutrients(nutrition_df)
#
#             # Step 4: Generate Nutrition Labels
#             st.subheader("🏷️ Nutrition Labels")
#             for food, fdc_id in zip(food_list, fdc_ids):
#                 food_nutrition = processed_df[processed_df['fdcID'] == fdc_id]
#                 label = agent.generate_label(food, food_nutrition)
#                 st.text_area(f"Nutrition Label for {food}", label, height=180)
# else:
#     st.info("Enter food items and click 'Generate Labels' to begin.")
#
