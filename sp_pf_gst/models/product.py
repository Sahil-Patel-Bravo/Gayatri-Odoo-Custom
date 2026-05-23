# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PproductTemplate(models.Model):
	_inherit = 'product.template'

	is_hilti = fields.Boolean("Is Hilti")
	pf_gst = fields.Float("P&F",default="3")

	@api.onchange('default_code')
	def _onchange_default_code(self):
		# Suppress the base soft warning; uniqueness is enforced as a hard error via constrains
		return

class PproductProduct(models.Model):
	_inherit = 'product.product'

	@api.constrains('default_code')
	def _check_unique_default_code(self):
		for rec in self:
			if not rec.default_code:
				continue
			duplicate = self.search([
				('default_code', '=', rec.default_code),
				('id', '!=', rec.id),
			], limit=1)
			if duplicate:
				raise ValidationError(
					_("The Internal Reference '%s' already exists. Each product must have a unique Internal Reference.") % rec.default_code
				)

	@api.onchange("is_hilti")
	def onchange_on_is_hilti(self):
		for rec in self:
			rec.pf_gst = 0
