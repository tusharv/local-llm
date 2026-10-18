import ipaddress
from urllib.parse import urlparse, urlunparse

class UrlPolicyError(ValueError):
    """The base URL cannot be saved under Studio's privacy rules."""


CLOUD_SUFFIXES = (
    "openai.com",
    "anthropic.com",
    "claude.ai",
    "googleapis.com",
    "mistral.ai",
    "groq.com",
    "together.ai",
    "together.xyz",
    "fireworks.ai",
    "openrouter.ai",
    "deepseek.com",
    "cohere.ai",
    "cohere.com",
    "x.ai",
    "azure.com",
    "amazonaws.com",
    "replicate.com",
    "perplexity.ai",
)

PRIVATE_DNS_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
    ".home",
    ".lan",
    ".localdomain",
)


def normalize_base_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise UrlPolicyError("A base URL is required.")
    if "://" not in text:
        text = "http://" + text
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise UrlPolicyError("The base URL must start with http:// or https://.")
    if not parsed.hostname or not parsed.netloc:
        raise UrlPolicyError("The base URL needs a host.")
    path = parsed.path or ""
    marker = path.find("/v1")
    if marker == -1:
        path = path.rstrip("/") + "/v1"
    else:
        path = path[: marker + 3]
    if path != "/v1" and not path.endswith("/v1"):
        path = path.rstrip("/") + "/v1"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def host_class(hostname: str) -> str:
    name = (hostname or "").strip().lower().rstrip(".")
    if name == "localhost":
        return "loopback"
    if _is_cloud(name):
        return "cloud"
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        address = None
    if address is not None:
        if address.is_loopback:
            return "loopback"
        if address.is_private or address.is_link_local:
            return "private"
        return "public"
    if any(name.endswith(suffix) for suffix in PRIVATE_DNS_SUFFIXES):
        return "private"
    if "." not in name:
        return "private"
    return "public"


def accept_base_url(raw: str, confirmed: bool = False) -> str:
    url = normalize_base_url(raw)
    kind = host_class(urlparse(url).hostname or "")
    if kind == "cloud":
        raise UrlPolicyError(
            "That host is a public cloud model service. Studio only saves a loopback or private-network server."
        )
    if kind == "public":
        raise UrlPolicyError(
            "That host is on the public internet. Studio only saves a loopback or confirmed private-network server."
        )
    if kind == "private" and not confirmed:
        raise UrlPolicyError(
            "This private-network address needs an explicit confirm before Studio will send prompts there."
        )
    return url


def _is_cloud(hostname: str) -> bool:
    return any(hostname == suffix or hostname.endswith("." + suffix) for suffix in CLOUD_SUFFIXES)
