# Copyright (c) 2013 Alan McIntyre

import httplib
import json
import decimal
import re

class InvalidTradePairException(Exception):
    ''' Exception raised when an invalid pair is passed. '''
    pass

class InvalidTradeTypeException(Exception):
    ''' Exception raise when invalid trade type is passed. '''
    pass

class InvalidTradeAmountException(Exception):
    ''' Exception raised if trade amount is too much or too little. '''
    pass

decimal.getcontext().rounding = decimal.ROUND_DOWN
exps = [decimal.Decimal("1e-%d" % i) for i in range(16)]

btce_domain = "btc-e.com"

all_currencies = ("btc", "usd", "rur", "ltc", "nmc", "eur", "nvc",
                  "ppc", "cnh", "gbp")
all_pairs = ("btc_usd", "btc_rur", "btc_eur", "btc_cnh", "btc_gbp",
             "ltc_btc", "ltc_usd", "ltc_rur", "ltc_eur", "ltc_cnh",
             "ltc_gbp", "nmc_btc", "nmc_usd", "nvc_btc", "nvc_usd",
             "usd_rur", "usd_cnh", "eur_usd", "eur_rur", "gbp_usd",
             "ppc_btc", "ppc_usd")

max_digits = {"btc_usd": 3,
              "btc_rur": 5,
              "btc_eur": 5,
              "btc_cnh": 2,
              "btc_gbp": 5,
              "ltc_btc": 5,
              "ltc_usd": 6,
              "ltc_rur": 5,
              "ltc_eur": 3,
              "ltc_cnh": 2,
              "ltc_gbp": 3,
              "nmc_btc": 5,
              "nmc_usd": 3,
              "nvc_btc": 5,
              "nvc_usd": 3,
              "usd_rur": 5,
              "eur_usd": 5,
              "eur_rur": 5,
              "usd_cnh": 4,
              "gbp_usd": 4,
              "ppc_btc": 5,
              "ppc_usd": 3}

min_orders = {"btc_usd": decimal.Decimal("0.01"),
              "btc_rur": decimal.Decimal("0.01"),
              "btc_eur": decimal.Decimal("0.01"),
              "btc_cnh": decimal.Decimal("0.01"),
              "btc_gbp": decimal.Decimal("0.01"),
              "ltc_btc": decimal.Decimal("0.1"),
              "ltc_usd": decimal.Decimal("0.1"),
              "ltc_rur": decimal.Decimal("0.1"),
              "ltc_eur": decimal.Decimal("0.1"),
              "ltc_cnh": decimal.Decimal("0.1"),
              "ltc_gbp": decimal.Decimal("0.1"),
              "nmc_btc": decimal.Decimal("0.1"),
              "nmc_usd": decimal.Decimal("0.1"),
              "nvc_btc": decimal.Decimal("0.1"),
              "nvc_usd": decimal.Decimal("0.1"),
              "usd_rur": decimal.Decimal("0.1"),
              "eur_usd": decimal.Decimal("0.1"),
              "eur_rur": decimal.Decimal("0.1"),
              "usd_cnh": decimal.Decimal("0.1"),
              "gbp_usd": decimal.Decimal("0.1"),
              "ppc_btc": decimal.Decimal("0.1"),
              "ppc_usd": decimal.Decimal("0.1")}


def parseJSONResponse(response):
    def parse_decimal(var):
        return decimal.Decimal(var)

    try:
        r = json.loads(response, parse_float=parse_decimal,
                       parse_int=parse_decimal)
    except Exception as e:
        msg = "Error while attempting to parse JSON response:"\
              " %s\nResponse:\n%r" % (e, response)
        raise Exception(msg)

    return r

HEADER_COOKIE_RE = re.compile(r'__cfduid=([a-f0-9]{46})')
BODY_COOKIE_RE = re.compile(r'document\.cookie="a=([a-f0-9]{32});path=/;";')

class BTCEConnection:
    def __init__(self, timeout=30):
        self._timeout = timeout
        self.setup_connection()

    def setup_connection(self):
        self.conn = httplib.HTTPSConnection(btce_domain, timeout=self._timeout)
        self.cookie = None

    def close(self):
        self.conn.close()

    def getCookie(self):
        self.cookie = ""

        try:
            self.conn.request("GET", '/')
            response = self.conn.getresponse()
        except Exception:
            # reset connection so it doesn't stay in a weird state if we catch
            # the error in some other place
            self.conn.close()
            self.setup_connection()
            raise

        setCookieHeader = response.getheader("Set-Cookie")
        match = HEADER_COOKIE_RE.search(setCookieHeader)
        if match:
            self.cookie = "__cfduid=" + match.group(1)

        match = BODY_COOKIE_RE.search(response.read())
        if match:
            if self.cookie != "":
                self.cookie += '; '
            self.cookie += "a=" + match.group(1)

    def makeRequest(self, url, extra_headers=None, params="", with_cookie=False):
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        if extra_headers is not None:
            headers.update(extra_headers)

        if with_cookie:
            if self.cookie is None:
                self.getCookie()

            headers.update({"Cookie": self.cookie})
        try:
            self.conn.request("POST", url, params, headers)
        finally:
            response = self.conn.getresponse().read()

        return response

    def makeJSONRequest(self, url, extra_headers=None, params=""):
        response = self.makeRequest(url, extra_headers, params)
        return parseJSONResponse(response)


def validatePair(pair):
    if pair not in all_pairs:
        if "_" in pair:
            a, b = pair.split("_", 1)
            swapped_pair = "%s_%s" % (b, a)
            if swapped_pair in all_pairs:
                msg = "Unrecognized pair: %r (did you mean %s?)"
                msg = msg % (pair, swapped_pair)
                raise InvalidTradePairException(msg)
        raise InvalidTradePairException("Unrecognized pair: %r" % pair)


def validateOrder(pair, trade_type, rate, amount):
    validatePair(pair)
    if trade_type not in ("buy", "sell"):
        raise InvalidTradeTypeException("Unrecognized trade type: %r" % trade_type)

    minimum_amount = min_orders[pair]
    formatted_min_amount = formatCurrency(minimum_amount, pair)
    if amount < minimum_amount:
        msg = "Trade amount %r is too small, it should be >= %s" % (amount,formatted_min_amount)
        raise InvalidTradeAmountException(msg)


def truncateAmountDigits(value, digits):
    quantum = exps[digits]
    if type(value) is float:
        value = str(value)
    if type(value) is str:
        value = decimal.Decimal(value)
    return value.quantize(quantum)


def truncateAmount(value, pair):
    return truncateAmountDigits(value, max_digits[pair])


def formatCurrencyDigits(value, digits):
    s = str(truncateAmountDigits(value, digits))
    dot = s.index(".")
    while s[-1] == "0" and len(s) > dot + 2:
        s = s[:-1]

    return s


def formatCurrency(value, pair):
    return formatCurrencyDigits(value, max_digits[pair])
