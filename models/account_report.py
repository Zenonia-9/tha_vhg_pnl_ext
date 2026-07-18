# -*- coding: utf-8 -*-

from odoo import models


class AccountReport(models.Model):
    _inherit = "account.report"

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
        summary_report = self.env.ref(
            "tha_vhg_pnl_ext.report_vhg_profit_and_loss_summary", raise_if_not_found=False
        )
        if self != summary_report:
            return super()._inject_report_into_xlsx_sheet(options, workbook, sheet)

        print_options = self.get_options({**options, "export_mode": "file"})
        lines = self._get_lines(print_options)
        header = workbook.add_format({
            "bold": True, "border": 1, "align": "center", "valign": "vcenter",
            "bg_color": "#FFF2CC",
        })
        text = workbook.add_format({"border": 1})
        total_text = workbook.add_format({"border": 1, "bold": True})
        number = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        total_number = workbook.add_format({"border": 1, "bold": True, "num_format": "#,##0.00"})
        percentage = workbook.add_format({"border": 1, "num_format": "0.00%"})
        total_percentage = workbook.add_format({"border": 1, "bold": True, "num_format": "0.00%"})

        columns = print_options["columns"]
        monetary_factor = self._vhg_xlsx_rounding_factor(print_options)
        if print_options.get("vhg_summary_horizontal_mode"):
            sheet.merge_range(0, 0, 1, 0, "No.", header)
            sheet.merge_range(0, 1, 1, 1, "Particular", header)
            x_offset = 2
            for group_header in print_options["vhg_summary_horizontal_headers"]:
                sheet.merge_range(
                    0, x_offset, 0, x_offset + group_header.get("colspan", 2) - 1,
                    group_header["name"], header,
                )
                x_offset += group_header.get("colspan", 2)
            for x, column in enumerate(columns[1:], start=2):
                sheet.write(1, x, column["name"], header)
            sheet.set_column(0, len(columns), 14)
            sheet.set_column(1, 1, 34)
            for y, line in enumerate(lines, start=2):
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
                )
            return

        actual_month_count = len(print_options["vhg_summary_month_keys"])
        budget_month_count = len(print_options["vhg_summary_budget_month_keys"])
        sheet.merge_range(0, 0, 0, 5, print_options["vhg_summary_mtd_label"], header)
        sheet.merge_range(0, 6, 1, 6, "No.", header)
        sheet.merge_range(0, 7, 1, 7, "Particular", header)
        sheet.merge_range(0, 8, 0, 9, print_options["vhg_summary_ytd_actual_label"], header)
        if actual_month_count:
            sheet.merge_range(0, 10, 0, 9 + actual_month_count, "Monthly Actual", header)
        budget_month_start = 10 + actual_month_count
        if budget_month_count:
            sheet.merge_range(
                0, budget_month_start, 0, budget_month_start + budget_month_count - 1,
                "Monthly Budget", header,
            )
        ytd_budget_start = budget_month_start + budget_month_count
        sheet.merge_range(
            0,
            ytd_budget_start,
            0,
            ytd_budget_start + 3,
            print_options["vhg_summary_ytd_budget_label"],
            header,
        )
        subheaders = columns[:6] + columns[7:]
        subheader_positions = list(range(6)) + list(range(8, 8 + len(columns) - 7))
        for x, column in zip(subheader_positions, subheaders):
            sheet.write(1, x, column["name"], header)
        labels = columns[:7] + [{"name": "Particular"}] + columns[7:]
        sheet.set_column(0, len(labels) - 1, 14)
        sheet.set_column(7, 7, 34)

        for y, line in enumerate(lines, start=2):
            is_total = line.get("level") == 0
            values = line["columns"][:7] + [{"no_format": line["name"], "figure_type": "string"}] + line["columns"][7:]
            self._write_vhg_summary_xlsx_row(
                sheet, y, values, is_total,
                text, total_text, number, total_number, percentage, total_percentage,
                monetary_factor,
            )

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
        monetary_factor,
    ):
        for x, cell in enumerate(values):
            value = cell.get("no_format")
            figure_type = cell.get("figure_type")
            if figure_type == "percentage" and value is not None:
                value /= 100.0
                cell_format = total_percentage if is_total else percentage
            elif isinstance(value, (int, float)):
                value /= monetary_factor
                cell_format = total_number if is_total else number
            else:
                cell_format = total_text if is_total else text
            sheet.write(y, x, value if value is not None else "", cell_format)
