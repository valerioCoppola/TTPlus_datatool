# -*- coding: utf-8 -*-
"""
Code Developed by Nature4.0 and FEM teams.
"""

import ssl
import sys
import FreeSimpleGUI as sg
from pathlib import Path
import pytz
import json
import numpy as np
import pandas as pd
import urllib.request
import os
from scipy.signal import savgol_filter
from matplotlib import pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import plotly
import numpy as numpy
plt.rcParams["font.family"] = "Palatino Linotype"
# from sklearn import linear_model
import os
import glob
import ssl
import urllib.request


# import pandas as pd
# from sklearn.linear_model import LinearRegression

TreeType = ["ring-porous", "ring-porous 1 cm",
    "diffuse-porous", "conifer", "conifer 20/40", "sawdust"]
# SFD_Type = ["ring-porous (10|50) 2 cm","ring-porous (10|50) 1 cm","diffuse-porous (10|50) 2 cm","coniferous (10|50) 2 cm",'coniferous (10|50) 2 cm']
# Equation = ["linear","sigmoid"]
# Initialize an empty dictionary
saved_values = {}


def save_values_to_file(values, file_path):
    with open(file_path, 'w') as f:
        json.dump(values, f, indent=4)  # Save values as JSON with indentation


def load_values_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    else:
        return {}

def read_server_data(url):
    """Yield rows from a server data file line by line, splitting on semicolon."""
    all_rows = []
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    max_rows=10000
    count = 0
    
    with urllib.request.urlopen(url, context=context) as response:
        for line in response:
            decoded = line.decode('UTF-8').strip().replace(',', ';')
            if decoded:
                # Split and yield the list (do not replace , with ; here unless it's really needed)
                decoded = decoded.split(';')
                all_rows.append(decoded)
                
            #count += 1
            if max_rows is not None and count >= max_rows:
                return(all_rows)
            
    return (all_rows)
                

def read_folder_files(folder_path):
    """Return list-of-lists from all .txt and .csv in folder, adding '0' server_time column."""
    all_rows = []
    for ext in ('*.csv', '*.txt'):
        for file_path in glob.glob(os.path.join(folder_path, ext)):
            with open(file_path, 'r', encoding='utf-8') as f:
                
                max_rows=1000
                count = 0
                for line in f:
                    
                    
                    if line.strip():
                        fields = line.strip().split(';')
                        # Add dummy '0' as server_time
                        fields = ['0'] + fields
                        all_rows.append(fields)
                        
                        #count += 1
                        if max_rows is not None and count >= max_rows:
                            break
    return all_rows

def merge_and_pad(server_rows, local_rows):
    """Pad all rows to equal length and merge."""
    all_rows = []
    if server_rows and local_rows:
        all_rows = server_rows + local_rows
    else:
        all_rows = server_rows
        
    # 2. Find the max row length:
    maxlen = max(len(row) for row in all_rows)
    
    # 3. Pad all rows:
    padded_rows = [row + [''] * (maxlen - len(row)) for row in all_rows]
        
        
    df = pd.DataFrame(padded_rows)
    
    return df


def update_output_window(message):
    output_window['-OUTPUT-'].print(message)


class ConsoleOutput:
    def __init__(self, update_func):
        self.update_func = update_func

    def write(self, message):
        self.update_func(message)

    def flush(self):
        pass  # Add the flush method




# Define the layout for the output window
output_layout = [
    [sg.Output(size=(80, 20), key='-OUTPUT-')],
]

output_window = sg.Window('Output Window', output_layout, finalize=True)

# Replace sys.stdout with the console output object
sys.stdout = ConsoleOutput(update_output_window)


# Define the main layout for the TreeTalker TT+ Data Analyzer window
layout = [
    [sg.Text('Load config'), sg.Input(saved_values.get('load', ''), key='load'),
             sg.FileBrowse(file_types=(("JSON Files", "*.json"),)), sg.Button('Load')],
    [sg.Text('Site name'), sg.InputText(
        saved_values.get('site_name', ''), key='site_name')],
    [sg.Text('Serial No., eg. 81238007,81238008,...'), sg.InputText(
        key='item_id', default_text=saved_values.get('item_id', ''))],
    [sg.Text('Select manual data folder'), sg.Input(key='manual_upload'), sg.FolderBrowse()],
    
    [sg.Text('Folder'), sg.Input(saved_values.get(
        'folder', ''), key='folder'), sg.FolderBrowse()],
    [sg.Text('Select timezone'), sg.Combo(pytz.all_timezones,
             default_value=saved_values.get('timezone', ''), key='timezone')],
    [sg.Text('Start Date (YYYY-MM-DD HH:mm:ss)'), sg.InputText(key='start_date',
             default_text=saved_values.get('start_date', ''))],
    [sg.Text('End Date (YYYY-MM-DD HH:mm:ss)'), sg.InputText(key='end_date',
             default_text=saved_values.get('end_date', ''))],
    [sg.Checkbox('Tree probe', default=saved_values.get('tree_probe', False), key='tree_probe'),
     sg.Checkbox('Soil probe', default=saved_values.get('soil_probe', False), key='soil_probe')],
    [sg.Text('Species type'), sg.Combo(TreeType, key='species_type', default_value=saved_values.get('species_type', '')),
     sg.Text('Plot'), sg.Combo(['Store and visualize', 'Store only'], key='plot_option', default_value=saved_values.get('plot_option', ''))],
    [sg.Text('Save config'), sg.Input(saved_values.get('save', ''), key='save'),
             sg.FileSaveAs(file_types=(("JSON Files", "*.json"),)), sg.Button('Save')],
    [sg.Button('START'), sg.Button('CANCEL')],
]
# sg.Text('Species SFD type'), sg.Combo(TreeType, key='tree_sfd', default_value=saved_values.get('tree_sfd', '')),
# sg.Text('Equation type'), sg.Combo(TreeType, key='equation', default_value=saved_values.get('equation', '')),
# Create the TreeTalker TT+ Data Analyzer window
window = sg.Window('TreeTalker TT+ Data Analyzer', layout, finalize=True)

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED or event == 'CANCEL':
        break

    if event == 'Save':
        file_path = values['save']
        if file_path:
            save_values_to_file(values, file_path)
            sg.popup('Data saved successfully!')

    elif event == 'Load':
        file_path = values['load']
        if file_path:
            saved_values = load_values_from_file(file_path)
            window['site_name'].update(saved_values.get('site_name', ''))
            window['item_id'].update(saved_values.get('item_id', ''))
            window['manual_upload'].update(saved_values.get('manual_upload', ''))
            window['folder'].update(saved_values.get('folder', ''))
            window['timezone'].update(saved_values.get('timezone', ''))
            window['start_date'].update(saved_values.get('start_date', ''))
            window['end_date'].update(saved_values.get('end_date', ''))
            window['tree_probe'].update(saved_values.get('tree_probe', False))
            window['soil_probe'].update(saved_values.get('soil_probe', False))
            window['species_type'].update(saved_values.get('species_type', ''))
            # window['tree_sfd'].update(saved_values.get('tree_sfd', ''))
            # window['equation'].update(saved_values.get('equation', ''))
            window['plot_option'].update(saved_values.get('plot_option', ''))
            # print(saved_values)  # Print loaded values

    elif event == 'START':
        pass  # Your logic here
        if event == 'START':
            # Set the directory
            site = values['site_name']
            site_id = values['item_id']

            # Initialize dfall
            dfall = None
            
            # ---- How you use this in your GUI event loop ----
            server_rows = []
            local_rows = []
            
            urls = [f"http://naturetalkers.altervista.org/{site_id}/ttcloud.txt",
            f"http://ittn.altervista.org/{site_id}/ttcloud.txt"]
            
            if site_id:
                for url in urls:
                    server_rows += read_server_data(url)
            
            if values['manual_upload']:
                local_rows = read_folder_files(values['manual_upload'])
            
            # Merge everything
            dfall = merge_and_pad(server_rows, local_rows)
            
            # Convert TT ID to string type
            dfall[[1]] = dfall[[1]].astype(str)
            devices = dfall[1].unique()
            
            dfall = dfall.drop(columns=[0], axis=1)
            
            dfall.drop_duplicates(inplace=True)
            
            if dfall.empty:
                sg.popup_error("No data loaded. Please check your inputs.")
            else:
                sg.popup(f"Data loaded and merged. Shape: {dfall.shape}")

            output_directory = Path(values['folder'])
            timezone = values['timezone']

            if values['timezone'] in pytz.all_timezones:
                timezone = pytz.timezone(values['timezone'])
            else:
                print("Incorrect timezone - restart the program")

            start_date = values['start_date']
            
            end_date = values['end_date']

            if (values['tree_probe'] and values['soil_probe']) == True:
                print("Please select Tree OR Soil - restart the program")
            else:
                if values['tree_probe'] == True:
                    # Frequency data source ('soil' or 'tree')
                    data_freq = 'tree'
                elif values['soil_probe'] == True:
                    # Frequency data source ('soil' or 'tree')
                    data_freq = 'soil'
                else:
                    print("Please select Tree or Soil - restart the program")

                if values['species_type'] in TreeType:
                    species = values['species_type']
                else:
                    print("Incorrect species - restart the program")
                # if values['tree_sfd'] in SFD_Type:
                #     species = values['tree_sfd']
                # else:
                #      print("Incorrect species - restart the program")
                # if values['equation'] in Equation:
                #      equation = values['equation']
                # else:
                #       print("Incorrect species - restart the program")

                if values['plot_option'] == 'No Visualization':
                    continue  # Skip plotting


# window.close()
# output_window.close()


################

# function for season


                def seasons(date):
                    m = date.month
                    d = date.day
                    season = None
                    if (3 == m and d >= 21) or m == 4 or m == 5 or (m == 6 and 20 <= d):
                        season = 'spring'
                    elif (6 == m and d >= 21) or m == 7 or m == 8 or (m == 9 and 20 <= d):
                        season = 'summer'
                    elif (9 == m and d >= 21) or m == 10 or m == 11 or (m == 12 and 20 <= d):
                        season = 'autumn'
                    elif (12 == m and d >= 21) or m == 1 or m == 2 or (m == 3 and 20 <= d):
                        season = 'winter'
                    return season

################

