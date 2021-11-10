from json.decoder import JSONDecodeError
import requests, time, sys

# Main function. Starts by calling getWallets to get list of wallets.
# Prints the local time and the sum of the values of all wallets in the wallets list.
# Runs in a loop. Every 30 seconds, the value printed is updated with a new value
# based on current pricing data.
def main():
    wallets = getWallets()
    while True:
        try:
            sys.stdout.write("\r" + time.strftime("%I:%M:%S %p", time.localtime()) + " " + formatUsd(sumAllWallets(wallets)))
            sys.stdout.flush()
        except JSONDecodeError:
            continue
        time.sleep(30)

# Wallet class. Wallet objects have the address attribute storing a string of their address,
# as well as other attributes and methods depending on the blockchain they are part of.
class Wallet:
    def __init__(self, address):
        self.address = address

# LUNA wallet class. Inherits from the Wallet class.
# Pricing data and wallet balance data come from fcd.terra.dev.
class LunaWallet(Wallet):
    pricingDataSource = "https://fcd.terra.dev/v1/market/swaprate/uusd"
    divFactor = 1000000

    # Constructor saves a string URL from which we can pull wallet balance data.
    # Also creates a set naming all the coins held by the wallet.
    # LUNA wallets can hold LUNA as well as other coins (Terra stablecoins and other tokens).
    def __init__(self, address):
        super().__init__(address)
        self.balanceDataSource = "https://fcd.terra.dev/v1/bank/" + self.address
        self.coins = self.getCoinSet()
    
    # Returns a list of dictionaries. Each dictionary represents one of the coins held by the wallet.
    # For example, the LUNA dictionary will have 'denom' 'LUNA' and 'available' equal to the balance of LUNA
    # held by the wallet times a constant (divFactor).
    def getLiquidBalances(self):
        return requests.get(self.balanceDataSource).json()["balance"]
    
    # Returns a list of dictionaries. Each dictionary represents a delegation of LUNA to a validator.
    # If you have delegated LUNA to several validators, you will have multiple dictionaries, one for each,
    # so to get the sum of your staked LUNA, you must add up the 'amount' fields from each dictionary.
    def getStakedBalances(self):
        return requests.get(self.balanceDataSource).json()["delegations"]
    
    # Returns a set naming all the coins held by the wallet.
    def getCoinSet(self):
        coinSet = set()
        liq = self.getLiquidBalances()
        for item in liq:
            if 'denom' in item.keys():
                coinSet.add(item['denom'])
        return coinSet

    # Returns the balance of a particular coin held by the wallet. liq and stk are lists of
    # dictionaries in the format output by the functions getLiquidBalances() and getStakedBalances().
    # They're parameters here because, when we get the total wallet value, we have to call
    # this function for each coin held by the wallet. If we called getLiquidBalances() and
    # getStakedBalances() each time, that would be horribly inefficient. Instead, when we are
    # iterating over all the coins in the coins set, we get the data once, and then pass it in
    # as parameters.
    def getCoinBalance(self, coin, liq=None, stk=None):
        bal = 0
        if liq == None:
            liq = self.getLiquidBalances()
        if stk == None:
            stk = self.getStakedBalances()
        for item in liq:
            if item['denom'] == coin:
                bal += float(item['available'])
                break
        if coin == 'uluna':
            for item in stk:
                bal += float(item['amount'])
        return bal / self.divFactor

    # Returns a dictionary whose keys are the names of coins and whose values are the prices of
    # those coins in USD (or, more precisely, the UST stablecoin). The number is inverted here
    # because the data are given as coin per $ instead of $ per coin, which is what we need.
    def getPrices(self):
        prices = {}
        datastream = requests.get(self.pricingDataSource).json()
        for item in datastream:
            prices[item['denom']] = 1 / float(item['swaprate'])
        return prices
    
    # Returns the price of a particular coin in USD (again really UST). Allows price data
    # to be passed in as a parameter to save on computation.
    def getCoinPrice(self, coin, prices=None):
        if coin == 'uusd':
            return 1.0
        if prices == None:
            prices = self.getPrices()
        return prices[coin]

    # Returns the total value of all coins held by the wallet.     
    def getWalletValue(self):
        total = 0
        prices = self.getPrices()
        liq = self.getLiquidBalances()
        stk = self.getStakedBalances()
        for coin in self.coins:
            if coin != 'ibc/0471F1C4E7AFD3F07702BEF6DC365268D64570F7C1FDC98EA6098DD6DE59817B':
                price = self.getCoinPrice(coin, prices)
                quantity = self.getCoinBalance(coin, liq, stk)
                total += price * quantity
        return total

# SOL wallet class. Inherits from the Wallet class.
# Pricing data from coingecko.com. Wallet balance data from prod-api.solana.surf.
class SolWallet(Wallet):
    coins = set("SOL")
    divFactor = 1000000000
    pricingDataSource = "https://api.coingecko.com/api/v3/coins/solana"

    # Constructor saves a string URL from which we can pull wallet balance data and staking data.
    def __init__(self, address):
        super().__init__(address)
        self.balanceDataSource = "https://prod-api.solana.surf/v1/account/" + self.address
        self.stakingDataSource = "https://prod-api.solana.surf/v1/account/" + self.address + "/stakes?limit=10&offset=0"
    
    # Returns a dictionary whose keys are coins held by the wallet and whose values are the liquid balances of such coins.
    def getLiquidBalances(self):
        return {'SOL': requests.get(self.balanceDataSource).json()['value']['base']['balance'] / self.divFactor}

    # Same as above, but staked balances instead of liquid balances.
    def getStakedBalances(self):
        response = requests.get(self.stakingDataSource).json()
        total = 0
        for dict in response['data']:
            total += dict['lamports']
        return {'SOL': total / self.divFactor}

    # Returns the current price of Solana coins.
    def getPrice(self):
        return requests.get(self.pricingDataSource).json()["market_data"]["current_price"]["usd"]
    
    # Returns the total value of the Solana wallet.
    def getWalletValue(self):
        price = self.getPrice()
        quantity = self.getLiquidBalances()['SOL'] + self.getStakedBalances()['SOL']
        return price * quantity

# Gets coin names and wallet addresses from user. Returns a list of wallet objects.
def getWallets():
    lst = []
    while True:
        coin = input("Please input the coin this wallet contains (LUNA or SOL): ")
        s = input("Please input your public wallet address: ")
        coin = coin.strip().upper()
        s = s.strip()
        if coin == 'LUNA':
            lst.append(LunaWallet(s))
        elif coin == 'SOL':
            lst.append(SolWallet(s))
        done = False
        while True:
            anotherWallet = input("Another wallet? y/n: ")
            if anotherWallet == "y" or anotherWallet == "Y":
                break
            if anotherWallet == "n" or anotherWallet == "N":
                done = True
                break
        if done:
            break
    return lst

# Sums the values of all wallets in a list.
def sumAllWallets(wallets):
    total = 0
    for wallet in wallets:
        total += wallet.getWalletValue()
    return total

# Formats a numerical sum as a USD string (e.g. $x,xxx.xx).
def formatUsd(amount):
    return '${:,.2f}'.format(amount)

main()
