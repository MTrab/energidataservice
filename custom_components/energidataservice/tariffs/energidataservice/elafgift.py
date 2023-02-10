"""List of el afgift as defined by the Danish government."""

from datetime import datetime


FM_EL_AFGIFT = [
    {
        "from": datetime.strptime("01-01-2023", "%d-%m-%Y"),
        "to": datetime.strptime("01-06-2023", "%d-%m-%Y"),
        "value": 0.008,
    },
    {
        "from": datetime.strptime("01-06-2023", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2024", "%d-%m-%Y"),
        "value": 0.697,
    },
    {
        "from": datetime.strptime("01-01-2024", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2025", "%d-%m-%Y"),
        "value": 0.71,
    },
    {
        "from": datetime.strptime("01-01-2025", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2026", "%d-%m-%Y"),
        "value": 0.648,
    },
    {
        "from": datetime.strptime("01-01-2026", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2027", "%d-%m-%Y"),
        "value": 0.648,
    },
    {
        "from": datetime.strptime("01-01-2027", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2028", "%d-%m-%Y"),
        "value": 0.648,
    },
    {
        "from": datetime.strptime("01-01-2028", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2029", "%d-%m-%Y"),
        "value": 0.632,
    },
    {
        "from": datetime.strptime("01-01-2029", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2030", "%d-%m-%Y"),
        "value": 0.617,
    },
    {
        "from": datetime.strptime("01-01-2030", "%d-%m-%Y"),
        "to": datetime.strptime("01-01-2031", "%d-%m-%Y"),
        "value": 0.561,
    },
]
