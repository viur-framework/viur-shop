import typing as t


class PaymentTransactionSpecific(t.TypedDict):
    # must be set in payment provider
    payment_id: str

class PaymentTransaction(PaymentTransactionSpecific):
    # set in abstract
    payment_provider: str
    creationdate: str
    uuid: str
    client_ip: str
    user_agent: str
