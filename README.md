# NutritionLabelMaker

An AI-powered Streamlit app that helps you search for foods in the USDA FoodData Central database, retrieve their nutrient facts, and generate nutrition labels. It combines semantic search (SBERT) with fuzzy matching to find the best matching foods (including branded items), fetches detailed nutrients, and can compose a combined label for multiple ingredients with adjustable gram amounts. The app can also fetch a representative product image for each result.

## Key Features
- Hybrid food search (SBERT + fuzzy string match) against USDA FoodData Central
- Option to prioritize branded foods
- Retrieves macro- and micronutrients from the USDA API using FDC IDs
- Preprocessing utility to scale nutrients (e.g., per kcal)
- Interactive Streamlit UI to:
  - Enter one or more comma-separated foods
  - Tune the α weight between SBERT and fuzzy matching
  - Toggle branded-only search
  - View FDC search results and raw nutrient tables
  - Adjust per-ingredient grams and see combined totals
  - Render a Nutrition Facts style label image using PIL
  - Download preprocessed data as CSV
- Basic image lookup via DuckDuckGo to display product images for results
- Simple on-disk caching of USDA search results

## How It Works (High Level)
1. You enter one or more food names in the UI.
2. For each food, the app queries the USDA search endpoint and scores candidates via:
   - SBERT cosine similarity (SentenceTransformer paraphrase-MiniLM-L6-v2)
   - Fuzzy token-set ratio
   - A weighted hybrid score controlled by α (0–1)
3. The best match’s FDC ID is used to fetch detailed nutrients.
4. Nutrients are displayed raw and can be preprocessed and aggregated.
5. The UI can render a Nutrition Facts label image from the combined nutrients.

## Project Structure
- app.py – Streamlit app (USDA search, nutrients, image preview, CSV download)
- food.py – Streamlit app with an extended workflow (image-based nutrition label rendering and ingredient scaling)
- agents/food_search_funcs.py – FoodSearcher class (USDA search + hybrid matching, nutrient retrieval, preprocessing, image search)
- food_getter.py – A simpler, programmatic utility for FDC lookup and nutrient retrieval
- images/ – Notebooks or assets for experiments
- tests/ – Placeholder for tests (none provided yet)

## Requirements
- Python 3.11
- See pyproject.toml for dependencies (installed automatically by Poetry or pip)

Notable runtime notes:
- The first run will download the SBERT model (paraphrase-MiniLM-L6-v2).
- DuckDuckGo image search requires internet access and may return external image URLs.
- USDA API usage requires an API key; “DEMO_KEY” is used in code as a placeholder and may be rate-limited or unsupported. Use your own key for reliable results.

## Setup
You can use Poetry (recommended) or pip.

### Using Poetry
- Install Poetry if needed: https://python-poetry.org/docs/#installation
- From the project root:
  - poetry install
  - poetry run streamlit run food.py

### Using pip
- Create and activate a virtual environment
- Install dependencies:
  - pip install -r <generated requirements>  (or manually install packages from pyproject.toml)
- Run Streamlit:
  - streamlit run food.py

## Configuration (USDA API Key)
The code currently defaults to api_key = "DEMO_KEY" for convenience. For real usage, set your own key.

Options:
- Quick edit: open food.py (or app.py) and replace api_key = "DEMO_KEY" with your key.
- Environment variable: you can also modify the code to read from an env var (e.g., USDA_API_KEY) using python-dotenv.

Get a key at: https://fdc.nal.usda.gov/api-guide.html

## Running the App
- Preferred entry point:
  - streamlit run food.py
- Alternative (experimental/variant):
  - streamlit run app.py

Then, in the UI:
1. Enter one or more foods separated by commas (e.g., "bob’s red mill all purpose flour, wild roots trail mix").
2. Optionally toggle “Branded Foods Only” and adjust α.
3. Click “Generate Labels” to see FDC matches, nutrients, product images, and the generated label image.

## Notes & Limitations
- Image search returns best-effort matches; not guaranteed to be the exact product.
- Nutrient units come from USDA; some nutrients may be missing per item.
- The Nutrition Facts rendering is a simplified approximation for demonstration.
- The food_cache.pkl file stores cached search results to speed up repeated queries.

## What Does This Project Do? (One-liner)
It’s an AI-assisted Streamlit tool that finds foods in USDA FoodData Central with hybrid semantic + fuzzy matching, retrieves their nutrients, and generates nutrition labels (including a combined label for multiple ingredients).