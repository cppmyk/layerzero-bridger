from logic import AccountThread
from config import check_configuration, load_private_keys

if __name__ == "__main__":
    check_configuration()

    accounts = []

    for account_id, private_key in enumerate(load_private_keys()):
        accounts.append(AccountThread(account_id, private_key))
        accounts[account_id].start()

    for account in accounts:
        account.join()
