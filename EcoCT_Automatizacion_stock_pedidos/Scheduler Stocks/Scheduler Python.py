import schedule
import time
import pandas as pd
from datetime import datetime
import requests
from io import BytesIO
import configparser 
import gspread
from gspread_dataframe import set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import a1_to_rowcol, rowcol_to_a1


CONFIG_FILE_PATH = 'Curso agentes/Agente contenedores/seguimiento-matriculas/EcoCT_Automatizacion_stock_pedidos/config/config_stock.ini' 
CREDENTIALS_FILE = 'Curso agentes/Agente contenedores/seguimiento-matriculas/EcoCT_Automatizacion_stock_pedidos/Scheduler Stocks/stocks-480110-0c0bf0c9b1e2.json' 
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

def get_config_value(section, key):
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE_PATH)
        value = config.get(section, key)
        return value.strip('"').strip("'")
    except Exception as e:
        print(f"Error al leer la configuración [{section}] {key}: {e}")
        return None

FILE_PATH_OR_URL = get_config_value('GOOGLE_SHEETS', 'FILE_URL')
SPREADSHEET_ID = get_config_value('GOOGLE_SHEETS', 'SPREADSHEET_ID')
SHEET_NAME_FOR_ORDER = get_config_value('GOOGLE_SHEETS', 'WORKSHEET_NAME') or 'Stock'

if not FILE_PATH_OR_URL:
    print("FATAL: No se pudo cargar la URL del archivo desde la configuración. Terminando.")
if not SPREADSHEET_ID:
    print("FATAL: No se pudo cargar el SPREADSHEET_ID desde la configuración. Terminando.")


def abrirArchivoDatos(path_or_url: str) -> pd.DataFrame:
    print(f"Abriendo archivo de datos desde: {path_or_url}...")
    
    if path_or_url.startswith('http'):
        try:
            response = requests.get(path_or_url)
            response.raise_for_status() 
            
            content = BytesIO(response.content)
            
            try:
                df = pd.read_csv(content)
                print("Datos leídos como CSV desde URL.")
                return df
            except Exception:
                content.seek(0)
                try:
                    df = pd.read_excel(content)
                    print("Datos leídos como Excel desde URL.")
                    return df
                except Exception as ex:
                    print(f"Fallo al intentar leer como CSV y Excel desde URL. Error: {ex}")
                    return pd.DataFrame()

        except requests.exceptions.RequestException as e:
            print(f"Error al acceder a la URL: {e}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error al leer el archivo desde la URL con pandas: {e}")
            return pd.DataFrame()
            
    else:
        try:
            df = pd.read_excel(path_or_url) 
            print("Datos leídos desde archivo Excel local.")
            return df
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo en la ruta local: {path_or_url}")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error al leer el archivo Excel local: {e}")
            return pd.DataFrame()

def formatear_como_numero_en_gsheets(spreadsheet_id: str, sheet_name: str, col_index: int, total_rows: int):
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        
        start_row = 2 
        end_row = total_rows + 1 
        
        col_letter = rowcol_to_a1(1, col_index).rstrip('1')
        range_to_format = f"{col_letter}{start_row}:{col_letter}{end_row}"

        worksheet.format(range_to_format, {
            "numberFormat": {
                "type": "NUMBER", 
                "pattern": "0"     
            }
        })
        print(f"Formato numérico aplicado a rango: {range_to_format}.")

    except Exception as e:
        print(f"Error al aplicar formato numérico: {e}")
        
# --------------------------------------------------------


