import enclib as enc
import rdisc_kv
from rsa import newkeys, PublicKey, decrypt
from time import sleep
from sys import platform
from zlib import error as zl_error
from random import randint, uniform
from time import perf_counter
from random import choices
from hashlib import sha512
from os import path, mkdir, listdir
from datetime import datetime
from threading import Thread
from socket import socket
from base64 import b32encode

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty

if not path.exists("resources"):
    mkdir("resources")

if not path.exists("resources/blank_captcha.png") or not path.exists("resources/blank_qr.png"):
    rdisc_kv.w_images()

if not path.exists("rdisc.kv"):
    rdisc_kv.kv()

if path.exists("rdisc.py"):
    rdisc_kv.kv()

if path.exists("rdisc.exe"):
    app_hash = enc.hash_a_file("rdisc.exe")
else:
    if path.exists("rdisc.py"):
        app_hash = enc.hash_a_file("rdisc.py")
    else:
        app_hash = f"Unknown distro: {platform}"

version_ = None
if path.exists("sha.txt"):
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
            print("CONNECTION_LOST")  # todo deal with this

    def recv_d(self, buf_lim):
        try:
            return enc.dec_from_key(self.s.recv(buf_lim), self.enc_key)
        except ConnectionResetError:
            print("CONNECTION_LOST")  # todo deal with this


s = Server()


class ErrorPopup(Popup):
    pass


def connect_system():
    if s.ip and s.connect():
        print("Loading account keys...")
        if path.exists(f'userdata/key'):
            with open(f'userdata/key', 'rb') as f:
                key_data = f.read()
            print(" - Key data loaded")
            App.uid, App.ipk = str(key_data[:8])[2:-1], key_data[8:]
            sm.switch_to(KeyUnlock(), direction="left")
        else:
            print(" - No keys found")
            sm.switch_to(LogInOrSignUp(), direction="left")
    else:
        sm.switch_to(IpSet(), direction="left")


class AttemptConnection(Screen):
    def __init__(self, **kwargs):
        super(AttemptConnection, self).__init__(**kwargs)
        Clock.schedule_once(lambda dt: connect_system(), 1)  # todo make this retry


class IpSet(Screen):
    ip_address = ObjectProperty(None)

    def try_connect(self):
        if self.ip_address.text == "":
            App.error_reason = "IP Blank\n- Type an IP into the IP box"
            ErrorPopup().open()
        else:
            try:
                server_ip, server_port = self.ip_address.text.split(":")
                server_port = int(server_port)
            except ValueError or NameError:
                App.error_reason = "Invalid IP address\n- Please type a valid IP"
                ErrorPopup().open()
            else:
                if server_port < 1 or server_port > 65535:
                    App.error_reason = "IP Port Invalid\n- Port must be between 1 and 65535"
                    ErrorPopup().open()
                else:
                    try:
                        ip_1, ip_2, ip_3, ip_4 = server_ip.split(".")
                        if all(i.isdigit() and 0 <= int(i) <= 255 for i in [ip_1, ip_2, ip_3, ip_4]):
                            s.ip = [server_ip, server_port]
                            sm.switch_to(AttemptConnection(), direction="left")
                        else:
                            App.error_reason = "IP Address Invalid\n- Address must have integers between 0 and 255"
                            ErrorPopup().open()
                    except ValueError or NameError:
                        App.error_reason = "IP Address Invalid\n- Address must be in the format 'xxx.xxx.xxx.xxx"
                        ErrorPopup().open()


class LogInOrSignUp(Screen):
    pass


class KeyUnlock(Screen):
    pwd = ObjectProperty(None)
    passcode_prompt_text = StringProperty()
    counter = 0

    def on_pre_enter(self, *args):
        self.passcode_prompt_text = f"Enter passcode for account {App.uid}"

    def login(self):
        if self.pwd.text == "":
            self.counter += 1
            if self.counter != 3:
                App.error_reason = "Password Blank\n- Top tip, type something in the password box."
                ErrorPopup().open()
            else:
                App.error_reason = "Password Blank\n- WHY IS THE BOX BLANK?"
                ErrorPopup().open()
        else:
            try:
                user_pass = enc.pass_to_key(self.pwd.text, default_salt, 50000)
                user_pass = enc.pass_to_key(user_pass, App.uid)
                ipk = enc.dec_from_pass(App.ipk, user_pass[:40], user_pass[40:])
                s.send_e(f"ULK:{App.uid}🱫{ipk}")
                ulk_resp = s.recv_d(128)
                if ulk_resp == "SESH_T":
                    App.error_reason = "This accounts session is taken."
                    ErrorPopup().open()
                else:
                    if ulk_resp == "N":
                        App.error_reason = "Incorrect Password\n- Not exactly sure how you managed to trigger this one."
                        ErrorPopup().open()
                    else:
                        App.uname, App.xp, App.r_coin, App.d_coin = ulk_resp.split("🱫")
                        sm.switch_to(Home(), direction="left")
            except zl_error:
                App.error_reason = "Incorrect Password"
                ErrorPopup().open()


