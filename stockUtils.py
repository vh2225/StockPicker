import json
import re
import urllib
import urllib.request
from collections import OrderedDict
from time import sleep
from urllib.request import urlopen

import requests
import urllib3
from lxml import html

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

regexMask = {
    'price Book Ratio': 'Price\/Book.*?data\-reactid.*?>(\d+\.\d*)</td>',
    'PEG Ratio 5y': 'PEG\sRatio.*?data\-reactid.*?>(\d+\.\d*)</td>'
}


def yahooRequest(stock):
    try:
        url = "https://finance.yahoo.com/quote/{}/key-statistics?ltr=1".format(stock)
        # print("url: " + url)
        response = urllib.request.urlopen(url)
        html = str(response.read())
        return html

    except Exception as e:
        print("failed in the main loop of yahooKeyStats" + str(e))


def yahooStats(html, stat):
    try:
        # statVal = re.search(regexMask[stat] + '.*?data\-reactid.*?>(\d+\.\d*)</td>', html).group(1)
        statVal = re.search(regexMask[stat], html).group(1)
        return statVal

    except Exception as e:
        print("failed in the main loop of yahooKeyStats" + str(e))


def getStatsFromYahoo(ticker):
    url = "http://finance.yahoo.com/quote/%s?p=%s" % (ticker, ticker)
    response = requests.get(url, verify=False)
    # print("Parsing %s" % (url))
    sleep(4)
    parser = html.fromstring(response.text)
    summary_table = parser.xpath('//div[contains(@data-test,"summary-table")]//tr')
    summary_data = dict()
    other_details_json_link = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{0}?formatted=true&lang=en-US&region=US&modules=summaryProfile%2CfinancialData%2CrecommendationTrend%2CupgradeDowngradeHistory%2Cearnings%2CdefaultKeyStatistics%2CcalendarEvents&corsDomain=finance.yahoo.com".format(
        ticker)
    summary_json_response = requests.get(other_details_json_link)
    try:
        json_loaded_summary = json.loads(summary_json_response.text)
        y_Target_Est = json_loaded_summary["quoteSummary"]["result"][0]["financialData"]["targetMeanPrice"]['raw']
        earnings_list = json_loaded_summary["quoteSummary"]["result"][0]["calendarEvents"]['earnings']
        eps = json_loaded_summary["quoteSummary"]["result"][0]["defaultKeyStatistics"]["trailingEps"]['raw']
        datelist = []
        for i in earnings_list['earningsDate']:
            datelist.append(i['fmt'])
        earnings_date = ' to '.join(datelist)
        for table_data in summary_table:
            raw_table_key = table_data.xpath('.//td[contains(@class,"C(black)")]//text()')
            raw_table_value = table_data.xpath('.//td[contains(@class,"Ta(end)")]//text()')
            table_key = ''.join(raw_table_key).strip()
            table_value = ''.join(raw_table_value).strip()
            summary_data.update({table_key: table_value})
        summary_data.update(
            {"1y Target Est": y_Target_Est, "EPS (TTM)": eps, "Earnings Date": earnings_date, "url": url})
        return summary_data
    except Exception as e:
        print("Failed to parse json response in getStatsFromYahoo: " + str(e))
        return {"error": "Failed to parse json response in getStatsFromYahoo" + str(e)}


# TODO: 1. extra filter: filter out the set with the following parameters:
#       PE 5y < 20
#       Growth rate: revenue, EPS, or net income >= 5-6%
#       margin of safety > 30%
#

