# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
	_inherit = 'sale.order'

	limit_warning_msg = fields.Char("Warning Msg",copy=False)
	approval_state = fields.Selection([("pending","Pending"),("approved","Approved"),("rejected","Rejected")],string="Approval State",copy=False)
	payment_type = fields.Selection(related="partner_id.payment_type")

	def action_check_previos_order(self):
		for rec in self:
			sale_orders = self.env['sale.order'].search([('partner_id','=',rec.partner_id.id),('id','!=',rec.id),('state','!=','cancel')])
			remain_sale_orders = sale_orders.filtered(lambda x:x.limit_warning_msg)
			invoice_ids = remain_sale_orders.invoice_ids.filtered(lambda x:x.status_in_payment != "paid" and x.state != "cancel")
			if invoice_ids:
				raise UserError(_("The credit limit for the previous Sale Order has already been increased, and the Invoice Payment is currently not Paid. Kindly prioritize paid it first \n Invoice Numbers : %s") % ','.join(invoice_ids.mapped("name")))

	def action_confirm(self):
		for rec in self:
			self.action_check_previos_order()
			if rec.limit_warning_msg and not rec.approval_state:
				raise UserError(_(rec.limit_warning_msg))
			elif rec.approval_state == "pending":
				raise UserError(_("Sales Approval Pending !"))
			elif rec.approval_state == "rejected":
				raise UserError(_("Sales Approval Rejected !"))
		res = super().action_confirm()
		return res

	def action_create_request(self):
		for rec in self:
			vals = {
				"request_type":rec.partner_id.payment_type,
				"sale_id":self.id,
				"amount":self.amount_total,
				"requested_user_id":self.env.user.id,
				"partner_id":self.partner_id.id,
			}
			credit_request_id = self.env['credit.request'].create(vals)
			credit_request_id.action_send_mail()
			rec.approval_state = "pending"

	@api.onchange("order_line","payment_type","partner_id")
	def onchange_on_amount_total(self):
		for rec in self:
			if rec.payment_type == "advance":
				advance_amount = rec.partner_id.get_advance_amount()
				if rec.amount_total > advance_amount:
					limit_warning_msg = "This Sales Order cannot be processed because the customer has not made an advance payment."
					rec.write({'limit_warning_msg':limit_warning_msg})
				else:
					rec.limit_warning_msg = ""
			else:
				if rec.amount_total > rec.partner_id.credit_limit_amount:
					limit_warning_msg = "This Sales Order cannot be processed because the customer has exceeded their credit limit."
					rec.write({'limit_warning_msg':limit_warning_msg})
				else:
					rec.limit_warning_msg = ""

	@api.model_create_multi
	def create(self,vals):
		res = super().create(vals)
		res.onchange_on_amount_total()
		return res