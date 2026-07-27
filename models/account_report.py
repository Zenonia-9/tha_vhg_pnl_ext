# -*- coding: utf-8 -*-

from odoo import models


class AccountReport(models.Model):
    _inherit = "account.report"

    def _get_lines(self, options, all_column_groups_expression_totals=None, warnings=None):
        lines = super()._get_lines(
            options,
            all_column_groups_expression_totals=all_column_groups_expression_totals,
            warnings=warnings,
        )
        notes_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss", raise_if_not_found=False
        )
        if self == notes_report and options.get("vhg_notes_native_xlsx"):
            for line in lines:
                if line.get("level") == 1 and line.get("unfoldable"):
                    line["columns"] = [
                        {
                            **column,
                            "name": "",
                            "no_format": None,
                            "comparison_mode": None,
                        }
                        for column in line["columns"]
                    ]
        return lines

    def _init_options_horizontal_groups(self, options, previous_options):
        super()._init_options_horizontal_groups(options, previous_options)
        notes_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss", raise_if_not_found=False
        )
        source_report = self.env.ref("account_reports.profit_and_loss", raise_if_not_found=False)
        summary_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary", raise_if_not_found=False
        )
        if self not in (notes_report, summary_report) or not source_report:
            return

        horizontal_groups = source_report.horizontal_group_ids
        options["available_horizontal_groups"] = [
            {"id": horizontal_group.id, "name": horizontal_group.name}
            for horizontal_group in horizontal_groups
        ]
        previous_selected = previous_options.get("selected_horizontal_group_id")
        options["selected_horizontal_group_id"] = (
            previous_selected if previous_selected in horizontal_groups.ids else None
        )

    def _inject_report_into_xlsx_sheet(self, options, workbook, sheet):
        notes_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss", raise_if_not_found=False
        )
        summary_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary", raise_if_not_found=False
        )
        if self not in (notes_report, summary_report):
            return super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

        print_options = self.get_options({**options, "export_mode": "file"})
        lines = self._get_lines(print_options)
        header = workbook.add_format({
            "bold": True, "border": 1, "border_color": "#B4C7E7",
            "align": "center", "valign": "vcenter", "font_color": "#FFFFFF",
            "bg_color": "#1F4E78",
        })
        text = workbook.add_format({"border": 1, "border_color": "#D9E2F3"})
        total_text = workbook.add_format({
            "border": 1, "border_color": "#A9D18E", "bold": True,
            "font_color": "#1E4D2B", "bg_color": "#E2F0D9",
        })
        number = workbook.add_format({"border": 1, "border_color": "#D9E2F3", "num_format": "#,##0.00"})
        total_number = workbook.add_format({
            "border": 1, "border_color": "#A9D18E", "bold": True,
            "font_color": "#1E4D2B", "bg_color": "#E2F0D9", "num_format": "#,##0.00",
        })
        percentage = workbook.add_format({"border": 1, "border_color": "#D9E2F3", "num_format": "0.00%"})
        total_percentage = workbook.add_format({
            "border": 1, "border_color": "#A9D18E", "bold": True,
            "font_color": "#1E4D2B", "bg_color": "#E2F0D9", "num_format": "0.00%",
        })
        green_number = workbook.add_format({
            "border": 1, "bold": True, "bg_color": "#A9D18E", "num_format": "#,##0.00",
        })
        green_percentage = workbook.add_format({
            "border": 1, "bold": True, "bg_color": "#A9D18E", "num_format": "0.00%",
        })

        columns = print_options["columns"]
        monetary_factor = self._vhg_xlsx_rounding_factor(print_options)
        if self == notes_report:
            native_options = {
                **print_options,
                "unfold_all": True,
                "vhg_notes_native_xlsx": True,
            }
            native_options["column_headers"] = [
                [{
                    "name": print_options["vhg_notes_company_names"],
                    "colspan": len(columns),
                }],
                [{
                    "name": print_options["vhg_notes_report_title"],
                    "colspan": len(columns),
                }],
                *print_options["column_headers"],
            ]
            return super()._inject_report_into_xlsx_sheet(
                native_options, workbook, sheet
            )

        title_row = self._write_vhg_xlsx_title(
            print_options, workbook, sheet, len(columns), self.name,
        )
        if print_options.get("vhg_summary_horizontal_mode"):
            sheet.merge_range(title_row, 0, title_row + 1, 0, "No.", header)
            sheet.merge_range(title_row, 1, title_row + 1, 1, "Particular", header)
            x_offset = 2
            for group_header in print_options["vhg_summary_horizontal_headers"]:
                sheet.merge_range(
                    title_row, x_offset, title_row, x_offset + group_header.get("colspan", 2) - 1,
                    group_header["name"], header,
                )
                x_offset += group_header.get("colspan", 2)
            for x, column in enumerate(columns[1:], start=2):
                sheet.write(title_row + 1, x, column["name"], header)
            sheet.set_column(0, len(columns), 14)
            sheet.set_column(1, 1, 34)
            for y, line in enumerate(lines, start=title_row + 2):
                is_total = line.get("level") == 0
                values = (
                    line["columns"][:1]
                    + [{"no_format": line["name"], "figure_type": "string"}]
                    + line["columns"][1:]
                )
                self._write_vhg_summary_xlsx_row(
                    sheet, y, values, is_total,
                    text, total_text, number, total_number, percentage, total_percentage,
                    monetary_factor,
                    line["name"],
                )
            return

        actual_month_count = len(print_options["vhg_summary_month_keys"])
        budget_month_count = len(print_options["vhg_summary_budget_month_keys"])
        sheet.merge_range(title_row, 0, title_row, 5, print_options["vhg_summary_mtd_label"], header)
        sheet.merge_range(title_row, 6, title_row + 1, 6, "No.", header)
        sheet.merge_range(title_row, 7, title_row + 1, 7, "Particular", header)
        sheet.merge_range(title_row, 8, title_row, 9, print_options["vhg_summary_ytd_actual_label"], header)
        if actual_month_count:
            sheet.merge_range(title_row, 10, title_row, 9 + actual_month_count, "Monthly Actual", header)
        budget_month_start = 10 + actual_month_count
        if budget_month_count:
            sheet.merge_range(
                title_row, budget_month_start, title_row, budget_month_start + budget_month_count - 1,
                "Monthly Budget", header,
            )
        ytd_budget_start = budget_month_start + budget_month_count
        sheet.merge_range(
            title_row,
            ytd_budget_start,
            title_row,
            ytd_budget_start + 3,
            print_options["vhg_summary_ytd_budget_label"],
            header,
        )
        subheaders = columns[:6] + columns[7:]
        subheader_positions = list(range(6)) + list(range(8, 8 + len(columns) - 7))
        for x, column in zip(subheader_positions, subheaders):
            sheet.write(title_row + 1, x, column["name"], header)
        labels = columns[:7] + [{"name": "Particular"}] + columns[7:]
        sheet.set_column(0, len(labels) - 1, 14)
        sheet.set_column(7, 7, 34)

        for y, line in enumerate(lines, start=title_row + 2):
            is_total = line.get("level") == 0
            values = line["columns"][:7] + [{"no_format": line["name"], "figure_type": "string"}] + line["columns"][7:]
            self._write_vhg_summary_xlsx_row(
                sheet, y, values, is_total,
                text, total_text, number, total_number, percentage, total_percentage,
                monetary_factor,
                line["name"],
            )

    def _write_vhg_xlsx_title(self, options, workbook, sheet, last_column, report_name):
        title = workbook.add_format({"bold": True, "font_size": 12, "align": "center"})
        company = workbook.add_format({"bold": True, "align": "center"})
        unit = workbook.add_format({"bold": True, "align": "right"})
        company_ids = self.get_report_company_ids(options)
        companies = self.env["res.company"].browse(company_ids)
        company_names = ", ".join(companies.mapped("name")) or self.env.company.name
        currency = companies[:1].currency_id or self.env.company.currency_id
        currency_name = "Kyats" if currency.name == "MMK" else currency.name
        unit_name = {
            "thousands": "Thousand",
            "lakhs": "Lakh",
            "millions": "Million",
        }.get(options.get("rounding_unit"), "")
        unit_label = f"{currency_name} in {unit_name}" if unit_name else currency_name
        if last_column > 1:
            company_end = last_column - 2
            if company_end:
                sheet.merge_range(0, 0, 0, company_end, company_names, company)
            else:
                sheet.write(0, 0, company_names, company)
            sheet.merge_range(0, last_column - 1, 0, last_column, unit_label, unit)
        else:
            sheet.write(0, 0, company_names, company)
            sheet.write(0, last_column, unit_label, unit)
        report_title = (
            options.get("vhg_summary_xlsx_report_title")
            or options.get("vhg_notes_report_title")
            or report_name
        )
        sheet.merge_range(1, 0, 1, last_column, report_title, title)
        return 3

    @staticmethod
    def _vhg_xlsx_rounding_factor(options):
        return {
            "thousands": 1_000.0,
            "lakhs": 100_000.0,
            "millions": 1_000_000.0,
        }.get(options.get("rounding_unit"), 1.0)

    @staticmethod
    def _write_vhg_summary_xlsx_row(
        sheet, y, values, is_total,
        text, total_text, number, total_number, percentage, total_percentage,
        monetary_factor, line_name,
    ):
        row_formats = (
            (total_text, total_number, total_percentage)
            if is_total or line_name.startswith("Total ")
            else (text, number, percentage)
        )
        text_format, number_format, percentage_format = row_formats
        for x, cell in enumerate(values):
            value = cell.get("no_format")
            figure_type = cell.get("figure_type")
            if figure_type == "percentage" and value is not None:
                value /= 100.0
                cell_format = percentage_format
            elif isinstance(value, (int, float)):
                value /= monetary_factor
                cell_format = number_format
            else:
                cell_format = text_format
            sheet.write(y, x, value if value is not None else "", cell_format)
