import requests
import pickle
import os
import pandas as pd
from fuzzywuzzy import fuzz
from sentence_transformers import SentenceTransformer, util
from fastbook import *

from fastdownload import download_url
from fastai.vision.all import *
from pathlib import Path

class FoodSearcher:
    def __init__(self, api_key, cache_file='food_cache.pkl'):
        """
        Initialize the FoodSearchAgent with the USDA API key and SBERT model.
        """
        self.api_key = api_key
        self.base_url = "https://api.nal.usda.gov/fdc/v1/"
        self.headers = {'Content-Type': 'application/json'}
        self.cache_file = cache_file
        self.cache = self.load_cache()

        # Load SBERT model
        self.sbert_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
        self.embedding_cache = {}

    def load_cache(self):
        """Load cached search results from a file."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        return {}

    def save_cache(self):
        """Save search results to cache."""
        with open(self.cache_file, 'wb') as f:
            pickle.dump(self.cache, f)

    def get_embedding(self, text):
        """Get SBERT embedding with caching."""
        if text not in self.embedding_cache:
            self.embedding_cache[text] = self.sbert_model.encode(text, convert_to_tensor=True)
        return self.embedding_cache[text]

    def search_usda(self, item):
        """Search the USDA FoodData Central database for a food item."""
        if item in self.cache:
            return self.cache[item]

        data = {"generalSearchInput": item}
        requested_url = f"{self.base_url}search?api_key={self.api_key}"
        response = requests.post(requested_url, headers=self.headers, json=data)

        if response.status_code == 200:
            results = response.json().get('foods', [])
            self.cache[item] = results
            self.save_cache()
            return results
        else:
            print(f"USDA search error for {item}: {response.status_code}")
            return []

    def hybrid_match(self, item, results, branded=True, alpha=0.5):
        """
        Find the best match using a hybrid score (SBERT + Fuzzy Matching).

        Args:
            item (str): Input food item.
            results (list): USDA search results.
            branded (bool): If True, prioritize branded matches.
            alpha (float): Weight for SBERT (0.0 - 1.0). Default is 0.5.

        Returns:
            dict: Best matching result with scores.
        """
        item_embedding = self.get_embedding(item)
        best_idx, best_score = None, 0

        for idx, food in enumerate(results):
            description = food.get('description', '')
            if branded and 'brandOwner' in food:
                compare_str = f"{food['brandOwner']} {description}"
            else:
                compare_str = description

            # SBERT Similarity
            compare_embedding = self.get_embedding(compare_str)
            sbert_score = util.pytorch_cos_sim(item_embedding, compare_embedding).item()

            # Fuzzy Matching Score
            fuzzy_score = fuzz.token_set_ratio(item.lower(), compare_str.lower()) / 100.0

            # Hybrid Score (Weighted Combination)
            hybrid_score = (alpha * sbert_score) + ((1 - alpha) * fuzzy_score)

            if hybrid_score > best_score:
                best_idx, best_score = idx, hybrid_score

        return results[best_idx] if best_idx is not None else None

    def retrieve_fdc_ids(self, food_list, branded=True, alpha=0.5):
        """
        Retrieve FDCIDs for a list of food items using hybrid semantic and fuzzy matching.

        Args:
            food_list (list): List of food items to search for.
            branded (bool): If True, prioritize branded matches.
            alpha (float): Weight for SBERT vs. Fuzzy Matching.

        Returns:
            pd.DataFrame: DataFrame with food items, FDC IDs, and match scores.
        """
        results = []

        for item in food_list:
            usda_results = self.search_usda(item)
            if usda_results:
                best_match = self.hybrid_match(item, usda_results, branded, alpha)
                if best_match:
                    # Ensure foodCategory is a dictionary before calling .get()
                    food_category = best_match.get('foodCategory', 'N/A')
                    if isinstance(food_category, dict):
                        food_category = food_category.get('description', 'N/A')

                    results.append({
                        "food_item": item,
                        "fdcId": best_match.get('fdcId', 'N/A'),
                        "description": best_match.get('description', 'N/A'),
                        "brandOwner": best_match.get('brandOwner', 'N/A'),
                        "foodCategory": food_category
                    })
                else:
                    results.append({"food_item": item, "fdcId": None, "description": "No match found"})
            else:
                results.append({"food_item": item, "fdcId": None, "description": "No results from USDA"})

        return pd.DataFrame(results)


    def nutrition_retrieval(self, fdcIDs, descriptors = pd.DataFrame(columns = ['description'])):
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
            print(f"Fetching nutrition data from: {requested_url}")
            response = requests.get(requested_url, headers=self.headers)

            if response.status_code == 200:
                parsed = response.json()
                nutrients = {key: 0 for key in nutrient_list}
                nutrients['fdcID'] = fdcID
                nutrients['name'] = descriptors['description'][descriptors['fdcId'] == nutrients['fdcID']].iloc[0]


                for nutrient in parsed.get('foodNutrients', []):
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



    def search_images(self, food, max_images=1):
        """
        Search DuckDuckGo for product images based on the given term.

        Args:
            food (str): Search query ( food item ) for the product.
            max_images (int): Maximum number of images to return - set to 1, but might change.

        Returns:
            str: Local path of the first downloaded image.
        """
        print(f"Searching for '{food}'")
        result = search_images_ddg(f'{food} food', max_images=max_images)
        url = result[0]
        print(f"The image: {url}")

        return url



