"""
App to manage my Stocks
"""
import datetime
import sqlite3
import logging
import toga
from toga.style import Pack
from toga.style.pack import CENTER, COLUMN, ROW, LEFT, RIGHT, END
from toga.colors import rgb
from plyer import notification
import asyncio
from pathlib import Path

class AppPaths:
    app = None

    @classmethod
    def init(cls, app):
        cls.app = app

    @classmethod
    def base_dir(cls, kind="data"):
        """
        kind: data | cache
        """

        # 🟢 Caso 1: Toga (Briefcase dev / iOS / macOS app)
        if cls.app and hasattr(cls.app, "paths"):
            return getattr(cls.app.paths, kind)

        # 🟡 Caso 2: desarrollo local (Cursor, PyCharm, python directo)
        project_root = Path(__file__).resolve().parent.parent.parent

        if kind == "data":
            base = project_root / "data"
        elif kind == "cache":
            base = project_root / "cache"
        else:
            base = project_root / kind

        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def get(cls, kind="data", filename=None):
        base = cls.base_dir(kind)
        return base / filename if filename else base

class BolsaPy(toga.App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        # ✅ AQUÍ sí existe self
        AppPaths.init(self)
        print("APP ID:", self.app_id)

        self.main_window = toga.MainWindow(title=self.formal_name)

        # Obtener la ruta del directorio actual del script
        self.log_path = AppPaths.get("data", "bolsapy.log")
        print("DATA DIR:", self.paths.data)
        print("Log DIR:", self.log_path)
        
        logging.basicConfig(filename=self.log_path, level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
        logging.info("Inicio BolsaPy iOS App!!!")
        print("Inicio BolsaPy iOS App!!!")

        self.main_window.content = self.construir_pantalla_uno()
        self.main_window.show()

    def semaforo_a_rgb(self, color: str) -> rgb:
        color = (color or "").lower()
        if color == "rojo":
            return rgb(255, 0, 0)
        if color == "amarillo":
            return rgb(255, 190, 0)
        if color == "verde":
            return rgb(0, 200, 0)
        return rgb(128, 128, 128)  # fallback (desconocido)

    # -------- Pantalla 1 --------
    def construir_pantalla_uno(self):
        # =========================
        # Header (Pantalla 1)
        # =========================
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20))
        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        titulo_estado = "Título"  # Cambia esto por tu título
        valor_numerico_estado = 0  # Cambia esto por tu valor numérico
        porcentaje_estado = 0.0  # Cambia esto por tu porcentaje (0-100)
        semaforo_estado = "verde"  # "rojo" | "amarillo" | "verde"
        
        encabezado_box = toga.Box(
            style=Pack(direction=COLUMN, align_items=CENTER, gap=0)
        )
        titulo_label = toga.Label(
            titulo_estado,
            style=Pack(text_align=CENTER, font_size=20, font_weight="bold"),
        )
        encabezado_box.add(titulo_label)
        caja_estado = toga.Box(
            style=Pack(direction=ROW, align_items=CENTER, gap=10)
        )
        valor_label = toga.Label(
            str(valor_numerico_estado),
            style=Pack(text_align=CENTER, font_size=18),
        )
        semaforo_label = toga.Label(
            "●",
            style=Pack(
                color=self.semaforo_a_rgb(semaforo_estado),
                font_size=24,
            ),
        )
        porcentaje_label = toga.Label(
            f"{porcentaje_estado}%",
            style=Pack(text_align=CENTER, font_size=18),
        )
        caja_estado.add(valor_label)
        caja_estado.add(semaforo_label)
        caja_estado.add(porcentaje_label)
        encabezado_box.add(caja_estado)
        contenido_box.add(encabezado_box)
        main_box.add(contenido_box)
        return main_box

    # -------- Pantalla 2 --------
    def construir_pantalla_dos(self, valor):
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        tituloSreen5 = "Añadir Componente: "+str(valor)

        self.label_pantalla_dos = toga.Label(
            tituloSreen5,
            style=Pack(margin_bottom=20, text_align=CENTER)
        )

        contenido_box.add(self.label_pantalla_dos)

        # Caja con label "Fecha" a la izquierda y campo de texto a la derecha
        caja_fecha = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_fecha = toga.Label(
            "Fecha",
            style=Pack(margin_right=10)
        )

        self.entrada_fecha = toga.TextInput(
            placeholder="Fecha instalación",
            style=Pack(width=250),
            value=datetime.today().strftime("%Y-%m-%d")
        )

        caja_fecha.add(label_fecha)
        caja_fecha.add(self.entrada_fecha)

        # Caja con dropdown "Elemento"
        tipos_elemento = []
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute("SELECT nombre FROM Elemento ORDER BY nombre")
            tipos_elemento = [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as error:
            logging.error("Error al leer tabla Elemento %s", error)

        # Si no hay datos en la tabla Elemento, usamos una lista por defecto
        if not tipos_elemento:
            tipos_elemento = ["Cadena", "Pastillas Freno", "Cubiertas"]

        caja_elemento = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_elemento = toga.Label(
            "Elemento",
            style=Pack(margin_right=10)
        )

        self.selection_elemento = toga.Selection(
            items=tipos_elemento,
            style=Pack(width=250)
        )

        # Caja con label "Descripción" a la izquierda y campo de texto a la derecha
        caja_descripcion = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_descripcion = toga.Label(
            "Descripción: ",
            style=Pack(margin_right=10)
        )

        self.descripcion_texto = toga.TextInput(
            placeholder="Escribe algo...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_marca = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_marca = toga.Label(
            "Marca Comp: ",
            style=Pack(margin_right=10)
        )

        self.marca_texto = toga.TextInput(
            placeholder="Escribe algo...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_tiempolim = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_tiempolim = toga.Label(
            "Tiempo Límite: ",
            style=Pack(margin_right=10)
        )

        self.tiempolim_texto = toga.TextInput(
            placeholder="Escribe algo...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_distancialim = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_distancialim = toga.Label(
            "Distancia Límite: ",
            style=Pack(margin_right=10)
        )

        self.distancialim_texto = toga.TextInput(
            placeholder="Escribe algo...",
            style=Pack(width=250)
        )

        boton_Cargar = toga.Button(
            "Cargar",
            on_press=lambda widget:self.cargar_componente(self.entrada_fecha, self.usuarioSeleccionado, self.selection_elemento, self.descripcion_texto, self.marca_texto, self.distancialim_texto, self.tiempolim_texto),
            style=Pack(margin=10)
        )

        caja_elemento.add(label_elemento)
        caja_elemento.add(self.selection_elemento)
        caja_descripcion.add(label_descripcion)
        caja_descripcion.add(self.descripcion_texto)
        caja_marca.add(label_marca)
        caja_marca.add(self.marca_texto)
        caja_distancialim.add(label_distancialim)
        caja_distancialim.add(self.distancialim_texto)
        caja_tiempolim.add(label_tiempolim)
        caja_tiempolim.add(self.tiempolim_texto)
        

        contenido_box.add(caja_fecha)
        contenido_box.add(caja_elemento)
        contenido_box.add(caja_descripcion)
        contenido_box.add(caja_marca)
        contenido_box.add(caja_distancialim)
        contenido_box.add(caja_tiempolim)
        
        contenido_box.add(boton_Cargar)

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior con botón a la izquierda (por defecto)
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )

        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.volver_pantalla_inicial,
            style=Pack(margin=10)
        )
        barra_inferior.add(boton_volver)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    def ir_a_pantalla_dos(self, widget, valor):
        self.main_window.content = self.construir_pantalla_dos(valor)

    def iniciar_tarea(self, widget):
        self.add_background_task(self.tarea_larga)
        notification.notify(title="Inicio", message="Fin Tareas", app_name="BikeCompFollowApp", app_icon="resources/bici2.icns")

    async def tarea_larga(self, widget):
        for i in range(1, self.total + 1):
            await asyncio.sleep(0.3)   
            # Actualizar barra
            self.progress.value = i
            # actualizar texto
            self.label.text = f"Procesando {i} de {self.total}"

    def ir_a_pantalla_recoleccionDatos(self, widget):
        self.main_window.content = self.barraProgresoCargaDatos()    

    def barraProgresoCargaDatos(self):    

        self.total = 20

        # Texto de progreso
        self.label = toga.Label(
            "Pulsa Inicio para cargar los datos.",
            style=Pack(padding=10)
        )

        # Barra de progreso
        self.progress = toga.ProgressBar(max=self.total,
            value=0, style=Pack(padding=10))

        # Botón para iniciar tarea
        box = toga.Box(style=Pack(direction=COLUMN, padding=20))

        # Añadimos los widgets al mismo box
        box.add(self.label)
        box.add(self.progress)

        boton_iniciar = toga.Button("Iniciar", on_press=self.iniciar_tarea, style=Pack(padding=10))
        box.add(boton_iniciar)

        boton_datos = toga.Button("Extraer Datos Strava", on_press=self.recolectarDatosStrava, style=Pack(padding=10))
        box.add(boton_datos)

        # Barra inferior con botón a la izquierda (por defecto)
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )
        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.volver_pantalla_inicial,
            style=Pack(margin=10)
        )

        barra_inferior.add(boton_volver)
        box.add(barra_inferior)

        # self.main_window = toga.MainWindow(title="Ejemplo ProgressBar")
        # self.main_window.content = box
        # self.main_window.show()
        return box

def main():
    return BolsaPy("BolsaPy App", "com.SkullWithGasMask", icon="resources/icon.png")

if __name__ == "__main__":
    app = main()
    app.main_loop()