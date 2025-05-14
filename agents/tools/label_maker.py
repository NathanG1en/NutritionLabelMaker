from PIL import Image, ImageDraw, ImageFont

class NutritionLabelDrawer:
    def __init__(self, width=450, height=1000):
        self.width = width
        self.height = height
        self.fonts = self._load_fonts()

    def _load_fonts(self):
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

    def draw_vertical_label(self, data):
        image = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(image)
        y = 10

        def draw_line(text, bold=False, indent=0, size='normal', right_align_value=None):
            nonlocal y
            if size == 'title':
                font = self.fonts["title"]
                spacing = 40
            elif size == 'subheader':
                font = self.fonts["subheader"]
                spacing = 28
            elif size == 'calories':
                font = self.fonts["calories"]
                spacing = 50
            elif size == 'small':
                font = self.fonts["small"]
                spacing = 22
            else:
                font = self.fonts["bold"] if bold else self.fonts["regular"]
                spacing = 28
            draw.text((10 + indent, y), text, font=font, fill='black')
            if right_align_value:
                value_font = self.fonts["bold"] if bold else self.fonts["regular"]
                bbox = draw.textbbox((0, 0), right_align_value, font=value_font)
                w = bbox[2] - bbox[0]
                draw.text((self.width - 10 - w, y), right_align_value, font=value_font, fill='black')
            y += spacing

        def draw_bar(thickness=5, margin=5):
            nonlocal y
            draw.rectangle([0, y, self.width, y + thickness], fill='black')
            y += thickness + margin

        # Header
        draw_line("Nutrition Facts", size='title')
        draw_line(f"{data['servings_per_container']} servings per container")
        draw_line(f"Serving size     {data['serving_size']}", bold=True)
        draw_bar(7)
        draw_line("Amount per serving", size='small')
        draw_line("Calories", size='calories', bold=True, right_align_value=str(data['calories']))
        draw_bar(3)
        draw_line("% Daily Value*", bold=True)

        for nutrient in data["nutrients"]:
            name = nutrient["name"]
            amount = nutrient.get("amount", "")
            dv = nutrient.get("daily_value", "")
            label = f"{name} {amount}"
            draw_line(label, bold="Total" in name or "Includes" in name or "Protein" in name, indent=10, right_align_value=dv)

        draw_bar(3)

        micro = data.get("micronutrients", [])
        for i in range(0, len(micro), 2):
            left = f"{micro[i]['name']} {micro[i]['amount']} {micro[i]['daily_value']}"
            right = f"{micro[i+1]['name']} {micro[i+1]['amount']} {micro[i+1]['daily_value']}" if i+1 < len(micro) else ""
            draw_line(f"{left:<24} {right}")

        for line in data.get("footer", [
            "* The % Daily Value (DV) tells you how much a nutrient in",
            "a serving of food contributes to a daily diet. 2,000 calories",
            "a day is used for general nutrition advice."
        ]):
            draw_line(line, size='small')

        return image
