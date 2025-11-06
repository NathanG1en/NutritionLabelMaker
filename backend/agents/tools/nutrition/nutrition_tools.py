"""
LangChain tools for nutrition agent.
Provides tools for USDA food search, nutrition data retrieval, and comparison.
"""

import json
from langchain_core.tools import tool
from backend.agents.tools.nutrition.food_search_funcs import FoodSearcher


def create_nutrition_tools(food_searcher: FoodSearcher):
    """
    Create nutrition-related tools for the agent.
    
    Args:
        food_searcher: FoodSearcher instance to use for USDA API calls
        
    Returns:
        List of LangChain tool objects
    """
    
    @tool
    def search_food_items(food_items: str, branded: bool = True, alpha: float = 0.5) -> str:
        """
        Search for food items in the USDA database and retrieve their FDC IDs.
        
        Args:
            food_items: Comma-separated list of food item names to search for (e.g., "chicken breast, salmon")
            branded: Whether to prioritize branded food items
            alpha: Weight for SBERT vs fuzzy matching (0.0-1.0)
        
        Returns:
            JSON string containing FDC IDs and food descriptions
        """
        try:
            # Parse comma-separated string into list
            items_list = [item.strip() for item in food_items.split(",")]
            results = food_searcher.retrieve_fdc_ids(items_list, branded=branded, alpha=alpha)
            
            if results.empty:
                return json.dumps({"error": "No food items found", "results": []})
            
            return results.to_json(orient="records", indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error searching for food items: {str(e)}", "results": []})

    @tool
    def get_nutrition_data(fdc_ids: str) -> str:
        """
        Retrieve detailed nutrition information for given FDC IDs.
        
        Args:
            fdc_ids: Comma-separated list of FDC ID numbers (e.g., "12345, 67890")
        
        Returns:
            JSON string containing nutrition data (calories, protein, vitamins, etc.)
        """
        try:
            # Parse comma-separated string into list of integers
            ids_list = [int(id_str.strip()) for id_str in fdc_ids.split(",")]
            
            # Call nutrition_retrieval WITHOUT descriptors - let it use defaults
            nutrition_df = food_searcher.nutrition_retrieval(ids_list)
            
            if nutrition_df.empty:
                return json.dumps({"error": "No nutrition data found", "results": []})
            
            # Convert to dict for better JSON serialization
            result = nutrition_df.to_dict(orient="records")
            return json.dumps(result, indent=2)
        except ValueError as e:
            return json.dumps({"error": f"Invalid FDC ID format: {str(e)}", "results": []})
        except Exception as e:
            return json.dumps({"error": f"Error retrieving nutrition data: {str(e)}", "results": []})

    @tool
    def compare_nutrients(food_data: str, nutrient_name: str) -> str:
        """
        Compare a specific nutrient across multiple foods.
        
        Args:
            food_data: JSON string containing nutrition data from get_nutrition_data
            nutrient_name: Name of nutrient to compare (e.g., "protein", "energy", "calcium")
        
        Returns:
            Comparison summary as a string
        """
        try:
            data = json.loads(food_data)
            
            if isinstance(data, dict) and "error" in data:
                return f"Cannot compare: {data['error']}"
            
            comparison = []
            for item in data:
                name = item.get('name', 'Unknown')
                value = item.get(nutrient_name, 0)
                comparison.append(f"{name}: {value}")
            
            return "\n".join(comparison)
        except Exception as e:
            return f"Error comparing nutrients: {str(e)}"
    
    return [search_food_items, get_nutrition_data, compare_nutrients]