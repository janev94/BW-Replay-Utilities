# img_viewer.py

import PySimpleGUI as sg
import os.path
import replay_parser
from replay_parser import batch_parse, parse

# First the window layout in 2 columns

file_list_column = [
    [
        sg.Text("File Explorer"),
        sg.In(size=(25, 1), enable_events=True, key="-FILE_EXPLORER-"),
        sg.FolderBrowse(),
    ],
    [
        sg.Listbox(
            values=[], enable_events=True, size=(40, 20), key="-FILE LIST-"
        )
    ],
]

# For now will only show the name of the file that was chosen
image_viewer_column = [
    [sg.Text("Select a directory to analyze from the list on left:")],
    [sg.Text(size=(40, 1), key="-TOUT-")],
    [sg.Text(size=(40,40), key="-PARSED_OUTPUT-", text_color="black")],
]

# ----- Full layout -----
layout = [
    [
        sg.Column(file_list_column),
        sg.VSeperator(),
        sg.Column(image_viewer_column),
    ]
]

window = sg.Window("BW Replay Util", layout, resizable=True)

# Run the Event Loop
while True:
    event, values = window.read()
    if event == "Exit" or event == sg.WIN_CLOSED:
        break
    # Folder name was filled in, make a list of files in the folder
    if event == "-FILE_EXPLORER-":
        folder = values["-FILE_EXPLORER-"]
        items = []
        try:
            # Get list of files in folder
            for path, _, files in os.walk(folder):
                temp = []
                if files:
                    for rep in files:
                        if rep.endswith('.rep'):
                            rel_path = path.replace(folder, '.')
                            item = os.path.join(rel_path, rep)
                            temp.append(item)
                if temp:
                    items.append(path)
                    items.extend(temp)
        except:
            items = []

        window["-FILE LIST-"].update(items)

    elif event == "-FILE LIST-":  # A file was chosen from the listbox
        try:
            filename = os.path.join(
                os.path.normpath(values["-FILE_EXPLORER-"]), values["-FILE LIST-"][0]
            )
            out = ""

            replay_parser.batch = True
            replay_parser.print_all = True

            if os.path.isdir(filename):
                replay_parser.batch = True
                replay_parser.print_all = False
                out = batch_parse(filename)
            else:
                # if it's a file we need to remove the . that we added for displaying purposes
                filename = os.path.join(os.path.normpath(values["-FILE_EXPLORER-"]), values["-FILE LIST-"][0][1:])
                parsed = replay_parser.parse(filename)
                if not parsed:
                    # Parsing failed for any reason, e.g., replay was not 1.21
                    continue
                players = set([ x['player_name'] for x in parsed['player_info'] ])
                if replay_parser.print_all:
                    out = f'{filename}: {parsed["time_formatted"]} {players}'
                

            window["-TOUT-"].update(filename)
            window["-PARSED_OUTPUT-"].update(out)

        except Exception as e:
            raise e

window.close()
