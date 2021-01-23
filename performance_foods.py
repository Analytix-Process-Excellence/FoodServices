import asyncio
import aiohttp
from bs4 import BeautifulSoup
import os
import csv
from datetime import datetime
from settings import USER_AGENT, LIMIT, TIMEOUT


BASE_URL = 'https://pay.performancefoodservice.com/ngs'


def load_location_settings():
    locations = []
    location_settings_file_path = 'location_settings.csv'
    if not os.path.isfile(location_settings_file_path):
        return None
    with open(location_settings_file_path, 'r') as location_settings:
        reader = csv.DictReader(location_settings)
        for row in reader:
            locations.append(row)
    return locations


def get_location_folder_name(locations, account_name):
    for location in locations:
        if location.get('AccountName') == account_name:
            return location.get('SubFolderName')
    return ''


async def login_load_page(sema, session):
    endpoint = '/s/NGS_A_Login'

    headers = {
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Dest': 'document',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    params = (
        ('e', 'nli'),
    )
    async with sema:
        async with session.get(f'{BASE_URL}{endpoint}', headers=headers, params=params) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            bs = BeautifulSoup(content, 'html.parser')
            login_form = bs.find('form', attrs={'id': 'login'})
            if login_form:
                login_process_url = login_form.get('action')
                csrf_token = str(login_process_url).split('CSRF_NONCE=')[-1]
            return csrf_token


