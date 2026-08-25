from datetime import datetime, date
import calendar


def add_months_from_today(d: date, months: int):
    # Primero tengo que restar 1 al mes
    month = d.month - 1 + months  # Pasamos de rango (1-12) a (0-11) para poder usar %
    year = d.year + month // 12  # En los meses, cuantos años han pasado?
    month = (
        month % 12 + 1
    )  # Cuantos meses del nuevo año hay? y sumar 1 para volver a rango de fecha (1-12)
    day = min(
        d.day, calendar.monthrange(month=month, year=year)[1]
    )  # O bien el día si esta en el rango de la nueva fecha, o el ultimo día de ese mes.

    nf = date(day=day, month=month, year=year)
    return datetime(day=nf.day, month=nf.month, year=nf.year)


v = add_months_from_today(date.today(), 19)
dia = calendar.monthrange(v.day, v.month)[0]
semana = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}
print(semana[dia])
