{
    'name': 'Almoutakamel_invoice ',
    'version': '1.0',
    'description': 'This module for  Almoutakamel invoice requirements',
    'summary': 'Almoutakamel Required Invoice ',
    'author': 'Mohannad Waheed',
    'sequence': 1,
    'license': 'LGPL-3',
    'category': 'accounting',
    'depends': [
        'base',
        'account',
        'web'
    ],
    'data': [
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/partner.xml",
        'templates/motakamel_extenal_layout.xml',
        'templates/report_invoice.xml',
    ],
    'demo': [
        'data/report_layout.xml'
    ],
    'installable': True,
    'application': True,
    'assets': {
        
    }
}
