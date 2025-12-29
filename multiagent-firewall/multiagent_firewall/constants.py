# Shared constants for multiagent-firewall

# Prompt filenames stored under prompts/
LLM_DETECTOR_PROMPT = "sensitive-data-llm-prompt.txt"
OCR_DETECTOR_PROMPT = "ocr-llm-prompt.txt"

# Regex patterns for DLP detection agent
REGEX_PATTERNS = {
    "SSN": {
        "field": "SSN",
        "regex": r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b",
        "window": 6,
        "keywords": [
            "ssn",
            "social security",
            "social-security",
            "socialsecurity",
        ],
    },
    "EMAIL": {
        "field": "EMAIL",
        "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    },
    "PHONENUMBER": {
        "field": "PHONENUMBER",
        "regex": r"(?<!\w)\+?\d[\d\s\-\(\)]{7,}\d\b",
    },
    "CREDITCARDNUMBER": {
        "field": "CREDITCARDNUMBER",
        "regex": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
        "window": 4,
        "keywords": [
            "card",
            "credit card",
            "cc",
            "visa",
            "mastercard",
        ],
    },
    "CREDITCARDCVV": {
        "field": "CREDITCARDCVV",
        "regex": r"\b\d{3,4}\b",
        "window": 4,
        "keywords": ["cvv", "cvc", "cvv2", "security code"],
    },
    "IPV4": {
        "field": "IPV4",
        "regex": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
    },
    "IPV6": {
        "field": "IPV6",
        "regex": r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b|(?:[A-Fa-f0-9]{1,4}:){1,7}:|(?:[A-Fa-f0-9]{1,4}:){1,6}:[A-Fa-f0-9]{1,4}\b",
    },
    "MAC": {
        "field": "MAC",
        "regex": r"\b(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b",
        "window": 4,
        "keywords": ["mac"],
    },
    "IBAN": {
        "field": "IBAN",
        "regex": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
        "window": 6,
        "keywords": ["iban", "account", "bank"],
    },
    "BIC": {
        "field": "BIC",
        "regex": r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b",
        "window": 6,
        "keywords": ["bic", "swift"],
    },
    "URL": {
        "field": "URL",
        "regex": r"\b(?:https?|ftp)://[^\s/$.?#].[^\s]*\b",
    },
    "BITCOINADDRESS": {
        "field": "BITCOINADDRESS",
        "regex": r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|bc1[a-z0-9]{39,59}\b",
    },
    "ETHEREUMADDRESS": {
        "field": "ETHEREUMADDRESS",
        "regex": r"\b0x[a-fA-F0-9]{40}\b",
    },
    "LITECOINADDRESS": {
        "field": "LITECOINADDRESS",
        "regex": r"\b(?:[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}|ltc1[0-9a-z]{39,59})\b",
    },
    "ZIPCODE": {
        "field": "ZIPCODE",
        "regex": r"\b\d{5}(?:[\-\s]\d{4})?\b",
        "window": 4,
        "keywords": ["zip", "zipcode", "postal"],
    },
    "VEHICLEVIN": {
        "field": "VEHICLEVIN",
        "regex": r"\b[A-HJ-NPR-Z0-9]{17}\b",
        "window": 6,
        "keywords": ["vin", "vehicle"],
    },
    "PIN": {
        "field": "PIN",
        "regex": r"\b\d{4,6}\b",
        "window": 4,
        "keywords": ["pin", "personal identification number"],
    },
    "PHONEIMEI": {
        "field": "PHONEIMEI",
        "regex": r"\b\d{2}-\d{6}-\d{6}-\d\b|\b\d{15}\b",
        "window": 4,
        "keywords": ["imei"],
    },
    "NEARBYGPSCOORDINATE": {
        "field": "NEARBYGPSCOORDINATE",
        "regex": r"\b-?\d{1,2}\.\d+\s*,\s*-?\d{1,3}\.\d+\b",
        "window": 6,
        "keywords": ["coordinates", "coordinate", "lat", "lng", "latitude", "longitude"],
    },
    "DOB": {
        "field": "DOB",
        "regex": r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
        "window": 6,
        "keywords": ["dob", "date of birth", "born"],
    },
    "DATE": {
        "field": "DATE",
        "regex": r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
        "window": 4,
        "keywords": ["date", "dated"],
    },
    "TIME": {
        "field": "TIME",
        "regex": r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
        "window": 3,
        "keywords": ["time"],
    },
    "ACCOUNTNUMBER": {
        "field": "ACCOUNTNUMBER",
        "regex": r"\b\d{8,18}\b",
        "window": 6,
        "keywords": [
            "account number",
            "acct",
            "account",
            "iban",
            "routing",
        ],
    },
    "CURRENCYCODE": {
        "field": "CURRENCYCODE",
        "regex": r"\b[A-Z]{3}\b",
        "window": 2,
        "keywords": ["currency", "code", "iso"],
    },
    "CURRENCYSYMBOL": {
        "field": "CURRENCYSYMBOL",
        "regex": r"[$]",
    },
    "AMOUNT": {
        "field": "AMOUNT",
        "regex": r"\b\d{1,3}(?:[,\d]{0,15})(?:\.\d+)?\b",
        "window": 4,
        "keywords": ["amount", "total", "sum", "usd", "eur", "gbp", "$"],
    },
}

# Keyword lists for DLP detection agent
KEYWORDS = {
    "PASSWORD": ["password", "passcode", "pwd"],
    "USERNAME": ["username", "user name", "user id", "userid"],
    "ACCOUNTNAME": ["account name", "account holder", "beneficiary"],
    "ACCOUNTNUMBER": ["account number", "acct number", "account #", "iban"],
}

# Labels for NER detection and their mapping to application sensitive fields.
NER_LABELS = {
    "person": "FIRSTNAME",
    "first name": "FIRSTNAME",
    "middle name": "MIDDLENAME",
    "last name": "LASTNAME",
    "company": "COMPANYNAME",
    "organization": "COMPANYNAME",
    "job title": "JOBTITLE",
    "job area": "JOBAREA",
    "job type": "JOBTYPE",
    "street": "STREET",
    "street address": "STREET",
    "building number": "BUILDINGNUMBER",
    "secondary address": "SECONDARYADDRESS",
    "city": "CITY",
    "state": "STATE",
    "county": "COUNTY",
    "zipcode": "ZIPCODE",
    "postal code": "ZIPCODE",
}

# Defines the scoring value each detected field category sums
RISK_SCORE = {
    "high": 6,
    "medium": 2,
    "low": 1,
}

# Defines the threshold to calculate global risk value based on the sum of all detected fields.
RISK_SCORE_THRESHOLDS = {
    "high": 6,
    "medium": (4, 5),
    "low": (1, 3),
}

# Risk level field sets
HIGH_RISK_FIELDS = {
    "ACCOUNTNUMBER",
    "BITCOINADDRESS",
    "CREDITCARDCVV",
    "CREDITCARDNUMBER",
    "DOB",
    "ETHEREUMADDRESS",
    "IBAN",
    "LITECOINADDRESS",
    "NEARBYGPSCOORDINATE",
    "PASSWORD",
    "PHONEIMEI",
    "PIN",
    "SSN",
    "VEHICLEVIN",
}

MEDIUM_RISK_FIELDS = {
    "ACCOUNTNAME",
    "AMOUNT",
    "BIC",
    "BUILDINGNUMBER",
    "CITY",
    "COMPANYNAME",
    "COUNTY",
    "CREDITCARDISSUER",
    "CURRENCY",
    "CURRENCYCODE",
    "CURRENCYNAME",
    "CURRENCYSYMBOL",
    "EMAIL",
    "IP",
    "IPV4",
    "IPV6",
    "JOBAREA",
    "JOBTITLE",
    "JOBTYPE",
    "MAC",
    "MASKEDNUMBER",
    "PHONENUMBER",
    "SECONDARYADDRESS",
    "STATE",
    "STREET",
    "USERAGENT",
    "USERNAME",
    "VEHICLEVRM",
    "ZIPCODE",
}

LOW_RISK_FIELDS = {
    "AGE",
    "DATE",
    "EYECOLOR",
    "FIRSTNAME",
    "GENDER",
    "HEIGHT",
    "LASTNAME",
    "MIDDLENAME",
    "ORDINALDIRECTION",
    "PREFIX",
    "SEX",
    "TIME",
    "URL",
}
