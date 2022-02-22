import brownie
from brownie import accounts, config, RevealERC721, network
from scripts.helpers.contracts import get_contract, fund_with_link


def get_tokens_ids(ct):
    totalSupply = ct.totalSupply()
    return [int(ct.tokenURI(token_id+1).split("/")[-1].split(".json")[0]) for token_id in range(totalSupply)]


def get_tokens_uri(ct):
    totalSupply = ct.totalSupply()
    return [ct.tokenURI(token_id+1) for token_id in range(totalSupply)]


def test_normal_workflow():
    account0 = accounts.add(config["wallets"]["from_key"])
    collectionName: str = "Collection"
    baseURI: str = "ipfs://12345/"
    vrfCoordinator = get_contract("VRFCoordinator", account0)
    link = get_contract("LinkToken", account0)
    linkFee = config["networks"][network.show_active()]["fee"]
    linkKeyhash = config["networks"][network.show_active()]["keyhash"]

    ct = RevealERC721.deploy(
        collectionName, baseURI, vrfCoordinator.address, link.address, linkFee, linkKeyhash,
        {"from": account0},
        publish_source=False
    )

    # Initial values
    assert ct.name() == collectionName
    assert ct.balance() == 0
    assert ct.balanceOf(account0.address) == 0
    assert ct.paused() is False
    assert ct.owner() == account0.address
    assert ct.totalSupply() == 0
    assert ct.contractState() == 0

    with brownie.reverts("ERC721Metadata: URI query for nonexistent token"):
        ct.tokenURI(1)

    # Owner Minting
    amount = 50
    ct.mint(account0.address, amount, {"from": account0})
    assert ct.totalSupply() == amount
    assert ct.balanceOf(account0.address) == amount
    ids = get_tokens_ids(ct)
    assert ids == list(range(1,51))

    # Not owner minting
    with brownie.reverts("Ownable: caller is not the owner"):
        ct.mint(accounts[1].address, 1, {"from": accounts[1]})

    # No reveal URIs
    uris = get_tokens_uri(ct)
    assert [baseURI+"noreveal/"+str(id)+".json" for id in ids] == uris

    # Not owner reveal
    with brownie.reverts("Ownable: caller is not the owner"):
        ct.revealTokens({"from": accounts[1]})

    # Reveal before random number
    with brownie.reverts("Wrong contract state"):
        ct.revealTokens({"from": account0})

    # Get random number without enough LINK
    with brownie.reverts("Not enough LINK"):
        ct.getRandomNumber({"from": account0})

    # Found the contract and get the random number
    tx = fund_with_link(ct.address, account0, link, linkFee)
    tx.wait(1)
    tx = ct.getRandomNumber({"from": account0})
    tx.wait(1)
    assert ct.contractState() == 2

    # Run the vrfCoordinator mock, only for local tests
    request_id = tx.events["RequestedRandomness"]["requestID"]
    rand = 57960407935404775673433170853203864526063280851215043454225382818284790976260
    tx = vrfCoordinator.callBackWithRandomness(request_id, rand, ct.address, {"from": account0})
    assert ct.randomResult() != 0

    # Reveal the tokens
    ct.revealTokens({"from": account0})
    assert ct.balanceOf(account0.address) == amount
    
    # Try to reveal twice
    with brownie.reverts("Wrong contract state"):
        ct.revealTokens({"from": account0})

    # We don't allow minting after reveal
    with brownie.reverts("Tokens can only be minted before reveal"):
        ct.mint(account0.address, 1, {"from": account0})

    # Check shuffled ids
    idsShuffled = get_tokens_ids(ct)
    assert idsShuffled != ids
    assert sorted(idsShuffled) == sorted(ids)

    # Check reveal uris
    uris = get_tokens_uri(ct)
    assert [baseURI+"reveal/"+str(id)+".json" for id in idsShuffled] == uris

    # Check nft transfer
    ct.transferFrom(account0.address, accounts[1].address, 1, {'from': account0})
    ct.transferFrom(accounts[1].address, accounts[2].address, 1, {'from': accounts[1]})
    ct.transferFrom(account0.address, accounts[2].address, 2, {'from': account0})
    assert ct.balanceOf(account0.address) == amount-2
    assert ct.balanceOf(accounts[1].address) == 0
    assert ct.balanceOf(accounts[2].address) == 2

    # Try to transfer a token that the account is not the owner
    with brownie.reverts("ERC721: transfer caller is not owner nor approved"):
        ct.transferFrom(accounts[1].address, accounts[2].address, 1, {'from': accounts[1]})

    # Contract owner try to transfer a token from another owner
    with brownie.reverts("ERC721: transfer caller is not owner nor approved"):
        ct.transferFrom(accounts[2].address, accounts[3].address, 1, {'from': account0})

    # Allow an account to transfer tokens
    approved = ct.isApprovedForAll(accounts[2].address, account0.address)
    assert approved == False
    ct.setApprovalForAll(account0.address, True, {'from': accounts[2]})
    approved = ct.isApprovedForAll(accounts[2].address, account0.address)
    assert approved == True
    ct.transferFrom(accounts[2].address, accounts[4].address, 1, {'from': account0})

    # Test revoke permission
    ct.setApprovalForAll(account0.address, False, {'from': accounts[2]})
    with brownie.reverts("ERC721: transfer caller is not owner nor approved"):
        ct.transferFrom(accounts[2].address, accounts[4].address, 2, {'from': account0})

    # Test interfaces
    supported_interface_ids = {
        "ERC721": 0x80ac58cd,         # Non-Fungible Token Standard
        "ERC721Metadata": 0x5b5e139f, # Non-Fungible Token Standard, optional metadata extension
        "IERC2981": 0x2a55205a,       # NFT Royalty Standard
        "EIP165": 0x01ffc9a7,         # Standard Interface Detection
    }
    for interface, id in supported_interface_ids.items():
        assert ct.supportsInterface(id) == True, "supportsInterface: "+interface

    # Test royalt
    sale_price = 100000
    assert ct.royaltyInfo(1, sale_price) == (account0.address, sale_price*0)
    with brownie.reverts("Ownable: caller is not the owner"):
        ct.setRoyalty(200, {"from": accounts[1]})
    ct.setRoyalty(200, {'from': account0})
    assert ct.royaltyInfo(1, sale_price) == (account0.address, sale_price*0.02)