"""
ERP Test Server - Flask Application
Run this to simulate the client's ERP system for testing

Usage:
    pip install flask
    python erp_test_server.py

Server will run on: http://192.168.1.45:8000/
"""

from flask import Flask, request, jsonify
import base64
from datetime import datetime

app = Flask(__name__)

# ==================== DUMMY DATA ====================

# API Tokens storage
API_TOKENS = {}

# Item Master Data
ITEMS = [
    {
        "c_item_code": "I00003",
        "itemName": "DOLO 250MG SUSP",
        "itemQtyPerBox": 1,
        "batchNo": "DOLN096",
        "stockBalQty": 984,
        "std_disc": 24.24,
        "max_disc": 0.00,
        "expiryDate": "2027-5-13",
        "mrp": 75.03
    },
    {
        "c_item_code": "I00017",
        "itemName": "AMALGIN",
        "itemQtyPerBox": 1,
        "batchNo": "AMG001",
        "stockBalQty": 2000,
        "std_disc": 15.00,
        "max_disc": 0.00,
        "expiryDate": "2027-12-01",
        "mrp": 85.50
    },
    {
        "c_item_code": "I00049",
        "itemName": "ASPIRIN 500MG",
        "itemQtyPerBox": 10,
        "batchNo": "ASP001",
        "stockBalQty": 500,
        "std_disc": 20.00,
        "max_disc": 5.00,
        "expiryDate": "2027-10-15",
        "mrp": 6.81
    },
    {
        "c_item_code": "I00048",
        "itemName": "PARACETAMOL 650MG",
        "itemQtyPerBox": 10,
        "batchNo": "PARA001",
        "stockBalQty": 1200,
        "std_disc": 18.00,
        "max_disc": 3.00,
        "expiryDate": "2027-09-30",
        "mrp": 16.81
    },
    {
        "c_item_code": "513556",
        "itemName": "1 PARA 650MG TAB",
        "itemQtyPerBox": 10,
        "batchNo": "PARA002",
        "stockBalQty": 9970,
        "std_disc": 22.00,
        "max_disc": 4.00,
        "expiryDate": "2027-08-20",
        "mrp": 45.00
    },
    {
        "c_item_code": "648538",
        "itemName": "&ME PCOS CRANBERRY DRINK",
        "itemQtyPerBox": 1,
        "batchNo": "3030",
        "stockBalQty": 150,
        "std_disc": 10.00,
        "max_disc": 2.00,
        "expiryDate": "2027-07-01",
        "mrp": 170.00
    },
    {
        "c_item_code": "I00099",
        "itemName": "AMOXICILLIN 500MG - OUT OF STOCK",
        "itemQtyPerBox": 10,
        "batchNo": "AMX001",
        "stockBalQty": 0,
        "std_disc": 20.00,
        "max_disc": 5.00,
        "expiryDate": "2027-06-30",
        "mrp": 45.50
    },
    {
        "c_item_code": "I00077",
        "itemName": "IBUPROFEN 400MG - EXPIRED",
        "itemQtyPerBox": 10,
        "batchNo": "IBU001",
        "stockBalQty": 500,
        "std_disc": 15.00,
        "max_disc": 3.00,
        "expiryDate": "2027-01-15",
        "mrp": 12.50
    },
     {
    "c_item_code": "I00101",
    "itemName": "CETIRIZINE 10MG",
    "itemQtyPerBox": 10,
    "batchNo": "CET001",
    "stockBalQty": 850,
    "std_disc": 18.00,
    "max_disc": 3.00,
    "expiryDate": "2028-03-12",
    "mrp": 22.50
  },
  {
    "c_item_code": "I00102",
    "itemName": "AZITHROMYCIN 500MG",
    "itemQtyPerBox": 5,
    "batchNo": "AZI001",
    "stockBalQty": 420,
    "std_disc": 20.00,
    "max_disc": 5.00,
    "expiryDate": "2028-01-10",
    "mrp": 98.75
  },
  {
    "c_item_code": "I00103",
    "itemName": "VITAMIN C 500MG",
    "itemQtyPerBox": 20,
    "batchNo": "VITC01",
    "stockBalQty": 760,
    "std_disc": 12.00,
    "max_disc": 2.00,
    "expiryDate": "2028-05-20",
    "mrp": 55.00
  },
  {
    "c_item_code": "I00104",
    "itemName": "OMEPRAZOLE 20MG",
    "itemQtyPerBox": 15,
    "batchNo": "OME001",
    "stockBalQty": 640,
    "std_disc": 17.00,
    "max_disc": 4.00,
    "expiryDate": "2027-11-18",
    "mrp": 68.90
  },
  {
    "c_item_code": "I00105",
    "itemName": "METFORMIN 500MG",
    "itemQtyPerBox": 15,
    "batchNo": "MET001",
    "stockBalQty": 950,
    "std_disc": 19.00,
    "max_disc": 5.00,
    "expiryDate": "2028-02-25",
    "mrp": 72.40
  },
  {
    "c_item_code": "I00106",
    "itemName": "ORS POWDER",
    "itemQtyPerBox": 1,
    "batchNo": "ORS001",
    "stockBalQty": 300,
    "std_disc": 8.00,
    "max_disc": 1.00,
    "expiryDate": "2027-09-15",
    "mrp": 18.00
  },
  {
    "c_item_code": "I00107",
    "itemName": "DOXYCYCLINE 100MG",
    "itemQtyPerBox": 10,
    "batchNo": "DOX001",
    "stockBalQty": 520,
    "std_disc": 21.00,
    "max_disc": 5.00,
    "expiryDate": "2028-04-08",
    "mrp": 88.00
  },
  {
    "c_item_code": "I00108",
    "itemName": "PANTOPRAZOLE 40MG",
    "itemQtyPerBox": 10,
    "batchNo": "PAN001",
    "stockBalQty": 430,
    "std_disc": 16.00,
    "max_disc": 3.00,
    "expiryDate": "2027-12-20",
    "mrp": 105.50
  },
  {
    "c_item_code": "I00109",
    "itemName": "MULTIVITAMIN CAPSULE",
    "itemQtyPerBox": 30,
    "batchNo": "MVC001",
    "stockBalQty": 700,
    "std_disc": 14.00,
    "max_disc": 2.00,
    "expiryDate": "2028-06-14",
    "mrp": 145.00
  },
  {
    "c_item_code": "I00110",
    "itemName": "CALCIUM + VIT D3",
    "itemQtyPerBox": 15,
    "batchNo": "CAL001",
    "stockBalQty": 610,
    "std_disc": 13.00,
    "max_disc": 2.50,
    "expiryDate": "2028-01-30",
    "mrp": 132.75
  },
  {
    "c_item_code": "I00111",
    "itemName": "LEVOCETIRIZINE SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "LEV001",
    "stockBalQty": 275,
    "std_disc": 11.00,
    "max_disc": 1.50,
    "expiryDate": "2027-10-05",
    "mrp": 68.00
  },
  {
    "c_item_code": "I00112",
    "itemName": "RANITIDINE 150MG",
    "itemQtyPerBox": 10,
    "batchNo": "RAN001",
    "stockBalQty": 390,
    "std_disc": 18.00,
    "max_disc": 4.00,
    "expiryDate": "2028-03-01",
    "mrp": 48.60
  },
  {
    "c_item_code": "I00113",
    "itemName": "CIPROFLOXACIN 500MG",
    "itemQtyPerBox": 10,
    "batchNo": "CIP001",
    "stockBalQty": 460,
    "std_disc": 22.00,
    "max_disc": 5.00,
    "expiryDate": "2028-07-12",
    "mrp": 96.50
  },
  {
    "c_item_code": "I00114",
    "itemName": "LOSARTAN 50MG",
    "itemQtyPerBox": 15,
    "batchNo": "LOS001",
    "stockBalQty": 720,
    "std_disc": 17.00,
    "max_disc": 4.00,
    "expiryDate": "2028-05-25",
    "mrp": 124.00
  },
  {
    "c_item_code": "I00115",
    "itemName": "ATORVASTATIN 10MG",
    "itemQtyPerBox": 10,
    "batchNo": "ATO001",
    "stockBalQty": 540,
    "std_disc": 16.00,
    "max_disc": 3.50,
    "expiryDate": "2028-08-10",
    "mrp": 138.25
  },
  {
    "c_item_code": "I00116",
    "itemName": "TELMISARTAN 40MG",
    "itemQtyPerBox": 10,
    "batchNo": "TEL001",
    "stockBalQty": 610,
    "std_disc": 18.00,
    "max_disc": 4.50,
    "expiryDate": "2028-02-15",
    "mrp": 165.00
  },
  {
    "c_item_code": "I00117",
    "itemName": "GLIMEPIRIDE 2MG",
    "itemQtyPerBox": 10,
    "batchNo": "GLI001",
    "stockBalQty": 450,
    "std_disc": 15.00,
    "max_disc": 3.00,
    "expiryDate": "2027-12-28",
    "mrp": 84.40
  },
  {
    "c_item_code": "I00118",
    "itemName": "MONTELUKAST 10MG",
    "itemQtyPerBox": 10,
    "batchNo": "MON001",
    "stockBalQty": 380,
    "std_disc": 19.00,
    "max_disc": 4.00,
    "expiryDate": "2028-04-22",
    "mrp": 112.90
  },
  {
    "c_item_code": "I00119",
    "itemName": "ZINCOVIT TABLET",
    "itemQtyPerBox": 15,
    "batchNo": "ZIN001",
    "stockBalQty": 930,
    "std_disc": 14.00,
    "max_disc": 2.50,
    "expiryDate": "2028-01-19",
    "mrp": 95.00
  },
  {
    "c_item_code": "I00120",
    "itemName": "B-COMPLEX CAPSULE",
    "itemQtyPerBox": 20,
    "batchNo": "BCX001",
    "stockBalQty": 810,
    "std_disc": 12.00,
    "max_disc": 2.00,
    "expiryDate": "2028-06-30",
    "mrp": 76.25
  },
  {
    "c_item_code": "I00121",
    "itemName": "DICLOFENAC GEL",
    "itemQtyPerBox": 1,
    "batchNo": "DIC001",
    "stockBalQty": 250,
    "std_disc": 10.00,
    "max_disc": 2.00,
    "expiryDate": "2027-11-05",
    "mrp": 89.00
  },
  {
    "c_item_code": "I00122",
    "itemName": "COLD RELIEF SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "CRS001",
    "stockBalQty": 310,
    "std_disc": 13.00,
    "max_disc": 2.00,
    "expiryDate": "2027-10-14",
    "mrp": 65.75
  },
  {
    "c_item_code": "I00123",
    "itemName": "INSULIN GLARGINE",
    "itemQtyPerBox": 1,
    "batchNo": "INS001",
    "stockBalQty": 120,
    "std_disc": 8.00,
    "max_disc": 1.50,
    "expiryDate": "2027-09-09",
    "mrp": 685.00
  },
  {
    "c_item_code": "I00124",
    "itemName": "CEFIXIME 200MG",
    "itemQtyPerBox": 10,
    "batchNo": "CEF001",
    "stockBalQty": 470,
    "std_disc": 21.00,
    "max_disc": 5.00,
    "expiryDate": "2028-03-17",
    "mrp": 142.80
  },
  {
    "c_item_code": "I00125",
    "itemName": "ANTI FUNGAL CREAM",
    "itemQtyPerBox": 1,
    "batchNo": "AFC001",
    "stockBalQty": 290,
    "std_disc": 11.00,
    "max_disc": 2.00,
    "expiryDate": "2027-12-11",
    "mrp": 78.50
  },
  {
    "c_item_code": "I00126",
    "itemName": "DIGESTIVE ENZYME SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "DES001",
    "stockBalQty": 180,
    "std_disc": 9.00,
    "max_disc": 1.50,
    "expiryDate": "2027-08-27",
    "mrp": 110.00
  },
  {
    "c_item_code": "I00127",
    "itemName": "IRON + FOLIC ACID",
    "itemQtyPerBox": 30,
    "batchNo": "IFA001",
    "stockBalQty": 660,
    "std_disc": 15.00,
    "max_disc": 3.00,
    "expiryDate": "2028-05-08",
    "mrp": 98.20
  },
  {
    "c_item_code": "I00113",
    "itemName": "CIPROFLOXACIN 500MG",
    "itemQtyPerBox": 10,
    "batchNo": "CIP001",
    "stockBalQty": 460,
    "std_disc": 22.00,
    "max_disc": 5.00,
    "expiryDate": "2028-07-12",
    "mrp": 96.50
  },
  {
    "c_item_code": "I00114",
    "itemName": "LOSARTAN 50MG",
    "itemQtyPerBox": 15,
    "batchNo": "LOS001",
    "stockBalQty": 720,
    "std_disc": 17.00,
    "max_disc": 4.00,
    "expiryDate": "2028-05-25",
    "mrp": 124.00
  },
  {
    "c_item_code": "I00115",
    "itemName": "ATORVASTATIN 10MG",
    "itemQtyPerBox": 10,
    "batchNo": "ATO001",
    "stockBalQty": 540,
    "std_disc": 16.00,
    "max_disc": 3.50,
    "expiryDate": "2028-08-10",
    "mrp": 138.25
  },
  {
    "c_item_code": "I00116",
    "itemName": "TELMISARTAN 40MG",
    "itemQtyPerBox": 10,
    "batchNo": "TEL001",
    "stockBalQty": 610,
    "std_disc": 18.00,
    "max_disc": 4.50,
    "expiryDate": "2028-02-15",
    "mrp": 165.00
  },
  {
    "c_item_code": "I00117",
    "itemName": "GLIMEPIRIDE 2MG",
    "itemQtyPerBox": 10,
    "batchNo": "GLI001",
    "stockBalQty": 450,
    "std_disc": 15.00,
    "max_disc": 3.00,
    "expiryDate": "2027-12-28",
    "mrp": 84.40
  },
  {
    "c_item_code": "I00118",
    "itemName": "MONTELUKAST 10MG",
    "itemQtyPerBox": 10,
    "batchNo": "MON001",
    "stockBalQty": 380,
    "std_disc": 19.00,
    "max_disc": 4.00,
    "expiryDate": "2028-04-22",
    "mrp": 112.90
  },
  {
    "c_item_code": "I00119",
    "itemName": "ZINCOVIT TABLET",
    "itemQtyPerBox": 15,
    "batchNo": "ZIN001",
    "stockBalQty": 930,
    "std_disc": 14.00,
    "max_disc": 2.50,
    "expiryDate": "2028-01-19",
    "mrp": 95.00
  },
  {
    "c_item_code": "I00120",
    "itemName": "B-COMPLEX CAPSULE",
    "itemQtyPerBox": 20,
    "batchNo": "BCX001",
    "stockBalQty": 810,
    "std_disc": 12.00,
    "max_disc": 2.00,
    "expiryDate": "2028-06-30",
    "mrp": 76.25
  },
  {
    "c_item_code": "I00121",
    "itemName": "DICLOFENAC GEL",
    "itemQtyPerBox": 1,
    "batchNo": "DIC001",
    "stockBalQty": 250,
    "std_disc": 10.00,
    "max_disc": 2.00,
    "expiryDate": "2027-11-05",
    "mrp": 89.00
  },
  {
    "c_item_code": "I00122",
    "itemName": "COLD RELIEF SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "CRS001",
    "stockBalQty": 310,
    "std_disc": 13.00,
    "max_disc": 2.00,
    "expiryDate": "2027-10-14",
    "mrp": 65.75
  },
  {
    "c_item_code": "I00123",
    "itemName": "INSULIN GLARGINE",
    "itemQtyPerBox": 1,
    "batchNo": "INS001",
    "stockBalQty": 120,
    "std_disc": 8.00,
    "max_disc": 1.50,
    "expiryDate": "2027-09-09",
    "mrp": 685.00
  },
  {
    "c_item_code": "I00124",
    "itemName": "CEFIXIME 200MG",
    "itemQtyPerBox": 10,
    "batchNo": "CEF001",
    "stockBalQty": 470,
    "std_disc": 21.00,
    "max_disc": 5.00,
    "expiryDate": "2028-03-17",
    "mrp": 142.80
  },
  {
    "c_item_code": "I00125",
    "itemName": "ANTI FUNGAL CREAM",
    "itemQtyPerBox": 1,
    "batchNo": "AFC001",
    "stockBalQty": 290,
    "std_disc": 11.00,
    "max_disc": 2.00,
    "expiryDate": "2027-12-11",
    "mrp": 78.50
  },
  {
    "c_item_code": "I00126",
    "itemName": "DIGESTIVE ENZYME SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "DES001",
    "stockBalQty": 180,
    "std_disc": 9.00,
    "max_disc": 1.50,
    "expiryDate": "2027-08-27",
    "mrp": 110.00
  },
  {
    "c_item_code": "I00127",
    "itemName": "IRON + FOLIC ACID",
    "itemQtyPerBox": 30,
    "batchNo": "IFA001",
    "stockBalQty": 660,
    "std_disc": 15.00,
    "max_disc": 3.00,
    "expiryDate": "2028-05-08",
    "mrp": 98.20
  },
  {
    "c_item_code": "I00128",
    "itemName": "DOLO 650MG TAB",
    "itemQtyPerBox": 15,
    "batchNo": "DOL6501",
    "stockBalQty": 1450,
    "std_disc": 23.00,
    "max_disc": 5.00,
    "expiryDate": "2028-08-14",
    "mrp": 32.50
  },
  {
    "c_item_code": "I00129",
    "itemName": "PREGABALIN 75MG",
    "itemQtyPerBox": 10,
    "batchNo": "PRE001",
    "stockBalQty": 320,
    "std_disc": 17.00,
    "max_disc": 4.00,
    "expiryDate": "2028-02-09",
    "mrp": 185.75
  },
  {
    "c_item_code": "I00130",
    "itemName": "LEVOTHYROXINE 50MCG",
    "itemQtyPerBox": 20,
    "batchNo": "LEV050",
    "stockBalQty": 840,
    "std_disc": 14.00,
    "max_disc": 3.00,
    "expiryDate": "2028-07-01",
    "mrp": 128.40
  },
  {
    "c_item_code": "I00131",
    "itemName": "ALBENDAZOLE 400MG",
    "itemQtyPerBox": 1,
    "batchNo": "ALB001",
    "stockBalQty": 270,
    "std_disc": 12.00,
    "max_disc": 2.00,
    "expiryDate": "2027-11-23",
    "mrp": 18.90
  },
  {
    "c_item_code": "I00132",
    "itemName": "ONDANSETRON 4MG",
    "itemQtyPerBox": 10,
    "batchNo": "OND001",
    "stockBalQty": 510,
    "std_disc": 19.00,
    "max_disc": 4.00,
    "expiryDate": "2028-03-30",
    "mrp": 56.25
  },
  {
    "c_item_code": "I00133",
    "itemName": "LORATADINE 10MG",
    "itemQtyPerBox": 10,
    "batchNo": "LOR001",
    "stockBalQty": 690,
    "std_disc": 15.00,
    "max_disc": 3.00,
    "expiryDate": "2028-05-17",
    "mrp": 42.80
  },
  {
    "c_item_code": "I00134",
    "itemName": "ACECLOFENAC + PARACETAMOL",
    "itemQtyPerBox": 10,
    "batchNo": "ACP001",
    "stockBalQty": 580,
    "std_disc": 20.00,
    "max_disc": 5.00,
    "expiryDate": "2028-01-21",
    "mrp": 74.50
  },
  {
    "c_item_code": "I00135",
    "itemName": "AMLODIPINE 5MG",
    "itemQtyPerBox": 15,
    "batchNo": "AML001",
    "stockBalQty": 760,
    "std_disc": 16.00,
    "max_disc": 3.50,
    "expiryDate": "2028-04-11",
    "mrp": 66.00
  },
  {
    "c_item_code": "I00136",
    "itemName": "NEUROBION FORTE",
    "itemQtyPerBox": 30,
    "batchNo": "NEU001",
    "stockBalQty": 420,
    "std_disc": 13.00,
    "max_disc": 2.50,
    "expiryDate": "2028-06-26",
    "mrp": 195.00
  },
  {
    "c_item_code": "I00137",
    "itemName": "LACTIC ACID BACILLUS CAPSULE",
    "itemQtyPerBox": 10,
    "batchNo": "LAB001",
    "stockBalQty": 310,
    "std_disc": 11.00,
    "max_disc": 2.00,
    "expiryDate": "2027-10-08",
    "mrp": 58.75
  },
  {
    "c_item_code": "I00138",
    "itemName": "COUGH EXPECTORANT SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "CES001",
    "stockBalQty": 225,
    "std_disc": 10.00,
    "max_disc": 2.00,
    "expiryDate": "2027-12-19",
    "mrp": 72.00
  },
  {
    "c_item_code": "I00139",
    "itemName": "HYDROXYZINE 25MG",
    "itemQtyPerBox": 10,
    "batchNo": "HYD001",
    "stockBalQty": 295,
    "std_disc": 14.00,
    "max_disc": 3.00,
    "expiryDate": "2028-02-28",
    "mrp": 48.90
  },
  {
    "c_item_code": "I00140",
    "itemName": "BETADINE OINTMENT",
    "itemQtyPerBox": 1,
    "batchNo": "BET001",
    "stockBalQty": 340,
    "std_disc": 9.00,
    "max_disc": 1.50,
    "expiryDate": "2027-09-25",
    "mrp": 95.00
  },
  {
    "c_item_code": "I00141",
    "itemName": "CALPOL 500MG",
    "itemQtyPerBox": 15,
    "batchNo": "CAL001",
    "stockBalQty": 1180,
    "std_disc": 21.00,
    "max_disc": 4.00,
    "expiryDate": "2028-07-09",
    "mrp": 34.75
  },
  {
    "c_item_code": "I00142",
    "itemName": "RABEPRAZOLE 20MG",
    "itemQtyPerBox": 10,
    "batchNo": "RAB001",
    "stockBalQty": 505,
    "std_disc": 18.00,
    "max_disc": 4.00,
    "expiryDate": "2028-03-05",
    "mrp": 118.60
  },
  {
    "c_item_code": "I00143",
    "itemName": "MEFTAL SPAS",
    "itemQtyPerBox": 10,
    "batchNo": "MFS001",
    "stockBalQty": 640,
    "std_disc": 20.00,
    "max_disc": 4.00,
    "expiryDate": "2028-06-18",
    "mrp": 52.40
  },
  {
    "c_item_code": "I00144",
    "itemName": "PAN-D CAPSULE",
    "itemQtyPerBox": 15,
    "batchNo": "PAND01",
    "stockBalQty": 730,
    "std_disc": 18.00,
    "max_disc": 4.00,
    "expiryDate": "2028-01-29",
    "mrp": 145.80
  },
  {
    "c_item_code": "I00145",
    "itemName": "ECOSPRIN 75MG",
    "itemQtyPerBox": 14,
    "batchNo": "ECO001",
    "stockBalQty": 580,
    "std_disc": 15.00,
    "max_disc": 3.00,
    "expiryDate": "2028-05-10",
    "mrp": 34.60
  },
  {
    "c_item_code": "I00146",
    "itemName": "CLAVAM 625MG",
    "itemQtyPerBox": 10,
    "batchNo": "CLV001",
    "stockBalQty": 410,
    "std_disc": 22.00,
    "max_disc": 5.00,
    "expiryDate": "2028-04-16",
    "mrp": 198.90
  },
  {
    "c_item_code": "I00147",
    "itemName": "DERMICOOL POWDER",
    "itemQtyPerBox": 1,
    "batchNo": "DER001",
    "stockBalQty": 360,
    "std_disc": 11.00,
    "max_disc": 2.00,
    "expiryDate": "2027-11-12",
    "mrp": 78.25
  },
  {
    "c_item_code": "I00148",
    "itemName": "BENADRYL COUGH SYRUP",
    "itemQtyPerBox": 1,
    "batchNo": "BEN001",
    "stockBalQty": 295,
    "std_disc": 10.00,
    "max_disc": 1.50,
    "expiryDate": "2027-10-04",
    "mrp": 96.00
  },
  {
    "c_item_code": "I00149",
    "itemName": "MONOCEF-O 200MG",
    "itemQtyPerBox": 10,
    "batchNo": "MON001",
    "stockBalQty": 330,
    "std_disc": 21.00,
    "max_disc": 5.00,
    "expiryDate": "2028-02-22",
    "mrp": 176.50
  },
  {
    "c_item_code": "I00150",
    "itemName": "AUGMENTIN 625MG",
    "itemQtyPerBox": 10,
    "batchNo": "AUG001",
    "stockBalQty": 275,
    "std_disc": 20.00,
    "max_disc": 5.00,
    "expiryDate": "2028-03-13",
    "mrp": 214.00
  },
  {
    "c_item_code": "I00151",
    "itemName": "VOLINI SPRAY",
    "itemQtyPerBox": 1,
    "batchNo": "VOL001",
    "stockBalQty": 185,
    "std_disc": 9.00,
    "max_disc": 1.50,
    "expiryDate": "2027-12-30",
    "mrp": 165.75
  },
  {
    "c_item_code": "I00152",
    "itemName": "DIGENE GEL",
    "itemQtyPerBox": 1,
    "batchNo": "DIG001",
    "stockBalQty": 410,
    "std_disc": 12.00,
    "max_disc": 2.50,
    "expiryDate": "2028-01-08",
    "mrp": 115.40
  },
  {
    "c_item_code": "I00153",
    "itemName": "ENO FRUIT SALT",
    "itemQtyPerBox": 1,
    "batchNo": "ENO001",
    "stockBalQty": 520,
    "std_disc": 8.00,
    "max_disc": 1.00,
    "expiryDate": "2027-09-14",
    "mrp": 18.50
  },
  {
    "c_item_code": "I00154",
    "itemName": "VICKS VAPORUB",
    "itemQtyPerBox": 1,
    "batchNo": "VIC001",
    "stockBalQty": 610,
    "std_disc": 10.00,
    "max_disc": 2.00,
    "expiryDate": "2028-05-27",
    "mrp": 72.90
  },
  {
    "c_item_code": "I00155",
    "itemName": "MOOV PAIN RELIEF CREAM",
    "itemQtyPerBox": 1,
    "batchNo": "MOV001",
    "stockBalQty": 245,
    "std_disc": 9.00,
    "max_disc": 1.50,
    "expiryDate": "2027-11-07",
    "mrp": 132.00
  },
  {
    "c_item_code": "I00156",
    "itemName": "CROCIN ADVANCE",
    "itemQtyPerBox": 15,
    "batchNo": "CRC001",
    "stockBalQty": 980,
    "std_disc": 19.00,
    "max_disc": 4.00,
    "expiryDate": "2028-08-03",
    "mrp": 36.80
  },
  {
    "c_item_code": "I00157",
    "itemName": "ORS ELECTROLYTE DRINK",
    "itemQtyPerBox": 1,
    "batchNo": "ORSD01",
    "stockBalQty": 300,
    "std_disc": 7.00,
    "max_disc": 1.00,
    "expiryDate": "2027-10-20",
    "mrp": 24.00
  }

]

