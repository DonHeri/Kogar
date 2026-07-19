from datetime import date
import calendar


def add_months(d: date, months: int) -> date:
    """Suma (o resta, si months es negativo) meses a una fecha.

    Ajusta el día al último válido del mes destino cuando no existe
    (31 ene + 1 mes -> 28/29 feb, según el año sea bisiesto o no).
    """
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)
