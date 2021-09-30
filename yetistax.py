##########################################################################
#  YetiStax Compounder v0.1a
#  - uses Python3
#  - Install web3 using pip
#  - Really, we haven't tested this on anything but linux or WSL
#  - Use at your own risk
#  - this code is not optimized.  Its hacked together from other scripts
#  - Use at your own risk
#
##########################################################################
import os
import json
import asyncio
import logging
from decimal import Decimal
from urllib.request import urlopen, Request
from web3 import Web3
from web3.middleware import geth_poa_middleware

# Setup logging
log_format = '%(levelname)s:%(asctime)s: %(message)s'

logging.basicConfig(level=logging.INFO,format=log_format)

logging.info('Reading config')

"""" Add your wallet's private Key """
your_wallet_key = 'insertYourWalletPrivateKeyHere'
MinBlizzardCompound = 15
PollSeconds = 300

compound_pct = Decimal('.01')
# RPC to access Binance Smart Chain
rpc_uri = 'https://bsc-dataseed3.ninicoin.io/'

# Contract Info
seekContract = '0x03414b0E526A5D6C2E1fC813724448a871598287'
abiContract = '[{"constant":true,"inputs":[],"name":"ceoAddress","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getMyMiners","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getMyBlizzard","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getBalance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"initialized","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"blizzardMiners","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"sellBlizzard","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"rt","type":"uint256"},{"name":"rs","type":"uint256"},{"name":"bs","type":"uint256"}],"name":"calculateTrade","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"claimedBlizzard","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"eth","type":"uint256"},{"name":"contractBalance","type":"uint256"}],"name":"calculateBlizzardBuy","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"amount","type":"uint256"}],"name":"devFee","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"pure","type":"function"},{"constant":true,"inputs":[{"name":"adr","type":"address"}],"name":"getblizzardsinceBake","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"blizzardBake","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"ref","type":"address"}],"name":"compoundBlizzard","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"BLIZZARD_TO_BAKE_MINERS","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"referrals","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"amount","type":"uint256"}],"name":"seedBlizzard","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"marketBlizzard","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"ref","type":"address"},{"name":"amount","type":"uint256"}],"name":"investBlizzard","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"ceoAddress2","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"eth","type":"uint256"}],"name":"calculateBlizzardBuySimple","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"blizzard","type":"uint256"}],"name":"calculateBlizzardSell","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[],"payable":false,"stateMutability":"nonpayable","type":"constructor"}]'

"""" No need to touch anything after this """

precision = Decimal(1e18)
web3 = Web3(Web3.HTTPProvider(rpc_uri))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

def execute_transaction(call, target_account):
    logging.info(f'\texecute_transaction call={call}, target_account={target_account}')
    nonce = web3.eth.getTransactionCount(target_account.address)
    build = call.buildTransaction({'from': target_account.address, 'nonce': nonce, 'gasPrice': 5000000000})
    sign = target_account.sign_transaction(build)

    args = dict(zip([x['name'] for x in call.abi['inputs']], call.args))
    print(f'{target_account.address}: {call.address} {call.fn_name} with args {str(args)}')
    transaction = web3.eth.sendRawTransaction(sign.rawTransaction)
    if transaction:
        return transaction

account = web3.eth.account.from_key(your_wallet_key)

logging.info(f'\tMy Account: {account.address}')

""" Get the ABI for the existing contracts on BSC"""
pit_address = seekContract
pit_abi = abiContract

pit = web3.eth.contract(pit_address, abi=pit_abi)
#deposit = pit.functions.userInfo(0, account.address).call()[0]
yeti = pit.functions.blizzardMiners(account.address).call()
logging.info(f'\tMy current yeti: {yeti}')

async def check_for_compound(poll_interval):
    global deposit
    while True:
        pending = pit.functions.getblizzardsinceBake(account.address).call()
        sellamount = pit.functions.calculateBlizzardSell(pending).call()
        NewPending = (sellamount/1000000000000000000)
        # approximation.  close enough...
        pending = (NewPending * 0.95)

        if pending < MinBlizzardCompound:
            logging.info(f'\tPending [{pending}] less than min [{MinBlizzardCompound}]')
        else:
            run_compound = pit.functions.compoundBlizzard(account.address)
            # run_compound = pit.functions.enterStaking(pending)
            txn = execute_transaction(run_compound, account)

            print(web3.eth.waitForTransactionReceipt(txn))
            #deposit += pending
            yeti = pit.functions.blizzardMiners(account.address).call()
            logging.info(f'\tMy current yeti: {yeti}')
            
        await asyncio.sleep(poll_interval)

event_handler = asyncio.get_event_loop()

try:
    event_handler.run_until_complete(check_for_compound(PollSeconds))
except KeyboardInterrupt:
    pass
