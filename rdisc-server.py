import sqlite3
from enclib import rand_b96_str, pass_to_key, enc_from_key, enc_from_pass, dec_from_key
from gamelib import coin_game
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from time import sleep
from datetime import datetime, timedelta
from rsa import PublicKey, encrypt
from zlib import error as zl_error
from os import listdir, path, mkdir
from csv import writer, reader
from threading import Thread
from random import choices, randint
from requests import get
from captcha.image import ImageCaptcha


class InvalidClientData(Exception):
    pass


if not path.exists('users'):
    mkdir('users')


class Users:
    chat_users = {}
    logged_in_users = []
    uid_keys = {}

    def __init__(self):
        self.db = sqlite3.connect('rdisc_server.db', check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY NOT NULL UNIQUE,"
                        "creation_time DATE NOT NULL, master_key TEXT NOT NULL, secret TEXT NOT NULL,"
                        "user_pass TEXT NOT NULL, ipk1 TEXT, ipk2 TEXT, ipk3 TEXT, ipk4 TEXT, "
                        "username TEXT NOT NULL, last_online DATE NOT NULL, xp FLOAT NOT NULL, r_coin FLOAT NOT NULL, "
                        "d_coin FLOAT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS codes (code TEXT PRIMARY KEY NOT NULL UNIQUE,"
                        "expiry_date DATE NOT NULL, left TEXT NOT NULL, reward_type TEXT NOT NULL, "
                        "amount FLOAT NOT NULL)")

    def login(self, u_id, ip, enc_key):
        self.logged_in_users.append(u_id)
        self.logged_in_users.append(ip)
        self.uid_keys.update({u_id: enc_key})

    def logout(self, u_id, ip):
        try:
            self.logged_in_users.pop(self.logged_in_users.index(u_id))
            self.logged_in_users.pop(self.logged_in_users.index(ip))
            self.uid_keys.pop(u_id)
            self.db.execute("UPDATE users SET last_online = ? WHERE user_id = ?", (str(datetime.now())[:-7], u_id))
            self.db.commit()
        except ValueError:
            pass

    def add_user(self, uid, master_key, secret, u_pass, ipk, username):
        now = str(datetime.now())[:-7]
        expiry_time = str(datetime.now()+timedelta(days=14))[:-7]
        self.db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (uid, now,
                        pass_to_key(master_key, uid), enc_from_key(secret, u_pass),
                        pass_to_key(u_pass, uid), ipk+"🱫"+expiry_time, None,
                        None, None, username, now, 0, 0, 350))
        self.db.commit()
        mkdir(f"users/{uid}")
        with open(f"users/{uid}/friends.csv", 'w') as f:
            f.write("")
        with open(f"users/{uid}/transactions.csv", "w", newline='', encoding="utf-8") as csv:
            writer(csv).writerows([["Date", "Type", "Amount", "Spent", "Description", "Hash"],
                                  [str(datetime.now())[:-7], "NACD", "350", "0", "New account 350 D bonus",
                                   pass_to_key(f"{str(datetime.now())[:-7]}" 
                                   "NACD3500New account 350 D bonus", uid)]])

    def check_logged_in(self, uid, ip):
        if uid in self.logged_in_users:
            return True
        elif ip in self.logged_in_users:
            return True
        else:
            return False


    def join_chat(self, uid, cs):
        self.chat_users.update({uid: cs})


