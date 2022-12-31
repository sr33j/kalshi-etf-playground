import os
from engine import download_all_kalshi_market_info

def main():
    print("making missing folders and files...")
    ## if cache folder doesn't exist, create it
    if not os.path.exists("cache"):
        os.mkdir("cache")

    ## if price_data folder doesn't exist in cache, create it
    if not os.path.exists("cache/price_data"):
        os.mkdir("cache/price_data")
    
    ## if etfs_created.csv doesn't exist, create it
    if not os.path.exists("cache/etfs_created.csv"):
        with open("cache/etfs_created.csv", "w") as f:
            f.write("ticker,user,expression")
    
    ## if full_market_data.csv doesn't exist, create it
    if not os.path.exists("cache/full_market_data.csv"):
        print("downloading all kalshi market info...")
        download_all_kalshi_market_info()
        
if __name__ == '__main__':
    main()