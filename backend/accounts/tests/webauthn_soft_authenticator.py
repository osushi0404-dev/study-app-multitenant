"""テスト用のソフトの認証器（I619）

本物の py_webauthn の検証を通る、登録（attestation `none`）とログイン（assertion）の応答を作る。
ブラウザの `PublicKeyCredential.toJSON()` と同じ形の dict を返す。検証は差し替えない。
"""
import hashlib
import json
import os
from base64 import urlsafe_b64encode

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

FLAG_UP = 0x01
FLAG_UV = 0x04
FLAG_AT = 0x40


def b64url(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b'=').decode()


class SoftAuthenticator:
    def __init__(self, *, rp_id: str = 'localhost', origin: str = 'http://localhost:3000',
                 sign_count: int = 0):
        self.rp_id = rp_id
        self.origin = origin
        self.sign_count = sign_count
        self.credential_id = os.urandom(32)
        self._key = ec.generate_private_key(ec.SECP256R1())

    def _cose_public_key(self) -> bytes:
        numbers = self._key.public_key().public_numbers()
        return cbor2.dumps({
            1: 2, 3: -7, -1: 1,
            -2: numbers.x.to_bytes(32, 'big'),
            -3: numbers.y.to_bytes(32, 'big'),
        })

    def _client_data(self, kind: str, challenge: str, origin: str | None) -> bytes:
        return json.dumps({
            'type': kind, 'challenge': challenge, 'origin': origin or self.origin,
            'crossOrigin': False,
        }).encode()

    @staticmethod
    def _flags(uv: bool, extra: int = 0) -> int:
        return FLAG_UP | (FLAG_UV if uv else 0) | extra

    def _credential(self, response: dict) -> dict:
        return {
            'id': b64url(self.credential_id), 'rawId': b64url(self.credential_id),
            'type': 'public-key', 'authenticatorAttachment': 'platform',
            'clientExtensionResults': {}, 'response': response,
        }

    def registration_response(self, challenge: str, *, origin: str | None = None,
                              uv: bool = True) -> dict:
        """登録の応答。challenge は options の `challenge`（base64url の文字列）。署名回数は今の値"""
        auth_data = (
            hashlib.sha256(self.rp_id.encode()).digest()
            + bytes([self._flags(uv, FLAG_AT)])
            + self.sign_count.to_bytes(4, 'big')
            + bytes(16)  # AAGUID（attestation none なので 0）
            + len(self.credential_id).to_bytes(2, 'big')
            + self.credential_id
            + self._cose_public_key()
        )
        attestation = cbor2.dumps({'fmt': 'none', 'attStmt': {}, 'authData': auth_data})
        client_data = self._client_data('webauthn.create', challenge, origin)
        return self._credential({
            'clientDataJSON': b64url(client_data),
            'attestationObject': b64url(attestation),
            'transports': ['internal'],
        })

    def assertion_response(self, challenge: str, *, user_handle: bytes | None,
                           origin: str | None = None, uv: bool = True,
                           sign_count: int | None = None) -> dict:
        """ログイン・本人確認の応答。sign_count を省くと、持っている回数を 1 増やして使う"""
        if sign_count is None:
            self.sign_count += 1
            sign_count = self.sign_count
        auth_data = (
            hashlib.sha256(self.rp_id.encode()).digest()
            + bytes([self._flags(uv)])
            + sign_count.to_bytes(4, 'big')
        )
        client_data = self._client_data('webauthn.get', challenge, origin)
        signature = self._key.sign(auth_data + hashlib.sha256(client_data).digest(),
                                   ec.ECDSA(hashes.SHA256()))
        response = {
            'clientDataJSON': b64url(client_data),
            'authenticatorData': b64url(auth_data),
            'signature': b64url(signature),
        }
        if user_handle is not None:
            response['userHandle'] = b64url(user_handle)
        return self._credential(response)
