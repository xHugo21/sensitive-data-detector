# Shared constants for multiagent-firewall

# Regex patterns for DLP
REGEX_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PHONE_NUMBER": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
}

# Keyword lists for DLP
KEYWORDS = {
    "API_KEY": ["api_key", "apikey", "api-key", "api key"],
    "SECRET": ["secret", "password", "pwd"],
    "TOKEN": ["token", "bearer", "auth"],
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
    "API_KEY",
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

# Risk scoring thresholds
RISK_SCORE_THRESHOLDS = {
    "High": 6,
    "Medium": (4, 5),
    "Low": (1, 3),
}
