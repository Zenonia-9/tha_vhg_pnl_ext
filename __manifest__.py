# -*- coding: utf-8 -*-
{
    "name": "VHG Profit and Loss Extension",
    "summary": "Workbook-aligned VHG Profit and Loss notes and management summary reports.",
    "version": "19.0.1.1.5",
    "category": "Accounting/Accounting",
    "author": "Thein Htoo Aung",
    "license": "LGPL-3",
    "depends": ["account_reports", "analytic"],
    "data": [
        "data/profit_and_loss_report.xml",
        "data/profit_and_loss_summary_report.xml",
        "report/profit_and_loss_summary_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "tha_vhg_pnl_ext/static/src/components/summary_report/summary_report.js",
            "tha_vhg_pnl_ext/static/src/components/summary_report/summary_report.xml",
            "tha_vhg_pnl_ext/static/src/components/summary_report/summary_report.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
