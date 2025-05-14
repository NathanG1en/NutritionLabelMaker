nutrition_data = {
    'serving_size': '1 cup (228g)',
    'servings_per_container': 2,
    'calories': 260,
    'calories_from_fat': 120,
    'total_fat': 13,
    'saturated_fat': 5,
    'trans_fat': 2,
    'cholesterol': 30,
    'sodium': 660,
    'total_carbs': 31,
    'fiber': 0,
    'sugars': 5,
    'protein': 5,
    'vitamin_a': 4,
    'vitamin_c': 2,
    'calcium': 15,
    'iron': 4
}

from PIL import Image, ImageDraw, ImageFont

def draw_nutrition_label_fallback(data, filename='label_output_fallback.png'):
    width, height = 400, 800
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Graceful fallback to default font
    try:
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
        font_small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
    except:
        font_bold = font = font_small = ImageFont.load_default()

    y = 10
    line_spacing = 28

    def draw_line(text, bold=False, indent=0, size='normal'):
        nonlocal y
        current_font = font_bold if bold else (font_small if size == 'small' else font)
        draw.text((10 + indent, y), text, font=current_font, fill='black')
        y += line_spacing if size != 'small' else 22

    def draw_bar(height=5):
        nonlocal y
        draw.rectangle([0, y, width, y + height], fill='black')
        y += height + 5

    draw_line("Nutrition Facts", bold=True)
    draw_bar(10)

    draw_line(f"Serving Size {data['serving_size']}")
    draw_line(f"Servings Per Container {data['servings_per_container']}")
    draw_bar(5)

    draw_line("Amount Per Serving", bold=True)
    draw_line(f"Calories {data['calories']}   Calories from Fat {data['calories_from_fat']}", bold=True)
    draw_bar(5)

    draw_line("% Daily Value*", bold=False)
    draw_line(f"Total Fat {data['total_fat']}g", bold=True)
    draw_line(f"Saturated Fat {data['saturated_fat']}g", indent=20)
    draw_line(f"Trans Fat {data['trans_fat']}g", indent=20)

    draw_line(f"Cholesterol {data['cholesterol']}mg", bold=True)
    draw_line(f"Sodium {data['sodium']}mg", bold=True)
    draw_line(f"Total Carbohydrate {data['total_carbs']}g", bold=True)
    draw_line(f"Dietary Fiber {data['fiber']}g", indent=20)
    draw_line(f"Sugars {data['sugars']}g", indent=20)
    draw_line(f"Protein {data['protein']}g", bold=True)

    draw_bar(5)

    draw_line(f"Vitamin A {data['vitamin_a']}%   |   Vitamin C {data['vitamin_c']}%", size='small')
    draw_line(f"Calcium {data['calcium']}%     |   Iron {data['iron']}%", size='small')

    draw_line("* Percent Daily Values are based on a 2,000 calorie diet.", size='small')
    draw_line("Your Daily Values may be higher or lower depending on your calorie needs:", size='small')

    image.save(f"{filename}")
    return f"images/{filename}"

# Generate the fallback label image
    draw_nutrition_label_fallback(nutrition_data)
