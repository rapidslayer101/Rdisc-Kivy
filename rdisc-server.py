import socket
import sqlite3
import enclib as enc
from time import sleep
from datetime import datetime
from rsa import PublicKey, encrypt
from zlib import error as zl_error
from os import listdir, remove, removedirs, rename
from threading import Thread
from random import choices, randint
from hashlib import sha512
from requests import get
from captcha.image import ImageCaptcha

# TODO MAJOR: REMOVE 1 THREAD PER USER


def version_info(hashed):
    version_data = None
    with open("sha.txt", encoding="utf-8") as f:
        for _hash_ in f.readlines():
            if hashed == _hash_.split("§")[0]:
                version_data = _hash_
    if not version_data:
        return f"UNKNOWN"
        print(f"UNKNOWN: {hashed}")
    version_, tme_, run_num = version_data.split("§")[1:]
    print(f"{version_}🱫{tme_}🱫{run_num}")
    return f"{version_}🱫{tme_}🱫{run_num}"


class Users:
    def __init__(self):
        self.db = sqlite3.connect('rdisc_server.db', check_same_thread=False)
        try:
            self.db.execute("SELECT user_id FROM users")
        except sqlite3.OperationalError:
            print("No such table: users")
            self.db.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY NOT NULL UNIQUE, "
                            "creation_time DATE NOT NULL, master_key TEXT NOT NULL, secret TEXT NOT NULL)")
        try:
            self.db.execute("SELECT user_id FROM ip_keys")
        except sqlite3.OperationalError:
            print("No such table: ip_keys")
            self.db.execute("CREATE TABLE ip_keys (user_id TEXT PRIMARY KEY NOT NULL UNIQUE, "
                            "ip TEXT NOT NULL, ip_key TEXT NOT NULL, expiry_time DATE NOT NULL)")

    def add_user(self, user_id, master_key, secret):
        self.db.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                        (user_id, str(datetime.now())[:-7], master_key, secret))
        self.db.commit()


users = Users()


#class Users:
#    def __init__(self):
#        self.logged_in_users = []
#        self.sockets = []
#
#    def ids_up(self, u_id):
#        self.ids.append(u_id)
#        self.ids.sort()
#
#    def ids_r(self, u_id):
#        self.ids.pop(self.ids.index(u_id))
#
#    def login(self, u_id, ip, cs):
#        self.logged_in_users.append(u_id)
#        self.logged_in_users.append(ip)
#        self.sockets.append(cs)
#
#    def logout(self, u_id, ip, cs):
#        try:
#            self.logged_in_users.pop(self.logged_in_users.index(u_id))
#            self.logged_in_users.pop(self.logged_in_users.index(ip))
#            self.sockets.pop(self.sockets.index(cs))
#        except ValueError:
#            pass


#users = Users()
client_sockets = set()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 30678))
s.listen()
print(f"[*] Listening as {str(s).split('laddr=')[1][:-1]}")


