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

import actualiza_bolsa

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
    def get(cls, kind="data", cadena="", filename=None):
        base = cls.base_dir(kind)
        return base / cadena / filename if filename else base

class BolsaPy(toga.App):
    cursor = None
    sqliteConnection = None

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
        self.log_path = AppPaths.get("data","BolsaPy", "bolsapy.log")
        print("DATA DIR:", self.paths.data)
        print("Log DIR:", self.log_path)
        
        logging.basicConfig(filename=self.log_path, level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
        logging.info("Inicio BolsaPy iOS App!!!")
        print("Inicio BolsaPy iOS App!!!")

        self.arrancarDB() # Arrancar BDD

        self.main_window.content = self.construir_pantalla_uno()
        self.main_window.show()

    def chequearIntegrarDB(self):
        self.cursor.execute("PRAGMA integrity_check;")
        result = self.cursor.fetchone()

        if result[0] == "ok":
            print("✅ DB íntegra")
        else:
            print("❌ DB corrupta")

    def semaforo_a_rgb(self, color: str) -> rgb:
        color = (color or "").lower()
        if color == "rojo":
            return rgb(255, 0, 0)
        if color == "amarillo":
            return rgb(255, 190, 0)
        if color == "verde":
            return rgb(0, 200, 0)
        return rgb(128, 128, 128)  # fallback (desconocido)
    
    def arrancarDB(self):
        # Obtener la ruta del directorio actual del script
        
        self.db_path = AppPaths.get("data", "BolsaPy", "dbBolsaPy.db")

        # Esto crea el fichero si no existe
        self.sqliteConnection = sqlite3.connect(self.db_path)
        self.cursor = self.sqliteConnection.cursor()

        print("DB DIR:", self.db_path)
        
        self.sqliteConnection.commit()
        print("Base de datos lista")

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS acciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            TICKERS TEXT,
            Mercado TEXT, 
            FechaCompra Date,
            Num_acciones INTEGER, 
            Valor_compra NUMERIC,  
            Valor_actual NUMERIC, 
            Delta_ayer NUMERIC,
            Delta_semana NUMERIC, 
            Delta_3meses NUMERIC
        )""")

        self.sqliteConnection.commit()

        logging.info('Creación Base de Datos y Tablas principales.')

    def cerrarDB(self):
        #Cerramos base de datos
        self.sqliteConnection.close()
        logging.info("The SQLite connection is closed")

    def volver_pantalla_inicial(self, widget):
        self.main_window.content = self.construir_pantalla_uno()

    # -------- Pantalla 1 --------
    def construir_pantalla_uno(self):
        # =========================
        # Header (Pantalla 1)
        # =========================
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20, flex=1))
        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, alignment=LEFT)
        )

        titulo_estado = "Título"  # Cambia esto por tu título
        valor_numerico_estado = 0  # Cambia esto por tu valor numérico
        porcentaje_estado = 0.0  # Cambia esto por tu porcentaje (0-100)
        semaforo_estado = "verde"  # "rojo" | "amarillo" | "verde"
        
        encabezado_box = toga.Box(
            style=Pack(direction=COLUMN, align_items=CENTER)
        )
        titulo_label = toga.Label(
            titulo_estado,
            style=Pack(text_align=CENTER, font_size=20, font_weight="bold"),
        )
        encabezado_box.add(titulo_label)
        caja_estado = toga.Box(
            style=Pack(direction=ROW, align_items=CENTER)
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

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior: botón izquierda, hueco en medio, botón derecha
        barra_inferior = toga.Box(
            style=Pack(direction=ROW, alignment=CENTER, padding=5)
        )

        boton_descargar = toga.Button(
            "Sync Stocks",
            on_press=self.ir_a_pantalla_recoleccionDatos,
            style=Pack(margin=10, 
            background_color="orange")
        )

        pilaBoton = toga.Box(
            style=Pack(direction=COLUMN)
        )

        boton_acciones = toga.Button(
            "Acciones Pos.",
            on_press=self.ir_a_pantalla_dos,
            style=Pack(margin=10,
            background_color="blue")
        )

        boton_masinfo = toga.Button(
            "+ info",
            on_press=self.ir_a_pantalla_tres,
            style=Pack(margin=10)
        )

        espaciador_horizontal = toga.Box(style=Pack(flex=1))
        pilaBoton.add(boton_acciones)
        pilaBoton.add(boton_masinfo)

        caja_estado.add(valor_label)
        caja_estado.add(semaforo_label)
        caja_estado.add(porcentaje_label)
        encabezado_box.add(caja_estado)
        contenido_box.add(encabezado_box)
        
        barra_inferior.add(boton_descargar)
        barra_inferior.add(espaciador_horizontal)
        barra_inferior.add(pilaBoton)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    # -------- Pantalla 2 --------
    def construir_pantalla_dos(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        tituloSreen5 = "Añadir Componente: X"

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
            value=datetime.date.today().strftime("%Y-%m-%d")
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

    def ir_a_pantalla_dos(self, widget):
        self.main_window.content = self.construir_pantalla_dos()

    # -------- Pantalla info (3) --------
    def construir_pantalla_uno(self):
        # =========================
        # Header (Pantalla info)
        # =========================
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20, flex=1))
        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        titulo_estado = "Valor Liquidativo Total"  # Cambia esto por tu título
        valor_numerico_estado = 0  # Cambia esto por tu valor numérico
        porcentaje_estado = 0.0  # Cambia esto por tu porcentaje (0-100)
        semaforo_estado = "verde"  # "rojo" | "amarillo" | "verde"
        
        encabezado_box = toga.Box(
            style=Pack(direction=COLUMN, align_items=CENTER)
        )
        titulo_label = toga.Label(
            titulo_estado,
            style=Pack(text_align=CENTER, font_size=20, font_weight="bold"),
        )
        encabezado_box.add(titulo_label)
        caja_estado = toga.Box(
            style=Pack(direction=ROW, align_items=CENTER)
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

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior: botón izquierda, hueco en medio, botón derecha
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )
        pilaBoton1 = toga.Box(
            style=Pack(direction=COLUMN)
        )

        pilaBoton = toga.Box(
            style=Pack(direction=COLUMN)
        )

        boton_descarga = toga.Button(
            "Stocks Sync",
            on_press=self.ir_a_pantalla_recoleccionDatos,
            style=Pack(margin=10,
            background_color="orange")
        )

        boton_acciones = toga.Button(
            "Acciones Pos.",
            on_press=self.ir_a_pantalla_dos,
            style=Pack(margin=10,
            background_color="blue")
        )

        boton_masinfo = toga.Button(
            "+ info",
            on_press=self.ir_a_pantalla_info,
            style=Pack(margin=10)
        )

        espaciador_horizontal = toga.Box(style=Pack(flex=1))
        pilaBoton.add(boton_acciones)
        pilaBoton.add(boton_masinfo)
        pilaBoton1.add(boton_descarga)

        caja_estado.add(valor_label)
        caja_estado.add(semaforo_label)
        caja_estado.add(porcentaje_label)
        encabezado_box.add(caja_estado)
        contenido_box.add(encabezado_box)
        
        barra_inferior.add(pilaBoton1)
        barra_inferior.add(espaciador_horizontal)
        barra_inferior.add(pilaBoton)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    def ir_a_pantalla_info(self, widget):
        self.main_window.content = self.construir_pantalla_detalles()    

    # -------- Pantalla 3 --------
    def construir_pantalla_detalles(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, padding_left=40, align_items='start', flex=1)
        )

        titulo = "User: "
        # self.usuarioSeleccionado = valor

        self.label_pantalla_dos = toga.Label(
            titulo,
            style=Pack(margin_bottom=20, text_align=CENTER)
        )

        contenido_box.add(self.label_pantalla_dos)

        dataTable = None
        data = None

        # archivoscomponentes (id INTEGER PRIMARY KEY, usuario, elemento TEXT, descripcion TEXT, marca TEXT, fechaInsercion Date, distanciaLímite integer, tiempoLímite integer, activo BOOLEAN)
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute(
                "SELECT elemento, descripcion, fechaInsercion, distanciaLimite, 'x', tiempoLimite, activo "
                "FROM archivoscomponentes WHERE usuario = ?",
                (self.usuarioSeleccionado,),
            )
            dataTable = cursor.fetchall()
        except sqlite3.Error as error:
            logging.error("Error en el SELECT de la TABLA Comp: %s", error)
            print("Error en el SELECT de la TABLA Comp: %s", error)
            data=[("Juan", "Madrid", "08-07-1984", 5000, 1249, 300, "True"),
                ("Ana", "Barcelona","06-08-2020", 2500, 2300, 125, "False"),
                ("Luis", "Zaragoza","28-11-2023", 3300, 256, 120, "True"),
            ]
        finally:
            self.label_pantalla_dos.text = "Datos de la TABLA COMP leídos  correctamente."
            self.label_pantalla_dos.style.color = rgb(0, 255, 0)
            logging.info("Datos de TABLA LEÍDOS correctamente.")
            if dataTable is not None:
                data = dataTable

        data = list(data) if data is not None else []
        # Altura según nº de filas (Toga no la calcula sola). Tope para listas largas → scroll dentro de la tabla.
        _h_cabecera, _h_fila, _h_max = 28, 22, 520
        _n = len(data)
        _altura_tabla = _h_cabecera + max(_n, 1) * _h_fila
        _altura_tabla = min(_altura_tabla, _h_max)

        # Definir tabla con cabeceras
        self.tabla = toga.Table(
            headings=["Componente", "Descripción", "Fecha", "Distancia Max Comp", "Distancia desde Inserción", "Tiempo Montado", "Activo"],
            data=data,
            style=Pack(height=_altura_tabla),
        )

        contenido_box.add(self.tabla)

        # Barra inferior con botón a la izquierda (por defecto)
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )

        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.volver_pantalla_inicial,
            style=Pack(margin=10)
        )

        espaciador_horizontal = toga.Box(style=Pack(flex=1))

        # boton_nuevocomponente = toga.Button(
        #    "+ Componente",
        #    on_press=lambda widget, valor=valor:self.ir_a_pantalla_cinco(widget, valor),
        #    style=Pack(margin=10)
        #)

        barra_inferior.add(boton_volver)
        barra_inferior.add(espaciador_horizontal)
        #barra_inferior.add(boton_nuevocomponente)

        main_box.add(contenido_box)
        main_box.add(barra_inferior)

        return main_box

    def ir_a_pantalla_tres(self, widget, valor):
        self.main_window.content = self.construir_pantalla_detalles(valor)

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

        AB = actualiza_bolsa.ActualizaBolsa()
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

        boton_datos = toga.Button("Extraer Datos Strava", on_press=AB.lanzarAcciones, style=Pack(padding=10))
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