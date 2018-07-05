import hashlib, random, string, pickle

with open('email_whitelist.txt', 'r') as email_whitelist:
    email_list = [line for line in email_whitelist.read().split("\n") if line != ""]

 
def hash_email(email, salt, iterations=1000):        
    """ Iterativley hash emails
    """
    encoded_email = bytes(email, encoding='utf-8')
    encoded_salt = bytes(salt, encoding='utf-8')
    
    email_hash = hashlib.sha3_512(encoded_email+encoded_salt).hexdigest()
    
    for _ in range(iterations):
        email_hash = hashlib.sha3_512(
            bytes(email_hash, encoding="utf-8")+encoded_email
        ).hexdigest()
    
    return email_hash

global_salt = "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16) )

if __name__=='__main__': 

    hashed_email_list = [ hash_email(email, global_salt) for email in email_list]

    pickle_obj = (global_salt, hashed_email_list)

    # pickle the hashed_email_list and the salt 
    with open('server/src/email_hashed.p', 'wb') as pickle_file:
        pickle.dump(pickle_obj, pickle_file)
