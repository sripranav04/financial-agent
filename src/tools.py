"""
tools.py
--------
Defines the tools available to our financial agent.

WHY TOOLS MATTER IN AGENTIC AI:
  Without tools, an LLM just generates text from memory.
  With tools, it can fetch REAL data, do REAL calculations,
  and take REAL actions. This is what makes it "agentic."

  The agent decides: "I need stock data → I'll call get_stock_info"
  Then it gets the result and reasons about it. That loop is ReAct.

HOW LANGGRAPH USES THESE:
  We decorate functions with @tool so LangGraph knows:
  - The tool's name
  - What it does (from the docstring)
  - What arguments it takes (from type hints)
  Claude reads the docstring to decide WHEN to use each tool.
"""

import yfinance as yf
import pandas as pd
from langchain_core.tools import tool
from datetime import datetime


@tool
def get_stock_price(ticker: str) -> str:
    """
    Fetch the current stock price and key stats for a given ticker symbol.
    Use this when you need to know the current price of a stock.

    Args:
        ticker: Stock ticker symbol e.g. 'AAPL', 'MSFT', 'TSLA'

    Returns:
        A formatted string with current price and key metrics
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # Pull key fields — not all tickers have all fields
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
        prev_close = info.get("previousClose", "N/A")
        day_high = info.get("dayHigh", "N/A")
        day_low = info.get("dayLow", "N/A")
        volume = info.get("volume", "N/A")
        market_cap = info.get("marketCap", "N/A")
        company_name = info.get("longName", ticker.upper())

        # Calculate daily change if possible
        if isinstance(current_price, (int, float)) and isinstance(prev_close, (int, float)):
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            change_str = f"{change:+.2f} ({change_pct:+.2f}%)"
        else:
            change_str = "N/A"

        return f"""
📊 {company_name} ({ticker.upper()})
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Current Price:  ${current_price}
Daily Change:   {change_str}
Day High:       ${day_high}
Day Low:        ${day_low}
Prev Close:     ${prev_close}
Volume:         {volume:,} shares
Market Cap:     ${market_cap:,}
Fetched at:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    except Exception as e:
        return f"Error fetching price for {ticker}: {str(e)}"


@tool
def get_stock_history(ticker: str, period: str = "1mo") -> str:
    """
    Fetch historical price data for a stock to analyze trends.
    Use this to understand price movement over time before making decisions.

    Args:
        ticker: Stock ticker symbol e.g. 'AAPL', 'MSFT'
        period: Time period - options: '5d', '1mo', '3mo', '6mo', '1y'

    Returns:
        A summary of historical performance including highs, lows, and trend
    """
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)

        if hist.empty:
            return f"No historical data found for {ticker}"

        # Calculate key stats from the history
        start_price = hist["Close"].iloc[0]
        end_price = hist["Close"].iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100
        period_high = hist["High"].max()
        period_low = hist["Low"].min()
        avg_volume = hist["Volume"].mean()
        volatility = hist["Close"].pct_change().std() * 100  # daily std dev

        # Simple trend: compare first half avg vs second half avg
        mid = len(hist) // 2
        first_half_avg = hist["Close"].iloc[:mid].mean()
        second_half_avg = hist["Close"].iloc[mid:].mean()
        trend = "📈 Upward" if second_half_avg > first_half_avg else "📉 Downward"

        # Last 5 days closing prices for context
        last_5 = hist["Close"].tail(5)
        last_5_str = "\n".join(
            [f"  {date.strftime('%Y-%m-%d')}: ${price:.2f}"
             for date, price in last_5.items()]
        )

        return f"""
📈 {ticker.upper()} Historical Analysis ({period})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Period Return:    {total_return:+.2f}%
Period High:      ${period_high:.2f}
Period Low:       ${period_low:.2f}
Start Price:      ${start_price:.2f}
End Price:        ${end_price:.2f}
Avg Daily Volume: {avg_volume:,.0f}
Daily Volatility: {volatility:.2f}%
Overall Trend:    {trend}

Last 5 Trading Days:
{last_5_str}
"""
    except Exception as e:
        return f"Error fetching history for {ticker}: {str(e)}"


@tool
def compare_stocks(tickers: str) -> str:
    """
    Compare multiple stocks side by side to help decide between investment options.
    Use this when the user wants to compare several stocks against each other.

    Args:
        tickers: Comma-separated ticker symbols e.g. 'AAPL,MSFT,GOOGL'

    Returns:
        A side-by-side comparison of key metrics for all stocks
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        results = []

        for ticker in ticker_list:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1mo")

            if hist.empty:
                continue

            price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            prev_close = info.get("previousClose", price)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            monthly_return = ((hist["Close"].iloc[-1] - hist["Close"].iloc[0])
                              / hist["Close"].iloc[0] * 100) if not hist.empty else 0
            pe_ratio = info.get("trailingPE", "N/A")
            week_52_high = info.get("fiftyTwoWeekHigh", "N/A")
            week_52_low = info.get("fiftyTwoWeekLow", "N/A")

            results.append({
                "Ticker": ticker,
                "Price": f"${price:.2f}",
                "Today": f"{change_pct:+.2f}%",
                "1M Return": f"{monthly_return:+.2f}%",
                "P/E Ratio": pe_ratio,
                "52W High": f"${week_52_high}" if isinstance(week_52_high, float) else week_52_high,
                "52W Low": f"${week_52_low}" if isinstance(week_52_low, float) else week_52_low,
            })

        if not results:
            return "Could not fetch data for any of the provided tickers."

        # Format as a readable table
        df = pd.DataFrame(results).set_index("Ticker")
        return f"\n📊 Stock Comparison\n{'━'*50}\n{df.to_string()}\n"

    except Exception as e:
        return f"Error comparing stocks: {str(e)}"


@tool
def get_analyst_recommendation(ticker: str) -> str:
    """
    Get analyst recommendations and price targets for a stock.
    Use this to understand what professional analysts think about a stock.

    Args:
        ticker: Stock ticker symbol e.g. 'AAPL'

    Returns:
        Analyst consensus, price target, and recommendation breakdown
    """
    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        recommendation = info.get("recommendationKey", "N/A").upper()
        target_price = info.get("targetMeanPrice", "N/A")
        target_high = info.get("targetHighPrice", "N/A")
        target_low = info.get("targetLowPrice", "N/A")
        num_analysts = info.get("numberOfAnalystOpinions", "N/A")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")

        # Calculate upside potential
        if isinstance(target_price, (int, float)) and isinstance(current_price, (int, float)):
            upside = ((target_price - current_price) / current_price) * 100
            upside_str = f"{upside:+.2f}%"
        else:
            upside_str = "N/A"

        return f"""
🎯 {ticker.upper()} Analyst Recommendations
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Consensus:       {recommendation}
# of Analysts:   {num_analysts}
Current Price:   ${current_price}
Mean Target:     ${target_price}
High Target:     ${target_high}
Low Target:      ${target_low}
Upside Potential:{upside_str}
"""
    except Exception as e:
        return f"Error fetching recommendations for {ticker}: {str(e)}"


# Collect all tools in one list — imported by agent.py
# WHY: agent.py just does `from tools import TOOLS` cleanly
TOOLS = [
    get_stock_price,
    get_stock_history,
    compare_stocks,
    get_analyst_recommendation,
]