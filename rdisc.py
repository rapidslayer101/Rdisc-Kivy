import enclib as enc
import rdisc_kv
from rsa import newkeys, PublicKey, decrypt
from zlib import error as zl_error
from random import randint, uniform
from time import perf_counter, sleep
from random import choices
from hashlib import sha512
from os import path, mkdir
from datetime import datetime
from threading import Thread
from socket import socket
from base64 import b32encode

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.config import Config

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
    app_hash = enc.hash_a_file("rdisc.py")
if path.exists("sha.txt"):
    with open("sha.txt", "r", encoding="utf-8") as f:
        latest_sha_, version_, tme_, bld_num_, run_num_ = f.readlines()[-1].split("§")
    print("prev", version_, tme_, bld_num_, run_num_)
    release_major, major, build, run = version_.replace("V", "").split(".")
    if latest_sha_ != app_hash:
        run = int(run) + 1
        with open("sha.txt", "a+", encoding="utf-8") as f:
            write = f"\n{app_hash}§V{release_major}.{major}.{build}.{run}" \
                    f"§TME-{str(datetime.now())[:-4].replace(' ', '_')}" \
                    f"§BLD_NM-{bld_num_[7:]}§RUN_NM-{int(run_num_[7:])+1}"
            print(f"crnt V{release_major}.{major}.{build}.{run} "
                  f"TME-{str(datetime.now())[:-4].replace(' ', '_')} "
                  f"BLD_NM-{bld_num_[7:]} RUN_NM-{int(run_num_[7:])+1}")
            f.write(write)
    print(f"Running rdisc V{release_major}.{major}.{build}.{run}")

default_salt = "52gy\"J$&)6%0}fgYfm/%ino}PbJk$w<5~j'|+R .bJcSZ.H&3z'A:gip/jtW$6A=" \
               "G-;|&&rR81!BTElChN|+\"TCM'CNJ+ws@ZQ~7[:¬`-OC8)JCTtI¬k<i#.\"H4tq)p4"


class Server:
    def __init__(self):
        self.s = socket()
        self.enc_seed = None
        self.enc_salt = None
        self.enc_key = None
        if path.exists("userdata/server_ip"):
            with open(f"userdata/server_ip", "rb") as f:
                self.ip = f.read().decode().split(":")
        else:
            self.ip = None

    def connect(self):
        try:
            self.s.connect((self.ip[0], int(self.ip[1])))
            print("Connected to server")
            l_ip, l_port = str(self.s).split("laddr=")[1].split("raddr=")[0][2:-3].split("', ")
            s_ip, s_port = str(self.s).split("raddr=")[1][2:-2].split("', ")
            print(f" << Server connected via {l_ip}:{l_port} -> {s_ip}:{s_port}")
            pub_key, pri_key = newkeys(1024)
            try:
                self.s.send(PublicKey.save_pkcs1(pub_key))
            except ConnectionResetError:
                return False
            print(" >> Public RSA key sent")
            enc_seed = decrypt(self.s.recv(128), pri_key).decode()
            enc_salt = decrypt(self.s.recv(128), pri_key).decode()
            self.enc_key = enc.pass_to_key(enc_seed, enc_salt, 100000)
            print(" << Client enc_seed and enc_salt received and loaded\n "
                  "-- RSA Enc bootstrap complete")
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


class key_system:
    def __init__(self):
        self.master_key = None
        self.uid = None
        self.secret_code = None
        self.ip_key = None
        self.pass_code = None
        self.pin_code = None
        self.screen_path = None


keys = key_system()


class logInOrSignUpScreen(Screen):
    def __init__(self, **kwargs):
        super(logInOrSignUpScreen, self).__init__(**kwargs)
        print("Loading account keys...")
        if path.exists(f'userdata\key'):
            print(f" - Found user account keys")
            with open(f'userdata\key', 'rb') as f:
                key_data = f.read()
            print(" - Key data loaded")
            if key_data.endswith(b"MAKE_KEY1"):
                print(" - MAKE KEY FROM CAPTCHA")
                keys.screen_path = "make"
                keys.master_key = str(key_data)[2:-10]
                sm.switch_to(ipSetScreen(), direction="left")  # if ip exists this should have gone to attempt screen
            else:
                if key_data.endswith(b"MAKE_KEY2"):
                    print(" - MAKE KEY FROM 2FA")
                    keys.screen_path = "make"
                    keys.master_key, keys.uid, keys.secret_code = str(key_data)[2:-10].split("\\xf0\\x9f\\xb1\\xab")
                    s.connect()
                    if s.ip:
                        sm.switch_to(twoFacSetupScreen(), direction="left")
                    else:
                        sm.switch_to(ipSetScreen(), direction="left")
                else:
                    keys.screen_path = "unlock"
                    keys.uid, keys.ip_key = str(key_data[:8])[2:-1], key_data[8:]
                    sm.switch_to(keyUnlockScreen(), direction="left")
        else:
            print(" - No keys found")