# Stock Data
STOCK = [
    {
        "itemCode": "I00017",
        "itemName": "AMALGIN",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 1,
        "totalBalLsQty": 2000,
        "packQty": 2000,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-12-08 16:57:25.162"
    },
    {
        "itemCode": "513556",
        "itemName": "1 PARA 650MG TAB",
        "contCode": "P008",
        "contName": "PARACETAMOL",
        "qtyBox": 10,
        "totalBalLsQty": 9970,
        "packQty": 997,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-08-11 16:39:41.296"
    },
    {
        "itemCode": "I00003",
        "itemName": "DOLO 250MG SUSP",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 1,
        "totalBalLsQty": 984,
        "packQty": 984,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-11-01 10:00:00.000"
    },
    {
        "itemCode": "I00049",
        "itemName": "ASPIRIN 500MG",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 5,
        "totalBalLsQty": 500,
        "packQty": 50,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-10-15 12:00:00.000"
    },
    {
        "itemCode": "I00048",
        "itemName": "PARACETAMOL 650MG",
        "contCode": "P008",
        "contName": "PARACETAMOL",
        "qtyBox": 10,
        "totalBalLsQty": 1200,
        "packQty": 120,
        "looseQty": 0,
        "lastModifiedDateTime": "2025-09-30 14:00:00.000"
    },
    {
        "itemCode": "648538",
        "itemName": "&ME PCOS CRANBERRY DRINK",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 150,
        "totalBalLsQty": 150,
        "packQty": 150,
        "looseQty": 0,
        "lastModifiedDateTime": "2027-07-01 10:00:00.000"
    },
    {
        "itemCode": "I00099",
        "itemName": "AMOXICILLIN 500MG - OUT OF STOCK",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 10,
        "totalBalLsQty": 0,
        "packQty": 0,
        "looseQty": 0,
        "lastModifiedDateTime": "2026-03-10 10:00:00.000"
    },
    {
        "itemCode": "I00077",
        "itemName": "IBUPROFEN 400MG - EXPIRED",
        "contCode": "-",
        "contName": "-",
        "qtyBox": 10,
        "totalBalLsQty": 500,
        "packQty": 50,
        "looseQty": 0,
        "lastModifiedDateTime": "2027-01-15 10:00:00.000"
    }
]

