#
# import requests
# import json
# import pandas as pd
# import pickle
# import os
# from fuzzywuzzy import fuzz
#
# class FoodSearchAgent:
#     def __init__(self, api_key, cache_file='food_cache.pkl'):
#         """
#         Initialize the FoodSearchAgent with the USDA API key.
#         """
#         self.api_key = api_key
#         self.base_url = "https://api.nal.usda.gov/fdc/v1/"
#         self.headers = {'Content-Type': 'application/json'}
#         self.cache_file = cache_file
#         self.cache = self.load_cache()
#
#     def load_cache(self):
#         """Load cached search results from a file."""
#         if os.path.exists(self.cache_file):
#             with open(self.cache_file, 'rb') as f:
#                 return pickle.load(f)
#         return {}
#
#     def save_cache(self):
#         """Save search results to cache."""
#         with open(self.cache_file, 'wb') as f:
#             pickle.dump(self.cache, f)
#
#     def search_usda(self, item):
#         """Search the USDA FoodData Central database for a food item."""
#         if item in self.cache:
#             return self.cache[item]
#
#         data = {"generalSearchInput": item}
#         requested_url = f"{self.base_url}search?api_key={self.api_key}"
#         response = requests.post(requested_url, headers=self.headers, json=data)
#
#         if response.status_code == 200:
#             results = response.json().get('foods', [])
#             self.cache[item] = results
#             self.save_cache()
#             return results
#         else:
#             print(f"USDA search error for {item}: {response.status_code}")
#             return []
#
#     def fuzzy_match(self, item, results, branded=True):
#         """Find the best match for the item using fuzzy matching."""
#         best_idx, best_score = None, 0
#
#         for idx, food in enumerate(results):
#             try:
#                 if branded and 'brandOwner' in food:
#                     compare_str = f"{food.get('brandOwner', '')} {food.get('description', '')}"
#                 else:
#                     compare_str = food.get('description', '')
#
#                 score = fuzz.token_set_ratio(item.lower(), compare_str.lower())
#                 if score > best_score:
#                     best_idx, best_score = idx, score
#             except Exception as e:
#                 print(f"Fuzzy match error: {e}")
#
#         if best_idx is not None:
#             return results[best_idx]['fdcId'], best_score
#         return None, 0
#
#     def retrieve_fdc_ids(self, food_list, branded=True):
#         """Retrieve FDCIDs for a list of food items using fuzzy matching."""
#         fdc_ids = {}
#         for item in food_list:
#             results = self.search_usda(item)
#             if results:
#                 fdc_id, score = self.fuzzy_match(item, results, branded)
#                 fdc_ids[item] = {'fdcId': fdc_id, 'match_score': score}
#             else:
#                 fdc_ids[item] = {'fdcId': None, 'match_score': 0}
#         return pd.DataFrame.from_dict(fdc_ids, orient='index').reset_index().rename(columns={'index': 'food_item'})
#
#     def clear_cache(self):
#         """Clear the search cache."""
#         if os.path.exists(self.cache_file):
#             os.remove(self.cache_file)
#         self.cache = {}
#         print("Cache cleared.")
#
#
#     def nutrition_retrieval(self, fdcIDs):
#         """
#         Retrieve nutritional data for a list of FDCIDs.
#         """
#         nutrient_container = []
#         nutrient_list = [
#             'trans_fat', 'sat_fat', 'cholesterol', 'sodium', 'carbs',
#             'fiber', 'sugars', 'protein', 'vit_a', 'vit_c',
#             'calcium', 'iron', 'energy', 'fdcID'
#         ]
#
#         for fdcID in fdcIDs:
#             requested_url = f"{self.base_url}{fdcID}?api_key={self.api_key}"
#             print(f"Fetching nutrition data from: {requested_url}")
#             response = requests.get(requested_url, headers=self.headers)
#
#             if response.status_code == 200:
#                 parsed = response.json()
#                 nutrients = {key: 0 for key in nutrient_list}
#                 nutrients['fdcID'] = fdcID
#
#                 for nutrient in parsed.get('foodNutrients', []):
#                     id_to_key = {
#                         1257: 'trans_fat', 1258: 'sat_fat', 1253: 'cholesterol',
#                         1093: 'sodium', 1005: 'carbs', 1079: 'fiber',
#                         2000: 'sugars', 1003: 'protein', 1104: 'vit_a',
#                         1162: 'vit_c', 1087: 'calcium', 1089: 'iron',
#                         1008: 'energy'
#                     }
#                     if nutrient['nutrient']['id'] in id_to_key:
#                         key = id_to_key[nutrient['nutrient']['id']]
#                         nutrients[key] = nutrient['amount']
#
#                 nutrient_container.append(nutrients)
#             else:
#                 print(f"Error retrieving nutrition data for FDCID {fdcID}: {response.status_code}")
#
#         return pd.DataFrame(nutrient_container)
#
#     def preprocess_nutrients(self, df):
#         """
#         Preprocess nutritional data by scaling nutrients to per kcal.
#         """
#         for col in ['protein', 'fiber', 'trans_fat', 'sat_fat', 'sugars', 'calcium', 'vit_c', 'sodium']:
#             df[col] = df[col] / df['energy']
#         return df
#
#     def generate_label(self, food_name, df):
#         """
#         Generate a formatted nutrition label for a food item.
#         """
#         if not df.empty:
#             label_data = df.iloc[0]
#             label = f"Nutrition Facts for {food_name}\n"
#             label += f"Calories: {label_data['energy']} kcal\n"
#             label += f"Protein: {label_data['protein']:.2f} g\n"
#             label += f"Fiber: {label_data['fiber']:.2f} g\n"
#             label += f"Total Fat: {label_data['trans_fat']:.2f} g\n"
#             label += f"Saturated Fat: {label_data['sat_fat']:.2f} g\n"
#             label += f"Sugars: {label_data['sugars']:.2f} g\n"
#             label += f"Calcium: {label_data['calcium']:.2f} mg\n"
#             label += f"Vitamin C: {label_data['vit_c']:.2f} mg\n"
#             label += f"Sodium: {label_data['sodium']:.2f} mg\n"
#             return label
#         else:
#             return f"No nutrition data available for {food_name}."
#
#
#
