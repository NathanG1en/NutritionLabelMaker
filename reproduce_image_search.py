from duckduckgo_search import DDGS
import time

def test_image_search():
    food = "avocado"
    print(f"Searching for '{food}'...")
    start_time = time.time()
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(f'{food} food', max_results=1))
        
        print(f"Search completed in {time.time() - start_time:.2f} seconds")
        if results:
            print(f"Result: {results[0]['image']}")
        else:
            print("No results found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_image_search()
