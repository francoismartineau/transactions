import os
from datetime import date, datetime
import util
import sheets
import categories
import ocr
from ocr import TableExceededException
from dotenv import load_dotenv
load_dotenv()

# -- Globals ----------------------------------------------
RATIO = 8   # greater means more pixels (slower / more precise)

#  = int( pixel * RATIO / ratio at measurement )
YEAR_MONTH_LEFT = int(3244 * RATIO / 8)
YEAR_MONTH_TOP = int(828 * RATIO / 8)
YEAR_MONTH_RIGHT = int(3664 * RATIO / 8)
YEAR_MONTH_DOWN = int(928 * RATIO / 8)

TABLE_LEFT = int(954 * RATIO / 8)
TABLE_RIGHT = int(4726 * RATIO / 8)
TABLE_TOP = int(1063 * RATIO / 8)
TABLE_ROW_H = int(55 * RATIO / 8)
TABLE_ROW_OFFSET_H = int(95 * RATIO / 8)
TABLE_BOTTOM = int(6271 * RATIO / 8)

DATES_RIGHT = int(1252 * RATIO / 8)
DESCR_LEFT = int(1393 * RATIO / 8)
DESCR_RIGHT = int(3210 * RATIO / 8)
WIDTHDRAWAL_LEFT = DESCR_RIGHT
WIDTHDRAWAL_RIGHT = int(3613 * RATIO / 8)
DEPOSIT_LEFT = WIDTHDRAWAL_RIGHT
DEPOSIT_RIGHT = int(4212 * RATIO / 8)

DEFAULT_PARAMS = {
    "TABLE_LEFT": TABLE_LEFT,
    "TABLE_RIGHT": TABLE_RIGHT,
    "TABLE_TOP": TABLE_TOP,
    "TABLE_ROW_H": TABLE_ROW_H,
    "TABLE_ROW_OFFSET_H": TABLE_ROW_OFFSET_H,
    "TABLE_BOTTOM": TABLE_BOTTOM
}
MONTHS_STRS = ["JAN", "FEV", "MAR", "APR", "MAI", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
def init_months_letters():
    months_letters = ""
    for month in MONTHS_STRS:
        for c in month:
            if c not in months_letters:
                months_letters += c
    return months_letters
MONTHS_LETTERS = init_months_letters()
# --

# --
def get_year_month(pages):
    if len(pages) == 0:
        return None
    config = ocr.date_config(
        default_params=DEFAULT_PARAMS,
        more_whitelist="-"
    )
    txt = ocr.get_zone(pages[0], config, x1=YEAR_MONTH_LEFT, y1=YEAR_MONTH_TOP, x2=YEAR_MONTH_RIGHT, y2=YEAR_MONTH_DOWN)
    d = datetime.strptime(txt, "%Y-%m")
    return d

def get_date(page, year, i):
    config = ocr.date_config(
        default_params=DEFAULT_PARAMS,
        more_whitelist=MONTHS_LETTERS
    )
    txt = ocr.get_value(page, config,  i, top=TABLE_TOP, x2=DATES_RIGHT)
    def convert_date(txt):
        try:
            month, day = txt.split()
            day = int(day)
            for i, m in enumerate(MONTHS_STRS):
                if m == month:
                    month = i + 1
                    break
            d = date(year=year, month=month, day=day)
            return d
        except:
            return None
    d = convert_date(txt)
    return d

# --
def get_description(page, i, save_img=False):
    config = {}
    config["save_img"] = save_img
    config["DEFAULT_PARAMS"] = DEFAULT_PARAMS
    config["whitelist"] = '0123456789/.-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#*.? '
    config["params"] = r'--oem 3 --psm 6 tessedit_char_whitelist=' + config["whitelist"]
    descr = ocr.get_value(page, config, i, top=TABLE_TOP,x1=DESCR_LEFT, x2=DESCR_RIGHT)
    return descr

# --
def get_price(page, i, save_img=False):
    config = {}
    config["save_img"] = save_img
    config["DEFAULT_PARAMS"] = DEFAULT_PARAMS
    config["whitelist"] = '0123456789,.-'
    config["params"] = \
        r'--oem 3 '\
        r'--psm 6 -c '\
        r'tessedit_char_whitelist="{}" '\
        r'-c tessedit_pageseg_mode=6 -c '\
        r'preserve_interword_spaces=1 -c '\
        r'tessedit_create_hocr=0 -c '\
        r'load_system_dawg=0 -c '\
        r'load_freq_dawg=0 -c '\
        r'load_unambig_dawg=0 -c '\
        r'load_punc_dawg=0 -c '\
        r'load_number_dawg=0 -c '\
        r'language_model_penalty_non_dict_word=1 -c '\
        r'language_model_penalty_non_freq_dict_word=1 -c '\
        r'wordrec_max_ngram_search_size=3 -c '\
        r'lstm_choice_mode=2 -c '\
        r'lstm_single_char_unicharset=1 -c '\
        r'lstm_fixed_point_seed=1'.format(config["whitelist"])
    deposit = ocr.get_value(page, config, i, x1=DEPOSIT_LEFT, x2=DEPOSIT_RIGHT)
    widthdrawal = ocr.get_value(page, config, i, x1=WIDTHDRAWAL_LEFT, x2=WIDTHDRAWAL_RIGHT)
    def to_float(value):
        try:
            value = value.replace(',', '')
            return float(value)
        except:
            print("ERROR float(): deposit:", deposit, "value:", value)
            exit(1)
    if deposit:
        return -to_float(deposit)
    if widthdrawal:
        return to_float(widthdrawal)
 
# -- main ----
def get_rows(path):
    rows = []
    pages = list(ocr.get_pages(path, RATIO))
    year_month = get_year_month(pages)
    for i, page in enumerate(pages[1:]):
        print(f"get_rows: page: {i}\n\tpath:", path)
        i = 0
        exceeded = False
        while not exceeded:
            try:
                row = get_row(page, year_month.year, i)
                i += 1
                if not row.get("date"):
                    break
                if row.get("category") == categories.Categories.IGNORE \
                    or not row.get("price"):
                    continue
                util.print_row(row)
                rows.append(row)
            except TableExceededException:
                exceeded = True
    return rows

def get_row(page, year, i):
    res = {}
    res["date"] = get_date(page, year, i)
    if not res["date"]:
        return res
    res["price"] = get_price(page, i)
    if not res["price"]:
        return res
    res["shop"] = descr = get_description(page, i)
    res["category"] = categories.get_category(descr, res["price"])
    return res

# --
def main():
    print("TODO: --MAKE A TESTER. ASSERT VALUES ACCORDING TO KNOWN PDF--------")
    paths = util.get_documents(os.getenv("BNC_FOLDER"))
    rows = []
    for path in paths:
        print("path:", os.path.basename(path))
        rows += get_rows(path)
    sheets.upload_rows(reversed(rows))

if __name__ == '__main__':
    main()
