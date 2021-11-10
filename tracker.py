import requests

def main():
    wallets = getWallets()
    total = 0
    for wallet in wallets:
        if 'LUNA' in wallet.keys():
            total += getTerraWalletValue(wallet['LUNA'])
    return formatUsd(total)

# Gets coin names and wallet addresses from user.
# Returns a list of dictionaries. Each dictionary consists of a single key-value pair.
# The key is a string representing the coin name (e.g. LUNA).
# The value is the wallet address.
def getWallets():
    lst = []
    while True:
        coin = input("Please input the coin this wallet contains (e.g. BTC, ETH): ") # only works for LUNA right now
        s = input("Please input your public wallet address: ")
        lst.append({coin.strip().upper(): s.strip()})
        anotherWallet = input("Another wallet? y/n: ")
        if anotherWallet == "n" or anotherWallet == "N":
            break
    return lst

# Takes in a string representing a Terra wallet address 
# and returns the value of the coins held by that wallet.
def getTerraWalletValue(wallet):
    wallet_datastream = getTerraWalletData(wallet)
    swaprates = constructSwapRateDict()

    retrieved_balances = wallet_datastream["balance"]
    retrieved_delegations = wallet_datastream["delegations"]

    balances = constructWalletBalanceDict(retrieved_balances, retrieved_delegations)

    return calculateSum(balances, swaprates)

# Queries Terra data source for balances of coins in wallet.
# Returns a dictionary containing four keys: balance, vesting, delegations, and unbonding.
def getTerraWalletData(wallet):
    response = requests.get("https://fcd.terra.dev/v1/bank/" + wallet)
    return response.json()

# Queries Terra market data for price of coins denominated in USD (UST).
# Returns a list of dictionaries, one for each coin.
# Each coin's dictionary has the keys 'denom', 'swaprate', 'oneDayVariation', and 'oneDayVariationRate'.
# The most relevant ones here are 'denom' (the name of the coin) and 'swaprate' (how much of that coin to buy 1 UST).
def getTerraMarketData():
    return requests.get("https://fcd.terra.dev/v1/market/swaprate/uusd").json()

# Returns a dictionary whose keys are the names of coins in the Terra swap market
# and whose values are the swap rates for that coin (how much of that coin to buy 1 UST).
def constructSwapRateDict():
    swaprates = {}
    datastream = getTerraMarketData()
    for item in datastream:
        swaprates[item['denom']] = item['swaprate']
    return swaprates

# Takes in as parameters the name of a coin and the swaprate dictionary
# and returns the swap rate for that coin.
def getSwapRate(coin, swaprates):
    for item in swaprates:
        if item == coin:
            return float(swaprates[item])

# Returns a dictionary whose keys are the names of coins owned by the wallet
# and whose values are the number of such coins in the wallet.
def constructWalletBalanceDict(retrieved_balances, retrieved_delegations):
    balances = {}
    for item in retrieved_balances:
        if item['denom'] != 'ibc/0471F1C4E7AFD3F07702BEF6DC365268D64570F7C1FDC98EA6098DD6DE59817B':
            balances[item['denom']] = round(float(item['available']) / 1000000, 6)
        if item['denom'] == 'uluna':
            luna = float(item['available']) / 1000000
    for item in retrieved_delegations:
        luna += float(item['amount']) / 1000000
    balances['uluna'] = round(luna, 6)
    return balances

# Takes in as parameters the balances dictionary (which lists how much of each coin the wallet has)
# and the swaprates dictionary (which gives how much of each coin is required to buy 1 UST)
# and returns the value in UST of the wallet's holdings.
def calculateSum(balances, swaprates):
    sum = 0
    for item in balances:
        if item != 'uusd':
            rate = getSwapRate(item, swaprates)
            sum += balances[item] / rate
    return sum

# Formats a numerical sum as a USD string (e.g. $x,xxx.xx).
def formatUsd(amount):
    return '${:,.2f}'.format(amount)
    
print(main())
