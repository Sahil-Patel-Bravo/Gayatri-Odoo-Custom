# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class Purchaserder(models.Model):
	_inherit = 'purchase.order'

	def button_confirm(self):
		if not self.env.user.has_group("base.group_system"):
			raise UserError(_("Only an Administrator can approve this Purchase Order. Please contact your administrator."))
		res = super().button_confirm()
		return res