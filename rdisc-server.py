import sqlite3
import enclib as enc
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from time import sleep
from datetime import datetime, timedelta
from rsa import PublicKey, encrypt
from zlib import error as zl_error
from os import listdir, path
from threading import Thread
from random import choices, randint
from requests import get
from captcha.image import ImageCaptcha

# TODO MAJOR: REMOVE 1 THREAD PER USER, Disconnect inactive not logged in users?
#  async, sesh_key front of enc to identify user


class InvalidClientData(Exception):
    pass


class Users:
    def __init__(self):
        self.logged_in_users = []
        self.sockets = []
        self.db = sqlite3.connect('rdisc_server.db', check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY NOT NULL UNIQUE,"
                        "creation_time DATE NOT NULL, master_key TEXT NOT NULL, secret TEXT NOT NULL,"
                        "user_pass TEXT NOT NULL, ip_key1 TEXT, ip_key2 TEXT, ip_key3 TEXT, ip_key4 TEXT, "
                        "username TEXT NOT NULL, last_online DATE NOT NULL, xp FLOAT NOT NULL,"
                        "r_coin FLOAT NOT NULL, d_coin FLOAT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY NOT NULL UNIQUE,"
                        "expiry_date DATE NOT NULL, claimed TEXT NOT NULL,"
                        "reward_type TEXT NOT NULL, amount FLOAT NOT NULL)")

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

    def add_user(self, user_id, master_key, secret, user_pass, ip_key, username):
        now = str(datetime.now())[:-7]
        expiry_time = str(datetime.now()+timedelta(days=14))[:-7]
        self.db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (user_id, now,
                        enc.pass_to_key(master_key, user_id), secret, user_pass, ip_key+"🱫"+expiry_time, None,
                        None, None, username, now, 0, 0, 1000))
        self.db.commit()

    def check_logged_in(self, uid, ip):
        if uid in self.logged_in_users:
            return True
        elif ip in self.logged_in_users:
            return True
        else:
            return False


