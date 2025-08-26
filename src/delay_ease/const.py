HSP_SERVICE_METRICS_URL = "https://hsp-prod.rockshore.net/api/v1/serviceMetrics"
HSP_SERVICE_DETAILS_URL = "https://hsp-prod.rockshore.net/api/v1/serviceDetails"

TYPE_A_TOCS = {
    "CrossCountry": "https://delayrepay.crosscountrytrains.co.uk/en/login",
    "Transport for Wales": "https://delayrepay.tfwrail.wales/en/login",
    "TransPennine Express": "https://delayrepay.tpexpress.co.uk/en/login?loginTarget=%2F",
    "Great Western Railway": "https://delayrepay.gwr.com/en/login?loginTarget=%2F%3F_gl%3D1*81tu50*_gcl_au*MjE0NDgxNzI1MC4xNzQyODQ0OTcy",
    "Northern": "https://delayrepay.northernrailway.co.uk/en/login?loginTarget=%2F",
    "South Western Railway": "https://delayrepay.southwesternrailway.com/en/login?loginTarget=%2F%3F_gl%3D1*glu0ie*_gcl_au*MTczMjE1Nzk0NS4xNzQyODQ1NzQ3",
    "Island Line": "https://delayrepay.southwesternrailway.com/en/login?loginTarget=%2F%3F_gl%3D1*glu0ie*_gcl_au*MTczMjE1Nzk0NS4xNzQyODQ1NzQ3"
}

ALLOWED_DOMAINS=[
            'https://delayrepay.crosscountrytrains.co.uk',      # CrossCountry
            'https://delayrepay.tfwrail.wales',                 # Transport for Wales  
            'https://delayrepay.tpexpress.co.uk',               # TransPennine Express
            'https://delayrepay.gwr.com',                       # Great Western Railway
            'https://delayrepay.northernrailway.co.uk',         # Northern
            'https://delayrepay.southwesternrailway.com'        # South Western Railway & Island Line
]