# Orders storage
ORDERS = {
    "aditya001": {
        "orderId": "aditya001",
        "custCode": "GC01",
        "customerName": "Lawrence Nadar",
        "fromGstNo": "07NQQAE5107K2ZW",
        "toGstNo": "07NQQAE5107K2ZW",
        "customerType": "Un - Registered",
        "doctorName": "-",
        "documentPk": "24001540035",
        "brCode": "001",
        "tranYear": "24",
        "tranPrefix": "6",
        "tranSrno": "35",
        "createdDate": "2024-07-24",
        "billTotal": "254.18",
        "invoices": [
            {
                "docNo": "001/25/S/105",
                "docDate": "2025-09-20",
                "docStatus": "Invoice Created",
                "createdBy": "MYBOSS",
                "docDiscount": "0.00",
                "docTotal": "106.00",
                "detail": [
                    {
                        "productId": "648538",
                        "productName": "&ME PCOS CRANBERRY DRINK",
                        "hsnCode": "21069099",
                        "qtyPerBox": "1",
                        "batch": "3030",
                        "qty": "1.000",
                        "expiryDate": "2027-07-01",
                        "mrp": "170.000",
                        "saleRate": "90.000",
                        "discAmt": "0.00",
                        "discPer": "0.00",
                        "itemTotal": "170.000000",
                        "cgstPer": "0.00",
                        "cgstAmt": "0.00",
                        "sgstPer": "0.00",
                        "sgstAmt": "0.00",
                        "igstPer": "18.00",
                        "igstAmt": "16.20",
                        "cessPer": "0.00",
                        "cessAmt": "0.00"
                    }
                ]
            }
        ]
    },
    "00120260422110652A765CAD1": {
        "orderId": "00120260422110652A765CAD1",
        "custCode": "GC02",
        "customerName": "Test Retailer",
        "fromGstNo": "07NQQAE5107K2ZW",
        "toGstNo": "07NQQAE5107K2ZW",
        "customerType": "Un - Registered",
        "doctorName": "-",
        "documentPk": "26001540100",
        "brCode": "001",
        "tranYear": "26",
        "tranPrefix": "6",
        "tranSrno": "100",
        "createdDate": "2026-04-27",
        "billTotal": "542.50",
        "invoices": [
            {
                "docNo": "001/26/S/250",
                "docDate": "2026-04-27",
                "docStatus": "Invoice Created",
                "createdBy": "SYSTEM",
                "docDiscount": "0.00",
                "docTotal": "542.50",
                "detail": [
                    {
                        "productId": "I00003",
                        "productName": "DOLO 250MG SUSP",
                        "hsnCode": "30049090",
                        "qtyPerBox": "1",
                        "batch": "DOLN096",
                        "qty": "10.000",
                        "expiryDate": "2027-11-01",
                        "mrp": "75.030",
                        "saleRate": "56.270",
                        "discAmt": "188.30",
                        "discPer": "25.00",
                        "itemTotal": "562.700",
                        "cgstPer": "0.00",
                        "cgstAmt": "0.00",
                        "sgstPer": "0.00",
                        "sgstAmt": "0.00",
                        "igstPer": "5.00",
                        "igstAmt": "28.14",
                        "cessPer": "0.00",
                        "cessAmt": "0.00"
                    },
                    {
                        "productId": "I00017",
                        "productName": "AMALGIN",
                        "hsnCode": "30049099",
                        "qtyPerBox": "1",
                        "batch": "AMG001",
                        "qty": "5.000",
                        "expiryDate": "2027-12-01",
                        "mrp": "85.500",
                        "saleRate": "72.675",
                        "discAmt": "64.13",
                        "discPer": "15.00",
                        "itemTotal": "363.375",
                        "cgstPer": "0.00",
                        "cgstAmt": "0.00",
                        "sgstPer": "0.00",
                        "sgstAmt": "0.00",
                        "igstPer": "5.00",
                        "igstAmt": "18.17",
                        "cessPer": "0.00",
                        "cessAmt": "0.00"
                    }
                ]
            }
        ]
    },
    "TEST-COD-34BE5317": {
        "orderId": "TEST-COD-34BE5317",
        "custCode": "GC02",
        "customerName": "Test Retailer COD",
        "fromGstNo": "07NQQAE5107K2ZW",
        "toGstNo": "07NQQAE5107K2ZW",
        "customerType": "Un - Registered",
        "doctorName": "-",
        "documentPk": "26001540101",
        "brCode": "001",
        "tranYear": "26",
        "tranPrefix": "6",
        "tranSrno": "101",
        "createdDate": "2026-04-28",
        "billTotal": "542.50",
        "invoices": [
            {
                "docNo": "001/26/S/999",
                "docDate": "2026-04-28",
                "docStatus": "Invoice Created",
                "createdBy": "SYSTEM",
                "docDiscount": "0.00",
                "docTotal": "542.50",
                "detail": [
                    {
                        "productId": "I00003",
                        "productName": "DOLO 250MG SUSP",
                        "hsnCode": "30049090",
                        "qtyPerBox": "1",
                        "batch": "DOLN096",
                        "qty": "10.000",
                        "expiryDate": "2027-11-01",
                        "mrp": "75.030",
                        "saleRate": "56.270",
                        "discAmt": "188.30",
                        "discPer": "25.00",
                        "itemTotal": "562.700",
                        "cgstPer": "0.00",
                        "cgstAmt": "0.00",
                        "sgstPer": "0.00",
                        "sgstAmt": "0.00",
                        "igstPer": "5.00",
                        "igstAmt": "28.14",
                        "cessPer": "0.00",
                        "cessAmt": "0.00"
                    },
                    {
                        "productId": "I00017",
                        "productName": "AMALGIN",
                        "hsnCode": "30049099",
                        "qtyPerBox": "1",
                        "batch": "AMG001",
                        "qty": "5.000",
                        "expiryDate": "2027-12-01",
                        "mrp": "85.500",
                        "saleRate": "72.675",
                        "discAmt": "64.13",
                        "discPer": "15.00",
                        "itemTotal": "363.375",
                        "cgstPer": "0.00",
                        "cgstAmt": "0.00",
                        "sgstPer": "0.00",
                        "sgstAmt": "0.00",
                        "igstPer": "5.00",
                        "igstAmt": "18.17",
                        "cessPer": "0.00",
                        "cessAmt": "0.00"
                    }
                ]
            }
        ]
    }
}

