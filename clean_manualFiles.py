import os
import re
import FreeSimpleGUI as sg

def process_files_in_folder(folder_path, window):
    """
    Processes .txt files in the given folder_path, extracts data based on a pattern,
    and saves the processed data (matched lines) to new .txt files in a 
    'processed_files' subfolder.

    Args:
        folder_path (str): The path to the folder containing .txt files.
        window (sg.Window): The PySimpleGUI window object to update with messages.
    """
    if not folder_path or not os.path.isdir(folder_path):
        window['-OUTPUT-'].print("Error: Please select a valid folder first.", text_color='red')
        return

    window['-OUTPUT-'].print(f"Selected folder: {folder_path}")

    # Create a subfolder for processed files inside the selected folder
    output_folder = os.path.join(folder_path, "processed_files")
    try:
        os.makedirs(output_folder, exist_ok=True)
        window['-OUTPUT-'].print(f"Processed files will be saved in: {output_folder}")
    except OSError as e:
        window['-OUTPUT-'].print(f"Error creating output directory {output_folder}: {e}", text_color='red')
        return

    # Regex pattern: Captures the entire relevant segment starting with 8digitID.
    # (\w{8};[^;]+;[^;]+;[^;]+;.*)
    # \w{8}: exactly 8 digits for ID
    # [^;]+: one or more characters that are not a semicolon (for record_number, string_type, timestamp)
    # .*: any characters until the end of the line (for other data, including further semicolons)
    pattern = re.compile(r"(\w{8};[^;]+;[^;]+;[^;]+;.*)")

    found_txt_files = False
    processed_any_file_successfully = False

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):

            if os.path.commonpath([os.path.join(folder_path, filename), output_folder]) == output_folder:
                if os.path.samefile(os.path.dirname(os.path.join(folder_path, filename)), output_folder): # More specific check
                    continue


            found_txt_files = True
            filepath = os.path.join(folder_path, filename)
            window['-OUTPUT-'].print(f"\nProcessing file: {filepath}...")

            lines_to_write_to_output_file = [] # Store the exact matched strings
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_content in f: 
                        match = pattern.search(line_content)
                        if match:
                           
                            stripped_line = match.group(0) 
                            lines_to_write_to_output_file.append(stripped_line)
                
                if lines_to_write_to_output_file:
                    base_filename = os.path.splitext(filename)[0]
                    output_txt_filename = f"{base_filename}_processed.txt"
                    output_txt_filepath = os.path.join(output_folder, output_txt_filename)
                    
                    # Write the collected lines directly to the new .txt file
                    with open(output_txt_filepath, 'w', encoding='utf-8') as outfile:
                        for line_to_write in lines_to_write_to_output_file:
                            outfile.write(line_to_write + "\n")
                    
                    window['-OUTPUT-'].print(f"  Successfully processed and saved to: {output_txt_filepath}", text_color='green')
                    processed_any_file_successfully = True
                else:
                    window['-OUTPUT-'].print(f"  No lines matching the pattern found in {filename}.", text_color='orange')

            except Exception as e:
                window['-OUTPUT-'].print(f"  Error processing file {filename}: {e}", text_color='red')
    
    if not found_txt_files:
        window['-OUTPUT-'].print(f"\nNo .txt files found in the folder: {folder_path}", text_color='orange')
    elif processed_any_file_successfully:
        window['-OUTPUT-'].print("\nProcessing complete. ✅", text_color='green')
    else:
        window['-OUTPUT-'].print("\nProcessing finished. No new files created or no matching data found.", text_color='orange')


def main_gui():
    """
    Sets up and runs the PySimpleGUI interface.
    """
    sg.theme("SystemDefault1")

    layout = [
        [sg.Text("Select the folder containing your .txt files:")],
        [sg.InputText(key="-FOLDER_PATH-", readonly=True, enable_events=True, size=(60,1)), 
         sg.FolderBrowse(target="-FOLDER_PATH-")],
        [sg.Button("Process Files", key="-PROCESS-", size=(15,1), button_color=('white', 'green')), 
         sg.Button("Exit", size=(10,1), button_color=('white', 'red'))],
        [sg.Text("Output Log:")],
        [sg.Multiline(size=(88, 20), key="-OUTPUT-", autoscroll=True, reroute_stdout=False, write_only=False, disabled=True, background_color='light grey', text_color='black')]
    ]

    window = sg.Window("Log File Processor v1.1", layout, finalize=True)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == "Exit":
            break
        
        if event == "-FOLDER_PATH-": 
            selected_path = values["-FOLDER_PATH-"]
            if selected_path:
                
                 # window["-OUTPUT-"].update("") 
                 window["-OUTPUT-"].print(f"Folder selected: {selected_path}")
            
        if event == "-PROCESS-":
            folder_path = values["-FOLDER_PATH-"]
            if folder_path:
                window["-OUTPUT-"].update("") # Clear previous output before new processing
                process_files_in_folder(folder_path, window)
            else:
                
                window["-OUTPUT-"].print("Error: No folder selected. Please browse for a folder.", text_color='red')
                sg.popup_error("No folder selected!", "Please use the 'Browse' button to select a folder containing your .txt files.")


    window.close()

if __name__ == "__main__":
    main_gui()
