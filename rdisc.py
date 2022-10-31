import rdisc_kv
from enclib import hash_a_file, to_base, pass_to_key, enc_from_key, dec_from_pass, dec_from_key
from base64 import b32encode
from datetime import datetime
from hashlib import sha512
from os import path, mkdir, listdir
from random import randint, uniform, choices
from socket import socket
from threading import Thread
from time import perf_counter, sleep
from zlib import error as zl_error

from kivy.app import App as KivyApp
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.graphics import Line, Color, RoundedRectangle
from kivy.utils import platform, get_color_from_hex as rgb
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from rsa import newkeys, PublicKey, decrypt

if path.exists("rdisc.exe"):
    app_hash = hash_a_file("rdisc.exe")
elif path.exists("rdisc.py"):
    app_hash = hash_a_file("rdisc.py")
else:
    app_hash = f"Unknown distro: {platform}"

version = None
if path.exists("sha.txt"):
    rdisc_kv.kv()
    with open("sha.txt", "r", encoding="utf-8") as f:
        latest_sha_, version, tme_, bld_num_, run_num_ = f.readlines()[-1].split("§")
    print("prev", version, tme_, bld_num_, run_num_)
    release_major, major, build, run = version.replace("V", "").split(".")
    if latest_sha_ != app_hash:
        run = int(run)+1
        with open("sha.txt", "a+", encoding="utf-8") as f:
            f.write(f"\n{app_hash}§V{release_major}.{major}.{build}.{run}"
                    f"§TME-{str(datetime.now())[:-4].replace(' ', '_')}"
                    f"§BLD_NM-{bld_num_[7:]}§RUN_NM-{int(run_num_[7:]) + 1}")
            print(f"crnt V{release_major}.{major}.{build}.{run} "
                  f"TME-{str(datetime.now())[:-4].replace(' ', '_')} "
                  f"BLD_NM-{bld_num_[7:]} RUN_NM-{int(run_num_[7:]) + 1}")
    print(f"Running rdisc V{release_major}.{major}.{build}.{run}")

default_salt = "52gy\"J$&)6%0}fgYfm/%ino}PbJk$w<5~j'|+R .bJcSZ.H&3z'A:gip/jtW$6A=G-;|&&rR81!BTElChN|+\"T"


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
            self.enc_key = pass_to_key(enc_seed[:18], enc_seed[18:], 100000)
            print(" << Client enc_seed and enc_salt received and loaded\n -- RSA Enc bootstrap complete")
            return True
        except ConnectionRefusedError:
            print("Connection refused")
            return False

    def send_e(self, text):
        try:
            self.s.send(enc_from_key(text, self.enc_key))
        except ConnectionResetError:
            print("CONNECTION_LOST, reconnecting...")
            if s.ip and s.connect():
                self.s.send(enc_from_key(text, self.enc_key))
            else:
                print("Failed to reconnect")

    def recv_d(self, buf_lim):
        try:
            return dec_from_key(self.s.recv(buf_lim), self.enc_key)
        except ConnectionResetError:
            print("CONNECTION_LOST, reconnecting...")
            if s.ip and s.connect():
                return dec_from_key(self.s.recv(buf_lim), self.enc_key)
            else:
                print("Failed to reconnect")


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
    pwd = ObjectProperty(None)
    counter = 0

    def on_pre_enter(self, *args):
        self.passcode_prompt_text = f"Enter passcode for account {App.uid}"
        if path.exists("password.txt"):  # this is for testing ONLY
            with open("password.txt", "r") as f:
                self.pwd.text = f.read()
                self.login()

    def login(self):
        if self.pwd.text == "":
            self.counter += 1
            if self.counter != 3:
                error_popup("Password Blank\n- Top tip, type something in the password box.")
            else:
                error_popup("Password Blank\n- WHY IS THE BOX BLANK?")
        else:
            try:
                user_pass = pass_to_key(self.pwd.text, default_salt, 50000)
                ipk = dec_from_pass(App.ipk, user_pass[:40], user_pass[40:])
                s.send_e(f"ULK:{App.uid}🱫{ipk}")
                ulk_resp = s.recv_d(128)
                if ulk_resp == "SESH_T":
                    error_popup("This accounts session is taken.")
                elif ulk_resp == "N":
                    error_popup("Incorrect Password\n- How exactly did you manage to trigger this.")
                    self.pwd.text = ""
                else:
                    App.uname, App.xp, App.r_coin, App.d_coin = ulk_resp.split("🱫")
                    if App.r_coin.endswith(".0"):
                        App.r_coin = App.r_coin[:-2]
                    if App.d_coin.endswith(".0"):
                        App.d_coin = App.d_coin[:-2]
                    App.sm.switch_to(Home(), direction="left")
            except zl_error:
                error_popup("Incorrect Password")
                self.pwd.text = ""


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
        App.mkey = to_base(96, 16, master_key.hex())
        self.rand_confirmation = str(randint(0, 9))
        self.pin_code_text = f"Account Pin: {to_base(36, 10, current_depth)}"
        self.rand_confirm_text = f"Once you have written down your Account Key " \
                                 f"and Pin enter {self.rand_confirmation} below.\n" \
                                 f"By proceeding with account creation you agree to our Terms and Conditions."
        App.pin_code = to_base(36, 10, current_depth)

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
                if platform in ["win", "linux"]:
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
        App.mkey = to_base(96, 16, master_key.hex())
        Clock.schedule_once(lambda dt: App.sm.switch_to(Captcha(), direction="left"))

    def on_enter(self, *args):
        self.gen_left_text = f"Generating master key"
        Thread(target=self.regenerate_master_key, args=(App.pass_code[:6].encode(),
               App.pass_code[6:].encode(), int(to_base(10, 36, App.pin_code)),), daemon=True).start()


