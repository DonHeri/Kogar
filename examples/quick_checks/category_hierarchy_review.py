"""
REVIEW — Jerarquía de categorías

Espejo de inspección para ir viendo cómo queda la jerarquía padre→hijo
cada vez que toques el modelo (Budget / BudgetCategory / CategoryLibrary).

NO usa WorkflowManager ni BD: ataca Budget directamente, en memoria pura,
porque la feature todavía vive a nivel de dominio. Solo LEE lo que tus
clases exponen y lo dibuja — si cambias la API, cambia este script.

Uso:
    python examples/category_hierarchy_review.py
"""

from src.models.budget import Budget
from src.utils.currency import to_cents, to_euros


def print_tree(budget: Budget) -> None:
    """Dibuja las categorías como árbol siguiendo el campo `parent`.

    Construye un mapa padre -> [hijos] a partir de budget.categories y
    recorre desde las raíces (parent is None) hacia abajo, a cualquier
    profundidad.
    """
    children: dict[str | None, list] = {}
    for bc in budget.categories.values():
        children.setdefault(bc.parent, []).append(bc)

    def walk(parent_name: str | None, depth: int) -> None:
        for bc in children.get(parent_name, []):
            indent = "  " * depth
            shared = "compartida" if bc.is_shared else "personal"
            print(
                f"{indent}- {bc.name:<14} {to_euros(bc.planned_amount):>10}  ({shared})"
            )
            walk(bc.name, depth + 1)

    walk(None, 0)

    # Aviso si algún parent apunta a una categoría que no existe
    # (no debería pasar: add_category valida, pero el espejo lo delata).
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

    # --- Raíces: las estándar (fijos / variables / reserva) ---
    budget.set_standard_categories()

    # --- Hijas: cuelga subcategorías de las raíces ---
    # Suministros y vivienda bajo "fijos"
    budget.add_category("vivienda", parent="fijos")
    budget.add_category("suministros", parent="fijos")
    # Día a día bajo "variables"
    budget.add_category("salud", parent="variables")
    budget.add_category("transporte", parent="variables")
    # Custom (no está en la librería) bajo una hija -> dos niveles
    budget.add_category("gasolina", parent="transporte")

    # --- Algunos importes para ver que el dinero viaja por el árbol ---
    
    budget.set_budget("vivienda", to_cents(800.00))
    budget.set_budget("suministros", to_cents(130.50))
    budget.set_budget("salud", to_cents(60.00))
    budget.set_budget("gasolina", to_cents(90.00))

    print("=" * 50)
    print("JERARQUÍA DE CATEGORÍAS")
    print("=" * 50)
    print_tree(budget)

    print("\n" + "-" * 50)
    print(f"Categorías activas: {len(budget.get_categories_list())}")
    print(f"Total presupuestado: {to_euros(budget.get_total_budgeted())}")


if __name__ == "__main__":
    main()
