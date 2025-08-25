# -*- coding: utf-8 -*-
import os
import Tkinter as tk
import tkFileDialog
import tkMessageBox
import re
import arcpy
from arcpy.sa import *
import datetime
import csv

# Constantes para los nombres de los directorios
MASKS_DIR_LABEL = "Seleccionar Directorio de Máscaras"
NDVI_DIR_LABEL = "Seleccionar Directorio de NDVI"
RGB_DIR_LABEL = "Seleccionar Directorio de RGB"
OUTPUT_DIR_LABEL = "Seleccionar Directorio de Salida"

# Variables globales para almacenar los directorios seleccionados
directorio_mascaras = ""
directorio_ndvi = ""
directorio_rgb = ""
directorio_salida = ""

def seleccionar_directorio(label_text, lista_archivos=None, label_salida=None, variable_seleccion=None):
    """
    Función para seleccionar un directorio.
    Si lista_archivos está definida, muestra los archivos del directorio seleccionado.
    Si label_salida está definida, muestra el directorio seleccionado en la etiqueta.
    Si variable_seleccion está definida, almacena el directorio seleccionado en una variable global.
    """
    global directorio_mascaras, directorio_ndvi, directorio_rgb, directorio_salida

    directorio = tkFileDialog.askdirectory(title=label_text)

    if directorio:
        if lista_archivos:
            lista_archivos.delete(0, tk.END)  # Limpiamos la lista anterior
            archivos = os.listdir(directorio)  # Obtenemos los archivos del directorio
            for archivo in archivos:
                lista_archivos.insert(tk.END, archivo)  # Mostramos los archivos en la lista
        if label_salida:
            label_salida.config(text=directorio)  # Mostrar el directorio de salida en la etiqueta
        if variable_seleccion == "directorio_mascaras":
            directorio_mascaras = directorio
        elif variable_seleccion == "directorio_ndvi":
            directorio_ndvi = directorio
        elif variable_seleccion == "directorio_rgb":
            directorio_rgb = directorio
        elif variable_seleccion == "directorio_salida":
            directorio_salida = directorio

    return directorio  # Retorna el directorio seleccionado


def crear_lista_con_scrollbar(frame, width=30, height=5):
    """
    Crea una lista con scrollbar en un frame.
    """
    lista_frame = tk.Frame(frame)
    lista = tk.Listbox(lista_frame, width=width, height=height)
    lista.pack(side="left", fill="both")

    scrollbar = tk.Scrollbar(lista_frame, orient="vertical")
    scrollbar.pack(side="right", fill="y")
    lista.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=lista.yview)

    return lista_frame, lista


def validar_y_calcular():
    """
    Valida los directorios seleccionados y realiza el cálculo.
    Muestra errores o confirmación de éxito según el resultado de la validación.
    """
    global directorio_mascaras, directorio_ndvi, directorio_rgb, directorio_salida

    # Validar que los directorios no estén vacíos
    if not directorio_mascaras or not directorio_ndvi or not directorio_rgb or not directorio_salida:
        tkMessageBox.showerror("Error", "Debe seleccionar los cuatro directorios.")
        return

    # Validar que en el directorio de máscaras haya exactamente un archivo .shp
    archivos_mascaras = [f for f in os.listdir(directorio_mascaras) if f.endswith('.shp')]
    if len(archivos_mascaras) != 1:
        tkMessageBox.showerror("Error", "El directorio de Máscaras debe contener exactamente un archivo .shp.")
        return

    # Validar que los archivos en NDVI tengan el formato NDVI_YYYY-MM-DD.tif
    patron_ndvi = re.compile(r"^NDVI_\d{4}-\d{2}-\d{2}\.tif$")
    archivos_ndvi = [f for f in os.listdir(directorio_ndvi) if f.endswith('.tif')]
    if not all(patron_ndvi.match(f) for f in archivos_ndvi):
        tkMessageBox.showerror("Error", "Los archivos en NDVI deben tener el formato NDVI_YYYY-MM-DD.tif.")
        return

    # Validar que los archivos en RGB tengan el formato RGB_YYYY-MM-DD.tif
    patron_rgb = re.compile(r"^RGB_\d{4}-\d{2}-\d{2}\.tif$")
    archivos_rgb = [f for f in os.listdir(directorio_rgb) if f.endswith('.tif')]
    if not all(patron_rgb.match(f) for f in archivos_rgb):
        tkMessageBox.showerror("Error", "Los archivos en RGB deben tener el formato RGB_YYYY-MM-DD.tif.")
        return

    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        directorio_output_resources = os.path.join(directorio_salida, timestamp + "/resources")
        directorio_salida = os.path.join(directorio_salida, timestamp)
        # Crear el directorio de salida si no existe
        if not os.path.exists(directorio_salida):
            os.makedirs(directorio_salida)
        if not os.path.exists(directorio_output_resources):
            os.makedirs(directorio_output_resources)
        ejecutar_proceso_vegetacion(directorio_mascaras, directorio_ndvi, directorio_rgb, directorio_output_resources)
        calcular_areas_shapefiles(directorio_salida, directorio_output_resources)
        tkMessageBox.showinfo("Éxito", "El proceso se ha completado exitosamente.")
    except Exception as e:
        print e
        tkMessageBox.showerror("Error durante el proceso", "Ha ocurrido un error: " + str(e))

