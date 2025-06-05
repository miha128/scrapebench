# scrapebench
scrape from geekbench (python edition)

geekbench result parser i wrote because i needed it for... educational purposes (and a pretty json list too!!) (and also because the only scraper i found was ruby based and i hate ruby)

configurable with another baseurl if you're really into that and are trying to host ur own ig

wait i forgot to write usage n shit hold on 

oh yeah you need to install requests and bs4 

pip install beautifulsoup4 requests

| argument        | descritpion                                                                                                                                                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `query`         | device model to search for (e.g., `sm-a566b`)                                                                                                                                                                                  |
| `-f, --file`    | use an existing input file (`.json`, `.xml`, `.csv`) instead of web scraping                                                                                                                                                   |
| `-t, --threads` | threads to use, defaults to 1                                                                                                                                                                                                  |
| `-p, --pages`   | max pages to scrape (defaults to max)                                                                                                                                                                                          |
| `-o, --output`  | base name for output files (default: timestamp + query)                                                                                                                                                                        |
| `--json`        | self explanatory                                                                                                                                                                                                               |
| `--csv`         | Output results in CSV format                                                                                                                                                                                                   |
| `--xml`         | Output results in XML format                                                                                                                                                                                                   |
| `--stats`       | Output statistics in JSON format                                                                                                                                                                                               |
| `--all`         | Output **all** formats                                                                                                                                                                                                         |
| `-h, --help`    | show help, even tho its literally written in the guide and i did have a little bit of fun with it and i did capitalize the name n shi but whatever it died down my autism only activttes when i have to code in python anywyas |
example usage:

`python geekbench_parser.py sm-a136u --all` 

to save results for the a13 5g in all formats, single threaded only

`python geekbench_parser.py "pixel 6" -p 3 -t 4 --json --stats`

to save results for the pixel 6 in json format, 3 pages and 4 threads, also show JSON formatted stats

example output for json formatted stats: 

`{
    "mean_single_core": 1097.66,
    "mean_multi_core": 3242.91,
    "min_single_core": 846,
    "max_single_core": 1160,
    "min_multi_core": 2388,
    "max_multi_core": 3502,
    "sample_count": 100
}`

do note that if geekbench changes their site layout this will explode (pls dont)