# analyzing cloud data string type 4B

                if '4B' in dfall[3].values:
                    # Perform calculations when 'b' is present
                # Perform the calculation or any desired action here
                    df4B = dfall[dfall[3] == '4B'].copy()
                    # df4B = df4B.drop(df4B.columns[[13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]], axis = 1)
                    df4B = df4B.replace('', pd.NA)

                    df4B = df4B.dropna(how='all', axis=1)
                    # adding column's headers
                    df4B.columns = ['ID', 'record_number', 'device type', 'timestamp', 'records in memory',
                        'pending records',	'MCC',	'MNC',	'GSM registration',	'GSM field', 'Vbat',	'Firmware']

                    df4B = df4B.apply(pd.to_numeric, errors='ignore')

                    # # # # dropping wrong timstamps from dataset or selecting the period of measurment
                    # df4B.drop(df4B.loc[df4B['timestamp']<=1586976604].index, inplace=True)
                    # df4B.drop(df4B.loc[df4B['timestamp']>=1902787804].index, inplace=True)

                    # converting timestamp to real datetime
                    df4B['date'] = pd.to_datetime(df4B['timestamp'], unit='s').dt.tz_localize(
                        'UTC').dt.tz_convert(timezone).dt.tz_localize(None)

                    # Filter and keep rows within the date range
                    df4B = df4B[(df4B['date'] >= start_date)
                                 & (df4B['date'] <= end_date)]

                    # Day of Year
                    df4B['DOY'] = df4B['date'].dt.dayofyear
                    df4B = df4B.reset_index()
                    df4B = df4B[['ID', 'record_number', 'device type', 'timestamp', 'date', 'DOY',
                        'records in memory', 'pending records',	'MCC',	'MNC',	'GSM registration',	'GSM field', 'Vbat',	'Firmware']]

                    # Save the DataFrame as a CSV file
                    df4B.to_csv(output_directory / 'df4B.csv', index=False)

                    col = ['Vbat', 'GSM field']
      
                    units = {'Vbat': 'Cloud battery level (miliVolt)', 'GSM field': 'Signal strength'}
                            
                    for i in col:
                        fig = px.line(df4B, x = df4B['date'], y =[i], color='ID')  # Assuming 'ID' is a column in your DataFrame
                        
                        # Set the y-axis title with units if defined
                        y_axis_title = f"{i} ({units.get(i, 'no unit')})"  # 'no unit' will be used if the unit is not defined in the units dictionary
                        fig.update_layout(yaxis_title=y_axis_title)
                    
                        if values['plot_option'] == 'Store and visualize':
                            plotly.offline.plot(fig, filename=str(output_directory / (i+'_4B.html')))
                            
                        else:
                            plotly.offline.plot(fig, filename= str(output_directory / (i+'_4B.html')), auto_open=False)

                    df4B = df4B.reset_index()

                else:
                    # Print a message when 'b' is not present
                    print("There is no string type '4B' in the DataFrame column.")


