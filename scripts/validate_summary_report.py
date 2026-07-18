from datetime import date
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile


def column_name(number):
    name = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name


company = env["res.company"].search([
    ("name", "ilike", "THUKHA SAYTANAR CO. Ltd"),
], limit=1)
report = env.ref("tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary").with_company(company).with_context(
    allowed_company_ids=[company.id]
)
budget = env["account.report.budget"].sudo().with_company(company).search([
    ("name", "=", "VHG Summary Demo Budget JUL 26"),
], limit=1)
assert budget, "Demo budget is missing"
fy_budget = env["account.report.budget"].sudo().with_company(company).search([
    ("name", "=", "VHG Summary Demo Budget FY2026-27"),
], limit=1)
assert fy_budget and len(fy_budget.item_ids) == 2832

base_previous = {
    "date": {
        "date_from": "2026-07-01",
        "date_to": "2026-07-31",
        "filter": "custom",
        "mode": "range",
    },
}
no_budget_options = report.get_options(base_previous)
no_budget_lines = report._get_lines(no_budget_options)
assert no_budget_options["vhg_hide_zero_monthly_columns"] is True
assert [column["name"] for column in no_budget_options["columns"][:9]] == [
    "Jul 2026", "%", "Budget", "%", "Variance", "%", "No.", "Actual", "%",
]
assert len(no_budget_lines) == 27, len(no_budget_lines)
assert all(not line.get("unfoldable") for line in no_budget_lines)
assert all(not line.get("expand_function") for line in no_budget_lines)
number_cells = [line["columns"][6]["no_format"] for line in no_budget_lines]
assert [number for number in number_cells if number] == [
    *[str(number) for number in range(1, 15)],
    "14.1",
    *[str(number) for number in range(15, 18)],
]
assert not no_budget_options["filters"]["show_period_comparison"]
assert not no_budget_options["filters"]["show_all"]
assert no_budget_options["vhg_summary_ytd_month_keys"] == [
    "actual_2026_04", "actual_2026_05", "actual_2026_06", "actual_2026_07",
]
assert no_budget_options["vhg_summary_month_keys"] == [
    "actual_2026_06", "actual_2026_07",
]
assert no_budget_options["vhg_summary_budget_month_keys"] == []
assert no_budget_options["vhg_summary_fiscal_month_keys"] == [
    f"actual_{year}_{month:02d}"
    for year, month in [(2026, month) for month in range(4, 13)] + [(2027, month) for month in range(1, 4)]
]
budget_labels = {"mtd_budget", "mtd_budget_percent", "mtd_variance", "mtd_variance_percent", "ytd_budget", "ytd_budget_percent", "ytd_variance", "ytd_variance_percent"}
for line in no_budget_lines:
    for column, cell in zip(no_budget_options["columns"], line["columns"]):
        if column["expression_label"] in budget_labels:
            assert cell["no_format"] is None

budget_previous = dict(base_previous)
budget_previous["budgets"] = [{"id": fy_budget.id, "selected": True}]
budget_options = report.get_options(budget_previous)
budget_lines = report._get_lines(budget_options)
assert len(budget_lines) == 27
assert any(
    cell.get("no_format")
    for line in budget_lines
    for column, cell in zip(budget_options["columns"], line["columns"])
    if column["expression_label"] == "mtd_budget"
)

expanded_options = report.get_options({
    **budget_previous,
    "vhg_show_monthly_columns": True,
})
assert expanded_options["vhg_summary_month_keys"] == [
    "actual_2026_04", "actual_2026_05", "actual_2026_06", "actual_2026_07",
]
assert expanded_options["vhg_summary_budget_month_keys"] == [
    "budget_2026_04", "budget_2026_05", "budget_2026_06", "budget_2026_07",
]
expanded_lines = report._get_lines(expanded_options)
assert any(
    cell.get("no_format")
    for line in expanded_lines
    for column, cell in zip(expanded_options["columns"], line["columns"])
    if column["expression_label"] == "budget_month_2026_07"
)

