import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class TablaCustom(toga.Box):   # 👈 MUY IMPORTANTE
    def __init__(self, datos):
        super().__init__(style=Pack(direction=COLUMN))  # 👈 ahora sí funciona

        self.datos = datos

        # Cabecera
        self.add(self._crear_cabecera())

        # Scroll
        self.filas_box = toga.Box(style=Pack(direction=COLUMN))
        scroll = toga.ScrollContainer(content=self.filas_box)

        self.add(scroll)

        self._cargar_datos()

    # -------------------------
    # Cabecera
    # -------------------------
    def _crear_cabecera(self):
        headers = ["Nombre", "TICKER", "Valor", "Δ Ayer", "Δ Semana", "Máx Anual", "Mín Anual"]

        fila = toga.Box(style=Pack(direction=ROW, margin=5))

        for h in headers:
            fila.add(
                toga.Label(
                    h,
                    style=Pack(flex=1, font_weight="bold")
                )
            )
        return fila

    # -------------------------
    # Crear celda delta (color)
    # -------------------------
    def _celda_delta(self, valor):
        try:
            valor_num = float(str(valor).replace("%", "").replace(",", "."))
        except (ValueError, TypeError):
            valor_num = 0.0

        if valor_num > 0:
            color = "#2ecc71"
            texto = f"+{valor_num:.2f}"
        elif valor_num < 0:
            color = "#e74c3c"
            texto = f"{valor_num:.2f}"
        else:
            color = "black"
            texto = f"{valor_num:.2f}"

        return toga.Label(
            texto,
            style=Pack(flex=1, color=color)
        )

    # -------------------------
    # Crear fila
    # -------------------------
    def _crear_fila(self, item):
        fila = toga.Box(style=Pack(direction=ROW, padding=5))

        fila.add(toga.Label(item["nombre"], style=Pack(flex=1)))
        fila.add(toga.Label(item["ticker"], style=Pack(flex=1)))
        fila.add(toga.Label(str(item["valor"]), style=Pack(flex=1)))

        fila.add(self._celda_delta(item["delta_ayer"]))
        fila.add(self._celda_delta(item["delta_semana"]))

        fila.add(toga.Label(item["min_año"], style=Pack(flex=1)))
        fila.add(toga.Label(item["max_año"], style=Pack(flex=1)))

        return fila

    # -------------------------
    # Cargar datos
    # -------------------------
    def _cargar_datos(self):
        for item in self.datos:
            self.filas_box.add(self._crear_fila(item))

    # -------------------------
    # Widget final
    # -------------------------
    def widget(self):
        return self.contenedor