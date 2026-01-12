import pandas as pd
import matplotlib.pyplot as plt
from fredapi import Fred

# 1. Initialize with the API key from your image
api_key = '3e6b3d277d0889cb78aebd2cd1548181'
fred = Fred(api_key=api_key)

# 2. Define the Series IDs for each macro event
# CPI: CPIAUCSL, PCE: PCEPI, PPI: PPIFIS, Fed Rate: FEDFUNDS
series_ids = {
    'CPI (Consumer Inflation)': 'CPIAUCSL',
    'PCE (Fed Target Inflation)': 'PCEPI',
    'PPI (Producer Inflation)': 'PPIFIS',
    'Fed Funds Rate (FOMC)': 'FEDFUNDS'
}

def fetch_and_plot_macro():
    data_dict = {}
    
    for name, s_id in series_ids.items():
        # Fetch data
        series = fred.get_series(s_id)
        
        # Calculate YoY % change for inflation metrics (except for Fed Rate)
        if s_id != 'FEDFUNDS':
            data_dict[name] = series.pct_change(periods=12) * 100
        else:
            data_dict[name] = series # The interest rate is already a percentage

    # Combine into a single DataFrame and filter for recent history (e.g., since 2018)
    df = pd.DataFrame(data_dict).dropna().loc['2018-01-01':]

    # 3. Create the Visualization
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['CPI (Consumer Inflation)'], label='CPI (YoY %)', linewidth=2)
    plt.plot(df.index, df['PCE (Fed Target Inflation)'], label='PCE (YoY %)', linestyle='--')
    plt.plot(df.index, df['PPI (Producer Inflation)'], label='PPI (YoY %)', alpha=0.6)
    plt.step(df.index, df['Fed Funds Rate (FOMC)'], label='Fed Funds Rate', where='post', color='black', linewidth=2)

    # Formatting the chart
    plt.title('US Macro Indicators: Inflation vs. Fed Interest Rates', fontsize=14)
    plt.ylabel('Percentage (%)')
    plt.xlabel('Year')
    plt.legend()
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

# Run the function
fetch_and_plot_macro()