class Captcha(Screen):
    captcha_prompt_text = StringProperty()
    captcha_inp = ObjectProperty(None)

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

    def try_captcha(self):
        if len(self.captcha_inp.text) == 10:
            s.send_e(self.captcha_inp.text.replace(" ", "").replace("1", "I").replace("0", "O").upper())
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
            error_popup("Password Mismatch\n- Passwords must be the same")
        else:
            pass_send = pass_to_key(self.nac_password_1.text, default_salt, 50000)
            if App.path == "CHANGE_PASS":
                s.send_e(pass_send)
                App.sm.switch_to(TwoFacLog(), direction="left")
            else:
                s.send_e(f"NAC:{App.mkey}🱫{pass_send}")
                App.sm.switch_to(TwoFacSetup(), direction="left")


class LogUnlock(Screen):
    pwd = ObjectProperty(None)
    passcode_prompt_text = StringProperty()

    def on_pre_enter(self, *args):
        self.passcode_prompt_text = f"Enter passcode for account {App.uid}"

    def login(self):
        if self.pwd.text == "":
            error_popup("Password Blank\n- The question is, why is it blank?")
        else:
            try:
                user_pass = pass_to_key(self.pwd.text, default_salt, 50000)
                s.send_e(user_pass)
                ipk = s.recv_d(1024)
                if ipk == "N":
                    error_popup("Incorrect Password\n- How exactly did you manage to trigger this")
                    self.pwd.text = ""
                else:
                    App.ipk = ipk
                    App.sm.switch_to(TwoFacLog(), direction="left")
            except zl_error:
                error_popup("Incorrect Password")
                self.pwd.text = ""


