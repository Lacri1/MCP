import pandas as pd
from mcp.server.fastmcp import FastMCP
import logging
import yfinance as yf
from pykrx import stock
from datetime import datetime
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    stream=sys.stderr,
    encoding='utf-8',
    force=True
)
logger = logging.getLogger(__name__)

# MCP 서버 초기화
mcp = FastMCP("StocksMCPServer")

# KRX 주식 검색 함수
def search_krx_stock_by_name(name: str):
    try:
        stock_list = stock.get_market_ticker_list()

        # 코드로 직접 검색 시도
        if name in stock_list:
            stock_code = name
            stock_name = stock.get_market_ticker_name(stock_code)
        else:
            matching_stocks = {
                code: stock.get_market_ticker_name(code)
                for code in stock_list if name in stock.get_market_ticker_name(code)
            }

            if not matching_stocks:
                logger.warning(f"No matching stocks found for '{name}'")
                return None

            stock_code = list(matching_stocks.keys())[0]
            stock_name = matching_stocks[stock_code]

        today = datetime.today().strftime('%Y%m%d')
        df = stock.get_market_ohlcv_by_date(today, today, stock_code)

        if df.empty:
            logger.warning(f"No data found for stock code: {stock_code}")
            return None

        last_price = df.iloc[0]['종가']
        volume = df.iloc[0]['거래량']

        return {
            "name": stock_name,
            "price": last_price,
            "volume": volume,
            "code": stock_code
        }

    except Exception as e:
        logger.error(f"Error occurred while searching stock '{name}': {e}")
        return None


# 1. 주식 시장 상태
@mcp.resource("market://state")
def get_market_state() -> str:
    try:
        indices = {
            "S&P 500": "^GSPC",
            "NASDAQ": "^IXIC",
            "KOSPI": "^KS11",
            "KOSDAQ": "^KQ11",
            "Nikkei 225": "^N225"
        }

        fx_rates = {
            "USD/KRW": "USDKRW=X",
            "JPY/KRW": "JPYKRW=X"
        }

        response = "[🌐 Global Market Snapshot]\n\n📊 주요 지수:\n"

        for name, symbol in indices.items():
            data = yf.Ticker(symbol)
            price = data.info.get("regularMarketPrice", "N/A")
            response += f"- {name}: {price}\n"

        response += "\n💱 환율:\n"
        for name, symbol in fx_rates.items():
            data = yf.Ticker(symbol)
            rate = data.info.get("regularMarketPrice", "N/A")

            if name == "JPY/KRW" and isinstance(rate, (int, float)):
                rate_100 = rate * 100
                response += f"- 100 JPY/KRW: {rate_100:.2f}\n"
            else:
                response += f"- {name}: {rate}\n"

        return response.strip()

    except Exception as e:
        logger.error(f"Error fetching market snapshot: {e}")
        return "시장 정보를 가져오는 데 실패했습니다."


# 2-1. 미국 주식 가격 조회
@mcp.tool("get_stock_price")
def get_stock_price(symbol: str) -> str:
    try:
        logger.info(f"yfinance stock : {symbol}")
        stock_data = yf.Ticker(symbol)
        price = stock_data.info.get("regularMarketPrice")
        if price is None:
            return f"주식 기호 {symbol}에 대한 가격을 가져올 수 없습니다."
        return f"{symbol}의 현재 주가는 ${price}입니다."
    except Exception as e:
        logger.error(f"Error fetching stock price for {symbol}: {e}")
        return f"{symbol}의 주식 가격을 가져오는 데 실패했습니다."

# 2-2. 한국 주식 가격 조회
@mcp.tool("get_krx_price")
def get_krx_price(symbol: str) -> str:
    try:
        symbol = symbol.strip()
        logger.info(f"krx stock : {symbol}")
        stock_info = search_krx_stock_by_name(symbol)
        if stock_info is None:
            return f"한국 종목명 '{symbol}'을(를) 찾을 수 없습니다."

        price = stock_info.get("price")
        if price is None:
            return f"한국 종목 '{symbol}'에 대한 가격 정보를 가져올 수 없습니다."

        return f"{symbol}의 현재 주가는 {price}원입니다."
    except Exception as e:
        logger.error(f"Error fetching KRX stock price for {symbol}: {e}")
        return f"{symbol}의 주식 가격을 가져오는 데 실패했습니다."

# 3. 주식 분석 기능
@mcp.tool()
def analyze_stock(symbol: str, last_years_profit: str = "", company_info: str = "") -> str:
    try:
        if symbol.isascii():
            stock_data = yf.Ticker(symbol)
            info = stock_data.info
            financials = stock_data.financials

            revenue = financials.loc["Total Revenue"].iloc[0] if "Total Revenue" in financials.index else "N/A"
            gross_profit = financials.loc["Gross Profit"].iloc[0] if "Gross Profit" in financials.index else "N/A"
            net_income = financials.loc["Net Income"].iloc[0] if "Net Income" in financials.index else "N/A"

            company_summary = info.get("longBusinessSummary", "회사 정보가 없습니다.")

            return f"""
[{symbol}의 주식 분석]

회사 정보:
{company_summary}

재무 정보:
- 수익 (지난해): {revenue}
- 총 이익: {gross_profit}
- 순이익: {net_income}

추천:
재무 데이터와 회사 정보를 바탕으로 주식을 매수, 매도 또는 보유할지를 결정하십시오.
"""
        else:
            logger.info(f"KRX 종목 분석: {symbol}")
            stock_info = search_krx_stock_by_name(symbol)
            if stock_info is None:
                return f" 한국 종목명 '{symbol}'을(를) 찾을 수 없습니다."

            return f"""
[KRX 종목 분석: {symbol}] 

종목명: {stock_info['name']}
종가: {stock_info['price']}원
거래량: {stock_info['volume']}
종목코드: {stock_info['code']}

추천:
이 기본 데이터를 바탕으로 추가적인 재무 분석이나 차트 패턴을 고려해 보세요.
"""
    except Exception as e:
        logger.error(f"주식 분석 중 오류 발생 {symbol}: {e}")
        return f"{symbol}의 주식 분석에 실패했습니다."


