import sys
import PySimpleGUI as sg
from replay_parser import batch_parse
import replay_parser

NUM_ROWS = 2
NUM_COLS = 2

ROW_DISPLAY = 15


def populate_table(table, raw_data, table_data):
    records = []
    dir_entry_idx = []
    for idx, record in enumerate(raw_data):
        name = record['path']
        duration = record['elapsed_time']
        records.append([name, duration])
        if record.get('is_dir'):
            dir_entry_idx.append((idx + 1, 'black'))


    table_data = [table_data[0]] + records

    table.Update(table_data, row_colors=dir_entry_idx)


def sort_table_by(*,table, key, headings, table_data, data):
    sort_idx = -1
    for idx, heading  in enumerate(headings):
        if heading.lower().strip() == key:
            sort_idx = idx
            break
    table_data = list(table_data)
    if sort_idx:
        table_data = sorted(table_data, key=lambda x: x['elapsed_time'])
    else:
        table_data = sorted(table_data, key=lambda x: x['path'])
    
    populate_table(table, table_data, data)


def main():
    data = [i for i in range(NUM_ROWS)]
    data[0] = ['Name' + ' '*100, 'Duration' + ' '*3]
    for i in range(1, NUM_ROWS):
        data[i] = ['', '']

    headings = [data[0][x] for x in range(len(data[0]))]

    # ------------------ Create a window layout ------------------
    layout = [
            [
                sg.Text("File Explorer"),
                sg.In(size=(80, 1), enable_events=True, key="_FILE_EXPLORER_"),
                sg.FolderBrowse(),
                sg.Text("Filters:"),
                sg.Checkbox('Folders', default=True, key='_filter_folders_', enable_events=True),
                sg.Checkbox('Replays', default=True, key='_filter_files_', enable_events=True)
            ],
            [
                sg.Text("Sort on:"),
                *[sg.Radio(heading, 'SORT_KEYS', key=f'_radio_{heading.lower().strip()}_', enable_events=True) for heading in headings]
            ],
        [sg.Table(values=data[1:][:], headings=headings,  
                            auto_size_columns=True,
                             display_row_numbers=True,
                            vertical_scroll_only=False, enable_events=True, bind_return_key=True,
                                justification='left', num_rows=ROW_DISPLAY, font='Courier 12',
                                key='_table_',
                                row_colors=[(5, 'white', 'black')],
                                # col_widths=(500, 500) Colwidths are infered from header width :/
                                )],
                ]

    # ------------------ Create the window ------------------
    window = sg.Window('Table', grab_anywhere=False,
                        resizable=True).Layout(layout)

    memoized = {}
    parsed = None
    filtered_data = None
    # ------------------ The Event Loop ------------------
    while True:
            event, values = window.Read()
            if event in (None, 'Exit'):
                break
            if event == '_FILE_EXPLORER_':
                filename = values['_FILE_EXPLORER_']
                window.Element('_filter_folders_').update(value=True)
                window.Element('_filter_files_').update(value=True)
                window.Element('_radio_name_').update(value=True)
                replay_parser.batch = True
                replay_parser.print_all = True
                
                if filename in memoized:
                    parsed = memoized[filename]
                else:
                    parsed = batch_parse(filename)
                    memoized[filename] = parsed
                filtered_data = parsed

                sort_table_by(table=window.Element('_table_'), key='name', headings=headings, table_data=filtered_data, data=data)

                populate_table(window.Element('_table_'), parsed, data)
            if event == '_filter_folders_':
                if parsed:
                    filter_folders = values['_filter_folders_']
                    filter_files = values['_filter_files_']
                    if filter_folders and filter_files:
                        filtered_data = parsed
                    elif filter_folders or filter_files: 
                        filtered_data = filter(lambda x: bool(x.get('is_dir')) == values['_filter_folders_'], parsed)
                        filtered_data = list(filtered_data)
                    
                    else:
                        filtered_data = []

                    if values['_radio_duration_']:
                        #TODO: might cause problems if more keys are introduced
                        sort_table_by(table=window.Element('_table_'), key='duration', headings=headings, table_data=filtered_data, data=data)
                        continue

                    populate_table(window.Element('_table_'), filtered_data, data)
            if event == '_filter_files_':
                if parsed:
                    filter_folders = values['_filter_folders_']
                    filter_files = values['_filter_files_']
                    if filter_folders and filter_files:
                        filtered_data = parsed
                    elif filter_files or filter_folders:
                        filtered_data = filter(lambda x: not bool(x.get('is_dir')) == filter_files, parsed)
                        filtered_data = list(filtered_data)
                    
                    else:
                        filtered_data = []

                    if values['_radio_duration_']:
                        #TODO: might cause problems if more keys are introduced
                        sort_table_by(table=window.Element('_table_'), key='duration', headings=headings, table_data=filtered_data, data=data)    
                        continue

                    populate_table(window.Element('_table_'), filtered_data, data)
            if event.startswith('_radio'):
                if parsed:
                    sort_key = event.replace('_radio_', '')[:-1]
                    sort_table_by(table=window.Element('_table_'), key=sort_key, headings=headings, table_data=filtered_data, data=data)

    # ------------------ User closed window so exit ------------------
    window.Close()

main()
