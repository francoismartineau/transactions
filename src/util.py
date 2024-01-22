import glob
import os
import time as time_module
import categories
from dotenv import load_dotenv
load_dotenv()

def get_documents(subfolder):
    PDF_FOLDER = os.getenv("PDF_FOLDER")
    folder = os.path.join(PDF_FOLDER, subfolder)
    documents = os.path.join(folder, "*")
    documents = glob.glob(documents)
    return documents

START_TIME = time_module.time()
def time(msg=""):
    elapsed_time = time_module.time() - START_TIME
    START_TIME = elapsed_time
    print(f"{msg}: {int(elapsed_time)} seconds")

def print_row(row):
    category = row.get("category", "")
    category = categories.category_to_str(category)
    d = row.get("date", "")
    price = row.get("price", "")
    print(f'{d}\t{category}\t\t{price} $')
    if category == "?":
        shop = row.get("shop", "")
        print(f'shop: {shop}')