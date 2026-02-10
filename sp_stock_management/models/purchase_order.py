# -*- coding: utf-8 -*-

from odoo import models, fields, api, _ , SUPERUSER_ID
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

class Purchaserder(models.Model):
	_inherit = 'purchase.order'

	def _create_picking(self):
		StockPicking = self.env['stock.picking']
		for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
			if any(product.type == 'consu' for product in order.order_line.product_id):

				# Group purchase order lines by product_location_id
				grouped_lines = {}
				for line in order.order_line:
					if line.product_location_id not in grouped_lines:
						grouped_lines[line.product_location_id] = self.env['purchase.order.line']
					grouped_lines[line.product_location_id] |= line

				for location, lines in grouped_lines.items():
					order = order.with_company(order.company_id)
					pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.id == location.id)
					if not pickings:
						res = order._prepare_picking()
						# Set destination location as the grouped location
						res['location_dest_id'] = location.id
						picking_type_id = self.env['stock.picking.type'].search([('code','=','incoming'),('warehouse_id','=',location.warehouse_id.id)],limit=1)
						res['picking_type_id'] = picking_type_id.id
						picking = StockPicking.with_user(SUPERUSER_ID).create(res)
						pickings = picking
					else:
						picking = pickings[0]

					# Create stock moves for grouped lines
					moves = lines._create_stock_moves(picking)
					moves.location_dest_id = location.id
					moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()

					seq = 0
					for move in sorted(moves, key=lambda move: move.date):
						seq += 5
						move.sequence = seq

					moves._action_assign()

					# Get following pickings (created by push rules) to confirm them as well
					forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
					(pickings | forward_pickings).action_confirm()

					picking.message_post_with_source(
						'mail.message_origin_link',
						render_values={'self': picking, 'origin': order},
						subtype_xmlid='mail.mt_note',
					)
		return True

class PurchaserderLine(models.Model):
	_inherit = 'purchase.order.line'

	product_location_id = fields.Many2one(related="product_id.product_location_id")

	def _create_or_update_picking(self):
		StockPicking = self.env['stock.picking']

		for line in self:
			if not line.product_id or line.product_id.type != 'consu':
				continue

			location = line.product_location_id
			if not location:
				continue

			rounding = line.product_uom.rounding
			# Prevent decreasing below received quantity			
			if float_compare(line.product_qty, line.qty_received, precision_rounding=rounding) < 0:
				raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
								  'Create a return first.'))

			if float_compare(line.product_qty, line.qty_invoiced, precision_rounding=rounding) < 0 and line.invoice_lines:
				# If the quantity is now below the invoiced quantity, create an activity on the vendor bill
				# inviting the user to create a refund.
				line.invoice_lines[0].move_id.activity_schedule(
					'mail.mail_activity_data_warning',
					note=_('The quantities on your purchase order indicate less than billed. You should ask for a refund.')
				)

			order = line.order_id.with_company(line.order_id.company_id)
			picking = order.picking_ids.filtered(
				lambda p: p.state not in ('done', 'cancel')
				and p.location_dest_id.id == location.id
			)

			picking = picking[:1] if picking else False
			if not picking:
				if not line.product_qty > line.qty_received:
					continue

				res = order._prepare_picking()
				res['location_dest_id'] = location.id
				picking_type_id = self.env['stock.picking.type'].search([
					('code', '=', 'incoming'),
					('warehouse_id', '=', location.warehouse_id.id)
				], limit=1)

				res['picking_type_id'] = picking_type_id.id
				picking = StockPicking.with_user(SUPERUSER_ID).create(res)

			moves = line._create_stock_moves(picking)
			moves.write({'location_dest_id': location.id})
			moves = moves.filtered(lambda m: m.state not in ('done', 'cancel'))._action_confirm()
			moves._action_assign()
			forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
			(picking | forward_pickings).action_confirm()

		return True
