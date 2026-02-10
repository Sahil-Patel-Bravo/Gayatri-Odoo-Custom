# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	product_location_id = fields.Many2one(related="product_id.product_location_id")