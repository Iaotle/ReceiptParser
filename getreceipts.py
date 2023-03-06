#!/usr/bin/env python3

import datetime
from decimal import Decimal
from enum import Enum
from http.client import OK, HTTPException
from multiprocessing import Pool
import os
import requests
import json

import csv

# get list of receipts
RECEIPTS_URL = 'https://api.ah.nl/mobile-services/v1/receipts'

TOKEN = 'Bearer 60327390_7efb-4fe0-b57b-5a462b888285'  # pain in the ass to get


print('Getting receipts from Albert Heijn...')
r = requests.get(RECEIPTS_URL, headers={'Authorization': TOKEN}) # todo error handling
print(r)
receipts = json.loads(r.content)
with open('receipts.json', 'w+') as file:
    file.write(json.dumps(receipts, indent=4))
    file.close()


print(f'Got a total of {len(receipts)} receipts', end='\n\n')


receiptsparsed = []


class Product:
    """A product from AH"""

    def __init__(self, json):
        self.description = json.get('description')
        self.quantity = json.get('quantity')
        self.amount = json.get('amount')
        self.price = json.get('price')
        self.indicator = json.get('indicator')
        self.text = json.get('text')
        self.label = json.get('label')
        self.type = json.get('type')

    def __str__(self):
        return str(self.type) + str(self.description)


keep = ['product', 'subtotal', 'total']
drop = ['BONUSKAART', 'BONUS BOX', 'Waarvan']


def filter_product(p: json):
    type = p.get('type')
    description = p.get('description')
    label = p.get('label')
    if type in keep and description not in drop and label != 'UW VOORDEEL':
        return True
    else:
        return False


class Receipt:
    items = []
    subtotal = 0
    discounts = []
    total_with_discounts = 0
    koopzegels = 0
    total = 0

    def pretty_print(self):
        print('items:')
        for i in self.items:
            print(i.quantity, i.description, i.amount, i.indicator)

        print('subtotal: ' + str(self.subtotal))

        print('discounts:')
        for i in self.discounts:
            print(i.quantity, i.description, i.amount, i.indicator)

        print('total with discount: ' + str(self.total_with_discounts))
        print('koopzegels: ' + str(self.koopzegels))
        print('total: ' + str(self.total))

    def __init__(self, products: list, time):
        self.products = products
        self.time = time
        self.parse_products()

    def parse_products(self):
        # items
        # subtotal
        # discounts from bonus (try to apply these to the products prolly)
        # subtotal with discounts
        # koopzegels
        # total
        # todo parse these out properly
        # buckets:
        class Stage(Enum):
            items = 0
            subtotal = 1
            discounts = 2
            total_with_discounts = 3
            koopzegels = 4
            total = 5

        stage = Stage.items

        for p in self.products:
            match stage:
                case Stage.items:
                    if p.type == 'subtotal':
                        self.subtotal = p.amount
                        stage = Stage.discounts
                        continue
                    self.items.append(p)
                case Stage.discounts:  # will not always be there, fuck
                    if p.type == 'subtotal':
                        self.total_with_discounts = p.amount
                        stage = Stage.koopzegels
                        continue
                    self.discounts.append(p)
                case Stage.koopzegels:
                    self.koopzegels = p.amount
                    stage = Stage.total
                case Stage.total:
                    self.total = p.price
                    break

    def __str__(self):
        return str(self.time) + str(self.items) + str(self.subtotal) + str(self.discounts) + str(self.total_with_discounts) + str(self.koopzegels) + str(self.total)


def parse_receipt(receipt_json):
    time = datetime.datetime.strptime(
        receipt_json['transactionMoment'], '%Y-%m-%dT%H:%M:%SZ') # todo convert for timezone
    entries = receipt_json['receiptUiItems']


    entries
    # entries = filter(filter_product, entries)
    # products = []
    # for i in entries:
    #     print(i)
    #     p = Product(i)
    #     products.append(p)
    #     if p.type == 'TOTAAL':
    #         break

    # return Receipt(products, time)


