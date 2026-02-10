# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	@api.depends('order_id.warehouse_id','product_id','product_location_id','product_id.product_location_id')
	def _compute_warehouse_id(self):
		for line in self:
			if line.product_location_id:
				line.warehouse_id = line.product_location_id.warehouse_id
			else:
				super()._compute_warehouse_id()