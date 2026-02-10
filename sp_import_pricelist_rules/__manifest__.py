# -- coding: utf-8 --

{
	'name': 'Import Pricelist Rules',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Import Pricelist Rules',
	'description': """Import Pricelist Rules""",
	'category': 'Sales',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale'],
	'data': [
		'security/ir.model.access.csv',
		'wizard/import_pricelist_rules_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