# Customers storage
CUSTOMERS = {
    "GC01": {
        "code": "GC01",
        "ipName": "Lawrence Nadar",
        "mail": "lawrence@pharmacy.com",
        "gender": "M",
        "city": "Mumbai",
        "ipState": "Maharashtra"
    }
}

# Order counter for generating document numbers
ORDER_COUNTER = 100


# ==================== API ENDPOINTS ====================

@app.route('/ws_c2_services_generate_token', methods=['GET', 'POST'])
def generate_token():
    """Generate API Token"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        c2_code = data.get('c2Code')
        store_id = data.get('storeId')
        prod_code = data.get('prodCode', '02')
        security_key = data.get('securityKey')
        
        if not all([c2_code, store_id, security_key]):
            return jsonify({
                "code": "400",
                "type": "generateToken",
                "message": "Missing required parameters"
            }), 400
        
        # Generate API key
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        api_key = base64.b64encode(f"{c2_code}{store_id}^{timestamp}".encode()).decode()
        
        # Store token
        API_TOKENS[api_key] = {
            "c2_code": c2_code,
            "store_id": store_id,
            "created_at": timestamp
        }
        
        print(f"[TOKEN] Generated for {c2_code}: {api_key}")
        
        return jsonify({
            "code": "200",
            "type": "generateToken",
            "apiKey": api_key
        })
    except Exception as e:
        return jsonify({
            "code": "500",
            "type": "generateToken",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_get_master_data', methods=['GET', 'POST'])
def get_master_data():
    """Get Item Master Data"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        api_key = data.get('apiKey')
        index_id = data.get('indexId')
        
        # For testing, accept any API key or check if it exists
        # In production, validate properly
        
        print(f"[MASTER DATA] Request received with apiKey: {api_key[:20] if api_key else 'None'}...")
        
        response_data = ITEMS
        
        # Filter by indexId if provided
        if index_id:
            try:
                idx = int(index_id)
                if 0 <= idx < len(ITEMS):
                    response_data = [ITEMS[idx]]
            except ValueError:
                pass
        
        return jsonify({
            "code": "200",
            "type": "getMasterData",
            "data": response_data
        })
    except Exception as e:
        return jsonify({
            "code": "400",
            "type": "getMasterData",
            "message": str(e)
        }), 400


