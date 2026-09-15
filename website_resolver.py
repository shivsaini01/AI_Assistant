import re
import socket
from urllib.parse import urlparse


# ==================================================
# VALIDATE URL
# ==================================================

def is_valid_web_url(url):

    if not isinstance(
        url,
        str
    ):

        return False

    url = url.strip()

    if not url:

        return False

    try:

        parsed = urlparse(
            url
        )

        if parsed.scheme not in {
            "http",
            "https"
        }:

            return False

        if not parsed.netloc:

            return False

        hostname = parsed.hostname

        if not hostname:

            return False

        hostname = hostname.lower()

        blocked_hosts = {
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
        }

        if hostname in blocked_hosts:

            return False

        return True

    except Exception:

        return False


# ==================================================
# CLEAN WEBSITE NAME
# ==================================================

def clean_website_name(
    target
):

    if not isinstance(
        target,
        str
    ):

        return None

    target = target.strip().lower()

    target = re.sub(
        r"^https?://",
        "",
        target
    )

    target = re.sub(
        r"^www\.",
        "",
        target
    )

    target = target.split(
        "/"
    )[0]

    target = target.rstrip(
        ".,!?;:"
    )

    if not target:

        return None

    if not re.match(
        r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$",
        target
    ):

        return None

    return target


# ==================================================
# DOMAIN EXISTS
# ==================================================

def domain_exists(
    domain
):

    try:

        socket.gethostbyname(
            domain
        )

        return True

    except (
        socket.gaierror,
        OSError
    ):

        return False


# ==================================================
# RESOLVE WEBSITE
# ==================================================

def resolve_website(
    target
):

    if not target:

        return None

    target = str(
        target
    ).strip()

    # ----------------------------------------------
    # Full URL
    # ----------------------------------------------

    if re.match(
        r"^https?://",
        target,
        re.IGNORECASE
    ):

        if is_valid_web_url(
            target
        ):

            return target.rstrip(
                "/"
            )

        return None

    # ----------------------------------------------
    # Clean domain
    # ----------------------------------------------

    domain = clean_website_name(
        target
    )

    if not domain:

        return None

    # ----------------------------------------------
    # User provided TLD
    # ----------------------------------------------

    if "." in domain:

        candidate = (
            "https://"
            + domain
        )

        if (
            is_valid_web_url(
                candidate
            )
            and
            domain_exists(
                domain
            )
        ):

            return candidate

        return None

    # ----------------------------------------------
    # Try normal TLDs
    # ----------------------------------------------

    tlds = [
        ".com",
        ".org",
        ".net",
        ".io",
        ".dev",
        ".ai",
        ".app",
        ".co",
    ]

    for tld in tlds:

        candidate_domain = (
            domain
            + tld
        )

        if not domain_exists(
            candidate_domain
        ):

            continue

        candidate_url = (
            "https://"
            + candidate_domain
        )

        if is_valid_web_url(
            candidate_url
        ):

            return candidate_url

    return None


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    print("=" * 60)
    print("JARVIS WEBSITE RESOLVER TEST")
    print("=" * 60)
    print()

    tests = [
        "github",
        "reddit",
        "youtube",
        "python.org",
        "https://stackoverflow.com",
    ]

    for test in tests:

        print(
            f"Resolving: {test}"
        )

        result = resolve_website(
            test
        )

        if result:

            print(
                f"[FOUND] {result}"
            )

        else:

            print(
                "[NOT FOUND]"
            )

        print()

    print("=" * 60)