import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from categories import Categories, category_to_str
import time
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = 0
SHEET_NAME = "transactions"

def upload_rows(rows, sheet_id=SHEET_ID, sheet_name=SHEET_NAME):
	def map_rows(rows):
		_rows = []
		for row in rows:
			date = row.get("date", "")
			category = row.get("category", "")
			if category == Categories.IGNORE:
				continue
			category = category_to_str(category)
			price = row.get("price", "")
			if price:
				price = "{:.2f}".format(price)
				price = price.replace('.', ',')
			_row = [str(date), category, str(price)]
			_rows.append(_row)
		return _rows
	rows = map_rows(rows)
	SheetsApi.connect()
	ss_id = os.getenv("SPREADSHEET_ID")
	x = 1
	y = 2
	SheetsApi.insert_rows(ss_id, sheet_id, y=y, qty=len(rows))
	try:
		SheetsApi.set_values(ss_id, sheet_name, x=x, y=y, vals=rows)
	except HttpError as e:
		if e.resp.status == 429:
			print("Quota exceeded. Waiting for a minute before retrying...")
			time.sleep(60)
		else:
			print(f"An HTTP error occurred: {e}")

class SheetsApi:
	service = None
	sheets = None
	purged_sheets = []

	@classmethod
	def connect(cls):
		key_file = "service-account-key.json"
		credentials = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
		cls.service = build("sheets", "v4", credentials=credentials)
		cls.sheets = cls.service.spreadsheets()

	@classmethod
	def insert_rows(cls, spreadsheet_id, sheet_id, y, qty=1):
		req = {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': y - 1, 'endIndex': y - 1 + qty}
		req = {
			'requests': [
				{'insertDimension': {'range': req}}
			]
		}
		cls.service.spreadsheets().batchUpdate(
			spreadsheetId=spreadsheet_id,
			body=req
		).execute()

	@classmethod
	def clear_row(cls, spreadsheet_id, sheet_name, y):
		cls.sheets.values().update(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{y}:{y}", valueInputOption="USER_ENTERED", 
						body={"values": [["" for _ in range(20)]]}).execute()	

	@staticmethod
	def translate_col(x):
		return chr(x + ord('A') - 1)

	@staticmethod
	def incr_col(col):
		col = chr(ord(col) + 1)

	# vals: [[]]
	@classmethod
	def set_values(cls, spreadsheet_id, sheet_name, x, y, vals):
		col = cls.translate_col(x)
		row = y
		cls.sheets.values().update(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{col}{row}", valueInputOption="USER_ENTERED", 
						body={"values": vals}).execute()	

	# return: [[]]
	@classmethod
	def read_values(cls, spreadsheet_id, sheet_name, selection):
		def get_type(s):
			try:
				float(s)
			except ValueError:
				return str
			else:
				if float(s).is_integer():
					return int
				else:
					return float	
		result = cls.sheets.values().get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{selection}").execute()
		values = result.get("values", [])
		for y, row in enumerate(values):
			for x, val in enumerate(row):
				values[y][x] = get_type(val)(val)
		return values