# _________________CALLING DIFF DVICE TYPE______________________________________________________________________________________________
                # --------------------------45--------------------------------------
                # ----------------------------------------------------------------
                # THIS FILE WILL RUN FOR DATA TYPE 45, TT+3.1 VERSION (all data)

                if '45' in dfall[3].values:
                        # Filter the DataFrame to include only rows with 'b' in 'column_name'
                    df45 = dfall[dfall[3] == '45'].copy()
                    
                    df45 = df45.replace('', pd.NA)
                    df45 = df45.dropna(how='all', axis=1)
                    df45 = df45.reset_index(drop=True)

                    # adding column's headers
                    df45.columns = ['ID', 'record_number', 'device type', 'timestamp', 'Tref_start', 'Theat_start', 'Sharp sensor [d.n]',
                                    'adc_bat[d.n.]', 'No_of_bits', 'RH', 'airT', 'x','g_z(std.dev) [d.n.]','y','g_y (std.dev) [d.n.]','z','g_x (std.dev) [d.n.]',
                                    'Tref_end', 'Theat_end', 'freq']
                    
                    df45 = df45.apply(pd.to_numeric, errors='ignore')

                    df45['ID'] = df45['ID'].astype(str)

                    df45['date'] = pd.to_datetime(df45['timestamp'], unit='s').dt.tz_localize('UTC').dt.tz_convert(timezone).dt.tz_localize(None)
                    # Filter and keep rows within the date range
                    df45 = df45[(df45['date'] >= start_date)
                                 & (df45['date'] <= end_date)]

                    # df4D['season'] = df4D.apply(lambda x: seasons(x['date']), axis=1)  # Day of Year
                    df45['DOY'] = df45['date'].dt.dayofyear
                    df45['year'] = df45['date'].dt.year
                    df45['month'] = df45['date'].dt.month
                    df45['day'] = df45['date'].dt.day
                    df45['hour'] = df45['date'].dt.hour
                
                    		
                    df45 = df45.reset_index(drop=True, inplace=False)
                
                    
                
                
                    #************************ Applying lookup table for sap flow temeparure conversion ***************

                    from scipy.interpolate import interp1d
                    
                    X = [
                        1453, 1456.5, 1460, 1463.5, 1467, 1470.5, 1474, 1477.5, 1481, 1484.5,
                        1488, 1491.6, 1495.2, 1498.8, 1502.4, 1506, 1509.6, 1513.2, 1516.8,
                        1520.4, 1524, 1527.6, 1531.2, 1534.8, 1538.4, 1542, 1545.6, 1549.2,
                        1552.8, 1556.4, 1560, 1563.7, 1567.4, 1571.1, 1574.8, 1578.5, 1582.2,
                        1585.9, 1589.6, 1593.3, 1597, 1600.9, 1604.8, 1608.7, 1612.6, 1616.5,
                        1620.4, 1624.3, 1628.2, 1632.1, 1636, 1639.9, 1643.8, 1647.7, 1651.6,
                        1655.5, 1659.4, 1663.3, 1667.2, 1671.1, 1675, 1679.1, 1683.2, 1687.3,
                        1691.4, 1695.5, 1699.6, 1703.7, 1707.8, 1711.9, 1716, 1720.1, 1724.2,
                        1728.3, 1732.4, 1736.5, 1740.6, 1744.7, 1748.8, 1752.9, 1757, 1761.3,
                        1765.6, 1769.9, 1774.2, 1778.5, 1782.8, 1787.1, 1791.4, 1795.7, 1800,
                        1804.3, 1808.6, 1812.9, 1817.2, 1821.5, 1825.8, 1830.1, 1834.4, 1838.7,
                        1843, 1847.5, 1852, 1856.5, 1861, 1865.5, 1870, 1874.5, 1879, 1883.5,
                        1888, 1892.5, 1897, 1901.5, 1906, 1910.5, 1915, 1919.5, 1924, 1928.5,
                        1933, 1937.7, 1942.4, 1947.1, 1951.8, 1956.5, 1961.2, 1965.9, 1970.6,
                        1975.3, 1980, 1984.8, 1989.6, 1994.4, 1999.2, 2004, 2008.8, 2013.6,
                        2018.4, 2023.2, 2028, 2032.9, 2037.8, 2042.7, 2047.6, 2052.5, 2057.4,
                        2062.3, 2067.2, 2072.1, 2077, 2082, 2087, 2092, 2097, 2102, 2107,
                        2112, 2117, 2122, 2127, 2132.2, 2137.4, 2142.6, 2147.8, 2153, 2158.2,
                        2163.4, 2168.6, 2173.8, 2179, 2184.3, 2189.6, 2194.9, 2200.2, 2205.5,
                        2210.8, 2216.1, 2221.4, 2226.7, 2232, 2237.5, 2243, 2248.5, 2254,
                        2259.5, 2265, 2270.5, 2276, 2281.5, 2287, 2292.5, 2298, 2303.5, 2309,
                        2314.5, 2320, 2325.5, 2331, 2336.5, 2342, 2347.8, 2353.6, 2359.4,
                        2365.2, 2371, 2376.8, 2382.6, 2388.4, 2394.2, 2400, 2405.8, 2411.6,
                        2417.4, 2423.2, 2429, 2434.8, 2440.6, 2446.4, 2452.2, 2458, 2464.1,
                        2470.2, 2476.3, 2482.4, 2488.5, 2494.6, 2500.7, 2506.8, 2512.9, 2519,
                        2525.1, 2531.2, 2537.3, 2543.4, 2549.5, 2555.6, 2561.7, 2567.8, 2573.9,
                        2580, 2586.4, 2592.8, 2599.2, 2605.6, 2612, 2618.4, 2624.8, 2631.2,
                        2637.6, 2644, 2650.5, 2657, 2663.5, 2670, 2676.5, 2683, 2689.5, 2696,
                        2702.5, 2709, 2715.6, 2722.2, 2728.8, 2735.4, 2742, 2748.6, 2755.2,
                        2761.8, 2768.4, 2775, 2781.8, 2788.6, 2795.4, 2802.2, 2809, 2815.8,
                        2822.6, 2829.4, 2836.2, 2843, 2850, 2857, 2864, 2871, 2878, 2885,
                        2892, 2899, 2906, 2913, 2920.1, 2927.2, 2934.3, 2941.4, 2948.5, 2955.6,
                        2962.7, 2969.8, 2976.9, 2984, 2991.3, 2998.6, 3005.9, 3013.2, 3020.5,
                        3027.8, 3035.1, 3042.4, 3049.7, 3057, 3064.5, 3072, 3079.5, 3087,
                        3094.5, 3102, 3109.5, 3117, 3124.5, 3132, 3139.6, 3147.2, 3154.8,
                        3162.4, 3170, 3177.6, 3185.2, 3192.8, 3200.4, 3208, 3215.8, 3223.6,
                        3231.4, 3239.2, 3247, 3254.8, 3262.6, 3270.4, 3278.2, 3286, 3294,
                        3302, 3310, 3318, 3326, 3334, 3342, 3350, 3358, 3366, 3374.2, 3382.4,
                        3390.6, 3398.8, 3407, 3415.2, 3423.4, 3431.6, 3439.8, 3448, 3456.3,
                        3464.6, 3472.9, 3481.2, 3489.5, 3497.8, 3506.1, 3514.4, 3522.7, 3531,
                        3539.6, 3548.2, 3556.8, 3565.4, 3574, 3582.6, 3591.2, 3599.8, 3608.4,
                        3617, 3625.8, 3634.6, 3643.4, 3652.2, 3661, 3669.8, 3678.6, 3687.4,
                        3696.2, 3705, 3713.9, 3722.8, 3731.7, 3740.6, 3749.5, 3758.4, 3767.3,
                        3776.2, 3785.1, 3794, 3803.3, 3812.6, 3821.9, 3831.2, 3840.5, 3849.8,
                        3859.1, 3868.4, 3877.7, 3887, 3896.5, 3906, 3915.5, 3925, 3934.5,
                        3944, 3953.5, 3963, 3972.5, 3982, 3991.7, 4001.4, 4011.1, 4020.8,
                        4030.5, 4040.2, 4049.9, 4059.6, 4069.3, 4079, 4088.9, 4098.8, 4108.7,
                        4118.6, 4128.5, 4138.4, 4148.3, 4158.2, 4168.1, 4178, 4188.1, 4198.2,
                        4208.3, 4218.4, 4228.5, 4238.6, 4248.7, 4258.8, 4268.9, 4279, 4289.2,
                        4299.4, 4309.6, 4319.8, 4330, 4340.2, 4350.4, 4360.6, 4370.8, 4381,
                        4391.5, 4402, 4412.5, 4423, 4433.5, 4444, 4454.5, 4465, 4475.5, 4486,
                        4496.7, 4507.4, 4518.1, 4528.8, 4539.5, 4550.2, 4560.9, 4571.6, 4582.3,
                        4593, 4604, 4615, 4626, 4637, 4648, 4659, 4670, 4681, 4692, 4703,
                        4714.1, 4725.2, 4736.3, 4747.4, 4758.5, 4769.6, 4780.7, 4791.8, 4802.9,
                        4814, 4825.3, 4836.6, 4847.9, 4859.2, 4870.5, 4881.8, 4893.1, 4904.4,
                        4915.7, 4927, 4938.5, 4950, 4961.5, 4973, 4984.5, 4996, 5007.5, 5019,
                        5030.5, 5042, 5053.7, 5065.4, 5077.1, 5088.8, 5100.5, 5112.2, 5123.9,
                        5135.6, 5147.3, 5159, 5171, 5183, 5195, 5207, 5219, 5231, 5243, 5255,
                        5267, 5279, 5291.1, 5303.2, 5315.3, 5327.4, 5339.5, 5351.6, 5363.7,
                        5375.8, 5387.9, 5400, 5412.3, 5424.6, 5436.9, 5449.2, 5461.5, 5473.8,
                        5486.1, 5498.4, 5510.7, 5523, 5535.6, 5548.2, 5560.8, 5573.4, 5586,
                        5598.6, 5611.2, 5623.8, 5636.4, 5649, 5661.7, 5674.4, 5687.1, 5699.8,
                        5712.5, 5725.2, 5737.9, 5750.6, 5763.3, 5776, 5788.9, 5801.8, 5814.7,
                        5827.6, 5840.5, 5853.4, 5866.3, 5879.2, 5892.1, 5905, 5918.1, 5931.2,
                        5944.3, 5957.4, 5970.5, 5983.6, 5996.7, 6009.8, 6022.9, 6036, 6049.2,
                        6062.4, 6075.6, 6088.8, 6102, 6115.2, 6128.4, 6141.6, 6154.8, 6168,
                        6181.5, 6195, 6208.5, 6222, 6235.5, 6249, 6262.5, 6276, 6289.5, 6303,
                        6316.6, 6330.2, 6343.8, 6357.4, 6371, 6384.6, 6398.2, 6411.8, 6425.4,
                        6439, 6452.8, 6466.6, 6480.4, 6494.2, 6508, 6521.8, 6535.6, 6549.4,
                        6563.2, 6577, 6590.9, 6604.8, 6618.7, 6632.6, 6646.5, 6660.4, 6674.3,
                        6688.2, 6702.1, 6716, 6730.1, 6744.2, 6758.3, 6772.4, 6786.5, 6800.6,
                        6814.7, 6828.8, 6842.9, 6857, 6871.3, 6885.6, 6899.9, 6914.2, 6928.5,
                        6942.8, 6957.1, 6971.4, 6985.7, 7000, 7014.5, 7029, 7043.5, 7058,
                        7072.5, 7087, 7101.5, 7116, 7130.5, 7145, 7159.5, 7174, 7188.5, 7203,
                        7217.5, 7232, 7246.5, 7261, 7275.5, 7290, 7304.8, 7319.6, 7334.4,
                        7349.2, 7364, 7378.8, 7393.6, 7408.4, 7423.2, 7438, 7452.8, 7467.6,
                        7482.4, 7497.2, 7512, 7526.8, 7541.6, 7556.4, 7571.2, 7586, 7601,
                        7616, 7631, 7646, 7661, 7676, 7691, 7706, 7721, 7736, 7751.1, 7766.2,
                        7781.3, 7796.4, 7811.5, 7826.6, 7841.7, 7856.8, 7871.9, 7887, 7902.2,
                        7917.4, 7932.6, 7947.8, 7963, 7978.2, 7993.4, 8008.6, 8023.8, 8039,
                        8054.3, 8069.6, 8084.9, 8100.2, 8115.5, 8130.8, 8146.1, 8161.4, 8176.7,
                        8192, 8207.3, 8222.6, 8237.9, 8253.2, 8268.5, 8283.8, 8299.1, 8314.4,
                        8329.7, 8345, 8360.4, 8375.8, 8391.2, 8406.6, 8422, 8437.4, 8452.8,
                        8468.2, 8483.6, 8499, 8514.4, 8529.8, 8545.2, 8560.6, 8576, 8591.4,
                        8606.8, 8622.2, 8637.6, 8653, 8668.5, 8684, 8699.5, 8715, 8730.5,
                        8746, 8761.5, 8777, 8792.5, 8808, 8823.5, 8839, 8854.5, 8870, 8885.5,
                        8901, 8916.5, 8932, 8947.5, 8963, 8978.6, 8994.2, 9009.8, 9025.4,
                        9041, 9056.6, 9072.2, 9087.8, 9103.4, 9119, 9134.6, 9150.2, 9165.8,
                        9181.4, 9197, 9212.6, 9228.2, 9243.8, 9259.4, 9275, 9290.6, 9306.2,
                        9321.8, 9337.4, 9353, 9368.6, 9384.2, 9399.8, 9415.4, 9431, 9446.6,
                        9462.2, 9477.8, 9493.4, 9509, 9524.6, 9540.2, 9555.8, 9571.4, 9587,
                        9602.6, 9618.2, 9633.8, 9649.4, 9665, 9680.6, 9696.2, 9711.8, 9727.4,
                        9743, 9758.6, 9774.2, 9789.8, 9805.4, 9821, 9836.6, 9852.2, 9867.8,
                        9883.4, 9899, 9914.5, 9930, 9945.5, 9961, 9976.5, 9992, 10007.5, 10023,
                        10038.5, 10054, 10069.5, 10085, 10100.5, 10116, 10131.5, 10147, 10162.5,
                        10178, 10193.5, 10209, 10224.4, 10239.8, 10255.2, 10270.6, 10286,
                        10301.4, 10316.8, 10332.2, 10347.6, 10363, 10378.3, 10393.6, 10408.9,
                        10424.2, 10439.5, 10454.8, 10470.1, 10485.4, 10500.7, 10516, 10531.3,
                        10546.6, 10561.9, 10577.2, 10592.5, 10607.8, 10623.1, 10638.4, 10653.7,
                        10669, 10684.1, 10699.2, 10714.3, 10729.4, 10744.5, 10759.6, 10774.7,
                        10789.8, 10804.9, 10820, 10835, 10850, 10865, 10880, 10895, 10910,
                        10925, 10940, 10955, 10970, 10984.9, 10999.8, 11014.7, 11029.6,
                        11044.5, 11059.4, 11074.3, 11089.2, 11104.1, 11119, 11133.8, 11148.6,
                        11163.4, 11178.2, 11193, 11207.8, 11222.6, 11237.4, 11252.2, 11267,
                        11281.6, 11296.2, 11310.8, 11325.4, 11340, 11354.6, 11369.2, 11383.8,
                        11398.4, 11413, 11427.5, 11442, 11456.5, 11471, 11485.5, 11500,
                        11514.5, 11529, 11543.5, 11558, 11572.3, 11586.6, 11600.9, 11615.2,
                        11629.5, 11643.8, 11658.1, 11672.4, 11686.7, 11701, 11715.1, 11729.2,
                        11743.3, 11757.4, 11771.5, 11785.6, 11799.7, 11813.8, 11827.9, 11842,
                        11855.9, 11869.8, 11883.7, 11897.6, 11911.5, 11925.4, 11939.3, 11953.2,
                        11967.1, 11981, 11994.8, 12008.6, 12022.4, 12036.2, 12050, 12063.8,
                        12077.6, 12091.4, 12105.2, 12119, 12132.6, 12146.2, 12159.8, 12173.4,
                        12187, 12200.6, 12214.2, 12227.8, 12241.4, 12255, 12268.4, 12281.8,
                        12295.2, 12308.6, 12322, 12335.4, 12348.8, 12362.2, 12375.6, 12389,
                        12402.2, 12415.4, 12428.6, 12441.8, 12455, 12468.2, 12481.4, 12494.6,
                        12507.8, 12521, 12534, 12547, 12560, 12573, 12586, 12599, 12612,
                        12625, 12638, 12651, 12663.7, 12676.4, 12689.1, 12701.8, 12714.5,
                        12727.2, 12739.9, 12752.6, 12765.3, 12778, 12790.5, 12803, 12815.5,
                        12828, 12840.5, 12853, 12865.5, 12878, 12890.5, 12903, 12915.2,
                        12927.4, 12939.6, 12951.8, 12964, 12976.2, 12988.4, 13000.6, 13012.8,
                        13025, 13037.1, 13049.2, 13061.3, 13073.4, 13085.5, 13097.6, 13109.7,
                        13121.8, 13133.9, 13146, 13157.7, 13169.4, 13181.1, 13192.8, 13204.5,
                        13216.2, 13227.9, 13239.6, 13251.3, 13263, 13274.5, 13286, 13297.5,
                        13309, 13320.5, 13332, 13343.5, 13355, 13366.5, 13378, 13389.1,
                        13400.2, 13411.3, 13422.4, 13433.5, 13444.6, 13455.7, 13466.8, 13477.9,
                        13489, 13500, 13511, 13522, 13533, 13544, 13555, 13566, 13577, 13588,
                        13599, 13609.6, 13620.2, 13630.8, 13641.4, 13652, 13662.6, 13673.2,
                        13683.8, 13694.4, 13705, 13715.4, 13725.8, 13736.2, 13746.6, 13757,
                        13767.4, 13777.8, 13788.2, 13798.6, 13809, 13819.2, 13829.4, 13839.6,
                        13849.8, 13860, 13870.2, 13880.4, 13890.6, 13900.8, 13911, 13920.8,
                        13930.6, 13940.4, 13950.2, 13960, 13969.8, 13979.6, 13989.4, 13999.2,
                        14009, 14018.6, 14028.2, 14037.8, 14047.4, 14057, 14066.6, 14076.2,
                        14085.8, 14095.4, 14105, 14114.4, 14123.8, 14133.2, 14142.6, 14152,
                        14161.4, 14170.8, 14180.2, 14189.6, 14199, 14208, 14217, 14226, 14235,
                        14244, 14253, 14262, 14271, 14280, 14289
                    ]

                    Y = list(range(1000, -200 - 1, -1)) # Corrected range to include -200
                    # Finding the interpolation
                    y_interp = interp1d(X, Y)
                    y_interp_back = interp1d(Y, X)
                    
                    temp_cols = ['Tref_start', 'Theat_start','airT', 'Tref_end', 'Theat_end']
                    df45[temp_cols] = df45[temp_cols].clip(upper=1000)
                    df45[temp_cols] = df45[temp_cols].clip(lower=-200)
                    
                    
                    for col in temp_cols:
                        adc = y_interp_back(df45[col])
                        adc_c = (adc*43690.67)/df45['adc_bat[d.n.]']
                        
                        adc_c = adc_c.clip(upper=14289)
                        adc_c = adc_c.clip(lower=1453)

                        df45[col] = y_interp(adc_c)

                    df45[temp_cols] = df45[temp_cols]/10
                    
                    
                    #filtering for outliers values
                    max_Twood =  35
                    min_Twood = -19.9
                    
                    df45.loc[df45['Tref_start'] < min_Twood, 'Tref_start'] = np.nan
                    df45.loc[df45['Tref_start'] > max_Twood, 'Tref_start'] = np.nan
                    
                    df45.loc[df45['Theat_start'] < min_Twood, 'Theat_start'] = np.nan
                    df45.loc[df45['Theat_start'] > max_Twood, 'Theat_start'] = np.nan
                    
                    df45.loc[df45['Tref_end'] < min_Twood, 'Tref_end'] = np.nan
                    df45.loc[df45['Tref_end'] > max_Twood, 'Tref_end'] = np.nan
                    
                    df45.loc[df45['Theat_end'] < min_Twood, 'Theat_end'] = np.nan
                    df45.loc[df45['Theat_end'] > max_Twood, 'Theat_end'] = np.nan
                    
                
                    df45 = [x for _, x in df45.groupby('ID')]   
                              
                    for i in range(len(df45)):
                
                        # correct the timestamp 
                        # Check if each row is equal to the next row
                        mask = (df45[i] == df45[i].shift(1)).all(axis=1)
                        
                        # Keep only the first occurrence of equal rows
                        df45[i] = df45[i][~mask]
                        
                        
                        # Convert the 'DateTime' column to datetime type
                        df45[i]['date'] = pd.to_datetime(df45[i]['date'])
                        
                        # Sort the DataFrame by the 'DateTime' column from old to new
                        df45[i] = df45[i].sort_values('date')
                        
                
                
                        #  interpolation to find stem background temp based on the heater probe before heating data
                        try:
                        # Convert the 'Time' column to date type
                         df45[i]['date'] = pd.to_datetime(df45[i]['date'])
                        
                         # Set the 'Time' column as the DataFrame's index
                         df45[i].set_index('date', inplace=True)
                         
                         # Group the data by index and aggregate using a function (e.g., mean)
                         grouped_df = df45[i].groupby(pd.Grouper(freq='10T')).mean()
                        
                        
                        # Resample the grouped data to have a fixed frequency (e.g., every 10 minutes)
                         resampled_df45 = grouped_df.resample('10T').asfreq()
                        
                         # Perform linear interpolation between the numbers
                         interpolated_values = resampled_df45['Theat_start'].interpolate(method='linear')
                         # Replace the new number in place of the first number
                         df45[i]['Theat_start'].iloc[0] = interpolated_values.iloc[1]
                
                        except Exception as e:
                            print("Error occurred during resampling:", str(e))
                
                        # Continue with the rest of the code    
                        df45[i] = df45[i].reset_index()
                        #sap flow 
                    
                        # Heating phase/ using data from both heater and ref probes 
                        
                        #included the starting temperature difference 
                        df45[i]['dTon'] = ( df45[i]['Theat_end'])-( df45[i]['Tref_end']). round(2)
                        df45[i]['dToff'] =  ( df45[i]['Theat_start'])-( df45[i]['Tref_start']). round(2)
                        
                        
                        df45[i]['dT1'] = ( df45[i]['dTon'])-( df45[i]['dToff']). round(2)
                        df45[i]['date'] = pd.to_datetime( df45[i]['date'], format='%d-%b %H:%M')
                        
                        df45[i].loc[df45[i]['dT1'] < -10, 'dT1'] = np.nan
                        df45[i].loc[df45[i]['dT1'] > 10, 'dT1'] = np.nan
                        
                        #rolling 24H window method to calculate DTmax
                        df45[i] = df45[i].sort_values('date')
                        df45[i] = df45[i].set_index('date')           
                        # Calculate dTmax using a rolling window of 12 hours before and after
                        df45[i]['dTmax1'] = df45[i]['dT1'].rolling('24H', center=True).max()
                        df45[i] = df45[i].reset_index()
                        #'''
                        
                        df45[i]['K1_hr'] = (( df45[i]['dTmax1']- df45[i]['dT1'])/ df45[i]['dT1']). round(2)
  
                        # Heating phase/ using data from only heater probe    
                        df45[i]['dT2'] = ( df45[i]['Theat_end'])-( df45[i]['Theat_start']). round(2)
                        df45[i]['date'] = pd.to_datetime( df45[i]['date'], format='%d-%b %H:%M')
                        
                        #rolling 24H window method to calculate DTmax2
                        df45[i] = df45[i].sort_values('date')
                        df45[i] = df45[i].set_index('date')           
                        # Calculate dTmax using a rolling window of 12 hours before and after
                        df45[i]['dTmax2'] = df45[i]['dT2'].rolling('24H', center=True).max()
                        df45[i] = df45[i].reset_index()
                        
                        
                        df45[i]['K1_h'] = ((df45[i]['dTmax2']- df45[i]['dT2'])/ df45[i]['dT2']). round(2)

    

                        #sap flow density 
                        if data_freq == 'tree':
                                                       
                              # Apply equation for tree data
                              # Equation for tree data
                            if species == 'diffuse-porous':
                                  df45[i]['SFD1'] = 5.5750 * df45[i]['K1_h']
                                 
                                  df45[i]['SFD2'] = 5.5750 * df45[i]['K1_hr']

                            elif species == 'ring-porous':
                                  # for oak 2 cm
                                  df45[i]['SFD1'] = 10.0920 * df45[i]['K1_h']
                    
                                  df45[i]['SFD2'] = 10.0920 * df45[i]['K1_hr']
                                
                            elif species == 'ring-porous 1 cm':
                                  # for oak 1 cm
                                  df45[i]['SFD1'] = 15.09 * df45[i]['K1_h']
                                  df45[i]['SFD2'] = 15.09 * df45[i]['K1_hr']
                            
                            elif species == 'conifer':
                                  # for conifers 10/50
                                  df45[i]['SFD1'] = ((2.54 * df45[i]['K1_h'])/(1-df45[i]['K1_h'])) ** 1.44
                                  df45[i]['SFD2'] = ((2.54 * df45[i]['K1_hr'])/(1-df45[i]['K1_hr'])) ** 1.44

                            elif species == 'conifer 20/40':
                                  # for conifers 20/40
                                  df45[i]['SFD1'] = ((2.70 * df45[i]['K1_h'])/(1-df45[i]['K1_h'])) ** 1.23
                                  df45[i]['SFD2'] = ((2.70 * df45[i]['K1_hr'])/(1-df45[i]['K1_hr'])) ** 1.23

                            else:
                                  # for sawdust, FEM calibration coefficients
                                  #alpha = 67.99735
                                  alpha = 119                              
                                  #beta = 1.18245
                                  beta = 1.231
                                  df45[i]['SFD1'] = alpha * (df45[i]['K1_h']**beta)  # g/m^2/s
                                  df45[i]['SFD2'] = alpha * (df45[i]['K1_hr']**beta) # g/m^2/s
                            
                                   

                        df45[i].loc[df45[i]['SFD1'] < 0, 'SFD1'] = np.nan
                        df45[i].loc[df45[i]['SFD1'] > 60, 'SFD1']= np.nan
                        
                        df45[i].loc[df45[i]['SFD2'] < 0, 'SFD2'] = np.nan
                        df45[i].loc[df45[i]['SFD2'] > 60, 'SFD2']= np.nan
                        
                        
                        
                        
                        df45[i].set_index('date', inplace=True)

                        window_size = 2  # You can adjust the window size as needed

                        df45[i] = df45[i].reset_index()                                

                        '''
                        # VPD, vapour pressure deficit
                        df45[i]['ea']= 0.611*np.exp((17.27*(df45[i]['airT']))/((df45[i]['airT'])+237.3))
                        df45[i]['es'] =  df45[i]['ea']*(df45[i]['RH']/100)
                        df45[i]['VPD']= 	 df45[i]['ea'] -  df45[i]['es']
                        # df45[i].drop(df45[i].loc[df45[i]['VPD']>=6].index, inplace=True)
                        # df45[i].drop(df45[i].loc[df45[i]['VPD']<0].index, inplace=True)
                        '''

                        # tree stability oscillate angle
                        df45[i]['yaw']= np.degrees(np.arctan((np.sqrt(((df45[i]['x']. round(2).abs())**2)+((df45[i]['y']. round(2).abs())**2)))/(df45[i]['z']. round(2).abs())))
                        df45[i]['pitch'] = np.degrees(np.arctan((df45[i]['x']. round(2).abs())/(np.sqrt(((df45[i]['y']. round(2).abs())**2)+((df45[i]['z']. round(2).abs())**2)))))
                        df45[i]['roll'] = np.degrees(np.arctan((df45[i]['y']. round(2).abs())/(np.sqrt(((df45[i]['x']. round(2).abs())**2)+((df45[i]['z']. round(2).abs())**2)))))
                        
                        #air temperature conversion, and AirT / RH boundary values
                        max_Tair = 40
                        min_Tair = -30
                        max_RH = 100
                        min_RH = 0
                        
                        df45[i].loc[df45[i]['airT'] < min_Tair, 'airT'] = np.nan
                        df45[i].loc[df45[i]['airT'] > max_Tair, 'airT'] = np.nan
                        
                        df45[i].loc[df45[i]['RH'] < min_RH, 'RH'] = np.nan
                        df45[i].loc[df45[i]['RH'] > max_RH, 'RH'] = np.nan
                        # growth
                        # Define the range for valid values
                        lower_bound = 48000
                        upper_bound = 95000

                        # Replace out-of-range values with None
                        df45[i].loc[~df45[i]['Sharp sensor [d.n]'].between(lower_bound, upper_bound), 'Sharp sensor [d.n]'] = None
                        
                        df45[i]['Vbat'] = 650 + (131072*1100)/ df45[i]['adc_bat[d.n.]']

                        # Drop values in sharp d.n. where Vbat values are below 3500
                        
                        df45[i].loc[~df45[i]['Vbat'].between(1000, 5000), 'Vbat'] = np.nan 
                        
                        df45[i].loc[df45[i]['Vbat'] < 3500, 'Sharp sensor [d.n]'] = np.nan 
                        
                                       

                        df45[i]['mv'] = (df45[i]['Sharp sensor [d.n]'] / df45[i]['adc_bat[d.n.]'])*1100
                        
                        #interquartile filter for values
                        
                        df45[i]['dis'] =  ((24.8272) + (-26.9287) * df45[i]['mv'] / (342.88 + df45[i]['mv']))

                        #filtering final values of distances
                        min_dist = 1.5 # mm
                        max_dist = 5 # mm
                        
                        df45[i].loc[df45[i]['dis'] < min_dist, 'dis'] = np.nan
                        df45[i].loc[df45[i]['dis'] > max_dist, 'dis'] = np.nan
                        
                        Q1 = df45[i]['dis'].quantile(0.25)
                        Q3 = df45[i]['dis'].quantile(0.75)

                        IQR = Q3 - Q1
                    
                        lower_bound = Q1 - 2.5 * IQR
                        upper_bound = Q3 + 2.5 * IQR
                        

                        df45[i].loc[~df45[i]['dis'].between(lower_bound, upper_bound), 'dis'] = np.nan 
                        
                        #filtraggio interquartile con finestra
                        
                        df45[i]['dis'] =  (df45[i]['dis'].max() - df45[i]['dis']).rolling(window=72, center=True).median()

                        if data_freq == 'tree':

                            # if species == 'diffuse-porous':
                            #     # for beech
                            #     print('Choose "sawdust". Calibration for diffuse-porous is not available.')
                            #     # species = 'sawdust'  # Force species to "sawdust"
                            # elif species == 'ring-porous':
                            #     # for oak
                            #     print('Choose "sawdust". Calibration for ring-porous is not available.')
                            #     # species = 'sawdust'  # Force species to "sawdust"
                            # elif species == 'conifer':
                            #     # for oak
                            #     print('Choose "sawdust". Calibration for conifer is not available.')
                            #     # species = 'sawdust'  # Force species to "sawdust"

                            # else:
                                 # for sawdust
                            # slope = -99
                            # B1 = -7E-11
                            # B2 = 0.0002
                            # B0 = -90.254

                        # Replace the first 300 records in 'freq' with NA
                            df45[i]['freq'].iloc[:400] = np.nan
                            df45[i]['frequi'] = df45[i]['freq'].rolling(window=100, center=True).median()

                            # Setzen Sie den optionalen Smoothing-Faktor
                            # smoothing_factor = 0.15
                            # Define the range for valid values in reg analysis
                            # water Hz minimum acceptable freq for old version of TT
                            # lower_bound = 1200000
                            # #dry air
                            # upper_bound = 2600000
                            # 1. stem stauration index
                            # water Hz minimum acceptable freq for old version of TT

                            min_possible_ECF = 18000
                            # dri air
                            max_possible_ECf= 50000
                            df45[i]['frequi_0'] = np.where(df45[i]['frequi'] <  min_possible_ECF, np.nan, df45[i]['frequi'])
                            if not df45[i]['frequi_0'].isnull().all():
                                df45[i]['freq_n(Hz)']= np.where(df45[i]['frequi_0'] <= min_possible_ECF, np.nan,  df45[i]['frequi_0'])
                                # looking for temperature on staurated condition of stem
                                df45[i]['T_Sat']=  df45[i].loc[df45[i]['freq_n(Hz)'].idxmin(), 'Tref_start']
                                # df['ECFsat_Ti'] = (min(df['freq_n(Hz)'])) + ((T_Sat - df['Air temp (° C)'])*-74.15)
                                # mean of three slope for -6010,6666 = Mean(-76.27,-93.04,-111.44)*64
                                df45[i]['ECFsat_Ti']= (-74.15 * (df45[i]['Tref_start'] - df45[i]['T_Sat'])) + df45[i]['freq_n(Hz)'].min()
                                # Relative stem humidity index %
                                df45[i]['sat%'] =  (1-((df45[i]['freq_n(Hz)']-df45[i]['ECFsat_Ti'])/df45[i]['ECFsat_Ti']))*100
                            else:
                                df45[i]['sat%'] =  0
                            # # Replace out-of-range values with None
                            # df45[i].loc[~df45[i]['freq'].between(lower_bound, upper_bound), 'freq'] = None
                            # slope = -99
                            # df45[i]['freqi'] = df45[i]['freq'] - (slope * (df45[i]['Tref_start'] - 20))
                            # df45[i]['vwc'] = B1 * df45[i]['freqi']**2 + B2 * df45[i]['freqi'] + B0

                        # Continue with the rest of your code for tree data
                            print("Processing tree data...")

                        elif data_freq == 'soil':
                            # Apply equation for soil data
                            # water contet 3 MHz-loamy Azienda
                            # Define the range for valid values
                            lower_bound = 50000
                            upper_bound = 1800000
                            # Sample : S6	with density of 0.9708

                            m = -758
                            b = 154844
                            b1 = 7.09E-12
                            b2 = -1.78E-05
                            b3 = 17

                            # Replace out-of-range values with None
                            df45[i].loc[~df45[i]['freq'].between(lower_bound, upper_bound), 'freq'] = None
                            df45[i]['freqi'] = df45[i]['freq'] - ((m * (df45[i]['Tref_start'] - 20)))
                            df45[i]['vwc']=  -1.7915173e-17 *  df45[i]['freqi']**3 + 9.5651517e-11 * df45[i]['freqi']**2 + -0.000128698 * df45[i]['freqi'] + 50.44138201   # poly3 form
                            df45[i]['vwc1'] =  b1 * df45[i]['freqi']**2 + b2 * df45[i]['freqi'] + b3  # poly 2 from

                            # Continue with the rest of your code for soil data
                            print("Processing soil data...")


                        else:
                                # Handle the case when the frequency is neither 'soil' nor 'tree'
                            print("Invalid data frequency.")





                else:
                 # Print a message when 'b' is not present
                     print("There is no string type '4D' in the DataFrame column.")

                    # -------------------------------------------------------------------------------------------------




                try:
                    if 'df45' in locals() and df45:  # Check if `df45` is defined and not empty
                        df45= pd.concat(df45)
                        #df45.rename(columns={'smoothed_SFD2': 'SFD-Heating phase'}, inplace=True)
                        
                        #df45 = df45.set_index('date')

                        #col= ['Vbat', 'airT', 'RH', 'freq', 'sat%', 'Tref_start','Theat_end','SFD1','SFD2','smoothed_SFD1', 'smoothed_SFD2', 'dis', 'dis_old','yaw','pitch','roll']
                        col= ['Vbat', 'airT', 'RH', 'dT1','dTmax1','dT2','dTmax2','SFD1','SFD2','dis','yaw','pitch','roll']

                        # Define a dictionary for units if available
                        units= {'Vbat': 'Battery voltage (mV)', 'airT': 'Air Temperature (°C)', 'RH': 'relative humidity (%)', 'dT1': 'Temp difference using both reference and heater (°C)', 'dTmax1': 'max value of DT1 over a 24 hour window (°C)', 'dT2': 'Temp difference using heater only (°C)', 'dTmax2': 'max value of DT2 over a 24 hour window (°C)', 'SFD1': 'Sap flux density_TDM (g*m-2*s-1)', 'SFD2': 'Sap flux density_TDM using only heater (g*m-2*s-1)', 'dis': 'growth sensor distance from bark (mm)', 'yaw': 'stability-Z (°)', 'pitch': 'stability-Y (°)', 'roll': 'stability-X (°)'}

                        for i in col:
                            fig = px.line(df45, x = df45['date'], y =[i], color='ID')  # Assuming 'ID' is a column in your DataFrame

                            # Set the y-axis title with units if defined
                            y_axis_title = f"{i} ({units.get(i, 'no unit')})"  # 'no unit' will be used if the unit is not defined in the units dictionary
                            fig.update_layout(yaxis_title=y_axis_title)

                            
                            if values['plot_option'] == 'Store and visualize':
                                plotly.offline.plot(fig, filename=str(output_directory / (i+'_45.html')))
                                
                            else:
                                plotly.offline.plot(fig, filename= str(output_directory / (i+'_45.html')), auto_open=False)
                                
                        
                        df45 = df45[['ID', 'device type', 'date', 'Vbat', 'airT', 'dT1', 'dTmax1', 'dT1', 'dTmax2', 'SFD1', 'SFD2', 'dis', 'yaw', 'pitch', 'roll']]


                        # Save the DataFrame as a CSV file
                        df45.to_csv(output_directory / 'df45.csv', index=False)

                    else:
                        print("No objects to concatenate. Skipping concatenation.")

                except ValueError as e:
                    # Handle the error or skip the concatenation step
                    print("Error occurred during concatenation:", str(e))







