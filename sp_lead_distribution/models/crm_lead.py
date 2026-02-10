# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo import Command
from datetime import date
from odoo.fields import Domain

class CrmLead(models.Model):
	_inherit = 'crm.lead'

	state_zip_dict = fields.Char(
		string="State Zip Dict",
		help="Stores a combination of state and zip as a dictionary format."
	)
	state_dict = fields.Char(
		string="State Dict",
		help="Stores a combination of state and zip as a dictionary format."
	)
	followup_date = fields.Date(string="Follow-up Date")
	vat = fields.Char('GST NO.')
	product_name = fields.Char('Product Name')
	product_ids = fields.Many2many("product.product",string="Products")
	product_code = fields.Char('Product Number')
	product_qty = fields.Char('Product Qty')
	# email_from = fields.Char(required=True)
	phone = fields.Char(required=True)
	# partner_id = fields.Many2one('res.partner',required=True)

	@api.onchange("zip", "state_id")
	def onchange_on_state_zip_dict(self):
		"""
		Updates `state_zip_dict` field whenever `zip` or `state_id` changes.
		Combines `zip` and `state_id` into a formatted string.
		"""
		for rec in self:
			rec.state_zip_dict = "[%s, %s]" % (rec.zip if rec.zip else "NONE", rec.state_id.id if rec.state_id else "NONE")
			rec.state_dict = "[%s]" % (rec.state_id.id if rec.state_id else "NONE")

	@api.model
	def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
		"""
		Overrides the `_search` method to filter leads based on 
		the logged-in user's zip and state distribution settings.

		If the user has a defined `zip_distribute` on their employee record,
		leads are filtered to match the allowed states and zip codes.
		"""
		if self.env.user.employee_id.zip_distribute:
			# Get the user's zip distribution data
			zip_distribute = self.env.user.employee_id.zip_distribute
			list_of_both = zip_distribute.mapped('state_zip_dict') + [False]
			list_of_state = zip_distribute.mapped('state_dict') + [False]
			# state_ids = zip_distribute.mapped('state_id.id')
			# zips = zip_distribute.mapped('zip')

			# Extend the domain to include state and zip constraints
			# domain += ['|',('state_id', 'in', state_ids),('zip', 'in', zips)]
			domain = Domain.AND([domain,Domain.OR([Domain('state_zip_dict', 'in', list_of_both),Domain('state_dict','in',list_of_state)])])

		print('--domain',domain)

		# Call the super method with the updated domain
		return super()._search(domain, offset, limit, order, **kwargs)

	# def _prepare_opportunity_quotation_context(self):
	# 	res = super()._prepare_opportunity_quotation_context()
	# 	product_ids = self.product_code
	# 	quantities = self.product_qty

	# 	product_id_list = product_ids.split(",")
	# 	product_ids = []
	# 	for product_id in product_id_list:
	# 		product = self.env['product.product'].search([('default_code','=',product_id)])
	# 		pf_gst_per = product.pf_gst or 0.0
	#         pf_gst_amount = (product.list_price or 0.0) * pf_gst_per / 100.0
	#         hilti_price = product.hilti_price if hasattr(product, 'hilti_price') else 0.0
	# 		product_ids.append(str(product.id))
	# 	quantity_list = quantities.split(",")

	# 	o2m_lines = [Command.create({"product_id": int(pid), "product_uom_qty": int(qty)}) for pid, qty in zip(product_ids, quantity_list)]
		
	# 	res['default_order_line'] = o2m_lines
	# 	return res

	def _prepare_opportunity_quotation_context(self):
		res = super()._prepare_opportunity_quotation_context()

		product_codes = self.product_code  # CSV string of default_code
		quantities = self.product_qty      # CSV string of qtys

		product_id_list = product_codes.split(",")
		quantity_list = quantities.split(",")

		o2m_lines = []

		for product_code, qty in zip(product_id_list, quantity_list):
			product = self.env['product.product'].search([('default_code', '=', product_code.strip())], limit=1)
			if product:
				pf_gst_per = product.pf_gst or 0.0
				pf_gst_amount = (product.list_price or 0.0) * pf_gst_per / 100.0
				# hilti_price = product.hilti_price if hasattr(product, 'hilti_price') else 0.0

				o2m_lines.append(Command.create({
					"product_id": product.id,
					"product_uom_qty": int(qty),
					"pf_gst_per": pf_gst_per,
					"pf_gst_amount": pf_gst_amount,
					# "hilti_price": hilti_price,
					"is_hilti": product.is_hilti,
				}))

		res['default_order_line'] = o2m_lines
		res['default_currency_id'] = self.env.company.currency_id
		return res

	@api.onchange("product_ids")
	def onchange_on_product_number(self):
		for rec in self:
			if rec.product_ids:
				product_ids = []
				for product_id in rec.product_ids:
					product_ids.append(str(product_id.default_code))
				product_code = ",".join(product_ids)
				rec.product_code = product_code
			else:
				rec.product_code = ""

	def action_send_notification(self):
		crm_leads = self.env['crm.lead'].search([('followup_date','=',date.today())])
		for lead in crm_leads:
			if lead.user_id:
				vals = {
					'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
					'summary': f'Follow up on Lead',
					'res_id': lead.id,
					'note': f'Reminder to follow up on lead: {lead.name}',
					'user_id': lead.user_id.id,
					'res_model_id': self.env['ir.model']._get_id('crm.lead'),
				}
				self.env['mail.activity'].create(vals)