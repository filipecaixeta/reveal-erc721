from pydantic import BaseModel
from copy import deepcopy
from typing import List, Tuple, Dict, Any, Optional
from scripts.helpers.nft_storage_helper import upload_to_ipfs
import shutil
import json
import os


class ContractMetadata(BaseModel):
    name: str
    description: str
    image: str
    external_link: str
    seller_fee_basis_points: int
    fee_recipient: str


class TokenMetadata(BaseModel):
    name: str
    description: Optional[str]
    image: Optional[str]
    animation_url: Optional[str]
    background_color: Optional[str]
    external_uri: Optional[str]
    attributes: Dict[str, Any] = {}


class Token(BaseModel):
    metadata: TokenMetadata
    amount: int = 0


# upload_tokens upload metadata and images to ipfs
def upload_tokens(
    no_reveal_tokens: List[Token],
    reveal_tokens: List[Token],
    contract_metadata: ContractMetadata,
    baseURL: str = "ipfs://",
) -> Tuple[str, str]:
    if len(no_reveal_tokens) == 1:
        for _ in reveal_tokens[1:]:
            no_reveal_tokens.append(deepcopy(no_reveal_tokens[0]))
    if len(no_reveal_tokens) != len(reveal_tokens):
        raise "Wrong no_reveal_tokens size"

    tmp_ipfs = "../../tmp/ipfs"
    shutil.rmtree(tmp_ipfs, ignore_errors=True)

    # Copy images to a temp folder
    os.makedirs(f"{tmp_ipfs}/img/noreveal")
    os.makedirs(f"{tmp_ipfs}/img/reveal")
    token_id = 1
    for reveal_token, no_reveal_token in zip(reveal_tokens, no_reveal_tokens):
        img_name = f"noreveal/{token_id}.{no_reveal_token.metadata.image.split('.')[-1]}"
        shutil.copyfile(no_reveal_token.metadata.image, f"{tmp_ipfs}/img/{img_name}")
        no_reveal_token.metadata.image = img_name

        img_name = f"reveal/{token_id}.{reveal_token.metadata.image.split('.')[-1]}"
        shutil.copyfile(reveal_token.metadata.image, f"{tmp_ipfs}/img/{img_name}")
        reveal_token.metadata.image = img_name

        token_id += 1

    img_name = "contract."+contract_metadata.image.split('.')[-1]
    shutil.copyfile(contract_metadata.image, f"{tmp_ipfs}/img/{img_name}")
    contract_metadata.image = img_name

    # Upload the images to IPFS
    url = upload_to_ipfs(f"{tmp_ipfs}/img/", wrapWithDirectory=False)
    for reveal_token, no_reveal_token in zip(reveal_tokens, no_reveal_tokens):
        no_reveal_token.metadata.image = f"{baseURL}{url}/{no_reveal_token.metadata.image}"
        reveal_token.metadata.image = f"{baseURL}{url}/{reveal_token.metadata.image}"
    contract_metadata.metadata.image = f"{baseURL}{url}/{contract_metadata.metadata.image}"

    # Generate metadata
    os.makedirs(f"{tmp_ipfs}/metadata/noreveal")
    os.makedirs(f"{tmp_ipfs}/metadata/reveal")

    token_id = 1
    for reveal_token, no_reveal_token in zip(reveal_tokens, no_reveal_tokens):
        with open(f"{tmp_ipfs}/metadata/noreveal/{token_id}.json", "w") as f:
            f.write(json.dumps(no_reveal_token.metadata.dict(exclude_none=True, exclude_defaults=True, exclude_unset=True)))
        with open(f"{tmp_ipfs}/metadata/reveal/{token_id}.json", "w") as f:
            f.write(json.dumps(reveal_token.metadata.dict(exclude_none=True, exclude_defaults=True, exclude_unset=True)))
        token_id += 1

    with open(f"{tmp_ipfs}/metadata/contract.json", "w") as f:
        f.write(json.dumps(contract_metadata.dict(exclude_none=True, exclude_defaults=True, exclude_unset=True)))

    # Upload metadata
    url = upload_to_ipfs(f"{tmp_ipfs}/metadata/", wrapWithDirectory=False)

    return f"{baseURL}{url}/"
