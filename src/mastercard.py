import os
from datetime import date
import categories
import sheets
import util
import ocr
from ocr import TableExceededException
from dotenv import load_dotenv
load_dotenv()

# -- Globals ----------------------------------------------
RATIO = 8
TABLE_LEFT = int(405 * RATIO / 15)
TABLE_RIGHT = int(7445 * RATIO / 15)
TABLE_TOP = int(5092 * RATIO / 15)
TABLE_ROW_H = int(135 * RATIO / 15)
TABLE_BOTTOM = int(9295 * RATIO / 15)

SHOPS_LEFT = int(1456 * RATIO / 8)
SHOPS_RIGHT = int(5969 * RATIO / 15)
PRICE_LEFT = int(6271 * RATIO / 15)
DATES_RIGHT = int(646 * RATIO / 10)

YEAR_MONTH_LEFT = int(2966 * RATIO / 15)
YEAR_MONTH_TOP = int(1408 * RATIO / 15)
YEAR_MONTH_RIGHT = int(3833 * RATIO / 15)
YEAR_MONTH_DOWN = int(1589 * RATIO / 15)
DEFAULT_PARAMS = {
    "TABLE_LEFT": TABLE_LEFT,
    "TABLE_RIGHT": TABLE_RIGHT,
    "TABLE_TOP": TABLE_TOP,
    "TABLE_ROW_H": TABLE_ROW_H,
    "TABLE_BOTTOM": TABLE_BOTTOM
}
# --


# --
def get_year_month(page):
    config = ocr.date_config(default_params=DEFAULT_PARAMS)
    txt = ocr.get_zone(page, config, x1=YEAR_MONTH_LEFT, y1=YEAR_MONTH_TOP, x2=YEAR_MONTH_RIGHT, y2=YEAR_MONTH_DOWN)
    def convert_date(str):
        d = str
        try:
            year, month, day = map(int, str.split())
            d = date(year, month, day)
        except:
            pass
        return d     
    d = convert_date(txt)
    return d

def get_date(page, year, i):
    def convert_date(str):
        d = str
        try:            
            month, day = map(int, str.split())
            d = date(year, month, day)
        except:
            pass
        return d       
    config = ocr.date_config(default_params=DEFAULT_PARAMS)
    d = ocr.get_value(page, config,  i, top=TABLE_TOP, x2=DATES_RIGHT)
    d = convert_date(d)
    return d

# --
def get_shop(page, i, save_img=False):
    config = {}
    config["save_img"] = save_img
    config["DEFAULT_PARAMS"] = DEFAULT_PARAMS
    config["whitelist"] = '0123456789.-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#*.? '
    config["params"] = r'--oem 3 --psm 6 tessedit_char_whitelist=' + config["whitelist"]
    shop = ocr.get_value(page, config, i, top=TABLE_TOP,x1=SHOPS_LEFT, x2=SHOPS_RIGHT)
    return shop

# --
def get_price(page, i, save_img=False):
    def make_config():
        config = {}
        config["save_img"] = save_img
        config["DEFAULT_PARAMS"] = DEFAULT_PARAMS
        config["whitelist"] = '0123456789.-'
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
        return config
    config = make_config()
    price = ocr.get_value(page, config, i, top=TABLE_TOP, x1=PRICE_LEFT)
    def move_minus(price):
        f = lambda x: x if not x.endswith('-') else '-' + x[:-1]
        return f(price)
    price = move_minus(price)
    def to_float(price):
        f = lambda x: float(x) if (x.replace('.', '', 1).replace('-', '', 1)).isdigit() else x
        return f(price)
    price = to_float(price)
    return price

# -- main ----
def get_rows(path):
    rows = []
    pages = list(ocr.get_pages(path, RATIO))
    for i, page in enumerate(pages):
        print(f"get_rows: page: {i}\n\tpath:", os.path.basename(path))
        year_month = get_year_month(page)
        i = 0
        exceeded = False
        while not exceeded:
            try:
                row = get_row(page, year_month, i)
                if row != {}:
                    util.print_row(row)
                    rows.append(row)
                i += 1
            except TableExceededException:
                exceeded = True
    return rows

def get_row(page, year_month, i):
    def extract_year(year_month):
        if isinstance(year_month, date):
            return year_month.year
        return ""
    year = extract_year(year_month)
    res = {}
    d = get_date(page, year, i)
    if d == "":
        return {}
    res["date"] = d
    res["shop"] = shop = get_shop(page, i)
    res["category"] = categories.get_category(shop)
    if res["category"] == categories.Categories.IGNORE:
        return {}
    res["price"] = get_price(page, i)
    return res

# --
def main():
    print("TODO: --MAKE A TESTER. ASSERT VALUES ACCORDING TO KNOWN PDF--------")
    paths = util.get_documents(os.getenv("MASTER_FOLDER"))
    rows = []
    for path in paths:
        rows += get_rows(path)
        break
    sheets.upload_rows(reversed(rows))

if __name__ == '__main__':
    main()
    
