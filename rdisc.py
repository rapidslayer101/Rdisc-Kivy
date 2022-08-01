import enclib as enc
from rsa import newkeys, PublicKey, decrypt
from random import randint, uniform
from time import perf_counter
from random import choices
from hashlib import sha512
from os import path, mkdir, remove
from datetime import datetime
from threading import Thread
from socket import socket

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.config import Config

if not path.exists("rdisc.kv"):
    import rdisc_kv
    rdisc_kv.kv()

if path.exists("rdisc.py"):
    import rdisc_kv
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


#def regenerate_master_key(self, key_location, file_key, salt, depth_to, current_depth=0):
#    print("\n🱫[COL-GRN] Generating master key...")
#    start, depth_left, loop_timer = perf_counter(), depth_to-current_depth, perf_counter()
#    for depth_count in range(1, depth_left+1):
#        file_key = sha512(file_key+salt).digest()
#        if perf_counter() - loop_timer > 0.25:
#            try:
#                loop_timer = perf_counter()
#                real_dps = int(round(depth_count/(perf_counter()-start), 0))
#                print(f"\n Runtime: {round(perf_counter()-start, 2)}s  "
#                     f"Time Left: {round((depth_left-depth_count)/real_dps, 2)}s  "
#                     f"DPS: {round(real_dps/1000000, 3)}M  "
#                     f"Depth: {current_depth+depth_count}/{depth_to}  "
#                     f"Progress: {round((current_depth+depth_count)/depth_to * 100, 3)}%")
#                with open(f'{key_location}key', 'wb') as f:
#                    f.write(file_key + b"RGEN" + salt + b"RGEN" +
#                            str(depth_to).encode() + b"RGEN" + str(current_depth+depth_count).encode())
#            except ZeroDivisionError:
#                pass
#    with open(f"{key_location}key", "wb") as f:
#        f.write(file_key+b"MAKE_KEY")
#    return file_key

class Server:
    def __init__(self):
        self.s = socket()
        self.pub_key = None
        self.pri_key = None
        self.enc_seed = None
        self.enc_salt = None
        self.enc_key = None
        if path.exists("userdata/server_ip"):
            with open(f"userdata/server_ip", "rb") as f:
                self.ip = f.read().decode().split(":")
        else:
            self.ip = None

    def connect(self):
        if not self.pub_key:
            self.pub_key, self.pri_key = newkeys(1024)
        try:
            self.s.connect((self.ip[0], int(self.ip[1])))
            print("Connected to server")
            l_ip, l_port = str(self.s).split("laddr=")[1].split("raddr=")[0][2:-3].split("', ")
            s_ip, s_port = str(self.s).split("raddr=")[1][2:-2].split("', ")
            print(f" << Server connected via {l_ip}:{l_port} -> {s_ip}:{s_port}")
            try:
                self.s.send(PublicKey.save_pkcs1(self.pub_key))
            except ConnectionResetError:
                return False
            print(" >> Public RSA key sent")
            enc_seed = decrypt(self.s.recv(128), self.pri_key).decode()
            enc_salt = decrypt(self.s.recv(128), self.pri_key).decode()
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


class logInOrSignUpScreen(Screen):
    def on_enter(self, *args):
        print("Loading account keys...")
        key_location = None
        if path.exists(f'userdata\key'):
            print(f" - Found user account keys")
            with open(f'userdata\key', 'rb') as f:
                key_data = f.read()
            print(" - Key data loaded")
            if len(key_data.split(b"NGEN")) == 4 or len(key_data.split(b"RGEN")) == 4:
                print("Detected incomplete generation key, deleting...")
                remove(f'userdata\key')
        if path.exists(f'userdata\key'):
            if key_data.endswith(b"MAKE_KEY"):
                print(" - MAKE KEY")
                #file_key = key_data.replace(b"MAKE_KEY", b"")
                if s.ip:  # todo: get rid of weird problem where server connects twice if going via MAKE_KEY route
                    sm.switch_to(attemptConnection(), direction="left")
                    #pass
                else:
                    sm.switch_to(ipSetScreen(), direction="left")
            else:
                if path.exists(f'{key_location}key_salt'):
                    with open(f'{key_location}key_salt', encoding="utf-8") as f:
                        key_salt, uid = f.read().split("🱫")
                    print(" - Key salt loaded\n - User id loaded")
                else:
                    print("Activation key required")
                    sm.switch_to(keyUnlockScreen(), direction="left")
        else:
            print(" - No keys found")


