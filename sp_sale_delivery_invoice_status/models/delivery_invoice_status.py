# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrder(models.Model):
	_inherit = "sale.order"

	is_partially_delivery = fields.Boolean(string="Partially Delivered",readonly=True,copy=False)
	is_fully_delivery = fields.Boolean(string="Fully Delivered",readonly=True,copy=False)
	is_partially_paid = fields.Boolean(string="Partially Paid",readonly=True,copy=False)
	is_fully_paid = fields.Boolean(string="Fully Paid",readonly=True,copy=False)


class StockPicking(models.Model):
	_inherit = "stock.picking"

	def write(self,vals):
		res = super().write(vals)
		self._compute_sale_fully_picking()
		return res

	def _compute_sale_fully_picking(self):
		for picking in self:
			order = self.env['sale.order'].search([('picking_ids','in',[picking.id])])
			total_quantity = sum(order.order_line.mapped('product_uom_qty'))
			delivered_quantity = sum(order.order_line.mapped('qty_delivered'))
			invoiced_quantity = sum(order.order_line.mapped('qty_invoiced'))
			not_consider_qty = delivered_quantity - invoiced_quantity
			delivered_quantity -= not_consider_qty
			if total_quantity == delivered_quantity and total_quantity != 0:
				order.is_fully_delivery = True
				order.is_partially_delivery = False
			elif total_quantity > delivered_quantity and total_quantity != 0 and delivered_quantity != 0:
				order.is_fully_delivery = False
				order.is_partially_delivery = True
			else:
				order.is_fully_delivery = False
				order.is_partially_delivery = False

class inherit_invoicing(models.Model):
	_inherit = "account.move"

	def write(self,vals):
		res = super().write(vals)
		self._compute_sale_invoice()
		return res

	def _compute_sale_invoice(self):
		for invoice in self:
			orders = self.env['sale.order'].search([('invoice_ids', 'in', invoice.ids)])
			for order in orders:
				amount_residual = sum(order.invoice_ids.mapped('amount_residual'))
				amount_total = sum(order.invoice_ids.mapped('amount_total'))
				if amount_residual == 0 and amount_total:
					order.is_fully_paid = True
					order.is_partially_paid = False
				elif 0 < amount_residual < amount_total:
					order.is_fully_paid = False
					order.is_partially_paid = True
				else:
					order.is_fully_paid = False
					order.is_partially_paid = False
				order.picking_ids._compute_sale_fully_picking()
