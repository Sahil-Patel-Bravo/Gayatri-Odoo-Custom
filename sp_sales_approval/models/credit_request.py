# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class CreditRequest(models.Model):
	_name = "credit.request"
	_inherit = ["mail.thread", "mail.activity.mixin",'analytic.mixin']
	_description = "Sales Approval Request"

	name = fields.Char('Name')
	request_type = fields.Selection([('credit','By Credit'),('advance','By Advance Payment')],string="Request Type")
	sale_id = fields.Many2one("sale.order","Sale Order Ref")
	amount = fields.Float("Amount")
	requested_user_id = fields.Many2one("res.users","Requested User")
	partner_id = fields.Many2one("res.partner","Partner")
	state = fields.Selection([('pending','Pending'),('approved','Approved'),('rejected','Rejected')],string="State",default="pending")

	def action_open_sale_order(self):
		return {
			'type':'ir.actions.act_window',
			'res_model':'sale.order',
			'view_mode':'form',
			'res_id':self.sale_id.id,
		}

	def _mark_related_activities_done(self):
		"""Mark all related mail activities as done"""
		activities = self.env['mail.activity'].search([
			('res_model', '=', self._name),
			('res_id', 'in', self.ids)
		])
		for activity in activities:
			activity.action_done()

	def action_approve(self):
		self.sale_id.approval_state = "approved"
		self.state = "approved"
		self._mark_related_activities_done()

	def action_reject(self):
		self.sale_id.approval_state = "rejected"
		self.state = "rejected"
		self._mark_related_activities_done()

	@api.model_create_multi
	def create(self,vals):
		for val in vals:
			seq = self.env['ir.sequence'].next_by_code('credit.request.seq') or '/'
			val['name'] = seq
		res = super().create(vals)
		return res

	def action_send_mail(self):
		for rec in self:
			mail_activity_obj = self.env['mail.activity']
			activity_type_id = self.env.ref("mail.mail_activity_data_todo")
			model_id = self.env.ref("sp_sales_approval.model_credit_request")
			sp_sales_approval = self.env.ref('sp_sales_approval.group_sales_approval')
			if rec.request_type == "advance":
				sp_sales_approval = self.env.ref('sp_sales_approval.group_accounting_approval')
			note = "Please Approve Sales Approval Request."
			if note:
				for user_id in sp_sales_approval.user_ids:
					vals = {'activity_type_id': activity_type_id.id,
							'summary': note,
							'res_id': rec.id,
							'user_id': user_id.id or self._uid,
							'res_model_id': model_id.id}
					mail_activity_obj.create(vals)