from base64 import urlsafe_b64decode, urlsafe_b64encode


TOKEN_PREFIX = "knowledge-token:"


# ä¸ºå½åç¨æ·çæä¸ä¸ªè½»éæ¼ç¤º tokenã
def create_token(user_id: str) -> str:
    # 当前 V1 使用的是最轻量的演示 token，不是正式 JWT。
    payload = f"{TOKEN_PREFIX}{user_id}".encode("utf-8")
    return urlsafe_b64encode(payload).decode("utf-8")


# ä»æ¼ç¤º token ä¸­è¿åç¨æ· idã
def decode_token(token: str) -> str | None:
    # 从前端 token 里还原 user_id。
    try:
        payload = urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
    except Exception:
        return None

    if not payload.startswith(TOKEN_PREFIX):
        return None
    return payload.replace(TOKEN_PREFIX, "", 1)
