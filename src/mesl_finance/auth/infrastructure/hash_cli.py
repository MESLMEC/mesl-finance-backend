"""Make the value for MESL_AUTH_PASSWORD_HASH.

Run:  python -m mesl_finance.auth.infrastructure.hash_cli
"""

from getpass import getpass

from argon2 import PasswordHasher


def main() -> None:
    password = getpass("Password: ")
    if password != getpass("Again: "):
        raise SystemExit("Passwords differ.")
    print(PasswordHasher().hash(password))


if __name__ == "__main__":
    main()