# class to accept user info and validate it
class keyUnlockScreen(Screen):
    pwd = ObjectProperty(None)

    def validate(self):
        print("Validating user info")
        if self.pwd.text:
            print(self.pwd.text)
        else:
            sm.current = 'logdata'
            self.pwd.text = ""


class createKeyScreen(Screen):
    confirmation_code = ObjectProperty(None)
    confirmation_warning = ObjectProperty(None)
    pass_code_text = StringProperty()
    pin_code_text = StringProperty()
    rand_confirm_text = StringProperty()
    start_time = None
    rand_confirmation = None

    def generate_master_key(self, file_key, salt, depth_time, current_depth=0):
        start, time_left, loop_timer = perf_counter(), depth_time, perf_counter()
        if not path.exists("userdata"):
            mkdir("userdata")
        while time_left > 0:
            current_depth += 1
            file_key = sha512(file_key+salt).digest()
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
                    with open(f'userdata/key', 'wb') as f:
                        f.write(file_key + b"NGEN" + salt + b"NGEN" +
                                str(time_left).encode() + b"NGEN" + str(current_depth).encode())
                    self.pin_code_text = f"Generating keys ({round(time_left, 2)}s left)"
                except ZeroDivisionError:
                    pass
        with open(f"userdata/key", "wb") as f:
            f.write(file_key + b"MAKE_KEY")
        self.rand_confirmation = str(randint(0, 9))
        self.pin_code_text = f"Your account pin is: {current_depth}"
        self.rand_confirm_text = f"Once you have written down your account code " \
                                 f"and pin enter {self.rand_confirmation} below"

    def on_pre_enter(self, *args):
        self.start_time = perf_counter()
        pass_code = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=int(25)))
        time_depth = uniform(3, 10)  # time_depth
        Thread(target=self.generate_master_key, args=(pass_code[:15].encode(),
               pass_code[15:].encode(), time_depth,), daemon=True).start()
        self.pin_code_text = f"Generating key and pin ({time_depth}s left)"
        pass_code_print = f"{pass_code[:5]}-{pass_code[5:10]}-{pass_code[10:15]}-{pass_code[15:20]}-{pass_code[20:]}"
        self.pass_code_text = f"Your account code is: {pass_code_print}"

    def continue_confirmation(self):
        if self.rand_confirmation:
            if self.confirmation_code == "":
                print("No input provided")
            else:
                if self.confirmation_code.text == self.rand_confirmation:
                    print("Confirmation code correct")
                    if s.ip:
                        sm.switch_to(attemptConnection(), direction="left")
                    else:
                        sm.switch_to(ipSetScreen(), direction="left")
                else:
                    print("Confirmation code incorrect")