# TODO: 2. report: email the ticker with the following parameters:
#         - Symbol
#         - Name
#         - Exchange
#         - Price & Value: EV, Price & Market cap -> (analyst) target price, price expected growth, STM reversal, LTM reversal
#         - 52w low/high
#         - Valuation ratios (intrinsic Val): all price/IV val% dif, margin of safety
#         - Valuation ratios (yield): price/eps (b, 5y), PEG Ratio
#         - Valuation ratios (Balance): price/book
#         - Liquidity ratios: current ratio
#         - Solvency ratios: LT Debt/Equity, Net debt/equity, FCF/LT Debt
#         - Shares: held by insiders, held by institutions
#         - Income: dividend (per share, 1y growth, 5y CAGR)
def getStatsFromFMPrep(ticker):
    summary_data = dict()
    try:
        # get general info
        url = "https://financialmodelingprep.com/api/v3/company/profile/{}".format(ticker)
        data = get_jsonparsed_data(url)
        if "profile" in data:
            summary_data.update(data["profile"])
            summary_data.pop("image")
            summary_data.pop("website")
            summary_data.pop("description")
            summary_data.pop("ceo")
        # get metrics - this would replace yahoo
        url = "https://financialmodelingprep.com/api/v3/company-key-metrics/{}".format(ticker)
        data = get_jsonparsed_data(url)
        if "metrics" in data:
            summary_data.update({"EV": data["metrics"][0]["Enterprise Value"]})
            summary_data.update({"PE": data["metrics"][0]["PE ratio"]})
            summary_data.update({"PB": data["metrics"][0]["PB ratio"]})
            summary_data.update({"EV to FCF": data["metrics"][0]["EV to Free cash flow"]})
            summary_data.update({"Debt to Equity": data["metrics"][0]["Debt to Equity"]})
            summary_data.update({"Debt to Assets": data["metrics"][0]["Debt to Assets"]})
            summary_data.update({"Current ratio": data["metrics"][0]["Current ratio"]})
            summary_data.update({"Dividend Yield": data["metrics"][0]["Dividend Yield"]})
            summary_data.update({"Graham Number": data["metrics"][0]["Graham Number"]})
            summary_data.update({"Graham Net-Net": data["metrics"][0]["Graham Net-Net"]})
        # get ratings
        url = "https://financialmodelingprep.com/api/v3/company/rating/{}".format(ticker)
        data = get_jsonparsed_data(url)
        if "rating" in data:
            summary_data.update(data["rating"])
        # get intrinsic val
        url = "https://financialmodelingprep.com/api/v3/company/discounted-cash-flow/{}".format(ticker)
        data = get_jsonparsed_data(url)
        if "dcf" in data:
            try:
                if ("price" not in summary_data or summary_data.get("price") == 0) and "Stock Price" in data:
                    summary_data.update({"price": float(data.get("Stock Price"))})
                price = summary_data.get("price")
            except Exception as e:
                print("float casting exception fot price: " + ticker + " : " + str(e))
                price = 0
            dcf = data.get("dcf")
            summary_data.update({"DCF": dcf})
            marginOS = "{0:.2f}".format((float(summary_data.get("DCF")) - price)
                                        * 100 / price) + "%" if price != 0 else "N/A"

            summary_data.update({"margin of safety": marginOS})
        # get cap rate
        url = "https://financialmodelingprep.com/api/v3/financials/income-statement/{}".format(ticker)
        data = get_jsonparsed_data(url)
        if "financials" in data and data["financials"][0] and data["financials"][0]["Net Income"]:
            netIncome = data["financials"][0]["Net Income"]
            try:
                mktCap = float(summary_data.get("mktCap")) if "mktCap" in summary_data else 0
            except Exception as e:
                print("float casting exception fot mktCap: " + ticker + " : " + str(e))
                mktCap = 0
            capRate = "{0:.2f}".format((float(netIncome) * 100) / mktCap) + "%" if mktCap != 0 else "N/A"
            summary_data.update({"capRate": capRate})
        # get growth rates:
        url = "https://financialmodelingprep.com/api/v3/financial-statement-growth/{}".format(ticker)
        data = get_jsonparsed_data(url)
        if "growth" in data and data["growth"][0]:
            summary_data.update({"EPS Growth": data["growth"][0]["EPS Growth"]})
            summary_data.update({"EPS Diluted Growth": data["growth"][0]["EPS Diluted Growth"]})
            summary_data.update({"10Y CF Growth": data["growth"][0]["10Y Operating CF Growth (per Share)"]})
            summary_data.update({"5Y CF Growth": data["growth"][0]["5Y Operating CF Growth (per Share)"]})
            summary_data.update({"3Y CF Growth": data["growth"][0]["3Y Operating CF Growth (per Share)"]})
            summary_data.update({"Debt Growth": data["growth"][0]["Debt Growth"]})

        # get FCF
        url = "https://www.gurufocus.com/term/total_freecashflow/{}/Free%252BCash%252BFlow".format(ticker)
        response = requests.get(url, verify=False)
        sleep(4)
        parser = html.fromstring(response.content)
        try:
            price = summary_data.get("price")
            fcfps = float(parser.xpath('//div[@id="target_def_description" and @class=""]/p[2]/strong[5]/text()')[0][1:].replace(',', ''))
            tenCap = fcfps * 10
            discountNeeded = 1 - (tenCap/price)
        except Exception as e:
            print("cannot process tenCap price: " + ticker + " : " + str(e))
            tenCap = "N/A"
            discountNeeded = "N/A"
        summary_data.update({"10 CAP price": tenCap})
        summary_data.update({"Discount Needed": discountNeeded})

        # get guru URL:
        summary_data.update({"Guru Summary": "https://www.gurufocus.com/stock/{}/summary".format(ticker)})

        # # get EP rate
        # if "PE ratio" in summary_data:
        #     try:
        #         peRate = float(summary_data.get("PE ratio"))
        #     except Exception as e:
        #         print("float casting exception for peRate: " + ticker + " : " + str(e))
        #         peRate = 0
        #     epRate = "{0:.2f}".format(100.0 / peRate) + "%" if peRate != 0 else "N/A"
        #     summary_data.update({"EP Rate": epRate})

        return summary_data
    except Exception as e:
        print("Failed to parse json response in getStatsFromFMPrep: " + str(e))
        return {"error": "Failed to parse json response in getStatsFromFMPrep" + str(e)}