users = Users()
client_sockets = set()
s = socket(AF_INET, SOCK_STREAM)
s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
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
            raise InvalidClientData
        enc_seed = enc.rand_b96_str(36)
        cs.send(encrypt(enc_seed.encode(), pub_key_cli))
        enc_key = enc.pass_to_key(enc_seed[:18], enc_seed[18:], 100000)

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

        def send_update(update_file):
            send_e(f"{update_file}🱫{(path.getsize(f'dist/{update_file}'))}")
            with open(f"dist/{update_file}", "rb") as f:
                while True:
                    bytes_read = f.read(32768)
                    if not bytes_read:
                        cs.sendall(b"_BREAK_")
                        break
                    cs.sendall(bytes_read)

        while True:
            login_request = recv_d(1024)
            print(login_request)  # temp debug for dev

            if login_request.startswith("UPD:"):  # update request
                current_hash = login_request[4:]
                file = [file for file in listdir("dist") if file.endswith(".zip")][-1]
                if current_hash == "N":
                    send_update(file)
                else:
                    with open("dist/latest_hash.txt", "r", encoding="utf-8") as f:
                        latest_hash = f.read()
                    if login_request[4:] != latest_hash:
                        send_update(file)
                    else:
                        send_e("V")
                raise ConnectionResetError

            elif login_request == "CAP":  # captcha request
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
                    while True:
                        uid = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=8))
                        u_name = uid+"#"+str(randint(111, 999))
                        if users.db.execute("SELECT user_id FROM users WHERE user_id = ?",
                                            (uid,)).fetchone() is None:
                            break
                    user_secret = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXY"
                                                  "abcdefghijklmnopqrstuvwxyz", k=8))
                    send_e(f"{uid}🱫{user_secret}")
                    while True:
                        code_challenge = recv_d(1024)
                        if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                               f"Pin={code_challenge}&SecretCode={user_secret}").content == b"True":
                            ip_key = enc.rand_b96_str(24)
                            user_pass = enc.pass_to_key(user_pass, uid)
                            send_e(enc.enc_from_pass(ip_key, user_pass[:40], user_pass[40:]))
                            send_e(f"{u_name}🱫0🱫0🱫1000")
                            users.add_user(uid, master_key, user_secret, user_pass,
                                           enc.pass_to_key(ip+ip_key, uid), u_name)
                            break
                        else:
                            send_e("N")

                if log_or_create.startswith("LOG:"):
                    master_key_c, search_for, uname_or_uid = log_or_create[4:].split("🱫")
                    if search_for == "u":
                        try:
                            uid, master_key, user_secret, user_pass, u_name, xp, r_coin, d_coin = users.db.execute(
                                "SELECT user_id, master_key, secret, user_pass, username, xp, r_coin, d_coin "
                                "FROM users WHERE username = ?", (uname_or_uid,)).fetchone()
                        except TypeError:
                            uid = None
                            send_e("NU")  # user does not exist
                    else:
                        try:
                            uid = uname_or_uid
                            master_key, user_secret, user_pass, u_name, xp, r_coin, d_coin = users.db.execute(
                                "SELECT master_key, secret, user_pass, username, xp, r_coin, d_coin "
                                "FROM users WHERE user_id = ?", (uname_or_uid,)).fetchone()
                        except TypeError:
                            uid = None
                            send_e("NU")  # user does not exist
                    if uid:
                        if enc.pass_to_key(master_key_c, uid) == master_key:
                            ip_key = enc.rand_b96_str(24)
                            print("IP KEY:", ip_key)
                            send_e(enc.enc_from_pass(ip_key, user_pass[:40], user_pass[40:]))
                            if search_for == "u":
                                send_e(uid)
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
                                    # get ip keys from db
                                    ipk1, ipk2, ipk3, ipk4 = users.db.execute(
                                        "SELECT ip_key1, ip_key2, ip_key3, ip_key4 FROM users WHERE user_id = ?",
                                        (uid,)).fetchone()

                                    expiry_time = str(datetime.now()+timedelta(days=14))[:-7]
                                    if ipk1 and ipk2 and ipk3 and ipk4:  # if 4 ip keys, replace the oldest one
                                        oldest_ipk = "1"
                                        oldest_ipk_d = datetime.strptime(ipk1.split("🱫")[1], "%Y-%m-%d %H:%M:%S")
                                        if oldest_ipk_d > datetime.strptime(ipk2.split("🱫")[1], "%Y-%m-%d %H:%M:%S"):
                                            oldest_ipk_d = datetime.strptime(ipk2.split("🱫")[1], "%Y-%m-%d %H:%M:%S")
                                            oldest_ipk = "2"
                                        if oldest_ipk_d > datetime.strptime(ipk3.split("🱫")[1], "%Y-%m-%d %H:%M:%S"):
                                            oldest_ipk_d = datetime.strptime(ipk3.split("🱫")[1], "%Y-%m-%d %H:%M:%S")
                                            oldest_ipk = "3"
                                        if oldest_ipk_d > datetime.strptime(ipk4.split("🱫")[1], "%Y-%m-%d %H:%M:%S"):
                                            oldest_ipk = "4"
                                        users.db.execute("UPDATE users SET ip_key"+oldest_ipk+" = ? WHERE user_id = ?",
                                                         (enc.pass_to_key(ip+ip_key, uid)+"🱫"+expiry_time, uid))
                                    else:  # save to empty ip key
                                        if not ipk1:
                                            users.db.execute("UPDATE users SET ip_key1 = ? WHERE user_id = ?",
                                                             (enc.pass_to_key(ip+ip_key, uid)+"🱫"+expiry_time, uid))
                                        elif not ipk2:
                                            users.db.execute("UPDATE users SET ip_key2 = ? WHERE user_id = ?",
                                                             (enc.pass_to_key(ip+ip_key, uid)+"🱫"+expiry_time, uid))
                                        elif not ipk3:
                                            users.db.execute("UPDATE users SET ip_key3 = ? WHERE user_id = ?",
                                                             (enc.pass_to_key(ip+ip_key, uid)+"🱫"+expiry_time, uid))
                                        elif not ipk4:
                                            users.db.execute("UPDATE users SET ip_key4 = ? WHERE user_id = ?",
                                                             (enc.pass_to_key(ip+ip_key, uid)+"🱫"+expiry_time, uid))
                                    users.db.commit()
                                    break
                                else:
                                    send_e("N")
                            break
                        else:
                            send_e("IMK")  # master key wrong

            elif login_request.startswith("ULK:"):
                uid, u_ipk = login_request[4:].split("🱫")
                if users.check_logged_in(uid, ip):
                    send_e("SESH_T")
                else:
                    try:
                        ipk1, ipk2, ipk3, ipk4, u_name, xp, r_coin, d_coin = \
                            users.db.execute("SELECT ip_key1, ip_key2, ip_key3, ip_key4, username, xp, r_coin,"
                                             " d_coin FROM users WHERE user_id = ?", (uid,)).fetchone()
                    except ValueError:
                        send_e("N")  # User ID not found
                    else:
                        u_ipk = enc.pass_to_key(ip+u_ipk, uid)

                        def check_ipk(ipk):
                            ipk, ipk_e = ipk.split("🱫")
                            if u_ipk == ipk:
                                if datetime.now() < datetime.strptime(ipk_e, "%Y-%m-%d %H:%M:%S"):
                                    return True
                                else:
                                    return False
                            else:
                                return False

                        if ipk1:
                            if check_ipk(ipk1):
                                send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                                break
                        if ipk2:
                            if check_ipk(ipk2):
                                send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                                break
                        if ipk3:
                            if check_ipk(ipk3):
                                send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                                break
                        if ipk4:
                            if check_ipk(ipk4):
                                send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                                break
                        send_e("N")

            else:
                raise InvalidClientData

        users.login(uid, ip, cs)
        print(f"{uid} logged in with IP-{ip}:{port}")
        while True:  # main loop
            request = recv_d(1024)
            print(request)  # temp debug for dev

            # logout causing requests
            if request.startswith("LOG_A"):  # deletes all IP keys
                raise ConnectionResetError

            if request.startswith("DLAC:"):  # todo delete account
                pass

            if request.startswith("BGC:"):  # buy gift card
                try:
                    amount = int(request[4:])
                except ValueError:
                    raise InvalidClientData
                if amount in [25, 40, 100, 250, 600]:
                    if r_coin >= amount:
                        r_coin = round(r_coin - amount, 2)
                        users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?", (r_coin, uid))
                        while True:
                            code = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXY", k=16))
                            try:
                                users.db.execute("INSERT INTO codes VALUES (?, ?, ?, ?, ?)", (code,
                                                 str(datetime.now()+timedelta(days=14))[:-7], False, "R", amount))
                                break
                            except sqlite3.IntegrityError:
                                pass
                        users.db.commit()
                        send_e(f"{code[:4]}-{code[4:8]}-{code[8:12]}-{code[12:]}")
                    else:
                        raise InvalidClientData
                else:
                    raise InvalidClientData

            if request.startswith("BYD:"):  # buy d_coin
                try:
                    amount = int(request[4:])
                except ValueError:
                    raise InvalidClientData
                if amount in [15, 35, 50, 100, 210]:
                    if r_coin >= amount:
                        r_coin = round(r_coin-amount, 2)
                        users.db.execute("UPDATE users SET r_coin = ?, d_coin = ? WHERE user_id = ?",
                                         (r_coin, d_coin+{15: 150, 35: 375, 50: 550, 100: 1150, 210: 2500}.get(amount),
                                          uid))
                        users.db.commit()
                        send_e("V")
                    else:
                        raise InvalidClientData
                else:
                    raise InvalidClientData

            if request.startswith("CUP:"):
                print("Triggered CUP, not yet built feature")

            if request.startswith("CUN:"):  # change username
                if d_coin >= 5:
                    n_u_name = request[4:]
                    if not 4 < len(n_u_name) < 25:
                        raise InvalidClientData
                    if "#" in n_u_name or "  " in n_u_name:
                        raise InvalidClientData
                    counter = 0
                    while True:
                        counter += 1
                        n_u_name_i = n_u_name+"#"+str(randint(111, 999))
                        try:
                            if users.db.execute("SELECT * FROM users WHERE username = ?",
                                                (n_u_name_i,)).fetchone() is None:
                                d_coin = round(d_coin-5, 2)
                                users.db.execute("UPDATE users SET username = ?, d_coin = ? WHERE user_id = ?",
                                                 (n_u_name_i, d_coin, uid))
                                users.db.commit()
                                send_e(n_u_name_i)
                                break
                        except sqlite3.OperationalError:
                            if counter == 10:
                                send_e("N")
                                break

                else:
                    raise InvalidClientData

            if request.startswith("TRF:"):  # transfer R coins
                transfer_to, transfer_amount = request[4:].split("🱫")
                if round(float(transfer_amount)/0.995, 2) > r_coin:
                    raise InvalidClientData
                if transfer_to == uid:
                    raise InvalidClientData
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
                            raise InvalidClientData
                        else:
                            print("process new friend")
                            print(add_friend_n)
                    except ValueError:
                        raise InvalidClientData
                else:
                    raise InvalidClientData

            if request.startswith("COF:"):  # coinflip game
                print("Coinflip game triggered")
                # make game expire after x time

    except ConnectionResetError:
        print(f"{uid}-{ip}:{port} DC")
        if ip in users.logged_in_users:
            users.logout(uid, ip, cs)
    except InvalidClientData:
        print(f"{uid}-{ip}:{port} DC - modified/invalid client request")
        if ip in users.logged_in_users:
            users.logout(uid, ip, cs)
        # todo log misbehaving user


while True:
    client_socket, client_address = s.accept()
    t = Thread(target=client_connection, args=(client_socket,))
    t.daemon = True
    t.start()
