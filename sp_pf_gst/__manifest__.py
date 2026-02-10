# -- coding: utf-8 --

{
	'name': 'SP P&F GST',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'SP P&F GST',
	'description': """SP P&F GST""",
	'category': 'Sales Management',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale','purchase','account'],
	'data': [
		'views/product_view.xml',
		'views/sale_order_view.xml',
		'views/purchase_order_view.xml',
		'views/account_move_view.xml',

		'report/invoice_report.xml',
		'report/sale_report.xml',
		'report/purchase_report.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
