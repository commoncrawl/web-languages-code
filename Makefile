init:
	pip install -r requirements.txt

get-table:
	# https://iso639-3.sil.org/code_tables/download_tables
	wget https://iso639-3.sil.org/sites/iso639-3/files/downloads/iso-639-3_Code_Tables_20240415.zip
	unzip -o iso-639-3_Code_Tables_20240415.zip

combine-wikipedia:
	cat wikipedia_languages.csv  wikipedia_languages_extra.csv > wikipedia_languages_all.csv

generate:
	python3 generate.py
