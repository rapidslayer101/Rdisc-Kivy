from random import randint, uniform
from time import perf_counter
from random import choices
from hashlib import sha512
import enclib as enc
from os import path, mkdir, remove
from datetime import datetime
from threading import Thread

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.config import Config


# todo stop all screens from starting at startup


hashed = enc.hash_a_file("rdisc.py")
if path.exists("sha.txt"):
    with open("sha.txt", "r", encoding="utf-8") as f:
        latest_sha_, version_, tme_, run_num_ = f.readlines()[-1].split("§")
    print(f"Previous {version_} {tme_} {run_num_}")
    print(version_)
    release_major, major, run = version_.replace("V", "").split(".")
    if latest_sha_ != hashed:
        run = int(run) + 1
        with open("sha.txt", "a+", encoding="utf-8") as f:
            write = f"\n{hashed}§V{release_major}.{major}.{run}" \
                    f"§TME-{str(datetime.now())[:-4].replace(' ', '_')}" \
                    f"§RUN_NM-{int(run_num_[7:]) + 1}"
            print(f"Current V{release_major}.{major}.{run} "
                  f"TME-{str(datetime.now())[:-4].replace(' ', '_')} "
                  f"RUN_NM-{int(run_num_[7:]) + 1}")
            f.write(write)
    print(f"Running rdisc V{release_major}.{major}.{run}")


def regenerate_master_key(self, key_location, file_key, salt, depth_to, current_depth=0):
    to_c("\n🱫[COL-GRN] Generating master key...")
    start, depth_left, loop_timer = perf_counter(), depth_to-current_depth, perf_counter()
    for depth_count in range(1, depth_left+1):
        file_key = sha512(file_key+salt).digest()
        if perf_counter() - loop_timer > 0.25:
            try:
                loop_timer = perf_counter()
                real_dps = int(round(depth_count/(perf_counter()-start), 0))
                to_c(f"\n Runtime: {round(perf_counter()-start, 2)}s  "
                     f"Time Left: {round((depth_left-depth_count)/real_dps, 2)}s  "
                     f"DPS: {round(real_dps/1000000, 3)}M  "
                     f"Depth: {current_depth+depth_count}/{depth_to}  "
                     f"Progress: {round((current_depth+depth_count)/depth_to * 100, 3)}%")
                with open(f'{key_location}key', 'wb') as f:
                    f.write(file_key + b"RGEN" + salt + b"RGEN" +
                            str(depth_to).encode() + b"RGEN" + str(current_depth+depth_count).encode())
            except ZeroDivisionError:
                pass
    with open(f"{key_location}key", "wb") as f:
        f.write(file_key+b"MAKE_KEY")
    return file_key


class logInOrSignUpScreen(Screen):
    def __init__(self, **kwargs):
        super(logInOrSignUpScreen, self).__init__(**kwargs)
        print("Loading account keys...")
        key_location = None
        if path.exists(f'userdata\key'):
            print(f" - Found user account keys")
            with open(f'userdata\key', 'rb') as f:
                key_data = f.read()
            print(" - Key data loaded")
            if len(key_data.split(b"NGEN")) == 4:
                print(" - Detected old generation key, resuming...")
                key_data = key_data.split(b"NGEN")
                file_key = generate_master_key(key_location, key_data[0], key_data[1],
                                               float(key_data[2]), int(key_data[3]))
                input()
            if len(key_data.split(b"RGEN")) == 4:
                print(" - Detected old regeneration key, resuming...")
                key_data = key_data.split(b"RGEN")
                file_key = regenerate_master_key(key_location, key_data[0], key_data[1],
                                                 int(key_data[2]), int(key_data[3]))
                input()
            if key_data.endswith(b"MAKE_KEY"):
                print(" - MAKE KEY")
                file_key = key_data.replace(b"MAKE_KEY", b"")
                return None
                input()
            else:
                if path.exists(f'{key_location}key_salt'):
                    with open(f'{key_location}key_salt', encoding="utf-8") as f:
                        key_salt, uid = f.read().split("🱫")
                    print(" - Key salt loaded\n - User id loaded")
                else:
                    print("Activation key required")
                    sm.switch_to(keyUnlockScreen())
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
            # switching the current screen to display validation result
            sm.current = 'logdata'
            # reset TextInput widget
            self.pwd.text = ""


