# Shared constants for multiagent-firewall
# Prompts usable by the LLM detector agent and their locations under prompts/
LLM_PROMPT_MAP = {
    "zero-shot": "zero-shot.txt",
    "enriched-zero-shot": "enriched-zero-shot.txt",
    "few-shot": "few-shot.txt",
    "generic": "generic.txt",
}

# Regex patterns for DLP detection agent
REGEX_PATTERNS = {
    "SSN": r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PHONENUMBER": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
    "CREDITCARDNUMBER": r"\b(?:\d{4}[\s\-]?){3}\d{4}\b",
    "CREDITCARDCVV": r"\b\d{3,4}\b",
    "IPV4": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
    "IPV6": r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b|(?:[A-Fa-f0-9]{1,4}:){1,7}:|(?:[A-Fa-f0-9]{1,4}:){1,6}:[A-Fa-f0-9]{1,4}\b",
    "MAC": r"\b(?:[0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b",
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
    "BIC": r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b",
    "URL": r"\b(?:https?|ftp)://[^\s/$.?#].[^\s]*\b",
    "DNI": r"\b\d{8}[A-Z]\b",
    "PASSPORTNUMBER": r"\b[A-Z]{1,2}\d{6,9}\b",
    "BITCOINADDRESS": r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|bc1[a-z0-9]{39,59}\b",
    "ETHEREUMADDRESS": r"\b0x[a-fA-F0-9]{40}\b",
    "LITECOINADDRESS": r"\b[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}\b",
    "ZIPCODE": r"\b\d{5}(?:[\-\s]\d{4})?\b",
    "DATE": r"\b(?:\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
    "TIME": r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b",
    "VEHICLEVIN": r"\b[A-HJ-NPR-Z0-9]{17}\b",
    "PIN": r"\b\d{4,6}\b",
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
    "SSN",
    "DNI",
    "PASSPORTNUMBER",
    "CREDITCARDNUMBER",
    "IP",
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
    "CONFIDENTIALDOC",
    "LITECOINADDRESS",
    "BITCOINADDRESS",
    "ETHEREUMADDRESS",
    "PHONEIMEI",
    "APIKEY",
    "SECRET",
    "TOKEN",
}

MEDIUM_RISK_FIELDS = {
    "EMAIL",
    "PHONENUMBER",
    "URL",
    "CLIENTDATA",
    "EMPLOYEEDATA",
    "SALARYDETAILS",
    "COMPANYNAME",
    "JOBTITLE",
    "JOBTYPE",
    "JOBAREA",
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
    "VEHICLEVRM",
    "NEARBYGPSCOORDINATE",
    "BIC",
    "MASKEDNUMBER",
    "AMOUNT",
    "CURRENCY",
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
    "DOB",
    "GENDER",
    "SEX",
    "HAIRCOLOR",
    "EYECOLOR",
    "HEIGHT",
    "WEIGHT",
    "SKINTONE",
    "OTHER FEATURES",
    "RACIALORIGIN",
    "RELIGION",
    "POLITICALOPINION",
    "PHILOSOPHICALBELIEF",
    "TRADEUNION",
    "DATE",
    "TIME",
    "ORDINALDIRECTION",
    "SEXUALORIENTATION",
    "CHILDRENDATA",
    "LEGALDISCLOSURE",
}
