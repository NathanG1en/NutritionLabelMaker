import streamlit as st
import pandas as pd
from agents.food_search_funcs import FoodSearcher
from PIL import Image, ImageDraw, ImageFont


# Functions
def load_fonts():
    try:
        return {
            "title": ImageFont.truetype("/System/Library/Fonts/Supplemental/HelveticaNeue.ttc", size=40, index=4),
            "subheader": ImageFont.truetype("/System/Library/Fonts/Supplemental/Helvetica.ttc", 18),
            "calories": ImageFont.truetype("/System/Library/Fonts/Supplemental/HelveticaNeue.ttc", size=40, index=4),
            "bold": ImageFont.truetype("/System/Library/Fonts/Supplemental/Helvetica.ttc", 16),
            "regular": ImageFont.truetype("/System/Library/Fonts/Supplemental/Helvetica.ttc", 16),
            "small": ImageFont.truetype("/System/Library/Fonts/Supplemental/Helvetica.ttc", 14),
        }
    except:
        default = ImageFont.load_default()
        return {k: default for k in ["title", "subheader", "calories", "bold", "regular", "small"]}

# Core function to draw the label
def draw_nutrition_label(data):
    width, height = 450, 700
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    fonts = load_fonts()
    y = 10

    def draw_line(text, bold=False, indent=0, size='normal', right_align_value=None):
        nonlocal y
        if size == 'title':
            font = fonts["title"]
            spacing = 40
        elif size == 'subheader':
            font = fonts["subheader"]
            spacing = 28
        elif size == 'calories':
            font = fonts["calories"]
            spacing = 50
        elif size == 'small':
            font = fonts["small"]
            spacing = 22
        else:
            font = fonts["bold"] if bold else fonts["regular"]
            spacing = 28
        draw.text((10 + indent, y), text, font=font, fill='black')
        if right_align_value:
            value_font = fonts["bold"] if bold else fonts["regular"]
            bbox = draw.textbbox((0, 0), right_align_value, font=value_font)
            w = bbox[2] - bbox[0]  # width = right - left
            draw.text((width - 10 - w, y), right_align_value, font=value_font, fill='black')
        y += spacing

    def draw_bar(thickness=5, margin=5):
        nonlocal y
        draw.rectangle([0, y, width, y + thickness], fill='black')
        y += thickness + margin

    # Draw header
    draw_line("Nutrition Facts", size='title')
    draw_line(f"{data['servings_per_container']} servings per container")
    draw_line(f"Serving size     {data['serving_size']}", bold=True)
    draw_bar(7)
    draw_line("Amount per serving", size='small')
    draw_line("Calories", size='calories', bold=True,right_align_value=str(data['calories']) )
    draw_bar(3)

    draw_line("% Daily Value*", bold=True)

    for nutrient in data["nutrients"]:
        name = nutrient["name"]
        amount = nutrient.get("amount", "")
        dv = nutrient.get("daily_value", "")
        label = f"{name} {amount}"
        draw_line(label, bold="Total" in name or "Includes" in name or "Protein" in name, indent=10, right_align_value=dv)

    draw_bar(3)

    # Micronutrients side-by-side
    micro = data.get("micronutrients", [])
    for i in range(0, len(micro), 2):
        left = f"{micro[i]['name']} {micro[i]['amount']} {micro[i].get('daily_value', '')}"
        right = ""
        if i + 1 < len(micro):
            right = f"{micro[i + 1]['name']} {micro[i + 1]['amount']} {micro[i + 1].get('daily_value', '')}"
        draw_line(f"{left:<24} {right}")

    # Footer
    for line in data.get("footer", [
        "* The % Daily Value (DV) tells you how much a nutrient in",
        "a serving of food contributes to a daily diet. 2,000 calories",
        "a day is used for general nutrition advice."
    ]):
        draw_line(line, size='small')

    return image

def convert_to_nutrition_data(combined_nutrients):
    # Basic info (use placeholders if needed)
    nutrition_data = {
        "servings_per_container": 1,  # You can customize
        "serving_size": "100g",       # You can customize
        "calories": combined_nutrients.get("energy", 0),
        "nutrients": [],
        "micronutrients": []
    }

    # Mapping for nicer names (and categorization)
    macronutrient_map = {
        "trans_fat": "Trans Fat",
        "sat_fat": "Saturated Fat",
        "cholesterol": "Cholesterol",
        "sodium": "Sodium",
        "carbs": "Total Carbohydrate",
        "fiber": "Dietary Fiber",
        "sugars": "Total Sugars",
        "added_sugars": "Added Sugars",
        "protein": "Protein"
    }

    micronutrient_map = {
        "vit_a": "Vit. A",
        "vit_c": "Vit. C",
        "vit_d": "Vit. D",
        "calcium": "Calcium",
        "iron": "Iron",
        "potassium": "Potas."
    }

    # Add macronutrients
    for key, label in macronutrient_map.items():
        if key in combined_nutrients:
            value = combined_nutrients[key]
            nutrition_data["nutrients"].append({
                "name": label,
                "amount": f"{round(value, 2)}g" if "fat" in key or key in ["carbs", "fiber", "sugars", "added_sugars", "protein"] else f"{round(value)}mg"
            })

    # Add micronutrients
    for key, label in micronutrient_map.items():
        if key in combined_nutrients:
            value = combined_nutrients[key]
            suffix = "mcg" if key in ["vit_a", "vit_d"] else "mg"
            nutrition_data["micronutrients"].append({
                "name": label,
                "amount": f"{round(value, 2)}{suffix}",
                "daily_value": ""  # Add empty daily value if you don't calculate it
            })

    return nutrition_data


if __name__ == "__main__":

    # Main
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

        # --- Step 2: Trigger Food Search ---
        st.subheader("🖼️ Product Images")
        for idx, row in st.session_state.fdc_results.iterrows():
            description = row.get("description", "")
            brand_owner = row.get("brandOwner", "")
            search_term = f"{description} {brand_owner}".strip()

            image_url = agent.search_images(food=search_term)

            if image_url:
                st.image(image_url, width=200, caption=description)
            else:
                st.warning(f"No image found for: {search_term}")

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

        # Clean commas from names and join with ', '
        combined_name = ", ".join(
            name.replace(",", "") for name in scaled['name'].astype(str)
        )
        # Add to nutrient dict
        combined_nutrients = scaled.drop(columns='fdcID').sum(numeric_only=True).to_dict()
        combined_nutrients["name"] = combined_name
        st.subheader("🧮 Combined Nutrients (Weighted Total)")
        st.write(combined_nutrients)

        combined_dict = convert_to_nutrition_data(combined_nutrients)
        image = draw_nutrition_label(combined_dict)
        st.image(image, caption="Generated Nutrition Label", use_container_width=True)





