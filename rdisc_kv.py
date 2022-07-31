kv_payload = """# You can edit this file to change the settings of the UI. 
# To see what can be edited visit the wiki at https://kivy.org/doc/stable/guide/lang.html

# Dont touch this section
windowManager:
    logInOrSignUpScreen:
    keyUnlockScreen:
    createKeyScreen:
    ipSetScreen:
    next:
    reCreateKeyScreen:
    loginScreen:
    logDataScreen:

<logInOrSignUpScreen>:
    FloatLayout:
        size: root.width, root.height
        Label:
            text : "Welcome to Rdisc!"
            #size_hint : 0.2, 0.1
            pos_hint : {"x" : 0, "top" : 1.25}
        RoundedButton:
            text : "Login"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.55}
            on_release:
                app.root.current = 'login'
                root.manager.transition.direction = "left"
        RoundedButton:
            text : "Sign Up"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.35}
            on_release:
                app.root.current = 'create_key'
                root.manager.transition.direction = "left"

<keyUnlockScreen>:
    pwd : pwd
    FloatLayout:
        size: root.width, root.height
        Label:
            text : "PASSWORD: "
            size_hint : 0.2, 0.1
            pos_hint : {"x" : 0.25, "top" : 0.7}
        TextInput:
            id : pwd
            multiline :False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.45, "top" : 0.7}
        RoundedButton:
            text : "LOGIN"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.5}
            on_release:
                root.validate()
                root.manager.transition.direction = "left"


<createKeyScreen>:
    confirmation_code : confirmation_code
    confirmation_warning : confirmation_warning
    FloatLayout:
        Label:
            text : root.pass_code_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.9}
        Label:
            text : root.pin_code_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.8}
        Label:
            id : confirmation_warning
            text : ""
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.7}
        Label:
            text : root.rand_confirm_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.6}
        TextInput:
            id : confirmation_code
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.45}
        RoundedButton:
            text : "Next"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.3}
            on_press : root.continue_confirmation()
        Label:
            text : "Account Keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
            color : 0, 0, 0, 1
            canvas.before:
                Color:
                    rgba: (243/255, 240/255, 51/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Server Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<ipSetScreen>:
    ip_address : ip_address
    FloatLayout:
        Label:
            text : "Enter server IP address"
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.85}
        TextInput:
            id : ip_address
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.65}
        RoundedButton:
            text : "Connect"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.45}
            on_press : root.try_connect()
        Label:
            text : "Backup Keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
            color : 0, 0, 0, 1
            canvas.before:
                Color:
                    rgba: (20/255, 228/255, 43/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Server Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
            color : 0, 0, 0, 1
            canvas.before:
                Color:
                    rgba: (243/255, 240/255, 51/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<next>:
    FloatLayout:
        Label:
            text : "Next"
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.85}
        Label:
            text : "Backup Keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
            color : 0, 0, 0, 1
            canvas.before:
                Color:
                    rgba: (20/255, 228/255, 43/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Server Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
            color : 0, 0, 0, 1
            canvas.before:
                Color:
                    rgba: (20/255, 228/255, 43/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<reCreateKeyScreen>:
    confirmation_code : confirmation_code
    FloatLayout:
        Label:
            text : root.pass_code_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.9}
        Label:
            text : root.pin_code_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.8}
        Label:
            text : root.rand_confirm_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.7}
        TextInput:
            id : confirmation_code
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.55}
        RoundedButton:
            text : "CONFIRM"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.4}
            on_press : root.continue_confirmation()
        Button:
            text : "<< Back"
            size_hint : 0.1, 0.05
            pos_hint : {"x" : 0, "top" : 1}
            on_press :
                app.root.current = 'login_signup'
                root.manager.transition.direction = "right"

<loginScreen>:
    FloatLayout:
        Button:
            text : "<< Back"
            size_hint : 0.1, 0.05
            pos_hint : {"x" : 0, "top" : 1}
            on_press :
                app.root.current = 'login_signup'
                root.manager.transition.direction = "right"

# show login success
<logDataScreen>:
    info : info
    FloatLayout:
        Label:
            id : info
            size_hint : 0.8, 0.2
            pos_hint : {"x" : 0.12, "top" : 0.8}
            text : "SUCCESSFULLY LOGGED IN AS"


<RoundedButton@Button>
    background_color: (0,0,0,0)
    background_normal: ''
    canvas.before:
        Color:
            #rgba: (48/255,84/255,150/255,1)
            rgba: (104/255, 84/255, 252/255,1)
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [10]


"""


def kv():
    with open("rdisc.kv", "w", encoding="utf-8") as f:
        f.write(kv_payload)
