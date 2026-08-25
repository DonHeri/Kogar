## Flujo de creación de presupuestos
ingresos
├── fijos compartidos    → % o monto
├── variables compartidos → % o monto
└── loose_money
    ├── deuda personal   → cada miembro declara la suya
    ├── ahorro personal  → el resto va aquí automáticamente
    └── restante → User transfiere a otra cat o miembro (fijos, variables, ahorro, deuda) - Futuro(gasto especial)


[Expense] - is_shared: bool  # default según categoría: fijos=True, variables=False, deuda=False
Categorías *fijos* y *variables* son SHARED, **ahorro y deuda** PERSONAL. Esto significa que gastos dentro de cada cat, heredan su flag de *DESTINATION* excepto variables, que por defecto expenses = PERSONAL.

La confusión puede nacer de pensar que hablamos de lo mismo, pero no, fijos y variables, los monto salen del metodo de reparto, el restante: cada miembre le dara un sitio
**Flujo de creación de presupuestos**
ingresos
├── fijos compartidos    → % o monto
├── variables compartidos → % o monto
└── loose_money
    ├── deuda personal   → cada miembro declara la suya
    ├── ahorro personal  → el resto va aquí automáticamente
    └── restante → User transfiere a otra cat o miembro (fijos, variables, ahorro, deuda) - Futuro(gasto especial)

Cuando vayamos a registrar gastos, es cuando user podrá realmente declarar que un gasto es personal o compartido, de ese modo, cuando queramos sacar el acuerdo entre miembros [settlement] solo tendremos que mirar aquello que tenga la bandera de SHARED. Permitiendo identificar si algun usuario ha llegado a su limite en algun gasto, producto de que el otro miembro debe pagarle algo.
De ese modo el flujo cobra vida, ya que si user 2 le envia 20 euros a user 1, porque se lo debia, user 1 tendrá 20 euros mas para gastar en personal.