# class to accept user info and validate it
class keyUnlockScreen(Screen):
    pwd = ObjectProperty(None)
    passcode_prompt_text = StringProperty()

    def on_pre_enter(self, *args):
        self.passcode_prompt_text = f"Enter passcode for account {keys.uid}"

    def login(self):
        if self.pwd.text == "":
            print("Password blank")
        else:
            print(self.pwd.text)
            try:  # todo login
                user_pass = enc.pass_to_key(self.pwd.text, default_salt, 50000)
                user_pass = enc.to_base(96, 16, sha512((user_pass+keys.uid).encode()).hexdigest())
                print(keys.ip_key, user_pass[:40], user_pass[40:])
                enc.dec_from_pass(keys.ip_key, user_pass[:40], user_pass[40:])
                sm.switch_to(mainPageScreen(), direction="left")
            except zl_error:
                print("Invalid password")


class createKeyScreen(Screen):
    confirmation_code = ObjectProperty(None)
    confirmation_warning = ObjectProperty(None)
    pass_code_text = StringProperty()
    pin_code_text = StringProperty()
    rand_confirm_text = StringProperty()
    start_time = None
    rand_confirmation = None

    def generate_master_key(self, master_key, salt, depth_time, current_depth=0):
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
                    self.pin_code_text = f"Generating key and pin ({round(time_left, 2)}s left)"
                except ZeroDivisionError:
                    pass
        master_key = enc.to_base(96, 16, master_key.hex())
        with open("userdata/key", "w", encoding="utf-8") as f:
            f.write(f"{master_key}MAKE_KEY1")
        keys.master_key = master_key
        self.rand_confirmation = str(randint(0, 9))
        self.pin_code_text = f"Depth pin: {enc.to_base(36, 10, current_depth)}"
        self.rand_confirm_text = f"Once you have written down your account code " \
                                 f"and pin enter {self.rand_confirmation} below"

    def on_pre_enter(self, *args):
        keys.screen_path = "make"
        self.start_time = perf_counter()
        acc_key = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=int(20)))
        time_depth = uniform(3, 10)
        Thread(target=self.generate_master_key, args=(acc_key[:15].encode(),
               acc_key[15:].encode(), time_depth,), daemon=True).start()
        self.pin_code_text = f"Generating key and pin ({time_depth}s left)"
        acc_key_print = f"{acc_key[:5]}-{acc_key[5:10]}-{acc_key[10:15]}-{acc_key[15:]}"
        self.pass_code_text = f"Your account key is: {acc_key_print}"

    def continue_confirmation(self):
        if self.rand_confirmation:
            if self.confirmation_code == "":
                print("No input provided")
            else:
                if self.confirmation_code.text == self.rand_confirmation:
                    print("Confirmation code correct")
                    if s.ip:
                        sm.switch_to(attemptConnectionScreen(), direction="left")
                    else:
                        sm.switch_to(ipSetScreen(), direction="left")
                else:
                    print("Confirmation code incorrect")


class reCreateKeyScreen(Screen):
    pass_code = ObjectProperty()
    pin_code = ObjectProperty()

    def on_enter(self, *args):
        keys.screen_path = "login"

    def start_regenerator(self):
        if len(self.pass_code.text.replace("-", "")) == 20:  # todo replace with 4 separate boxes
            if self.pin_code.text != "":
                keys.pass_code, keys.pin_code = self.pass_code.text, self.pin_code.text
                sm.switch_to(reCreateGenScreen(), direction="left")