def add_transaction(uid, t_type, amount, spent, desc):
    with open(f"users/{uid}/transactions.csv", "r", encoding="utf-8") as csv:
        prev_hash = list(reader(csv))[-1][5]
    with open(f"users/{uid}/transactions.csv", "a", newline='', encoding="utf-8") as csv:
        writer(csv).writerow([str(datetime.now())[:-7], t_type, amount, spent, desc,
                              pass_to_key(f"{str(datetime.now())[:-7]}{t_type}{amount}{spent}{desc}", prev_hash)])


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
        enc_seed = rand_b96_str(36)
        cs.send(encrypt(enc_seed.encode(), pub_key_cli))
        enc_key = pass_to_key(enc_seed[:18], enc_seed[18:], 100000)
        coinflip_games = []
        request = None

        def send_e(text):
            try:
                cs.send(enc_from_key(text, enc_key))
            except zl_error:
                raise ConnectionResetError

        def recv_d(buf_lim=1024):
            try:
                return dec_from_key(cs.recv(buf_lim), enc_key)
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
            login_request = recv_d()
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
                    captcha_attempt = recv_d()
                    if captcha_attempt != captcha_text:
                        send_e("N")
                        if counter > 3:
                            sleep(10)  # rate limit
                    else:
                        send_e("V")
                        break

                log_or_create = recv_d()
                if log_or_create.startswith("NAC:"):  # new account
                    master_key, u_pass = log_or_create[4:].split("🱫")
                    while True:
                        uid = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=8))
                        u_name = uid+"#"+str(randint(111, 999))
                        if users.db.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,)).fetchone() is None:
                            break
                    u_secret = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYabcdefghijklmnopqrstuvwxyz", k=8))
                    send_e(f"{uid}🱫{u_secret}")
                    while True:
                        code_challenge = recv_d()
                        if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                               f"Pin={code_challenge}&SecretCode={u_secret}").content != b"True":
                            send_e("N")
                        else:
                            ipk = rand_b96_str(24)
                            send_e(enc_from_pass(ipk, u_pass[:40], u_pass[40:]))
                            send_e(f"{u_name}🱫0🱫0🱫350")
                            users.add_user(uid, master_key, u_secret, u_pass,
                                           pass_to_key(ip+ipk, uid), u_name)
                            break

                if log_or_create.startswith("LOG:"):
                    master_key_c, search_for, uname_or_uid = log_or_create[4:].split("🱫")
                    if search_for == "u":
                        try:
                            uid, master_key, u_secret, u_pass, u_name, xp, r_coin, d_coin = users.db.execute(
                                "SELECT user_id, master_key, secret, user_pass, username, xp, r_coin, d_coin "
                                "FROM users WHERE username = ?", (uname_or_uid,)).fetchone()
                        except TypeError:
                            uid = None
                            send_e("NU")  # user does not exist
                    else:
                        try:
                            uid = uname_or_uid
                            master_key, u_secret, u_pass, u_name, xp, r_coin, d_coin = users.db.execute(
                                "SELECT master_key, secret, user_pass, username, xp, r_coin, d_coin "
                                "FROM users WHERE user_id = ?", (uname_or_uid,)).fetchone()
                        except TypeError:
                            uid = None
                            send_e("NU")  # user does not exist
                    if uid:
                        if pass_to_key(master_key_c, uid) != master_key:
                            send_e("IMK")  # master key wrong
                        else:
                            send_e("V")
                            if search_for == "u":
                                send_e(uid)
                            while True:
                                u_pass_c = recv_d()
                                if pass_to_key(u_pass_c, uid) == u_pass:
                                    ipk = rand_b96_str(24)
                                    send_e(enc_from_pass(ipk, u_pass_c[:40], u_pass_c[40:]))
                                    break
                                else:
                                    send_e("N")
                            u_secret = dec_from_key(u_secret, u_pass_c)
                            while True:
                                code_challenge = recv_d()
                                if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                                       f"Pin={code_challenge}&SecretCode={u_secret}").content != b"True":
                                    send_e("N")
                                else:
                                    break
                            send_e(f"{u_name}🱫{xp}🱫{r_coin}🱫{d_coin}")
                            ipk1, ipk2, ipk3, ipk4 = users.db.execute(
                                "SELECT ipk1, ipk2, ipk3, ipk4 FROM users WHERE user_id = ?",
                                (uid,)).fetchone()  # get ip keys from db

                            expiry_time = str(datetime.now() + timedelta(days=14))[:-7]
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
                                users.db.execute("UPDATE users SET ipk" + oldest_ipk + " = ? WHERE user_id = ?",
                                                 (pass_to_key(ip+ipk, uid)+"🱫"+expiry_time, uid))
                            elif not ipk1:  # save to empty ip key
                                users.db.execute("UPDATE users SET ipk1 = ? WHERE user_id = ?",
                                                 (pass_to_key(ip+ipk, uid)+"🱫"+expiry_time, uid))
                            elif not ipk2:
                                users.db.execute("UPDATE users SET ipk2 = ? WHERE user_id = ?",
                                                 (pass_to_key(ip+ipk, uid)+"🱫"+expiry_time, uid))
                            elif not ipk3:
                                users.db.execute("UPDATE users SET ipk3 = ? WHERE user_id = ?",
                                                 (pass_to_key(ip+ipk, uid)+"🱫"+expiry_time, uid))
                            elif not ipk4:
                                users.db.execute("UPDATE users SET ipk4 = ? WHERE user_id = ?",
                                                 (pass_to_key(ip+ipk, uid)+"🱫"+expiry_time, uid))
                            users.db.commit()
                            break

            elif login_request.startswith("ULK:"):
                uid, u_ipk = login_request[4:].split("🱫")
                print(uid, u_ipk)
                if users.check_logged_in(uid, ip):
                    send_e("SESH_T")
                else:
                    try:
                        ipk1, ipk2, ipk3, ipk4, u_name, xp, r_coin, d_coin = \
                            users.db.execute("SELECT ipk1, ipk2, ipk3, ipk4, username, xp, r_coin, "
                                             "d_coin FROM users WHERE user_id = ?", (uid,)).fetchone()
                    except ValueError:
                        send_e("N")  # User ID not found
                    else:
                        u_ipk = pass_to_key(ip+u_ipk, uid)

                        def check_ipk(ipk):
                            ipk, ipk_e = ipk.split("🱫")
                            if u_ipk != ipk:
                                return False
                            elif datetime.now() < datetime.strptime(ipk_e, "%Y-%m-%d %H:%M:%S"):
                                return True
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

        users.login(uid, ip, enc_key)
        print(f"{uid} logged in with IP-{ip}:{port}")
        while True:  # main loop
            request = recv_d()
            print(request)  # temp debug for dev

            if request.startswith("LOG_A"):  # deletes all IP keys
                raise ConnectionResetError

            elif request.startswith("DLAC:"):  # todo delete account
                pass

            elif request.startswith("BGC:"):  # buy gift card
                try:
                    amount = int(request[4:])
                except ValueError:
                    raise InvalidClientData
                if amount not in [25, 40, 100, 250, 600]:
                    raise InvalidClientData
                elif r_coin >= amount:
                    r_coin = round(r_coin - amount, 2)
                    users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?", (r_coin, uid))
                    while True:
                        code = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXY", k=16))
                        try:
                            users.db.execute("INSERT INTO codes VALUES (?, ?, ?, ?, ?)", (code,
                                             str(datetime.now()+timedelta(days=14))[:-7], 1, "R", amount))
                            break
                        except sqlite3.IntegrityError:
                            pass
                    users.db.commit()
                    add_transaction(uid, "BGC", amount, amount, f"Code: {code}")
                    send_e(f"{code[:4]}-{code[4:8]}-{code[8:12]}-{code[12:]}")
                else:
                    raise InvalidClientData

            elif request.startswith("BYD:"):  # buy d_coin
                try:
                    amount = int(request[4:])
                except ValueError:
                    raise InvalidClientData
                if amount not in [15, 35, 50, 100, 210]:
                    raise InvalidClientData
                elif r_coin >= amount:
                    r_coin = round(r_coin-amount, 2)
                    d_coin_amt = {15: 150, 35: 375, 50: 550, 100: 1150, 210: 2500}.get(amount)
                    users.db.execute("UPDATE users SET r_coin = ?, d_coin = ? WHERE user_id = ?",
                                     (r_coin, d_coin+d_coin_amt, uid))
                    users.db.commit()
                    add_transaction(uid, "BUYD", d_coin_amt, amount, "Bought d_coin")
                    send_e("V")
                else:
                    raise InvalidClientData

            elif request.startswith("CUP:"):  # change user password
                u_pass_c = request[4:]
                try:
                    u_pass, u_secret = users.db.execute("SELECT user_pass, secret FROM users WHERE user_id = ?",
                                                        (uid,)).fetchone()
                    if pass_to_key(u_pass_c, uid) != u_pass:
                        send_e("N")
                    else:
                        send_e("V")
                        n_u_pass = recv_d()
                        u_secret = dec_from_key(u_secret, u_pass_c)
                        while True:
                            code_challenge = recv_d()
                            if get(f"https://www.authenticatorapi.com/Validate.aspx?"
                                   f"Pin={code_challenge}&SecretCode={u_secret}").content != b"True":
                                send_e("N")
                            else:
                                break
                        n_ipk = rand_b96_str(24)
                        expiry_time = str(datetime.now() + timedelta(days=14))[:-7]
                        users.db.execute("UPDATE users SET secret = ?, user_pass = ?, ipk1 = ?, ipk2 = ?, ipk3 = ?, "
                                         "ipk4 = ? WHERE user_id = ?", (enc_from_key(u_secret, n_u_pass),
                                                                        pass_to_key(n_u_pass, uid),
                                                                        pass_to_key(ip+n_ipk,uid)+"🱫"+expiry_time,
                                                                        None, None, None, uid))
                        users.db.commit()
                        send_e(enc_from_pass(n_ipk, n_u_pass[:40], n_u_pass[40:]))
                except sqlite3.OperationalError:
                    send_e("N")

            elif request.startswith("CUN:"):  # change username
                if d_coin < 5:
                    raise InvalidClientData
                else:
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
                                add_transaction(uid, "CUN", 0, 5, f"Changed u_name to {n_u_name_i}")
                                send_e(n_u_name_i)
                                u_name = n_u_name_i
                                break
                        except sqlite3.OperationalError:
                            if counter == 10:
                                send_e("N")
                                break

            elif request.startswith("JNC"):  # join public chat
                Users.chat_users.update({uid: cs})
                while True:
                    u_msg = recv_d()
                    if u_msg == "LVC":  # leave public chat
                        Users.chat_users.pop(uid)
                        send_e("LVC🱫")
                        break
                    else:
                        for user_id in Users.chat_users.keys():  # todo keys for each user
                            if user_id != uid:
                                try:
                                    print(user_id, Users.chat_users[user_id])
                                    Users.chat_users[user_id].send(enc_from_key(f"{u_name}🱫{u_msg}",
                                                                                Users.uid_keys[user_id]))
                                except zl_error:
                                    raise ConnectionResetError

            elif request.startswith("TRF:"):  # transfer R coins
                transfer_to, transfer_amount = request[4:].split("🱫")
                if round(float(transfer_amount)/0.995, 2) > r_coin:
                    raise InvalidClientData
                if transfer_to == uid:
                    raise InvalidClientData
                try:
                    transfer_to_r_coin = users.db.execute("SELECT r_coin FROM users WHERE username = ?",
                                                          (transfer_to,)).fetchone()[0]
                    r_coin = round(float(r_coin)-float(transfer_amount)/0.995, 2)
                    users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?", (r_coin, uid))
                    users.db.execute("UPDATE users SET r_coin = ? WHERE username = ?",
                                     (float(transfer_to_r_coin)+float(transfer_amount), transfer_to))
                    users.db.commit()
                    add_transaction(uid, "TRF", float(transfer_amount)/0.995, float(transfer_amount),
                                    f"Transferred to {transfer_to}")
                    send_e("V")
                except TypeError:
                    try:  # todo what if the user is already logged in, resolve username to UID
                        transfer_to_r_coin = users.db.execute("SELECT r_coin FROM users WHERE user_id = ?",
                                                              (transfer_to,)).fetchone()[0]
                        r_coin = round(float(r_coin)-float(transfer_amount)/0.995, 2)
                        users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?", (r_coin, uid))
                        users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?",
                                         (float(transfer_to_r_coin)+float(transfer_amount), transfer_to))
                        users.db.commit()
                        add_transaction(uid, "TRF", float(transfer_amount)/0.995, float(transfer_amount),
                                        f"Transferred to {transfer_to}")
                        send_e("V")
                    except TypeError:
                        send_e("N")  # user not exist

            elif request.startswith("CLM:"):  # claim code
                code = request[4:].replace("-", "")
                code_data = users.db.execute("SELECT * FROM codes WHERE code = ?", (code,)).fetchone()
                if code_data is None:
                    send_e("N")
                elif code_data[3] == "R":
                    r_coin = round(r_coin+float(code_data[4]), 2)
                    users.db.execute("UPDATE users SET r_coin = ? WHERE user_id = ?", (r_coin, uid))
                    users.db.commit()
                    add_transaction(uid, "CLM", float(code_data[4]), 0, f"Claimed code: {code}")
                    send_e(f"R:{code_data[4]}")
                if code_data[2] == "1":
                    users.db.execute("DELETE FROM codes WHERE code = ?", (code,))
                    users.db.commit()
                elif code_data[2] == "-1":  # infinite code
                    pass
                else:
                    users.db.execute("UPDATE codes SET left = ? WHERE code = ?", (int(code_data[2])-1, code))
                    users.db.commit()

            elif request.startswith("AFR:"):
                add_friend_n = request[6:]
                if 9 < len(add_friend_n) < 38:
                    try:
                        int(add_friend_n[-4:])
                        if add_friend_n[-5] != "#":
                            raise InvalidClientData
                        else:
                            print("process new friend", add_friend_n)
                    except ValueError:
                        raise InvalidClientData
                else:
                    raise InvalidClientData

            elif request.startswith("MCF:"):  # create coinflip game  # todo make game expire after x time
                mult = request[4:]
                if len(coinflip_games) > 0:
                    coinflip_games.pop()
                if mult not in ["2", "3", "5", "10"]:
                    raise InvalidClientData
                else:
                    odds = {"2": "470:530", "3": "310:690", "5": "190:810", "10": "105:895"}.get(mult)
                    print(odds)
                    seed_inp, rand_float, outcome, game_hash = coin_game(odds)
                    print(seed_inp, rand_float, outcome, game_hash, mult)
                    coinflip_games.append([seed_inp, rand_float, outcome, game_hash, mult])
                    send_e(game_hash)

            elif request.startswith("RCF:"):  # accept coinflip game
                game_hash_c, bet_amt = request[4:].split("🱫")
                if game_hash_c == coinflip_games[0][3]:
                    if float(bet_amt) > r_coin:
                        raise InvalidClientData
                    elif float(bet_amt) > 30:
                        raise InvalidClientData
                    else:
                        if outcome == "WIN":
                            r_coin = round(r_coin+float(bet_amt)*int(coinflip_games[0][4]), 2)
                            add_transaction(uid, f"COF{coinflip_games[0][4]}", float(bet_amt),
                                            float(bet_amt)*int(coinflip_games[0][4]),
                                            "Coinflip win")
                        else:
                            r_coin = round(r_coin-float(bet_amt), 2)
                            add_transaction(uid, f"COF{coinflip_games[0][4]}", float(bet_amt), 0, "Coinflip loss")
                        xp += round(float(bet_amt)/5, 2)
                        users.db.execute("UPDATE users SET xp = ?, r_coin = ? WHERE user_id = ?", (xp, r_coin, uid))
                        users.db.commit()
                        send_e(f"{seed_inp}🱫{rand_float}🱫{outcome}")
                        coinflip_games.pop()

            else:
                raise InvalidClientData  # invalid request

    except ConnectionResetError:
        print(f"{uid}-{ip}:{port} DC")
        if ip in users.logged_in_users:
            users.logout(uid, ip)
    except InvalidClientData:
        print(f"{uid}-{ip}:{port} DC - modified/invalid client request")
        if ip in users.logged_in_users:
            users.logout(uid, ip)
        with open(f"users/{uid}/log.txt", "a") as log:
            if request:
                log.write(f"{str(datetime.now())[:-7]} - ICR: {request}\n")
            else:
                log.write(f"{str(datetime.now())[:-7]} - ICR: None\n")


while True:
    client_socket, client_address = s.accept()
    t = Thread(target=client_connection, args=(client_socket,), daemon=True).start()
