import requests
import json
import pandas as pd
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import os

class NutritionLabelMaker:
    def __init__(self, api_key):
        """
        Initialize the NutritionLabelMaker with the USDA API key.
        """
        self.api_key = api_key
        self.base_url = "https://api.nal.usda.gov/fdc/v1/"
        self.headers = {'Content-Type': 'application/json'}

    def fdcID_retrieval(self, food_list, branded=True):
        """
        Retrieve FDCIDs for a list of food items using the USDA database.
        """
        fdcIDs = []
        for item in food_list:
            # Prepare request payload
            data = {"generalSearchInput": item}
            requested_url = f"{self.base_url}search?api_key={self.api_key}"
            response = requests.post(requested_url, headers=self.headers, json=data)

            print(response)

            if response.status_code == 200:
                parsed = response.json()
                best_idx, best_ratio = None, 0

                for idx, food in enumerate(parsed.get('foods', [])):
                    try:
                        # Match based on branded or unbranded criteria
                        if branded and 'brandOwner' in food:
                            curr_ratio = fuzz.token_set_ratio(item, food['brandOwner'] + ' ' + food['description'])
                        else:
                            curr_ratio = fuzz.token_set_ratio(item, food['description'])
                        if curr_ratio > best_ratio:
                            best_idx, best_ratio = idx, curr_ratio
                    except:
                        pass
                if best_idx is not None:
                    fdcIDs.append(parsed['foods'][best_idx]['fdcId'])
                else:
                    fdcIDs.append(None)
            else:
                print(f"Error retrieving FDCID for {item}: {response.status_code}")
                fdcIDs.append(None)
        return fdcIDs

    def nutrition_retrieval(self, fdcIDs):
        """
        Retrieve nutritional data for a list of FDCIDs.
        """
        nutrient_container = []
        nutrient_list = [
            'trans_fat', 'sat_fat', 'cholesterol', 'sodium', 'carbs',
            'fiber', 'sugars', 'protein', 'vit_a', 'vit_c',
            'calcium', 'iron', 'energy', 'fdcID'
        ]

        for fdcID in fdcIDs:
            requested_url = f"{self.base_url}{fdcID}?api_key={self.api_key}"
            print(requested_url)
            response = requests.get(requested_url, headers=self.headers)
            if response.status_code == 200:
                parsed = response.json()
                nutrients = {key: 0 for key in nutrient_list}
                nutrients['fdcID'] = fdcID

                for nutrient in parsed.get('foodNutrients', []):
                    try:
                        id_to_key = {
                            1257: 'trans_fat', 1258: 'sat_fat', 1253: 'cholesterol',
                            1093: 'sodium', 1005: 'carbs', 1079: 'fiber',
                            2000: 'sugars', 1003: 'protein', 1104: 'vit_a',
                            1162: 'vit_c', 1087: 'calcium', 1089: 'iron',
                            1008: 'energy'
                        }
                        if nutrient['nutrient']['id'] in id_to_key:
                            key = id_to_key[nutrient['nutrient']['id']]
                            nutrients[key] = nutrient['amount']
                    except:
                        pass
                nutrient_container.append(nutrients)
            else:
                print(f"Error retrieving nutrition data for FDCID {fdcID}: {response.status_code}")

        return pd.DataFrame(nutrient_container)

    def preprocess_nutrients(self, df):
        """
        Preprocess nutritional data by scaling nutrients to per kcal.
        """
        for col in ['protein', 'fiber', 'trans_fat', 'sat_fat', 'sugars', 'calcium', 'vit_c', 'sodium']:
            df[col] = df[col] / df['energy']
        return df

    def generate_label(self, food_name, df):
        """
        Generate a formatted nutrition label for a food item.
        """
        # Filter the dataframe for the desired food item
        if not df.empty:
            label_data = df.iloc[0]
            label = f"Nutrition Facts for {food_name}\n"
            label += f"Calories: {label_data['energy']} kcal\n"
            label += f"Protein: {label_data['protein']:.2f} g\n"
            label += f"Fiber: {label_data['fiber']:.2f} g\n"
            label += f"Total Fat: {label_data['trans_fat']:.2f} g\n"
            label += f"Saturated Fat: {label_data['sat_fat']:.2f} g\n"
            label += f"Sugars: {label_data['sugars']:.2f} g\n"
            label += f"Calcium: {label_data['calcium']:.2f} mg\n"
            label += f"Vitamin C: {label_data['vit_c']:.2f} mg\n"
            label += f"Sodium: {label_data['sodium']:.2f} mg\n"
            return label
        else:
            return f"No nutrition data available for {food_name}."

# Example usage
if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("USDA_KEY")
    print(api_key)
    food_list = ['bob\'s red mill natural foods gluten free all purpose flour', 'wild roots omega powerhouse trail mix']

    # Initialize the label maker
    label_maker = NutritionLabelMaker(api_key)

    # Retrieve FDCIDs
    fdcIDs = label_maker.fdcID_retrieval(food_list)
    print(fdcIDs)

    # Retrieve and preprocess nutrition data
    nutrition_df = label_maker.nutrition_retrieval(fdcIDs)
    processed_df = label_maker.preprocess_nutrients(nutrition_df)

    # Generate and print labels
    for food, fdcID in zip(food_list, fdcIDs):
        if fdcID:
            label = label_maker.generate_label(food, processed_df[processed_df['fdcID'] == fdcID])
            print(label)
        else:
            print(f"No data available for {food}.")
