## Parses data from bank statements

This tool helps having a big picture of my finances by parsing bank statements, converting specific transactions to more general categories and uploading (date, category, amount) tuples to a Google Sheets document. Then, I can visualize my finances in various ways.

Pdf files can be difficult to parse. Depending on the document, extracting text can lead to unexpected behavior. I found that using Optical Character Recognition ([OCR](https://en.wikipedia.org/wiki/Optical_character_recognition)) with precise configuration is easier and more reliable.

##### Usage:
- Set the .env.example values and remove ".example"
- Configure data/categories.json.example and remove ".example"
- Set a Google Sheets Api service account and place service-account-key.json at the root
- Put your bank statements in pdf/
- python src/main.py

To design categories:
- .env: UPLOAD=0
- run program and use unrecognized transactions to fill data/categories.json
- then, set UPLOAD=1 and run again



##### Supported statements:
- National Bank
- Mastercard