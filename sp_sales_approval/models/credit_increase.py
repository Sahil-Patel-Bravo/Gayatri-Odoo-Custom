# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class CreditLimitIncrease(models.Model):
	_name = "credit.limit.increase"
	_inherit = ["mail.thread", "mail.activity.mixin"]
	_description = "Credit Limit Request"

	name = fields.Char('Name',tracking=True)
	partner_id = fields.Many2one("res.partner","Partner",tracking=True)
	amount = fields.Float("Amount",tracking=True)
	state = fields.Selection([('draft','Draft'),('submit','Submit'),('approved','Approved'),('rejected','Rejected')],string="State",default="draft",tracking=True)
	user_id = fields.Many2one("res.users",string="User",default=lambda self:self.env.user,tracking=True)
	note = fields.Char("Note",tracking=True)

	def action_submit(self):
		self.state = "submit"
		self.action_send_mail()

	def action_approve(self):
		credit_limit_amount = self.partner_id.credit_limit_amount
		credit_limit_amount += self.amount
		self.partner_id.credit_limit_amount = credit_limit_amount
		self.state = "approved"
	
	def action_reject(self):
		self.state = "rejected"

	@api.model_create_multi
	def create(self,vals):
		for val in vals:
			seq = self.env['ir.sequence'].next_by_code('credit.limit.request.seq') or '/'
			val['name'] = seq
		res = super().create(vals)
		return res

	def action_send_mail(self):
		for rec in self:
			mail_activity_obj = self.env['mail.activity']
			activity_type_id = self.env.ref("mail.mail_activity_data_todo")
			model_id = self.env.ref("sp_sales_approval.model_credit_limit_increase")
			sp_sales_approval = self.env.ref('sp_sales_approval.group_sales_approval')
			note = "Please Approve Credit Limit Request."
			if note:
				for user_id in sp_sales_approval.user_ids:
					vals = {'activity_type_id': activity_type_id.id,
							'summary': note,
							'res_id': rec.id,
							'user_id': user_id.id or self._uid,
							'res_model_id': model_id.id}
					mail_activity_obj.create(vals)