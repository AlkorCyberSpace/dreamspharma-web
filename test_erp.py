import os
import sys
import django

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dreamspharma.settings")
django.setup()

from dreamspharmaapp.erp_service import ERPService
from dreamspharmaapp.erp_token_service import get_erp_token_for_store_config
import requests, json, re

store_id = '001'
config = ERPService.get_config_by_store_id(store_id)
erp_config = config['erp_config']
api_key = get_erp_token_for_store_config(erp_config)
print('API_KEY:', api_key)
url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
payload = {
    'apiKey': api_key,
    'storeId': erp_config['store_id'],
    'c2Code': erp_config['c2_code'],
    'prodCode': erp_config['prod_code'],
    'inputDateTime': '2021-07-01 10:10:00',
    'itemCodes': []
}
print(f"Request Payload: {payload}")
resp = requests.post(url, json=payload) # NOTE: should this be GET or POST? wait, InventoryInsights uses GET! Let's try GET first.
print('GET STATUS:', resp.status_code)
text = resp.text
print('GET RAW TEXT[:200]:', text[:200])

resp_post = requests.post(url, json=payload)
print('POST STATUS:', resp_post.status_code)
print('POST RAW TEXT[:200]:', resp_post.text[:200])

try:
    text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', text)
    data = json.loads(text)
    stock_data = data.get('stockDetails', []) or data.get('data', [])
    if not stock_data and isinstance(data, list):
        stock_data = data
    print('PARSED ITEMS:', len(stock_data))
    if stock_data:
        print('FIRST ITEM:', stock_data[0])
except Exception as e:
    print('PARSE ERROR:', e)
