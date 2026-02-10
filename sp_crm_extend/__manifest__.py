# -- coding: utf-8 --

{
	'name': 'SP CRM Extend',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'Module For SP CRM Extend',
	'description': """SP CRM Extend""",
	'category': 'CRM',
	'website': 'https://sptechnologiessolution.com/',
	'license': 'AGPL-3',
	'depends': ['base','crm'],
	'data': [
		'views/crm_view.xml',
	],
	'qweb': [],
	"license": "LGPL-3",
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ["SP"],
}
