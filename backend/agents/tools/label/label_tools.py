"""
LangChain tools for nutrition label generation.
Provides tools for creating, formatting, and rendering nutrition labels.
"""

import json
import os
from pathlib import Path
import traceback
from datetime import datetime
from langchain_core.tools import tool
from backend.agents.tools.label.label_maker import NutritionLabelDrawer


def create_label_tools():
    """
    Create label generation and formatting tools for the agent.
    
    Returns:
        List of LangChain tool objects for label operations
    """
    
    # Initialize the label drawer
    label_drawer = NutritionLabelDrawer(width=450, height=1000)
    
    @tool
    def format_nutrition_label(nutrition_data: str, food_name: str) -> str:
        """
        Format nutrition data into a text-based nutrition label.
        
        Args:
            nutrition_data: JSON string containing nutrition data with keys like 
                          'energy', 'protein', 'carbs', 'fiber', etc.
            food_name: Name of the food item for the label header
        
        Returns:
            Formatted nutrition label as a string
        """
        try:
            data = json.loads(nutrition_data)
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]  # Take first item if list
            
            if isinstance(data, dict) and "error" in data:
                return f"Cannot create label: {data['error']}"
            
            # Build the label
            label = f"═══════════════════════════════════\n"
            label += f"  Nutrition Facts\n"
            label += f"  {food_name}\n"
            label += f"═══════════════════════════════════\n\n"
            label += f"Serving Size: 100g\n"
            label += f"───────────────────────────────────\n\n"
            label += f"Amount Per Serving:\n"
            label += f"  Calories ............. {data.get('energy', 0):.0f} kcal\n\n"
            
            label += f"Macronutrients:\n"
            label += f"  Total Fat ............ {data.get('trans_fat', 0) + data.get('sat_fat', 0):.1f}g\n"
            label += f"    Saturated Fat ...... {data.get('sat_fat', 0):.1f}g\n"
            label += f"    Trans Fat .......... {data.get('trans_fat', 0):.1f}g\n"
            label += f"  Cholesterol .......... {data.get('cholesterol', 0):.0f}mg\n"
            label += f"  Sodium ............... {data.get('sodium', 0):.0f}mg\n"
            label += f"  Total Carbohydrate ... {data.get('carbs', 0):.1f}g\n"
            label += f"    Dietary Fiber ...... {data.get('fiber', 0):.1f}g\n"
            label += f"    Total Sugars ....... {data.get('sugars', 0):.1f}g\n"
            label += f"    Added Sugars ....... {data.get('added_sugars', 0):.1f}g\n"
            label += f"  Protein .............. {data.get('protein', 0):.1f}g\n\n"
            
            label += f"Vitamins & Minerals:\n"
            label += f"  Vitamin A ............ {data.get('vit_a', 0):.1f}mcg\n"
            label += f"  Vitamin C ............ {data.get('vit_c', 0):.1f}mg\n"
            label += f"  Vitamin D ............ {data.get('vit_d', 0):.1f}mcg\n"
            label += f"  Calcium .............. {data.get('calcium', 0):.0f}mg\n"
            label += f"  Iron ................. {data.get('iron', 0):.1f}mg\n"
            label += f"  Potassium ............ {data.get('potassium', 0):.0f}mg\n"
            label += f"═══════════════════════════════════\n"
            
            return label
            
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format - {str(e)}"
        except Exception as e:
            return f"Error formatting label: {str(e)}"

    @tool
    def generate_label_image(nutrition_data: str, food_name: str = "Food Item", save_path: str = "") -> str:
        """
        Generate a visual FDA-style nutrition facts label image and SAVE it to a file.
        
        Args:
            nutrition_data: JSON string containing nutrition data with keys like 
                          'energy', 'protein', 'carbs', etc.
            food_name: Name of the food item (used for filename)
            save_path: Optional custom path to save the image. If empty, saves to 'nutrition_labels/' folder.
        
        Returns:
            File path where the image was saved, or error message
        """
        try:
            data = json.loads(nutrition_data)
            
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            if isinstance(data, dict) and "error" in data:
                return f"Cannot create image: {data['error']}"
            
            # Convert nutrition data to label format
            label_data = {
                "servings_per_container": 1,
                "serving_size": "100g",
                "calories": int(data.get("energy", 0)),
                "nutrients": [],
                "micronutrients": [],
                "footer": [
                    "* The % Daily Value (DV) tells you how much a nutrient in",
                    "a serving of food contributes to a daily diet. 2,000 calories",
                    "a day is used for general nutrition advice."
                ]
            }
            
            # Map macronutrients
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
            
            for key, label in macronutrient_map.items():
                if key in data:
                    value = data[key]
                    if "fat" in key or key in ["carbs", "fiber", "sugars", "added_sugars", "protein"]:
                        amount = f"{round(value, 2)}g"
                    else:
                        amount = f"{round(value)}mg"
                    
                    label_data["nutrients"].append({
                        "name": label,
                        "amount": amount,
                        "daily_value": ""  # Can add %DV calculation later
                    })
            
            # Map micronutrients
            micronutrient_map = {
                "vit_a": "Vit. A",
                "vit_c": "Vit. C",
                "vit_d": "Vit. D",
                "calcium": "Calcium",
                "iron": "Iron",
                "potassium": "Potas."
            }
            
            for key, label in micronutrient_map.items():
                if key in data:
                    value = data[key]
                    suffix = "mcg" if key in ["vit_a", "vit_d"] else "mg"
                    label_data["micronutrients"].append({
                        "name": label,
                        "amount": f"{round(value, 2)}{suffix}",
                        "daily_value": ""
                    })
            
            # Generate the image using NutritionLabelDrawer
            image = label_drawer.draw_vertical_label(label_data)
            
            # Determine save path
            if not save_path:
                # Always save directly under backend/data
                data_dir = Path(__file__).resolve().parents[3] / "data"
                data_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in food_name)
                filename = f"{safe_name}_{timestamp}.png"
                save_path = data_dir / filename

            # Save the image
            image.save(save_path)
            abs_path = os.path.abspath(save_path)
            filename = os.path.basename(abs_path)

            print("[DEBUG] returning JSON from generate_label_image:", {
                "message": f"The nutrition label image for '{food_name}' has been successfully created.",
                "filename": filename
            })

            # Return structured JSON — filename only
            return json.dumps({
                "message": f"The nutrition label image for '{food_name}' has been successfully created.",
                "filename": filename
            })


        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format - {str(e)}"
        except Exception as e:
            print("[DEBUG] Error generating label image:")
            traceback.print_exc()
            return f"Error generating label image: {str(e)}"

    return [format_nutrition_label, generate_label_image]