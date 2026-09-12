"""
Currency Converter - free API se kisi bhi currency ko PKR mein convert karta hai
Uses @fawazahmed0/currency-api (free, no key, supports 150+ currencies including PKR)

Note: Kuch hosting platforms (jaise PythonAnywhere free tier) sirf specific
"whitelisted" domains ko access karne dete hain. Agar live API blocked ho,
ye code ek approximate FALLBACK rate table use karta hai taake total kabhi
0/khali na dikhe - sirf thora kam accurate ho sakta hai.
"""

import requests

# Simple cache taake baar baar same currency ke liye API call na karni pare
_rate_cache = {}

# Fallback rates (approximate, agar live API access na ho - jaise restricted hosting par)
# In rates ko occasionally manually update kar sakte hain
FALLBACK_RATES_TO_PKR = {
    "usd": 285.0,
    "eur": 300.0,
    "gbp": 350.0,
    "inr": 3.3,
    "aed": 77.5,
    "sar": 76.0,
    "cad": 205.0,
    "aud": 185.0,
    "cny": 39.5,
    "pkr": 1.0,
}


def get_pkr_rate(from_currency):
    """
    Ek currency (jaise 'USD') ke liye PKR conversion rate nikalta hai.
    Pehle live API try karta hai, agar wo blocked/fail ho to fallback rate use karta hai.
    Return: rate (float) ya None agar dono fail ho jayein.
    """
    if not from_currency:
        return None

    from_currency = from_currency.lower().strip()

    if from_currency == "pkr":
        return 1.0

    if from_currency in _rate_cache:
        return _rate_cache[from_currency]

    # --- Pehle live API try karo ---
    try:
        response = requests.get(
            f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{from_currency}.json",
            timeout=5
        )
        data = response.json()

        if from_currency in data and "pkr" in data[from_currency]:
            rate = data[from_currency]["pkr"]
            _rate_cache[from_currency] = rate
            return rate
    except Exception as e:
        print(f"⚠️ Live currency API unavailable ({from_currency}): {e}. Fallback rate use kar raha hoon.")

    # --- Live API fail ho gayi to fallback rate use karo ---
    if from_currency in FALLBACK_RATES_TO_PKR:
        rate = FALLBACK_RATES_TO_PKR[from_currency]
        _rate_cache[from_currency] = rate
        return rate

    return None


def convert_to_pkr(amount, currency):
    """
    Amount ko PKR mein convert karta hai.
    Return: converted amount (float) ya None agar convert na ho sake.
    """
    if amount is None:
        return None

    rate = get_pkr_rate(currency)
    if rate is None:
        return None

    return round(amount * rate, 2)
