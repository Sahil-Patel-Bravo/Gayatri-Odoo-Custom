# -- coding: utf-8 --

{
	'name': 'Import Stock',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Import Stock',
	'description': """Import Stock""",
	'category': 'Inventory',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','stock'],
	'data': [
		'security/ir.model.access.csv',
		'wizard/import_stock_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
