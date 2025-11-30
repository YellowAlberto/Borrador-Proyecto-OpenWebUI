import schedule
import time
import pandas as pd
from datetime import datetime

ARCHIVO_STOCKS = "C:/Users/alber/OneDrive/Escritorio/IABD/Curso agentes/Agente contenedores/seguimiento-matriculas/src/Cron Stocks/Archivo Excel Ejemplo.xlsx"

def abrirArchivoExcel():
    print("Abriendo archivo Excel...")
    df = pd.read_excel(ARCHIVO_STOCKS) #Aqui iria el archivo de excel al que acceder
    
    return df

def generar_stock_listado():
        
    df = abrirArchivoExcel()

    def calcular_pedido(row):
        quantity = row['Quantity']
        minimum = row['Minimum']
        additional = row['Additional after Minimum']
        
        if quantity <= minimum:
            return (minimum - quantity) + additional
        else:
            return '' # No se necesita compra

    df['Shopping list'] = df.apply(calcular_pedido, axis=1)

    
    file_name = f"Stock_Supplies_Automatizado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    try:
        df.to_excel(file_name, sheet_name='Stock Supplies', index=False)
        print(f"Archivo '{file_name}' generado con éxito.")
        print(f"La lista de la compra calculada (columna 'Shopping list') contiene los siguientes valores:\n{df['Shopping list']}")
        
        lista_final_adm = df[df['Shopping list'] != '']
        if not lista_final_adm.empty:
            print("\n Lista final para el pedido (Administración - sin vacíos):")
            print(lista_final_adm[['MATERIALS', 'SUPPLIER', 'Shopping list']].to_string(index=False))
        else:
             print("\nNo hay productos que cumplan con la condición de pedido.")
             
    except Exception as e:
        print(f"Error al generar el archivo Excel: {e}")

def tarea_programada():
    print(f"\n--- Ejecutando tarea de stock a las {datetime.now().strftime('%H:%M:%S')} ---")
    generar_stock_listado()

schedule.every(14).days.at("07:00").do(tarea_programada)

print("Scheduler iniciado. Esperando la próxima ejecución...")

while True:
    schedule.run_pending()
    time.sleep(1) 