# _________________CALLING DIFF DVICE TYPE______________________________________________________________________________________________
                # --------------------------4D--------------------------------------
                # ----------------------------------------------------------------
                # THIS FILE WILL RUN FOR DATA TYPE 4D, TT+3.2 VERSION

                if '4D' in dfall[3].values:
                        # Filter the DataFrame to include only rows with 'b' in 'column_name'
                    df4D = dfall[dfall[3] == '4D'].copy()
                    
                    df4D = df4D.replace('', pd.NA)
                    df4D = df4D.dropna(how='all', axis=1)
                    df4D = df4D.reset_index(drop=True)

                    # adding column's headers
                    df4D.columns = ['ID', 'record_number', 'device type', 'timestamp', 'T_ref_start', 'T_heat_start', 'Sharp sensor [d.n]',
                                    'adc_bandgap [d.n.]', 'No_of_bits', 'RH', 'airT', 'x','g_z(std.dev) [d.n.]','y','g_y (std.dev) [d.n.]','z','g_x (std.dev) [d.n.]',
                                    'T_ref_end', 'T_heat_end', 'freq', 'adc_Vbat [d.n.]']
                    
                    df4D = df4D.apply(pd.to_numeric, errors='ignore')

                    df4D['ID'] = df4D['ID'].astype(str)
                    # df4D['TT ID'] = df4D['TT ID'].str[-2:]

                    # Convert timestamp column to datetime objects
                    # df4D['datetime'] = pd.to_datetime(df4D['timestamp'], unit='s')

                    # # # # dropping wrong timstamps from dataset or selecting the period of measurment
                    # df4D.drop(df4D.loc[df4D['timestamp']<=1586976604].index, inplace=True)
                    # df4D.drop(df4D.loc[df4D['timestamp']>=2102787804].index, inplace=True)
                    # Convert timestamp column to datetime objects
                    df4D['date'] = pd.to_datetime(df4D['timestamp'], unit='s').dt.tz_localize(
                        'UTC').dt.tz_convert(timezone).dt.tz_localize(None)
                    # Filter and keep rows within the date range
                    df4D = df4D[(df4D['date'] >= start_date)
                                 & (df4D['date'] <= end_date)]

                    # df4D['season'] = df4D.apply(lambda x: seasons(x['date']), axis=1)  # Day of Year
                    df4D['DOY'] = df4D['date'].dt.dayofyear
                    df4D['year'] = df4D['date'].dt.year
                    df4D['month'] = df4D['date'].dt.month
                    df4D['day'] = df4D['date'].dt.day
                    df4D['hour'] = df4D['date'].dt.hour

                     # calculating VBat in mV
                    df4D['Vbat'] = 2* 1100 * (df4D['adc_Vbat [d.n.]']/df4D['adc_bandgap [d.n.]'])	
                                    
                
                    		
                    df4D = df4D.reset_index(drop=True, inplace=False)
                
                    
                
                
                    #************************ Applying lookup table for sap flow temeparure conversion ***************
                    # Python3 code
                    # Implementation of Linear Interpolation using Python3 code
                    # Importing library
                    from scipy.interpolate import interp1d
                    
                    X = [57159,56799,56423,56039,55647,55239,54822,54398,53958,53514,53054,52585,52101,51612,51112,50604,50084,49557,49021,48478,47927,47370,46806,46233,45653,45069,44477,43882,43282,42679,42068,41455,40839,40219,39599,38975,38351,37727,37103,36479,35856,35235,34614,33997,33380,32768,32156,31548,30944,30344,29753,29161,28581,28002,27430,26867,26310,25758,25214,24674,24146,23622,23106,22598,22094,21602,21117,20637,20168,19708,19256,18812,18372,17944,17524,17116,16712,16316,15928,15548,15177,14821,14469,14125,13793,13465,13145,12834,12530,12231,11940,11655,11375,11103,10839,10579,10323,10079,9836,9604,9373,9152,8931,8718,8509,8309,8113,7921,7733,7553,7374,7202,7030,6866,6702,6547,6391,6243,6099,5955,5816] 
                    Y = list(range(-20,101))
                    # Finding the interpolation
                    y_interp = interp1d(X, Y)
                     
                    
                    df4D[['T_ref_start','T_heat_start', 'T_ref_end','T_heat_end']] = df4D[['T_ref_start','T_heat_start', 'T_ref_end','T_heat_end']].clip(upper=57159)
                    df4D[['T_ref_start','T_heat_start', 'T_ref_end','T_heat_end']] = df4D[['T_ref_start','T_heat_start', 'T_ref_end','T_heat_end']].clip(lower=5816)
                    
                    
                    # heating phase
                    df4D['Tref_start']=  y_interp(df4D['T_ref_start'])  
                    df4D['Theat_start']=  y_interp(df4D['T_heat_start'])  
                    df4D['Tref_end']=  y_interp(df4D['T_ref_end'])  
                    df4D['Theat_end']=  y_interp(df4D['T_heat_end'])  
                    
                    #filtering for outliers values
                    max_Twood =  45
                    min_Twood = -19.9
                    
                    df4D.loc[df4D['Tref_start'] < min_Twood, 'Tref_start'] = np.nan
                    df4D.loc[df4D['Tref_start'] > max_Twood, 'Tref_start'] = np.nan
                    
                    df4D.loc[df4D['Theat_start'] < min_Twood, 'Theat_start'] = np.nan
                    df4D.loc[df4D['Theat_start'] > max_Twood, 'Theat_start'] = np.nan
                    
                    df4D.loc[df4D['Tref_end'] < min_Twood, 'Tref_end'] = np.nan
                    df4D.loc[df4D['Tref_end'] > max_Twood, 'Tref_end'] = np.nan
                    
                    df4D.loc[df4D['Theat_end'] < min_Twood, 'Theat_end'] = np.nan
                    df4D.loc[df4D['Theat_end'] > max_Twood, 'Theat_end'] = np.nan
                    

                    
                    df4D = [x for _, x in df4D.groupby('ID')]
                    
                
                    
                    
                    
                    for i in range(len(df4D)):
                
                        # correct the timestamp 
                        # Check if each row is equal to the next row
                        mask = (df4D[i] == df4D[i].shift(1)).all(axis=1)
                        
                        # Keep only the first occurrence of equal rows
                        df4D[i] = df4D[i][~mask]
                        
                        
                        # Convert the 'DateTime' column to datetime type
                        df4D[i]['date'] = pd.to_datetime(df4D[i]['date'])
                        
                        # Sort the DataFrame by the 'DateTime' column from old to new
                        df4D[i] = df4D[i].sort_values('date')
                        
                
                        
                        #  interpolation to find stem background temp based on the heater probe before heating data
                        try:
                            # Convert the 'Time' column to date type
                             df4D[i]['date'] = pd.to_datetime(df4D[i]['date'])
                            
                             # Set the 'Time' column as the DataFrame's index
                             df4D[i].set_index('date', inplace=True)
                             
                             # Group the data by index and aggregate using a function (e.g., mean)
                             grouped_df = df4D[i].groupby(pd.Grouper(freq='10T')).mean()
                            
                            
                            # Resample the grouped data to have a fixed frequency (e.g., every 10 minutes)
                             resampled_df4D = grouped_df.resample('10T').asfreq()
                            
                             # Perform linear interpolation between the numbers
                             interpolated_values = resampled_df4D['Theat_start'].interpolate(method='linear')
                             # Replace the new number in place of the first number
                             df4D[i]['Theat_start'].iloc[0] = interpolated_values.iloc[1]
                
                        except Exception as e:
                            print("Error occurred during resampling:", str(e))
                        
                        
                        
                        # Continue with the rest of the code    
                        df4D[i] = df4D[i].reset_index()
                        #sap flow 
                    
                        # Heating phase/ using data from both heater and ref probes 
                        
                        #included the starting temperature difference 
                        df4D[i]['dTon'] = ( df4D[i]['Theat_end'])-( df4D[i]['Tref_end']). round(2)
                        df4D[i]['dToff'] =  ( df4D[i]['Theat_start'])-( df4D[i]['Tref_start']). round(2)
                        
                        
                        df4D[i]['dT1'] = ( df4D[i]['dTon'])-( df4D[i]['dToff']). round(2)
                        df4D[i]['date'] = pd.to_datetime( df4D[i]['date'], format='%d-%b %H:%M')
                        
                        df4D[i].loc[df4D[i]['dT1'] < -10, 'dT1'] = np.nan
                        df4D[i].loc[df4D[i]['dT1'] > 10, 'dT1'] = np.nan
                        
                        #daily method to calculate the DTmax
                        #df4D[i]['dTmax1'] =  df4D[i].groupby( df4D[i]['date'].dt.date)['dT1'].transform('max')
                        
                        #'''
                        #rolling 24H window method to calculate DTmax
                        df4D[i] = df4D[i].sort_values('date')
                        df4D[i] = df4D[i].set_index('date')           
                        # Calculate dTmax using a rolling window of 12 hours before and after
                        df4D[i]['dTmax1'] = df4D[i]['dT1'].rolling('24H', center=True).max()
                        df4D[i] = df4D[i].reset_index()
                        #'''
                        
                        df4D[i]['K1_hr'] = (( df4D[i]['dTmax1']- df4D[i]['dT1'])/ df4D[i]['dT1']). round(2)
  
                        # Heating phase/ using data from only heater probe    
                        df4D[i]['dT2'] = ( df4D[i]['Theat_end'])-( df4D[i]['Theat_start']). round(2)
                        df4D[i]['date'] = pd.to_datetime( df4D[i]['date'], format='%d-%b %H:%M')
                        
                        #df4D[i]['dTmax2'] =  df4D[i].groupby( df4D[i]['date'].dt.date)['dT2'].transform('max')
                        
                        
                        #rolling 24H window method to calculate DTmax
                        df4D[i] = df4D[i].sort_values('date')
                        df4D[i] = df4D[i].set_index('date')           
                        # Calculate dTmax using a rolling window of 12 hours before and after
                        df4D[i]['dTmax2'] = df4D[i]['dT2'].rolling('24H', center=True).max()
                        df4D[i] = df4D[i].reset_index()
                        
                        
                        df4D[i]['K1_h'] = ((df4D[i]['dTmax2']- df4D[i]['dT2'])/ df4D[i]['dT2']). round(2)

    

                        #sap flow density 
                        if data_freq == 'tree':
                                                       
                              # Apply equation for tree data
                              # Equation for tree data
                            if species == 'diffuse-porous':
                                  df4D[i]['SFD1'] = 5.5750 * df4D[i]['K1_h']
                                 
                                  df4D[i]['SFD2'] = 5.5750 * df4D[i]['K1_hr']

                            elif species == 'ring-porous':
                                  # for oak 2 cm
                                  df4D[i]['SFD1'] = 10.0920 * df4D[i]['K1_h']
                    
                                  df4D[i]['SFD2'] = 10.0920 * df4D[i]['K1_hr']
                                
                            elif species == 'ring-porous 1 cm':
                                  # for oak 1 cm
                                  df4D[i]['SFD1'] = 15.09 * df4D[i]['K1_h']
                                  df4D[i]['SFD2'] = 15.09 * df4D[i]['K1_hr']
                            
                            elif species == 'conifer':
                                  # for conifers 10/50
                                  df4D[i]['SFD1'] = ((2.54 * df4D[i]['K1_h'])/(1-df4D[i]['K1_h'])) ** 1.44
                                  df4D[i]['SFD2'] = ((2.54 * df4D[i]['K1_hr'])/(1-df4D[i]['K1_hr'])) ** 1.44

                            elif species == 'conifer 20/40':
                                  # for conifers 20/40
                                  df4D[i]['SFD1'] = ((2.70 * df4D[i]['K1_h'])/(1-df4D[i]['K1_h'])) ** 1.23
                                  df4D[i]['SFD2'] = ((2.70 * df4D[i]['K1_hr'])/(1-df4D[i]['K1_hr'])) ** 1.23

                            else:
                                  # Calibration coefficients derived from original 1985 Granier parametrization
                                  
                                  alpha = 118.9                          
                                  
                                  beta = 1.231
                                  df4D[i]['SFD1'] = alpha * (df4D[i]['K1_h']**beta)  # g/m^2/s
                                  df4D[i]['SFD2'] = alpha * (df4D[i]['K1_hr']**beta) # g/m^2/s
                            
                                   

                        df4D[i].loc[df4D[i]['SFD1'] < 0, 'SFD1'] = np.nan
                        df4D[i].loc[df4D[i]['SFD1'] > 60, 'SFD1']= np.nan
                        
                        df4D[i].loc[df4D[i]['SFD2'] < 0, 'SFD2'] = np.nan
                        df4D[i].loc[df4D[i]['SFD2'] > 60, 'SFD2']= np.nan
                        
                        
                        
                        
                        df4D[i].set_index('date', inplace=True)

                        window_size = 2  # You can adjust the window size as needed

                        df4D[i] = df4D[i].reset_index()                                

                        # tree stability oscillate angle
                        df4D[i]['yaw']= np.degrees(np.arctan((np.sqrt(((df4D[i]['x']. round(2).abs())**2)+((df4D[i]['y']. round(2).abs())**2)))/(df4D[i]['z']. round(2).abs())))
                        df4D[i]['pitch'] = np.degrees(np.arctan((df4D[i]['x']. round(2).abs())/(np.sqrt(((df4D[i]['y']. round(2).abs())**2)+((df4D[i]['z']. round(2).abs())**2)))))
                        df4D[i]['roll'] = np.degrees(np.arctan((df4D[i]['y']. round(2).abs())/(np.sqrt(((df4D[i]['x']. round(2).abs())**2)+((df4D[i]['z']. round(2).abs())**2)))))
                        
                        #air temperature conversion, and AirT / RH boundary values
                        max_Tair = 40
                        min_Tair = -30
                        max_RH = 100
                        min_RH = 0
                        
                        df4D[i]['airT'] = df4D[i]['airT']/10
                        
                        df4D[i].loc[df4D[i]['airT'] < min_Tair, 'airT'] = np.nan
                        df4D[i].loc[df4D[i]['airT'] > max_Tair, 'airT'] = np.nan
                        
                        df4D[i].loc[df4D[i]['RH'] < min_RH, 'RH'] = np.nan
                        df4D[i].loc[df4D[i]['RH'] > max_RH, 'RH'] = np.nan
                        # growth
                        # Define the range for valid values
                        lower_bound = 48000
                        upper_bound = 95000

                        # Replace out-of-range values with None
                        df4D[i].loc[~df4D[i]['Sharp sensor [d.n]'].between(lower_bound, upper_bound), 'Sharp sensor [d.n]'] = None
                        # Drop values in sharp d.n. where Vbat values are below 3600
                        
                        df4D[i].loc[~df4D[i]['Vbat'].between(1000, 5000), 'Vbat'] = np.nan 
                        
                        
                        df4D[i].loc[df4D[i]['Vbat'] < 3500, 'Sharp sensor [d.n]'] = None
                     

                        df4D[i]['mv'] = df4D[i]['Sharp sensor [d.n]'] * 3300 / 2**17
                        
                        #interquartile filter for values
                        
                        a = 152.6354509157652
                        b = -0.0010336651238710699
                        
                        
                        df4D[i]['dis'] =  ((24.8272) + (-26.9287) * df4D[i]['mv'] / (342.88 + df4D[i]['mv']))
                        # df4D[i]['smoothed_dis'] = df4D[i]['dis'].rolling(window=10, center=True).mean()
                        
                        #filtering final values of distances
                        min_dist = 1.5 # mm
                        max_dist = 5 # mm
                        
                        df4D[i].loc[df4D[i]['dis'] < min_dist, 'dis'] = np.nan
                        df4D[i].loc[df4D[i]['dis'] > max_dist, 'dis'] = np.nan
                        
                        Q1 = df4D[i]['dis'].quantile(0.25)
                        Q3 = df4D[i]['dis'].quantile(0.75)

                        IQR = Q3 - Q1
                    
                        lower_bound = Q1 - 2.5 * IQR
                        upper_bound = Q3 + 2.5 * IQR
                        

                        df4D[i].loc[~df4D[i]['dis'].between(lower_bound, upper_bound), 'dis'] = np.nan 
                        
                        #filtraggio interquartile con finestra
                        
                        df4D[i]['dis'] =  (df4D[i]['dis'].max() - df4D[i]['dis']).rolling(window=72, center=True).median()
                        if data_freq == 'tree':

                        # Replace the first 300 records in 'freq' with NA
                            df4D[i]['freq'].iloc[:400] = np.nan
                            df4D[i]['frequi'] = df4D[i]['freq'].rolling(window=100, center=True).median()

                            # Setzen Sie den optionalen Smoothing-Faktor
                            # smoothing_factor = 0.15
                            # Define the range for valid values in reg analysis
                            # water Hz minimum acceptable freq for old version of TT
                            # lower_bound = 1200000
                            # #dry air
                            # upper_bound = 2600000
                            # 1. stem stauration index
                            # water Hz minimum acceptable freq for old version of TT

                            min_possible_ECF = 18000
                            # dri air
                            max_possible_ECf= 50000
                            df4D[i]['frequi_0'] = np.where(df4D[i]['frequi'] <  min_possible_ECF, np.nan, df4D[i]['frequi'])
                            if not df4D[i]['frequi_0'].isnull().all():
                                df4D[i]['freq_n(Hz)']= np.where(df4D[i]['frequi_0'] <= min_possible_ECF, np.nan,  df4D[i]['frequi_0'])
                                # looking for temperature on staurated condition of stem
                                df4D[i]['T_Sat']=  df4D[i].loc[df4D[i]['freq_n(Hz)'].idxmin(), 'Tref_start']
                                # df['ECFsat_Ti'] = (min(df['freq_n(Hz)'])) + ((T_Sat - df['Air temp (° C)'])*-74.15)
                                # mean of three slope for -6010,6666 = Mean(-76.27,-93.04,-111.44)*64
                                df4D[i]['ECFsat_Ti']= (-74.15 * (df4D[i]['Tref_start'] - df4D[i]['T_Sat'])) + df4D[i]['freq_n(Hz)'].min()
                                # Relative stem humidity index %
                                df4D[i]['sat%'] =  (1-((df4D[i]['freq_n(Hz)']-df4D[i]['ECFsat_Ti'])/df4D[i]['ECFsat_Ti']))*100
                            else:
                                df4D[i]['sat%'] =  0
                            # # Replace out-of-range values with None
                            # df4D[i].loc[~df4D[i]['freq'].between(lower_bound, upper_bound), 'freq'] = None
                            # slope = -99
                            # df4D[i]['freqi'] = df4D[i]['freq'] - (slope * (df4D[i]['Tref_start'] - 20))
                            # df4D[i]['vwc'] = B1 * df4D[i]['freqi']**2 + B2 * df4D[i]['freqi'] + B0

                        # Continue with the rest of your code for tree data
                            print("Processing tree data...")

                        elif data_freq == 'soil':
                            # Apply equation for soil data
                            # water contet 3 MHz-loamy Azienda
                            # Define the range for valid values
                            lower_bound = 50000
                            upper_bound = 1800000
                            # Sample : S6	with density of 0.9708

                            m = -758
                            b = 154844
                            b1 = 7.09E-12
                            b2 = -1.78E-05
                            b3 = 17

                            # Replace out-of-range values with None
                            df4D[i].loc[~df4D[i]['freq'].between(lower_bound, upper_bound), 'freq'] = None
                            df4D[i]['freqi'] = df4D[i]['freq'] - ((m * (df4D[i]['Tref_start'] - 20)))
                            df4D[i]['vwc']=  -1.7915173e-17 *  df4D[i]['freqi']**3 + 9.5651517e-11 * df4D[i]['freqi']**2 + -0.000128698 * df4D[i]['freqi'] + 50.44138201   # poly3 form
                            df4D[i]['vwc1'] =  b1 * df4D[i]['freqi']**2 + b2 * df4D[i]['freqi'] + b3  # poly 2 from

                            # Continue with the rest of your code for soil data
                            print("Processing soil data...")


                        else:
                                # Handle the case when the frequency is neither 'soil' nor 'tree'
                            print("Invalid data frequency.")

                else:
                 # Print a message when 'b' is not present
                     print("There is no string type '4D' in the DataFrame column.")

                    # -------------------------------------------------------------------------------------------------

                try:
                    if 'df4D' in locals() and df4D:  # Check if `df4D` is defined and not empty
                        df4D= pd.concat(df4D)
                        #df4D.rename(columns={'smoothed_SFD2': 'SFD-Heating phase'}, inplace=True)
                        df4D = df4D.set_index('date')

                        # col= ['Vbat', 'airT', 'RH', 'VPD', 'freq', 'sat%', 'Tref_start','Theat_end', 'SFD1','smoothed_SFD1','SFD2', 'smoothed_SFD2', 'SFD3', 'dis','yaw','pitch','roll']
                        col= ['Vbat', 'airT', 'RH', 'dT1','dTmax1','dT2','dTmax2','SFD1','SFD2','dis','yaw','pitch','roll']

                        # Define a dictionary for units if available
                        units= {'Vbat': 'Battery voltage (mV)', 'airT': 'Air Temperature (°C)', 'RH': 'relative humidity (%)', 'dT1': 'Temp difference using both reference and heater (°C)', 'dTmax1': 'max value of DT1 over a 24 hour window (°C)', 'dT2': 'Temp difference using heater only (°C)', 'dTmax2': 'max value of DT2 over a 24 hour window (°C)', 'SFD1': 'Sap flux density_TDM (g*m-2*s-1)', 'SFD2': 'Sap flux density_TDM using only heater (g*m-2*s-1)', 'dis': 'growth sensor distance from bark (mm)', 'yaw': 'stability-Z (°)', 'pitch': 'stability-Y (°)', 'roll': 'stability-X (°)'}

                        for i in col:
                            fig = px.line(df4D, x = df4D.index, y =[i], color='ID')  # Assuming 'ID' is a column in your DataFrame

                            # Set the y-axis title with units if defined
                            y_axis_title = f"{i} ({units.get(i, 'no unit')})"  # 'no unit' will be used if the unit is not defined in the units dictionary
                            fig.update_layout(yaxis_title=y_axis_title)

                            if values['plot_option'] == 'Store and visualize':
                                plotly.offline.plot(fig, filename=str(output_directory / (i+'_4D.html')))
                                
                            else:
                                plotly.offline.plot(fig, filename= str(output_directory / (i+'_4D.html')), auto_open=False)




                        # for i in col:
                        #     fig = px.line(df4D, x = df4D.index, y =[i],color='ID')  #,color='TT ID'
                        #     # show figure
                        #     if values['plot_option'] == 'Store Plots':
                        #         plotly.offline.plot(fig, filename=i + 'TT+3.4.html')  # Save the plot as HTML file
                        #         fig.show()  # Show the plot

                        df4D = df4D.reset_index()

                        # df4D = df4D[['ID', 'device type', 'date', 'DOY', 'month', 'year', 'Vbat', 'airT', 'RH', 'VPD', 'Tref_start', 'Tref_end', 'Theat_start', 'Theat_end', 'dT1', 'dTmax1', 'K1_hr', 'SFD1', 'smoothed_SFD1' ,'dT2', 'dTmax2', 'K1_h', 'SFD2',  'smoothed_SFD2','I','K3', 'SFD3','freq', 'sat%', 'dis','yaw','pitch','roll']]
                        df4D = df4D[['ID', 'device type', 'date', 'Vbat', 'airT', 'RH', 'dT1', 'dTmax1', 'dT2', 'dTmax2', 'SFD1', 'SFD2', 'dis', 'yaw', 'pitch', 'roll']]
                        df4D = df4D.reset_index()


                        # Save the DataFrame as a CSV file
                        df4D.to_csv(output_directory / 'df4D.csv', index=True)

                    else:
                        print("No objects to concatenate. Skipping concatenation.")

                except ValueError as e:
                    # Handle the error or skip the concatenation step
                    print("Error occurred during concatenation:", str(e))

