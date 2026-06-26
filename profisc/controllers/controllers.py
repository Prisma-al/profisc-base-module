# -*- coding: utf-8 -*-
# from odoo import http


# class Profisc(http.Controller):
#     @http.route('/profisc/profisc', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/profisc/profisc/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('profisc.listing', {
#             'root': '/profisc/profisc',
#             'objects': http.request.env['profisc.profisc'].search([]),
#         })

#     @http.route('/profisc/profisc/objects/<model("profisc.profisc"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('profisc.object', {
#             'object': obj
#         })
