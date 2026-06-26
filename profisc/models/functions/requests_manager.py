import json
import logging

import requests

from odoo import models, api

_logger = logging.getLogger(__name__)


class RequestManager(models.AbstractModel):
    _name = 'request.manager'
    _description = 'Profisc Request Manager'

    @api.model
    def post_with_header(self, endpoint, payload=None):
        return self._make_request('POST', endpoint, payload, headers=self.env['profisc.auth'].generateHeaders())

    @api.model
    def post(self, endpoint, payload=None, headers=None):
        return self._make_request('POST', endpoint, payload, headers)

    @api.model
    def get(self, endpoint, params=None, headers=None):
        return self._make_request('GET', endpoint, params, headers)

    @api.model
    def put(self, endpoint, payload=None, headers=None):
        return self._make_request('PUT', endpoint, payload, headers)

    @api.model
    def delete(self, endpoint, headers=None):
        return self._make_request('DELETE', endpoint, None, headers)

    def _make_request(self, method, endpoint, data=None, headers=None, retry_count=0):
        try:
            _logger.info("RequestManager::%s to %s", method, endpoint)
            response = requests.request(
                method,
                endpoint,
                params=data if method == 'GET' else None,
                json=data if method in ('POST', 'PUT') else None,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            res = None
            if response.content:
                res = response.json()
                _logger.info("RequestManager::response::success::with data::%s", res)

            return res

        except requests.RequestException as e:

            if e.response is not None:
                _logger.error('Failed to make request: %s, response: %s, content: %s', e, e.response,
                              e.response.content)
                if e.response.status_code == 401 and retry_count < 3:
                    self.env['profisc.auth'].profisc_login()
                    # We recall the same method with the same parameters but its required to regenerate headers to get new token
                    return self._make_request(method, endpoint, data,
                                              headers=self.env['profisc.auth'].generateHeaders(),
                                              retry_count=retry_count + 1)

                elif e.response.status_code == 500:
                    _logger.error('Server error (500): %s', e.response.content)
            else:
                _logger.error('Failed to make request: %s', e)
