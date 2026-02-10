# -- coding: utf-8 --

{
	'name': 'SP Stock Management',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Module for SP Stock Management',
	'description': """SP Stock Management""",
	'category': 'Stock',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale_stock','purchase_stock'],
	'data': [
		'views/product_view.xml',
		'views/sale_order_view.xml',
		'views/purchase_order_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
