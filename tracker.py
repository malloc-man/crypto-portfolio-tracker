import requests

def main():
    wallets = getWallets()
    total = 0
    for wallet in wallets:
        total += wallet.getWalletValue()
    return formatUsd(total)

class Wallet:
    def __init__(self, address):
        self.address = address

class LunaWallet(Wallet):
    pricingDataSource = "https://fcd.terra.dev/v1/market/swaprate/uusd"
    divFactor = 1000000

    def __init__(self, address):
        super().__init__(address)
        self.balanceDataSource = "https://fcd.terra.dev/v1/bank/" + self.address
        self.coins = self.getCoinSet()
    
    def getLiquidBalances(self):
        return requests.get(self.balanceDataSource).json()["balance"]
    
    def getStakedBalances(self):
        return requests.get(self.balanceDataSource).json()["delegations"]
    
    def getCoinSet(self):
        coinSet = set()
        liq = self.getLiquidBalances()
        for item in liq:
            if 'denom' in item.keys():
                coinSet.add(item['denom'])
        return coinSet
    
    def getCoinBalance(self, coin):
        bal = 0
        liq = self.getLiquidBalances()
        stk = self.getStakedBalances()
        for item in liq:
            if item['denom'] == coin:
                bal += float(item['available'])
                break
        if coin == 'uluna':
            for item in stk:
                bal += float(item['amount'])
        return bal / self.divFactor

    def getCoinBalanceCached(self, coin, liq_cache, stk_cache):
        bal = 0
        for item in liq_cache:
            if item['denom'] == coin:
                bal += float(item['available'])
                break
        if coin == 'uluna':
            for item in stk_cache:
                bal += float(item['amount'])
        return bal / self.divFactor

    def getPrices(self):
        prices = {}
        datastream = requests.get(self.pricingDataSource).json()
        for item in datastream:
            prices[item['denom']] = 1 / float(item['swaprate'])
        return prices

    def getCoinPrice(self, coin):
        return self.getPrices()[coin]
    
    def getCoinPriceCached(self, coin, cache):
        return cache[coin]
        
    def getWalletValue(self):
        total = 0
        prices = self.getPrices()
        liq = self.getLiquidBalances()
        stk = self.getStakedBalances()
        for coin in self.coins:
            if coin != 'uusd' and coin != 'ibc/0471F1C4E7AFD3F07702BEF6DC365268D64570F7C1FDC98EA6098DD6DE59817B':
                price = self.getCoinPriceCached(coin, prices)
                quantity = self.getCoinBalanceCached(coin, liq, stk)
                total += price * quantity
        return total
    
class SolWallet(Wallet):
    coins = set("SOL")
    divFactor = 1000000000
    pricingDataSource = "https://api.coingecko.com/api/v3/coins/solana"

    def __init__(self, address):
        super().__init__(address)
        self.balanceDataSource = "https://prod-api.solana.surf/v1/account/" + self.address
        self.stakingDataSource = "https://prod-api.solana.surf/v1/account/" + self.address + "/stakes?limit=10&offset=0"
    
    def getLiquidBalances(self):
        return {'SOL': requests.get(self.balanceDataSource).json()['value']['base']['balance'] / self.divFactor}

    def getStakedBalances(self):
        response = requests.get(self.stakingDataSource).json()
        total = 0
        for dict in response['data']:
            total += dict['lamports']
        return {'SOL': total / self.divFactor}

    def getPrice(self):
        return requests.get(self.pricingDataSource).json()["market_data"]["current_price"]["usd"]
    
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

# Formats a numerical sum as a USD string (e.g. $x,xxx.xx).
def formatUsd(amount):
    return '${:,.2f}'.format(amount)
    
print(main())
