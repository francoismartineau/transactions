import os
import time
from functools import wraps
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from categories import Categories, category_to_str

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_ID = 0
SHEET_NAME = "transactions"

def upload_rows(rows, sheet_name=SHEET_NAME):
	if os.getenv("UPLOAD") != "1":
		return
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
	x = 1
	y = 2
	SheetsApi.insert_rows(sheet_name, y=y, qty=len(rows))
	try:
		SheetsApi.set_values(sheet_name, x=x, y=y, vals=rows)
	except HttpError as e:
		if e.resp.status == 429:
			print("Quota exceeded. Waiting for a minute before retrying...")
			time.sleep(60)
		else:
			print(f"An HTTP error occurred: {e}")

class SheetsApi:
	service = None
	spreadsheets = None
	spreadsheet_id = None
	purged_sheets = []
	
	_sheets = []

	def connect(func):
		@wraps(func)
		def wrapper(cls, *args, **kwargs):
			if not cls.service or not cls.spreadsheets:
				try:
					key_file = "service-account-key.json"
					credentials = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
					cls.service = build("sheets", "v4", credentials=credentials)
					cls.spreadsheets = cls.service.spreadsheets()
					cls.spreadsheet_id = os.getenv("SPREADSHEET_ID")
					return func(cls, *args, **kwargs)
				except HttpError as error:
					print(f"An error occurred: {error}")
		return wrapper

	# -- sheets ----
	@classmethod
	@connect
	def insert_sheet(cls, title):
		cls._sheets = []
		request_body = {
			"requests": [
				{
					"addSheet": {"properties": {"title": title}}
				}
			]
		}
		response = cls.spreadsheets.batchUpdate(
			spreadsheetId=cls.spreadsheet_id,
			body=request_body
		).execute()
		sheet_id = response.get('replies', [{}])[0]\
			.get('addSheet', {})\
			.get('properties', {})\
			.get('sheetId')
		return sheet_id

	@classmethod
	@connect
	def get_sheets(cls):
		if cls._sheets:
			return cls._sheets
		response = cls.spreadsheets.get(spreadsheetId=cls.spreadsheet_id, fields='sheets.properties').execute()
		cls._sheets = {
			sheet['properties']['sheetId']: sheet['properties']['title']
			for sheet in response['sheets']
		}
		return cls._sheets

	@classmethod
	@connect
	def get_sheet_id(cls, sheet_name):
		sheets = cls.get_sheets()
		for id, name in sheets:
			if sheet_name == name:
				return id
	# ----
	@classmethod
	@connect
	def insert_rows(cls, sheet_name, y, qty=1):
		sheet_id = cls.get_sheet_id(sheet_name)
		req = {'sheetId': sheet_id, 'dimension': 'ROWS', 'startIndex': y - 1, 'endIndex': y - 1 + qty}
		req = {
			'requests': [
				{'insertDimension': {'range': req}}
			]
		}
		cls.service.spreadsheets().batchUpdate(
			spreadsheetId=cls.spreadsheet_id,
			body=req
		).execute()

	@classmethod
	@connect
	def clear_row(cls, spreadsheet_id, sheet_name, y):
		cls.spreadsheets.values().update(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{y}:{y}", valueInputOption="USER_ENTERED", 
						body={"values": [["" for _ in range(20)]]}).execute()	

	@staticmethod
	def translate_col(x):
		return chr(x + ord('A') - 1)

	@staticmethod
	def incr_col(col):
		col = chr(ord(col) + 1)

	# vals: [[]]
	@classmethod
	@connect
	def set_values(cls, spreadsheet_id, sheet_name, x, y, vals):
		col = cls.translate_col(x)
		row = y
		cls.spreadsheets.values().update(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{col}{row}", valueInputOption="USER_ENTERED", 
						body={"values": vals}).execute()	

	# return: [[]]
	@classmethod
	@connect
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
		result = cls.spreadsheets.values().get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!{selection}").execute()
		values = result.get("values", [])
		for y, row in enumerate(values):
			for x, val in enumerate(row):
				values[y][x] = get_type(val)(val)
		return values

if __name__ == "__main__":
	sheets = SheetsApi.insert_sheet("test")
	print(sheets)