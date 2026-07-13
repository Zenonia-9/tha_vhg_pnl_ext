# Run with: odoo shell -d THA < scripts/seed_summary_demo_budget.py
result = env["tha.vhg.pnl.summary.report.handler"].seed_demo_budget()
env.cr.commit()
print(result)