def getStat(ticker):
    summary_data = dict()
    summary_data.update({"ticker": ticker})
    # summary_data.update(getStatsFromYahoo(ticker))
    summary_data.update(getStatsFromFMPrep(ticker))
    return OrderedDict(sorted(summary_data.items()))


def get_jsonparsed_data(url):
    """
    Receive the content of ``url``, parse it as JSON and return the object.

    Parameters
    ----------
    url : str

    Returns
    -------
    dict
    """
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)


def getStockFromFinviz():
    try:
        stockSet = set()
        page = 0;
        while True:
            # url = "https://finviz.com/screener.ashx?v=111&f=cap_smallover,fa_curratio_o1.5,fa_ltdebteq_u0.3,fa_pb_u2,fa_pe_u20,sh_insiderown_o10&ft=4&o=ticker&r={}".format(
            #     str(page * 20 + 1))
            # url = "https://finviz.com/screener.ashx?v=111&f=cap_largeover,fa_curratio_o1.5,fa_ltdebteq_u0.5,fa_pb_u3,fa_pe_u20&o=ticker&r={}".format(
            #     str(page * 20 + 1))
            url = "https://finviz.com/screener.ashx?v=111&f=cap_midover,fa_debteq_u0.5,fa_eps5years_pos,fa_ltdebteq_u0.3,fa_pb_u2,fa_pe_u10,fa_pfcf_low&ft=2&o=ticker&r={}".format(
                str(page * 20 + 1))
            page += 1
            # print("url: " + url)
            response = urllib.request.urlopen(url)
            html = str(response.read())
            # print(html)
            regex = 'href=\"quote\.ashx\?t=([a-zA-Z]+)\&ty=c&p=d&b=1\" class=\"screener-link-primary'
            stocks = re.findall(regex, html)
            # print(stocks)
            if any(stock in stockSet for stock in stocks):
                break
            stockSet.update(stocks)

        return stockSet

    except Exception as e:
        print("failed in the main loop of finviz" + str(e))