class reCreateGenScreen(Screen):
    gen_left_text = StringProperty()

    #def __init__(self, **kwargs):
    #    super(reCreateGenScreen, self).__init__(**kwargs)
    #    Clock.schedule_interval(self.check_key(), 0.2)

    def regenerate_master_key(self, master_key, salt, depth_to, current_depth=0):
        start, depth_left, loop_timer = perf_counter(), depth_to - current_depth, perf_counter()
        for depth_count in range(1, depth_left + 1):
            master_key = sha512(master_key + salt).digest()
            if perf_counter() - loop_timer > 0.25:
                try:
                    loop_timer = perf_counter()
                    real_dps = int(round(depth_count / (perf_counter() - start), 0))
                    print(f"Runtime: {round(perf_counter() - start, 2)}s  "
                          f"Time Left: {round((depth_left - depth_count) / real_dps, 2)}s  "
                          f"DPS: {round(real_dps / 1000000, 3)}M  "
                          f"Depth: {current_depth + depth_count}/{depth_to}  "
                          f"Progress: {round((current_depth + depth_count) / depth_to * 100, 3)}%")
                    self.gen_left_text = f"Generating master key ({round((depth_left-depth_count)/real_dps, 2)}s left)"
                except ZeroDivisionError:
                    pass
        keys.master_key = enc.to_base(96, 16, master_key.hex())

    def on_enter(self, *args):
        Thread(target=self.regenerate_master_key, args=(keys.pass_code[:15].encode(),
               keys.pass_code[15:].encode(), int(enc.to_base(10, 36, keys.pin_code)),), daemon=True).start()
        self.gen_left_text = f"Generating master key"
        while True:
            sleep(0.2)
            if keys.master_key:
                if s.ip:
                    sm.switch_to(attemptConnectionScreen(), direction="left")
                else:
                    sm.switch_to(ipSetScreen(), direction="left")


# todo inheritance for login / signup versions of the below screen


class ipSetScreen(Screen):
    ip_address = ObjectProperty(None)
    ip = None

    def try_connect(self):
        if self.ip_address.text == "":
            print("No input provided")
        else:
            try:
                server_ip, server_port = self.ip_address.text.split(":")
                server_port = int(server_port)
            except ValueError or NameError:
                print("\n🱫[COL-RED] Invalid input")
            else:
                if server_port < 1 or server_port > 65535:
                    print("\n🱫[COL-RED] Port number must be between 1 and 65535")
                else:
                    try:
                        ip_1, ip_2, ip_3, ip_4 = server_ip.split(".")
                    except ValueError:
                        print("\n🱫[COL-RED] IP address must be in the format 'xxx.xxx.xxx.xxx'")
                    try:
                        if all(i.isdigit() and 0 <= int(i) <= 255 for i in [ip_1, ip_2, ip_3, ip_4]):
                            s.ip = [server_ip, server_port]
                            sm.switch_to(attemptConnectionScreen(), direction="left")
                        else:
                            print("\n🱫[COL-RED] IP address must have integers between 0 and 255")
                    except NameError:
                        print("\n🱫[COL-RED] IP address must be in the form of 'xxx.xxx.xxx.xxx'")


class attemptConnectionScreen(Screen):
    def on_enter(self, *args):
        if s.connect():
            if not path.exists("userdata/server_ip"):
                with open("userdata/server_ip", "w", encoding="utf-8") as f:
                    f.write(f"{s.ip[0]}:{s.ip[1]}")
            sm.switch_to(captchaScreen(), direction="left")
        else:
            print("Failed to connect to set IP")
            sm.switch_to(ipSetScreen(), direction='right')


class captchaScreen(Screen):  # todo. redo for login captcha version
    captcha_prompt_text = StringProperty()
    captcha_input = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.captcha_prompt_text = "Waiting for captcha..."

    def on_enter(self, *args):
        print("Captcha screen")
        s.send_e("CAP")
        self.get_captcha()

    def get_captcha(self):
        image = s.recv_d(32768)  # todo remove the need for a file
        with open('captcha.jpg', 'wb') as f:
            f.write(image)
            print("new captcha")
        self.captcha_prompt_text = f"Enter the text below"
        self.ids.captcha_image.source = 'captcha.jpg'

    def try_captcha(self):
        if self.captcha_input.text == "":
            print("No input provided")
        else:
            s.send_e(self.captcha_input.text.replace(" ", "").replace("1", "I").replace("0", "O").upper())
            if s.recv_d(1024) == "V":
                sm.switch_to(nacPassword(), direction="left")
            else:
                print("Captcha failed")