def configurar_directorio(frame, row, col, label_text, variable_seleccion):
    """
    Configura un bloque con una etiqueta, lista con scrollbar, y botón de selección para directorios.
    """
    # Etiqueta para el directorio
    etiqueta = tk.Label(frame, text=label_text)
    etiqueta.grid(row=0, column=col, padx=10, pady=5)

    # Lista con scrollbar para mostrar archivos
    lista_frame, lista = crear_lista_con_scrollbar(frame)
    lista_frame.grid(row=1, column=col, padx=10, pady=5)

    # Botón para seleccionar el directorio
    boton = tk.Button(frame, text="Seleccionar", command=lambda: seleccionar_directorio(label_text, lista, variable_seleccion=variable_seleccion))
    boton.grid(row=2, column=col, padx=10, pady=5)


def calcular_areas_shapefiles(directorio_salida, directorio_output_resources):
    """
    Esta función lee los shapefiles en la raíz de la carpeta de recursos, calcula el área total de cada uno
    y escribe los resultados en un archivo CSV en el directorio de salida.
    """
    # Crear un nuevo archivo CSV para los resultados
    output_csv = os.path.join(directorio_salida, 'total_areas.csv')

    # Abrir el archivo CSV para escribir los resultados
    with open(output_csv, 'wb') as csvfile:
        writer = csv.writer(csvfile)

        # Escribir los encabezados de la tabla
        writer.writerow(['Shapefile', 'Total Area (m2)'])

        # Listar los shapefiles que están en la raíz de la carpeta de recursos
        arcpy.env.workspace = directorio_output_resources
        shapefiles = arcpy.ListFeatureClasses("*.shp")  # Listar todos los shapefiles en la raíz

        # Recorrer los shapefiles y calcular el área total
        for shapefile in shapefiles:
            # Verificar si el campo "area_m2" existe en el shapefile
            field_names = [f.name for f in arcpy.ListFields(shapefile)]
            if "area_m2" not in field_names:
                continue  # Saltar este shapefile si no tiene el campo

            total_area = 0

            # Usar un cursor para recorrer las áreas en el campo "area_m2"
            with arcpy.da.SearchCursor(shapefile, ["area_m2"]) as cursor:
                for record in cursor:
                    total_area += record[0]

            # Escribir el nombre del shapefile y el área total en el archivo CSV
            writer.writerow([shapefile, total_area])

    print("Resultados guardados en:", output_csv)


def sanitize_filename(filename):
    """
    Función para limpiar el nombre del archivo y eliminar caracteres no válidos.
    Reemplaza caracteres que no sean letras, números o guiones bajos.
    Los guiones ('-') también se reemplazan por guiones bajos ('_').
    """
    # Reemplazar los guiones ('-') por guiones bajos ('_')
    filename = filename.replace('-', '_')

    # Reemplazar cualquier otro carácter no válido por guiones bajos ('_')
    filename = re.sub(r'[^a-zA-Z0-9_]', '_', filename)

    return filename

