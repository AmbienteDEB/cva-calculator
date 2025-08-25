import os
import arcpy
import xlsxwriter

# Establecer el espacio de trabajo y las variables iniciales
ndvi_folder_proyect = "D:/HistoricoEmbalse/agosto2024/NDVI"
arcpy.env.workspace = ndvi_folder_proyect

# Listar las carpetas del directorio
folders = [f for f in os.listdir(arcpy.env.workspace) if os.path.isdir(os.path.join(arcpy.env.workspace, f))]

# Crear un nuevo archivo Excel para los resultados
workbook = xlsxwriter.Workbook('D:/HistoricoEmbalse/agosto2024/total_areas-ago2024.xlsx')
worksheet = workbook.add_worksheet()
worksheet.write(0, 0, 'Shapefile')
worksheet.write(0, 1, 'Total Area (m2)')

row = 1

# Recorrer las carpetas
for folder in folders:
    current_folder = os.path.join(ndvi_folder_proyect, folder)
    arcpy.env.workspace = current_folder
    shapefiles = arcpy.ListFeatureClasses("*projected*")  # Filtrar por shapefiles que contienen "projected"

    # Calcular el area total para cada shapefile y escribir en el Excel
    for shapefile in shapefiles:
        total_area = 0
        with arcpy.da.SearchCursor(shapefile, ["area_m2"]) as cursor:
            for record in cursor:
                total_area += record[0]

        # Escribir el nombre del shapefile y el area total en el archivo Excel
        worksheet.write(row, 0, shapefile)
        worksheet.write(row, 1, total_area)
        row += 1

# Cerrar el archivo Excel
workbook.close()
