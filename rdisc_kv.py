kv_payload = """# You can edit this file to change the settings of the UI. 
# To see what can be edited visit the wiki at https://kivy.org/doc/stable/api-kivy.lang.html
# other useful links:
# Programming Guide: https://kivy.org/doc/stable/guide/lang.html

### Window Manager ###
# [!] DO NOT EDIT THIS SECTION [!] # 

windowManager:
    logInOrSignUpScreen: 
    keyUnlockScreen:
    createKeyScreen:
    ipSetScreen:
    attemptConnectionScreen:
    captchaScreen:
    nacPassword:
    twoFacSetupScreen:
    unameAndFinish:
    reCreateKeyScreen:
    loginScreen:
    logDataScreen:
    
    
### Templates ###
    
# editing this will change most buttons 
<RoundedButton@Button>
    background_color: (0,0,0,0)
    background_normal: ''
    canvas.before:
        Color:
            rgba: (104/255, 84/255, 252/255,1)
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [10]
            
# colored labels
<YellowLabel@Label>
    color : 0, 0, 0, 1
    canvas.before:
        Color:
            rgba: (243/255, 240/255, 51/255,1)
        Rectangle:
            size: self.size
            pos: self.pos

<OrangeLabel@Label>
    color : 0, 0, 0, 1
    canvas.before:
        Color:
            rgba: (243/255, 132/255, 1/255,1)
        Rectangle:
            size: self.size
            pos: self.pos
            
<GreenLabel@Label>
    color : 0, 0, 0, 1
    canvas.before:
        Color:
            rgba: (20/255, 228/255, 43/255,1)
        Rectangle:
            size: self.size
            pos: self.pos
    

### Screens ###

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
            text : "Your account key and pin are REQUIRED to access your account on another device.\\nIf you lose these YOU WILL NOT be able to login in to your account or recover it.\\nFor security reasons we suggest you do not store these keys digitally"
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
        YellowLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        Label:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}
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
        GreenLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        YellowLabel:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
        Label:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos


<attemptConnectionScreen>:
    FloatLayout:
        Label:
            text : "Attempting to connect to server..."
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.85}
        GreenLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        OrangeLabel:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
        Label:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<captchaScreen>:
    captcha_input : captcha_input
    FloatLayout:
        Label:
            text : root.captcha_prompt_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.85}
        Image:
            id: captcha_image
            source: 'captcha_blank.jpg'
            pos_hint : {"x": 0, "top": 1.15}
        TextInput:
            id : captcha_input
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.5}
        RoundedButton:
            text : "Next"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.35}
            on_press : root.try_captcha()
        GreenLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        GreenLabel:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
        YellowLabel:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
        Label:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<nacPassword>:
    nac_password_1 : nac_password_1
    nac_password_2 : nac_password_2
    FloatLayout:
        Label:
            text : "Enter new password"
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.80}
        TextInput:
            id : nac_password_1
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.70}
        Label:
            text : "Repeat password"
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.60}
        TextInput:
            id : nac_password_2
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.50}
        RoundedButton:
            text : "Next"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.30}
            on_press : root.set_nac_password()
        GreenLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        GreenLabel:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
        GreenLabel:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
        YellowLabel:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
        Label:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos
        Label:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<twoFacSetupScreen>:
    two_fac_confirm : two_fac_confirm
    FloatLayout:
        Label:
            text : root.two_fac_wait_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.93}
        AsyncImage:
            id: two_fac_qr
            source: 'blank_qr.png'
            pos_hint : {"x": 0, "top": 1.10}
        TextInput:
            id : two_fac_confirm
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.34}
        RoundedButton:
            text : "Confirm"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.20}
            on_press : root.confirm_2fa()
        GreenLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        GreenLabel:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
        GreenLabel:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
        GreenLabel:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
        YellowLabel:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
        Label:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}
            canvas.before:
                Color:
                    rgba: (60/255, 60/255, 50/255,1)
                Rectangle:
                    size: self.size
                    pos: self.pos

<unameAndFinish>:
    username_setup : username_setup
    FloatLayout:
        Label:
            text : root.account_finished_details_text
            size_hint : 0.3, 0.1
            pos_hint : {"x": 0.35, "top": 0.8}
        TextInput:
            id : username_setup
            multiline : False
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.6}
        RoundedButton:
            text : "Set Username"
            size_hint : 0.3, 0.1
            pos_hint : {"x" : 0.35, "top" : 0.4}
            on_press : root.confirm_2fa()
        GreenLabel:
            text : "User keys >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.2,  "top": 1}
        GreenLabel:
            text : "Set IP >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.3,  "top": 1}
        GreenLabel:
            text : "CAPTCHA >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.4,  "top": 1}
        GreenLabel:
            text : "Password >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.5,  "top": 1}
        GreenLabel:
            text : "2FA Setup >>"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.6,  "top": 1}
        YellowLabel:
            text : "Username"
            size_hint : 0.1, 0.05
            pos_hint : {"x": 0.7,  "top": 1}

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


"""


def kv():
    with open("rdisc.kv", "w", encoding="utf-8") as f:
        f.write(kv_payload)