class CreateKey(Screen):
    confirmation_code = ObjectProperty(None)
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
        App.master_key = enc.to_base(96, 16, master_key.hex())
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

    def continue_confirmation(self):
        if self.rand_confirmation:
            if self.confirmation_code == "":
                App.error_reason = "Confirmation Empty"
                ErrorPopup().open()
            elif self.confirmation_code.text == self.rand_confirmation:
                if platform in ["win32", "linux"]:
                    sm.switch_to(UsbSetup(), direction="left")
                else:
                    sm.switch_to(Captcha(), direction="left")
            else:
                App.error_reason = "Incorrect Confirmation Number"
                ErrorPopup().open()


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
        with open(self.drive+"mkey1", "r", encoding="utf-8") as f:
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
            App.path = "login"
            App.uid, App.pass_code, App.pin_code = self.name_or_uid.text, self.pass_code.text, self.pin_code.text
            sm.switch_to(ReCreateGen(), direction="left")
        if 8 < len(self.name_or_uid.text) < 29 and "#" in self.name_or_uid.text and \
                len(self.pass_code.text) == 15 and self.pin_code.text:
            App.path = "login"
            App.uname, App.pass_code, App.pin_code = self.name_or_uid.text, self.pass_code.text, self.pin_code.text
            sm.switch_to(ReCreateGen(), direction="left")


def switch_to_captcha():
    sm.switch_to(Captcha(), direction="left")


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
                    self.gen_left_text = f"Generating master key ({round((depth_left-depth_count)/real_dps, 2)}s left)"
                except ZeroDivisionError:
                    pass
        App.master_key = enc.to_base(96, 16, master_key.hex())
        Clock.schedule_once(lambda dt: switch_to_captcha())

    def on_enter(self, *args):
        self.gen_left_text = f"Generating master key"
        Thread(target=self.regenerate_master_key, args=(App.pass_code[:6].encode(),
               App.pass_code[6:].encode(), int(enc.to_base(10, 36, App.pin_code)),), daemon=True).start()


class Captcha(Screen):
    captcha_prompt_text = StringProperty()
    captcha_input = ObjectProperty(None)

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
        if len(self.captcha_input.text) == 10:
            s.send_e(self.captcha_input.text.replace(" ", "").replace("1", "I").replace("0", "O").upper())
            if s.recv_d(1024) == "V":
                if App.path == "make":
                    sm.switch_to(NacPassword(), direction="left")
                if App.path == "login":
                    if App.uname:
                        s.send_e(f"LOG:{App.master_key}🱫u🱫{App.uname}")
                    else:
                        s.send_e(f"LOG:{App.master_key}🱫i🱫{App.uid}")
                    log_resp = s.recv_d(1024)
                    if log_resp == "IMK":
                        App.error_reason = "Invalid Master Key"
                        ErrorPopup().open()
                    elif log_resp == "NU":
                        App.error_reason = "Username/UID does not exist"
                        ErrorPopup().open()
                        sm.switch_to(ReCreateKey(), direction="right")
                    else:
                        App.ipk = log_resp
                        if App.uname:
                            App.uid = s.recv_d(1024)
                        sm.switch_to(LogUnlock(), direction="left")
            else:
                App.error_reason = "Captcha Failed"
                ErrorPopup().open()