class TwoFacSetup(Screen):
    two_fac_wait_text = StringProperty()
    two_fac_code = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.two_fac_wait_text = "Waiting for 2fa QR code..."

    def on_enter(self, *args):
        App.uid, secret_code = s.recv_d(1024).split("🱫")
        secret_code = b32encode(secret_code.encode()).decode().replace('=', '')
        print(secret_code)  # todo mention in UI text
        self.ids.two_fac_qr.source = "https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=otpauth%3A%2" \
                                     f"F%2Ftotp%2F{App.uid}%3Fsecret%3D{secret_code}%26issuer%3DRdisc"
        self.two_fac_wait_text = "Scan this QR with your authenticator, then enter code to confirm.\n" \
                                 f"Your User ID (UID) is {App.uid}"

    def confirm_2fa(self):
        if self.two_fac_code.text == "":
            error_popup("2FA Code Blank\n- Please enter a 2FA code")
        elif len(self.two_fac_code.text) != 6:
            error_popup("Invalid 2FA Code")
        else:
            s.send_e(self.two_fac_code.text.replace(" ", ""))
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
    two_fac_code = ObjectProperty(None)

    def confirm_2fa(self):
        if self.two_fac_code.text == "":
            error_popup("2FA Code Blank\n- Please enter a 2FA code")
        elif len(self.two_fac_code.text) != 6:
            error_popup("Invalid 2FA Code")
        else:
            s.send_e(self.two_fac_code.text.replace(" ", ""))
            two_fa_valid = s.recv_d(1024)
            if two_fa_valid == "N":
                error_popup("2FA Failed\n- Please Try Again")
            elif App.path == "CHANGE_PASS":
                with open("userdata/key", "wb") as f:
                    f.write(App.uid.encode()+two_fa_valid)
                App.sm.switch_to(Settings(), direction="left")
                success_popup("Password Changed")
            else:
                with open("userdata/key", "wb") as f:
                    f.write(App.uid.encode()+App.ipk)
                App.uname, App.xp, App.r_coin, App.d_coin = two_fa_valid.split("🱫")
                if App.r_coin.endswith(".0"):
                    App.r_coin = App.r_coin[:-2]
                if App.d_coin.endswith(".0"):
                    App.d_coin = App.d_coin[:-2]
                App.sm.switch_to(Home(), direction="left")


