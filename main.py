# coding=utf-8
import os
import arcpy
from arcpy.sa import *

# Establecer el espacio de trabajo y las variables iniciales
arcpy.CheckOutExtension("Spatial")
arcpy.env.overwriteOutput = True

# Datos ubicacion de los archivos de entrada
base_folder = 'D:\\HistoricoEmbalse\\agosto2024'
mascara_agua_folder = os.path.join(base_folder, "Mascaras_de_agua_actualizada")
ndvi_mask_folder = os.path.join(base_folder, "NDVI")
rgb_folder = os.path.join(base_folder, "RGB")
print(mascara_agua_folder, ndvi_mask_folder, rgb_folder)

# 2. Cargar archivos
# Para cargar los shapefiles de mascaras de agua, establece el workspace adecuadamente
arcpy.env.workspace = mascara_agua_folder
mascara_agua = arcpy.ListFiles("*.shp")  # Listar solo archivos .shp en el directorio actual del workspace
print("estas son las mascaras de agua ", mascara_agua)

# Cambiar el workspace para los rasters NDVI y luego listarlos
arcpy.env.workspace = ndvi_mask_folder

# Listar las carpetas del directorio
folders = [f for f in os.listdir(arcpy.env.workspace) if os.path.isdir(os.path.join(arcpy.env.workspace, f))]
print("estos son los folders ", folders)

# Recorrer las carpetas
for folder in folders:
    current_folder = os.path.join(ndvi_mask_folder, folder)
    print("estamos recorriendo el folder " + current_folder)
    arcpy.env.workspace = current_folder
    print(arcpy.env.workspace)
    ndvi_rasters = arcpy.ListRasters("*", "TIF")  # Listar todos los rasters TIF
    print(ndvi_rasters)

    # 4. Calcular mascara utilizando un umbral de NDVI
    ndvi_threshold = 0.3  # Este valor puede ajustarse segun sea necesario
    for ndvi_raster in ndvi_rasters:
        # Cargar el raster
        ndvi_raster_path = os.path.join(current_folder, ndvi_raster)
        ndvi_raster_obj = Raster(ndvi_raster_path)

        # Crear la mascara con valores de NDVI mayores al umbral
        vegetation_mask = ndvi_raster_obj > Float(
            ndvi_threshold)  # Asegurar que la comparacion se realiza correctamente

        # Construir el nombre del archivo de salida
        base_name, _ = os.path.splitext(ndvi_raster)
        output_raster_path = os.path.join(base_folder, "NDVI", folder, "{}mask.tif".format(base_name))

        # Guardar la mascara resultante
        vegetation_mask.save(output_raster_path)

        # 5. Convertir a vector
        vegetation_raster_path = output_raster_path  # type: str
        vegetation_polygon_path = vegetation_raster_path.replace('mask.tif',
                                                                 'veg.shp').replace("-", "").replace("_", "")
        print(vegetation_polygon_path, vegetation_raster_path)
        # Cambiar la extension para el archivo de salida
        arcpy.RasterToPolygon_conversion(vegetation_raster_path, vegetation_polygon_path, "NO_SIMPLIFY", "VALUE")

        # 6. Elegir poligonos correspondientes a vegetacion dentro del embalse
        # Crear una capa de entidades para poder seleccionar
        arcpy.MakeFeatureLayer_management(vegetation_polygon_path, "veglayer")
        arcpy.SelectLayerByAttribute_management("veglayer", "NEW_SELECTION", "gridcode = 1")

        # 7. Guardar capa con poligonos correspondientes a vegetacion dentro del embalse
        selected_vegetation_path = vegetation_polygon_path.replace('veg.shp', 'selected.shp')
        arcpy.CopyFeatures_management("veglayer", selected_vegetation_path)

        # 8. Proyectar capa a UTM para calculo de area en metros
        projected_vegetation_path = selected_vegetation_path.replace('selected.shp', 'projected.shp')
        arcpy.Project_management(selected_vegetation_path, projected_vegetation_path, arcpy.SpatialReference(32616))

        # Añadir un campo de área si aún no existe
        field_names = [f.name for f in arcpy.ListFields(projected_vegetation_path)]
        if "area_m2" not in field_names:
            arcpy.AddField_management(projected_vegetation_path, "area_m2", "DOUBLE")

        # Calcular el area de cada poligono en el shapefile y almacenarla en el campo "area_m2"
        arcpy.CalculateField_management(projected_vegetation_path, "area_m2", "!shape.area@SQUAREMETERS!", "PYTHON_9.3")
