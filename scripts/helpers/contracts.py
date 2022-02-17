from typing import Any
from brownie import (
    network,
    accounts,
    config,
    LinkToken,
    VRFCoordinatorMock,
    RevealERC721,
    Contract,
)

_contracts = {}


def fund_with_link(
    contract_address: str,
    account: Any,
    link_token: Contract = None,
    amount: int = 1000000000000000000,  # 1Ether
):
    link_token = link_token if link_token else get_contract("link_token")
    tx = link_token.transfer(contract_address, amount, {"from": account})
    return tx


def deploy_mock_link_token(
    account: Any
) -> Contract:
    _contracts["LinkToken"] = LinkToken.deploy({"from": account})
    return _contracts["LinkToken"]


def deploy_mock_vrf_coordinator(
    account: Any,
    link_token: Contract = None
) -> Contract:
    if not link_token:
        link_token = deploy_mock_link_token(account=account)
        _contracts["LinkToken"] = link_token
    _contracts["VRFCoordinator"] = VRFCoordinatorMock.deploy(
        link_token.address, {"from": account}
    )
    return _contracts["VRFCoordinator"]


def get_contract(
    contract_name: str,
    account: Any = None
) -> Contract:
    if network.show_active() == "development":
        if not _contracts.get(contract_name):
            if contract_name == "LinkToken":
                _contracts[contract_name] = deploy_mock_link_token(account=account)
            if contract_name == "VRFCoordinator":
                _contracts[contract_name] = deploy_mock_vrf_coordinator(account=account)
        return _contracts[contract_name]

    contract_address = config["networks"][network.show_active()][contract_name]
    c = None
    if "LinkToken":
        c = LinkToken
    elif "VRFCoordinator":
        c = VRFCoordinatorMock
    elif "RevealERC721":
        c = RevealERC721
    contract = Contract.from_abi(
        c._name, contract_address, c.abi
    )
    return contract
