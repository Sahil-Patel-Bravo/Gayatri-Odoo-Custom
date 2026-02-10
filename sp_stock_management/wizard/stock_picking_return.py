# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ReturnPicking(models.TransientModel):
	_inherit = 'stock.return.picking'

	def _prepare_picking_default_values_based_on(self, picking):
		vals = super()._prepare_picking_default_values_based_on(picking)
		return_type = picking.picking_type_id.return_picking_type_id
		if return_type and return_type.code == 'incoming':
			vals['location_dest_id'] = picking.location_id.id
		return vals