# 4. 주가 5영업일 추이
@mcp.tool("get_stock_history")
def get_stock_history(symbol: str, period: str = "1mo") -> str:
    try:
        stock_data = yf.Ticker(symbol)
        hist = stock_data.history(period=period)

        if hist.empty:
            return f"{symbol}의 과거 주가 데이터를 찾을 수 없습니다."

        prices = hist['Close'].tail(5).round(2)
        price_info = "\n".join([f"{date.date()}: ${price}" for date, price in prices.items()])
        return f"[{symbol}] 최근 {period}의 주가 추이:\n{price_info}"
    except Exception as e:
        logger.error(f"Error fetching stock history for {symbol}: {e}")
        return f"{symbol}의 주가 히스토리 조회에 실패했습니다."


# 5. 종목 세부 지표 출력
@mcp.tool("get_stock_indicators")
def get_stock_indicators(symbol: str) -> str:
    try:
        info = yf.Ticker(symbol).info

        pe = info.get("trailingPE", "N/A")
        pb = info.get("priceToBook", "N/A")
        eps = info.get("trailingEps", "N/A")

        market_cap = info.get("marketCap", "N/A")
        high_52 = info.get("fiftyTwoWeekHigh", "N/A")
        low_52 = info.get("fiftyTwoWeekLow", "N/A")
        avg_volume = info.get("averageVolume", "N/A")

        dividend_rate = info.get("dividendRate", "N/A")
        dividend_yield = info.get("dividendYield", "N/A")

        roa = info.get("returnOnAssets", "N/A")
        roe = info.get("returnOnEquity", "N/A")
        ebitda = info.get("ebitda", "N/A")
        operating_margin = info.get("operatingMargins", "N/A")

        short_ratio = info.get("shortRatio", "N/A")

        return f"""
[{symbol}] 주요 지표:

💰 밸류에이션
- PER (주가수익비율): {pe}
- PBR (주가순자산비율): {pb}
- EPS (주당순이익): {eps}
- 시가총액: {market_cap:,} USD

📈 주가 데이터
- 52주 최고가: {high_52}
- 52주 최저가: {low_52}
- 평균 거래량: {avg_volume:,}

💸 배당 정보
- 배당금: {dividend_rate}
- 배당수익률: {dividend_yield}

📊 수익성 지표
- ROA (총자산수익률): {roa}
- ROE (자기자본수익률): {roe}
- EBITDA: {ebitda}
- 영업이익률: {operating_margin}

📉 시장 포지션
- 공매도 비율: {short_ratio}
""".strip()

    except Exception as e:
        logger.error(f"Error fetching indicators for {symbol}: {e}")
        return f"{symbol}의 지표 조회에 실패했습니다."


# 6. 지수/환율의 기간별 종가 & 변화 추이 제공
@mcp.tool("get_market_trend")
def get_market_trend(ticker: str, start_date: str, end_date: str) -> str:
    """
    지정된 ticker에 대해 start_date ~ end_date 동안의 일별 종가 및 추이를 반환합니다.
    날짜는 'YYYY-MM-DD' 형식이어야 합니다.
    """
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        if df.empty:
            return f"{ticker}에 대한 {start_date}~{end_date} 기간의 데이터를 찾을 수 없습니다."

        # 'Close' 또는 'Adj Close' 컬럼을 안전하게 가져옴
        close_col = None
        for col in ["Close", "Adj Close"]:
            if col in df.columns:
                close_col = col
                break

        if close_col is None:
            return f"{ticker} 데이터에 'Close' 혹은 'Adj Close' 컬럼이 없습니다."

        closes = df[close_col]
        if isinstance(closes, pd.DataFrame):
            closes = closes.iloc[:, 0]  # 혹시 MultiIndex일 경우 대비

        closes = closes.dropna()

        if closes.empty:
            return f"{ticker}의 {start_date}~{end_date} 기간에는 유효한 종가 데이터가 없습니다."

        trend_lines = []
        for date in closes.index:
            price = closes.loc[date]
            if hasattr(date, "strftime"):
                date_str = date.strftime("%Y-%m-%d")
            else:
                date_str = str(date)
            trend_lines.append(f"{date_str}: {float(price):.2f}")  # ⭐ float으로 강제 변환

        start_price = float(closes.iloc[0])
        end_price = float(closes.iloc[-1])
        change = end_price - start_price
        change_pct = (change / start_price) * 100
        direction = "상승📈" if change > 0 else "하락📉" if change < 0 else "변동 없음"

        return f"""
[{ticker} 기간별 종가: {start_date} ~ {end_date}]

{chr(10).join(trend_lines)}

📊 기간 변화:
- 시작가: {start_price:.2f}
- 종료가: {end_price:.2f}
- 변동: {change:.2f} ({change_pct:.2f}%) → {direction}
        """.strip()

    except Exception as e:
        logger.error(f"Error fetching trend for {ticker} from {start_date} to {end_date}: {e}")
        return f"{ticker}에 대한 기간별 데이터 조회 실패: {e}"



# ✅ MCP 서버 실행
if __name__ == "__main__":
    logger.info(" MCP server start")
    mcp.run(transport="stdio")