class signUpScreen1(Screen):
    gen_progress_bar = ObjectProperty()
    confirmation_code = ObjectProperty(None)
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
                    print(f"\n Runtime: {round(perf_counter()-start, 2)}s  "
                          f"Time Left: {round(time_left, 2)}s  "
                          f"DPS: {round(real_dps/1000000, 3)}M  "
                          f"Depth: {current_depth}/{round(real_dps * time_left, 2)}  "
                          f"Progress: {round((depth_time-time_left)/depth_time*100, 3)}%")
                    with open(f'userdata/key', 'wb') as f:
                        f.write(file_key + b"NGEN" + salt + b"NGEN" +
                                str(time_left).encode() + b"NGEN" + str(current_depth).encode())
                    self.gen_progress_bar.value = (depth_time-time_left)/depth_time
                    self.pin_code_text = f"Generating key and pin ({round(time_left, 2)}s left)"
                except ZeroDivisionError:
                    pass
        with open(f"userdata/key", "wb") as f:
            f.write(file_key + b"MAKE_KEY")
        self.rand_confirmation = str(randint(0, 9))
        self.pin_code_text = f"Depth pin: {current_depth}"
        self.rand_confirm_text = f"Once you have written down your recovery code " \
                                 f"and pin enter {self.rand_confirmation} below"

    def on_pre_enter(self, *args):
        self.start_time = perf_counter()
        pass_code = "".join(choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=int(25)))
        time_depth = uniform(3, 10)  # time_depth
        Thread(target=self.generate_master_key, args=(pass_code[:15].encode(),
               pass_code[15:].encode(), time_depth,), daemon=True).start()
        self.pin_code_text = f"Generating key and pin ({time_depth}s left)"
        pass_code_print = f"{pass_code[:5]}-{pass_code[5:10]}-{pass_code[10:15]}-{pass_code[15:20]}-{pass_code[20:]}"
        self.pass_code_text = f"Your recovery code is: {pass_code_print}"

    def continue_confirmation(self):
        if self.rand_confirmation:
            if self.confirmation_code == "":
                print("No input provided")
            else:
                if self.confirmation_code.text == self.rand_confirmation:
                    print("Confirmation code correct")
                    sm.switch_to(signUpScreen2())
                else:
                    print("Confirmation code incorrect")


class signUpScreen2(Screen):
    gen_progress_bar = ObjectProperty()

    def __init__(self, **kwa):
        super(signUpScreen2, self).__init__(**kwa)
        Clock.schedule_interval(self.update_progress_bar, 1.0 / 60.0)

    def update_progress_bar(self, dt):
        self.gen_progress_bar.value += 0.01
        if self.gen_progress_bar.value >= 1:
            self.gen_progress_bar.value = 0
            #sm.switch_to(createScreen4())


class loginScreen(Screen):
    name2 = ObjectProperty(None)
    email = ObjectProperty(None)
    pwd = ObjectProperty(None)

    def signupbtn(self):
        print("null")


# class to display validation result
class logDataScreen(Screen):
    pass


# class for managing screens
class windowManager(ScreenManager):
    pass


kv = Builder.load_file('rdisc_screens.kv')
sm = windowManager()


# adding screens
sm.add_widget(logInOrSignUpScreen(name='login_signup'))
sm.add_widget(keyUnlockScreen(name='login'))
sm.add_widget(signUpScreen1(name='signup1'))
sm.add_widget(signUpScreen2(name='signup2'))
sm.add_widget(loginScreen(name='recovery'))
sm.add_widget(logDataScreen(name='logdata'))


# class that builds gui
class Rdisc(App):
    def build(self):
        Window.clearcolor = (50/255, 50/255, 50/255, 1)
        Window.size = (1264, 681)
        Config.set('input', 'mouse', 'mouse,disable_multitouch')
        return sm


# driver function
if __name__ == "__main__":
    Rdisc().run()