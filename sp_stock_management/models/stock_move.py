# -*- coding: utf-8 -*-

from odoo import models , api
from odoo.tools import float_compare
from odoo.tools.misc import groupby


class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.model_create_multi
	def create(self,vals_list):
		records = super().create(vals_list)
		for record in records:
			if record.sale_line_id and not record.picking_id.return_id:
				if record.sale_line_id.product_location_id:
					record.location_id = record.sale_line_id.product_location_id.id
		return records

	# def _assign_picking(self):
	# 	Picking = self.env['stock.picking']

	# 	if self.mapped("sale_line_id"):
	# 		grouped_moves = groupby(self, key=lambda m: m._key_assign_picking())
	# 		for group, moves in grouped_moves:
	# 			moves = self.env['stock.move'].concat(*moves)
	# 			new_picking = False
	# 			picking = moves[0]._search_picking_for_assignation()
	# 			if picking:
	# 				vals = moves._assign_picking_values(picking)
	# 				if vals:
	# 					picking.write(vals)
	# 			else:
	# 				# Skip negative quantity moves
	# 				moves = moves.filtered(lambda m: float_compare(m.product_uom_qty, 0.0, precision_rounding=m.product_uom.rounding) >= 0)
	# 				if not moves:
	# 					continue
	# 				new_picking = True
	# 				move_line = sorted(moves, key=lambda x: x.sale_line_id.product_location_id.id)
	# 				for product_location_id, lines in groupby(move_line, key=lambda x: x.sale_line_id.product_location_id):
	# 					new_moves = self.env['stock.move'].concat(*lines)
	# 					order_name = lines[0].sale_line_id.order_id.name
	# 					picking = Picking.search([
	# 						("location_id", "=", product_location_id.id),
	# 						("state", "not in", ("cancel", "done")),
	# 						("origin", "ilike", order_name)
	# 					], limit=1)
	# 					if picking:
	# 						picking.write(vals)
	# 					else:
	# 						new_values = new_moves._get_new_picking_values()
	# 						new_values['location_id'] = product_location_id.id
	# 						picking = Picking.create(new_values)

	# 						new_moves.write({'picking_id': picking.id})
	# 						new_moves._assign_picking_post_process(new=new_picking)
	# 						new_moves.location_id = product_location_id.id
	# 		# 5/0
	# 		return True
	# 	else:
	# 		return super()._assign_picking()
