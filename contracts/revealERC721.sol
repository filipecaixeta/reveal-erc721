// SPDX-License-Identifier: MIT
// If you use this smart contract, please cite it as below.
// author: Filipe Caixeta
// github: https://github.com/filipecaixeta
pragma solidity ^0.8.2;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/interfaces/IERC2981.sol";
import "@chainlink/contracts/src/v0.8/VRFConsumerBase.sol";


/*
* @title Reveal ERC721 using oracle
* @author Filipe Caixeta
* @notice Use this contract if you want to mint NFTs and reveal them later
* @dev Mint the tokens and call getRandomNumber when you decide to reveal, after the random number is fulfilled call revealTokens
*/
contract RevealERC721 is
    ERC721,
    IERC2981,
    Pausable,
    Ownable,
    VRFConsumerBase
{
    using Strings for uint256;
    enum ContractState {NOT_REVEALED,REVEALED,CALCULATING}

    event RequestedRandomness(bytes32 requestID);

    string public baseURI;
    string public collectionName;
    uint256 public randomResult;
    ContractState public contractState;

    uint256[] private tokenIDs;
    uint256 private linkFee;
    bytes32 private linkKeyhash;
    uint256 private royalt;

    constructor(
        string memory _collectionName,
        string memory _baseURI,
        address _vrfCoordinator,
        address _link,
        uint256 _linkFee,
        bytes32 _linkKeyhash
    ) 
    VRFConsumerBase(_vrfCoordinator, _link) 
    ERC721(_collectionName, "NFT") 
    {
        contractState = ContractState.NOT_REVEALED;
        baseURI = _baseURI;
        collectionName = _collectionName;
        linkFee = _linkFee;
        linkKeyhash = _linkKeyhash;
    }

    function mint(
        address to,
        uint256 amount
    ) 
    public onlyOwner 
    {
        require(
            contractState == ContractState.NOT_REVEALED,
            "Tokens can only be minted before reveal"
        );
        uint256 idOffset = tokenIDs.length+1;
        for (uint256 i = 0; i < amount; i++) {
            tokenIDs.push(idOffset+i);
            _safeMint(to, tokenIDs.length);
        }
    }

    function contractURI() 
    public view 
    returns (string memory) 
    {
        // https://docs.opensea.io/docs/contract-level-metadata
        return string(abi.encodePacked(baseURI,"contract.json"));
    }

    /*
    * @dev Royalty is in percentange, 100 = 1%
    */
    function setRoyalty(
        uint256 _royalt
    )
    public onlyOwner
    {
        royalt = _royalt;
    }

    function royaltyInfo(
        uint256 _tokenId,
        uint256 _salePrice
    )
    external view override
    returns (address,uint256)
    {
        return (owner(), _salePrice/10000*royalt);
    }

    function fulfillRandomness(
        bytes32 _requestId, 
        uint256 _randomness
    )
    internal override
    {
        require(randomResult == 0, "randomResult is already set");
        require(_randomness > 0, "random not found");
        randomResult = _randomness;
    }

    function getRandomNumber() 
    public onlyOwner 
    {
        require(LINK.balanceOf(address(this)) >= linkFee, "Not enough LINK");
        contractState = ContractState.CALCULATING;
        bytes32 requestID = requestRandomness(linkKeyhash, linkFee);
        emit RequestedRandomness(requestID);
    }

    function revealTokens() 
    public onlyOwner 
    {
        require(
            contractState == ContractState.CALCULATING,
            "Wrong contract state"
        );
        require(randomResult != 0, "Invalid random number");
        // Shuffle the IDs
        for (uint256 i = 0; i < tokenIDs.length; i++) {
            uint256 rand = uint256(
                keccak256(abi.encodePacked(i, randomResult))
            );
            uint256 n = i + (rand % (tokenIDs.length - i));
            uint256 temp = tokenIDs[n];
            tokenIDs[n] = tokenIDs[i];
            tokenIDs[i] = temp;
        }
        contractState = ContractState.REVEALED;
    }

    function tokenURI(
        uint256 tokenID
    )
    public view virtual override
    returns (string memory)
    {
        require(
            _exists(tokenID),
            "ERC721Metadata: URI query for nonexistent token"
        );
        return string(
            abi.encodePacked(
                baseURI,
                contractState == ContractState.REVEALED ? "reveal/": "noreveal/",
                tokenIDs[tokenID - 1].toString(),
                ".json"
            )
        );
    }

    function totalSupply() 
    public view 
    returns (uint256) 
    {
        return tokenIDs.length;
    }

    function pause() 
    public onlyOwner 
    {
        _pause();
    }

    function unpause() 
    public onlyOwner 
    {
        _unpause();
    }

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId
    ) 
    internal whenNotPaused override 
    {
        super._beforeTokenTransfer(from, to, tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, IERC165)
        returns (bool)
    {
        return interfaceId == type(IERC2981).interfaceId || super.supportsInterface(interfaceId);
    }

}
