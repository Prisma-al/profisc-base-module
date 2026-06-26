import json
import requests

from odoo import api, models
from odoo.exceptions import UserError


class profisc_actions(models.Model):
    _name = 'profisc.auth'
    _description = "Profisc auth model"

    @api.model
    def generateHeaders(self):
        company = self.get_current_company()
        headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache",
                   "Authorization": "Bearer " + company.profisc_login_token if company.profisc_login_token else ""}
        return headers

    @api.model
    def profisc_login(self):
        company = self.get_current_company()

        auth_object = {
            "username": company.profisc_username,
            "password": company.profisc_password,
            "isAgent": 1
        }

        headers = {"Content-Type": "application/json", "Accept": "application/json", "Catch-Control": "no-cache"}
        url = f"{company.profisc_api_endpoint}{company.profisc_login_endpoint}"
        res = requests.post(url, data=json.dumps(auth_object), headers=headers)
        if res.status_code == 200:
            token = res.text
            company.write({'profisc_login_token': token})
            self.env.cr.commit()
            return token
        else:
            raise UserError(f"Error:{res.text}")

    @api.model
    def get_current_company_v1(self):
        # Problem ne multi-companies
        user = self.env.user
        company_id = user.company_id.id
        company = self.env['res.company'].browse(company_id)
        return company

    @api.model
    def get_current_company(self):
        user_context = self.env.context
        current_company_id = user_context.get('company_id') or user_context.get('allowed_company_ids', [])[0]
        current_company = self.env['res.company'].browse(current_company_id)
        return current_company
