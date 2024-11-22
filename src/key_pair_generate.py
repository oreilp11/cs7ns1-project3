# Written by Paul O'Reilly, Arnav Tripathy & Daya Lokesh Duddupudi
import rsa
import os

if __name__ == "__main__":
    public_key, private_key = rsa.newkeys(2048)


    keypath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys")

    with open(os.path.join(keypath,'public.pem'), 'wb') as keyfile:
        keyfile.write(public_key.save_pkcs1())

    with open(os.path.join(keypath,'private.pem'), 'wb') as keyfile:
        keyfile.write(private_key.save_pkcs1())