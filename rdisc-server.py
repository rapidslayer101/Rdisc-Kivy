import os
import socket
import sqlite3
import enclib as enc
from time import sleep
from datetime import datetime, timedelta
from rsa import PublicKey, encrypt
from zlib import error as zl_error
from os import listdir, remove, removedirs, path
from threading import Thread
from random import choices, randint
from hashlib import sha512
from requests import get
from captcha.image import ImageCaptcha

# TODO MAJOR: REMOVE 1 THREAD PER USER, Disconnect inactive not logged in users?
#  async, sesh_key front of enc to identify user


class Users:
    def __init__(self):
        self.logged_in_users = []
        self.sockets = []
        self.db = sqlite3.connect('rdisc_server.db', check_same_thread=False)
        try:
            self.db.execute("SELECT user_id FROM users")
        except sqlite3.OperationalError:
            print("No such table: users")
            self.db.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY NOT NULL UNIQUE,"
                            "creation_time DATE NOT NULL, master_key TEXT NOT NULL, secret TEXT NOT NULL,"
                            "user_pass TEXT NOT NULL, username TEXT NOT NULL,"
                            "last_online DATE NOT NULL, xp FLOAT NOT NULL,"
                            "r_coin FLOAT NOT NULL, d_coin FLOAT NOT NULL)")
        try:
            self.db.execute("SELECT user_id FROM ip_keys")
        except sqlite3.OperationalError:
            print("No such table: ip_keys")
            self.db.execute("CREATE TABLE ip_keys (user_id TEXT NOT NULL,"
                            "ip TEXT NOT NULL, ip_key TEXT NOT NULL, expiry_time DATE NOT NULL)")

    def login(self, u_id, ip, cs):
        self.logged_in_users.append(u_id)
        self.logged_in_users.append(ip)
        self.sockets.append(cs)

    def logout(self, u_id, ip, cs):
        try:
            self.logged_in_users.pop(self.logged_in_users.index(u_id))
            self.logged_in_users.pop(self.logged_in_users.index(ip))
            self.sockets.pop(self.sockets.index(cs))
            self.db.execute("UPDATE users SET last_online = ? WHERE user_id = ?", (str(datetime.now())[:-7], u_id))
            self.db.commit()
        except ValueError:
            pass

    def add_user(self, user_id, master_key, secret, user_pass, username):
        now = str(datetime.now())[:-7]
        self.db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user_id, now,
                        enc.to_base(96, 16, sha512((master_key+user_id).encode()).hexdigest()), secret,
                        user_pass, username, now, 0, 0, 1000))
        self.db.commit()

    def add_user_key(self, user_id, ip, ip_key, expiry_time=14):
        expiry_time = str(datetime.now()+timedelta(days=expiry_time))[:-7]
        self.db.execute("INSERT INTO ip_keys VALUES (?, ?, ?, ?)",
                        (user_id, ip, enc.to_base(96, 16, sha512((ip_key+user_id).encode()).hexdigest()), expiry_time))
        self.db.commit()

    def check_logged_in(self, uid, ip):
        if uid in self.logged_in_users:
            return True
        else:
            if ip in self.logged_in_users:
                return True
            else:
                return False


