# Shared constants for multiagent-firewall

# Prompt filenames stored under prompts/
LLM_DETECTOR_PROMPT = "sensitive-data-llm-prompt.txt"
OCR_DETECTOR_PROMPT = "ocr-llm-prompt.txt"

# Regex patterns for DLP detection agent
REGEX_PATTERNS = {
    "SOCIALSECURITYNUMBER": {
        "field": "SOCIALSECURITYNUMBER",
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
        "regex": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
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
            "amex",
            "american express",
        ],
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
        "keywords": ["mac", "mac address"],
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
    "DNI": {
        "field": "DNI",
        "regex": r"\b\d{8}[A-Z]\b",
        "window": 6,
        "keywords": ["dni"],
    },
    "PASSPORTNUMBER": {
        "field": "PASSPORTNUMBER",
        "regex": r"\b[A-Z]{1,2}\d{6,9}\b",
        "window": 6,
        "keywords": ["passport"],
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
        "regex": r"\b[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}\b",
    },
    "ZIPCODE": {
        "field": "ZIPCODE",
        "regex": r"\b\d{5}(?:[\-\s]\d{4})?\b",
        "window": 4,
        "keywords": ["zip", "zipcode", "postal"],
    },
    "DATE": {
        "field": "DATE",
        "regex": r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
    },
    "TIME": {
        "field": "TIME",
        "regex": r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b",
    },
    "VEHICLEVIN": {
        "field": "VEHICLEVIN",
        "regex": r"\b[A-HJ-NPR-Z0-9]{17}\b",
        "window": 6,
        "keywords": ["vin", "vehicle"],
    },
}

# Keyword lists for DLP detection agent
KEYWORDS = {
    "SECRET": [
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----BEGIN EC PRIVATE KEY-----",
        "-----BEGIN ENCRYPTED PRIVATE KEY-----",
        "-----BEGIN DSA PRIVATE KEY-----",
    ],
}

# Labels for NER detection and their mapping to application sensitive fields.
NER_LABELS = {
    "person": "FIRSTNAME",
    "organization": "COMPANYNAME",
    "street": "STREET",
    "city": "CITY",
    "state": "STATE",
    "zipcode": "ZIPCODE",
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
    "PASSWORD",
    "CREDENTIALS",
    "SOCIALSECURITYNUMBER",
    "DNI",
    "PASSPORTNUMBER",
    "CREDITCARDNUMBER",
    "IPV4",
    "IPV6",
    "MAC",
    "CREDITCARDCVV",
    "ACCOUNTNUMBER",
    "IBAN",
    "PIN",
    "GENETICDATA",
    "BIOMETRICDATA",
    "STREET",
    "VEHICLEVIN",
    "HEALTHDATA",
    "CRIMINALRECORD",
    "CONFIDENTIALDOCUMENT",
    "LITECOINADDRESS",
    "BITCOINADDRESS",
    "ETHEREUMADDRESS",
    "PHONEIMEI",
    "APIKEY",
    "SECRET",
    "TOKEN",
    "CHILDRENDATA",
}

MEDIUM_RISK_FIELDS = {
    "EMAIL",
    "PHONENUMBER",
    "URL",
    "CLIENTDATA",
    "EMPLOYEEDATA",
    "SALARYDETAILS",
    "COMPANYNAME",
    "JOBDETAILS",
    "ACCOUNTNAME",
    "PROJECTNAME",
    "CODENAME",
    "EDUCATIONHISTORY",
    "CV",
    "SOCIALMEDIAHANDLE",
    "SECONDARYADDRESS",
    "CITY",
    "STATE",
    "COUNTY",
    "ZIPCODE",
    "BUILDINGNUMBER",
    "USERAGENT",
    "LICENSEPLATE",
    "GPSCOORDINATE",
    "BIC",
    "MASKEDNUMBER",
    "MONETARYAMOUNT",
    "CURRENCYSYMBOL",
    "CURRENCYNAME",
    "CURRENCYCODE",
    "CREDITCARDISSUER",
    "USERNAME",
    "INFRASTRUCTURE",
}

LOW_RISK_FIELDS = {
    "PREFIX",
    "FIRSTNAME",
    "MIDDLENAME",
    "LASTNAME",
    "AGE",
    "DATEOFBIRTH",
    "GENDER",
    "HAIRCOLOR",
    "EYECOLOR",
    "HEIGHT",
    "WEIGHT",
    "SKINTONE",
    "RACIALORIGIN",
    "RELIGION",
    "POLITICALOPINION",
    "PHILOSOPHICALBELIEF",
    "TRADEUNION",
    "DATE",
    "TIME",
    "ORDINALDIRECTION",
    "SEXUALORIENTATION",
    "LEGALDISCLOSURE",
}