@app.route('/ws_c2_services_fetch_stock', methods=['GET', 'POST'])
def fetch_stock():
    """Fetch Stock Data"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        api_key = data.get('apiKey')
        store_id = data.get('storeId')
        
        print(f"[STOCK] Request for store: {store_id}")
        
        return jsonify(STOCK)
    except Exception as e:
        return jsonify({
            "code": "500",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_create_sale_order', methods=['POST'])
def create_sale_order():
    """Create Sales Order"""
    global ORDER_COUNTER
    
    try:
        data = request.get_json()
        
        api_key = data.get('apiKey')
        order_id = data.get('orderId')
        patient_name = data.get('patientName')
        order_total = data.get('orderTotal')
        material_info = data.get('materialInfo', [])
        
        print(f"[ORDER] Creating order {order_id} for {patient_name}")
        
        # Generate document number
        ORDER_COUNTER += 1
        year = datetime.now().strftime("%y")
        doc_pk = f"{year}001540{ORDER_COUNTER:03d}"
        
        # Store order
        order_data = {
            "orderId": str(order_id),
            "custCode": data.get('actCode', 'GC01'),
            "customerName": data.get('actName', patient_name),
            "fromGstNo": "07NQQAE5107K2ZW",
            "toGstNo": "07NQQAE5107K2ZW",
            "customerType": "Un - Registered",
            "doctorName": data.get('drName', '-'),
            "documentPk": doc_pk,
            "brCode": data.get('storeId', '001'),
            "tranYear": year,
            "tranPrefix": "6",
            "tranSrno": str(ORDER_COUNTER),
            "createdDate": data.get('ordDate', datetime.now().strftime("%Y-%m-%d")),
            "billTotal": str(order_total),
            "invoices": []
        }
        
        ORDERS[str(order_id)] = order_data
        
        return jsonify({
            "code": "200",
            "type": "SaleOrderCreate",
            "message": f"Document No. : {doc_pk} successfully processed.",
            "documentDetails": [{
                "brCode": order_data["brCode"],
                "tranYear": order_data["tranYear"],
                "tranPrefix": order_data["tranPrefix"],
                "tranSrno": order_data["tranSrno"],
                "documentPk": doc_pk,
                "OrderId": order_id,
                "createdDate": order_data["createdDate"],
                "billTotal": order_data["billTotal"]
            }]
        }), 201
    except Exception as e:
        return jsonify({
            "code": "500",
            "type": "SaleOrderCreate",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_gl_cust_creation', methods=['GET', 'POST'])
def create_gl_customer():
    """Create Global Local Customer"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        code = data.get('Code')
        ip_name = data.get('ipName')
        
        if not code:
            return jsonify({
                "code": "400",
                "type": "glcustcreation",
                "message": "LcCode Cannot be Null or empty."
            }), 400
        
        if code in CUSTOMERS:
            return jsonify({
                "code": "400",
                "type": "glcustcreation",
                "message": f"LcCode Already Exists:{code}"
            }), 400
        
        # Store customer
        CUSTOMERS[code] = {
            "code": code,
            "ipName": ip_name,
            "mail": data.get('Mail'),
            "gender": data.get('Gender'),
            "city": data.get('City'),
            "ipState": data.get('ipState'),
            "mobile": data.get('Mobile'),
            "gstNo": data.get('Gstno')
        }
        
        print(f"[CUSTOMER] Created: {code} - {ip_name}")
        
        return jsonify({
            "code": "200",
            "type": "glcustcreation",
            "message": f"Customer Name : {ip_name} with Customer Code : {code} created sucessfully."
        }), 201
    except Exception as e:
        return jsonify({
            "code": "500",
            "type": "glcustcreation",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_get_orderstatus', methods=['GET', 'POST'])
def get_order_status():
    """Get Order Status with Transaction Details"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        order_id = data.get('orderId')
        
        print(f"[ORDER STATUS] Request for order: {order_id}")
        
        if not order_id:
            return jsonify({
                "code": "400",
                "message": "orderId is required"
            }), 400
        
        order = ORDERS.get(str(order_id))
        
        if not order:
            return jsonify({
                "code": "404",
                "message": f"Order {order_id} not found"
            }), 404
        
        return jsonify({
            "code": "200",
            "orderId": order["orderId"],
            "custCode": order["custCode"],
            "fromGstNo": order["fromGstNo"],
            "toGstNo": order["toGstNo"],
            "customerType": order["customerType"],
            "doctorName": order["doctorName"],
            "invoices": order["invoices"]
        })
    except Exception as e:
        return jsonify({
            "code": "500",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_get_invoice', methods=['GET', 'POST'])
def get_invoice():
    """Get Invoice Details for an Order"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        order_id = data.get('orderId')
        doc_no = data.get('docNo')
        
        print(f"[INVOICE] Request for order: {order_id}, doc_no: {doc_no}")
        
        if not order_id:
            return jsonify({
                "code": "400",
                "message": "orderId is required"
            }), 400
        
        order = ORDERS.get(str(order_id))
        
        if not order:
            return jsonify({
                "code": "404",
                "message": f"Order {order_id} not found"
            }), 404
        
        # Get invoices for the order
        invoices = order.get("invoices", [])
        
        if not invoices:
            return jsonify({
                "code": "404",
                "message": f"No invoices found for order {order_id}"
            }), 404
        
        # If specific doc_no requested, filter it
        if doc_no:
            invoices = [inv for inv in invoices if inv.get("docNo") == doc_no]
            if not invoices:
                return jsonify({
                    "code": "404",
                    "message": f"Invoice {doc_no} not found for order {order_id}"
                }), 404
        
        return jsonify({
            "code": "200",
            "orderId": order_id,
            "invoices": invoices
        })
    except Exception as e:
        print(f"[INVOICE ERROR] {str(e)}")
        return jsonify({
            "code": "500",
            "message": str(e)
        }), 500


@app.route('/create_test_invoice', methods=['POST', 'GET'])
def create_test_invoice():
    """Create a test invoice for an order (for testing purposes)"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        order_id = data.get('orderId', '00120260427055141517EC06F')
        doc_no = data.get('docNo', '001/26/S/250')
        doc_total = float(data.get('docTotal', '542.50'))
        
        print(f"[CREATE INVOICE] Creating invoice for order: {order_id}, doc_no: {doc_no}")
        
        # Create or update order if it doesn't exist
        if str(order_id) not in ORDERS:
            ORDERS[str(order_id)] = {
                "orderId": str(order_id),
                "custCode": "GC02",
                "customerName": "Test Retailer",
                "fromGstNo": "07NQQAE5107K2ZW",
                "toGstNo": "07NQQAE5107K2ZW",
                "customerType": "Un - Registered",
                "doctorName": "-",
                "documentPk": "26001540100",
                "brCode": "001",
                "tranYear": "26",
                "tranPrefix": "6",
                "tranSrno": "100",
                "createdDate": datetime.now().strftime("%Y-%m-%d"),
                "billTotal": str(doc_total),
                "invoices": []
            }
        
        # Create invoice object
        invoice = {
            "docNo": doc_no,
            "docDate": datetime.now().strftime("%Y-%m-%d"),
            "docStatus": "Invoice Created",
            "createdBy": "SYSTEM",
            "docDiscount": "0.00",
            "docTotal": str(doc_total),
            "detail": []
        }
        
        # Try to fetch real items from local Django DB
        try:
            import os
            import sys
            import django
            if 'DJANGO_SETTINGS_MODULE' not in os.environ:
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')
                django.setup()
            
            from dreamspharmaapp.models import SalesOrder
            sales_order = SalesOrder.objects.get(order_id=order_id)
            
            detail_items = []
            for item in sales_order.items.all():
                detail_items.append({
                    "productId": item.item_code or "TEST_PRD",
                    "productName": item.item_name or "Test Product",
                    "hsnCode": item.hsn_code or "30049090",
                    "qtyPerBox": "1",
                    "batch": item.batch_no or "TEST_BCH",
                    "qty": str(item.total_loose_qty or 1),
                    "expiryDate": str(item.expiry_date) if item.expiry_date else "2027-12-31",
                    "mrp": str(item.mrp or 0),
                    "saleRate": str(item.sale_rate or 0),
                    "discAmt": str(item.disc_amt or 0),
                    "discPer": str(item.disc_per or 0),
                    "itemTotal": str(item.item_total or 0),
                    "cgstPer": str(item.cgst_per or 0),
                    "cgstAmt": str(item.cgst_amt or 0),
                    "sgstPer": str(item.sgst_per or 0),
                    "sgstAmt": str(item.sgst_amt or 0),
                    "igstPer": str(item.igst_per or 0),
                    "igstAmt": str(item.igst_amt or 0),
                    "cessPer": "0.00",
                    "cessAmt": "0.00"
                })
            
            if detail_items:
                invoice["detail"] = detail_items
                print(f"[CREATE INVOICE] Successfully loaded {len(detail_items)} items from local DB for {order_id}")
        except Exception as e:
            print(f"[CREATE INVOICE WARNING] Could not load items from DB for {order_id}, using fallback data. Error: {e}")
            invoice["detail"] = [
                {
                    "productId": "I00003",
                    "productName": "DOLO 250MG SUSP",
                    "hsnCode": "30049090",
                    "qtyPerBox": "1",
                    "batch": "DOLN096",
                    "qty": "10.000",
                    "expiryDate": "2027-11-01",
                    "mrp": "75.030",
                    "saleRate": "56.270",
                    "discAmt": "188.30",
                    "discPer": "25.00",
                    "itemTotal": "562.700",
                    "cgstPer": "0.00",
                    "cgstAmt": "0.00",
                    "sgstPer": "0.00",
                    "sgstAmt": "0.00",
                    "igstPer": "5.00",
                    "igstAmt": "28.14",
                    "cessPer": "0.00",
                    "cessAmt": "0.00"
                }
            ]

        # Add or replace invoice in order
        ORDERS[str(order_id)]["invoices"] = [invoice]
        ORDERS[str(order_id)]["billTotal"] = str(doc_total)
        
        print(f"[CREATE INVOICE SUCCESS] Created invoice {doc_no} for order {order_id}")
        
        return jsonify({
            "code": "200",
            "type": "createTestInvoice",
            "message": f"Test invoice {doc_no} created successfully for order {order_id}",
            "orderId": order_id,
            "invoice": invoice
        }), 201
    except Exception as e:
        print(f"[CREATE INVOICE ERROR] {str(e)}")
        return jsonify({
            "code": "500",
            "type": "createTestInvoice",
            "message": str(e)
        }), 500


@app.route('/ws_c2_services_create_invoice', methods=['GET', 'POST'])
def ws_c2_services_create_invoice():
    """Create an invoice for an order with reference code"""
    try:
        if request.method == 'GET':
            data = request.args.to_dict()
        else:
            data = request.get_json() or request.args.to_dict()
        
        order_id = data.get('orderId')
        reference_code = data.get('referenceCode') or data.get('docNo')
        doc_total = float(data.get('docTotal', '542.50'))
        
        print(f"[WS_CREATE_INVOICE] Creating invoice for order: {order_id}, reference: {reference_code}")
        
        if not order_id:
            return jsonify({
                "code": "400",
                "message": "orderId is required"
            }), 400
        
        if not reference_code:
            return jsonify({
                "code": "400",
                "message": "referenceCode or docNo is required"
            }), 400
        
        # Create or get existing order
        if str(order_id) not in ORDERS:
            ORDERS[str(order_id)] = {
                "orderId": str(order_id),
                "custCode": "GC02",
                "customerName": "Test Retailer",
                "fromGstNo": "07NQQAE5107K2ZW",
                "toGstNo": "07NQQAE5107K2ZW",
                "customerType": "Un - Registered",
                "doctorName": "-",
                "documentPk": "26001540100",
                "brCode": "001",
                "tranYear": "26",
                "tranPrefix": "6",
                "tranSrno": "100",
                "createdDate": datetime.now().strftime("%Y-%m-%d"),
                "billTotal": str(doc_total),
                "invoices": []
            }
        
        # Create invoice object with reference code
        invoice = {
            "docNo": reference_code,
            "referenceCode": reference_code,
            "docDate": datetime.now().strftime("%Y-%m-%d"),
            "docStatus": "Invoice Created",
            "createdBy": "SYSTEM",
            "docDiscount": "0.00",
            "docTotal": str(doc_total),
            "detail": [
                {
                    "productId": "I00003",
                    "productName": "DOLO 250MG SUSP",
                    "hsnCode": "30049090",
                    "qtyPerBox": "1",
                    "batch": "DOLN096",
                    "qty": "10.000",
                    "expiryDate": "2027-11-01",
                    "mrp": "75.030",
                    "saleRate": "56.270",
                    "discAmt": "188.30",
                    "discPer": "25.00",
                    "itemTotal": "562.700",
                    "cgstPer": "0.00",
                    "cgstAmt": "0.00",
                    "sgstPer": "0.00",
                    "sgstAmt": "0.00",
                    "igstPer": "5.00",
                    "igstAmt": "28.14",
                    "cessPer": "0.00",
                    "cessAmt": "0.00"
                }
            ]
        }
        
        # Add invoice to order
        if "invoices" not in ORDERS[str(order_id)]:
            ORDERS[str(order_id)]["invoices"] = []
        
        ORDERS[str(order_id)]["invoices"].append(invoice)
        ORDERS[str(order_id)]["billTotal"] = str(doc_total)
        
        print(f"[WS_CREATE_INVOICE SUCCESS] Created invoice {reference_code} for order {order_id}")
        
        return jsonify({
            "code": "200",
            "type": "ws_c2_services_create_invoice",
            "message": f"Invoice {reference_code} created successfully for order {order_id}",
            "orderId": order_id,
            "referenceCode": reference_code,
            "invoice": invoice
        }), 201
    except Exception as e:
        print(f"[WS_CREATE_INVOICE ERROR] {str(e)}")
        return jsonify({
            "code": "500",
            "type": "ws_c2_services_create_invoice",
            "message": str(e)
        }), 500


@app.route('/')
def home():
    """Home page with API documentation"""
    return """
    <html>
    <head>
        <title>ERP Test Server</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { display: inline-block; padding: 3px 8px; border-radius: 3px; color: white; font-weight: bold; }
            .get { background: #61affe; }
            .post { background: #49cc90; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
            pre { background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🏥 ERP Test Server - Dream Pharma</h1>
        <p>Server is running on port 44000</p>
        
        <h2>Available Endpoints:</h2>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/ws_c2_services_generate_token</code>
            <p>Generate API Token</p>
            <pre>{
  "c2Code": "03C000",
  "storeId": "001",
  "prodCode": "02",
  "securityKey": "TUVVek1EQXhNalE9"
}</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/ws_c2_services_get_master_data</code>
            <p>Get Item Master Data</p>
            <pre>?c2Code=03C000&storeId=001&prodCode=02&apiKey=YOUR_API_KEY</pre>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/ws_c2_services_fetch_stock</code>
            <p>Fetch Stock Data</p>
            <pre>?c2Code=03C000&storeId=001&prodCode=02&apiKey=YOUR_API_KEY</pre>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/ws_c2_services_create_sale_order</code>
            <p>Create Sales Order</p>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/ws_c2_services_gl_cust_creation</code>
            <p>Create Global Local Customer</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/ws_c2_services_get_orderstatus</code>
            <p>Get Order Status</p>
            <pre>?c2Code=03C000&storeId=001&apiKey=YOUR_API_KEY&orderId=aditya001</pre>
        </div>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/create_test_invoice</code>
            <p>Create Test Invoice (For Testing Purposes)</p>
            <pre>{
  "orderId": "00120260427055141517EC06F",
  "docNo": "001/26/S/250",
  "docTotal": "542.50"
}</pre>
        </div>
        
        <h2>Quick Test:</h2>
        <p>Try <a href="/ws_c2_services_get_master_data?c2Code=03C000&storeId=001&apiKey=test">/ws_c2_services_get_master_data?c2Code=03C000&storeId=001&apiKey=test</a></p>
        <p>Try <a href="/ws_c2_services_fetch_stock?c2Code=03C000&storeId=001&apiKey=test">/ws_c2_services_fetch_stock?c2Code=03C000&storeId=001&apiKey=test</a></p>
        <p>Try <a href="/ws_c2_services_get_orderstatus?c2Code=03C000&storeId=001&apiKey=test&orderId=aditya001">/ws_c2_services_get_orderstatus?orderId=aditya001</a></p>
        <p><strong>Create Test Invoice (POST with JSON body):</strong></p>
        <pre>curl -X POST http://localhost:44000/create_test_invoice \
  -H "Content-Type: application/json" \
  -d '{
    "orderId": "00120260427055141517EC06F",
    "docNo": "001/26/S/250",
    "docTotal": "542.50"
  }'</pre>
    </body>
    </html>
    """


import os

if __name__ == '__main__':
    # Render provides the port via an environment variable
    # We default to 44000 for your local testing
    port = int(os.environ.get("PORT", 44000))
    
    print("=" * 60)
    print("ERP Test Server - Dream Pharma")
    print("=" * 60)
    print(f"Starting server on port: {port}")
    print("=" * 60)
    
    # We use 0.0.0.0 so it's accessible externally
    app.run(host='0.0.0.0', port=port, debug=True)
