import enclib as enc
from rsa import newkeys, PublicKey, decrypt
from os import path, mkdir, listdir, remove
from socket import socket
from subprocess import Popen, call
from zipfile import ZipFile
from time import sleep, perf_counter
from threading import Thread

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.config import Config


class Server:
    def __init__(self):
        self.s, self.enc_key = socket(), None
        if path.exists("app/server_ip"):
            with open(f"app/server_ip", "rb") as f:
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


def load(dt=None):
    if not path.exists("app"):
        mkdir("app")
        sm.switch_to(ChooseDistro())
    else:
        if path.exists("app/code/rdisc.py"):
            call("launch.bat")
            sleep(2)
            App.get_running_app().stop()
        else:
            try:
                [file for file in listdir('app') if file.endswith('.exe')][-1]
                sm.switch_to(AttemptConnection())
            except IndexError:
                sm.switch_to(ChooseDistro())


class Loading(Screen):
    def __init__(self, **kwargs):
        super(Loading, self).__init__(**kwargs)
        Clock.schedule_once(load, 0.1)


class ChooseDistro(Screen):
    def exe(self):
        sm.switch_to(AttemptConnection())

    def dev(self):
        sm.switch_to(CreateDev())


class AttemptConnection(Screen):
    def on_enter(self, *args):
        if s.ip and s.connect():
            print("Connected to server")
            with open(f"app/server_ip", "wb") as f:
                f.write(f"{s.ip[0]}:{s.ip[1]}".encode())
            sm.switch_to(Update())
        else:
            sm.switch_to(IpSet(), direction="left")


class IpSet(Screen):
    ip_address = ObjectProperty(None)

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
                        if all(i.isdigit() and 0 <= int(i) <= 255 for i in [ip_1, ip_2, ip_3, ip_4]):
                            s.ip = [server_ip, server_port]
                            sm.switch_to(AttemptConnection(), direction="left")
                        else:
                            print("\n🱫[COL-RED] IP address must have integers between 0 and 255")
                    except ValueError or NameError:
                        print("\n🱫[COL-RED] IP address must be in the format 'xxx.xxx.xxx.xxx'")


class Update(Screen):
    update_text = StringProperty()

    def update_system(self):
        self.update_text = "Checking for updates..."
        file_name = None
        try:
            app_location = [file for file in listdir('app') if file.endswith('.exe')][-1]
            app_hash = enc.hash_a_file(f"app/{app_location}")
            s.send_e(f"UPD:{app_hash}")
            update_data = s.recv_d(1024)
            if not update_data == "V":
                file_name, update_size = update_data.split("🱫")
        except IndexError:
            s.send_e("UPD:N")
            file_name, update_size = s.recv_d(1024).split("🱫")
        if file_name:
            update_size = int(update_size)
            self.update_text = f"Downloading version {file_name[:-4].replace('rdisc', 'Rdisc')}..."
            all_bytes = b""
            start = perf_counter()
            while True:
                bytes_read = s.s.recv(32768)
                if b"_BREAK_" in bytes_read:
                    all_bytes += bytes_read[:-7]
                    break
                if perf_counter()-start > 0.25:
                    start = perf_counter()
                    self.update_text = f"Downloading version {file_name[:-4].replace('rdisc', 'Rdisc')} " \
                                       f"({round((len(all_bytes)/update_size)*100, 2)}%)"
                all_bytes += bytes_read
            with open(f"app/{file_name}", "wb") as f:
                f.write(all_bytes)
            self.update_text = "Update downloaded, unpacking..."
            sleep(1)
            with ZipFile(f"app/{file_name}", 'r') as zip_:
                zip_.extractall("app")
            self.update_text = f"Successfully updated to {file_name[:-4].replace('rdisc', 'Rdisc')}."
            sleep(1)
            remove(f"app/{file_name}")
            for file in listdir("app"):
                if file.endswith(".exe") and file != f"{file_name[:-4]}.exe":
                    remove(f"app/{file}")

        self.update_text = "Launching..."
        Popen(f"app/{[file for file in listdir('app') if file.endswith('.exe')][-1]}")
        App.get_running_app().stop()

    def on_enter(self, *args):
        Thread(target=self.update_system).start()


class CreateDev(Screen):
    create_text = StringProperty()

    def create(self):
        self.create_text = "Detecting git..."
        try:
            call("git")
        except FileNotFoundError:
            self.create_text = "Git not installed, installing..."
            call("winget install --id Git.Git -e --source winget")
        self.create_text = "Loading repo installer..."
        with open("install.bat", "w") as f:
            f.write("""echo Setting up repository
        git clone --filter=blob:none --no-checkout --depth 1 --sparse https://github.com/rapidslayer101/Rdisc-Kivy app/code
        cd app/code
        git config core.sparsecheckout true
        echo rdisc.py > .git/info/sparse-checkout
        echo rdisc_kv.py >> .git/info/sparse-checkout
        echo enclib.py >> .git/info/sparse-checkout
        echo venv.zip >> .git/info/sparse-checkout
        git checkout
        tar -xf venv.zip
        )""")
        self.create_text = "Running repo installer..."
        call("install.bat")
        self.create_text = "Installing dependency (kivy) 1/2..."
        call("app/code/venv/Scripts/python -m pip install kivy")
        self.create_text = "Installing dependency (rsa) 2/2..."
        call("app/code/venv/Scripts/python -m pip install rsa")
        self.create_text = "Launching..."
        with open("launch.bat", "w") as f:
            f.write("""cd app/code
        echo Checking for updates
        git reset --hard
        git pull origin master
        echo Launching client
        start venv/Scripts/python.exe rdisc.py""")

        call("launch.bat")
        sleep(2)
        App.get_running_app().stop()

    def on_enter(self, *args):
        Thread(target=self.create).start()