june_expanded_options = report.get_options({
    "date": {
        "date_from": "2026-06-01",
        "date_to": "2026-06-30",
        "filter": "custom",
        "mode": "range",
    },
    "budgets": [{"id": fy_budget.id, "selected": True}],
    "vhg_show_monthly_columns": True,
})
assert june_expanded_options["vhg_summary_budget_month_keys"] == [
    "budget_2026_04", "budget_2026_05", "budget_2026_06",
]
no_budget_expanded_options = report.get_options({
    **base_previous,
    "vhg_show_monthly_columns": True,
})
assert no_budget_expanded_options["vhg_summary_budget_month_keys"] == [
    "budget_2026_04", "budget_2026_05", "budget_2026_06", "budget_2026_07",
]
assert all(
    cell["no_format"] is None
    for line in report._get_lines(no_budget_expanded_options)
    for column, cell in zip(no_budget_expanded_options["columns"], line["columns"])
    if column["expression_label"].startswith("budget_month_")
)
show_zero_options = report.get_options({
    **budget_previous,
    "vhg_show_monthly_columns": True,
    "vhg_hide_zero_monthly_columns": False,
})
assert show_zero_options["vhg_hide_zero_monthly_columns"] is False
assert show_zero_options["vhg_summary_month_keys"] == [
    f"actual_{year}_{month:02d}"
    for year, month in [(2026, month) for month in range(4, 13)] + [(2027, month) for month in range(1, 4)]
]
assert show_zero_options["vhg_summary_budget_month_keys"] == [
    "budget_2026_04", "budget_2026_05", "budget_2026_06", "budget_2026_07",
]
handler = env["tha.vhg.pnl.summary.report.handler"]
assert not handler._month_has_actual({"test": {"actual_2026_04": 0.0}}, date(2026, 4, 1))
assert handler._month_has_actual({"test": {"actual_2026_04": 1.0}}, date(2026, 4, 1))

zero_period = {
    "date": {
        "date_from": "2099-07-01",
        "date_to": "2099-07-31",
        "filter": "custom",
        "mode": "range",
    },
}
hidden_zero_options = report.get_options(zero_period)
assert hidden_zero_options["vhg_summary_month_keys"] == []
shown_zero_options = report.get_options({
    **zero_period,
    "vhg_hide_zero_monthly_columns": False,
})
assert shown_zero_options["vhg_summary_month_keys"] == [
    "actual_2099_06", "actual_2099_07",
]

horizontal_group = env.ref("account_reports.profit_and_loss").horizontal_group_ids[:1]
assert horizontal_group, "No Profit and Loss horizontal group is configured"
other_company_ids = env["res.company"].search([("id", "!=", company.id)]).ids
consolidated_report = report.with_context(
    allowed_company_ids=[company.id, *other_company_ids]
)
multi_company_options = consolidated_report.get_options(base_previous)
assert multi_company_options["vhg_summary_horizontal_mode"] is False
assert consolidated_report._get_lines(multi_company_options)
horizontal_options = consolidated_report.get_options({
    **budget_previous,
    "selected_horizontal_group_id": horizontal_group.id,
})
horizontal_lines = consolidated_report._get_lines(horizontal_options)
entities = horizontal_options["vhg_summary_horizontal_entities"]
assert horizontal_options["vhg_summary_horizontal_mode"] is True
assert horizontal_options["selected_horizontal_group_id"] == horizontal_group.id
assert entities
assert len(horizontal_options["columns"]) == 1 + (2 * len(entities)) + 6
assert [column["name"] for column in horizontal_options["columns"][:3]] == [
    "No.", horizontal_options["vhg_summary_horizontal_period_label"], "%",
]
assert len(horizontal_lines) == 27
assert all(not line.get("unfoldable") for line in horizontal_lines)
consolidated_index = 1 + (2 * len(entities))
for line in horizontal_lines:
    entity_total = sum(
        line["columns"][1 + (2 * index)]["no_format"] or 0.0
        for index in range(len(entities))
    )
    assert abs(line["columns"][consolidated_index]["no_format"] - entity_total) < 0.01

horizontal_expanded_options = consolidated_report.get_options({
    **budget_previous,
    "selected_horizontal_group_id": horizontal_group.id,
    "vhg_show_monthly_columns": True,
})
horizontal_expanded_lines = consolidated_report._get_lines(horizontal_expanded_options)
assert horizontal_expanded_options["vhg_summary_month_keys"] == [
    "actual_2026_04", "actual_2026_05", "actual_2026_06", "actual_2026_07",
]
assert any(
    header["name"].startswith("Monthly Conso")
    and header["colspan"] == len(horizontal_expanded_options["vhg_summary_month_keys"])
    for header in horizontal_expanded_options["vhg_summary_horizontal_headers"]
)
assert len(horizontal_expanded_options["columns"]) == (
    len(horizontal_options["columns"])
    + len(horizontal_expanded_options["vhg_summary_month_keys"])
)
horizontal_show_zero_options = consolidated_report.get_options({
    **budget_previous,
    "selected_horizontal_group_id": horizontal_group.id,
    "vhg_show_monthly_columns": True,
    "vhg_hide_zero_monthly_columns": False,
})
assert horizontal_show_zero_options["vhg_summary_month_keys"] == [
    f"actual_{year}_{month:02d}"
    for year, month in [(2026, month) for month in range(4, 13)] + [(2027, month) for month in range(1, 4)]
]
monthly_start = consolidated_index + 2
monthly_end = monthly_start + len(horizontal_expanded_options["vhg_summary_month_keys"])
for line in horizontal_expanded_lines:
    monthly_total = sum(
        cell["no_format"] or 0.0
        for cell in line["columns"][monthly_start:monthly_end]
    )
    assert abs(line["columns"][consolidated_index]["no_format"] - monthly_total) < 0.01