def file_exists(filename, search_path):
   for root, dir, files in os.walk(search_path):
    if filename in files:
         return True
   return False

def get_receipt_files():
    for root, dir, files in os.walk('./receipts'):
        return files # todo remove .json

def get_receipt(receipt):
    filepath = receipt['transactionId'] + '.json'
    if file_exists(filepath, './receipts'):
        print('\033[FReceipt ' + receipt['transactionId'] + ' already exists, skipping...')
        return
    try:
        r = requests.get(f'https://api.ah.nl/mobile-services/v2/receipts/' + receipt['transactionId'], headers={'Authorization': TOKEN})
        if (r.status_code != OK):
            raise HTTPException()

        print('Fetched receipt with ID ' + receipt['transactionId'])

        with open('./receipts/' + filepath, 'w+') as file:
            receipt = json.loads(r.content)
            file.write(json.dumps(receipt, indent=4))
            file.close()
    except:
        get_receipt(receipt) # will work if you don't have too many receipts haha



# fetch receipts from 
with Pool(8) as p:
    p.map(get_receipt, receipts)


def bonus_filter(entry):
    if entry.get('description') not in drop and entry.get('label') != 'UW VOORDEEL':
        return True
    return False

csvfile = open('results.csv', 'w+')
writer = csv.writer(csvfile)

sum = Decimal()
sumbonus = Decimal()


for receipt in receipts:
    filepath = receipt['transactionId'] + '.json'
    with open('./receipts/' + filepath, 'r') as file:
        receipt = json.load(file)
        counter = 0
        items = receipt['receiptUiItems']
        time = datetime.datetime.strptime(
                receipt['transactionMoment'], '%Y-%m-%dT%H:%M:%SZ') # todo convert for timezone

        lists = [   [],        [], [], [], []]
        for i in items:
            if i.get('type') == 'divider':
                counter += 1
                continue
            lists[counter].append(i)
        # print(lists[0], end='\n\n\n') # always useless
        products = lists[1][1:]
        if len(products) == 0:
            products = lists[1] # {'type': 'product', 'description': 'AH BONUS NR.', 'amount': 'xx5358'} todo handle it
        bonus_stuff = lists[2] # !!!subtotaal!!!, spacer, BONUS * n, UW VOORDEEL, WAARVAN, BONUS BOX
        subtotal = Decimal(bonus_stuff[0]['amount'].replace(',', '.'))
        without_stamps = subtotal
        bonus_stuff = filter(bonus_filter, bonus_stuff[2:])
        if len(lists[4]) == 0:
            # no koopzegels
            total = Decimal(lists[3][1]['price'].replace(',','.'))
        else:
            if (lists[3][0]['type'] == 'subtotal'): # there is a second subtotal
                without_stamps = Decimal(lists[3][0]['amount'].replace(',','.'))
                koopzegels = Decimal(lists[3][2]['amount'].replace(',','.'))
            else:
                koopzegels = Decimal(lists[3][1]['amount'].replace(',','.'))

            
            total = Decimal(lists[4][1]['price'].replace(',','.'))
            if without_stamps + koopzegels != total:
                print(filepath)
                print(without_stamps + koopzegels, total)
                exit(1)


        # print(f'products {products}, bonus {bonus_stuff}, stamps {total-without_stamps}, total {total}')
        for i in products:
            try:
                writer.writerow([i.get('description'), Decimal(i.get('amount').replace(',','.').replace('"', ''))])
            except:
                print(i)
                exit(1)

        sum += total
        sumbonus += total-without_stamps
        # exit(1)
        
        # print(lists[3], end='\n\n\n') # {'type': 'subtotal', 'text': 'SUBTOTAAL', 'amount': '13,36'}          {'type': 'spacer'}, {'type': 'product', 'quantity': '13', 'description': 'KOOPZEGELS', 'amount': '1,30'} # might not exist
        # print(lists[4], end='\n\n\n') # spacer, !!!total!!!

        file.close()
        # exit(1)

csvfile.close()

print(sum, sumbonus)