class nacPassword(Screen):
    nac_password_1 = ObjectProperty(None)
    nac_password_2 = ObjectProperty(None)

    def set_nac_password(self):
        if self.nac_password_1.text == "":
            print("No input provided (1)")
        else:
            if self.nac_password_2.text == "":
                print("No input provided (2)")
            else:
                if len(self.nac_password_1.text) < 9:
                    print("Password must be at least 9 characters")
                else:
                    if self.nac_password_1.text != self.nac_password_2.text:
                        print("Passwords do not match")
                    else:
                        pass_send = enc.pass_to_key(self.nac_password_1.text, default_salt, 50000)
                        s.send_e(f"NAC:{keys.master_key}🱫{pass_send}")
                        sm.switch_to(twoFacSetupScreen(), direction="left")


class twoFacSetupScreen(Screen):
    two_fac_wait_text = StringProperty()
    two_fac_confirm = ObjectProperty(None)

    def on_pre_enter(self, *args):
        print("Two factor setup screen")
        self.two_fac_wait_text = "Waiting for 2fa QR code..."

    def on_enter(self, *args):
        if not keys.secret_code:
            keys.uid, keys.secret_code = s.recv_d(2048).split("🱫")
            with open("userdata/key", "w", encoding="utf-8") as f:
                f.write(f"{keys.master_key}🱫{keys.uid}🱫{keys.secret_code}MAKE_KEY2")
        else:
            s.send_e(f"FIP:{keys.uid}🱫{keys.master_key}")
        secret_code = b32encode(keys.secret_code.encode()).decode().replace('=', '')
        print(secret_code)
        self.ids.two_fac_qr.source = "https://chart.googleapis.com/chart?cht=qr&chs=300x300&chl=otpauth%3A%2" \
                                     f"F%2Ftotp%2F{keys.uid}%3Fsecret%3D{secret_code}%26issuer%3DRdisc"
        self.two_fac_wait_text = "Scan this QR with your authenticator, then enter code to confirm.\n" \
                                 f"Your User ID is {keys.uid}"

    def confirm_2fa(self):
        if self.two_fac_confirm.text == "":
            print("No input provided")
        else:
            self.two_fac_confirm.text = self.two_fac_confirm.text.replace(" ", "")
            if len(self.two_fac_confirm.text) == 6:
                s.send_e(self.two_fac_confirm.text.replace(" ", ""))
                ip_key = s.recv_d(1024)
                if ip_key != "N":
                    with open("userdata/key", "wb") as f:
                        f.write(keys.uid.encode()+ip_key)
                    print("2FA confirmed")
                    sm.switch_to(mainPageScreen(), direction="left")
                else:
                    print("2FA failed")
            else:
                print("Invalid input")


class mainPageScreen(Screen):
    def on_pre_enter(self, *args):
        print("Main page")
        #print("Username setting and account create finished screen")
        #self.account_finished_details_text = "Account created. Please enter a username"


# class for managing screens
class windowManager(ScreenManager):
    pass


kv = Builder.load_file("rdisc.kv")
sm = windowManager()

# adding screens
sm.add_widget(logInOrSignUpScreen(name='login_signup'))
sm.add_widget(keyUnlockScreen(name='unlock_key'))
sm.add_widget(createKeyScreen(name='create_key'))
sm.add_widget(ipSetScreen(name='ip_set'))
sm.add_widget(attemptConnectionScreen(name='attempt_connect'))
sm.add_widget(captchaScreen(name='captcha'))
sm.add_widget(nacPassword(name='new_acc_pass'))
sm.add_widget(twoFacSetupScreen(name='2fa_setup'))
sm.add_widget(reCreateKeyScreen(name='recreate_key'))
sm.add_widget(reCreateKeyScreen(name='regen_key'))
sm.add_widget(mainPageScreen(name='main_page'))


# class that builds gui
class Rdisc(App):
    def build(self):
        Window.clearcolor = (50/255, 50/255, 50/255, 1)
        Window.size = (1264, 681)
        Config.set('input', 'mouse', 'mouse,disable_multitouch')
        Config.set('kivy', 'exit_on_escape', '0')
        return sm


# driver function
if __name__ == "__main__":
    Rdisc().run()
