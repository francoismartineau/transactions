import fitz
import os
import sys
from PIL import Image
from dotenv import load_dotenv
load_dotenv()
import pytesseract
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")

# -- Exception --
class TableExceededException(Exception):
    pass
# --

# -- configs --
def date_config(save_img=False, default_params={}, more_whitelist=""):
    config = {}
    config["save_img"] = save_img
    config["DEFAULT_PARAMS"] = default_params
    config["whitelist"] = '0123456789 ' + more_whitelist
    config["params"] = r'--oem 3 '\
                       r'--psm 6 -c '\
                       r'tessedit_char_whitelist="{}" -c '\
                       r'tessedit_pageseg_mode=6 -c '\
                       r'preserve_interword_spaces=1'.format(config["whitelist"])
    return config
# --

# --
def get_pages(path, ratio, save_images=False):
    with fitz.open(path) as pdf:
        for i in range(pdf.page_count):
            page = pdf.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(ratio, ratio))
            img_bytes = pix.samples
            img = Image.frombytes("RGB", (pix.width, pix.height), img_bytes)
            img = img.point(black_or_white)
            if save_images:
                save_image(page, f"page_{i:02d}")
            yield img

def black_or_white(pixel):
    if sys.byteorder == 'little':
        red = (pixel >> 0) & 0xFF
        green = (pixel >> 8) & 0xFF
        blue = (pixel >> 16) & 0xFF
        alpha = (pixel >> 24) & 0xFF
    else:
        red = (pixel >> 24) & 0xFF
        green = (pixel >> 16) & 0xFF
        blue = (pixel >> 8) & 0xFF
        alpha = pixel & 0xFF
    if red == 0 and green == 0 and blue == 0:
        return pixel
    else:
        return 0xFFFFFF 

# --
def default_params(config, x1, y1, x2, y2, h, offset_h, bottom):
    if x1 is None:
        x1=config["DEFAULT_PARAMS"]["TABLE_LEFT"]
    if y1 is None:
        y1=config["DEFAULT_PARAMS"]["TABLE_TOP"]
    if x2 is None:
        x2=config["DEFAULT_PARAMS"]["TABLE_RIGHT"]
    if h is None:
        h = config["DEFAULT_PARAMS"]["TABLE_ROW_H"]
    if offset_h is None:
        offset_h = config["DEFAULT_PARAMS"].get("TABLE_ROW_OFFSET_H", h)
    if y2 is None:
        y2=y1+h
    if bottom is None:
        bottom = config["DEFAULT_PARAMS"]["TABLE_BOTTOM"]
    return  x1, y1, x2, y2, h, offset_h, bottom

def get_value(img, config, i, x1=None, top=None, x2=None, h=None, offset_h=None):
    y1 = top
    x1, y1, x2, y2, h, offset_h, bottom = default_params(config,
                                               x1=x1, y1=y1, x2=x2, y2=None,
                                               h=h, offset_h=offset_h, bottom=None)
    y1 += offset_h * i
    y2 = y1 + h
    exceeded = y1 >= bottom
    if exceeded:
        raise TableExceededException
    bottom = y2 + 1
    img_c = img.crop((x1, y1, x2, y2))
    if config["save_img"]:
        save_image(img_c, f"row_{i}")    
    txt = pytesseract.image_to_string(img_c, config=config["params"])
    txt = filter_str(txt, config["whitelist"])
    return txt

def get_zone(img, config, x1=None, y1=None, x2=None, y2=None):
    img_c = img.crop((x1, y1, x2, y2))
    if config["save_img"]:
        save_image(img_c, f"zone{x1}-{y1}")
    txt = pytesseract.image_to_string(img_c, config=config["params"])
    txt = filter_str(txt, config["whitelist"])
    return txt

def filter_str(s: str, whitelist="") -> str:
    s = s.replace("\x0c", "")
    s = s.replace("\n", "")
    s = s.strip()
    if whitelist:
        s = ''.join([char for char in s if char in whitelist])
    return s

# --
def save_image(img, name):
    path =f"{name}.png"
    print(f"saving: {path}")
    img.save(path)