async def login_submit(sema, session, username, password, csrf_token):
    endpoint = '/s/NGS_A_ProcessLogin'

    headers = {
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Origin': 'https://pay.performancefoodservice.com',
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
        'Referer': 'https://pay.performancefoodservice.com/ngs/s/NGS_A_Login?e=nli',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    params = (
        ('org.apache.catalina.filters.CSRF_NONCE', csrf_token),
    )

    data = {
        'un': username,
        'pw': password,
        'sub': 'Login',
        # below numbers are for heights and widths of window, screen and html_document
        'wH': '599',
        'wW': '1503',
        'sH': '1152',
        'sW': '2048',
        'dH': '683',
        'dW': '1508'
    }

    login_status = False
    async with sema:
        async with session.post(f'{BASE_URL}{endpoint}', headers=headers, params=params, data=data) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            if 'NGS_A_Login' in content:
                login_status = False
            else:
                login_status = True
            return login_status


async def logout(sema, session):
    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://pay.performancefoodservice.com/ngs/NGS_ACH_Home?&trail=A659875',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    async with sema:
        async with session.get('https://pay.performancefoodservice.com/ngs/NGS_A_Logout', headers=headers) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            if 'NGS_A_ProcessLogin' in content:
                return True
            else:
                return False


async def get_accounts(sema, session):
    endpoint = '/NGS_ACH_Home'

    headers = {
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    accounts = []
    async with sema:
        async with session.get(f'{BASE_URL}{endpoint}', headers=headers) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            bs = BeautifulSoup(content, 'html.parser')
            accounts_element = bs.find('select', attrs={'name': 'nTrail'})
            if accounts_element:
                account_options = accounts_element.find_all('option')
                for element in account_options:
                    accounts.append(
                        {
                            'id': element.get('value'),
                            'name': str(element).split('>')[1].split('<')[0]
                        }
                    )
    return accounts


async def get_bills(sema, session, location_id, bill_type):
    if bill_type == 'bill':
        endpoint = '/NGS_ACI_ListInvoices'
    elif bill_type == 'credit':
        endpoint = '/NGS_ACI_ListCredits'
    else:
        return None

    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        # 'Referer': 'https://pay.performancefoodservice.com/ngs/NGS_ACH_Home?&trail=A659875',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    params = (
        ('trail', location_id),
    )

    async with sema:
        async with session.get(f'{BASE_URL}{endpoint}', headers=headers, params=params) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            return content


async def parse_bills(content, location_name, start_date, end_date, bill_type):
    output = []
    bs = BeautifulSoup(content, 'html.parser')
    invoice_table_div = bs.find('div', attrs={'class': 'scrollBody'})
    if invoice_table_div:
        invoice_table = invoice_table_div.find('table')
        headings = invoice_table.find_all('th')
        rows = invoice_table.find_all('tr')
        for index, heading in enumerate(headings):
            if heading.text == 'Inv #':
                enum_bill_num = index
                continue
            if heading.text == 'Invoice Date':
                enum_bill_date = index
                continue
            if heading.text == 'Due Date':
                enum_due_date = index
                continue
            if heading.text == 'Orig Amt':
                enum_bill_amount = index
                continue

        for row in rows[:-1]:
            columns = row.find_all('td')
            if columns:
                str_bill_date = columns[enum_bill_date].text
                if bill_type == 'credit':
                    due_date = str_bill_date
                elif bill_type == 'bill':
                    due_date = columns[enum_due_date].text
                bill_num = columns[enum_bill_num].text
                bill_amount = columns[enum_bill_amount].text.replace("$", "").replace(",", "")
                bill_link = columns[enum_bill_num].a.get("href")

                dt_bill_date = datetime.strptime(str_bill_date, '%m/%d/%Y')
                if start_date <= dt_bill_date <= end_date:
                    output.append(
                        {
                            'location': location_name,
                            'bill_date': str_bill_date,
                            'due_date': due_date,
                            'bill_num': bill_num,
                            'bill_amount': bill_amount,
                            'link': bill_link,
                            'type': bill_type,
                        }
                    )
    # print('  >', len(output), bill_type)
    return output


async def load_bill_page(sema, session, pdf_link):
    headers = {
        'Connection': 'keep-alive',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    async with sema:
        async with session.get(f'{BASE_URL}/{pdf_link}', headers=headers) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            bs = BeautifulSoup(content, 'html.parser')
            redirect_link_element = bs.find('div', attrs={'class': 'contents'})
            if redirect_link_element:
                return redirect_link_element.a.get('href')
            else:
                return None


async def load_pdf_page(sema, session, pdf_link):
    cookies = {
        'ASP.NET_SessionId': 'ryuhiw5mmoibzjywhvadyzqi',
    }

    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://pay.performancefoodservice.com/',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    async with sema:
        async with session.get(pdf_link, headers=headers) as request:
            response = await request.content.read()
            content = response.decode('utf-8')
            bs = BeautifulSoup(content, 'html.parser')
            pdf_link_element = bs.find('iframe', attrs={'id': 'MainContent_frmImage'})
            if pdf_link_element:
                return pdf_link_element.get('src')
            else:
                return None


async def download_pdf(sema, session, pdf_link, download_path, bill_num):
    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Dest': 'iframe',
        # 'Referer': 'https://invoice.pfgc.com/Default.aspx?91m2Z8eAr0MsmijPV3AXbmC8mQFOc12WFX%2FFXJqd8io%3D',
        'Accept-Language': 'en-US,en;q=0.9,pa;q=0.8',
    }

    async with sema:
        async with session.get(f'https://invoice.pfgc.com{pdf_link}', headers=headers) as request:
            response = await request.content.read()
            if response:
                os.makedirs(download_path, exist_ok=True)
                with open(f'{os.path.join(download_path, str(bill_num))}.pdf', 'wb') as output_file:
                    output_file.write(response)
                    return True
    return False


async def bulk_download(sema, session, download_path, bill_link, bill_num):
    redirect_to_pdf_link = await load_bill_page(sema, session, bill_link)
    pdf_link = await load_pdf_page(sema, session, redirect_to_pdf_link)
    # file_path =
    await download_pdf(sema, session, pdf_link, download_path, bill_num)


async def download_data(start_date, end_date, username, password, download_path, locations):
    tasks = []
    # total_files = 0  # number of files downloaded
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    conn = aiohttp.TCPConnector(limit=5, limit_per_host=5)
    sema = asyncio.Semaphore(LIMIT)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        csrf_token = await login_load_page(sema, session)
        login_status = await login_submit(sema, session, username, password, csrf_token)
        if not login_status:
            print(' > Error: Could not login! Please check username and password.')
            return None
        else:
            print(' > Login successful!')
            accounts = await get_accounts(sema, session)
            for account in accounts:
                location_folder = get_location_folder_name(locations, account['name'])
                sub_folder_path = os.path.join(download_path, location_folder)
                bills_content = await get_bills(sema, session, account['id'], 'bill')
                credits_content = await get_bills(sema, session, account['id'], 'credit')
                bills = await parse_bills(bills_content, account['name'], start_date, end_date, 'bill')
                bill_credits = await parse_bills(credits_content, account['name'], start_date, end_date, 'credit')
                for bill in bills:
                    tasks.append(bulk_download(sema, session, sub_folder_path, bill['link'], bill['bill_num']))
                for credit in bill_credits:
                    tasks.append(bulk_download(sema, session, sub_folder_path, credit['link'], credit['bill_num']))

            if tasks:
                print(f' > Downloading {len(tasks)} documents:')
                # await asyncio.wait(tasks)
                loop = asyncio.get_event_loop()
                document_count = 0
                for future in asyncio.as_completed(tasks, loop=loop):
                    await future
                    document_count += 1
                print(f'\tDownloaded {document_count} of {len(tasks)}')
            # logout
            logout_status = await logout(sema, session)
            if logout_status:
                print('> Logged out!')


async def main_task(start_date, end_date, username, password, download_path, locations):
    await download_data(start_date, end_date, username, password, download_path, locations)
    

class PerformanceFoods:
    def __init__(self):
        self.username = None
        self.password = None
        self.start_date = None
        self.end_date = None
        self.download_path = 'Downloads'
        self.locations = load_location_settings()

    def download(self):
        # start_time = time.perf_counter()
        loop = asyncio.new_event_loop()
        future = asyncio.ensure_future(
            main_task(self.start_date, self.end_date, self.username, self.password, self.download_path, self.locations), loop=loop
        )
        loop.run_until_complete(future)
        # end_time = time.perf_counter()
        # time_taken = time.strftime("%H:%M:%S", time.gmtime(int(end_time - start_time)))
        # print(f'\nFinished Downloading.\nTime Taken: {time_taken}')