class NacPassword(Screen):
    nac_password_1 = ObjectProperty(None)
    nac_password_2 = ObjectProperty(None)

    def set_nac_password(self):
        if self.nac_password_1.text == "":
            App.error_reason = "Password 1 Blank"
            ErrorPopup().open()
        elif self.nac_password_2.text == "":
            App.error_reason = "Password 2 Blank"
            ErrorPopup().open()
        elif len(self.nac_password_1.text) < 9:
            App.error_reason = "Password Invalid\n- Password must be at least 9 characters"
            ErrorPopup().open()
        elif self.nac_password_1.text != self.nac_password_2.text:
            App.error_reason = "Password Mismatch\n- Password must be the same"
            ErrorPopup().open()
        else:
            pass_send = enc.pass_to_key(self.nac_password_1.text, default_salt, 50000)
            s.send_e(f"NAC:{App.master_key}🱫{pass_send}")
            sm.switch_to(TwoFacSetup(), direction="left")


class LogUnlock(Screen):
    pwd = ObjectProperty(None)
    passcode_prompt_text = StringProperty()

    def on_pre_enter(self, *args):
        self.passcode_prompt_text = f"Enter passcode for account {App.uid}"

    def login(self):
        if self.pwd.text == "":
            App.error_reason = "Password Blank\n- The question is, why is it blank?"
            ErrorPopup().open()
        else:
            try:
                user_pass = enc.pass_to_key(self.pwd.text, default_salt, 50000)
                user_pass = enc.pass_to_key(user_pass, App.uid)
                ipk = enc.dec_from_pass(App.ipk, user_pass[:40], user_pass[40:])
                s.send_e(ipk)
                if s.recv_d(1024) == "V":
                    sm.switch_to(TwoFacLog(), direction="left")
                else:
                    App.error_reason = "Incorrect Password\n- Not exactly sure how you managed to trigger this one."
                    ErrorPopup().open()
            except zl_error:
                App.error_reason = "Incorrect Password"
                ErrorPopup().open()


class TwoFacSetup(Screen):
    two_fac_wait_text = StringProperty()
    two_fac_confirm = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.two_fac_wait_text = "Waiting for 2fa QR code..."

    def on_enter(self, *args):
        App.uid, App.secret_code = s.recv_d(1024).split("🱫")
        secret_code = b32encode(App.secret_code.encode()).decode().replace('=', '')
        print(secret_code)  # todo mention in UI text
        self.ids.two_fac_qr.source = "https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=otpauth%3A%2" \
                                     f"F%2Ftotp%2F{App.uid}%3Fsecret%3D{secret_code}%26issuer%3DRdisc"
        self.two_fac_wait_text = "Scan this QR with your authenticator, then enter code to confirm.\n" \
                                 f"Your User ID (UID) is {App.uid}"

    def confirm_2fa(self):
        if self.two_fac_confirm.text == "":
            App.error_reason = "2FA Code Blank\n- Please enter a 2FA code"
            ErrorPopup().open()
        else:
            self.two_fac_confirm.text = self.two_fac_confirm.text.replace(" ", "")
            if len(self.two_fac_confirm.text) == 6:
                s.send_e(self.two_fac_confirm.text.replace(" ", ""))
                ipk = s.recv_d(1024)
                if ipk != "N":
                    with open("userdata/key", "wb") as f:
                        f.write(App.uid.encode()+ipk)
                    App.uname, App.xp, App.r_coin, App.d_coin = s.recv_d(1024).split("🱫")
                    if App.new_drive:
                        mkey_file_num = 1
                        for file in listdir(App.new_drive):
                            if file.startswith("mkey"):
                                try:
                                    if int(file[4:]) >= mkey_file_num:
                                        mkey_file_num = int(file[4:]) + 1
                                except ValueError:
                                    pass
                        with open(f"{App.new_drive}mkey{mkey_file_num}", "w", encoding="utf-8") as f:
                            f.write(f"{App.uid}🱫{App.acc_key}🱫{App.pin_code}")
                    sm.switch_to(Home(), direction="left")
                else:
                    App.error_reason = "2FA Failed\n- Please Try Again"
                    ErrorPopup().open()
            else:
                App.error_reason = "Invalid 2FA Code"
                ErrorPopup().open()


class TwoFacLog(Screen):
    two_fac_confirm = ObjectProperty(None)

    def confirm_2fa(self):
        if self.two_fac_confirm.text == "":
            App.error_reason = "2FA Code Blank\n- Please enter a 2FA code"
            ErrorPopup().open()
        else:
            self.two_fac_confirm.text = self.two_fac_confirm.text.replace(" ", "")
            if len(self.two_fac_confirm.text) == 6:
                s.send_e(self.two_fac_confirm.text.replace(" ", ""))
                two_fa_valid = s.recv_d(1024)
                if two_fa_valid != "N":
                    with open("userdata/key", "wb") as f:
                        f.write(App.uid.encode()+App.ipk)
                    App.uname, App.xp, App.r_coin, App.d_coin = two_fa_valid.split("🱫")
                    sm.switch_to(Home(), direction="left")
                else:
                    App.error_reason = "2FA Failed\n- Please Try Again"
                    ErrorPopup().open()
            else:
                App.error_reason = "Invalid 2FA Code"
                ErrorPopup().open()


