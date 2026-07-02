from src.models.household import Household

from src.models.income_entry import IncomeEntry


class IncomeEntryService:
    @staticmethod
    def add_income_entry(income_entry: IncomeEntry, household: Household):

        household._income_entries.append(income_entry)

        household.recalculate_reserve()
