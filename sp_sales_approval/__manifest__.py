# -- coding: utf-8 --

{
	'name': 'Sales Approval',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Module for Sales Approval Manage Customer Credit and Advance Payment',
	'description': """Approval For Sales""",
	'category': 'Sale',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale','sales_team','account'],
	'data': [
		'data/demo.xml',
		'security/ir.model.access.csv',
		'security/security.xml',
		'views/res_partner_view.xml',
		'views/sale_order_view.xml',
		'views/advance_payment_view.xml',
		'views/credit_request_view.xml',
		'views/credit_increase_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
