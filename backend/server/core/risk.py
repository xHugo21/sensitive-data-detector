def compute_risk_level(detected_fields):
    def norm(name: str) -> str:
        return (name or "").strip().upper().replace("-", "").replace("_", "")

    high_risk = {
        "PASSWORD","CREDENTIALS","SSN","DNI","PASSPORTNUMBER",
        "CREDITCARDNUMBER","IP","IPV4","IPV6","MAC",
        "CREDITCARDCVV","ACCOUNTNUMBER","IBAN","PIN","GENETICDATA",
        "BIOMETRICDATA","STREET","VEHICLEVIN","HEALTHDATA","CRIMINALRECORD",
        "CONFIDENTIALDOC","LITECOINADDRESS","BITCOINADDRESS","ETHEREUMADDRESS",
        "PHONEIMEI"
    }

    medium_risk = {
        "EMAIL","PHONENUMBER","URL","CLIENTDATA","EMPLOYEEDATA","SALARYDETAILS",
        "COMPANYNAME","JOBTITLE","JOBTYPE","JOBAREA","ACCOUNTNAME","PROJECTNAME",
        "CODENAME","EDUCATIONHISTORY","CV","SOCIALMEDIAHANDLE","SECONDARYADDRESS",
        "CITY","STATE","COUNTY","ZIPCODE","BUILDINGNUMBER","USERAGENT","VEHICLEVRM",
        "NEARBYGPSCOORDINATE","BIC","MASKEDNUMBER","AMOUNT","CURRENCY",
        "CURRENCYSYMBOL","CURRENCYNAME","CURRENCYCODE","CREDITCARDISSUER","USERNAME",
        "INFRASTRUCTURE"
    }

    low_risk = {
        "PREFIX","FIRSTNAME","MIDDLENAME","LASTNAME","AGE","DOB","GENDER","SEX",
        "HAIRCOLOR","EYECOLOR","HEIGHT","WEIGHT","SKINTONE","OTHER FEATURES",
        "RACIALORIGIN","RELIGION","POLITICALOPINION","PHILOSOPHICALBELIEF","TRADEUNION",
        "DATE","TIME","ORDINALDIRECTION","SEXUALORIENTATION","CHILDRENDATA",
        "LEGALDISCLOSURE"
    }

    score = 0
    for f in detected_fields:
        field = norm(f.get("field", ""))
        if field in high_risk:
            score += 6
        elif field in medium_risk:
            score += 2
        elif field in low_risk:
            score += 1
        else:
            score += 2

    if score >= 6:
        return "High"
    if 4 <= score <= 5:
        return "Medium"
    if 1 <= score <= 3:
        return "Low"
    return "None"
