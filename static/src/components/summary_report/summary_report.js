/** @odoo-module **/

import { AccountReport } from "@account_reports/components/account_report/account_report";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";


export class VhgPnlSummaryFilters extends AccountReportFilters {
    static template = "tha_vhg_pnl_ext.SummaryReportFilters";

    async toggleMonthlyColumns() {
        await this.filterClicked({
            optionKey: "vhg_show_monthly_columns",
            reload: true,
        });
    }

    async toggleZeroMonthlyColumns() {
        await this.filterClicked({
            optionKey: "vhg_hide_zero_monthly_columns",
            reload: true,
        });
    }

    selectBudget(budget) {
        const selectBudget = !budget.selected;
        for (const candidate of this.controller.cachedFilterOptions.budgets) {
            candidate.selected = selectBudget && candidate.id === budget.id;
        }
        this.applyFilters("budgets");
    }
}

AccountReport.registerCustomComponent(VhgPnlSummaryFilters);
