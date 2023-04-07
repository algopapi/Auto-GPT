import yfinance as yf

def get_current_price(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    ticker_info = ticker.info
    return ticker_info['regularMarketPrice']

sp500_current_price = get_current_price('^GSPC')
print('Current S&P 500 value:', sp500_current_price)