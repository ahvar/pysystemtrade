import asyncio
import logging
import time
from typing import Dict
from typing import List

import ib_insync
from ib_insync import ContractDetails
from ib_insync import Future
from ib_insync import IB

from sysbrokers.IB.config.ib_instrument_config import IBconfig, read_ib_config_from_file

HOSTNAME = "127.0.0.1"


async def subscription_test(ib_config: IBconfig) -> Dict[str, List[ContractDetails]]:
    ib_insync.util.logToConsole(logging.INFO)
    ib = IB()
    failed = []
    exceptions = []
    ib_symbols: List[str] = ib_config.IBSymbol.tolist()
    instruments: List[str] = ib_config.Instrument.tolist()
    try:
        await ib.connectAsync(host=HOSTNAME, port=4001, clientId=1, timeout=15)
        coros = []
        for i, ib_symbol in enumerate(ib_symbols):
            try:
                ib_exchange = ib_config[
                    ib_config.IBSymbol == ib_symbol
                ].IBExchange.item()
                f = Future(symbol=ib_symbol, exchange=ib_exchange, includeExpired=True)
                coros.append(ib.reqContractDetailsAsync(f))
            except Exception as e:
                failed.append(instruments[i])
                exceptions.append(str(e))
        results = await asyncio.gather(*coros)
        data = {ib: sorted_ContractDetails(cd) for ib, cd in zip(ib_symbols, results)}
    finally:
        ib.disconnect()
    return data, failed, exceptions

async def list_contracts():
    ib_insync.util.logToConsole(logging.INFO)
    ib = IB()
    try:
        await ib.connectAsync(host=HOSTNAME, port=4001, clientId=1, timeout=15)
        time.sleep(10)
        futures = await ib.reqMatchingSymbols('SMO')  # Replace 'SMO' with a more generic symbol if needed
        #futures = await ib.reqMatchingSymbols('WH')
        #futures = await ib.reqMatchingSymbols('VOLQ')
        for future in futures:
            print(future.contract)

    except Exception as e:
        print(e)
    finally:
        ib.disconnect()


def sorted_ContractDetails(contract_details: List[ContractDetails]):
    return sorted(contract_details, key=lambda x: x.realExpirationDate)


def main():
    ib_config: IBconfig = read_ib_config_from_file()
    return asyncio.run(subscription_test(ib_config))
    #return asyncio.run(list_contracts())


if __name__ == "__main__":
    main()