class InvalidCodePopup(Popup):
    pass


class ClaimCodePopup(Popup):
    pass


class Home(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()
    welcome_text = StringProperty()
    transfer_uid = ObjectProperty(None)
    transfer_amount = ObjectProperty(None)
    transfer_cost = StringProperty()
    transfer_send = StringProperty()
    transfer_fee = StringProperty()
    transfer_direction = "R"
    direction_text = StringProperty()
    amount_convert = ObjectProperty(None)
    coin_conversion = StringProperty()
    code = ObjectProperty(None)

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"
        self.welcome_text = f"Welcome back {App.uname}"
        self.transfer_cost = "0.00"
        self.transfer_send = "0.00"
        self.transfer_fee = "0.00"
        self.coin_conversion = "0.00 R"
        self.direction_text = "Conversion Calculator (£->R)"

    def check_transfer(self):
        if self.transfer_amount.text not in ["", "."]:
            self.transfer_amount.text = self.transfer_amount.text[:12]
            if float(self.transfer_amount.text) > float(App.r_coin)*0.995:
                self.transfer_amount.text = str(float(App.r_coin)*0.995)
            if "." in self.transfer_amount.text:
                if len(self.transfer_amount.text.split(".")[1]) > 2:
                    self.transfer_amount.text = self.transfer_amount.text[:-1]
            self.transfer_cost = str(round(float(self.transfer_amount.text)/0.995, 2))
            self.transfer_send = self.transfer_amount.text
            self.transfer_fee = str(round(float(self.transfer_cost)-float(self.transfer_amount.text), 2))
        if self.transfer_amount.text == ".":
            self.transfer_amount.text = ""
        if self.transfer_amount.text == "":
            self.transfer_cost = "0.00"
            self.transfer_send = "0.00"
            self.transfer_fee = "0.00"

    def transfer_coins(self):
        if len(self.transfer_uid.text) > 7:
            if self.transfer_uid.text != App.uid:
                if float(self.transfer_amount.text) >= 3:
                    if float(self.transfer_amount.text) <= float(App.r_coin)*0.995:
                        s.send_e(f"TRF:{self.transfer_uid.text}🱫{self.transfer_amount.text}")
                        if s.recv_d(1024) == "V":
                            print("Transfer successful")  # todo green popup
                            App.r_coin = str(round(float(App.r_coin)-float(self.transfer_amount.text)/0.995, 2))
                            if App.r_coin.endswith(".0"):
                                App.r_coin = App.r_coin[:-2]
                            self.r_coins = App.r_coin+" R"
                            self.transfer_uid.text = ""
                            self.transfer_amount.text = ""
                        else:
                            App.error_reason = "Invalid Username/UID For Transfer"
                            ErrorPopup().open()
                    else:
                        App.error_reason = "Insufficient funds For Transfer"
                        ErrorPopup().open()
                else:
                    App.error_reason = "Below Minimum Transfer\n- Transaction amount below the 3 R minimum"
                    ErrorPopup().open()
            else:
                App.error_reason = "You cannot transfer funds to yourself\n- WHY ARE YOU EVEN TRYING TO?!"
                ErrorPopup().open()
        else:
            App.error_reason = "Invalid Username/UID For Transfer"
            ErrorPopup().open()

    def check_code(self):
        if len(self.code.text) == 19:
            if self.code.text[4] == "-" and self.code.text[9] == "-" and self.code.text[14] == "-":
                s.send_e(f"CLM:{self.code.text}")
                if s.recv_d(1024) != "N":
                    App.claim_result = "Code is for xxx"
                    ClaimCodePopup().open()
                else:
                    App.error_reason = "Invalid Code"
                    ErrorPopup().open()
            else:
                App.error_reason = "Invalid Code\n- Does not match format xxxx-xxxx-xxxx-xxxx"
                ErrorPopup().open()
        else:
            App.error_reason = "Invalid Code\n- Does not match format xxxx-xxxx-xxxx-xxxx"
            ErrorPopup().open()

    def convert_coins(self):
        if self.amount_convert.text not in ["", "."]:
            self.amount_convert.text = self.amount_convert.text[:7]
            if "." in self.amount_convert.text:
                if len(self.amount_convert.text.split(".")[1]) > 2:
                    self.amount_convert.text = self.amount_convert.text[:-1]
            if self.transfer_direction == "R":
                amount_converted = str(float(self.amount_convert.text)/0.06)
            else:
                amount_converted = str(float(self.amount_convert.text)*0.0585)
            if "." in amount_converted:
                amount_converted = amount_converted[:amount_converted.index(".")+3]
            if self.transfer_direction == "R":
                self.coin_conversion = f"{amount_converted} R"
            else:
                self.coin_conversion = f"£{amount_converted}"
        else:
            if self.amount_convert.text == "":
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

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"


class Store(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"


class Games(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"


class Inventory(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"


class Settings(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()
    uname = StringProperty()
    uid = StringProperty()
    uname_to = ObjectProperty(None)

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"
        self.uname = App.uname
        self.uid = App.uid

    def change_name(self):
        if float(App.d_coin) > 4:
            if 4 < len(self.uname_to.text) < 25:
                s.send_e(f"CUN:{self.uname_to.text}")
                new_uname = s.recv_d(1024)
                if new_uname != "N":
                    App.uname = new_uname
                    self.uname = App.uname
                    App.d_coin = str(float(App.d_coin)-5)
                    if App.d_coin.endswith(".0"):
                        App.d_coin = App.d_coin[:-2]
                    self.d_coins = App.d_coin+" D"
                    print("Username changed")  # todo green popup
            else:
                App.error_reason = "Invalid Username\n- Username must be between 5 and 24 characters"
                ErrorPopup().open()
        else:
            App.error_reason = "Insufficient Funds\n- You require 5 D to change your username"
            ErrorPopup().open()


class GiftCards(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"


class Coinflip(Screen):
    r_coins = StringProperty()
    d_coins = StringProperty()

    def on_pre_enter(self, *args):
        if App.r_coin.endswith(".0"):
            App.r_coin = App.r_coin[:-2]
        if App.d_coin.endswith(".0"):
            App.d_coin = App.d_coin[:-2]
        self.r_coins = App.r_coin+" R"
        self.d_coins = App.d_coin+" D"
        # request coinflip data


class WindowManager(ScreenManager):
    pass


Builder.load_file("rdisc.kv")
sm = WindowManager()
[sm.add_widget(screen) for screen in [AttemptConnection(name="AttemptConnection"), IpSet(name="IpSet"),
 LogInOrSignUp(name="LogInOrSignUp"), KeyUnlock(name="KeyUnlock"), CreateKey(name="CreateKey"),
 UsbSetup(name="UsbSetup"), ReCreateKey(name="ReCreateKey"), ReCreateGen(name="ReCreateGen"), Captcha(name="Captcha"),
 NacPassword(name="NacPassword"), LogUnlock(name="LogUnlock"), TwoFacSetup(name="TwoFacSetup"),
 TwoFacLog(name="TwoFacLog"), Home(name="Home"), Chat(name="Chat"), Store(name="Store"), Games(name="Games"),
 Inventory(name="Inventory"), Settings(name="Settings"), GiftCards(name="GiftCards"), Coinflip(name="Coinflip")]]


class App(App):
    def build(self):
        # app defaults
        App.t_and_c = rdisc_kv.t_and_c()
        App.master_key = None
        App.uid = None  # user id
        App.uname = None  # username
        App.secret_code = None
        App.ipk = None  # ip key
        App.pass_code = None
        App.pin_code = None
        App.acc_key = None
        App.path = None  # Make or Login
        App.xp = None

        if version_:
            App.title = f"Rdisc-{version_}"
        elif path.exists("rdisc.py"):
            App.title = "Rdisc-Dev"
        else:
            App.title = [file for file in listdir('app') if
                         file.endswith('.exe')][-1][:-4].replace("rdisc", "Rdisc")
        if platform in ["win32", "linux"]:
            Window.size = (1264, 681)
        Config.set('input', 'mouse', 'mouse,disable_multitouch')
        Config.set('kivy', 'exit_on_escape', '0')
        return sm


if __name__ == "__main__":
    App().run()
