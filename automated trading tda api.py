#!pip install tda-api             #open source library using TD Ameritrade API
#!pip install ta                  #technical analysis library for calculating financial ratios
#!pip install webdriver-manager   #brower control to login

import tda
from tda.auth import easy_client                      
from tda.client import Client                         #access and refresh client token
from tda.streaming import StreamClient                #get real-time stock data
from tda.orders.equities import equity_buy_market     #submit orders to buy and sell
from tda.orders.equities import equity_sell_market
import atexit
import pytz                                           #timezone if applicable
import datetime
from datetime import timedelta
import asyncio                                        #runs and updates function asynchronously
from contextlib import suppress
import json
from selenium import webdriver                        
from webdriver_manager.chrome import ChromeDriverManager
import ta                                             
import math
import numpy as np
import pandas as pd
import logging
import locale
import threading
import time
import sys
import os

#Bar Class
class Bar:
    open = 0
    close = 0
    high = 0
    low = 0
    volume = 0
    date = datetime.datetime.now()
    def __init__(self):
        self.open = 0
        self.close = 0
        self.high = 0
        self.low = 0
        self.volume = 0
        self.date = datetime.datetime.now()
        
#Bot Class
class Bot():
    barsize = 1
    currentBar = Bar()
    bars = []
    client = ''
    account_id = 0
    accountSize = 10000
    firstTime = True
    inPosition = False
    #Common Indicators
    rsi = []
    vol = []
    ema50 = []
    ema200 = []
    min_vol = 99999999
    #Parameters
    risPeriod = 14
    stream_client = ''
    status = None
    initialbartime = datetime.datetime.now() #.astimezone(pytz.timezone())
    
    #Connect to TD Ameritrade
    def __init__(self):
        try:
            #Global variables
            API_KEY = '@AMER.OAUTHAP'               ### INSERT YOUR PRIVATE API KEY ###
            REDIRECT_URI = 'http://localhost:8080'  ### INSERT localhost address ###
            TOKEN_PATH = 'token.pickle'
            
            #New client
            self.client = tda.auth.easy_client(API_KEY,
                                              REDIRECT_URI,
                                              TOKEN_PATH,
                                              self.make_webdriver)
            
            #Account ID
            r = self.client.get_accounts()
            assert r.status_code == 200, r.raise_for_status()
            data = r.json()
            self.account_id = data[0]['securitiesAccount']['accountId']
            self.accountSize = data[0]['securitiesAccount']['currentBalances']['cashBalances']
            self.stream_client = StreamClient(self.client, account_id=self.account_id)
            print("You are logged in to your TD Ameritrade Account.")
            
            #Get symbol info
            self.symbol = input("Enter the ticker you want to trade : ")
            
            #Get candle stick
            self.barsize = int(input("Enter the barsize you want to trade in minutes : "))
            self.stream_client = StreamClient(self.client, account_id=self.account_id)
            #run program asynchronously
            asyncio.run(self.read_stream())
            
        except Exception as e:
            print(e)
    
    #Stream realtime updates
    async def read_stream(self):
        try:
            await self.stream_client.login()
            await self.stream_client.quality_of_services(StreamClient.QOSLevel.EXPRESS)
            await self.stream_client.chart_equity_subs([self.symbol])
            self.stream_client.add_chart_equity_handler(self.onBarUpdate)
            print("Streaming real-time date now.")
            while True:
                try:
                    await self.stream_client.handle_message()
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)
            
    #Update everytime there is a bar
    def OnBarUpdates(self, msg):
        try:
            msg = json.dumps(msg, indent=4)
            msg = json.loads(msn)
                
             #Retrieve Bar
            for bar in msg['content']:
                
                #Check The Strategy
                bartime = datetime.datetime.fromtimestamp(msg['timestamp'] / 1000) #.astimezone(pytz.timezone())
                minutes_diff = (bartime-self.initialbartime).total_seconds() / 60.0
                self.currentBar.date = bartime
                    
                #On Bar Close
                if (minutes_diff > 0 and math.floor(minutes_diff) % self.barsize == 0):
                    self.initialbartime = bartime
                    """
                    INSERT ENTRY AND EXIT STRATEGY
                    """
                    #Investment strategy based on RSI
                    #Calculate RSI
                    closes = []
                    for histbar in self.bars:
                        closes.append(histbar.close)
                    self.close_array = pd.Series(np.asarray(closes))
                    if len(self.bars) > 0:
                        #Calculate RSI on bar close
                        self.rsi  = ta.momentum.rsi(self.close_array, self.rsiPeriod, True)
                        #Print last rsi
                        print(self.rsi[len(self.rsi)-1])
                        """
                        If the rsi <= 30 and we are not in position, buy
                        If the rsi >= 70 and we are in position, sell
                        """    
                        if self.rsi[len(self.rsi)-1] <= 30 and not inPosition:
                            order = tda.orders.equities.equity_buy_market(self.symbol,1)
                            inPosition = True
                        if self.rsi[len(self.rsi)-1] >= 70 and inPosition:
                            order = tda.orders.equities.equity_sell_market(self.symbol,1)
                            inPosition = False       
                    """
                    ALTERNATIVE STRATEGY
                    """
                    #Investment strategy based on EMA
                    #Calculate ema50 and ema200 on bar close
#                     self.ema50 = ta.trend.EMAIndicator(self.close_array,50,True)
#                     self.ema200 = ta.trend.EMAIndicator(self.close_array,200,True)
                        """
                        If ema50 > ema200 and today's volume is > 7 bar volume min and we are not in position, buy
                        If price < ema50 and we are in position, sell
                        """
#                         if self.ema50[len(self.ema50)-1] > self.ema200[len(self.ema200)-1] \
#                         and self.currentBar.volume > self.min_vol and not inPosition:
#                             order = tda.orders.equities.equity_buy_market(self.symbol,1)
#                             inPosition = True
#                         if self.ema50[len(self.ema50)-1] <= self.ema200[len(self.ema200)-1] and inPosition:
#                             order = tda.orders.equities.equity_sell_market(self.symbol,1)
#                             inPosition = False

                    #Bar closed append
                    self.currentBar.close = bar['CLOSE_PRICE']
                    print("New bar!")
                    self.bars.append(self.currentBar)
                    self.currentBar = Bar()
                    self.currentBar.open = bar['OPEN_PRICE']
                    
                #Build realtime bar
                if self.currentBar.open == 0:
                    self.currentBar.open = bar['OPEN_PRICE']
                if self.currentBar.open == 0 or bar['HIGH_PRICE'] > self.currentBar.high:
                    self.currentBar.open = bar['HIGH_PRICE']
                if self.currentBar.open == 0 or bar['LOW_PRICE'] < self.currentBar.low:
                    self.currentBar.open = bar['LOW_PRICE']
                
                #Volume append
                self.currentBar.volume += bar['VOLUME']
                #Set minimum volume
                for bar in self.bars[-7:-1]:
                    if bar.volume < self.min_vol:
                        self.min_vol = bar.volume
                
        except Exception as e:
            print(e)
                
    #Connect to TD Ameritrade OAUTH Login
    def make_webdriver(self):
        #from selenium import webdriver here if slow to import
        driver = webdriver.Chrome(ChromeDriverManager().install())
        atexit.register(lambda: driver.quit())
        return driver

#Start Bot
bot = Bot()
