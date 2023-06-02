from logger import setup_logger
from logic import AccountThread
from config import check_configuration, load_private_keys

if __name__ == "__main__":
    setup_logger()
    check_configuration()

    accounts = []

    for account_id, private_key in enumerate(load_private_keys()):
        accounts.append(AccountThread(account_id, private_key))
        accounts[account_id].start()

    if not accounts:
        raise Exception("No accounts found")

    for account in accounts:
        account.join()
