import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import re

def analyze_and_visualize_apple_prediction():
    # --- 1. Fetch Data ---
    slug = "what-will-apple-aapl-close-at-in-2025"
    url = "https://gamma-api.polymarket.com/events"
    params = {"slug": slug}
    
    # Headers to mimic a real browser (prevents 403 Forbidden)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    print(f"Fetching data for: {slug}...")
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print("❌ No event found.")
            return

        event = data[0]
        print(f"✅ Event Found: {event['title']}")
        
        markets = event.get('markets', [])
        rows = []

        # --- 2. Process Data ---
        for market in markets:
            # Title handling (e.g., "Above $250", "$250-255")
            title = market.get('groupItemTitle', market.get('question', 'Unknown'))
            
            # --- FIX FOR YOUR ERROR ---
            # safely parse outcomePrices whether it's a list OR a string
            outcome_prices = market.get('outcomePrices', [0, 0])
            
            if isinstance(outcome_prices, str):
                try:
                    # Converts "['0.1', '0.9']" -> ['0.1', '0.9']
                    outcome_prices = json.loads(outcome_prices.replace("'", '"')) 
                except json.JSONDecodeError:
                    outcome_prices = [0, 0]
            
            # Get Yes Price (index 0)
            try:
                yes_price = float(outcome_prices[0])
            except (IndexError, ValueError):
                yes_price = 0.0

            # Create a numeric sort key from the title
            # Matches the first number found (e.g., "$250-255" -> 250)
            numbers = re.findall(r'\d+', title)
            sort_val = float(numbers[0]) if numbers else 0

            # Special handling for "<" (put at start) and ">" (put at end)
            if "<" in title:
                sort_val -= 0.1
            elif ">" in title:
                sort_val += 0.1

            rows.append({
                "Target": title,
                "Probability": yes_price,
                "SortKey": sort_val
            })

        # Create DataFrame and Sort
        df = pd.DataFrame(rows)
        df = df.sort_values(by="SortKey")

        print("\n--- Current Market Probabilities ---")
        print(df[['Target', 'Probability']].to_string(index=False, formatters={'Probability': '{:.1%}'.format}))

        # --- 3. Visualize Data ---
        plt.figure(figsize=(14, 7))
        
        # Bar Chart
        bars = plt.bar(df['Target'], df['Probability'], color='#007AFF', alpha=0.8)
        
        # Formatting
        plt.title(f"Market Prediction: {event['title']}", fontsize=16, fontweight='bold', pad=20)
        plt.xlabel("Price Target (USD)", fontsize=12)
        plt.ylabel("Probability", fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', linestyle='--', alpha=0.3)
        
        # Add percentage labels on top of bars
        for bar in bars:
            height = bar.get_height()
            if height > 0.01: # Only label if > 1%
                plt.text(bar.get_x() + bar.get_width()/2., height,
                         f'{height:.1%}',
                         ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Save and Show
        plt.tight_layout()
        filename = "apple_2025_prediction.png"
        plt.savefig(filename)
        print(f"\n✅ Visualization saved to {filename}")
        plt.show()

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")

if __name__ == "__main__":
    analyze_and_visualize_apple_prediction()