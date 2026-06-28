"""
سكريبت توليد password hash عشان تضيفه في secrets.toml
يُشغّل من الترمينال: python generate_password_hash.py
"""

import hashlib
import secrets
import getpass

print("=" * 60)
print("🔐 Kayfa Dashboard - Password Hash Generator")
print("=" * 60)

# لو أول مرة، اعمل salt واحد ثابت يُستخدم لكل المستخدمين
existing_salt = input("\nFixed salt already in secrets.toml? (leave empty to generate new): ").strip()
salt = existing_salt or secrets.token_hex(16)

if not existing_salt:
    print(f"\n✅ Generated NEW salt — copy this once into secrets.toml under [auth]:")
    print(f'   salt = "{salt}"')

username = input("\nUsername: ").strip()
password = getpass.getpass("Password (hidden): ").strip()

password_hash = hashlib.sha256((salt + password).encode()).hexdigest()

print("\n" + "=" * 60)
print(f"Add this block to secrets.toml:\n")
print(f"[auth.users.{username}]")
print(f'password_hash = "{password_hash}"')
print(f'display_name = "{username.capitalize()}"')
print("=" * 60)