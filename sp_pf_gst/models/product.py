# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PproductTemplate(models.Model):
	_inherit = 'product.template'

	is_hilti = fields.Boolean("Is Hilti")
	pf_gst = fields.Float("P&F",default="3")

class PproductProduct(models.Model):
	_inherit = 'product.product'

	@api.onchange("is_hilti")
	def onchange_on_is_hilti(self):
		for rec in self:
			rec.pf_gst = 0