def ejecutar_proceso_vegetacion(directorio_mascaras, directorio_ndvi, directorio_rgb, directorio_output_resources):

    """
    Esta función utiliza los directorios seleccionados por el usuario en la interfaz y ejecuta el proceso de análisis NDVI,
    generación de máscaras de vegetación y conversión a vectores, utilizando la librería arcpy.
    """

    # Establecer el espacio de trabajo y las variables iniciales
    arcpy.CheckOutExtension("Spatial")
    arcpy.env.overwriteOutput = True

    # Obtener el archivo shapefile de máscaras (el primero que encuentre)
    arcpy.env.workspace = directorio_mascaras
    mascara_agua = arcpy.ListFiles("*.shp")[0]  # Usar el primer .shp encontrado
    mascara_agua_path = os.path.join(directorio_mascaras, mascara_agua)

    # Cargar archivos NDVI y RGB
    arcpy.env.workspace = directorio_ndvi
    ndvi_rasters = arcpy.ListRasters("NDVI_*.tif")  # Listar los rasters NDVI con el formato correcto

    arcpy.env.workspace = directorio_rgb
    rgb_rasters = arcpy.ListRasters("RGB_*.tif")  # Listar los rasters RGB con el formato correcto

    # Definir el umbral de NDVI
    ndvi_threshold = 0.3  # Este valor puede ajustarse

    for ndvi_raster in ndvi_rasters:
        # Cargar el raster NDVI
        ndvi_raster_path = os.path.join(directorio_ndvi, ndvi_raster)
        ndvi_raster_obj = Raster(ndvi_raster_path)

        # Crear la máscara de vegetación con valores de NDVI mayores al umbral
        vegetation_mask = ndvi_raster_obj > Float(ndvi_threshold)

        # Generar el nombre del archivo de salida para la máscara de vegetación
        base_name, _ = os.path.splitext(ndvi_raster)
        base_name = sanitize_filename(base_name)
        output_raster_path = os.path.abspath(
            os.path.join(directorio_output_resources, "{}_veg_mask.tif".format(base_name)))

        # Guardar la máscara resultante
        vegetation_mask.save(output_raster_path)

        # Convertir la máscara a polígonos (vector)
        vegetation_polygon_path = os.path.abspath(
            os.path.join(directorio_output_resources, "{}_veg.shp".format(base_name)))
        arcpy.RasterToPolygon_conversion(output_raster_path, vegetation_polygon_path, "NO_SIMPLIFY", "VALUE")

        # Seleccionar los polígonos correspondientes a vegetación dentro del embalse
        arcpy.MakeFeatureLayer_management(vegetation_polygon_path, "veglayer")
        arcpy.SelectLayerByAttribute_management("veglayer", "NEW_SELECTION", "gridcode = 1")

        # Guardar la capa seleccionada
        selected_vegetation_path = os.path.join(directorio_output_resources, "{}_selected_veg.shp".format(base_name))
        arcpy.CopyFeatures_management("veglayer", selected_vegetation_path)

        # Proyectar la capa a UTM para calcular el área en metros cuadrados
        projected_vegetation_path = os.path.join(directorio_output_resources, "{}_projected_veg.shp".format(base_name))
        arcpy.Project_management(selected_vegetation_path, projected_vegetation_path, arcpy.SpatialReference(32616))  # UTM Zone 16N

        # Añadir un campo para el área si no existe
        field_names = [f.name for f in arcpy.ListFields(projected_vegetation_path)]
        if "area_m2" not in field_names:
            arcpy.AddField_management(projected_vegetation_path, "area_m2", "DOUBLE")

        # Calcular el área de cada polígono y almacenarla en el campo "area_m2"
        arcpy.CalculateField_management(projected_vegetation_path, "area_m2", "!shape.area@SQUAREMETERS!", "PYTHON_9.3")

        print("Proceso completado para:", projected_vegetation_path)

    arcpy.CheckInExtension("Spatial")

def main():
    # Crear la ventana principal
    ventana = tk.Tk()
    ventana.title("Seleccionar Directorios")

    # Crear el contenedor para los primeros tres directorios (Máscaras, NDVI, RGB)
    frame_directorios = tk.Frame(ventana)
    frame_directorios.pack(pady=10)

    # Configurar los bloques de selección de directorio para "Máscaras", "NDVI", y "RGB"
    configurar_directorio(frame_directorios, row=0, col=0, label_text=MASKS_DIR_LABEL, variable_seleccion="directorio_mascaras")
    configurar_directorio(frame_directorios, row=0, col=1, label_text=NDVI_DIR_LABEL, variable_seleccion="directorio_ndvi")
    configurar_directorio(frame_directorios, row=0, col=2, label_text=RGB_DIR_LABEL, variable_seleccion="directorio_rgb")

    # Directorio de salida (sin mostrar contenido, pero mostrando la ruta en un label)
    etiqueta_salida = tk.Label(ventana, text=OUTPUT_DIR_LABEL)
    etiqueta_salida.pack(pady=10)

    label_salida = tk.Label(ventana, text="No se ha seleccionado un directorio", fg="blue")
    label_salida.pack(pady=5)

    boton_salida = tk.Button(ventana, text="Seleccionar Directorio de Salida",
                             command=lambda: seleccionar_directorio(OUTPUT_DIR_LABEL, label_salida=label_salida, variable_seleccion="directorio_salida"))
    boton_salida.pack(pady=10)

    # Botón para calcular (validar y ejecutar el script)
    boton_calcular = tk.Button(ventana, text="Calcular", command=validar_y_calcular)
    boton_calcular.pack(pady=10)

    # Iniciar el bucle de la ventana
    ventana.mainloop()


if __name__ == "__main__":
    main()