#______________________________CALLING DIFF DVICE TYPE______________________________________________________________________________________________
                #----------------------------------------------------------------
                #----------------------------------------------------------------
                
                
                #------------------------------------------------------------------------------
                #------------------ String 49-------------------------------- '''
                
                
                def spectrometer_610 (value):
                    
                    # result = -312.45+(1.6699*value)
                    result = (value)/989.1 #calibrazione a gain 2 (1: 3.4)
                    return  round(result,2)
                
                def spectrometer_680 (value):
                    
                    # result = -561.56+(1.5199*value)
                    result = (value)/957.1
                    return  round(result,2)
                
                def spectrometer_730 (value):
                    
                    # result = -1511.2+(1.6209*value)
                    result = (value)/943.2
                    return  round(result,2)
                
                def spectrometer_760 (value):
                    
                    # result = -1012.5+(1.4549*value)
                    result = (value)/915.2
                    return  round(result,2)
                
                def spectrometer_810 (value):
                    
                    # result = 91.58+(0.8414*value)
                    result = (value)/1000.9
                    return  round(result,2)
                
                def spectrometer_860 (value):
                    
                    # result = 334.88+(0.531*value)
                    result = (value)/994.3
                    return  round(result,2)
                
                def spectrometer_450 (value):
                    
                    # result = -212.62+(0.4562*value) 
                    result = (value)/2214.6
                    return  round(result,2)
                
                def spectrometer_500 (value):
                    
                    # result = -232.13+(0.6257 *value)
                    result = (value)/2002.7
                    return  round(result,2)
                
                def spectrometer_550 (value):
                    
                    # result = -842.1+(1.0546 *value)
                    result = (value)/1715.4
                    return  round(result,2)
                
                def spectrometer_570 (value):
                    
                    # result = -666.72+(1.0462 *value)
                    result = (value)/1690.9
                    return  round(result,2)
                
                def spectrometer_600 (value):
                    
                    # result = -328.08+(0.8654 *value)
                    result = (value)/1605.8
                    return  round(result,2)
                
                def spectrometer_650 (value):
                    
                    # result = 202.77+(0.7829*value)
                    result = (value)/1542.6
                    return  round(result,2)
                
                
           
                # #_________________CALLING DIFF DVICE TYPE______________________________________________________________________________________________
                # #--------------------------49--------------------------------------
                
                
                if '49' in dfall[3].values:
                        # Filter the DataFrame to include only rows with 'b' in 'column_name'
                    df49 = dfall[dfall[3] == '49'].copy()
                  
                    df49 = df49.replace('', pd.NA)
                    df49 = df49.dropna(how='all', axis=1)
                    df49 = df49.reset_index(drop=True)
                
                    # giving headers 
                    df49.columns = ['ID','record_number','device type','timestamp', 'AS7263_610 [d.n.]',	'AS7263_680 [d.n.]',	'AS7263_730 [d.n.]',	'AS7263_760 [d.n.]',	'AS7263_810 [d.n.]',	'AS7263_860 [d.n.]',	'AS7262_450 [d.n.]',	'AS7262_500 [d.n.]',	'AS7262_550 [d.n.]',	'AS7262_570 [d.n.]',	'AS7262_600 [d.n.]',	'AS7262_650 [d.n.]',	'integration time',	'gain']
                    
                    # conversting data type to numerice 
                    df49 = df49.apply(pd.to_numeric, errors='coerce')		
                    
                    # resetting the index number
                    df49 = df49.reset_index(drop=True, inplace=False)
                    
                    # dropping wrong timstamps from dataset 
                    
                
                    # df49.drop(df49.loc[df49['timestamp']<=1500000000].index, inplace=True)
                    # df49.drop(df49.loc[df49['timestamp']>=2108444440].index, inplace=True)
                    
                    #converting timestamp to real datetime 
                    df49['date'] = pd.to_datetime(df49['timestamp'],unit='s').dt.tz_localize('UTC').dt.tz_convert(timezone).dt.tz_localize(None)
                    
                    # Filter and keep rows within the date range
                    df49 = df49[(df49['date'] >= start_date) & (df49['date'] <= end_date)]
                    
                
                
                    
                    
                    df49[['ID']]= df49[['ID']].astype(str) # Converting TT ID to string type data because pd.numeric chnages the dfall data to int  
                    
                    
                    devices49 = df49['ID'].unique()
                    
                    # splitting dataframe to single df for each TT data 
                    
                    df49 = [x for _, x in df49.groupby('ID')]
                    
                    # for i in range(len(df49)):
                    #     exec(f'df49{i} = df49[i].reset_index(drop=True)')
                    
                    
                    for i in range(len(df49)):
                        
                        
                        
                        df49[i].reset_index(drop=True, inplace=False)
                        
                        # correct the timestamp 
                        # Check if each row is equal to the next row
                        mask = (df49[i] == df49[i].shift(1)).all(axis=1)
                        
                        # Keep only the first occurrence of equal rows
                        df49[i] = df49[i][~mask]
                        
                        
                        # Convert the 'DateTime' column to datetime type
                        df49[i]['date'] = pd.to_datetime(df49[i]['date'])
                        
                        # Sort the DataFrame by the 'DateTime' column from old to new
                        df49[i] = df49[i].sort_values('date')
                        
                        
                        
                        
                    # drop outlier
                        # alldf49[i].drop( alldf49[i].loc[ alldf49[i]['sfd2']>5].index, inplace=True) 
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_450 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_450 [d.n.]']< 0].index, inplace=True)
                        # df49[i].loc[~(( df49[i]['AS7262_450 [d.n.]']<0) | ( df49[i]['AS7262_450 [d.n.]']>40000))]
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_500 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_500 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_550 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_550 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_570 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_570 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_600 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_600 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_650 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7262_650 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_610 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_610 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_680 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_680 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_730 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_730 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_760 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_760 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_810 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_810 [d.n.]']< 0].index, inplace=True)
                    
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_860 [d.n.]']> 65000].index, inplace=True)
                        df49[i].drop(df49[i].loc[df49[i]['AS7263_860 [d.n.]']< 0].index, inplace=True)
                    
                        # savgol_filter(df4D['Tref_start'], 7, 3, mode='nearest')
                        
                       #calibration fromula, since gain is 3 devide by 4 and also divide by mean coef to convert digital numbers to energy watt pr cm2  
                        
                        df49[i]['VISBL_450'] = (spectrometer_450(df49[i]['AS7262_450 [d.n.]'])).rolling(3).median()
                        df49[i]['VISBL_500'] = (spectrometer_500(df49[i]['AS7262_500 [d.n.]'])).rolling(3).median()
                        df49[i]['VISBL_550'] = (spectrometer_550(df49[i]['AS7262_550 [d.n.]'])).rolling(3).median()
                        df49[i]['VISBL_570'] = (spectrometer_570(df49[i]['AS7262_570 [d.n.]'])).rolling(3).median()
                        df49[i]['VISBL_600'] = (spectrometer_600(df49[i]['AS7262_600 [d.n.]'])).rolling(3).median()
                        df49[i]['VISBL_650'] = (spectrometer_650(df49[i]['AS7262_650 [d.n.]'])).rolling(3).median()
                        df49[i]['NIR_610'] = (spectrometer_610(df49[i]['AS7263_610 [d.n.]'])).rolling(3).median()
                        df49[i]['NIR_680'] = (spectrometer_680(df49[i]['AS7263_680 [d.n.]'])).rolling(3).median()
                        df49[i]['NIR_730'] = (spectrometer_730(df49[i]['AS7263_730 [d.n.]'])).rolling(3).median()
                        df49[i]['NIR_760'] = (spectrometer_760(df49[i]['AS7263_760 [d.n.]'])).rolling(3).median()
                        df49[i]['NIR_810'] = (spectrometer_810(df49[i]['AS7263_810 [d.n.]'])).rolling(3).median()
                        df49[i]['NIR_860'] = (spectrometer_860(df49[i]['AS7263_860 [d.n.]'])).rolling(3).median()
                        
                    
                        # we are looking for time window to avoid direct sunlight, 30 degrees 
                        # nocturnal and diurnal data for sapflow & VPD
                        df49[i] = df49[i][['date','ID','device type', 'NIR_610','NIR_680','NIR_730','NIR_760', 'NIR_810','NIR_860','VISBL_450', 'VISBL_500', 'VISBL_550', 'VISBL_570', 'VISBL_600', 'VISBL_650' ]]
                        # df49[i] = df49[i].set_index('date', inplace = True)
                        df49[i] = df49[i].set_index(df49[i]['date']).between_time('7:00','9:30')
                    	
                      
                       
                        df49[i]['year'] = df49[i]['date'].dt.year
                        df49[i]['month'] = df49[i]['date'].dt.month
                        df49[i]['day'] = df49[i]['date'].dt.day
                        df49[i]['hour'] = df49[i]['date'].dt.hour
                        
                        # for i in range(len(df49)):
                        #     try:
                        #         df49[i]['season'] = df49[i].apply(lambda x: seasons(x['date']), axis=1)
                        #     except (ValueError, KeyError) as e:
                        #         print(f"Error occurred for subset {i}: {e}")
                        #         continue  # Skip to the next iteration of the loop if an error occurs  
                        # Day of Year 
                        df49[i]['DOY'] = df49[i]['date'].dt.dayofyear
                        
                        
                     #indexces   
                    #Normalized difference vegetation index: NDVI 
                        df49[i]['NDVI'] = (df49[i]['NIR_810'].rolling(3).median() - df49[i]['VISBL_650'].rolling(3).median()) / (df49[i]['NIR_810'].rolling(3).median() + df49[i]['VISBL_650'].rolling(3).median())
                        # df49[i]['NDVI'] = df49[i]['NDVI'].clip(upper=1)
                        # df49[i]['NDVI'] =  df49[i]['NDVI'].clip(lower=0.03) 
                            # # Load data into DataFrame
                        df = pd.DataFrame({'ndvi': df49[i]['NDVI']})
                        
                        # Calculate the interquartile range (IQR)
                        Q1 =  df['ndvi'].quantile(0.25)
                        Q3 =  df['ndvi'].quantile(0.75)
                        IQR = Q3 - Q1
                        
                        # Define the range of acceptable values
                        lower_bound = Q1 - 2 * IQR
                        upper_bound = Q3 + 2 * IQR
                        
                        # Remove outliers
                        df_no_outliers = df[( df['ndvi'] >= lower_bound) & ( df['ndvi'] <= upper_bound)]
                        df49[i] = df49[i].join(df_no_outliers )                               # # Load data into DataFrame
                    
                        
        
                
                   
                else:
                 # Print a message when 'b' is not present
                     print("There is no string type '49' in the DataFrame column.")       
                
                
                ###################################################################################################################################
                
        
    
                try:
                    if 'df49' in locals() and df49:  # Check if `df4D` is defined and not empty
                        df49 = pd.concat(df49)
                        # df49 = df49.set_index('date')
                        # col = ['VISBL_450', 'VISBL_500','VISBL_550', 'VISBL_570', 'VISBL_600', 'VISBL_650','NIR_610','NIR_680','NIR_730','NIR_760','NIR_810','NIR_860']
                        col = ['ndvi']
                        
                                                
                        
                        # Define a dictionary for units if available
                        units= {'ndvi': 'normalized difference vegetation index (NDVI)'}

                        for i in col:
                            fig = px.scatter(df49, x = df49.index, y =[i], color='ID')  # Assuming 'ID' is a column in your DataFrame

                            # Set the y-axis title with units if defined
                            y_axis_title = f"{i} ({units.get(i, 'no unit')})"  # 'no unit' will be used if the unit is not defined in the units dictionary
                            fig.update_layout(yaxis_title=y_axis_title)

                            if values['plot_option'] == 'Store and visualize':
                                plotly.offline.plot(fig, filename=str(output_directory / (i+'_49.html')))
                                
                            else:
                                plotly.offline.plot(fig, filename= str(output_directory / (i+'_49.html')), auto_open=False)
                        
                        df49 = df49.reset_index(drop=True)
                        
                        
                        df49 = df49[['ID','device type','date','DOY','month', 'year','VISBL_450', 'VISBL_500','VISBL_550', 'VISBL_570', 'VISBL_600', 'VISBL_650','NIR_610','NIR_680','NIR_730','NIR_760','NIR_810','NIR_860','ndvi']]
                        df49 = df49.reset_index()
                        
                        # # #------------------------------------------------------------------------------------------------- 
                        # # # ###exporting data 
                        # # #------------------------------------------------------------------------------------------------- 
                        # Save the DataFrame as a CSV file
                        df49.to_csv(output_directory /'df49.csv', index=False)
                
                    else:
                        print("No objects to concatenate. Skipping concatenation.")
                
                except ValueError as e:
                    # Handle the error or skip the concatenation step
                    print("Error occurred during concatenation:", str(e))           
                   

    if event == sg.WIN_CLOSED or event == 'Cancel':
        break

window.close()
output_window.close()