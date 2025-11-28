# Shared constants for multiagent-firewall
# Prompts usable by the LLM detector agent and their locations under prompts/
LLM_PROMPT_MAP = {
    "zero-shot": "zero-shot.txt",
    "enriched-zero-shot": "enriched-zero-shot.txt",
    "few-shot": "few-shot.txt",
}

# Regex patterns for DLP detection agent
REGEX_PATTERNS = {
    "SSN": r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PHONENUMBER": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
}

# Keyword lists for DLP detection agent
KEYWORDS = {
    "SSN": ["ssn", "social security", "social security number", "social"],
    "APIKEY": ["api_key", "apikey", "api-key", "api key"],
    "SECRET": ["secret"],
    "PASSWORD": ["password", "pwd"],
    "TOKEN": ["token", "bearer", "auth"],
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
