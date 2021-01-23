import urllib.request
import socket
import json
import os


def check_license(license_id):
    account = fr'{os.getenv("userdomain")}\{os.getlogin()}'
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)

    # set url with paramaters
    url = 'https://script.google.com/macros/s/AKfycbxV9X4oicxNwdjZg8sz4fUClp9IVqA_tIpJFn79itRUf_QKBmU/exec?'
    url += f'license={license_id}'
    url += f'&ip={ip_address}'
    url += f'&account={account}'

    # get response
    response = urllib.request.urlopen(url)
    data = json.load(response)
    # print(data)
    return data
