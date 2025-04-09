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
    return "The market is open"

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

# ✅ MCP 서버 실행
if __name__ == "__main__":
    logger.info(" MCP server start")
    mcp.run(transport="stdio")
