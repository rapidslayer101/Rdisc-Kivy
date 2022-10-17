from base64 import b32encode
from datetime import datetime
from hashlib import sha512
from os import path, mkdir, listdir
from random import choices
from random import randint, uniform
from socket import socket
from sys import platform
from threading import Thread
from time import perf_counter
from time import sleep
from zlib import error as zl_error

from kivy.app import App as KivyApp
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from rsa import newkeys, PublicKey, decrypt

import enclib as enc
import rdisc_kv

crash_num = 0
while True:
    try:
        if not path.exists("resources"):
            mkdir("resources")

        if not path.exists("resources/blank_captcha.png") or not path.exists("resources/blank_qr.png"):
            rdisc_kv.w_images()

        if not path.exists("rdisc.kv"):
            rdisc_kv.kv()

        if path.exists("rdisc.exe"):
            app_hash = enc.hash_a_file("rdisc.exe")
        elif path.exists("rdisc.py"):
            app_hash = enc.hash_a_file("rdisc.py")
        else:
            app_hash = f"Unknown distro: {platform}"

        version_ = None
        if path.exists("sha.txt"):
            rdisc_kv.kv()
            with open("sha.txt", "r", encoding="utf-8") as f:
                latest_sha_, version_, tme_, bld_num_, run_num_ = f.readlines()[-1].split("§")
            print("prev", version_, tme_, bld_num_, run_num_)
            release_major, major, build, run = version_.replace("V", "").split(".")
            if latest_sha_ != app_hash:
                run = int(run) + 1
                with open("sha.txt", "a+", encoding="utf-8") as f:
                    f.write(f"\n{app_hash}§V{release_major}.{major}.{build}.{run}"
                            f"§TME-{str(datetime.now())[:-4].replace(' ', '_')}"
                            f"§BLD_NM-{bld_num_[7:]}§RUN_NM-{int(run_num_[7:]) + 1}")
                    print(f"crnt V{release_major}.{major}.{build}.{run} "
                          f"TME-{str(datetime.now())[:-4].replace(' ', '_')} "
                          f"BLD_NM-{bld_num_[7:]} RUN_NM-{int(run_num_[7:])+1}")
            print(f"Running rdisc V{release_major}.{major}.{build}.{run}")

        default_salt = "52gy\"J$&)6%0}fgYfm/%ino}PbJk$w<5~j'|+R .bJcSZ.H&3z'A:gip/jtW$6A=" \
                       "G-;|&&rR81!BTElChN|+\"TCM'CNJ+ws@ZQ~7[:¬`-OC8)JCTtI¬k<i#.\"H4tq)p4"


        class Server:
            def __init__(self):
                self.s, self.enc_key = socket(), None
                if path.exists("app/server_ip"):
                    with open(f"app/server_ip", "rb") as f:
                        self.ip = f.read().decode().split(":")
                else:
                    self.ip = None

            def connect(self):
                try:  # try to connect to server
                    self.s.connect((self.ip[0], int(self.ip[1])))
                    print("Connected to server")
                    l_ip, l_port = str(self.s).split("laddr=")[1].split("raddr=")[0][2:-3].split("', ")
                    s_ip, s_port = str(self.s).split("raddr=")[1][2:-2].split("', ")
                    print(f" << Server connected via {l_ip}:{l_port} -> {s_ip}:{s_port}")
                    pub_key, pri_key = newkeys(512)
                    try:
                        self.s.send(PublicKey.save_pkcs1(pub_key))
                    except ConnectionResetError:
                        return False
                    print(" >> Public RSA key sent")
                    enc_seed = decrypt(self.s.recv(128), pri_key).decode()
                    self.enc_key = enc.pass_to_key(enc_seed[:18], enc_seed[18:], 100000)
                    print(" << Client enc_seed and enc_salt received and loaded\n -- RSA Enc bootstrap complete")
                    return True
                except ConnectionRefusedError:
                    print("Connection refused")
                    return False

            def send_e(self, text):
                try:
                    self.s.send(enc.enc_from_key(text, self.enc_key))
                except ConnectionResetError:
                    print("CONNECTION_LOST, reconnecting...")
                    if s.ip and s.connect():
                        self.s.send(enc.enc_from_key(text, self.enc_key))
                    else:
                        print("Failed to reconnect")

            def recv_d(self, buf_lim):
                try:
                    return enc.dec_from_key(self.s.recv(buf_lim), self.enc_key)
                except ConnectionResetError:
                    print("CONNECTION_LOST, reconnecting...")
                    if s.ip and s.connect():
                        return enc.dec_from_key(self.s.recv(buf_lim), self.enc_key)
                    else:
                        print("Failed to reconnect")


        s = Server()

        def error_popup(error_reason):
            App.popup_text = error_reason
            App.popup = Factory.ErrorPopup()
            App.popup.open()

        def claim_code_popup(code_text):
            App.popup_text = code_text
            App.popup = Factory.ClaimCodePopup()
            App.popup.open()

        def success_popup(success_text):
            App.popup_text = success_text
            App.popup = Factory.SuccessPopup()
            App.popup.open()

        def connect_system():
            if s.ip and s.connect():
                print("Loading account keys...")
                if path.exists(f'userdata/key'):
                    with open(f'userdata/key', 'rb') as f:
                        key_data = f.read()
                    print(" - Key data loaded")
                    App.uid, App.ipk = str(key_data[:8])[2:-1], key_data[8:]
                    App.sm.switch_to(KeyUnlock(), direction="left")
                else:
                    print(" - No keys found")
                    App.sm.switch_to(LogInOrSignUp(), direction="left")
            else:
                App.sm.switch_to(IpSet(), direction="left")


        class AttemptConnection(Screen):
            def on_enter(self, *args):
                Clock.schedule_once(lambda dt: connect_system(), 1)  # todo make this retry


        class IpSet(Screen):
            @staticmethod
            def try_connect(ip_address):
                if ip_address == "":
                    error_popup("IP Blank\n- Type an IP into the IP box")
                else:
                    try:
                        server_ip, server_port = ip_address.split(":")
                        server_port = int(server_port)
                    except ValueError or NameError:
                        error_popup("Invalid IP address\n- Please type a valid IP")
                    else:
                        if server_port < 1 or server_port > 65535:
                            error_popup("IP Port Invalid\n- Port must be between 1 and 65535")
                        else:
                            try:
                                ip_1, ip_2, ip_3, ip_4 = server_ip.split(".")
                                if all(i.isdigit() and 0 <= int(i) <= 255 for i in [ip_1, ip_2, ip_3, ip_4]):
                                    s.ip = [server_ip, server_port]
                                    App.sm.switch_to(AttemptConnection(), direction="left")
                                else:
                                    error_popup("IP Address Invalid\n- Address must have integers between 0 and 255")
                            except ValueError or NameError:
                                error_popup("IP Address Invalid\n- Address must be in the format 'xxx.xxx.xxx.xxx")


        class LogInOrSignUp(Screen):
            pass


        class KeyUnlock(Screen):
            passcode_prompt_text = StringProperty()
            counter = 0

            def on_pre_enter(self, *args):
                self.passcode_prompt_text = f"Enter passcode for account {App.uid}"
                if path.exists("password.txt"):  # this is for testing ONLY
                    with open("password.txt", "r") as f:
                        self.login(f.read())

            def login(self, pwd):
                if pwd == "":
                    self.counter += 1
                    if self.counter != 3:
                        error_popup("Password Blank\n- Top tip, type something in the password box.")
                    else:
                        error_popup("Password Blank\n- WHY IS THE BOX BLANK?")
                else:
                    try:
                        user_pass = enc.pass_to_key(pwd, default_salt, 50000)
                        user_pass = enc.pass_to_key(user_pass, App.uid)
                        ipk = enc.dec_from_pass(App.ipk, user_pass[:40], user_pass[40:])
                        s.send_e(f"ULK:{App.uid}🱫{ipk}")
                        ulk_resp = s.recv_d(128)
                        if ulk_resp == "SESH_T":
                            error_popup("This accounts session is taken.")
                        elif ulk_resp == "N":
                            error_popup("Incorrect Password\n- How exactly did you manage to trigger this.")
                        else:
                            App.uname, App.xp, App.r_coin, App.d_coin = ulk_resp.split("🱫")
                            if App.r_coin.endswith(".0"):
                                App.r_coin = App.r_coin[:-2]
                            if App.d_coin.endswith(".0"):
                                App.d_coin = App.d_coin[:-2]
                            App.sm.switch_to(Home(), direction="left")
                    except zl_error:
                        error_popup("Incorrect Password")


        class CreateKey(Screen):
            pass_code_text = StringProperty()
            pin_code_text = StringProperty()
            rand_confirm_text = StringProperty()
            rand_confirmation = None

            def generate_master_key(self, master_key, salt, depth_time, current_depth=0):
                sleep(0.2)
                start, time_left, loop_timer = perf_counter(), depth_time, perf_counter()
                if not path.exists("userdata"):
                    mkdir("userdata")
                while time_left > 0:
                    current_depth += 1
                    master_key = sha512(master_key+salt).digest()
                    if perf_counter()-loop_timer > 0.25:
                        try:
                            time_left -= (perf_counter()-loop_timer)
                            loop_timer = perf_counter()
                            real_dps = int(round(current_depth/(perf_counter()-start), 0))
                            print(f"Runtime: {round(perf_counter()-start, 2)}s  "
                                  f"Time Left: {round(time_left, 2)}s  "
                                  f"DPS: {round(real_dps/1000000, 3)}M  "
                                  f"Depth: {current_depth}/{round(real_dps*time_left, 2)}  "
                                  f"Progress: {round((depth_time-time_left)/depth_time*100, 3)}%")
                            self.pin_code_text = f"Generating Key and Pin ({round(time_left, 2)}s left)"
                        except ZeroDivisionError:
                            pass
                App.mkey = enc.to_base(96, 16, master_key.hex())
                self.rand_confirmation = str(randint(0, 9))
                self.pin_code_text = f"Account Pin: {enc.to_base(36, 10, current_depth)}"
                self.rand_confirm_text = f"Once you have written down your Account Key " \
                                         f"and Pin enter {self.rand_confirmation} below.\n" \
                                         f"By proceeding with account creation you agree to our Terms and Conditions."
                App.pin_code = enc.to_base(36, 10, current_depth)

            def on_pre_enter(self, *args):
                App.path = "make"
                acc_key = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=int(15)))
                time_depth = uniform(3, 5)
                Thread(target=self.generate_master_key, args=(acc_key[:6].encode(),
                       acc_key[6:].encode(), time_depth,), daemon=True).start()
                self.pin_code_text = f"Generating Key and Pin ({time_depth}s left)"
                acc_key_print = f"{acc_key[:5]}-{acc_key[5:10]}-{acc_key[10:15]}"
                self.pass_code_text = f"Your Account Key is: {acc_key_print}"
                App.acc_key = acc_key

            def continue_confirmation(self, confirmation_code):
                if self.rand_confirmation:
                    if confirmation_code == "":
                        error_popup("Confirmation Empty")
                    elif confirmation_code == self.rand_confirmation:
                        if platform in ["win32", "linux"]:
                            App.sm.switch_to(UsbSetup(), direction="left")
                        else:
                            App.sm.switch_to(Captcha(), direction="left")
                    else:
                        error_popup("Incorrect Confirmation Number")


        class UsbSetup(Screen):
            usb_text = StringProperty()
            skip_text = StringProperty()

            def check_usb(self):  # todo linux version
                dl = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                before_drives = [f"{d}:\\" for d in dl if path.exists(f"{d}:\\")]
                while True:
                    now_drives = [f"{d}:\\" for d in dl if path.exists(f"{d}:\\")]
                    if before_drives != now_drives:
                        try:
                            new_drive = [d for d in now_drives if d not in before_drives][0]
                            break
                        except IndexError:
                            before_drives = [f"{d}:\\" for d in dl if path.exists(f"{d}:\\")]
                    sleep(0.1)
                App.new_drive = new_drive
                self.usb_text = f"USB detected at {new_drive}\n" \
                                f"Do not unplug USB until your account is created and you are on the home screen"
                self.skip_text = "Continue"

            def on_pre_enter(self, *args):
                self.usb_text = "Detecting USB drive....\nPlease connect your USB drive\n" \
                                "(If it is already connected please disconnect and reconnect it)"
                self.skip_text = "Skip USB setup"
                Thread(target=self.check_usb, daemon=True).start()


        class ReCreateKey(Screen):
            load_text = StringProperty()
            name_or_uid = ObjectProperty()
            pass_code = ObjectProperty()
            pin_code = ObjectProperty()
            drive = None

            def on_pre_enter(self, *args):
                self.load_text = "Load from USB"

            def load_data(self):
                with open(self.drive+"mkey", "r", encoding="utf-8") as f:
                    self.name_or_uid.text, self.pass_code.text, self.pin_code.text = f.read().split("🱫")

            def detect_usb(self):
                dl = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                before_drives = [f"{d}:\\" for d in dl if path.exists(f"{d}:\\")]
                while True:
                    now_drives = [f"{d}:\\" for d in dl if path.exists(f"{d}:\\")]
                    if before_drives != now_drives:
                        try:
                            new_drive = [d for d in now_drives if d not in before_drives][0]
                            break
                        except IndexError:
                            before_drives = [f"{d}:\\" for d in dl if path.exists(f"{d}:\\")]
                    sleep(0.1)
                self.load_text = "USB loaded"
                self.drive = new_drive
                Clock.schedule_once(lambda dt: self.load_data())

            def load_from_usb(self):
                self.load_text = "Detecting USB"
                self.ids.load_from_usb_button.disabled = True
                Thread(target=self.detect_usb, daemon=True).start()

            def toggle_button(self):
                if len(self.name_or_uid.text) == 8 and len(self.pass_code.text) == 15 and self.pin_code.text:
                    self.ids.start_regen_button.disabled = False
                elif 8 < len(self.name_or_uid.text) < 29 and "#" in self.name_or_uid.text and \
                        len(self.pass_code.text) == 15 and self.pin_code.text:
                    self.ids.start_regen_button.disabled = False
                else:
                    self.ids.start_regen_button.disabled = True

            def start_regeneration(self):
                if len(self.name_or_uid.text) == 8 and len(self.pass_code.text) == 15 and self.pin_code.text:
                    App.path, App.uid = "login", self.name_or_uid.text
                    App.pass_code, App.pin_code = self.pass_code.text, self.pin_code.text
                    App.sm.switch_to(ReCreateGen(), direction="left")
                if 8 < len(self.name_or_uid.text) < 29 and "#" in self.name_or_uid.text and \
                        len(self.pass_code.text) == 15 and self.pin_code.text:
                    App.path, App.uname = "login", self.name_or_uid.text
                    App.pass_code, App.pin_code = self.pass_code.text, self.pin_code.text
                    App.sm.switch_to(ReCreateGen(), direction="left")


        class ReCreateGen(Screen):
            gen_left_text = StringProperty()

            def regenerate_master_key(self, master_key, salt, depth_to, current_depth=0):
                start, depth_left, loop_timer = perf_counter(), depth_to-current_depth, perf_counter()
                for depth_count in range(1, depth_left+1):
                    master_key = sha512(master_key+salt).digest()
                    if perf_counter()-loop_timer > 0.25:
                        try:
                            loop_timer = perf_counter()
                            real_dps = int(round(depth_count/(perf_counter()-start), 0))
                            print(f"Runtime: {round(perf_counter()-start, 2)}s  "
                                  f"Time Left: {round((depth_left-depth_count)/real_dps, 2)}s  "
                                  f"DPS: {round(real_dps/1000000, 3)}M  "
                                  f"Depth: {current_depth+depth_count}/{depth_to}  "
                                  f"Progress: {round((current_depth+depth_count)/depth_to*100, 3)}%")
                            self.gen_left_text = f"Generating master key " \
                                                 f"({round((depth_left-depth_count)/real_dps, 2)}s left)"
                        except ZeroDivisionError:
                            pass
                App.mkey = enc.to_base(96, 16, master_key.hex())
                Clock.schedule_once(lambda dt: App.sm.switch_to(Captcha(), direction="left"))

            def on_enter(self, *args):
                self.gen_left_text = f"Generating master key"
                Thread(target=self.regenerate_master_key, args=(App.pass_code[:6].encode(),
                       App.pass_code[6:].encode(), int(enc.to_base(10, 36, App.pin_code)),), daemon=True).start()


        class Captcha(Screen):
            captcha_prompt_text = StringProperty()

            def on_pre_enter(self, *args):
                self.captcha_prompt_text = "Waiting for captcha..."

            def on_enter(self, *args):
                s.send_e("CAP")
                self.get_captcha()

            def get_captcha(self):
                image = s.recv_d(32768)  # todo remove the need for a file
                with open('captcha.jpg', 'wb') as f:
                    f.write(image)
                self.captcha_prompt_text = f"Enter the text below"
                self.ids.captcha_image.source = 'captcha.jpg'

            @staticmethod
            def try_captcha(captcha_inp):
                if len(captcha_inp) == 10:
                    s.send_e(captcha_inp.replace(" ", "").replace("1", "I").replace("0", "O").upper())
                    if s.recv_d(1024) == "V":
                        if App.path == "make":
                            App.sm.switch_to(NacPassword(), direction="left")
                        if App.path == "login":
                            if App.uname:
                                s.send_e(f"LOG:{App.mkey}🱫u🱫{App.uname}")
                            else:
                                s.send_e(f"LOG:{App.mkey}🱫i🱫{App.uid}")
                            log_resp = s.recv_d(1024)
                            if log_resp == "IMK":
                                error_popup("Invalid Master Key")
                                App.sm.switch_to(ReCreateKey(), direction="left")
                            elif log_resp == "NU":
                                error_popup("Username/UID does not exist")
                                App.sm.switch_to(ReCreateKey(), direction="right")
                            else:
                                App.ipk = log_resp
                                if App.uname:
                                    App.uid = s.recv_d(1024)
                                App.sm.switch_to(LogUnlock(), direction="left")
                    else:
                        error_popup("Captcha Failed")


        class NacPassword(Screen):
            nac_password_1 = ObjectProperty(None)
            nac_password_2 = ObjectProperty(None)

            def set_nac_password(self):
                if self.nac_password_1.text == "":
                    error_popup("Password 1 Blank")
                elif self.nac_password_2.text == "":
                    error_popup("Password 2 Blank")
                elif len(self.nac_password_1.text) < 9:
                    error_popup("Password Invalid\n- Password must be at least 9 characters")
                elif self.nac_password_1.text != self.nac_password_2.text:
                    error_popup("Password Mismatch\n- Password must be the same")
                else:
                    pass_send = enc.pass_to_key(self.nac_password_1.text, default_salt, 50000)
                    s.send_e(f"NAC:{App.mkey}🱫{pass_send}")
                    App.sm.switch_to(TwoFacSetup(), direction="left")


        class LogUnlock(Screen):
            passcode_prompt_text = StringProperty()

            def on_pre_enter(self, *args):
                self.passcode_prompt_text = f"Enter passcode for account {App.uid}"

            @staticmethod
            def login(pwd):
                if pwd == "":
                    error_popup("Password Blank\n- The question is, why is it blank?")
                else:
                    try:
                        user_pass = enc.pass_to_key(pwd, default_salt, 50000)
                        user_pass = enc.pass_to_key(user_pass, App.uid)
                        ipk = enc.dec_from_pass(App.ipk, user_pass[:40], user_pass[40:])
                        s.send_e(ipk)
                        if s.recv_d(1024) == "V":
                            App.sm.switch_to(TwoFacLog(), direction="left")
                        else:
                            error_popup("Incorrect Password\n- How exactly did you manage to trigger this")
                    except zl_error:
                        error_popup("Incorrect Password")


        class TwoFacSetup(Screen):
            two_fac_wait_text = StringProperty()

            def on_pre_enter(self, *args):
                self.two_fac_wait_text = "Waiting for 2fa QR code..."

            def on_enter(self, *args):
                App.uid, secret_code = s.recv_d(1024).split("🱫")
                secret_code = b32encode(secret_code.encode()).decode().replace('=', '')
                print(secret_code)  # todo mention in UI text
                self.ids.two_fac_qr.source = "https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=otpauth%3A%2" \
                                             f"F%2Ftotp%2F{App.uid}%3Fsecret%3D{secret_code}%26issuer%3DApp"
                self.two_fac_wait_text = "Scan this QR with your authenticator, then enter code to confirm.\n" \
                                         f"Your User ID (UID) is {App.uid}"

            @staticmethod
            def confirm_2fa(two_fac_confirm):
                two_fac_confirm = two_fac_confirm.replace(" ", "")
                if two_fac_confirm == "":
                    error_popup("2FA Code Blank\n- Please enter a 2FA code")
                elif len(two_fac_confirm) != 6:
                    error_popup("Invalid 2FA Code")
                else:
                    s.send_e(two_fac_confirm.replace(" ", ""))
                    ipk = s.recv_d(1024)
                    if ipk != "N":
                        with open("userdata/key", "wb") as f:
                            f.write(App.uid.encode()+ipk)
                        App.uname, App.xp, App.r_coin, App.d_coin = s.recv_d(1024).split("🱫")
                        if App.r_coin.endswith(".0"):
                            App.r_coin = App.r_coin[:-2]
                        if App.d_coin.endswith(".0"):
                            App.d_coin = App.d_coin[:-2]
                        if App.new_drive:
                            with open(f"{App.new_drive}mkey", "w", encoding="utf-8") as f:
                                f.write(f"{App.uid}🱫{App.acc_key}🱫{App.pin_code}")
                        App.sm.switch_to(Home(), direction="left")
                    else:
                        error_popup("2FA Failed\n- Please Try Again")

        class TwoFacLog(Screen):
            @staticmethod
            def confirm_2fa(two_fac_confirm):
                two_fac_confirm = two_fac_confirm.replace(" ", "")
                if two_fac_confirm == "":
                    error_popup("2FA Code Blank\n- Please enter a 2FA code")
                elif len(two_fac_confirm) != 6:
                    error_popup("Invalid 2FA Code")
                else:
                    s.send_e(two_fac_confirm.replace(" ", ""))
                    two_fa_valid = s.recv_d(1024)
                    if two_fa_valid != "N":
                        with open("userdata/key", "wb") as f:
                            f.write(App.uid.encode()+App.ipk)
                        App.uname, App.xp, App.r_coin, App.d_coin = two_fa_valid.split("🱫")
                        if App.r_coin.endswith(".0"):
                            App.r_coin = App.r_coin[:-2]
                        if App.d_coin.endswith(".0"):
                            App.d_coin = App.d_coin[:-2]
                        App.sm.switch_to(Home(), direction="left")
                    else:
                        error_popup("2FA Failed\n- Please Try Again")


        class Home(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()
            welcome_text = StringProperty()
            transfer_uid = ObjectProperty(None)
            transfer_cost = StringProperty()
            transfer_send = StringProperty()
            transfer_fee = StringProperty()
            direction_text = StringProperty()
            coin_conversion = StringProperty()
            code = ObjectProperty(None)
            transfer_direction = "R"
            transfer_amt = None
            level_progress = [0, 100]
            transactions_counter = 0

            def on_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"
                #self.add_transaction("Coinflip [color=25be42ff]won[/color][color=f46f0eff] 50 R[/color] "
                #                     "[color=25be42ff]gained[/color] [color=f2ef32ff]10 XP[/color]")
                #self.add_transaction("Coinflip [color=fa1d04ff]lost[/color][color=f46f0eff] 50 R[/color] "
                #                     "[color=25be42ff]gained[/color] [color=f2ef32ff]10 XP[/color]")
                self.level_progress = [float(App.xp), 100]
                self.ids.level_bar_text.text = f"{self.level_progress[0]}/{self.level_progress[1]} XP"
                [self.add_transaction(transaction) for transaction in App.transactions]
                App.transactions = []

            def add_transaction(self, transaction):
                self.ids.transactions.add_widget(Label(text=transaction, font_size=16, color=(1, 1, 1, 1),
                                                       size_hint_y=None, height=40+transaction.count("\n")*20,
                                                       halign="left", markup=True))
                self.transactions_counter += 1
                if self.ids.transactions_scroll.scroll_y == 0:
                    scroll_down = True
                else:
                    scroll_down = False
                if self.transactions_counter > 101:
                    self.ids.transactions.remove_widget(self.ids.public_chat.children[-1])
                    self.ids.transactions.children[-1].text = "ONLY SHOWING LATEST 100 TRANSACTIONS"
                    self.transactions_counter -= 1
                message_height = 0
                for i in reversed(range(self.transactions_counter)):
                    self.ids.transactions.children[i].y = message_height
                    self.ids.transactions.children[i].x = 0
                    message_height += self.ids.transactions.children[i].height
                self.ids.transactions.height = message_height
                if scroll_down:
                    self.ids.transactions_scroll.scroll_y = 0
                else:
                    pass  # todo make stay still

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"
                self.welcome_text = f"Welcome back {App.uname}"
                self.transfer_cost = "0.00"
                self.transfer_send = "0.00"
                self.transfer_fee = "0.00"
                self.coin_conversion = "0.00 R"
                self.direction_text = "Conversion Calculator (£->R)"

            def check_transfer(self, transfer_amt):
                if transfer_amt not in ["", "."]:
                    transfer_amt = transfer_amt[:12]
                    if float(transfer_amt) > float(App.r_coin)*0.995:
                        transfer_amt = str(round(float(App.r_coin)*0.995, 2))
                    if "." in transfer_amt:
                        if len(transfer_amt.split(".")[1]) > 2:
                            transfer_amt = transfer_amt[:-1]
                    self.transfer_cost = str(round(float(transfer_amt)/0.995, 2))
                    self.transfer_send = transfer_amt
                    self.transfer_fee = str(round(float(self.transfer_cost) - float(transfer_amt), 2))
                if transfer_amt == ".":
                    self.transfer_amt = ""
                else:
                    self.transfer_amt = transfer_amt
                if transfer_amt == "":
                    self.transfer_cost = "0.00"
                    self.transfer_send = "0.00"
                    self.transfer_fee = "0.00"

            def transfer_coins(self):
                if self.transfer_amt == "":
                    error_popup("Below Minimum Transfer\n- Transaction amount below the 3 R minimum")
                elif len(self.transfer_uid.text) < 8:
                    error_popup("Invalid Username/UID For Transfer")
                elif self.transfer_uid.text == App.uid or self.transfer_uid.text == App.uname:
                    error_popup("You cannot transfer funds to yourself\n- WHY ARE YOU EVEN TRYING TO?!")
                elif float(self.transfer_amt) < 3:
                    error_popup("Below Minimum Transfer\n- Transaction amount below the 3 R minimum")
                elif float(self.transfer_amt) > float(App.r_coin)*0.995:
                    error_popup("Insufficient funds For Transfer")
                else:
                    #App.popup_text = f"Send {self.transfer_uid.text} R to {self.transfer_send}\n" \
                    #                 f"Fee: {self.transfer_fee}\nTotal Cost: {self.transfer_cost}"
                    #App.popup = Factory.TransferConfirmPopup()
                    #App.popup.open()
                    s.send_e(f"TRF:{self.transfer_uid.text}🱫{self.transfer_amt}")
                    if s.recv_d(1024) == "V":
                        success_popup(f"Transfer of {self.transfer_amt} R to "
                                      f"{self.transfer_uid.text} Successful")
                        App.r_coin = str(round(float(App.r_coin)-float(self.transfer_amt)/0.995, 2))
                        if App.r_coin.endswith(".0"):
                            App.r_coin = App.r_coin[:-2]
                        self.r_coins = App.r_coin+" R"
                        self.transfer_uid.text = ""
                        self.transfer_amt = ""
                    else:
                        error_popup("Invalid Username/UID For Transfer")

            def check_code(self):
                if not len(self.code.text) == 19:
                    error_popup("Invalid Code\n- Does not match format xxxx-xxxx-xxxx-xxxx")
                elif not self.code.text[5] == "-" and self.code.text[10] == "-" and self.code.text[15] == "-":
                    error_popup("Invalid Code\n- Does not match format xxxx-xxxx-xxxx-xxxx")
                else:
                    s.send_e(f"CLM:{self.code.text}")
                    code_resp = s.recv_d(1024)
                    if code_resp != "N":
                        if code_resp.startswith("R"):
                            App.r_coin = str(round(float(App.r_coin)+float(code_resp[2:]), 2))
                            if App.r_coin.endswith(".0"):
                                App.r_coin = App.r_coin[:-2]
                            self.r_coins = App.r_coin+" R"
                            success_popup(f"Successfully claimed {code_resp[2:]} R")
                            self.add_transaction(f"Claimed [color=f46f0eff]{code_resp[2:]} R[/color] from gift code")
                    else:
                        error_popup("Invalid Code")

            def convert_coins(self, amount_convert):
                if amount_convert not in ["", "."]:
                    amount_convert = amount_convert[:7]
                    if "." in amount_convert:
                        if len(amount_convert.split(".")[1]) > 2:
                            amount_convert = amount_convert[:-1]
                    if self.transfer_direction == "R":
                        amount_converted = str(round(float(amount_convert)/0.06, 2))
                    else:
                        amount_converted = str(round(float(amount_convert)*0.0585, 2))
                    if "." in amount_converted:
                        amount_converted = amount_converted[:amount_converted.index(".")+3]
                    if self.transfer_direction == "R":
                        self.coin_conversion = f"{amount_converted} R"
                    else:
                        self.coin_conversion = f"£{amount_converted}"
                else:
                    if amount_convert == "":
                        if self.transfer_direction == "R":
                            self.coin_conversion = "0.00 R"
                        else:
                            self.coin_conversion = "£0.00"

            def change_transfer_direction(self):
                self.level_progress[0] += 5
                with self.ids.level_bar.canvas:
                    Color(*App.col["yellow"])
                    RoundedRectangle(pos=self.ids.level_bar.pos,
                                     size=(self.ids.level_bar.size[0]*self.level_progress[0]/self.level_progress[1],
                                           self.ids.level_bar.size[1]))
                self.ids.level_bar_text.text = f"{self.level_progress[0]}/{self.level_progress[1]} XP"
                if self.transfer_direction == "R":
                    self.transfer_direction = "D"
                    self.direction_text = "Conversion Calculator (R->£)"
                else:
                    self.transfer_direction = "R"
                    self.direction_text = "Conversion Calculator (£->R)"


        class Chat(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()
            public_room_msg_counter = 0
            public_room_inp = ObjectProperty(None)

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"

            def send_public_message(self):
                if self.public_room_inp.text != "":
                    if "https://" in self.public_room_inp.text or "http://" in self.public_room_inp.text:
                        self.ids.public_chat.add_widget(AsyncImage(source=self.public_room_inp.text,
                                                                   size_hint_y=None, height=300, anim_delay=0.05))
                    else:
                        self.ids.public_chat.add_widget(Label(text=self.public_room_inp.text, font_size=16,
                                                              color=(1, 1, 1, 1), size_hint_y=None, height=40,
                                                              halign="left"))
                    #s.send_e(f"MSG:{self.public_room_inp.text}")
                    self.public_room_msg_counter += 1
                    if self.ids.public_room_scroll.scroll_y == 0:
                        scroll_down = True
                    else:
                        scroll_down = False
                    if self.public_room_msg_counter > 101:
                        self.ids.public_chat.remove_widget(self.ids.public_chat.children[-1])
                        self.ids.public_chat.children[-1].text = "MESSAGES ABOVE DELETED DUE 100 MESSAGE LIMIT"
                        self.public_room_msg_counter -= 1
                    message_height = 0
                    for i in range(self.public_room_msg_counter):
                        self.ids.public_chat.children[i].y = message_height
                        self.ids.public_chat.children[i].x = 0
                        message_height += self.ids.public_chat.children[i].height
                    self.ids.public_chat.height = message_height
                    self.public_room_inp.text = ""
                    if scroll_down:
                        self.ids.public_room_scroll.scroll_y = 0
                    else:
                        pass  # todo make stay still


        class Store(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"


        class Games(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"


        class Inventory(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"


        class Settings(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()
            uname = StringProperty()
            uid = StringProperty()
            uname_to = ObjectProperty(None)

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"
                self.uname = App.uname
                self.uid = App.uid

            def change_name(self):
                if float(App.d_coin) < 5:
                    error_popup("Insufficient Funds\n- You require 5 D to change your username")
                elif 4 < len(self.uname_to.text) < 25:
                    s.send_e(f"CUN:{self.uname_to.text}")
                    new_uname = s.recv_d(1024)
                    if new_uname != "N":
                        App.uname = new_uname
                        self.uname = App.uname
                        App.d_coin = str(round(float(App.d_coin)-5, 2))
                        if App.d_coin.endswith(".0"):
                            App.d_coin = App.d_coin[:-2]
                        self.d_coins = App.d_coin+" D"
                        success_popup(f"Username changed to {self.uname}")
                else:
                    error_popup("Invalid Username\n- Username must be between 5 and 24 characters")


        class ColorSettings(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()
            selected_color = None
            color_list_old = None

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"
                self.color_list_old = App.col.copy()

            def select_color(self, color_name):
                self.selected_color = color_name
                self.ids.color_picker.color = App.col[color_name]

            def change_color(self, color=None):
                if not color:
                    color = [round(rgb, 5) for rgb in self.ids.color_picker.color]
                if self.selected_color is not None:
                    App.col[self.selected_color] = color
                    if self.selected_color == "rdisc_purple":
                        with self.ids.rdisc_purple_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.rdisc_purple_btn.pos,
                                             size=self.ids.rdisc_purple_btn.size, radius=[10])
                    if self.selected_color == "rdisc_purple_dark":
                        with self.ids.rdisc_purple_dark_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.rdisc_purple_dark_btn.pos,
                                             size=self.ids.rdisc_purple_dark_btn.size, radius=[10])
                    if self.selected_color == "rdisc_cyan":
                        with self.ids.rdisc_cyan_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.rdisc_cyan_btn.pos,
                                             size=self.ids.rdisc_cyan_btn.size, radius=[10])
                    if self.selected_color == "rcoin_orange":
                        with self.ids.rcoin_orange_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.rcoin_orange_btn.pos,
                                             size=self.ids.rcoin_orange_btn.size, radius=[10])
                    if self.selected_color == "dcoin_blue":
                        with self.ids.dcoin_blue_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.dcoin_blue_btn.pos,
                                             size=self.ids.dcoin_blue_btn.size, radius=[10])
                    if self.selected_color == "link_blue":
                        with self.ids.link_blue_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.link_blue_btn.pos,
                                             size=self.ids.link_blue_btn.size, radius=[10])
                    if self.selected_color == "green":
                        with self.ids.green_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.green_btn.pos,
                                             size=self.ids.green_btn.size, radius=[10])
                    if self.selected_color == "yellow":
                        with self.ids.yellow_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.yellow_btn.pos,
                                             size=self.ids.yellow_btn.size, radius=[10])
                    if self.selected_color == "orange":
                        with self.ids.orange_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.orange_btn.pos,
                                             size=self.ids.orange_btn.size, radius=[10])
                    if self.selected_color == "red":
                        with self.ids.red_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.red_btn.pos,
                                             size=self.ids.red_btn.size, radius=[10])
                    if self.selected_color == "grey":
                        with self.ids.grey_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.grey_btn.pos,
                                             size=self.ids.grey_btn.size, radius=[10])
                    if self.selected_color == "bk_grey_1":
                        with self.ids.bk_grey_1_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.bk_grey_1_btn.pos,
                                             size=self.ids.bk_grey_1_btn.size, radius=[10])
                    if self.selected_color == "bk_grey_2":
                        with self.ids.bk_grey_2_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.bk_grey_2_btn.pos,
                                             size=self.ids.bk_grey_2_btn.size, radius=[10])
                    if self.selected_color == "bk_grey_3":
                        with self.ids.bk_grey_3_btn.canvas:
                            Color(*color)
                            RoundedRectangle(pos=self.ids.bk_grey_3_btn.pos,
                                             size=self.ids.bk_grey_3_btn.size, radius=[10])

            def reset_colors(self, color=None):
                if self.selected_color:
                    if color:
                        self.change_color(self.color_list_old[self.selected_color])
                    else:
                        for color in App.col:
                            self.selected_color = color
                            self.change_color(self.color_list_old[color])

            @staticmethod
            def reload():
                reload("reload")

            @staticmethod
            def save_colors():
                with open("color_scheme.txt", "w", encoding="utf-8") as f:
                    f.write(f"# CUSTOM COLOR SCHEME #\n")
                    for color in App.col:
                        f.write(f"{color}: {[round(rgb, 5) for rgb in App.col[color]]}\n")

            def default_theme(self, theme):
                if theme in ["purple", "pink", "green", "lime"]:
                    App.col = App.theme[theme]
                    for color in App.col:
                        self.selected_color = color
                        self.change_color(App.theme[theme][color])

        class GiftCards(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"

            def buy_gift_card(self, amount):
                if float(App.r_coin) >= float(amount):
                    s.send_e(f"BGC:{amount}")
                    gift_code = s.recv_d(1024)
                    App.r_coin = str(round(float(App.r_coin)-float(amount), 2))
                    if App.r_coin.endswith(".0"):
                        App.r_coin = App.r_coin[:-2]
                    self.r_coins = App.r_coin+" R"
                    success_popup(f"Successfully bought {amount} R gift card\nCode: {gift_code}\n\n"
                                  f"To view this code again,\ngo to your transaction history")
                    App.transactions.append(f"Bought [color=f46f0eff]{amount} R gift card[/color] for "
                                            f"[color=f46f0eff]{amount} R[/color]\n"
                                            f"Code: [color=25be42ff]{gift_code}[/color]")
                else:
                    error_popup("Insufficient Funds\n- You require more R Coins")

        class DataCoins(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"

            def buy_d(self, amount):
                if float(App.r_coin) < float(amount):
                    error_popup("Insufficient Funds\n- You require more R Coins")
                else:
                    s.send_e(f"BYD:{amount}")
                    if s.recv_d(1024) == "V":
                        App.r_coin = str(round(float(App.r_coin)-float(amount), 2))
                        d_amount = {15: 150, 35: 375, 50: 550, 100: 1150, 210: 2500}.get(amount)
                        App.d_coin = str(round(float(App.d_coin)+d_amount, 2))
                        if App.r_coin.endswith(".0"):
                            App.r_coin = App.r_coin[:-2]
                        if App.d_coin.endswith(".0"):
                            App.d_coin = App.d_coin[:-2]
                        self.d_coins = App.d_coin+" D"
                        self.r_coins = App.r_coin+" R"
                        success_popup(f"Successfully bought {d_amount} D for {amount} R")
                        App.transactions.append(f"Bought [color=15c1e0ff]{d_amount} D[/color] for "
                                                f"[color=f46f0eff]{amount} R[/color]")


        class Coinflip(Screen):
            r_coins = StringProperty()
            d_coins = StringProperty()

            def on_pre_enter(self, *args):
                self.r_coins = App.r_coin+" R"
                self.d_coins = App.d_coin+" D"
                # request coinflip data


        class Reloading(Screen):
            reload_text = StringProperty()

            def on_pre_enter(self, *args):
                self.reload_text = App.reload_text
            pass

        class WindowManager(ScreenManager):
            pass

        class App(KivyApp):
            def build(self):
                App.col = {"rdisc_purple": [104/255, 84/255, 252/255, 1],
                           "rdisc_purple_dark": [104/255, 73/255, 160/255, 1],
                           "rdisc_cyan": [37/255, 190/255, 150/255, 1],
                           "rcoin_orange": [245/255, 112/255, 15/255, 1],
                           "dcoin_blue": [22/255, 194/255, 225/255, 1],
                           "link_blue": [80/255, 154/255, 228/255, 1],
                           "green": [20/255, 228/255, 43/255, 1],
                           "yellow": [243/255, 240/255, 51/255, 1],
                           "orange": [243/255, 132/255, 1/255, 1],
                           "red": [251/255, 30/255, 5/255, 1],
                           "grey": [60/255, 60/255, 50/255, 1],
                           "bk_grey_1": [50/255, 50/255, 50/255, 1],
                           "bk_grey_2": [55/255, 55/255, 55/255, 1],
                           "bk_grey_3": [60/255, 60/255, 60/255, 1]}
                App.theme = {"purple": App.col.copy()}
                App.theme.update({"green": {"rdisc_purple": [0.0, 0.62745, 0.44314, 1.0],
                                            "rdisc_purple_dark": [0.40057, 0.55773, 0.21835, 1.0],
                                            "rdisc_cyan": [0.1451, 0.7451, 0.26237, 1],
                                            "rcoin_orange": [0.96078, 0.43922, 0.05882, 1],
                                            "dcoin_blue": [0.08627, 0.76078, 0.88235, 1],
                                            "link_blue": [0.31373, 0.60392, 0.89412, 1],
                                            "green": [0.07843, 0.89412, 0.16863, 1],
                                            "yellow": [0.95294, 0.94118, 0.2, 1],
                                            "orange": [0.95294, 0.51765, 0.00392, 1],
                                            "red": [0.98431, 0.11765, 0.01961, 1],
                                            "grey": [0.23529, 0.23529, 0.19608, 1],
                                            "bk_grey_1": [0.19608, 0.19608, 0.19608, 1],
                                            "bk_grey_2": [0.21569, 0.21569, 0.21569, 1],
                                            "bk_grey_3": [0.23529, 0.23529, 0.23529, 1]}})
                App.theme.update({"pink": {"rdisc_purple": [1.0, 0.27843, 0.44706, 1.0],
                                           "rdisc_purple_dark": [1.0, 0.42353, 0.44314, 1.0],
                                           "rdisc_cyan": [0.7687, 0.4043, 0.69965, 1],
                                           "rcoin_orange": [0.96078, 0.43922, 0.05882, 1],
                                           "dcoin_blue": [0.08627, 0.76078, 0.88235, 1],
                                           "link_blue": [0.31373, 0.60392, 0.89412, 1],
                                           "green": [0.07843, 0.89412, 0.16863, 1],
                                           "yellow": [0.95294, 0.94118, 0.2, 1],
                                           "orange": [0.95294, 0.51765, 0.00392, 1],
                                           "red": [0.98431, 0.11765, 0.01961, 1],
                                           "grey": [0.23529, 0.23529, 0.19608, 1],
                                           "bk_grey_1": [0.19608, 0.19608, 0.19608, 1],
                                           "bk_grey_2": [0.21569, 0.21569, 0.21569, 1],
                                           "bk_grey_3": [0.23529, 0.23529, 0.23529, 1]}})
                App.theme.update({"lime": {"rdisc_purple": [0.60358, 0.75294, 0.22389, 1.0],
                                           "rdisc_purple_dark": [0.6, 0.53088, 0.22353, 1.0],
                                           "rdisc_cyan": [0.8761, 0.73725, 0.2231, 1.0],
                                           "rcoin_orange": [0.96078, 0.43922, 0.05882, 1],
                                           "dcoin_blue": [0.08627, 0.76078, 0.88235, 1],
                                           "link_blue": [0.31373, 0.60392, 0.89412, 1],
                                           "green": [0.07843, 0.89412, 0.16863, 1],
                                           "yellow": [0.95294, 0.94118, 0.2, 1],
                                           "orange": [0.95294, 0.51765, 0.00392, 1],
                                           "red": [0.98431, 0.11765, 0.01961, 1],
                                           "grey": [0.23529, 0.23529, 0.19608, 1],
                                           "bk_grey_1": [0.19608, 0.19608, 0.19608, 1],
                                           "bk_grey_2": [0.21569, 0.21569, 0.21569, 1],
                                           "bk_grey_3": [0.23529, 0.23529, 0.23529, 1]}})

                if path.exists("color_scheme.txt"):
                    with open("color_scheme.txt", encoding="utf-8") as f:
                        color_scheme = f.readlines()[1:]
                    for color in color_scheme:
                        color_name, color = color.replace("\n", "").split(": ")
                        color = [float(cl) for cl in color[1:-1].split(", ")]
                        App.col[color_name] = color

                App.t_and_c = rdisc_kv.t_and_c()
                #App.uid = None  # user id
                #App.uname = None  # username
                #App.ipk = None  # ip key
                #App.pass_code = None
                #App.pin_code = None
                #App.acc_key = None
                #App.xp = None
                App.transactions = []
                App.popup = None
                App.reload_text = ""
                App.popup_text = "Popup Error"

                # app defaults and window manager
                Builder.load_file("rdisc.kv")
                App.sm = WindowManager()
                [App.sm.add_widget(screen) for screen in [AttemptConnection(name="AttemptConnection"),
                 IpSet(name="IpSet"), LogInOrSignUp(name="LogInOrSignUp"), KeyUnlock(name="KeyUnlock"),
                 CreateKey(name="CreateKey"), UsbSetup(name="UsbSetup"), ReCreateKey(name="ReCreateKey"),
                 ReCreateGen(name="ReCreateGen"), Captcha(name="Captcha"), NacPassword(name="NacPassword"),
                 LogUnlock(name="LogUnlock"), TwoFacSetup(name="TwoFacSetup"), TwoFacLog(name="TwoFacLog"),
                 Home(name="Home"), Chat(name="Chat"), Store(name="Store"), Games(name="Games"),
                 Inventory(name="Inventory"), Settings(name="Settings"), ColorSettings(name="ColorSettings"),
                 GiftCards(name="GiftCards"), DataCoins(name="DataCoins"), Coinflip(name="Coinflip"),
                 Reloading(name="Reloading")]]

                if version_:
                    App.title = f"Rdisc-{version_}"
                elif path.exists("rdisc.py"):
                    App.title = "Rdisc-Dev"
                else:
                    App.title = [file for file in listdir('app') if
                                 file.endswith('.exe')][-1][:-4].replace("rdisc", "Rdisc")
                if platform in ["win32", "linux"]:
                    Window.size = (1264, 681)

                Window.bind(on_keyboard=on_keyboard)
                Config.set('input', 'mouse', 'mouse,disable_multitouch')
                Config.set('kivy', 'exit_on_escape', '0')
                return App.sm

        def on_keyboard(window, key, scancode, text, modifiers):
            if 'ctrl' in modifiers and text == 'r':
                reload("reload")
            if 'ctrl' in modifiers and text == 'x':
                App.get_running_app().stop()
            if 'ctrl' and 'alt' in modifiers and text == 'c':
                App.stop()  # Forces a crash
            if App.popup and key == 8:
                App.popup.dismiss()
                App.popup = None

        def reload(reason):
            current_screen = App.sm.current
            if reason == "reload":
                App.reload_text = "Reloading..."
            if reason == "crash":
                App.reload_text = "Rdisc crashed, reloading..."
                if s.ip:
                    s.s.close()
            #if reason == "crash_loop":
            #    App.reload_text = "Rdisc crashed and was unable to reload."
            App.sm.current = "Reloading"
            Builder.unload_file("rdisc.kv")
            while len(App.sm.screens) > 2:
                [App.sm.remove_widget(screen) for screen in App.sm.screens if screen.name not in ["Reloading", ""]]
            if reason == "reload":
                Builder.load_file("rdisc.kv")
            [App.sm.add_widget(screen) for screen in [AttemptConnection(name="AttemptConnection"),
             IpSet(name="IpSet"), LogInOrSignUp(name="LogInOrSignUp"), KeyUnlock(name="KeyUnlock"),
             CreateKey(name="CreateKey"), UsbSetup(name="UsbSetup"), ReCreateKey(name="ReCreateKey"),
             ReCreateGen(name="ReCreateGen"), Captcha(name="Captcha"), NacPassword(name="NacPassword"),
             LogUnlock(name="LogUnlock"), TwoFacSetup(name="TwoFacSetup"), TwoFacLog(name="TwoFacLog"),
             Home(name="Home"), Chat(name="Chat"), Store(name="Store"), Games(name="Games"),
             Inventory(name="Inventory"), Settings(name="Settings"), ColorSettings(name="ColorSettings"),
             GiftCards(name="GiftCards"), DataCoins(name="DataCoins"), Coinflip(name="Coinflip")]]
            if reason == "reload":
                if current_screen == "_screen0":
                    current_screen = "Home"
                App.sm.current = current_screen


        if __name__ == "__main__":
            App().run()
            break

    except Exception as e:
        crash_num += 1
        print(f"Error {crash_num} caught: {e}")
        if crash_num == 5:
            App.reload_text = "Crash loop detected, exiting app in 5 seconds..."
            #reload("crash_loop")
            sleep(5)
            break
        else:
            reload("crash")