class Home(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()
    welcome_text = StringProperty()
    transfer_uid = ObjectProperty(None)
    transfer_amt = ObjectProperty(None)
    transfer_cost = StringProperty()
    transfer_send = StringProperty()
    transfer_fee = StringProperty()
    direction_text = StringProperty()
    coin_conversion = StringProperty()
    code = ObjectProperty(None)
    transfer_direction = "R"
    level_progress = [0, 100]
    transactions_counter = 0

    def update_level_bar(self):
        self.level_progress = [round(float(App.xp), 2), 100]
        self.ids.level_bar_text.text = f"{self.level_progress[0]}/{self.level_progress[1]} XP"
        with self.ids.level_bar.canvas:
            Color(*App.col["yellow"])
            RoundedRectangle(pos=self.ids.level_bar.pos,
                             size=(self.ids.level_bar.size[0]*self.level_progress[0]/self.level_progress[1],
                                   self.ids.level_bar.size[1]))

    def on_enter(self, *args):
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"
        Clock.schedule_once(lambda dt: self.update_level_bar())
        [self.add_transaction(transaction) for transaction in App.transactions]
        App.transactions = []

    def add_transaction(self, transaction):
        self.ids.transactions.add_widget(Label(text=transaction, font_size=16, color=(1, 1, 1, 1), size_hint_y=None,
                                               height=40+transaction.count("\n")*20, halign="left", markup=True))
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

    def check_transfer(self):
        if self.transfer_amt.text != "":
            self.transfer_amt.text = self.transfer_amt.text[:12]
            if float(self.transfer_amt.text) > float(App.r_coin)*0.995:
                self.transfer_amt.text = str(round(float(App.r_coin)*0.995, 2))
            if "." in self.transfer_amt.text:
                if len(self.transfer_amt.text.split(".")[1]) > 2:
                    self.transfer_amt.text = self.transfer_amt.text[:-1]
            self.transfer_cost = str(round(float(self.transfer_amt.text)/0.995, 2))
            self.transfer_send = self.transfer_amt.text
            self.transfer_fee = str(round(float(self.transfer_cost)-float(self.transfer_amt.text), 2))
        if self.transfer_amt.text == ".":
            self.transfer_amt.text = ""
        if self.transfer_amt.text == "":
            self.transfer_cost = "0.00"
            self.transfer_send = "0.00"
            self.transfer_fee = "0.00"

    def transfer_coins(self):
        if self.transfer_amt.text in ["", "."]:
            error_popup("Below Minimum Transfer\n- Transaction amount below the 3 R minimum")
        elif len(self.transfer_uid.text) < 8:
            error_popup("Invalid Username/UID For Transfer")
        elif self.transfer_uid.text == App.uid or self.transfer_uid.text == App.uname:
            error_popup("You cannot transfer funds to yourself\n- WHY ARE YOU EVEN TRYING TO?!")
        elif float(self.transfer_amt.text) < 3:
            error_popup("Below Minimum Transfer\n- Transaction amount below the 3 R minimum")
        elif float(self.transfer_amt.text) > float(App.r_coin)*0.995:
            error_popup("Insufficient funds For Transfer")
        else:
            #App.popup_text = f"Send {self.transfer_uid.text} R to {self.transfer_send}\n" \
            #                 f"Fee: {self.transfer_fee}\nTotal Cost: {self.transfer_cost}"
            #App.popup = Factory.TransferConfirmPopup()
            #App.popup.open()
            s.send_e(f"TRF:{self.transfer_uid.text}🱫{self.transfer_amt.text}")
            if s.recv_d(1024) == "V":
                success_popup(f"Transfer of {self.transfer_amt.text} R to {self.transfer_uid.text} Successful")
                self.add_transaction(f"Sent [color=f46f0eff]{self.transfer_amt.text} R[/color] "
                                     f"to {self.transfer_uid.text}")
                App.r_coin = str(round(float(App.r_coin)-float(self.transfer_amt.text)/0.995, 2))
                if App.r_coin.endswith(".0"):
                    App.r_coin = App.r_coin[:-2]
                self.r_coins = App.r_coin+" R"
                self.transfer_uid.text = ""
                self.transfer_amt.text = ""
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
                self.ids.public_chat.add_widget(AsyncImage(source=self.public_room_inp.text, size_hint_y=None,
                                                           height=300, anim_delay=0.05))
            else:
                self.ids.public_chat.add_widget(Label(text=f"[color=#14e42bff]{App.uname[:-4]}[/color] "
                                                           f"[color=#858d8fff] {str(datetime.now())[:-7]}[/color] "
                                                           f"{self.public_room_inp.text}", font_size=16,
                                                      color=(1, 1, 1, 1), size_hint_y=None, height=40, markup=True))
            s.send_e(f"MSG:{self.public_room_inp.text}")
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
    n_pass = ObjectProperty(None)

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
                App.transactions.append(f"Spent [color=#16c2e1ff]5 D[/color] to change username to "
                                        f"[color=#14e42aff]{self.uname}[/color]")
        else:
            error_popup("Invalid Username\n- Username must be between 5 and 24 characters")

    def change_pass(self):
        if len(self.n_pass.text) < 9:
            error_popup("Password Invalid\n- Password must be at least 9 characters")
        else:
            # todo 2fa, new ipk, needs old pass
            s.send_e(f"CUP:{pass_to_key(self.n_pass.text, default_salt, 50000)}")
            if s.recv_d(1024) == "V":
                App.path = "CHANGE_PASS"
                App.sm.switch_to(NacPassword(), direction="left")
            else:
                error_popup("Incorrect Password\n- Please try again")

            #if s.recv_d(1024) == "V":
            #    success_popup(f"Password changed")


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
            color = [round(col, 5) for col in self.ids.color_picker.color]
        if self.selected_color is not None:
            App.col[self.selected_color] = color
            with self.ids[self.selected_color+"_btn"].canvas:
                Color(*color)
                RoundedRectangle(size=self.ids[self.selected_color+"_btn"].size,
                                 pos=self.ids[self.selected_color+"_btn"].pos, radius=[10])

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
                hex_color = " #"
                for rgb1 in App.col[color]:
                    hex_color += hex(int(rgb1*255))[2:].zfill(2)
                f.write(f"{color}:{hex_color}\n")

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
            App.transactions.append(f"Bought [color=f46f0eff]{amount} R gift card[/color] for [color=f46f0eff]"
                                    f"{amount} R[/color]\n Code: [color=25be42ff]{gift_code}[/color]")
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


def draw_circle(self, segments, rotation=1):
    seg = [seg*0.36 for seg in segments]
    seg.append(0)
    with self.canvas:
        seg_count = 0
        cols = [App.col['green'], App.col['red']]
        for i in range(1, len(segments)+1):
            Color(*cols[i-1], mode="rgb")
            Line(circle=[self.center[0], self.center[1]+(self.center[1]/5), 125, seg[seg_count-1]+rotation,
                         seg[seg_count]+rotation+seg[seg_count-1]], width=15, cap="none")
            seg_count += 1


def draw_triangle(self):
    with self.canvas:
        Color(*App.col["yellow"])
        Line(points=[self.center[0], self.center[1]-(self.center[1]/4), self.center[0]-10,
                     self.center[1]-(self.center[1]/4)-20, self.center[0]+10, self.center[1]-(self.center[1]/4)-20,
                     self.center[0], self.center[1]-(self.center[1]/4)], width=1.5, cap="none")


def create_draws(result, odds):
    while True:
        last = 1
        draws = []
        for i in reversed(range(1, randint(100, 200))):
            draws.append(round(last-i*0.36, 4))
            last = round(last+i*0.36, 4)
        if result == "win":
            print(500, 500+odds[0], float(str(round(last/360, 3)).split(".")[1]))
            if 500-odds[0] <= float(str(round(last/360, 3)).split(".")[1]) < 500:
                return draws
        if result == "loss":
            print(500, 500+odds[0], float(str(round(last/360, 3)).split(".")[1]))
            if 500-odds[0] > float(str(round(last/360, 3)).split(".")[1]) or \
                    500 <= float(str(round(last/360, 3)).split(".")[1]):
                return draws


class Spinner(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()
    spin_bet = ObjectProperty(None)
    game_info = ObjectProperty(None)
    game_hash = None
    spin_odds = [480, 520]
    mult = 2

    def on_pre_enter(self, *args):
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"
        if self.game_hash is None:
            s.send_e("MCF:2")
            self.game_hash = s.recv_d(1024)
            self.game_info.text = "Game - 2x"
        draw_circle(self, self.spin_odds)
        draw_triangle(self)

    def set_odds(self, mult):
        s.send_e(f"MCF:{mult}")
        for mult_btn in ["set_x2", "set_x3", "set_x5", "set_x10"]:
            self.ids[mult_btn].disabled = False
        self.ids[f"set_x{mult}"].disabled = True
        self.spin_odds = {2: [470, 530], 3: [310, 690], 5: [190, 810], 10: [105, 895]}.get(mult)
        draw_circle(self, self.spin_odds)
        self.mult = mult
        self.game_hash = s.recv_d(1024)
        self.game_info.text = f"Game - {mult}x"

    def check_bet(self):
        if self.spin_bet.text != "":
            self.spin_bet.text = self.spin_bet.text[:12]
            if float(self.spin_bet.text) > float(App.r_coin):
                self.spin_bet.text = App.r_coin
            if "." in self.spin_bet.text:
                if len(self.spin_bet.text.split(".")[1]) > 2:
                    self.spin_bet.text = self.spin_bet.text[:-1]
        if self.spin_bet.text == ".":
            self.spin_bet.text = ""

    def canvas_update(self, color):
        with self.ids.spin_col.canvas:
            Color(*color)
            RoundedRectangle(size=self.ids.spin_col.size, pos=self.ids.spin_col.pos, radius=[10])

    def spin(self):
        if self.spin_bet.text == "":
            Clock.schedule_once(lambda dt: error_popup("Below Minimum Bet\n- Bet amount below the 1 R minimum"))
        elif float(self.spin_bet.text) < 1:
            Clock.schedule_once(lambda dt: error_popup("Below Minimum Bet\n- Bet amount below the 1 R minimum"))
        elif float(self.spin_bet.text) > float(App.r_coin):
            Clock.schedule_once(lambda dt: error_popup("Insufficient funds For Transfer"))
        elif float(self.spin_bet.text) > 30:
            Clock.schedule_once(lambda dt: error_popup("Above Maximum Bet\n- Bet amount above the 30 R maximum\n"
                                                       "This limit is based on your level"))
        else:
            for mult_btn in ["set_x2", "set_x3", "set_x5", "set_x10"]:
                self.ids[mult_btn].disabled = True
            self.ids.spin_btn.disabled = True
            s.send_e(f"RCF:{self.game_hash}🱫{self.spin_bet.text}")
            seed_inp, rand_float, outcome = s.recv_d(1024).split("🱫")
            for draw in create_draws(outcome.lower(), self.spin_odds):
                Clock.schedule_once(lambda dt: draw_circle(self, self.spin_odds, draw))
                sleep(0.03)
            xp_amt = round(float(self.spin_bet.text)/5, 2)
            App.xp = str(float(App.xp)+xp_amt)
            if outcome == "WIN":
                Clock.schedule_once(lambda dt: self.canvas_update(rgb("#2F3D2Fff")))
                self.ids.spin_text.text = "You Won!"
                App.r_coin = str(round(float(App.r_coin)+float(self.spin_bet.text)*self.mult))
                App.transactions.append(f"Coinflip [color=25be42ff]won[/color][color=f46f0eff] "
                                        f"{float(self.spin_bet.text)*2} R[/color] [color=25be42ff]gained[/color] "
                                        f"[color=f2ef32ff]{xp_amt} XP[/color]")
            else:
                Clock.schedule_once(lambda dt: self.canvas_update(rgb("#3D332Fff")))
                App.transactions.append(f"Coinflip [color=fa1d04ff]lost[/color][color=f46f0eff] {self.spin_bet.text} "
                                        f"R[/color] [color=25be42ff]gained[/color] [color=f2ef32ff]{xp_amt} XP[/color]")
                self.ids.spin_text.text = "You Lost"
                App.r_coin = str(round(float(App.r_coin)-float(self.spin_bet.text)))
            if App.r_coin.endswith(".0"):
                App.r_coin = App.r_coin[:-2]
            self.r_coins = App.r_coin+" R"
            sleep(2)
            Clock.schedule_once(lambda dt: self.canvas_update(rgb("#3c3c3cff")))
            Clock.schedule_once(lambda dt: draw_circle(self, self.spin_odds))
            s.send_e(f"MCF:{self.mult}")
            self.game_hash = s.recv_d(1024)
            self.ids.spin_text.text = ""
            self.ids.spin_btn.disabled = False
            for mult_btn in ["set_x2", "set_x3", "set_x5", "set_x10"]:
                self.ids[mult_btn].disabled = False
            self.ids[f"set_x{self.mult}"].disabled = True

    def run_spinner(self):
        Thread(target=self.spin).start()
        draw_circle(self, self.spin_odds, 0)


class Reloading(Screen):
    reload_text = StringProperty()

    def on_pre_enter(self, *args):
        self.reload_text = App.reload_text


class App(KivyApp):
    def build(self):
        App.col = {"rdisc_purple": rgb("#6753fcff"), "rdisc_purple_dark": rgb("#6748a0ff"),
                   "rdisc_cyan": rgb("#25be96ff"), "rcoin_orange": rgb("#f56f0eff"), "dcoin_blue": rgb("#16c2e1ff"),
                   "link_blue": rgb("#509ae4ff"), "green": rgb("#14e42bff"), "yellow": rgb("#f3ef32ff"),
                   "orange": rgb("#f38401ff"), "red": rgb("#fb1e05ff"), "grey": rgb("#3c3c32ff"),
                   "bk_grey_1": rgb("#323232ff"), "bk_grey_2": rgb("#373737ff"), "bk_grey_3": rgb("#3c3c3cff")}
        App.theme = {"purple": App.col.copy()}
        App.theme.update({"pink": {"rdisc_purple": rgb("#ff4772ff"), "rdisc_purple_dark": rgb("#ff6d71ff"),
                                   "rdisc_cyan": rgb("#c467b2ff"), "rcoin_orange": rgb("#f56f0eff"),
                                   "dcoin_blue": rgb("#16c2e1ff"), "link_blue": rgb("#509ae4ff"),
                                   "green": rgb("#14e42bff"), "yellow": rgb("#f3ef32ff"), "orange": rgb("#f38401ff"),
                                   "red": rgb("#fb1e05ff"), "grey": rgb("#3c3c32ff"), "bk_grey_1": rgb("#323232ff"),
                                   "bk_grey_2": rgb("#373737ff"), "bk_grey_3": rgb("#3c3c3cff")}})
        App.theme.update({"green": {"rdisc_purple": rgb("#009f70ff"), "rdisc_purple_dark": rgb("#658e37ff"),
                                    "rdisc_cyan": rgb("#25be42ff"), "rcoin_orange": rgb("#f56f0eff"),
                                    "dcoin_blue": rgb("#16c2e1ff"), "link_blue": rgb("#509ae4ff"),
                                    "green": rgb("#14e42bff"), "yellow": rgb("#f3ef32ff"), "orange": rgb("#f38401ff"),
                                    "red": rgb("#fb1e05ff"), "grey": rgb("#3c3c32ff"), "bk_grey_1": rgb("#323232ff"),
                                    "bk_grey_2": rgb("#373737ff"), "bk_grey_3": rgb("#3c3c3cff")}})
        App.theme.update({"lime": {"rdisc_purple": rgb("#99bf38ff"), "rdisc_purple_dark": rgb("#998739ff"),
                                   "rdisc_cyan": rgb("#dfbb38ff"), "rcoin_orange": rgb("#f56f0eff"),
                                   "dcoin_blue": rgb("#16c2e1ff"), "link_blue": rgb("#509ae4ff"),
                                   "green": rgb("#14e42bff"), "yellow": rgb("#f3ef32ff"), "orange": rgb("#f38401ff"),
                                   "red": rgb("#fb1e05ff"), "grey": rgb("#3c3c32ff"), "bk_grey_1": rgb("#323232ff"),
                                   "bk_grey_2": rgb("#373737ff"), "bk_grey_3": rgb("#3c3c3cff")}})

        if path.exists("color_scheme.txt"):
            with open("color_scheme.txt", encoding="utf-8") as f:
                for color in f.readlines()[1:]:
                    color_name, color = color.replace("\n", "").split(": ")
                    App.col[color_name] = rgb(color)

        App.t_and_c = rdisc_kv.t_and_c()
        App.uname = None  # username
        App.transactions = []
        App.popup = None
        App.new_drive = None
        App.reload_text = ""
        App.popup_text = "Popup Error"

        # app defaults and window manager
        Builder.load_file("rdisc.kv")
        App.sm = ScreenManager()
        [App.sm.add_widget(screen) for screen in [AttemptConnection(name="AttemptConnection"),
         IpSet(name="IpSet"), LogInOrSignUp(name="LogInOrSignUp"), KeyUnlock(name="KeyUnlock"),
         CreateKey(name="CreateKey"), UsbSetup(name="UsbSetup"), ReCreateKey(name="ReCreateKey"),
         ReCreateGen(name="ReCreateGen"), Captcha(name="Captcha"), NacPassword(name="NacPassword"),
         LogUnlock(name="LogUnlock"), TwoFacSetup(name="TwoFacSetup"), TwoFacLog(name="TwoFacLog"),
         Home(name="Home"), Chat(name="Chat"), Store(name="Store"), Games(name="Games"),
         Inventory(name="Inventory"), Settings(name="Settings"), ColorSettings(name="ColorSettings"),
         GiftCards(name="GiftCards"), DataCoins(name="DataCoins"), Spinner(name="Spinner"),
         Reloading(name="Reloading")]]

        if version:
            App.title = f"Rdisc-{version}"
        elif path.exists("rdisc.py"):
            App.title = "Rdisc-Dev"
        else:
            App.title = [file for file in listdir('app') if file.endswith('.exe')][-1][:-4].replace("rdisc", "Rdisc")
        if platform in ["win", "linux"]:
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
     GiftCards(name="GiftCards"), DataCoins(name="DataCoins"), Spinner(name="Spinner")]]
    if reason == "reload":
        if current_screen == "_screen0":
            current_screen = "Home"
        App.sm.current = current_screen


if __name__ == "__main__":
    if not path.exists("resources"):
        mkdir("resources")

    if not path.exists("resources/blank_captcha.png") or not path.exists("resources/blank_qr.png"):
        rdisc_kv.w_images()

    if not path.exists("rdisc.kv"):
        rdisc_kv.kv()
    crash_num = 0
    while True:
        try:
            s = Server()
            App().run()
            break
        except Exception as e:
            if "App.stop() missing 1 required positional argument: 'self'" in str(e):
                print("Crash forced by user.")
            else:
                crash_num += 1
                print(f"Error {crash_num} caught: {e}")
            if crash_num == 5:
                print("Crash loop detected, exiting app in 3 seconds...")
                sleep(3)
                break
            else:
                reload("crash")
