import sys
import PySimpleGUI as sg
# from faker import Faker
from random import randint
import random
import string
from replay_parser import batch_parse
import replay_parser

# ------------------ Create a fake table ------------------
# class Faker():
#     def word(self):
#         return ''.join(random.choice(string.ascii_lowercase) for i in range(10))

# fake = Faker()
NUM_ROWS = 2
NUM_COLS = 2

ROW_DISPLAY = 15


# def rand(max=1000):
#     return randint(0, max)


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
                sg.Checkbox('Folders', default=True),
                sg.Checkbox('Replays', default=True)
            ],
        [sg.Table(values=data[1:][:], headings=headings,  # max_col_width=25,
                            # auto_size_columns=True,
                             display_row_numbers=True,
                            vertical_scroll_only=False, enable_events=False, bind_return_key=True,
                                justification='left', num_rows=ROW_DISPLAY, font='Courier 12',
                                #alternating_row_color='lightblue',
                                key='_table_',
                                # background_color='yellow',
                                row_colors=[(5, 'white', 'black')],
                                # size=(800, 800),
                                col_widths=(500, 500)
                                )],
                # [sg.Button('Read'), sg.Button('Double')],
                # [sg.T('Read = read which rows are selected')], [
                    # sg.T('Double = double the amount of data in the table')],
                # [sg.T('Selected rows = '), sg.T(
                    # '', size=(30, 1), key='_selected_rows_')],
                # [sg.Exit()]
                ]

    # ------------------ Create the window ------------------
    window = sg.Window('Table', grab_anywhere=False,
                        resizable=True).Layout(layout)
    # Change the displayed starting row numberer and the column heading for the row number
    #window.FindElement('_table_').StartingRowNumber = 1
    #window.FindElement('_table_').RowHeaderText = 'Row'

    # ------------------ The Event Loop ------------------
    while True:
            event, values = window.Read()
            if event in (None, 'Exit'):
                break
            # if event == 'Double':
            #     for i in range(len(data)):
            #         data.append(data[i])
            #     window.FindElement('_table_').Update(values=data)
            # if event == 'Read':
            #     window.Element('_selected_rows_').Update(values['_table_'])
            #     data[1][1] = 'updated'
                # window.Element('_table_').Update(data, row_colors=[(6, 'black')])
            if event == '_FILE_EXPLORER_':
                filename = values['_FILE_EXPLORER_']
                print(filename)
                replay_parser.batch = True
                replay_parser.print_all = True
                parsed = batch_parse(filename)
                # print(parsed)
                parsed = parsed.split('\n')

                #TODO: Gonna need to fix that
                records = []
                dir_entry_idx = []
                for idx, record in enumerate(parsed):
                    name, rest = record.split(': ', 1)
                    duration = rest.split(' ')[0].strip()
                    # col_widths = (max(len(name), col_widths[0]), max(len(duration), col_widths[1]))
                    records.append([name, duration])
                    if not name.endswith('.rep'):
                        dir_entry_idx.append((idx + 1, 'black'))

                data = [data[0]] + records

                window.Element('_table_').Update(data, row_colors=dir_entry_idx)

    # ------------------ User closed window so exit ------------------
    window.Close()

main()
