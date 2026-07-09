import forge from 'node-forge';

const DEFAULT_LOGIN_KEY_ID = 'login-rsa-dev-2026-07';
const DEFAULT_LOGIN_PUBLIC_KEY = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtLxzv3ZmRWhtR524kKlW
r66VMw8NzRP1BhLCYGOT5WPQjwFnz7tVm8u0S0/cAUbxxApbtkT+7+ZMEayETh/t
pXecwIQ6EfBVqzCxM5+T1Ma10Zy/NGtVzFxEKbEw8UJay9LgOybBFF5RFg4g4CNB
n0DO3GOi6AGdaOBW2vcy11SpRX7uvQnTA1s+/xKqHuujEKWAn5RDh7pwIep9NC00
Jm35muTYVhBzSEh0GDJ0/uWhTBKmaQkkxMKNBYZz0upVDWFqVb6l/cXM/5Ep9Bpi
GGfNyZnoHhie8XcmKrXTkWdj600X9K+IV5ea/fLqBtOcVNOIWhH4Bx+O0OULMgEt
qQIDAQAB
-----END PUBLIC KEY-----`;
const DEFAULT_LOGIN_PUBLIC_KEY_FINGERPRINT = 'cbffTkg1lSQUfA56sBVNFdF1HIfyUgST4hDUdr-wlyk';

function normalizePem(value) {
  return (value || '').replace(/\\n/g, '\n').trim();
}

function base64Url(bytes) {
  return forge.util.encode64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

export function getPinnedLoginKey() {
  return {
    keyId: process.env.REACT_APP_SECURE_LOGIN_KEY_ID || DEFAULT_LOGIN_KEY_ID,
    publicKeyPem: normalizePem(process.env.REACT_APP_SECURE_LOGIN_PUBLIC_KEY || DEFAULT_LOGIN_PUBLIC_KEY),
    fingerprint:
      process.env.REACT_APP_SECURE_LOGIN_PUBLIC_KEY_FINGERPRINT ||
      DEFAULT_LOGIN_PUBLIC_KEY_FINGERPRINT
  };
}

export function fingerprintPublicKey(publicKeyPem) {
  const publicKey = forge.pki.publicKeyFromPem(publicKeyPem);
  const publicKeyInfo = forge.pki.publicKeyToAsn1(publicKey);
  const der = forge.asn1.toDer(publicKeyInfo).getBytes();
  const digest = forge.md.sha256.create();
  digest.update(der);
  return base64Url(digest.digest().getBytes());
}

export function assertPinnedLoginKey() {
  const pinned = getPinnedLoginKey();
  const actualFingerprint = fingerprintPublicKey(pinned.publicKeyPem);
  if (actualFingerprint !== pinned.fingerprint) {
    throw new Error('登录公钥指纹不匹配');
  }
  return pinned;
}

function encryptAesGcm(data, key, iv, aad) {
  const plaintext = typeof data === 'string' ? data : JSON.stringify(data);
  const cipher = forge.cipher.createCipher('AES-GCM', key);
  cipher.start({
    iv,
    additionalData: aad,
    tagLength: 128
  });
  cipher.update(forge.util.createBuffer(plaintext, 'utf8'));
  cipher.finish();
  return forge.util.encode64(cipher.output.getBytes() + cipher.mode.tag.getBytes());
}

function decryptAesGcm(encryptedBase64, key, ivBase64, aad) {
  const combined = forge.util.decode64(encryptedBase64);
  const tag = combined.slice(-16);
  const ciphertext = combined.slice(0, -16);
  const decipher = forge.cipher.createDecipher('AES-GCM', key);
  decipher.start({
    iv: forge.util.decode64(ivBase64),
    additionalData: aad,
    tag: forge.util.createBuffer(tag),
    tagLength: 128
  });
  decipher.update(forge.util.createBuffer(ciphertext));
  if (!decipher.finish()) {
    throw new Error('登录响应认证失败');
  }
  return JSON.parse(decipher.output.toString('utf8'));
}

export function createSecureLoginEnvelope(loginPayload) {
  const pinned = assertPinnedLoginKey();
  const aesKey = forge.random.getBytesSync(32);
  const iv = forge.random.getBytesSync(12);
  const nonce = forge.util.bytesToHex(forge.random.getBytesSync(16));
  const timestamp = Date.now();
  const aad = `${pinned.keyId}:${timestamp}:${nonce}`;
  const publicKey = forge.pki.publicKeyFromPem(pinned.publicKeyPem);
  const encryptedKey = publicKey.encrypt(aesKey, 'RSA-OAEP', {
    md: forge.md.sha256.create(),
    mgf1: {
      md: forge.md.sha256.create()
    }
  });

  return {
    request: {
      key_id: pinned.keyId,
      encrypted_key: forge.util.encode64(encryptedKey),
      iv: forge.util.encode64(iv),
      nonce,
      timestamp,
      data: encryptAesGcm(loginPayload, aesKey, iv, aad)
    },
    decryptResponse(responseEnvelope) {
      return decryptAesGcm(responseEnvelope.data, aesKey, responseEnvelope.iv, aad);
    }
  };
}
