import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import os
import csv
from xhtml2pdf import pisa
from datetime import datetime
from settings import USER_AGENT, LIMIT, TIMEOUT


BASE_URL = 'https://eastern5.onlinefoodservice.com'


class OnlineFoodService:
    def __init__(self):
        self.username = None
        self.password = None
        self.accounts = []
        self.session_id = None
        self.start_date = datetime(2020, 12, 1)
        self.end_date = datetime.today()
        self.download_path = 'Downloads'
        self.locations = []
        self.load_location_settings()
        self.sub_folder_path = ''

    async def login(self, sema, session):
        endpoint = '/pnet/eOrderServlet'

        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://eastern5.onlinefoodservice.com',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://eastern5.onlinefoodservice.com/pnet/eOrder',
            'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
        }

        data = {
            'SCRNFRME': '_top',
            'SCRNSESSIONID': '',
            'SCRNSRCE': 'SIGNON',
            'SCRNDEST': 'SIGNON',
            'SCRNCMD': 'Signon',
            'ResetMessage': 'true',
            'UserAgent': USER_AGENT,
            'BrowserVersion': USER_AGENT,
            'lang': '',
            'ScreenRes': '1080',
            'UserName': self.username,
            'Password': self.password
        }

        async with sema:
            async with session.post(f'{BASE_URL}{endpoint}', headers=headers, data=data
            ) as request:
                response = await request.content.read()
                content = response.decode('utf-8')
                if 'username' not in content and 'password' not in content and 'Internal Server Error' not in content:
                    await self.get_accounts(content)  # get vendor accounts
                    await self.get_session_id(content)  # find session id
                    return True
                else:
                    return False

    async def logout(self, sema, session):
        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://eastern5.onlinefoodservice.com',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,'
                      '*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            # 'Referer': 'https://eastern5.onlinefoodservice.com/pnet/Dashboard.jsp',
            'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
        }

        data = {
            'SCRNFRME': '_top',
            'SCRNSESSIONID': self.session_id,
            'SCRNSRCE': 'DASHBOARD',
            'SCRNDEST': 'SIGNOFF',
            'SCRNCMD': 'SIGNOFF',
            'SCRNOPT1': '',
            'SCRNOPT2': '',
            'SCRNMENU': 'main',
            'MessageId': '',
            'invoicenumber': '',
            'invoiceRowIndex': '',
            'invoicetotal': '',
            'invoicetype': '',
            'customer': '',
            'deliveryconfirmation': '',
            'refinvoicenumber': '',
            'allowaccess': '',
            'classes': True,
            'cats': True,
            'fams': False,
            'brands': True,
            'nacs': False,
            'attributes': False,
            'autocomplete': False
        }

        async with sema:
            async with session.post('https://eastern5.onlinefoodservice.com/pnet/eOrderServlet', headers=headers,
                                    data=data) as request:
                response = await request.content.read()
                content = response.decode('utf-8')
                if 'username' in content or 'password' in content or 'Internal Server Error' in content:
                    return True
                else:
                    return False

    async def get_session_id(self, content):
        session_id_text_pattern = re.compile(r"var screenSessionID = '(.+?)';", re.MULTILINE)
        session_id_regex = re.search(session_id_text_pattern, content)
        if session_id_regex:
            self.session_id = session_id_regex.group(1)
        return self.session_id

    async def get_accounts(self, content):
        bs = BeautifulSoup(content, 'html.parser')
        account_dropdown_element = bs.find('select', attrs={'name': 'selectedCustomer'})
        if account_dropdown_element:
            account_options_elements = account_dropdown_element.find_all('option')
            for element in account_options_elements:
                self.accounts.append(
                    {
                        'id': element.get('value'),
                        'name': element.text
                    }
                )
        return self.accounts

    def load_location_settings(self):
        location_settings_file_path = 'location_settings.csv'
        if not os.path.isfile(location_settings_file_path):
            return None
        with open(location_settings_file_path, 'r') as location_settings:
            reader = csv.DictReader(location_settings)
            for row in reader:
                self.locations.append(row)
        return self.locations

    def get_location_folder_name(self, account_name):
        for location in self.locations:
            if location.get('AccountName') == account_name:
                return location.get('SubFolderName')
        return ''

    async def set_account(self, sema, session, account_id):
        endpoint = '/pnet/eOrderServlet'

        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://eastern5.onlinefoodservice.com',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                      'application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://eastern5.onlinefoodservice.com/pnet/Dashboard.jsp',
            'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
        }

        data = {
            'SCRNFRME': '_top',
            'SCRNSESSIONID': self.session_id,
            'SCRNSRCE': 'DASHBOARD',
            'SCRNDEST': 'DASHBOARD',
            'SCRNCMD': 'init',
            'SCRNOPT1': account_id,
            'SCRNOPT2': '',
            'SCRNMENU': '',
            'MessageId': '',
            'invoicenumber': '',
            'invoiceRowIndex': '',
            'invoicetotal': '',
            'invoicetype': '',
            'customer': '',
            'deliveryconfirmation': '',
            'refinvoicenumber': '',
            'allowaccess': '',
            'classes': 'true',
            'cats': 'true',
            'fams': 'true',
            'brands': 'true',
            'nacs': 'false',
            'attributes': 'false',
            'autocomplete': 'false'
        }

        async with sema:
            async with session.post(f'{BASE_URL}{endpoint}', headers=headers, data=data) as request:
                response = await request.content.read()
                content = response.decode('utf-8')
                return content

    async def get_bills(self, sema, session):
        endpoint = '/pnet/AccountPanel.jsp'

        headers = {
            'Connection': 'keep-alive',
            'Accept': 'text/html, */*; q=0.01',
            'DNT': '1',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': USER_AGENT,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://eastern5.onlinefoodservice.com',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            # 'Referer': 'https://eastern5.onlinefoodservice.com/pnet/Dashboard.jsp',
            'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
        }

        data = {
            'reload': 'false'
        }

        async with sema:
            async with session.post(f'{BASE_URL}{endpoint}', headers=headers, data=data) as request:
                response = await request.content.read()
                content = response.decode('utf-8')
                # print(content)
                return content

    async def parse_bill_list(self, content):
        output = []
        bs = BeautifulSoup(content, 'html.parser')
        bill_table = bs.find('table', attrs={'id': 'account'})
        if bill_table:
            heading_elements = bill_table.find_all('th')
            if heading_elements:
                for index, heading_element in enumerate(heading_elements):
                    if heading_element.text == 'Invoice #':
                        enum_bill_num = index
                        continue
                    if heading_element.text == 'Date':
                        enum_bill_date = index
                        continue
                    if heading_element.text == 'Amount':
                        enum_bill_amount = index
                        continue
                    if heading_element.text == 'Type':
                        enum_bill_type = index
                        continue
                    if heading_element.text == 'Reference':
                        enum_reference = index
                        continue

            row_body_element = bill_table.find('tbody')
            if row_body_element:
                row_elements = row_body_element.find_all('tr')
                for index, row_element in enumerate(row_elements):
                    column_elements = row_element.find_all('td')
                    str_bill_date = column_elements[enum_bill_date].text
                    bill_date = datetime.strptime(str_bill_date, '%m/%d/%Y')
                    # check if bill date falls within the range of start date and end date
                    if not self.start_date <= bill_date <= self.end_date:
                        continue
                    bill_amount = column_elements[enum_bill_amount].text
                    bill_type = column_elements[enum_bill_type].text
                    if bill_type == 'Invoice' or bill_type == 'Adj':
                        reference_num_element = str(column_elements[enum_reference])
                        bill_num_element = str(column_elements[enum_bill_num])
                    else:
                        continue
                    # format bill_num and reference number
                    bill_num = await self.get_document_number(bill_num_element)
                    reference_num = await self.get_document_number(reference_num_element)
                    # add to output list
                    output.append(
                        {
                            'bill_num': bill_num,
                            'date': bill_date,
                            'amount': bill_amount,
                            'type': bill_type,
                            'ref_num': reference_num,
                            'row_index': index,
                        }
                    )
        return output

    async def get_document_number(self, html_element):
        doc_num = None
        if html_element != '' and html_element:
            doc_num_regex = re.search(r'value="(.+?)"', html_element)
            if doc_num_regex:
                doc_num = doc_num_regex.group(1)
        return doc_num

    async def download_bill(self, sema, session, bill_num):
        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': USER_AGENT,
            'Origin': 'https://eastern5.onlinefoodservice.com',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            # 'Referer': 'https://eastern5.onlinefoodservice.com/pnet/Dashboard.jsp',
            'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
        }

        data = {
            'SCRNFRME': 'Content',
            'SCRNSESSIONID': self.session_id,
            'SCRNSRCE': 'DASHBOARD',
            'SCRNDEST': 'ACCOUNTREV',
            'SCRNCMD': 'export',
            'SCRNOPT1': 'invoicedoclink',
            'SCRNOPT2': str(bill_num),
            'SCRNMENU': '',
            'MessageId': '',
            'invoicenumber': '',
            'invoiceRowIndex': '',
            'invoicetotal': '',
            'invoicetype': '',
            'customer': '',
            'deliveryconfirmation': '',
            'refinvoicenumber': '',
            'allowaccess': '',
            'classes': True,
            'cats': True,
            'fams': True,
            'brands': True,
            'nacs': False,
            'attributes': False,
            'autocomplete': False,
        }

        async with sema:
            async with session.post('https://eastern5.onlinefoodservice.com/pnet/eOrderServlet', headers=headers,
                                    data=data) as request:
                response = await request.content.read()
                # content = response.decode('utf-8')
                if response:
                    await self.save_pdf(bill_num=bill_num, content=response)
                    return True
                else:
                    return False

    async def download_adj(self, sema, session, adj_num, ref_num, amount, row_index):
        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Origin': 'https://eastern5.onlinefoodservice.com',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'iframe',
            # 'Referer': 'https://eastern5.onlinefoodservice.com/pnet/eOrderServlet',
            'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
        }

        # data = {
        #     'SCRNFRME': 'Content',
        #     'SCRNSESSIONID': self.session_id,
        #     'SCRNSRCE': 'ACCOUNTREV',
        #     'SCRNDEST': 'INVOICEIQ',
        #     'SCRNCMD': 'view',
        #     'SCRNOPT1': '',
        #     'SCRNOPT2': '',
        #     'SCRNMENU': '',
        #     'webnowurl': '',
        #     'invoicenumber': adj_num,
        #     'invoicetotal': str(amount),
        #     'invoiceRowIndex': str(row_index),
        #     'invoicetype': 'Adj',
        #     'customer': '',
        #     'deliveryconfirmation': '',
        #     'refinvoicenumber': ref_num
        # }

        data = {
            'SCRNFRME': 'Content',
            'SCRNSESSIONID': self.session_id,
            'SCRNSRCE': 'DASHBOARD',
            'SCRNDEST': 'INVOICEIQ',
            'SCRNCMD': 'view',
            'SCRNOPT1': '',
            'SCRNOPT2': '',
            'SCRNMENU': '',
            'MessageId': '',
            'invoicenumber': ref_num,
            'invoiceRowIndex': str(row_index),
            'invoicetotal': str(amount),
            'invoicetype': 'Adj',
            # 'customer': '55039955',
            'deliveryconfirmation': '',
            'refinvoicenumber': ref_num,
            'allowaccess': '',
            'classes': True,
            'cats': True,
            'fams': False,
            'brands': True,
            'nacs': False,
            'attributes': False,
            'autocomplete': False
        }

        async with sema:
            async with session.post('https://eastern5.onlinefoodservice.com/pnet/eOrderServlet', headers=headers,
                                    data=data) as request:
                response = await request.content.read()
                # content = response.decode('utf-8')
                if response:
                    output_folder = os.path.join(self.download_path, self.sub_folder_path)
                    os.makedirs(output_folder, exist_ok=True)
                    output_file_name = os.path.join(output_folder, f'{ref_num}.pdf')
                    save_status = await self.convert_html_to_pdf(response, output_file_name)
                    return save_status

    async def convert_html_to_pdf(self, source_html, output_filename):
        # open output file for writing (truncated binary)
        result_file = open(output_filename, "wb")

        # convert HTML to PDF
        pisa_status = pisa.CreatePDF(
            source_html,                # the HTML to convert
            dest=result_file)           # file handle to recieve result

        # close output file
        result_file.close()                 # close output file

        # return False on success and True on errors
        return pisa_status.err

    async def save_pdf(self, bill_num, content):
        folder_path = os.path.join(self.download_path, self.sub_folder_path)
        file_name = f'{bill_num}.pdf'
        os.makedirs(folder_path, exist_ok=True)
        with open(os.path.join(folder_path, file_name), 'wb') as output_file:
            output_file.write(content)

    async def download_data(self):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        conn = aiohttp.TCPConnector(limit=5, limit_per_host=5)
        sema = asyncio.Semaphore(LIMIT)
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            login_status = await self.login(sema, session)
            # if login_status is true means sign in was successful
            if not login_status:
                print(' > Error: Could not login! Please check username and password')
            else:
                print(' > Logged in successfully')
                for account in self.accounts:
                    # print(f' > Account: {account["name"]}')
                    self.sub_folder_path = self.get_location_folder_name(account['name'])
                    print('Location:', self.sub_folder_path)
                    await self.set_account(sema, session, account['id'])
                    bill_details = await self.get_bills(sema, session)
                    bill_list = await self.parse_bill_list(bill_details)
                    print(f'\tDownloading {len(bill_list)} documents')
                    tasks = []
                    for bill in bill_list:
                        # if bill['type'] == 'Invoice':
                        #     tasks.append(self.download_bill(sema, session, bill['bill_num']))
                        # elif bill['type'] == 'Adj':
                        #     tasks.append(self.download_adj(
                        #             sema, session, bill['bill_num'], bill['ref_num'], bill['amount'], bill['row_index']
                        #         ))
                        if bill['type'] == 'Invoice':
                            await self.download_bill(sema, session, bill['bill_num'])
                        elif bill['type'] == 'Adj':
                            await self.download_adj(
                                    sema, session, bill['bill_num'], bill['ref_num'], bill['amount'], bill['row_index']
                                )
                    # if tasks:
                    #     loop = asyncio.get_event_loop()
                    #     for future in asyncio.as_completed(tasks, loop=loop):
                    #         await future
                logout_status = await self.logout(sema, session)
                if logout_status:
                    print('>Logged out!')

    def download(self):
        loop = asyncio.new_event_loop()
        future = asyncio.ensure_future(self.download_data(), loop=loop)
        loop.run_until_complete(future)
