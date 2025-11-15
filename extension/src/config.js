(function initConfig(root) {
  const sg = (root.SG = root.SG || {});

  const API_BASE = "http://127.0.0.1:8000";
  const MODE = "zero-shot"; // Set to null to defer to backend DETECTION_MODE

  const HIGH_FIELDS = new Set([
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
  ]);

  const MEDIUM_FIELDS = new Set([
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
  ]);

  sg.config = {
    API_BASE,
    MODE,
    HIGH_FIELDS,
    MEDIUM_FIELDS,
  };
})(typeof window !== "undefined" ? window : globalThis);
