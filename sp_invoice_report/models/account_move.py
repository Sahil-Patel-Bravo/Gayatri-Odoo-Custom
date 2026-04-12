# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

# class AccountMove(models.Model):
# 	_inherit = "account.move"

class AccountMove(models.Model):
	_name = "account.move"
	_inherit = ["account.move", "date.range.search.mixin"]
	
	po_no = fields.Char("PO NO")
	po_date = fields.Date("PO Date")
	transport = fields.Char("Transport")
	lr_no = fields.Char("LR NO")
	lr_date = fields.Date("LR Date")
