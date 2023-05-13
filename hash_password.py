import bcrypt
import sys

def hash(password):
    original_password = password.encode('utf-8')  # Passwords should be bytes
    salt = bcrypt.gensalt()  # Generate a random salt
    hashed_password = bcrypt.hashpw(original_password, salt)  # Hash the password

    print(f"Password: {password}")
    print(f"HashedPW: {hashed_password}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hash_password.py <json_file_path>")
        sys.exit(1)

    password = sys.argv[1]
    hash(password)