users = Users()
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

        def new_ip(uid, secret, user_pass, u_name, xp, r_coin, d_coin):
            while True:
                code_challenge = recv_d(1024)
                if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                       f"Pin={code_challenge}&SecretCode={secret}").content == b"True":
                    ip_key = enc.rand_b96_str(24)
                    users.add_user_key(uid, ip, ip_key)
                    send_e(enc.enc_from_pass(ip_key, user_pass[:40], user_pass[40:]))
                    send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                    break
                else:
                    send_e("N")

        while True:
            login_request = recv_d(1024)
            print(login_request)  # temp debug for dev

            if login_request.startswith("UPD:"):
                current_hash = login_request[4:]
                file = [file for file in listdir("dist") if file.endswith(".zip")][-1]
                if current_hash == "N":
                    send_e(f"{file}🱫{(path.getsize(f'dist/{file}'))}")
                    with open(f"dist/{file}", "rb") as f:
                        while True:
                            bytes_read = f.read(4096)
                            if not bytes_read:
                                cs.sendall(b"_BREAK_")
                                break
                            cs.sendall(bytes_read)
                    raise ConnectionResetError
                else:
                    with open("dist/latest_hash.txt", "r", encoding="utf-8") as f:
                        latest_hash = f.read()
                    if login_request[4:] != latest_hash:
                        send_e(f"{file}🱫{(path.getsize(f'dist/{file}'))}")
                        with open(f"dist/{file}", "rb") as f:
                            while True:
                                bytes_read = f.read(4096)
                                if not bytes_read:
                                    break
                                cs.sendall(bytes_read)
                        raise ConnectionResetError
                    else:
                        send_e("V")
                        raise ConnectionResetError

            if login_request.startswith("CAP"):
                img = ImageCaptcha(width=280, height=90)
                captcha_text = "".join(choices("23456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=int(10)))
                print(captcha_text)
                img.generate(captcha_text)  # todo remove the need for a file
                img.write(captcha_text, 'captcha.jpg')
                with open("captcha.jpg", "rb") as f:
                    send_e(f.read())
                counter = 0
                while True:
                    counter += 1
                    captcha_attempt = recv_d(1024)
                    if captcha_attempt != captcha_text:
                        send_e("N")
                        if counter > 3:
                            sleep(10)  # rate limit
                    else:
                        send_e("V")
                        break
                print("CAPTCHA OK")
                log_or_create = recv_d(1024)
                if log_or_create.startswith("NAC:"):  # new account
                    master_key, user_pass = log_or_create[4:].split("🱫")
                    # todo password checks here
                    user_secret = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXY"
                                                  "abcdefghijklmnopqrstuvwxyz", k=8))
                    while True:
                        uid = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=8))
                        u_name = uid+"#"+str(randint(111, 999))
                        try:
                            user_pass = enc.to_base(96, 16, sha512((user_pass+uid).encode()).hexdigest())
                            users.add_user(uid, master_key, user_secret, user_pass, u_name)
                            break
                        except sqlite3.IntegrityError:
                            pass
                    send_e(f"{uid}🱫{user_secret}")
                    d_coin = 1000
                    new_ip(uid, user_secret, user_pass, u_name, 0, 0, d_coin)
                    break

                if login_request.startswith("FIP:"):  # first ip key
                    uid, master_key_c, = login_request[4:].split("🱫")
                    try:
                        master_key, user_secret, user_pass, u_name, xp, r_coin, d_coin = users.db.execute(
                            "SELECT master_key, secret, user_pass, username, xp, r_coin, d_coin FROM "
                            "users WHERE user_id = ?", (uid,)).fetchone()
                        if enc.to_base(96, 16, sha512((master_key_c+uid).encode()).hexdigest()) == master_key:
                            if users.db.execute("SELECT * FROM ip_keys WHERE user_id = ?", (uid,)).fetchone() is None:
                                new_ip(uid, user_secret, user_pass, u_name, xp, r_coin, d_coin)
                            else:
                                raise AssertionError
                        else:
                            send_e("IMK")  # master key wrong
                    except sqlite3.OperationalError:
                        send_e("NU")  # user does not exist
                    u_pass = recv_d(1024)
                    challenge_int = randint(99999, 499999)
                    challenge_hash = sha512(enc.pass_to_key(u_pass, uid, challenge_int).encode()).hexdigest()
                    send_e(f"{challenge_int}")
                    user_challenge = recv_d(1024)
                    if user_challenge == challenge_hash:
                        users.ids_up(uid)  # todo check
                        send_e(f"{uid}")
                        break
                    else:
                        send_e("N")

                if log_or_create.startswith("LOG:"):
                    master_key_c, uid = log_or_create[4:].split("🱫")
                    try:
                        master_key, user_secret, user_pass, u_name, xp, r_coin, d_coin = users.db.execute(
                            "SELECT master_key, secret, user_pass, username,  xp, r_coin, d_coin "
                            "FROM users WHERE user_id = ?", (uid,)).fetchone()
                        if enc.to_base(96, 16, sha512((master_key_c+uid).encode()).hexdigest()) == master_key:
                            ip_key = enc.rand_b96_str(24)
                            send_e(enc.enc_from_pass(ip_key, user_pass[:40], user_pass[40:]))
                            while True:
                                ip_key_c = recv_d(1024)
                                if ip_key_c == ip_key:
                                    send_e("V")
                                    break
                                else:
                                    send_e("N")
                            while True:
                                code_challenge = recv_d(1024)
                                if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                                       f"Pin={code_challenge}&SecretCode={user_secret}").content == b"True":
                                    send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                                    if users.db.execute("SELECT * FROM ip_keys WHERE ip = ?",
                                                        (ip,)).fetchone() is not None:
                                        users.db.execute("DELETE FROM ip_keys WHERE ip = ?", (ip,))
                                    if len(users.db.execute("SELECT * FROM ip_keys WHERE user_id = ?",
                                                            (uid,)).fetchall()) == 5:
                                        print("deleted 5th key")  # todo test 5 keys
                                        users.db.execute("DELETE FROM ip_keys WHERE user_id = ? AND expiry_time = "
                                                         "(SELECT MIN(expiry_time) FROM ip_keys WHERE user_id = ?)",
                                                         (uid, uid))
                                    users.add_user_key(uid, ip, ip_key)
                                    break
                                else:
                                    send_e("N")
                            break
                        else:
                            send_e("IMK")  # master key wrong
                    except sqlite3.OperationalError:
                        send_e("NU")  # user does not exist

            if login_request.startswith("ULK:"):
                uid = login_request[4:]
                if users.check_logged_in(uid, ip):
                    send_e("SESH_T")
                    raise ConnectionRefusedError
                else:
                    try:
                        u_name, xp, r_coin, d_coin = users.db.execute("SELECT username, xp, r_coin, d_coin FROM users "
                                                                      "WHERE user_id = ?", (uid,)).fetchone()
                    except ValueError:
                        send_e("N")  # User ID not found
                    else:
                        try:
                            ip_keys = users.db.execute("SELECT ip, ip_key FROM ip_keys WHERE user_id = ?", (uid,)).fetchall()
                        except ValueError:
                            send_e("N")  # No IP keys found
                        else:
                            ip_key = None
                            for ip_key in ip_keys:
                                if ip_key[0] == ip:
                                    ip_key = ip_key[1]
                                    break
                            if ip_key:
                                while True:
                                    challenge_int = randint(99999, 499999)
                                    print(ip_key)
                                    challenge_hash = sha512(
                                        enc.pass_to_key(ip_key, uid, challenge_int).encode()).hexdigest()
                                    send_e(f"{challenge_int}")
                                    user_challenge = recv_d(2048)
                                    if user_challenge == challenge_hash:
                                        send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                                        break
                                    else:
                                        send_e("N")
                                break

        print(f"{uid} reached version checking")  # debug, remove later
        #version_response = version_info(recv_d(1024))  # todo trigger from client if on exe
        #send_e(version_response)
        users.login(uid, ip, cs)
        print(f"{uid} logged in with IP-{ip}:{port} and version-")#{version_response}")
        while True:  # main loop
            request = recv_d(1024)
            print(request)  # temp debug for dev

            # logout causing requests
            if request.startswith("LOG_A"):  # deletes all IP keys
                raise ConnectionResetError

            if request.startswith("DLAC:"):
                if u_pass == request[5:]:
                    send_e("V")
                    challenge_int = randint(99999, 499999)
                    challenge_hash = sha512(enc.pass_to_key(u_pass, uid, challenge_int).encode()).hexdigest()
                    send_e(f"{challenge_int}")
                    if recv_d(1024) == challenge_hash:
                        send_e("V")
                        if recv_d(1024) == "Y":
                            for file in listdir(f"Users/{uid}"):
                                remove(f"Users/{uid}/{file}")
                            removedirs(f"Users/{uid}")
                            #users.ids_r(uid)
                            send_e(f"V")
                            raise ConnectionResetError
                else:
                    send_e("N")

            if request.startswith("CUP:"):
                print("Triggered CUP an not built feature")

            if request.startswith("CUN:"):  # change username
                if d_coin > 4:
                    n_u_name = request[4:]
                    if not 4 < len(n_u_name) < 25:
                        raise AssertionError
                    if "#" in n_u_name or "  " in n_u_name:
                        raise AssertionError
                    while True:  # todo possible infinite loop needing fix
                        n_u_name_i = n_u_name+"#"+str(randint(111, 999))
                        try:
                            if users.db.execute("SELECT * FROM users WHERE username = ?",
                                                (n_u_name_i,)).fetchone() is None:
                                d_coin -= 5
                                users.db.execute("UPDATE users SET username = ?, d_coin = ? WHERE user_id = ?",
                                                 (n_u_name_i, d_coin, uid))
                                users.db.commit()
                                send_e(n_u_name_i)
                                break
                        except sqlite3.OperationalError:
                            send_e("N")

                else:
                    raise AssertionError

            if request.startswith("TRF:"):  # transfer R coins
                transfer_to, transfer_amount = request[4:].split("🱫")
                if round(float(transfer_amount)/0.995, 2) > r_coin:
                    raise AssertionError
                if transfer_to == uid:
                    raise AssertionError
                try:  # todo what if the user is already logged in, resolve username to UID
                    transfer_to_r_coin = users.db.execute("SELECT r_coin FROM users WHERE user_id = ?",
                                                          (transfer_to,)).fetchone()[0]
                    r_coin = round(float(r_coin)-float(transfer_amount)/0.995, 2)
                    users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?",
                                     (r_coin, uid))
                    users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?",
                                     (float(transfer_to_r_coin)+float(transfer_amount), transfer_to))
                    users.db.commit()
                    send_e("V")
                except TypeError:
                    send_e("N")  # user not exist

            if request.startswith("CLM:"):  # claim code
                #code = request[4:]
                send_e("N")

            if request.startswith("AFR:"):
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

            if request.startswith("COF:"):  # coinflip game
                print("Coinflip game triggered")
                # make game expire after x time

    except ConnectionResetError:
        print(f"{uid}-{ip}:{port} DC")
        if ip in users.logged_in_users:
            users.logout(uid, ip, cs)
    except ConnectionRefusedError:
        print(f"{uid}-{ip}:{port} DC - 1 session limit")
    except AssertionError:
        print(f"{uid}-{ip}:{port} DC - modified/invalid client request")
        if ip in users.logged_in_users:
            users.logout(uid, ip, cs)


while True:
    client_socket, client_address = s.accept()
    t = Thread(target=client_connection, args=(client_socket,))
    t.daemon = True
    t.start()
