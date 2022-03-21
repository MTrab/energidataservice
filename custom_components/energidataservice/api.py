"""Energidatastyrelsen API handler"""
from datetime import datetime, timedelta

import time
import requests

class Energidatastyrelsen:
    """Energidatastyrelsen API"""
    
    def __init__(self, area):
        """Init API connection to Energidatastyrelsen"""
        self._area = area

    def get_spotprices(self):
        """Fetch latest spotprices, excl. VAT and tariff."""
        try:
            headers = self._header()
            url = "https://api.energidataservice.dk/datastore_search?resource_id=elspotprices&limit=48&filters={\"PriceArea\":\"" + self._area + "\"}&sort=HourUTC desc"
            return requests.get(url, headers=headers[0]).json()

        except Exception as ex:
            raise Exception(str(ex))

    def _header(self):
        """Create default request header"""

        data = {
            "Content-Type": "application/json"
        }

        return [data]