def client_connection(cs):
    try:
        ip, port = str(cs).split("raddr=")[1][2:-2].split("', ")
        print(f"NEW CLIENT-{ip}:{port}")
        uid = None
        try:
            pub_key_cli = PublicKey.load_pkcs1(cs.recv(256))
        except ValueError:
            raise AssertionError
        enc_seed, enc_salt = enc.rand_b96_str(48), enc.rand_b96_str(48)
        cs.send(encrypt(enc_seed.encode(), pub_key_cli))
        cs.send(encrypt(enc_salt.encode(), pub_key_cli))
        enc_key = enc.pass_to_key(enc_seed, enc_salt, 100000)

        def send_e(text):
            try:
                cs.send(enc.enc_from_key(text, enc_key))
            except zl_error:
                raise ConnectionResetError

        def recv_d(buf_lim):
            try:
                return enc.dec_from_key(cs.recv(buf_lim), enc_key)
            except zl_error:
                raise ConnectionResetError

        def check_logged_in(uid_):
            l_users = users.logged_in_users
            if uid_ in l_users:
                return True
            else:
                if ip in l_users:
                    return True
                else:
                    return False

        def fip(secret):
            while True:
                code_challenge = recv_d(2048)
                if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                       f"Pin={code_challenge}&SecretCode={secret}").content == b"True":
                    send_e("V")
                    break
                else:
                    send_e("N")

        while True:
            login_request = recv_d(1024)
            print(login_request)  # temp debug for dev
            if login_request.startswith("CAP"):
                img = ImageCaptcha(width=280, height=90)
                captcha_text = "".join(choices("123456789ABCDEFGHIJKLMNPQRSTUVWXYZ", k=int(10)))
                print(captcha_text)
                img.generate(captcha_text)  # todo remove the need for a file
                img.write(captcha_text, 'captcha.jpg')
                with open("captcha.jpg", "rb") as f:
                    send_e(f.read())

                counter = 0
                while True:
                    counter += 1
                    captcha_attempt = recv_d(2048)
                    if captcha_attempt != captcha_text:
                        send_e("N")
                        if counter == 3:
                            sleep(10)  # rate limit
                    else:
                        send_e("V")
                        break

                print("CAPTCHA OK")
                log_or_create = recv_d(2048)
                if log_or_create.startswith("NAC:"):  # new account
                    master_key, user_pass = log_or_create[4:].split("🱫")
                    # todo password checks here
                    user_secret = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXY"
                                                  "abcdefghijklmnopqrstuvwxyz", k=8))
                    while True:
                        uid = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=8))
                        try:
                            users.add_user(uid, enc.to_base(96, 16, sha512((master_key+uid).encode()).hexdigest()),
                                           user_secret)
                            break
                        except sqlite3.IntegrityError:
                            pass
                    send_e(f"{uid}🱫{user_secret}")
                    fip(user_secret)

            if login_request.startswith("FIP:"):  # first ip key
                uid, master_key_c = login_request[4:].split("🱫")
                try:
                    master_key, user_secret = users.db.execute("SELECT master_key, secret FROM "
                                                               "users WHERE user_id = ?", (uid,)).fetchone()
                    if master_key_c == master_key_c:
                        fip(user_secret)
                    else:
                        send_e("N")
                except sqlite3.OperationalError:
                    send_e("N")
                    pass
                input()
                user_secret = "x"
                fip(user_secret)

                input()
                u_pass = recv_d(2048)
                challenge_int = randint(1, 999999)
                challenge_hash = sha512(enc.pass_to_key(u_pass, u_salt, challenge_int).encode()).hexdigest()
                send_e(f"{challenge_int}")
                user_challenge = recv_d(2048)
                if user_challenge == challenge_hash:
                    users.ids_up(uid)
                    send_e(f"{uid}")
                    break
                else:
                    send_e("N")

            if login_request.startswith("LOG:"):
                uid = login_request[4:]
                if check_logged_in(uid):
                    send_e("SESH_T")
                    raise ConnectionRefusedError
                else:
                    try:
                        users.ids.index(uid)
                    except ValueError:
                        send_e("N")  # User ID not found
                    else:
                        try:
                            with open(f"Users/{uid}/{uid}-keys.txt", "r", encoding="utf-8") as f:
                                u_pass, u_salt = f.read().split("🱫")
                            while True:
                                challenge_int = randint(1, 999999)
                                challenge_hash = sha512(enc.pass_to_key(u_pass, u_salt, challenge_int).encode()).hexdigest()
                                send_e(f"{challenge_int}")
                                user_challenge = recv_d(2048)
                                if user_challenge != challenge_hash:
                                    send_e("N")
                                else:
                                    break
                            send_e("V")
                            break
                        except FileNotFoundError:
                            send_e("N")

        version_response = version_info(recv_d(512))
        send_e(version_response)
        users.login(uid, ip, cs)
        print(f"{uid} logged in with IP-{ip}:{port} and version-{version_response}")
        while True:  # main loop
            request = recv_d(1024)
            print(request)  # temp debug for dev

            # logout causing requests
            if request.startswith("LOG_A"):
                with open(f"Users/{u_dir}/{uid}-keys.txt", encoding="utf-8") as f:
                    log_a_write = f.readlines()[0]
                with open(f"Users/{u_dir}/{uid}-keys.txt", "w", encoding="utf-8") as f:
                    f.write(log_a_write)
                raise ConnectionResetError

            if request.startswith("DLAC:"):
                if u_pass == request[5:]:
                    send_e("V")
                    challenge_int = randint(1, 999999)
                    challenge_hash = sha512(enc.pass_to_key(u_pass, u_salt, challenge_int).encode()).hexdigest()
                    send_e(f"{challenge_int}")
                    user_challenge = recv_d(2048)
                    if user_challenge == challenge_hash:
                        send_e("V")
                        if recv_d(1024) == "Y":
                            for file in listdir(f"Users/{uid}"):
                                remove(f"Users/{uid}/{file}")
                            removedirs(f"Users/{uid}")
                            users.ids_r(uid)
                            send_e(f"V")
                            raise ConnectionResetError
                else:
                    send_e("N")

            if request.startswith("CPASS:"):
                try:
                    old_pass, new_pass = request[6:].split("🱫")
                except ValueError:
                    raise AssertionError
                if old_pass == new_pass:
                    send_e("SP")  # old pass and new pass the same
                else:
                    print(old_pass, new_pass)
                    # fetch old pass
                    with open(f"Users/{uid}/{uid}-keys.txt", encoding="utf-8") as f:
                        u_old_pass, _h_ = f.read().split("🱫")
                    if old_pass == u_old_pass:
                        print("success")
                        with open(f"Users/{uid}/{uid}-keys.txt", "w", encoding="utf-8") as f:
                            f.write(f"{new_pass}🱫{_h_}")
                        send_e("V")
                    else:
                        send_e("N")  # password wrong

            if request.startswith("CUSRN:"):
                u_name = request[6:]
                u_dir = users.dirs(0)[uid]
                u_dir = f"{uid} {u_dir[0]} {u_dir[1]}"
                if not 4 < len(u_name) < 33:
                    raise AssertionError
                if "#" in u_name or " " in u_name:
                    raise AssertionError
                if u_name == u_dir.split(" ")[2][:-5]:
                    raise AssertionError

                # todo check amount of username changes here

                u_name = f"{u_name}#{randint(1111, 9999)}"
                if u_name not in users.names(0):
                    user_dir_new = f"{uid} {u_dir.split(' ')[1]} {u_name}"
                    rename(f"Users/{u_dir}", f"Users/{user_dir_new}")
                    users.dirs_update(uid, u_dir.split(' ')[1], u_name)
                    users.names_remove(users.names(0).index(u_dir.split(" ")[2]))
                    users.names_update(u_name)
                    # todo update amount of username changes here
                    send_e(f"V{u_name}")
                else:
                    send_e("N_NAME")

            if request.startswith("ADDFR:"):
                add_friend_n = request[6:]
                if 9 < len(add_friend_n) < 38:
                    try:
                        int(add_friend_n[-4:])
                        if add_friend_n[-5] != "#":
                            raise AssertionError
                        else:
                            print("process new friend")
                            print(add_friend_n)
                    except ValueError:
                        raise AssertionError
                else:
                    raise AssertionError

    except ConnectionResetError:
        print(f"{uid}-{ip}:{port} DC")
        users.logout(uid, ip, cs)
    except ConnectionRefusedError:
        print(f"{uid}-{ip}:{port} DC - 1 session limit")
    except AssertionError:
        print(f"{uid}-{ip}:{port} DC - modified/invalid client request")
        users.logout(uid, ip, cs)


while True:
    client_socket, client_address = s.accept()
    t = Thread(target=client_connection, args=(client_socket,))
    t.daemon = True
    t.start()