def actualizar_columna_shopping_list(df_completo: pd.DataFrame, sheet_name: str, spreadsheet_id: str):
    """
    Actualiza SOLO la columna 'Shopping list' de la hoja de Google Sheets 
    enviando números y luego aplicando formato para evitar la detección de fecha.
    """
    
    try:
        # Autenticación
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPE)
        gc = gspread.authorize(creds)
        print("Autenticación con Google Sheets exitosa para actualización parcial.")
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)
        
        data_gs = worksheet.get_all_records()
        df_gs = pd.DataFrame(data_gs)
        
        if df_gs.empty:
            print("Error: La hoja de destino está vacía. No se puede actualizar parcialmente.")
            return

        df_merged = df_gs.merge(
            df_completo[['MATERIALS', 'Shopping list']], 
            on='MATERIALS', 
            how='left',
            suffixes=('_old', '_new')
        )
        
        new_shopping_list_values = df_merged['Shopping list_new'].fillna('').tolist()
        
        data_to_update = []
        for val in new_shopping_list_values:
            if val == '':
                data_to_update.append(['']) 
            else:
                try:
                    data_to_update.append([int(val)]) 
                except ValueError:
                    data_to_update.append(['']) 


        col_info = worksheet.find('Shopping list')
        col_index = col_info.col 
        total_rows = len(new_shopping_list_values) 

        start_row = 2 
        end_row = total_rows + 1 
        update_range = rowcol_to_a1(start_row, col_index) + ':' + rowcol_to_a1(end_row, col_index)
        
        worksheet.update(data_to_update, range_name=update_range)
        print(f"Columna 'Shopping list' ({update_range}) actualizada exitosamente en la hoja '{sheet_name}'.")

        formatear_como_numero_en_gsheets(spreadsheet_id, sheet_name, col_index, total_rows)


    except gspread.exceptions.SpreadsheetNotFound as e:
        print(f"Error: SpreadsheetNotFound. Verifica que el SPREADSHEET_ID es correcto. Detalle: {e}")
    except gspread.WorksheetNotFound:
        print(f"Error: La hoja '{sheet_name}' no existe en el documento. Verifica el WORKSHEET_NAME.")
    except gspread.exceptions.CellNotFound:
        print(f"Error: La columna 'Shopping list' NO fue encontrada en la hoja '{sheet_name}'. Asegúrate del nombre.")
    except Exception as r:
        print(f"DETALLE COMPLETO DEL ERROR EN ACTUALIZACIÓN PARCIAL: {type(r).__name__} - {r}")


def generar_stock_listado():
    df = abrirArchivoDatos(FILE_PATH_OR_URL) 

    if df.empty:
        print("No se pudo cargar el DataFrame, deteniendo la generación de la lista.")
        return

    required_cols = ['Quantity', 'Minimum', 'Additional after Minimum', 'MATERIALS']
    df.columns = df.columns.str.strip() 
    
    if not all(col in df.columns for col in required_cols):
        missing_cols = [col for col in required_cols if col not in df.columns]
        print(f"Error: El archivo de datos debe contener las columnas: {required_cols}. Faltan: {missing_cols}")
        return

    cols_to_convert = ['Quantity', 'Minimum', 'Additional after Minimum']
    for col in cols_to_convert:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    def calcular_pedido(row):
        quantity = row['Quantity']
        minimum = row['Minimum']
        additional = row['Additional after Minimum']
        
        if quantity <= minimum:
            return (minimum - quantity) + additional
        else:
            return ''

    df['Shopping list'] = df.apply(calcular_pedido, axis=1)

    lista_final_adm = df[df['Shopping list'] != '']
    
    if SPREADSHEET_ID: 
        df_to_update = df[['MATERIALS', 'Shopping list']].copy() 
        actualizar_columna_shopping_list(df_to_update, SHEET_NAME_FOR_ORDER, SPREADSHEET_ID)
    else:
        print(" Advertencia: No se pudo encontrar el Spreadsheet ID, no se puede guardar en Google Sheets.")
    """
    if not lista_final_adm.empty:
        print("\n Lista final para el pedido (Administración):")
        cols_to_print = ['MATERIALS', 'SUPPLIER', 'Shopping list']
        valid_cols = [col for col in cols_to_print if col in lista_final_adm.columns]
        print(lista_final_adm[valid_cols].to_string(index=False))
    else:
        print("\n No hay productos que cumplan con la condición de pedido.")
    """

def tarea_programada():
    print(f"\n--- Ejecutando tarea de stock a las {datetime.now().strftime('%H:%M:%S')} ---")
    generar_stock_listado()

if __name__ == "__main__":
    if not (FILE_PATH_OR_URL and SPREADSHEET_ID):
        print("Terminando la ejecución por falta de configuración vital.")
    else:
        schedule.every(10).seconds.do(tarea_programada) 
        # schedule.every(14).days.at("07:00").do(tarea_programada)

        print("Scheduler iniciado. Esperando la próxima ejecución...")

        while True:
            schedule.run_pending()
            time.sleep(1)