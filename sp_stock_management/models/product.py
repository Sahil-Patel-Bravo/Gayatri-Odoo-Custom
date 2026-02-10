# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	product_location_id = fields.Many2one("stock.location","Product Location")