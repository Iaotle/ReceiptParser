# ReceiptParser
Parser for Albert Heijn receipts. Because why can't you just download them in bulk?

Grab your Bearer-Token using [HTTPToolkit](https://httptoolkit.com/) (you will have to install a root CA to see the requests in plaintext), then paste it into the Python script. The script will then query the Albert Heijn API and download all of your receipts. It will save each one in an individual `.json` file, and will not re-download them again if you need to fetch more at some point.

It will also export your purchases into a `.csv` file for accounting purposes (though the parsing is very basic, feel free to make improvements).
