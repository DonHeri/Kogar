"""
REVIEW — Jerarquía de categorías

Espejo de inspección para ir viendo cómo queda la jerarquía padre→hijo
cada vez que toques el modelo (Budget / BudgetCategory / CategoryLibrary).

NO usa WorkflowManager ni BD: ataca Budget y ExpenseTracker directamente,
en memoria pura. Solo LEE lo que tus clases exponen y lo dibuja — si
cambias la API, cambia este script.

Uso:
    python examples/quick_checks/category_hierarchy_review.py
"""

from src.models.budget import Budget
from src.models.category import Category
from src.models.expense import Expense
from src.models.expense_tracker import ExpenseTracker
from src.utils.currency import to_cents, to_euros


def print_tree(budget: Budget, tracker: ExpenseTracker, members: list[str]) -> None:
    children: dict[str | None, list] = {}
    for bc in budget.categories.values():
        children.setdefault(bc.parent, []).append(bc)

    def walk(parent_name: str | None, depth: int) -> None:
        for bc in children.get(parent_name, []):
            indent = "  " * depth
            planned = to_euros(bc.planned_amount)
            spent = to_euros(tracker.get_total_spent_by_category(bc.name))

            member_parts = []
            for m in members:
                amount = tracker.get_total_spent_by_member_and_category(m, bc.name)
                if amount:
                    member_parts.append(f"{m}: {to_euros(amount)}")
            member_str = f"  [{', '.join(member_parts)}]" if member_parts else ""

            print(
                f"{indent}- {bc.name:<14}  plan {planned:>8}  gast {spent:>8}{member_str}"
            )
            walk(bc.name, depth + 1)

    walk(None, 0)

    known = set(budget.categories.keys())
    orphans = [
        bc.name
        for bc in budget.categories.values()
        if bc.parent is not None and bc.parent not in known
    ]
    if orphans:
        print(f"\n[!] Huérfanas (parent inexistente): {', '.join(orphans)}")


def main() -> None:
    budget = Budget()

    budget.set_standard_categories()
    budget.add_category("vivienda", parent="fijos")
    budget.add_category("suministros", parent="fijos")
    budget.add_category("salud", parent="variables")
    budget.add_category("transporte", parent="variables")
    budget.add_category("gasolina", parent="transporte")

    budget.set_planned_amount("fijos", to_cents(930.50))
    budget.set_planned_amount("vivienda", to_cents(800.00))
    budget.set_planned_amount("suministros", to_cents(130.50))
    budget.set_planned_amount("salud", to_cents(60.00))
    budget.set_planned_amount("gasolina", to_cents(90.00))

    members = ["heri", "ana"]

    tracker = ExpenseTracker()
    tracker.add_expense(
        Expense("heri", Category("gasolina"), to_cents(45.00), ["heri"])
    )
    tracker.add_expense(Expense("ana", Category("gasolina"), to_cents(30.00), ["ana"]))
    tracker.add_expense(
        Expense("heri", Category("salud"), to_cents(60.00), ["heri", "ana"])
    )
    tracker.add_expense(
        Expense("ana", Category("vivienda"), to_cents(800.00), ["heri", "ana"])
    )
    tracker.add_expense(
        Expense("heri", Category("suministros"), to_cents(55.00), ["heri"])
    )
    tracker.add_expense(
        Expense("ana", Category("suministros"), to_cents(40.00), ["ana"])
    )

    print("=" * 60)
    print("JERARQUÍA DE CATEGORÍAS")
    print("=" * 60)
    print_tree(budget, tracker, members)

    print("\n" + "-" * 60)
    print(f"Categorías activas:  {len(budget.get_category_names())}")
    print(f"Total presupuestado: {to_euros(budget.get_total_budgeted())}")
    print(f"Total gastado:       {to_euros(tracker.get_total_spent())}")


if __name__ == "__main__":
    main()