class WindowManager(ScreenManager):
    pass


Builder.load_string("""

#:set rdisc_purple (104/255, 84/255, 252/255,1)
#:set rdisc_purple_dark (104/255, 73/255, 160/255,1)
#:set rdisc_cyan (37/255, 190/255, 150/255,1)
#:set bk_grey_1 (50/255, 50/255, 50/255,1)

<GreyFloatLayout@FloatLayout>:
    canvas.before:
        Color:
            rgba: bk_grey_1
        Rectangle:
            pos: self.pos
            size: self.size    
            
<RoundedButton@Button>
    background_color: 0,0,0,0
    size_hint: 0.3, 0.1
    canvas.before:
        Color:
            rgba: rdisc_purple if self.state == 'normal' else rdisc_purple_dark
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [10]
            
<RoundedTextInput@TextInput>:
    font_size: '16dp'
    multiline: False
    halign: "center"
    size_hint: 0.3, 0.1
    padding: [0, self.height/2.0-(self.line_height/2.0)*len(self._lines), 0, 0]
    write_tab: False
    background_color: 0,0,0,0
    cursor_color: rdisc_cyan
    canvas.before:
        Color:
            rgba: rdisc_cyan
    canvas.after:
        Color:
            rgba: 0,0,0,0
        Ellipse:
            angle_start:180
            angle_end:360
            pos:(self.pos[0]-self.size[1]/2.0, self.pos[1])
            size: (self.size[1], self.size[1])
        Ellipse:
            angle_start:360
            angle_end:540
            pos: (self.size[0]+self.pos[0]-self.size[1]/2.0, self.pos[1])
            size: (self.size[1], self.size[1])
        Color:
            rgba: rdisc_purple
        Line:
            points: self.pos[0], self.pos[1], self.pos[0]+self.size[0], self.pos[1]
        Line:
            points: self.pos[0], self.pos[1]+self.size[1], self.pos[0]+self.size[0], self.pos[1]+self.size[1]
        Line:
            ellipse: self.pos[0]-self.size[1]/2.0, self.pos[1], self.size[1], self.size[1], 180, 360
        Line:
            ellipse: self.size[0]+self.pos[0]-self.size[1]/2.0, self.pos[1], self.size[1], self.size[1], 360, 540
            
<SizeLabel@Label>:
    size_hint: 0.1, 0.05
    
<Loading>:
    GreyFloatLayout:
        Label:
            text: "Loading..."
            font_size: '18dp'
            size_hint: 0.3, 0.1
            pos_hint: {"x": 0.35, "top": 0.6}
    
<ChooseDistro>:
    GreyFloatLayout:
        SizeLabel:
            text: "Choose Distro:"
            font_size: '18dp'
            pos_hint: {"x": 0.45, "top": 0.75}
        SizeLabel:
            text: "For normal users:"
            pos_hint: {"x": 0.25, "top": 0.58}
        RoundedButton:
            text: "Rdisc (exe)"
            pos_hint: {"x": 0.5, "top": 0.6}
            on_press: root.exe()
        SizeLabel:
            text: "For coders/devs:"
            pos_hint: {"x": 0.25, "top": 0.38}
        RoundedButton:
            text: "Rdisc Dev (py)"
            pos_hint: {"x": 0.5, "top": 0.4}
            on_press: root.dev()

<AttemptConnection>:
    GreyFloatLayout:
        Label:
            text: "Attempting to connect to server..."
            font_size: '18dp'
            size_hint: 0.3, 0.1
            pos_hint: {"x": 0.35, "top": 0.6}

<IpSet>:
    ip_address: ip_address
    GreyFloatLayout:
        SizeLabel:
            text: "Enter server IP address"
            pos_hint: {"x": 0.45, "top": 0.8}
        RoundedTextInput:
            id: ip_address
            pos_hint: {"x": 0.35, "top": 0.65}
            on_text_validate: root.try_connect()
        RoundedButton:
            text: "Connect"
            pos_hint: {"x": 0.35, "top": 0.45}
            on_press: root.try_connect()
            
            
<Update>:
    GreyFloatLayout:
        Label:
            text: root.update_text
            font_size: '18dp'
            size_hint: 0.3, 0.1
            pos_hint: {"x": 0.35, "top": 0.6}
            
            
<CreateDev>:
    GreyFloatLayout:
        Label:
            text: root.create_text
            font_size: '18dp'
            size_hint: 0.3, 0.1
            pos_hint: {"x": 0.35, "top": 0.6}
            


""")
sm = WindowManager()
[sm.add_widget(screen) for screen in [Loading(), ChooseDistro(), AttemptConnection(), IpSet(), Update(), CreateDev()]]


class RdiscUpdater(App):
    def build(self):
        self.title = f"Rdisc Updater"
        Window.size = (500, 600)
        Config.set('input', 'mouse', 'mouse,disable_multitouch')
        Config.set('kivy', 'exit_on_escape', '0')
        return sm


if __name__ == "__main__":
    RdiscUpdater().run()
