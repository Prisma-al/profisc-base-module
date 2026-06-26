import base64, logging
import io
import json
import re
import xml.etree.ElementTree as ET

import pycountry
import pyqrcode

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class other_functions(models.Model):
    _name = "other_functions"
    _description = "Some helper functions"

    @api.model
    def convert_country_code(self, country_code):
        _logger.info(f"country_code:{country_code}")
        if not country_code:
            return 'ALB'
        country = pycountry.countries.get(alpha_2=country_code.upper())
        if country:
            _logger.info(f"alpha3_code:{country.alpha_3}")
            return country.alpha_3
        elif country_code.upper()=="XK":
            # pycountry.countries.add_entry(alpha_2="XK", alpha_3="XXK", name="Kosovo", numeric="926")
            _logger.info(f"Installing Kosovo")
            return "RKS"
        return False

    @api.model
    def createQrCode(self, text):
        c = pyqrcode.create(text)
        s = io.BytesIO()
        c.png(s, scale=10)
        return base64.b64encode(s.getvalue()).decode("ascii")

    @api.model
    def nuis_regex_checker(self, input_string):
        if input_string is False or None:
            return False
        pattern = r'^[A-Z]\d{8}[A-Z]{1}$'
        match = re.match(pattern, input_string)
        if match:
            return True
        else:
            return False

    def dict_to_base64(self, input_dict):

        # Convert the dictionary to a JSON string
        json_str = json.dumps(input_dict)

        # Encode the JSON string to bytes
        json_bytes = json_str.encode('utf-8')

        # Encode the bytes using Base64
        base64_bytes = base64.b64encode(json_bytes)

        # Decode the Base64 bytes to a string
        base64_str = base64_bytes.decode('utf-8')

        return base64_str