horizontal_xlsx = consolidated_report.export_to_xlsx(horizontal_options)
assert len(horizontal_xlsx["file_content"]) > 1000
with ZipFile(BytesIO(horizontal_xlsx["file_content"])) as workbook:
    worksheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    assert b'A1:A2' in worksheet_xml
    assert b'B1:B2' in worksheet_xml
    start = 3
    for header in horizontal_options["vhg_summary_horizontal_headers"]:
        end = start + header["colspan"] - 1
        merged_range = f"{column_name(start)}1:{column_name(end)}1".encode()
        assert merged_range in worksheet_xml, merged_range
        start = end + 1
horizontal_expanded_xlsx = consolidated_report.export_to_xlsx(horizontal_expanded_options)
with ZipFile(BytesIO(horizontal_expanded_xlsx["file_content"])) as workbook:
    worksheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    start = 3
    for header in horizontal_expanded_options["vhg_summary_horizontal_headers"]:
        end = start + header["colspan"] - 1
        merged_range = f"{column_name(start)}1:{column_name(end)}1".encode()
        assert merged_range in worksheet_xml, merged_range
        start = end + 1
horizontal_pdf = consolidated_report.export_to_pdf(horizontal_options)
assert len(horizontal_pdf["file_content"]) > 1000
horizontal_expanded_pdf = consolidated_report.export_to_pdf(horizontal_expanded_options)
assert len(horizontal_expanded_pdf["file_content"]) > 1000

xlsx = report.export_to_xlsx(budget_options)
assert len(xlsx["file_content"]) > 1000
with ZipFile(BytesIO(xlsx["file_content"])) as workbook:
    worksheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    for merged_range in (b'A1:F1', b'G1:G2', b'H1:H2', b'I1:J1', b'K1:L1', b'M1:P1'):
        assert merged_range in worksheet_xml, merged_range
expanded_xlsx = report.export_to_xlsx(expanded_options)
with ZipFile(BytesIO(expanded_xlsx["file_content"])) as workbook:
    worksheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    for merged_range in (b'A1:F1', b'G1:G2', b'H1:H2', b'I1:J1', b'K1:N1', b'O1:R1', b'S1:V1'):
        assert merged_range in worksheet_xml, merged_range
pdf = report.export_to_pdf(budget_options)
assert len(pdf["file_content"]) > 1000

million_options = report.get_options({
    **budget_previous,
    "rounding_unit": "millions",
})
million_lines = report._get_lines(million_options)
total_revenue = next(line for line in million_lines if line["name"] == "Total Revenue")
assert total_revenue["columns"][1]["name"] == "100.00%"
assert total_revenue["columns"][1]["no_format"] == "100.00%"
million_xlsx = report.export_to_xlsx(million_options)
with ZipFile(BytesIO(million_xlsx["file_content"])) as workbook:
    worksheet = ElementTree.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    first_total_revenue_value = worksheet.find(".//x:c[@r='A6']/x:v", namespace)
    assert first_total_revenue_value is not None
    expected_millions = total_revenue["columns"][0]["no_format"] / 1_000_000.0
    assert abs(float(first_total_revenue_value.text) - expected_millions) < 0.000001

sequence_by_name = {
    line["name"]: line["columns"][6]["no_format"]
    for line in budget_lines
}
assert sequence_by_name["Sales & Marketing"] == "14"
assert sequence_by_name["Commission Expense"] == "14.1"
assert sequence_by_name["Depreciation & Amortization"] == "15"

print({
    "report_id": report.id,
    "line_count": len(budget_lines),
    "columns_default": len(budget_options["columns"]) + 1,
    "columns_expanded": len(expanded_options["columns"]) + 1,
    "xlsx_bytes": len(xlsx["file_content"]),
    "pdf_bytes": len(pdf["file_content"]),
    "first_line": budget_lines[0]["name"],
    "last_line": budget_lines[-1]["name"],
})
