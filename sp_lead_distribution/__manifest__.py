# -- coding: utf-8 --

{
	'name': 'SP Lead Distribution',
	'version': '1.0',
	'author': 'SP Technologies Solution',
	'summary': 'SP Lead Distribution',
	'description': """SP Lead Distribution""",
	'category': 'CRM',
	'website': 'https://sptechnologiessolution.com/',
	'depends': ['base','sale_crm','hr'],
	'data': [
		'demo/cron.xml',
		'security/ir.model.access.csv',
		'views/hr_employee_view.xml',
		'views/crm_view.xml',
	],
	'qweb': [],
	"license": 'LGPL-3',
	'images': ['static/description/icon.png'],
	'installable': True,
	'application': True,
	'auto_install': False,
	"maintainers": ['SP'],
}