class reCreateKeyScreen(Screen):
    pass_code_text = StringProperty()
    pin_code_text = StringProperty()
    rand_confirm_text = StringProperty()
    start_time = None
    rand_confirmation = None

    def generate_master_key(self, file_key, salt, depth_time, current_depth=0):
        start, time_left, loop_timer = perf_counter(), depth_time, perf_counter()
        if not path.exists("userdata"):
            mkdir("userdata")
        while time_left > 0:
            current_depth += 1
            file_key = sha512(file_key+salt).digest()
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
                    with open(f'userdata/key', 'wb') as f:
                        f.write(file_key + b"NGEN" + salt + b"NGEN" +
                                str(time_left).encode() + b"NGEN" + str(current_depth).encode())
                    self.pin_code_text = f"Generating key and pin ({round(time_left, 2)}s left)"
                except ZeroDivisionError:
                    pass
        with open(f"userdata/key", "wb") as f:
            f.write(file_key + b"MAKE_KEY")
        self.rand_confirmation = str(randint(0, 9))
        self.pin_code_text = f"Depth pin: {current_depth}"
        self.rand_confirm_text = f"Once you have written down your account code " \
                                 f"and pin enter {self.rand_confirmation} below"

    def on_pre_enter(self, *args):
        self.start_time = perf_counter()
        pass_code = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=int(25)))
        time_depth = uniform(3, 10)  # time_depth
        Thread(target=self.generate_master_key, args=(pass_code[:15].encode(),
               pass_code[15:].encode(), time_depth,), daemon=True).start()
        self.pin_code_text = f"Generating key and pin ({time_depth}s left)"
        pass_code_print = f"{pass_code[:5]}-{pass_code[5:10]}-{pass_code[10:15]}-{pass_code[15:20]}-{pass_code[20:]}"
        self.pass_code_text = f"Your account code is: {pass_code_print}"

    def continue_confirmation(self):
        if self.rand_confirmation:
            if self.confirmation_code == "":
                print("No input provided")
            else:
                if self.confirmation_code.text == self.rand_confirmation:
                    print("Confirmation code correct")
                    if s.ip:
                        sm.switch_to(attemptConnection(), direction="left")
                    else:
                        sm.switch_to(ipSetScreen(), direction="left")
                else:
                    print("Confirmation code incorrect")


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
                            sm.switch_to(attemptConnection(), direction="left")
                        else:
                            print("\n🱫[COL-RED] IP address must have integers between 0 and 255")
                    except NameError:
                        print("\n🱫[COL-RED] IP address must be in the form of 'xxx.xxx.xxx.xxx'")


class attemptConnection(Screen):
    def on_enter(self, *args):
        if s.connect():
            if not path.exists("userdata/server_ip"):
                with open(f"userdata/server_ip", "w", encoding="utf-8") as f:
                    f.write(f"{s.ip[0]}:{s.ip[1]}")
            sm.switch_to(captcha(), direction="left")
        else:
            print("Failed to connect to set IP")
            sm.switch_to(ipSetScreen(), direction='right')


class captcha(Screen):
    captcha_prompt_text = StringProperty()
    captcha_input = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.captcha_prompt_text = "Waiting for captcha..."

    def on_enter(self, *args):
        print("Captcha screen")
        self.get_captcha()

    def get_captcha(self):
        s.send_e("CAP")
        image = s.recv_d(32768)  # todo remove the need for a file
        with open('captcha.jpg', 'wb') as f:
            f.write(image)
        self.captcha_prompt_text = f"Enter the text below"
        self.ids.captcha_image.source = 'captcha.jpg'

    def try_captcha(self):
        if self.captcha_input.text == "":
            print("No input provided")
        else:
            print(self.captcha_input.text)


class loginScreen(Screen):
    name2 = ObjectProperty(None)
    email = ObjectProperty(None)
    pwd = ObjectProperty(None)

    def signupbtn(self):
        print("null")


class logDataScreen(Screen):
    pass


# class for managing screens
class windowManager(ScreenManager):
    pass


kv = Builder.load_file("rdisc.kv")
sm = windowManager()

# adding screens
sm.add_widget(logInOrSignUpScreen(name='login_signup'))
sm.add_widget(keyUnlockScreen(name='unlock_key'))
sm.add_widget(createKeyScreen(name='create_key'))
sm.add_widget(reCreateKeyScreen(name='recreate_key'))
sm.add_widget(ipSetScreen(name='ip_set'))
sm.add_widget(attemptConnection(name='attempt_connect'))
sm.add_widget(captcha(name='captcha'))
sm.add_widget(loginScreen(name='login'))
sm.add_widget(logDataScreen(name='logdata'))


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