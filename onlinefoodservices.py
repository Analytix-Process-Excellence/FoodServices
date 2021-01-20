import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup
import re
import os
from xhtml2pdf import pisa
from datetime import datetime


BASE_URL = 'https://eastern5.onlinefoodservice.com'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 ' \
             'Safari/537.36'

LIMIT = 3  # number of connections

TIMEOUT = 600  # seconds


class OnlineFoodService:
    def __init__(self):
        self.username = None
        self.password = None
        self.locations = []
        self.session_id = None
        self.start_date = datetime(2020, 12, 1)
        self.end_date = datetime.today()

    async def login(self, sema, session, username, password):
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
            'UserName': username,
            'Password': password
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

    async def get_session_id(self, content):
        session_id_text_pattern = re.compile(r"var screenSessionID = '(.+?)';", re.MULTILINE)
        session_id_regex = re.search(session_id_text_pattern, content)
        if session_id_regex:
            self.session_id = session_id_regex.group(1)
        return self.session_id

    async def get_accounts(self, content):
        bs = BeautifulSoup(content, 'html.parser')
        location_dropdown_element = bs.find('select', attrs={'name': 'selectedCustomer'})
        if location_dropdown_element:
            location_options_elements = location_dropdown_element.find_all('option')
            for element in location_options_elements:
                self.locations.append(
                    {
                        'id': element.get('value'),
                        'name': element.text
                    }
                )
        return self.locations

    async def set_account(self, sema, session, location_id):
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
            'SCRNOPT1': location_id,
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

        data = {
            'SCRNFRME': 'Content',
            'SCRNSESSIONID': self.session_id,
            'SCRNSRCE': 'ACCOUNTREV',
            'SCRNDEST': 'INVOICEIQ',
            'SCRNCMD': 'view',
            'SCRNOPT1': '',
            'SCRNOPT2': '',
            'SCRNMENU': '',
            'webnowurl': '',
            'invoicenumber': adj_num,
            'invoicetotal': str(amount),
            'invoiceRowIndex': str(row_index),
            'invoicetype': 'Adj',
            'customer': '',
            'deliveryconfirmation': '',
            'refinvoicenumber': ref_num
        }

        async with sema:
            async with session.post('https://eastern5.onlinefoodservice.com/pnet/eOrderServlet', headers=headers,
                                    data=data) as request:
                response = await request.content.read()
                # content = response.decode('utf-8')
                if response:
                    output_file_name = os.path.join('Downloads', f'{adj_num}.pdf')
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
        folder_path = os.path.join(os.getcwd(), 'Downloads')
        file_name = f'{bill_num}.pdf'
        os.makedirs(folder_path, exist_ok=True)
        with open(os.path.join(folder_path, file_name), 'wb') as output_file:
            output_file.write(content)

    async def download(self, username, password):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        conn = aiohttp.TCPConnector(limit=5, limit_per_host=5)
        sema = asyncio.Semaphore(LIMIT)
        async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
            login_status = await self.login(sema, session, username, password)
            # if login_status is true means sign in was successful
            if not login_status:
                print('Could not login!')
            else:
                print('Logged in successfully')
                for location in self.locations:
                    await self.set_account(sema, session, location['id'])
                    bill_details = await self.get_bills(sema, session)
                    bill_list = await self.parse_bill_list(bill_details)
                    tasks = []
                    for bill in bill_list:
                        if bill['type'] == 'Invoice':
                            await self.download_bill(sema, session, bill['bill_num'])
                        elif bill['type'] == 'Adj':
                            await self.download_adj(
                                    sema, session, bill['bill_num'], bill['ref_num'], bill['amount'], bill['row_index']
                                )
                    if tasks:
                        loop = asyncio.get_event_loop()
                        await asyncio.gather(*tasks, loop=loop)

    async def main_task(self):
        # https://eastern5.onlinefoodservice.com/pnet/eOrderServlet
        await self.download(username='55039449', password='34580')


if __name__ == '__main__':
    onlinefoodservices = OnlineFoodService()
    start_time = time.perf_counter()
    loop = asyncio.new_event_loop()
    future = asyncio.ensure_future(onlinefoodservices.main_task(), loop=loop)
    loop.run_until_complete(future)
    end_time = time.perf_counter()
    time_taken = time.strftime("%H:%M:%S", time.gmtime(int(end_time - start_time)))
    print(f'Finished Downloading.\nTime Taken: {time_taken}')
