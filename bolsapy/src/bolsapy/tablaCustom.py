import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

class TablaCustom(toga.Box):   # 👈 MUY IMPORTANTE
    sort_col = None
    sort_reverse = False
    header_box = None
    selected_item = None

    cols = {
        "nombre": 2,
        "ticker": 1,
        "valor": 1,
        "delta_ayer": 1,
        "delta_semana": 1,
        "min_año": 1,
        "max_año": 1,
    }

    def __init__(self, datos, on_row_click=None):
        super().__init__(style=Pack(direction=COLUMN, flex=1))

        self.selected_item = None
        self.datos = datos
        self.on_row_click = on_row_click  # 👈 ahora sí existe
        self.header_buttons = {}

        self.header_box = self._crear_cabecera()
        self.add(self.header_box)

        # Scroll
        self.filas_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        scroll = toga.ScrollContainer(
            content=self.filas_box,
            style=Pack(flex=1)
        )

        self.add(scroll)

        self._cargar_datos()

    # -------------------------
    # Cabecera
    # -------------------------
    def _crear_cabecera(self):
        headers = [
            ("Nombre", "nombre"),
            ("TICKER", "ticker"),
            ("Valor", "valor"),
            ("Δ Ayer", "delta_ayer"),
            ("Δ Semana", "delta_semana"),
            ("Mín Anual", "min_año"),
            ("Máx Anual", "max_año"),
        ]

        fila = toga.Box(style=Pack(direction=ROW, align_items="center"))
        self.header_buttons = {}
            
        for titulo, clave in headers:
            # Indicador visual en la columna ordenada
            if self.sort_col == clave:
                icono = " ▲" if not self.sort_reverse else " ▼"
            else:
                icono = ""

            btn = toga.Button(
                titulo + icono,
                on_press=lambda widget, c=clave: self._ordenar_por(c),
                style=Pack(flex=self.cols[clave])
            )
            self.header_buttons[clave] = btn
            fila.add(btn)

        return fila
    
    def _refrescar_cabecera(self):
        # En algunos backends de Toga, actualizar solo el texto del botón
        # puede dejar artefactos visuales; recrear la cabecera evita solapes.
        if self.header_box in self.children:
            self.remove(self.header_box)
        self.header_box = self._crear_cabecera()
        self.insert(0, self.header_box)

    # -------------------------
    # Método Ordenación
    # -------------------------
    def _ordenar_por(self, columna):
        if self.sort_col == columna:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = columna
            self.sort_reverse = False

        def convertir(v):
            try:
                return float(str(v).replace("%", "").replace(",", "."))
            except:
                return str(v).lower()

        self.datos.sort(
            key=lambda x: convertir(x[columna]),
            reverse=self.sort_reverse
        )

        self._refrescar_cabecera()
        self._refrescar_tabla()

    def _refrescar_tabla(self):
        # Importante: en Toga, limpiar con children.clear() puede dejar
        # widgets renderizados en algunos backends. Quitamos uno a uno.
        for child in list(self.filas_box.children):
            self.filas_box.remove(child)

        # volver a pintar
        for item in self.datos:
            self.filas_box.add(self._crear_fila(item))

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

    def _texto_dos_lineas(self, texto, max_linea=22):
        """Parte el texto en 2 líneas como máximo con elipsis."""
        s = str(texto or "").strip()
        if len(s) <= max_linea:
            return s

        corte1 = s.rfind(" ", 0, max_linea + 1)
        if corte1 == -1:
            corte1 = max_linea
        linea1 = s[:corte1].strip()
        resto = s[corte1:].strip()

        if len(resto) <= max_linea:
            linea2 = resto
        else:
            corte2 = resto.rfind(" ", 0, max_linea + 1)
            if corte2 == -1:
                corte2 = max_linea
            linea2 = resto[:corte2].strip() + "..."

        if not linea1:
            linea1 = s[:max_linea]
        if not linea2:
            linea2 = "..."
        return f"{linea1}\n{linea2}"

    # -------------------------
    # Crear fila
    # -------------------------
    def _celda_nombre_clickable(self, item):

        def click(widget):
            self.selected_item = item
            self._refrescar_tabla()

            if self.on_row_click:
                self.on_row_click(item)

        btn = toga.Button(
            item["nombre"],
            on_press=click,
            style=Pack(flex=self.cols["nombre"])
        )

        # estilo tipo label
        btn.style.update(background_color="transparent")

        return btn

    def _crear_fila(self, item):

        is_selected = item == self.selected_item
        fila = toga.Box(style=Pack(direction=ROW, margin=5))

        if is_selected:
            fila.style.update(background_color="#dff0d8")

        # 👇 SOLO el nombre es clickable
        fila.add(self._celda_nombre_clickable(item))

        # resto solo labels
        fila.add(toga.Label(item["ticker"], style=Pack(flex=self.cols["ticker"])))
        fila.add(toga.Label(str(item["valor"]), style=Pack(flex=self.cols["valor"])))

        fila.add(self._celda_delta(item["delta_ayer"]))
        fila.add(self._celda_delta(item["delta_semana"]))

        fila.add(toga.Label(item["min_año"], style=Pack(flex=self.cols["min_año"])))
        fila.add(toga.Label(item["max_año"], style=Pack(flex=self.cols["max_año"])))

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