import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')
django.setup()
import requests, json, re
from dreamspharmaapp.erp_service import ERPService
from dreamspharmaapp.erp_token_service import get_erp_token_for_store_config

config = ERPService.get_config_by_store_id('001')
erp_config = config['erp_config']
api_key = get_erp_token_for_store_config(erp_config)
url = f"{erp_config['base_url']}/ws_c2_services_fetch_stock"
payload = {'apiKey': api_key, 'storeId': erp_config['store_id'], 'c2Code': erp_config['c2_code'], 'prodCode': erp_config['prod_code'], 'inputDateTime': '2021-07-01 10:10:00', 'itemCodes': []}
resp = requests.post(url, json=payload)
text = resp.text
text = re.sub(r'([:,\[]\s*)\.(\d)', r'\g<1>0.\2', text)
data = json.loads(text)
stock_data = data.get('stockDetails', []) or data.get('data', [])

out_of_stock = 0
for item in stock_data:
    code = item.get('c_item_code') or item.get('itemCode')
    if code:
        batch_list = item.get('batchDetails', [])
        total_ls_qty = sum(float(b.get('packQty', 0)) for b in batch_list)
        if total_ls_qty == 0:
            out_of_stock += 1
print('Actual Out of stock:', out_of_stock)
