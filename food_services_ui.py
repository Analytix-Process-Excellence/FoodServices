import PySimpleGUI as sg
from datetime import datetime, timedelta
import threading
import os
import json
from onlinefoodservices import OnlineFoodService
from performance_foods import PerformanceFoods
from settings import LICENSE
from analytix_common_functions import check_license
import time


sg.theme('Dark2')  # set window color theme


def download_data(start_date, end_date, clients):
    start_time = time.perf_counter()
    for client in clients:
        print('\nClient:', client.get('client'))
        if client.get('group') == 'OnlineFood':
            vendor = OnlineFoodService()
            vendor.start_date = start_date
            vendor.end_date = end_date
            vendor.username = client.get('username')
            vendor.password = client.get('password')
            vendor.download_path = client.get('download_path')
            vendor.download()
        elif client.get('group') == 'PerfFood':
            vendor = PerformanceFoods()
            vendor.start_date = start_date
            vendor.end_date = end_date
            vendor.username = client.get('username')
            vendor.password = client.get('password')
            vendor.download_path = client.get('download_path')
            vendor.download()
    end_time = time.perf_counter()
    time_taken = time.strftime("%H:%M:%S", time.gmtime(int(end_time - start_time)))
    print('\nFinished!')
    print(f'Time Taken: {time_taken}')


def get_client_list(setting):
    client_names = []
    for client_data in setting:
        client_names.append(client_data.get('client'))
    return client_names


def load_settings(selected_clients=None):
    settings_file_path = 'client_settings.json'
    if not os.path.isfile(settings_file_path):
        print('Settings file not found!')
        return None
    else:
        with open(settings_file_path, 'r') as settings_file:
            all_settings_json = json.load(settings_file)
            settings_json = []
            for index, client in enumerate(all_settings_json):
                if selected_clients:
                    if client.get('client') in selected_clients:
                        settings_json.append(client)
            return settings_json or all_settings_json


def run_gui(thread=None):
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    settings = load_settings()
    clients_list = get_client_list(settings)
    layout =[
        [
            sg.Text('Vendor Bills Download',
                    size=(40, 1),
                    font=('Corbel', 22),
                    justification='center',
                    pad=((0, 0), (5, 10)))
        ],

        [
            sg.Text("Start Date: ", size=(15, 1), justification='left', font=('Corbel', 11)),
            sg.Input(yesterday.date(), key="start_date", size=(15, 1), font=('Calibri', 11), justification='left')
        ],

        [
            sg.Text("End Date: ", size=(15, 1), justification='left', font=('Corbel', 11)),
            sg.Input(yesterday.date(), key="end_date", size=(15, 1), font=('Calibri', 11), justification='left')
        ],

        [
            sg.Text("Client Name: ", size=(15, 1), justification='left', font=('Corbel', 11)),
            sg.Listbox(values=clients_list, size=(25, 4), font=('Corbel', 11),
                       select_mode='extended', key='client_list', tooltip='Hold CTRL to select multiple clients')
        ],

        # [
        #     sg.Text('Report:', size=(15, 1), justification='left', font=('Corbel', 11)),
        #     sg.Listbox(values=report_list, size=(29, 5), font=('Corbel', 10),
        #                select_mode='extended', key='report', tooltip='Hold CTRL to select multiple reports')
        # ],

        [
            sg.OK('Download', key='download', size=(10, 1), font=('Corbel', 12), pad=((5, 5), (10, 0))),
            sg.Exit('Exit', key='exit', size=(10, 1), font=('Corbel', 12), pad=((5, 5), (10, 0))),
        ],
        [
            sg.Frame(
                title='Status', pad=((5, 0), (10, 10)),
                layout=[
                    # [
                    #     sg.ProgressBar(max_value=100, key='progressbar', size=(100, 20), pad=((5, 5), (5, 5)))
                    # ],
                    [sg.Multiline(
                        'Ready', key='status', autoscroll=True, reroute_stdout=True, reroute_stderr=True,
                        size=(100, 20), disabled=True, font=('Calibri', '10')
                    )]
                ]
            )
        ],
        # [sg.Multiline('', key='status', autoscroll=True, visible=False, size=(60, 15), disabled=True)]
    ]

    window = sg.Window(
        'Vendor Bill Download',
        size=(500, 600),
        element_justification='left',
        text_justification='left',
        auto_size_text=True
    ).Layout(layout)

    while True:
        event, values = window.Read(timeout=1000)
        if event in ('Exit', None) or event == sg.WIN_CLOSED:  # if user closes window to clicks Exit button
            window.close()
            exit()
            break
        elif event == 'download':
            try:
                start_date = datetime.strptime(values['start_date'], '%Y-%m-%d')
                end_date = datetime.strptime(values['end_date'], '%Y-%m-%d')
                days_count = end_date - start_date
                window['status'].Update('Processing...\n')
                window.refresh()
                # print(days_count.days)
                if days_count.days > 31:
                    sg.Popup('Please select a Date Range of less than 31 Days', title='Error in date range')
                    continue
            except Exception:
                sg.Popup('Please enter start date and end date in YYYY-MM-DD format.', title='Error in date range')
                continue
            if start_date > end_date:
                sg.Popup('Start Date cannot be greater than End date.', title='Error in date range')
                continue
            # output_path = values['output_path']
            selected_clients = values['client_list']
            if not selected_clients:
                sg.Popup('No client selected. Please select atleast one client.', title='Error in client selection')
                continue

            # report_names = values['report']
            # if not report_names:
            #     sg.Popup('Report not selected. Please select any one report.', title='Error in report selection')
            #     continue
            window['download'].Update(disabled=True)
            # window['status'].Update(generate_status_tree(selected_clients))
            selected_clients_json = load_settings(selected_clients)
            window.refresh()
            thread = threading.Thread(target=download_data,
                                      args=(start_date, end_date, selected_clients_json))
            # download(report_name, start_date, end_date, selected_clients_json)
            thread.start()
        elif event == "exit" or event == sg.WIN_CLOSED:
            window.close()
            break

        # enable download button when thread is closed
        if thread:
            if not thread.is_alive():
                window['download'].Update(disabled=False)
                window.refresh()


if __name__ == '__main__':
    try:
        check_license(LICENSE)
    except Exception as e:
        pass
    run_gui()
