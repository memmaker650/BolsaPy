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
import valoracion_intrinseca

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
    db_path = None

    valorCompraTotal = 0
    valorTotalActual = 0
    total = 0

    label_estado = ""
    ruta_imagen = None
    imagen_grafica = None

    TICKERS_BASE = {
        "Repsol": "REP.MC",
        "Wolters Kluwer": "WKL.AS",
        "Apple": "AAPL",
        "Telefónica": "TEF.MC", 
        "Amadeus": "AMS.MC",
        "Banco Santander": "SAN",
        "Banco Sabadell": "SAB.MC",
        "BBVA": "BBVA",
        "OHLA": "OHLA.MC",
        "Sacyr": "SCYR.MC",
        "AENA": "AENA.MC",
        "Acciona": "ANA.MC",
        "Ferrovial": "FER",
        "Atos": "ATO.PA",
        "Alten": "ATE.PA",
        "Sopra Steria": "SOP.PA",
        "Indra": "IDR.MC",
        "Grifols": "GRF",
        "Inditex (Zara)": "ITX.MC",
        "Repsol": "REP.MC",
        "YPF": "YPF",
        "Endesa": "ELE.MC",
        "Iberdrola": "IBE.MC",
        "NIKE": "NKE",
        "ADIDAS": "ADS.DE",
        "ASICS": "7936.T",
        "Johnson & Johnson": "JNJ",
        "Procter & Gamble": "PG"
    }

    async def cargar_grafica(self, widget=None):
        self.ruta_imagen = await self.loop.run_in_executor(
            None,
            actualiza_bolsa.generar_grafica_ticker,
            "AAPL",
            self.app.paths.data
        )

        # actualizar UI en hilo principal
        if self.ruta_imagen:
            self.imagen_grafica.image = toga.Image(str(self.ruta_imagen))
            logging.info("Gráfica cargada")
        else:
            logging.error("❌ Error al generar gráfica")
    
    async def cargarGraficaVelas(self, widget=None):
        ruta = await self.loop.run_in_executor(
            None,
            actualiza_bolsa.generar_velas_ticker,
            "AAPL",
            self.app.paths.data
        )

        if ruta:
            self.imagenGraficaVelas.image = toga.Image(str(ruta))
            logging.info("Velas cargadas")
        else:
            logging.error("❌ Error al generar gráfica de velas")

    def ordenar_tabla(self, col_index):
        # En Toga, self.tabla.data devuelve objetos Row (no indexables con [i]).
        # Conservamos una copia en formato tupla para poder ordenar por índice.
        data = list(getattr(self, "_tabla_ordenable_data", []))
        if not data:
            # Si no tenemos base ordenable, no tocamos la tabla para evitar "vaciarla".
            logging.warning("No hay datos base para ordenar la tabla.")
            return
    
        # alternar asc/desc
        if not hasattr(self, "orden_estado"):
            self.orden_estado = {}
    
        reverse = self.orden_estado.get(col_index, False)
    
        # columnas numéricas
        columnas_numericas = [0, 3, 4, 5, 6, 7]
    
        def convertir(valor):
            if valor is None:
                return 0
    
            if col_index in columnas_numericas:
                try:
                    # Limpia símbolos monetarios/% y soporta formatos 1.234,56 y 1,234.56
                    texto = str(valor).strip().replace("%", "")
                    texto = texto.replace("€", "").replace("$", "").replace(" ", "")
                    if "." in texto and "," in texto:
                        if texto.rfind(",") > texto.rfind("."):
                            # formato europeo: 1.234,56
                            texto = texto.replace(".", "").replace(",", ".")
                        else:
                            # formato anglosajón: 1,234.56
                            texto = texto.replace(",", "")
                    elif "," in texto:
                        texto = texto.replace(",", ".")
                    return float(texto)
                except Exception:
                    return 0
            else:
                return str(valor).lower()
    
        data.sort(key=lambda x: convertir(x[col_index]), reverse=reverse)
    
        # guardar estado (toggle)
        self.orden_estado[col_index] = not reverse
    
        # refrescar tabla
        self._tabla_ordenable_data = data
        self.tabla.data = data
        self._actualizar_indicadores_orden(col_index, reverse)

    def _actualizar_indicadores_orden(self, col_index, reverse):
        botones = getattr(self, "_botones_orden", {})
        titulos = getattr(self, "_titulos_columnas_orden", {})
        if not botones or not titulos:
            return

        for idx, boton in botones.items():
            base = titulos.get(idx, boton.text)
            if idx == col_index:
                boton.text = f"{base} {'↓' if reverse else '↑'}"
            else:
                boton.text = base

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

        self.crearTablaTickers()
        self.guardarTickersBDD(self.TICKERS_BASE)

        tickers = self.leerTickersBDD()
        print(tickers)

        self.main_window.content = self.construir_pantalla_inicial()
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
            TICKER TEXT,
            Mercado TEXT, 
            FechaCompra Date,
            Num_acciones INTEGER, 
            Valor_compra NUMERIC,  
            tiempo_custodia INTEGER
        )""")

        self.sqliteConnection.commit()

        logging.info('Creación Base de Datos y Tablas principales.')

    def cerrarDB(self):
        #Cerramos base de datos
        self.sqliteConnection.close()
        logging.info("The SQLite connection is closed")

    def volver_pantalla_inicial(self, widget):
        self.main_window.content = self.construir_pantalla_inicial()

    

    # -------- Pantalla 1 --------
    def construir_pantalla_inicial(self):
        # =========================
        # Header (Pantalla 1)
        # =========================
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20, flex=1))
        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, alignment=LEFT)
        )

        filas = []
        try:
            self.cursor.execute("""SELECT nombre, TICKER, Num_acciones, Valor_compra from acciones""")
            filas = self.cursor.fetchall()   # lista de tuplas (nombre, tipov)
        except sqlite3.Error as error:
            logging.error(" Error al seleccionar Acciones del Usuario, tabla acciones en SQLite %s", error)

        # Texto inicial encima del botón
        self.label = toga.Label(
            "Acciones de tu Cartera Personal: ",
            style=Pack(margin_bottom=20, text_align=CENTER)
        )

        titulo_estado = "Título"  # Cambia esto por tu título
        valor_numerico_estado = len(filas)
        porcentaje_estado = 0.0  # Cambia esto por tu porcentaje (0-100)
        semaforo_estado = "amarillo"  # "rojo" | "amarillo" | "verde"

        # Recalcular total cada vez que se construye la pantalla.
        self.valorCompraTotal = 0.0
        for _, _, numAcciones, valorCompra in filas:
            try:
                num_acciones_val = float(str(numAcciones).replace(",", "."))
                valor_compra_val = float(str(valorCompra).replace(",", "."))
                self.valorCompraTotal += num_acciones_val * valor_compra_val
            except (TypeError, ValueError):
                logging.warning(
                    "Valor no numerico en acciones (Num_acciones=%s, Valor_compra=%s). Se omite del total.",
                    numAcciones,
                    valorCompra,
                )
        
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
            str(self.valorCompraTotal),
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

        encabezado_box.add(caja_estado)
        contenido_box.add(encabezado_box)

        contenido_box.add(self.label)

        print("Numero de Acciones Personales:", valor_numerico_estado)

        if filas:
            for nombre, ticker, numAcciones, valorCompra in filas:
                print("Nombre:", nombre, "TICKER:", ticker) 

                cadena = nombre + "-" + ticker # Concatener 2 string añadiendo un salto de línea. " \n "

                # Botón que cambia el texto (ahora circular con símbolo '+')
                boton = toga.Button(cadena, on_press=lambda widget, valor=cadena: self.ir_a_pantalla_tres(widget, valor),
                style=Pack(width=140, height=60, margin=0))
                fila_boton = toga.Box(style=Pack(direction=ROW))
                fila_boton.add(toga.Box(style=Pack(flex=1)))
                fila_boton.add(boton)
                fila_boton.add(toga.Box(style=Pack(flex=1)))

                contenido_box.add(fila_boton)

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior: botón izquierda, hueco en medio, botón derecha
        barra_inferior = toga.Box(
            style=Pack(direction=ROW, alignment=CENTER, margin=5)
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
            on_press=self.ir_a_pantalla_infoBolsaAccionesPersonales,
            style=Pack(margin=10,
            background_color="blue")
        )

        boton_masinfo = toga.Button(
            "+ info",
            on_press=self.ir_a_pantalla_infoTotalTickers,
            style=Pack(margin=10)
        )

        espaciador_horizontal = toga.Box(style=Pack(flex=1))
        pilaBoton.add(boton_acciones)
        pilaBoton.add(boton_masinfo)

        caja_estado.add(valor_label)
        caja_estado.add(semaforo_label)
        caja_estado.add(porcentaje_label)
        
        barra_inferior.add(boton_descargar)
        barra_inferior.add(espaciador_horizontal)
        barra_inferior.add(pilaBoton)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    # -------- Pantalla 2 --------
    def construir_pantalla_formAccionesUser(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )
        self.label_estado = ""
        tituloSreen5 = "Añadir Acción a la Bolsa Personal: "+self.label_estado

        self.label_pantalla_dos = toga.Label(
            tituloSreen5,
            style=Pack(margin_bottom=20, text_align=CENTER)
        )

        contenido_box.add(self.label_pantalla_dos)

        # Caja con label "Fecha" a la izquierda y campo de texto a la derecha
        caja_fecha = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_fecha = toga.Label(
            "Fecha Compra Acción",
            style=Pack(margin_right=10)
        )

        self.entrada_fecha = toga.TextInput(
            placeholder="Fecha compra",
            style=Pack(width=250),
            value=datetime.date.today().strftime("%Y-%m-%d")
        )

        caja_fecha.add(label_fecha)
        caja_fecha.add(self.entrada_fecha)

        # Caja con dropdown "Elemento"
        mercado = []
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute("SELECT nombre FROM Mercados ORDER BY nombre")
            mercado = [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as error:
            logging.error("Error al leer tabla Mercados %s", error)

        # Si no hay datos en la tabla Elemento, usamos una lista por defecto
        if not mercado:
            mercado = ["USA", "España", "Alemania", "Francia", "Japón", "UK"]

        caja_mercado = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_mercado = toga.Label(
            "Mercado : ",
            style=Pack(margin_right=10)
        )

        self.seleccion_mercado = toga.Selection(
            items=mercado,
            style=Pack(width=250)
        )

        # Caja con label "Descripción" a la izquierda y campo de texto a la derecha
        caja_nombre = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_nombre = toga.Label(
            "Nombre Compañía : ",
            style=Pack(margin_right=10)
        )

        self.nombre_texto = toga.TextInput(
            placeholder="Escribe nombre comp...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_ticker = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_ticker = toga.Label(
            "TICKER: ",
            style=Pack(margin_right=10)
        )

        self.ticker_texto = toga.TextInput(
            placeholder="TICKER si lo conoces...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_precioCompra = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_precioCompra = toga.Label(
            "precio Compra: ",
            style=Pack(margin_right=10)
        )

        self.precioCompra_texto = toga.TextInput(
            placeholder="Precio compra...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_numAcciones = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_numAcciones = toga.Label(
            "Número de Acciones:  ",
            style=Pack(margin_right=10)
        )

        self.numAcciones_texto = toga.TextInput(
            placeholder="Escribe Num Acciones...",
            style=Pack(width=250)
        )

        boton_Cargar = toga.Button(
            "Cargar",
            on_press=lambda widget:self.cargar_componente(self.entrada_fecha, self.seleccion_mercado, self.nombre_texto, self.ticker_texto, self.precioCompra_texto, self.numAcciones_texto),
            style=Pack(margin=10)
        )

        caja_mercado.add(label_mercado)
        caja_mercado.add(self.seleccion_mercado)
        caja_nombre.add(label_nombre)
        caja_nombre.add(self.nombre_texto)
        caja_ticker.add(label_ticker)
        caja_ticker.add(self.ticker_texto)
        caja_precioCompra.add(label_precioCompra)
        caja_precioCompra.add(self.precioCompra_texto)
        caja_numAcciones.add(label_numAcciones)
        caja_numAcciones.add(self.numAcciones_texto)
        
        contenido_box.add(caja_fecha)
        contenido_box.add(caja_mercado)
        contenido_box.add(caja_nombre)
        contenido_box.add(caja_ticker)
        contenido_box.add(caja_precioCompra)
        contenido_box.add(caja_numAcciones)
        
        contenido_box.add(boton_Cargar)

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior con botón a la izquierda (por defecto)
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )

        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.ir_a_pantalla_infoBolsaAccionesPersonales,
            style=Pack(margin=10)
        )
        barra_inferior.add(boton_volver)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    # CCREATE TABLE acciones ( id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, TICKER TEXT, Mercado TEXT, FechaCompra Date, Num_acciones INTEGER, Valor_compra NUMERIC, tiempo_custodia INTEGER )
    def anadirComponente(self, valor1, valor2, valor3, valor4, valor5, valor6=None):
        logging.info("Dentro añadir Componente.")

        tiempolim = 500
        distlim = 5000

        #if not (mi_textinput.value or "").strip():
        if not (valor5.value or "").strip():
            valor5 = distlim
        else:
            valor5 = valor5.value
        if not (valor6.value or "").strip():
            valor6 = tiempolim
        else:
            valor6 = valor6.value
        
        f = f = (valor1.value or "").strip() or datetime.today().strftime("%Y-%m-%d")
        print("Fecha de Compra : ", f)
        print("Mercado : ", valor2.value)
        print("Nombre : ", valor3.value)
        print("Ticker : ", valor4.value)
        print("Número Acciones : ", valor5)
        print("Precio Compra : ", valor6)

        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute(
                "INSERT INTO acciones (FechaCompra, Mercado, nombre, TICKER, Num_acciones, Valor_compra) VALUES (?, ?, ?, ?, ?, ?)",
                (f, valor2.value, valor3.value, valor4.value, valor5, valor6)
            )
            self.sqliteConnection.commit()
            self.label_pantalla_formAccionesUser.text = "Acciones cargada correctamente."
            self.label_pantalla_formAccionesUser.style.color = rgb(0, 255, 0)
            logging.info("Datos de Acciones cargados correctamente.")
        except sqlite3.Error as error:
            print("Error al insertar en Acciones: %s", error)
            logging.error("Error al insertar en Acciones: %s", error)
        finally:
            print("Terminado el proceso BDD en Acciones.")

    def cargar_componente(self, entrada_fecha, mercado, nombre, ticker, valor_compra, numAcciones) -> bool: 
        logging.info("Dentro de método Cargar Componente.")
        print("Dentro de método Cargar Componente.")
        self.anadirComponente(entrada_fecha, mercado, nombre, ticker, numAcciones, valor_compra)

        return True

    def ir_a_pantalla_formAccionesUser(self, widget):
        self.main_window.content = self.construir_pantalla_formAccionesUser()

    # -------- Pantalla info --------
    def construir_pantalla_info(self):
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
            style=Pack(height=80, margin=10,
            background_color="orange")
        )

        boton_acciones = toga.Button(
            "Acciones Pos.",
            on_press=self.ir_a_pantalla_formAccionesUser,
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
        self.main_window.content = self.construir_pantalla_info()    

    # -------- Pantalla info --------
    def construir_pantalla_infoTotalTickers(self):
        # =========================
        # Header (Pantalla info)
        # =========================
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20, flex=1))
        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        labelPantalla = toga.Label(
            "Info General Lista Tickers.",
            style=Pack(margin_bottom=20, text_align=CENTER)
        )
        label_pantalla_infoTickers = toga.Label(
            "Datos de la TABLA Valores leídos correctamente.",
            style=Pack(margin_bottom=20, text_align=CENTER)
        )
        dataTable = None
        data = None

        # acciones (id INTEGER PRIMARY KEY, usuario, elemento TEXT, descripcion TEXT, marca TEXT, fechaInsercion Date, distanciaLímite integer, tiempoLímite integer, activo BOOLEAN)
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute("""SELECT id, nombre, tickers, Valor_actual, Delta_ayer, Delta_semana, Maximo_Agno, Minimo_Agno FROM valores""")
            dataTable = cursor.fetchall()
        except sqlite3.Error as error:
            logging.error("Error en el SELECT de la TABLA Valores: %s", error)
            print("Error en el SELECT de la TABLA Acciones: %s", error)
        finally:
            label_pantalla_infoTickers.style.color = rgb(0, 255, 0)
            logging.info("Datos de TABLA Valores LEÍDOS correctamente.")
            if dataTable is not None:
                data = dataTable

        data = list(data) if data is not None else []
        self._tabla_ordenable_data = list(data)
        # Altura según nº de filas (Toga no la calcula sola). Tope para listas largas → scroll dentro de la tabla.
        _h_cabecera, _h_fila, _h_max = 28, 22, 520
        _n = len(data)
        _altura_tabla = _h_cabecera + max(_n, 1) * _h_fila
        _altura_tabla = min(_altura_tabla, _h_max)

        # Definir tabla con cabeceras
        self.tabla = toga.Table(
            headings=["id", "Nombre", "TICKER", "Valor actual", "Delta ayer", "Delta semana", "Máximo Anual", "Mínimo Anual"],
            data=data,
            style=Pack(height=_altura_tabla),
        )

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior: botón izquierda, hueco en medio, botón derecha
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )

        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.volver_pantalla_inicial,
            style=Pack(margin=10)
        )

        boton_anadirTicker = toga.Button(
            "+ Ticker",
            on_press=self.ir_a_pantalla_NuevoTicker,
            style=Pack(margin=10)
        )

        espaciador_horizontal = toga.Box(style=Pack(flex=1))
        contenido_box.add(labelPantalla)
        contenido_box.add(label_pantalla_infoTickers)
        contenido_box.add(self.tabla)
        
        barra_inferior.add(boton_volver)
        barra_inferior.add(espaciador_horizontal)
        barra_inferior.add(boton_anadirTicker)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    def ir_a_pantalla_infoTotalTickers(self, widget):
        self.main_window.content = self.construir_pantalla_infoTotalTickers()

    # -------- Pantalla 3 --------
    def construir_pantalla_detalles(self):
        scroll = toga.ScrollContainer(style=Pack(flex=1))
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20, flex=1))

        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start', padding_bottom=20)
        )

        titulo = "Acciones Usuario: "
        # self.usuarioSeleccionado = valor

        self.label_pantalla_detalles = toga.Label(
            titulo,
            style=Pack(margin_bottom=20, text_align=CENTER)
        )

        contenido_box.add(self.label_pantalla_detalles)

        dataTable = None
        data = None

        # acciones (id INTEGER PRIMARY KEY, usuario, elemento TEXT, descripcion TEXT, marca TEXT, fechaInsercion Date, distanciaLímite integer, tiempoLímite integer, activo BOOLEAN)
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute("""SELECT id, nombre, ticker, Num_acciones, Valor_compra, Tiempo_custodia,' ' FROM acciones""")
            dataTable = cursor.fetchall()
            self.label_estado = "✅"
            logging.info("Datos de TABLA LEÍDOS correctamente.")
        except sqlite3.Error as error:
            self.label_estado = "❌"
            logging.error("Error en el SELECT de la TABLA Comp: %s", error)
            print("Error en el SELECT de la TABLA Acciones: %s", error)
        finally:
            
            if dataTable is not None:
                data = dataTable

        data = list(data) if data is not None else []
        # Base ordenable para los botones de ordenación de esta tabla.
        self._tabla_ordenable_data = list(data)
        # Altura según nº de filas (Toga no la calcula sola). Tope para listas largas → scroll dentro de la tabla.
        _h_cabecera, _h_fila, _h_max = 28, 22, 520
        _n = len(data)
        _altura_tabla = _h_cabecera + max(_n, 1) * _h_fila
        _altura_tabla = min(_altura_tabla, _h_max)

        # Definir tabla con cabeceras
        self.tabla = toga.Table(
            headings=["id", "Nombre", "TICKER", "Num Acciones", "Valor compra", "Tiempo Custodia", "Valor actual"],
            data=data,
            style=Pack(height=_altura_tabla),
        )

        contenido_box.add(self.tabla)

        # En un ScrollContainer es mejor usar alto fijo que flex para forzar desbordamiento.
        self.imagen_grafica = toga.ImageView(style=Pack(height=260, margin=10))
        contenido_box.add(self.imagen_grafica)

        # 👇 lanzar tarea Generación Imagen Acción 3 meses en BACKGROUND
        self.app.add_background_task(self.cargar_grafica)

        # Cargar Gráfica de Velas
        self.imagenGraficaVelas = toga.ImageView(style=Pack(height=320, margin=10))
        contenido_box.add(self.imagenGraficaVelas)

        # 👇 lanzar tarea Generación Imagen Acción 3 meses en BACKGROUND
        self.app.add_background_task(self.cargarGraficaVelas)

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

        scroll.content = contenido_box

        barra_inferior.add(boton_volver)
        barra_inferior.add(espaciador_horizontal)
        #barra_inferior.add(boton_nuevocomponente)

        main_box.add(scroll)
        main_box.add(barra_inferior)

        return main_box

    def ir_a_pantalla_tres(self, widget, valor=None):
        self.main_window.content = self.construir_pantalla_detalles()

    async def iniciar_tarea(self, widget):
        AB = actualiza_bolsa.ActualizaBolsa(
            progress_callback=self.actualizar_progreso
        )
        AB.db_path = self.db_path
        AB.TICKERS = self.TICKERS_BASE

        await self.loop.run_in_executor(None, AB.lanzarAcciones)
    
    # Esta es una clase de prueba para testear la barra de progreso.
    async def tarea_larga(self, widget):
        for i in range(1, self.total + 1):
            await asyncio.sleep(0.3)   
            # Actualizar barra
            self.progress.value = i
            # actualizar texto
            self.label.text = f"Procesando {i} de {self.total}"

    def ir_a_pantalla_recoleccionDatos(self, widget):
        self.main_window.content = self.barraProgresoCargaDatos()    

    def actualizar_progreso(self, actual):
        def update():
            print("Dentro de progreso de BarraDeProgresso.")
            self.progress.max = self.total
            self.progress.value = actual
            self.label.text = f"Procesando {actual} de {self.total}"

        self.app.loop.call_soon_threadsafe(update)

    def barraProgresoCargaDatos(self):    
        self.total = len(self.TICKERS_BASE)
        print("Total Tickers a tratar es : ", self.total)

        # Texto de progreso
        self.label = toga.Label(
            "Pulsa Inicio para cargar los datos.",
            style=Pack(margin=10)
        )

        # Barra de progreso
        self.progress = toga.ProgressBar(max=self.total,
            value=0, style=Pack(margin=10))

        # Botón para iniciar tarea
        box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        # Añadimos los widgets al mismo box
        box.add(self.label)
        box.add(self.progress)

        #boton_iniciar = toga.Button("Iniciar", on_press=self.iniciar_tarea, style=Pack(margin=10))
        #box.add(boton_iniciar)

        boton_datos = toga.Button("Extraer Datos Bolsa", on_press=self.iniciar_tarea, style=Pack(margin=10))
        box.add(boton_datos)
        boton_valoracion = toga.Button("Calcular valoración Stocks", on_press=self.preparacion_ValuationConfig, style=Pack(margin=10))
        box.add(boton_valoracion)

        # Barra inferior con botón a la izquierda (por defecto)
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )
        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.volver_pantalla_inicial,
            style=Pack(margin=10)
        )

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))
        box.add(espaciador_vertical)

        barra_inferior.add(boton_volver)
        box.add(barra_inferior)

        # self.main_window = toga.MainWindow(title="Ejemplo ProgressBar")
        # self.main_window.content = box
        # self.main_window.show()
        return box

    async def preparacion_ValuationConfig(self, widget=None):
        override_pe = {
                "MSFT": 30.0,
                "AAPL": 28.0
                # "NVDA": 35.0
        }

        tickers = list(self.TICKERS_BASE.values())

        ValC = valoracion_intrinseca.ValuationConfig(0.10,
                                                    0.02,
                                                    5,
                                                    override_pe,
                                                    0.10, 
                                                    progress_callback=self.actualizar_progreso)
        ValC.db_path = self.db_path
        # Ejecutar la valoración en un hilo para no bloquear el loop UI.
        # Así los callbacks de progreso se pintan en cada iteración.
        df = await asyncio.to_thread(ValC.value_tickers, tickers)
        print(df)
    
    # -------- Pantalla Nuevo Ticker --------
    def construir_pantalla_nuevoTicker(self):
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20))

        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        tituloSreen5 = "Añadir Nuevo Ticker a la lista. " + self.label_estado

        self.label_pantalla_dnuevoTicker = toga.Label(
            tituloSreen5,
            style=Pack(margin_bottom=20, text_align=CENTER)
        )

        contenido_box.add(self.label_pantalla_nuevoTicker)

        # Caja con dropdown "Elemento"
        # mercado = []
        # try:
        #     cursor = self.sqliteConnection.cursor()
        #     cursor.execute("SELECT nombre FROM Mercados ORDER BY nombre")
        #     mercado = [row[0] for row in cursor.fetchall()]
        # except sqlite3.Error as error:
        #     logging.error("Error al leer tabla Mercados %s", error)

        # # Si no hay datos en la tabla Elemento, usamos una lista por defecto
        # if not mercado:
        #     mercado = ["USA", "España", "Alemania", "Francia", "Japón", "UK"]

        # caja_mercado = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        # label_mercado = toga.Label(
        #     "Mercado : ",
        #     style=Pack(margin_right=10)
        # )

        # self.seleccion_mercado = toga.Selection(
        #     items=mercado,
        #     style=Pack(width=250)
        # )

        # Caja con label "Descripción" a la izquierda y campo de texto a la derecha
        caja_nombre = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_nombre = toga.Label(
            "Nombre Compañía: ",
            style=Pack(margin_right=10)
        )

        self.nombre_texto = toga.TextInput(
            placeholder="Escribe nombre comp...",
            style=Pack(width=250)
        )

        # Caja con label "Marca" a la izquierda y campo de texto a la derecha
        caja_ticker = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))

        label_ticker = toga.Label(
            "TICKER: ",
            style=Pack(margin_right=10)
        )

        self.ticker_texto = toga.TextInput(
            placeholder="TICKER si lo conoces...",
            style=Pack(width=250)
        )

        boton_Cargar = toga.Button(
            "Cargar",
            on_press=self.on_cargar,
            style=Pack(margin=10)
        )

        #caja_mercado.add(label_mercado)
        #caja_mercado.add(self.seleccion_mercado)
        caja_nombre.add(label_nombre)
        caja_nombre.add(self.nombre_texto)
        caja_ticker.add(label_ticker)
        caja_ticker.add(self.ticker_texto)

        contenido_box.add(caja_nombre)
        contenido_box.add(caja_ticker)
        
        contenido_box.add(boton_Cargar)

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior con botón a la izquierda (por defecto)
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )

        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.ir_a_pantalla_infoTotalTickers,
            style=Pack(margin=10)
        )
        barra_inferior.add(boton_volver)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box
    
    def ir_a_pantalla_NuevoTicker(self, widget):
        self.main_window.content = self.construir_pantalla_nuevoTicker()

    # -------- Pantalla infoBolsaAccionesPersonales --------
    def construir_pantalla_infoBolsaAccionesPersonales(self):
        # =========================
        # Header (Pantalla info)
        # =========================
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=20, flex=1))
        contenido_box = toga.Box(
            style=Pack(direction=COLUMN, margin_left=40, align_items='start')
        )

        labelPantalla = toga.Label(
            "Info General Lista Tickers.",
            style=Pack(margin_bottom=20, text_align=CENTER)
        )
        label_pantalla_infoTickers = toga.Label(
            "Datos de la TABLA Valores leídos correctamente.",
            style=Pack(margin_bottom=20, text_align=CENTER)
        )
        dataTable = None
        data = None

        # acciones (id INTEGER PRIMARY KEY, usuario, elemento TEXT, descripcion TEXT, marca TEXT, fechaInsercion Date, distanciaLímite integer, tiempoLímite integer, activo BOOLEAN)
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute("""SELECT id, nombre, tickers, Valor_actual, Delta_ayer, Delta_semana, Maximo_Agno, Minimo_Agno FROM valores""")
            dataTable = cursor.fetchall()
        except sqlite3.Error as error:
            logging.error("Error en el SELECT de la TABLA Valores: %s", error)
            print("Error en el SELECT de la TABLA Acciones: %s", error)
        finally:
            label_pantalla_infoTickers.style.color = rgb(0, 255, 0)
            logging.info("Datos de TABLA Valores LEÍDOS correctamente.")
            if dataTable is not None:
                data = dataTable

        data = list(data) if data is not None else []
        self._tabla_ordenable_data = list(data)
        self.orden_estado = {}
        # Altura según nº de filas (Toga no la calcula sola). Tope para listas largas → scroll dentro de la tabla.
        _h_cabecera, _h_fila, _h_max = 28, 22, 520
        _n = len(data)
        _altura_tabla = _h_cabecera + max(_n, 1) * _h_fila
        _altura_tabla = min(_altura_tabla, _h_max)

        # Definir tabla con cabeceras
        cabecera_botones = toga.Box(style=Pack(direction=ROW, margin_bottom=5))

        columnas = [
            ("ID", 0),
            ("Nombre", 1),
            ("TICKER", 2),
            ("Valor", 3),
            ("Δ Ayer", 4),
            ("Δ Semana", 5),
            ("Max", 6),
            ("Min", 7),
        ]

        self._botones_orden = {}
        self._titulos_columnas_orden = {idx: texto for texto, idx in columnas}
        for texto, idx in columnas:
            btn = toga.Button(
                texto,
                on_press=lambda w, i=idx: self.ordenar_tabla(i),
                style=Pack(flex=1, padding=2)
            )
            self._botones_orden[idx] = btn
            cabecera_botones.add(btn)

        contenido_box.add(cabecera_botones)
        self.tabla = toga.Table(
            headings=["id", "Nombre", "TICKER", "Valor actual", "Delta ayer", "Delta semana", "Máximo Anual", "Mínimo Anual"],
            data=data,
            style=Pack(height=_altura_tabla),
        )

        # Espaciador vertical para empujar la barra inferior hacia abajo
        espaciador_vertical = toga.Box(style=Pack(flex=1))

        # Barra inferior: botón izquierda, hueco en medio, botón derecha
        barra_inferior = toga.Box(
            style=Pack(direction=ROW)
        )

        boton_volver = toga.Button(
            "◀ Volver",
            on_press=self.volver_pantalla_inicial,
            style=Pack(margin=10)
        )

        boton_anadirTicker = toga.Button(
            "+ Acciones Perso",
            on_press=self.ir_a_pantalla_formAccionesUser,
            style=Pack(margin=10)
        )

        espaciador_horizontal = toga.Box(style=Pack(flex=1))
        contenido_box.add(labelPantalla)
        contenido_box.add(label_pantalla_infoTickers)
        contenido_box.add(self.tabla)
        
        barra_inferior.add(boton_volver)
        barra_inferior.add(espaciador_horizontal)
        barra_inferior.add(boton_anadirTicker)

        main_box.add(contenido_box)
        main_box.add(espaciador_vertical)
        main_box.add(barra_inferior)

        return main_box

    def ir_a_pantalla_infoBolsaAccionesPersonales(self, widget):
        self.main_window.content = self.construir_pantalla_infoBolsaAccionesPersonales()

    def existe_ticker(self, nombre, ticker) -> bool:
        cursor = self.sqliteConnection.cursor()

        cursor.execute("""
            SELECT 1 FROM tickers 
            WHERE nombre = ? AND ticker = ?
        """, (nombre, ticker))

        return cursor.fetchone() is not None

    def nombre_con_otro_ticker(self, nombre, ticker) -> bool:
        cursor = self.sqliteConnection.cursor()

        cursor.execute("""
            SELECT ticker FROM tickers 
            WHERE nombre = ?
        """, (nombre,))

        row = cursor.fetchone()

        return row is not None and row[0] != ticker

    def ticker_con_otro_nombre(self, nombre, ticker) -> bool:
        cursor = self.sqliteConnection.cursor()

        cursor.execute("""
            SELECT nombre FROM tickers 
            WHERE ticker = ?
        """, (ticker,))

        row = cursor.fetchone()

        return row is not None and row[0] != nombre    

    def crearTablaTickers(self) -> bool:
        try:
            cursor = self.sqliteConnection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS tickers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            TICKER TEXT UNIQUE
            )""")
            self.sqliteConnection.commit()
            return True
        except sqlite3.Error as error:
            logging.error("Error en el CREAR la TABLA tickers: %s", error)
            print("Error en el CREAR la TABLA tickers: %s", error)
            return False

    def on_cargar(self, widget):
        datos = {
            (self.nombre_texto.value or "").strip():
            (self.ticker_texto.value or "").strip()
        }

        ok = False

        if self.existe_ticker(list(datos.keys())[0], list(datos.values())[0]):
            self.label_estado = "✅"
        elif self.nombre_con_otro_ticker(list(datos.keys())[0], list(datos.values())[0]):
            self.label_estado = "⚠️ El nombre ya existe con otro ticker"
        elif self.ticker_con_otro_nombre(list(datos.keys())[0], list(datos.values())[0]):
            self.label_estado = "⚠️ El ticker ya existe con otro nombre"
        else:
            ok = self.guardarTickersBDD(datos)

        if ok:
            self.valor_estado = "✅"
            self.label_pantalla_nuevoTicker.text += self.valor_estado
            print("Ticker guardado correctamente")
            return
        else:
            self.valor_estado = "❌"
            self.label_pantalla_nuevoTicker.text += self.valor_estado
            print("Error al guardar ticker")
        
        self.label_pantalla_nuevoTicker.text += self.valor_estado

    def on_cargarValoracion(self, widget):
        datos = {
            (self.nombre_texto.value or "").strip():
            (self.ticker_texto.value or "").strip()
        }

        ok = False

        if self.existe_ticker(list(datos.keys())[0], list(datos.values())[0]):
            self.label_estado = "✅"
        elif self.nombre_con_otro_ticker(list(datos.keys())[0], list(datos.values())[0]):
            self.label_estado = "⚠️ El nombre ya existe con otro ticker"
        elif self.ticker_con_otro_nombre(list(datos.keys())[0], list(datos.values())[0]):
            self.label_estado = "⚠️ El ticker ya existe con otro nombre"
        else:
            ok = self.guardarTickersBDD(datos)

        if ok:
            self.valor_estado = "✅"
            self.label_pantalla_nuevoTicker.text += self.valor_estado
            print("Ticker guardado correctamente")
            return
        else:
            self.valor_estado = "❌"
            self.label_pantalla_nuevoTicker.text += self.valor_estado
            print("Error al guardar ticker")
        
        self.label_pantalla_nuevoTicker.text += self.valor_estado
    
    def guardarTickersBDD(self, tickers_dict) -> bool:
        try:
            cursor = self.sqliteConnection.cursor()

            for nombre, ticker in tickers_dict.items():
                nombre = (nombre or "").strip()
                ticker = (ticker or "").strip()
                if not nombre or not ticker:
                    continue
                cursor.execute("""
                    INSERT INTO tickers (nombre, ticker)
                    VALUES (?, ?) ON CONFLICT(nombre) DO UPDATE SET ticker=excluded.ticker
                """, (nombre, ticker))

            self.sqliteConnection.commit()
            return True

        except sqlite3.Error as error:
            logging.error("Error al guardar tickers: %s", error)
            return False

    def leerTickersBDD(self) -> dict:
        try:
            cursor = self.sqliteConnection.cursor()

            cursor.execute("SELECT nombre, ticker FROM tickers")
            rows = cursor.fetchall()

            # reconstruir diccionario
            tickers = {nombre: ticker for nombre, ticker in rows}

            return tickers

        except sqlite3.Error as error:
            logging.error("Error al leer tickers: %s", error)
            return {}

def main():
    return BolsaPy("BolsaPy App", "com.SkullWithGasMask", icon="resources/icon.png")

if __name__ == "__main__":
    app = main()
    app.main_loop()