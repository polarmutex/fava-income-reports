import datetime
import yaml
from typing import List, Tuple
from collections import defaultdict
from decimal import Decimal
from beancount.query.query import run_query
from fava.ext import FavaExtensionBase
from fava.helpers import FavaAPIException


class MonthlyPnL(FavaExtensionBase):

    report_title = "Monthly PnL"

    @staticmethod
    def _iter_months(start: Tuple[int], end: Tuple[int]):
        """returns a list of months (tuples of year, month) between start and end"""
        year, month = start
        yield (year, month)
        while (year, month) != end:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            yield (year, month)

    def _query(self, where: str, months: List[Tuple], invert=False):
        """executes a query and returns values grouped by the requested months"""
        bql = f"SELECT year, month, CONVERT(VALUE(SUM(position)), 'EUR') AS val WHERE {where} GROUP BY year, month"
        _, rrows = run_query(self.ledger.entries, self.ledger.options, bql)
        data = defaultdict(Decimal)
        for row in rrows:
            if not row.val.is_empty():
                data[(row.year, row.month)] = row.val.get_only_position().units.number
        inv = -1 if invert else 1
        return [inv * data[month] for month in months]

    def monthly_pnl(self, chart_id):
        date_first = self.ledger._date_first
        date_last = self.ledger._date_last - datetime.timedelta(days=1)

        months = list(self._iter_months((date_first.year, date_first.month), (date_last.year, date_last.month)))
        xaxis = [f"{month:02d}/{year}" for year, month in months]
        operating_currency = self.ledger.options["operating_currency"][0]

        config_file = "monthly_pnl.yaml"
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as ex:
            raise FavaAPIException(f"Cannot read configuration file {config_file}: " + str(ex))

        chart = config[chart_id]
        all_series = []
        for stack_name, stack_items in chart["series"].items():
            stack_series = []
            for series in stack_items:
                invert = series.get("invert", False)
                if "account" in series:
                    query = f"account ~ '^{series['account']}'"
                    link = f"/beancount/account/{series['account']}/"
                    data = self._query(query, months, invert)
                elif "query" in series:
                    query = series["query"]
                    link = series.get("link")
                    data = self._query(query, months, invert)
                elif "type" in series:
                    if series["type"] == "other_income":
                        query = f"account ~ '^Income'"
                    elif series["type"] == "other_expenses":
                        query = f"account ~ '^Expenses'"
                    else:
                        raise FavaAPIException(
                            "Invalid value for type parameter. Allowed values: 'other_income' and 'other_expenses'."
                        )
                    link = series.get("link")
                    data = self._query(query, months, invert)
                    for i in range(len(data)):
                        data[i] -= sum(s["data"][i] for s in stack_series)
                else:
                    raise FavaAPIException("Neither 'query', 'account' or 'type' found in series definition.")

                stack_series.append(
                    {
                        "name": series.get("name", "Unnamed"),
                        "stack": stack_name,
                        "link": link,
                        "color": series.get("color"),
                        "data": data,
                    }
                )
            all_series.extend(stack_series)

        return {
            "config": config,
            "currency": operating_currency,
            "chart": {"xaxis": xaxis, "series": all_series},
        }
