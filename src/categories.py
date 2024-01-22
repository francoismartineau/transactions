import json
from enum import Enum

CONFIG = None
def get_config():
	global CONFIG
	if CONFIG is None:
		with open('data/categories.json', 'r', encoding='utf8') as config_file:
			CONFIG = json.load(config_file)
	return CONFIG

class Categories(Enum):
	UNKNOWN = 0
	IGNORE = 1

def category_to_str(category):
	categories_str = get_config().get("categories_str", {})
	return categories_str.get(category, "?")

def get_category(shop, price=0):
	if price < 0:
		return Categories.UNKNOWN
	if not shop.strip():
		return Categories.UNKNOWN
	sample_categories = get_config().get("sample_categories", {})
	for sample, category in sample_categories.items():
		if sample.lower() in shop.lower():
			if category == "IGNORE":
				return Categories.IGNORE
			return category
	return Categories.UNKNOWN