import datetime
import requests
import pandas as pd
#fraunhofer ISE energy charts public API


class MarketDataFetcher:
    """
    fetches real EPEX SPOT day-ahead electricity prices from Fraunhofer ISE.
    requires no API key for standard queries
    """
    BASE_URL = "https://api.energy-charts.info/price"

    def __init__(self, bidding_zone: str = "DE-LU"):
        #market bidding zone
        self.bzn = bidding_zone

    def get_day_ahead_prices(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        fetch day-ahead prices for a given date range (YYYY-MM-DD format)
        returns a DataFrame with timestamps and price in €/kWh
        """
        #query parameters for the REST GET request
        params = {
            "bzn": self.bzn, #zone code
            "start": start_date, #date filters
            "end": end_date
        }
        #send HTTP GET request
        response = requests.get(self.BASE_URL, params=params, timeout=10)
        response.raise_for_status() #check for success
        data = response.json() #parse the JSON response into a dict

        #extract unix epoch integer timestamps and convert them into UTC datetime objects
        timestamps = [
            datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            for ts in data["unix_seconds"]
        ]
        #extract corresponding prices
        prices_eur_mwh = data["price"]

    #making data dataframe matching timestamps to their prices
        df = pd.DataFrame({
            "timestamp_utc": timestamps,
            "price_eur_mwh": prices_eur_mwh
        })

        # #convert megawatt into kilowatt
        df["price_eur_kwh"] = df["price_eur_mwh"] / 1000.0
        
        # format and assign the UTC timestamp column as the primary dataframe datetimeindex
        df["datetime"] = pd.to_datetime(df["timestamp_utc"])
        df.set_index("datetime", inplace=True)
        return df


if __name__ == "__main__":
    fetcher = MarketDataFetcher(bidding_zone="DE-LU")
    
    # query the last 2 days of real grid data
    today = datetime.date.today()
    two_days_ago = today - datetime.timedelta(days=2)
    
    print(f"Fetching real market prices from {two_days_ago} to {today}...")
    df = fetcher.get_day_ahead_prices(
        start_date=two_days_ago.isoformat(),
        end_date=today.isoformat()
    )
    
    print("\n--- SAMPLE REAL MARKET DATA ---")
    print(df[["price_eur_mwh", "price_eur_kwh"]].head(10))
    print(f"\nPrice Summary (DE-LU):")
    print(f"Min: {df['price_eur_mwh'].min():.2f} €/MWh ({df['price_eur_kwh'].min():.4f} €/kWh)")
    print(f"Max: {df['price_eur_mwh'].max():.2f} €/MWh ({df['price_eur_kwh'].max():.4f} €/kWh)")
    print(f"Mean: {df['price_eur_mwh'].mean():.2f} €/MWh")