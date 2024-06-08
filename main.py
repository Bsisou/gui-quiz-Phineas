import hashlib
import json
import os
import tkinter as tk
import tkinter.font as tk_font

import psutil  # for memory usage only - pip install psutil
import pyglet  # pip install pyglet
from PIL import Image, ImageTk, ImageDraw  # pip install pillow


def get_memory():
    print(f"Memory usage: {psutil.Process(os.getpid()).memory_info().rss / 1e+6} MB")


class RecollectApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Recollect")
        self.root.geometry("750x563")  # Same ratio as 1000 x 750
        self.root.minsize(750, 563)
        self.username = None

        self.data_file = "data.json"

        self.themes = {
            "Fruity (Default)": {
                "img_bg": "background.png",
                "img_blob": "blob.png",
                "accent": "#53B0C8",
                "text": "black",
                "outline": "black",
                "btn_bg": "#5F7BF8",
                "btn_hvr": "#4B61C4",
                "btn_prs": "#2D3B77",
                "btn_warn_hvr": "#B14747",
                "btn_warn_prs": "#FE6666",
            },
            "Piercing Crimson": {
                "img_bg": "background_crimson.png",
                "img_blob": "blob_crimson.png",
                "accent": "#C85053",
                "text": "black",
                "outline": "black",
                "btn_bg": "#F85F7B",
                "btn_hvr": "#C44B61",
                "btn_prs": "#772D3B",
                "btn_warn_hvr": "#400c13",
                "btn_warn_prs": "#8d1c2a",
            }
        }

        self.games = {
            "Matching Tiles": Games.MatchingTiles
        }

        self.volume = tk.IntVar(value=50)
        self.last_volume = 50

        self.theme = list(self.themes.keys())[0]
        self.theme_data = self.themes[self.theme]

        """
        user_data_template = {
            "password": None,
            "options": {
                "volume": None,
                "theme": None
            }
        }
        """

        # Overriding default font if custom font does not work
        self.defaultFont = tk_font.nametofont("TkDefaultFont")
        self.defaultFont.configure(family="Calibri")

        self.current_screen = None
        self.show_screen(Screens.Homepage(self.root, self).get())

        self.root.mainloop()

    def get_background(self) -> Image:
        return Image.open(f"assets/{self.theme_data['img_bg']}")

    def get_blob(self, width, height, angle) -> (ImageTk.PhotoImage, Image):
        blob = Image.open(f"assets/{self.theme_data['img_blob']}").rotate(angle, Image.NEAREST, expand=True).resize((width, height), 1)
        return ImageTk.PhotoImage(blob)

    @staticmethod
    def get_coordinates_relative_window(widget):
        return widget.winfo_rootx() - root.winfo_rootx(), widget.winfo_rooty() - root.winfo_rooty()

    @staticmethod
    def encrypt_str(raw: str):
        sha256 = hashlib.sha256()
        sha256.update(raw.encode('utf-8'))
        return sha256.hexdigest()

    def encrypt_password(self, password: str):
        for _ in range(256):  # Encrypt 256 times
            password = self.encrypt_str(password)
        return password

    def check_if_data_file_exists(self):
        # Check if data file exists
        if not os.path.exists(self.data_file):
            with open("data.json", "w+") as data_file:
                json.dump({"users": {}}, data_file)

    def get_user_data(self, username):
        self.check_if_data_file_exists()

        try:
            with open("data.json", "r+") as data_file:
                data = json.load(data_file)
                return data['users'][username]
        except KeyError:
            return None

    def add_new_user_data(self, username, password):
        self.check_if_data_file_exists()
        user_data = {
            "password": self.encrypt_password(password),
            "options": {
                "volume": int(self.volume.get()),
                "theme": self.theme
            }
        }
        with open("data.json", "r+") as data_file:
            data = json.load(data_file)
            data['users'][username] = user_data
            data_file.seek(0)
            data_file.truncate()
            json.dump(data, data_file, indent=2)
        return user_data

    def rewrite_user_data(self, username, user_data):
        self.check_if_data_file_exists()

        with open("data.json", "r+") as data_file:
            data = json.load(data_file)
            data['users'][username] = user_data
            data_file.seek(0)
            data_file.truncate()
            json.dump(data, data_file, indent=2)

    def show_screen(self, screen: tk.Canvas):
        if self.current_screen is not None:
            self.current_screen.pack_forget()
            self.current_screen.destroy()
            del self.current_screen
        screen.pack(side="top", fill=tk.BOTH, expand=True)
        self.current_screen = screen

    def show_overlaying_screen(self, overlaying_screen: tk.Canvas):
        # overlaying_screen.place(x=0, y=0, anchor="nw")
        self.current_screen.pack_forget()
        overlaying_screen.pack(side="top", fill=tk.BOTH, expand=True)

    def finish_overlaying_screen(self, overlaying_screen: tk.Canvas, screen=None):
        overlaying_screen.destroy()
        if screen is None:  # Do not update screen if None
            self.current_screen.pack(side="top", fill=tk.BOTH, expand=True)
        else:  # Update screen if screen is provided
            self.show_screen(screen)

    @staticmethod
    def add_corners(image: Image, radius: int):
        # Adapted from https://stackoverflow.com/a/78202642
        circle = Image.new("L", (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, radius * 2 - 1, radius * 2 - 1), fill=255)
        alpha = Image.new("L", image.size, 255)
        w, h = image.size
        alpha.paste(circle.crop((0, 0, radius, radius)), (0, 0))
        alpha.paste(circle.crop((0, radius, radius, radius * 2)), (0, h - radius))
        alpha.paste(circle.crop((radius, 0, radius * 2, radius)), (w - radius, 0))
        alpha.paste(circle.crop((radius, radius, radius * 2, radius * 2)), (w - radius, h - radius))
        image.putalpha(alpha)
        return image


class BaseScreen:
    def __init__(self, root: tk.Tk, app: RecollectApp, has_background: bool = True, has_blobs: bool = True):
        self.root = root
        self.app = app
        self.has_background = has_background
        self.has_blobs = has_blobs

        self.current_background: Image = None
        self._blobs_tk: list = []  # Only works when it is inside the class scope not local scope

        self.canvas = tk.Canvas(self.root, borderwidth=0, highlightthickness=0)

        root.update_idletasks()  # Updates root background size
        if self.has_background:
            self.update_background()
        if self.has_blobs:
            self.update_blobs()

        self.transparent_images = []
        self.widgets = []

        print("Created screen with memory usage:")
        get_memory()

    def finish_init(self):
        self.canvas.update_idletasks()  # Updates canvas coordinates size

        if self.has_background:
            self.update_transparent_images()
            self.update_widgets_background()

            self.canvas.bind("<Configure>", self.update_background, add="+")
            self.canvas.bind("<Configure>", self.update_transparent_images, add="+")
            self.canvas.bind("<Configure>", self.update_widgets_background, add="+")
        if self.has_blobs:
            self.canvas.bind("<Configure>", self.update_blobs, add="+")

        print("Finished creating screen with memory usage:")
        get_memory()

    def get(self):
        return self.canvas

    def update_background(self, _=None):
        self.canvas.delete("background")
        # Adjust background stretching etc.
        width, height = self.root.winfo_width(), self.root.winfo_height()
        del self.current_background
        self.current_background = self.app.get_background().resize((width, height), 1)
        self.canvas.bg_image = ImageTk.PhotoImage(self.current_background)  # Must be in class scope
        self.canvas.create_image(0, 0, image=self.canvas.bg_image, anchor="nw", tags="background")  # Don't make one-liner

    def place_blob(self, size: int, angle: int | float, x: int | float, y: int | float, anchor):
        blob_tk = self.app.get_blob(size, size, angle)
        self._blobs_tk.append(blob_tk)  # Must be in class scope
        self.canvas.create_image(x, y, image=self._blobs_tk[-1], anchor=anchor, tags="blob")  # Don't make one-liner

    def update_blobs(self, _=None):
        self.canvas.delete("blob")
        # Clears previous blobs from memory
        del self._blobs_tk
        self._blobs_tk = []

        # all sizes minimum 100px
        self.place_blob(max(int(root.winfo_width() * 0.3333), 100), -30, -60, root.winfo_height() * 0.7, "w")  # size=33% of width, x=60, y=70% of height
        self.place_blob(max(int(root.winfo_width() * 0.2666), 100), 25, root.winfo_width() + 90, root.winfo_height() * 0.25, "e")  # size=27% of width, x=100% of height + 90px, y=25% of height
        self.place_blob(max(int(root.winfo_width() * 0.4), 100), 150, root.winfo_width() + 55, root.winfo_height() - 60, "e")  # size=40% of width, x=100% of height + 55px, y=100% of height - 60%

    def update_transparent_images(self, _=None):
        if self.has_background is False or self.current_background is None:  # No background or current background not showing
            return

        for transparent_image_data in self.transparent_images:
            image_label = transparent_image_data['label']
            image = transparent_image_data['raw_image']

            transparent_image_data['updated_image'] = ImageTk.PhotoImage(image)  # Don't make one-liner
            image_label.config(image=transparent_image_data['updated_image'])  # Used to remeasure image coordinates

            # Adjust label background
            self.canvas.update_idletasks()  # Updates coordinates
            x1, y1 = image_label.winfo_x(), image_label.winfo_y()
            x2, y2 = x1 + image_label.winfo_width(), y1 + image_label.winfo_height()

            background_at_bbox = self.current_background.crop((x1, y1, x2, y2))
            # Merge background (RGB) and image (RGBA)
            image_with_background = Image.new("RGBA", background_at_bbox.size)
            image_with_background.paste(background_at_bbox, (0, 0))
            image_with_background.paste(image, (0, 0), image)
            transparent_image_data['updated_image'] = ImageTk.PhotoImage(image_with_background)
            image_label.config(image=transparent_image_data['updated_image'])

    def update_widgets_background(self, _=None, specific_widget=None):
        if self.has_background is False or self.current_background is None:  # No background or current background not showing
            return

        # Adjust each button background
        self.canvas.update_idletasks()  # Updates coordinates

        update_widgets = self.widgets if specific_widget is None else [specific_widget]
        for widget in update_widgets:
            # x1, y1 = widget.winfo_x(), widget.winfo_y()
            x1, y1 = self.app.get_coordinates_relative_window(widget)
            x2, y2 = x1 + widget.winfo_width(), y1 + widget.winfo_height()

            background_at_bbox = self.current_background.crop((x1, y1, x2, y2))

            widget.bg_image = ImageTk.PhotoImage(background_at_bbox)

            if widget.__class__.__name__ in ["RoundedButton", "Canvas"]:
                widget.create_image(0, 0, image=widget.bg_image, anchor="nw")
            elif widget.__class__.__name__ == "Label":
                widget.config(image=widget.bg_image, compound=tk.CENTER, bd=0, borderwidth=0, highlightthickness=0, relief="flat", padx=0, pady=0)
            if widget.__class__.__name__ == "RoundedButton":
                widget.generate_button()  # Remakes polygon and text

    def destroy(self):
        self.canvas.unbind("<Configure>")
        del self


class Screens:
    class Homepage(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"

            logo_image = Image.open("assets/logo.png").convert("RGBA").resize((370, 121))  # Must be multiple of 935 x 306
            self.logo_label = tk.Label(self.canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": self.logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            self.logo_label.config(image=image_data['updated_image'])
            self.logo_label.pack(anchor=tk.CENTER, pady=(50, 0))
            self.transparent_images.append(image_data)
            del logo_image

            self.start_button = RoundedButton(
                self.canvas, text="START", font=("Poppins Bold", 20, "bold"),
                width=350, height=75, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_click_start
            )
            self.start_button.pack(anchor=tk.CENTER, pady=(30, 0))
            self.widgets.append(self.start_button)

            self.options_button = RoundedButton(
                self.canvas, text="OPTIONS", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_click_options
            )
            self.options_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(self.options_button)

            self.quit_button = RoundedButton(
                self.canvas, text="QUIT", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: root.destroy()
            )
            self.quit_button.pack(anchor=tk.CENTER, pady=(20, 20))
            self.widgets.append(self.quit_button)

            self.finish_init()

        def on_click_start(self):
            self.destroy()
            if self.app.username is None or self.app.get_user_data(self.app.username) is None:  # Not logged in or username not in data for some reason
                self.app.username = None
                self.app.show_screen(Screens.Login(self.root, self.app).get())
            else:
                self.app.show_screen(Screens.GameSelection(self.root, self.app).get())

        def on_click_options(self):
            self.app.show_overlaying_screen(Screens.SettingsMenu(self.root, self.app, self).get())

    class Login(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"

            self.logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            self.logo_canvas.pack(pady=(10, 0), padx=(10, 0), anchor="nw")
            self.widgets.append(self.logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            self.logo_label = tk.Label(self.logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": self.logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            self.logo_label.config(image=image_data['updated_image'])
            self.logo_label.pack(anchor="nw", padx=(5, 0), pady=(3, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            self.logo_title = tk.Label(self.logo_canvas, text="Sign In", font=("Poppins Regular", 15))
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            self.back_button = RoundedButton(
                self.canvas, text="BACK", font=("Poppins Bold", 15, "bold"),
                width=210, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_back
            )
            self.back_button.pack(pady=(5, 0), padx=(10, 0), anchor="nw")
            self.widgets.append(self.back_button)

            self.heading = tk.Label(self.canvas, text="Sign In", font=("Poppins Bold", 15, "bold"))
            self.heading.pack(anchor=tk.CENTER, pady=(10, 10))
            self.widgets.append(self.heading)

            self.username_entry = tk.Entry(self.canvas, font=("Poppins Regular", 11), width=25)
            self.username_entry.pack(anchor=tk.CENTER, pady=(5, 5))
            self.username_entry.bind("<FocusIn>", lambda event: self.on_focusin_entry(self.username_entry, "Username"))
            self.username_entry.bind("<FocusOut>", lambda event: self.on_focusout_entry(self.username_entry, "Username"))
            self.on_focusout_entry(self.username_entry, "Username")

            self.password_entry = tk.Entry(self.canvas, font=("Poppins Regular", 11), width=25)
            self.password_entry.pack(anchor=tk.CENTER, pady=(5, 5))
            self.password_entry.bind("<FocusIn>", lambda event: self.on_focusin_entry(self.password_entry, "Password"))
            self.password_entry.bind("<FocusOut>", lambda event: self.on_focusout_entry(self.password_entry, "Password"))
            self.on_focusout_entry(self.password_entry, "Password")

            self.error_message = tk.Label(self.canvas, text="", font=("Poppins Regular", 9), fg="red")
            self.error_message.pack(anchor=tk.CENTER, pady=(5, 10))
            self.widgets.append(self.error_message)

            self.sign_in_button = RoundedButton(
                self.canvas, text="SIGN IN", font=("Poppins Bold", 15, "bold"),
                width=250, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_sign_in
            )
            self.sign_in_button.pack(anchor=tk.CENTER, pady=(5, 5))
            self.widgets.append(self.sign_in_button)

            self.finish_init()

        def on_back(self):
            self.destroy()
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())

        def check_met_criteria(self):
            # Check if any entry is empty
            username_empty = self.username_entry.get().strip() in ["Username", ""]
            password_empty = self.password_entry.get().strip() in ["Password", ""]
            if username_empty or password_empty:
                if username_empty:
                    self.username_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                if password_empty:
                    self.password_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Cannot have blank username or password.")
                return False

            # Check length is greater than 7 characters
            if len(self.password_entry.get()) <= 7:
                self.password_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Password must be greater than 7 characters.")
                return False

            # Check number, uppercase, and lowercase criteria
            has_upper = False
            has_lower = False
            has_digit = False
            for i in self.password_entry.get():
                if i.isupper():
                    has_upper = True
                if i.islower():
                    has_lower = True
                if i.isdigit():
                    has_digit = True
            if not has_upper or not has_lower or not has_digit:
                self.password_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Password must have a number, uppercase, and lowercase characters.")
                return False

            return True

        def on_sign_in(self):
            self.error_message.config(text="", image="")
            self.root.focus()  # Unselects entry boxes

            if not self.check_met_criteria():
                self.update_widgets_background(specific_widget=self.error_message)
                return

            entered_username = self.username_entry.get().strip().lower()  # Lowercase usernames only
            entered_password = self.password_entry.get()

            user_data = self.app.get_user_data(entered_username)
            if user_data is None:  # Account does not exist
                user_data = self.app.add_new_user_data(entered_username, entered_password)  # Create new account

            elif self.app.encrypt_password(entered_password) != user_data['password']:  # Account exists, but wrong password
                self.password_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Incorrect password.")
                self.update_widgets_background(specific_widget=self.error_message)
                return

            # Password is correct / Account created
            self.app.username = entered_username

            try:
                self.app.volume.set(int(user_data['options']['volume']))
                self.app.theme = user_data['options']['theme']
                self.app.theme_data = self.app.themes[user_data['options']['theme']]
            except KeyError:
                print("User has no options data, continuing with existing options")

            self.destroy()
            self.app.show_screen(Screens.GameSelection(self.root, self.app).get())

        @staticmethod
        def on_focusin_entry(entry: tk.Entry, hint: str):
            entry.config(fg="black", bg="white")
            if hint == "Password":
                entry.config(show="*")
            if entry.get().strip() in ["Username", "Password"]:
                entry.delete(0, tk.END)

        @staticmethod
        def on_focusout_entry(entry: tk.Entry, hint: str):
            if entry.get().strip() == "":
                entry.delete(0, tk.END)
                entry.insert(0, hint)
                entry.config(fg="grey", show="")

    class GameSelection(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True, False)  # Implements all variables and function from base class "BaseScreen"

            self.selected_game = None

            self.logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            self.logo_canvas.pack(pady=(10, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(self.logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            self.logo_label = tk.Label(self.logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": self.logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            self.logo_label.config(image=image_data['updated_image'])
            self.logo_label.pack(anchor="nw", padx=(5, 0), pady=(3, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            self.logo_title = tk.Label(self.logo_canvas, text="Gamemodes", font=("Poppins Regular", 15))
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            self.settings_button = RoundedButton(
                self.logo_canvas, font=("", 0, ""),
                width=50, height=50, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/settings.png").convert("RGBA").resize((35, 35))),
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_settings_click
            )
            self.settings_button.pack(anchor="ne", pady=(15, 0), side=tk.RIGHT)
            self.widgets.append(self.settings_button)

            self.game_outer_frame = tk.Frame(self.canvas, bd=0, borderwidth=0, highlightthickness=0, bg=self.app.theme_data['accent'])
            self.game_outer_frame.pack(fill=tk.BOTH, expand=True)

            self.game_inner_canvas = tk.Canvas(self.game_outer_frame, bg=self.app.theme_data['accent'], bd=0, borderwidth=0, highlightthickness=0)
            self.game_inner_canvas.pack(anchor=tk.CENTER, side=tk.LEFT, fill=tk.Y, expand=True)

            self.scrollbar = tk.Scrollbar(self.game_outer_frame, orient=tk.VERTICAL, command=self.game_inner_canvas.yview)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.game_inner_canvas.configure(yscrollcommand=self.scrollbar.set)
            self.root.update()
            self.game_inner_canvas.bind("<Configure>", lambda e: self.game_inner_canvas.configure(scrollregion=self.game_inner_canvas.bbox("all")))

            self.game_button_canvas = tk.Canvas(self.game_inner_canvas, bg=self.app.theme_data['accent'], bd=0, borderwidth=0, highlightthickness=0)

            self.game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_game_select("Matching Tiles")
            )
            self.game_button.on_regen = lambda: self.after_game_button(self.game_button, self.app.get_background(), "MATCHING TILES", "Flip over and memorise pairs of cards, trying to find matching images.\nEnhances concentration and memory skills.")
            self.game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.game_button.on_regen()

            self.game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.game_button.on_regen = lambda: self.after_game_button(self.game_button, self.app.get_background(), "Coming soon...", "")
            self.game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.game_button.on_regen()

            self.game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.game_button.on_regen = lambda: self.after_game_button(self.game_button, self.app.get_background(), "Coming soon...", "")
            self.game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.game_button.on_regen()

            self.game_button_window = self.game_inner_canvas.create_window((0, 0), window=self.game_button_canvas, anchor="nw")

            self.game_inner_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            self.game_button_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            for child in self.game_button_canvas.children.values():
                child.bind("<MouseWheel>", self.on_mouse_wheel)

            # Fixes game button canvas getting cut off
            self.root.update()
            x1, y1, x2, y2 = self.game_inner_canvas.bbox("all")
            self.game_inner_canvas.config(width=x2 - x1, height=y2 - y1)

            # Create difficulty canvas, but don't pack until game is selected
            self.difficulty_canvas = tk.Canvas(self.canvas, bd=0, borderwidth=0, highlightthickness=0, bg=self.app.theme_data['accent'])

            self.back_button = RoundedButton(
                self.difficulty_canvas, text="BACK", font=("Poppins Bold", 15, "bold"),
                width=210, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_difficulty_back
            )
            self.back_button.pack(pady=(5, 0), padx=(10, 0), anchor="nw")

            self.heading = tk.Label(self.difficulty_canvas, text="Select a difficulty level", font=("Poppins Bold", 15, "bold"), bg=self.app.theme_data['accent'])
            self.heading.pack(anchor=tk.CENTER, pady=(10, 0))

            self.difficulty_button = RoundedButton(
                self.difficulty_canvas, font=("", 0, ""),
                width=450, height=85, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_difficulty_select("easy")
            )
            self.difficulty_button.on_regen = lambda: self.after_difficulty_button(self.difficulty_button, "Easy", "Match simple images of random categories\nEnhances memory")
            self.difficulty_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.difficulty_button.on_regen()

            self.difficulty_button = RoundedButton(
                self.difficulty_canvas, font=("", 0, ""),
                width=450, height=85, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_difficulty_select("normal")
            )
            self.difficulty_button.on_regen = lambda: self.after_difficulty_button(self.difficulty_button, "Normal", "Match images of the same category\nEnhances memory")
            self.difficulty_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.difficulty_button.on_regen()

            self.difficulty_button = RoundedButton(
                self.difficulty_canvas, font=("", 0, ""),
                width=450, height=85, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_difficulty_select("hard")
            )
            self.difficulty_button.on_regen = lambda: self.after_difficulty_button(self.difficulty_button, "Hard", "Match the answer to simple math problems\nEnhances math and memory")
            self.difficulty_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.difficulty_button.on_regen()

            self.finish_init()

        def after_game_button(self, button, image: Image, name: str, description: str):
            button.game_image = ImageTk.PhotoImage(self.app.add_corners(image.convert("RGBA").resize((130, 130)), 9))
            button.create_image(10, 10, image=button.game_image, anchor="nw", tag="button")
            button.create_text(150, 10, text=name, fill=self.app.theme_data['text'], font=("Poppins Bold", 15, "bold"), anchor="nw", tag="button")
            button.create_text(150, 50, text=description, fill=self.app.theme_data['text'], font=("Poppins Regular", 10), width=button.width - 160, anchor="nw", tag="button")

        def after_difficulty_button(self, button, title: str, text: str):
            button.create_text(10, 0, text=title, fill=self.app.theme_data['text'], font=("Poppins Bold", 14, "bold"), anchor="nw", tag="button")
            button.create_text(10, 33, text=text, fill=self.app.theme_data['text'], font=("Poppins Regular", 9), width=button.width - 10, anchor="nw", tag="button")

        def on_mouse_wheel(self, event):
            self.game_inner_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_settings_click(self):
            self.app.show_overlaying_screen(Screens.SettingsMenu(self.root, self.app, self).get())

        def on_difficulty_back(self):
            self.selected_game = None

            # Update title
            self.logo_title.config(text="Gamemodes")
            self.update_widgets_background(self.logo_title)  # Updates the background for title

            # Remove difficulty buttons and show game buttons
            self.difficulty_canvas.pack_forget()
            self.game_outer_frame.pack(fill=tk.BOTH, expand=True)

        def on_game_select(self, game_name: str):
            self.selected_game = game_name

            # Update title
            self.logo_title.config(text=game_name)
            self.update_widgets_background(self.logo_title)  # Updates the background for title

            # Remove game buttons and show difficulty buttons
            self.game_outer_frame.pack_forget()
            self.difficulty_canvas.pack(fill=tk.BOTH, expand=True)

        def on_difficulty_select(self, difficulty: str):
            self.app.show_screen(self.app.games[self.selected_game](self.root, self.app, difficulty).get())
            del self

    class SettingsMenu(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, caller=None):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"
            self.caller = caller

            self.original_theme = self.app.theme

            self.logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            self.logo_canvas.pack(pady=(10, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(self.logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            self.logo_label = tk.Label(self.logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": self.logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            self.logo_label.config(image=image_data['updated_image'])
            self.logo_label.pack(anchor="nw", padx=(5, 0), pady=(3, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            self.logo_title = tk.Label(self.logo_canvas, text="Options Menu", font=("Poppins Regular", 15))
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            if self.app.username is not None:
                self.sign_out_button = RoundedButton(
                    self.logo_canvas, text="SIGN OUT", font=("Poppins Bold", 15, "bold"),
                    width=210, height=50, radius=29, text_padding=0,
                    button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                    button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                    button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                    outline_colour=self.app.theme_data['outline'], outline_width=1,
                    command=self.on_sign_out
                )
                self.sign_out_button.pack(anchor="ne", pady=(15, 0), side=tk.RIGHT)
                self.widgets.append(self.sign_out_button)

            self.heading = tk.Label(self.canvas, text="Sound Settings", font=("Poppins Bold", 15, "bold"))
            self.heading.pack(anchor=tk.CENTER, pady=(0, 0))
            self.widgets.append(self.heading)

            self.mute_button = RoundedButton(
                self.canvas, text=("MUTE" if self.app.volume.get() != 0 else "UNMUTE"), font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_mute()
            )
            self.mute_button.pack(anchor=tk.CENTER, pady=(0, 0))
            self.widgets.append(self.mute_button)

            self.volume_button = RoundedButton(
                self.canvas, text="", font=("Poppins Bold", 10, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_bg'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_bg'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.volume_button.on_regen = lambda: self.gen_volume_button(self.volume_button)
            self.volume_button.pack(anchor=tk.CENTER, pady=(5, 0))
            self.widgets.append(self.volume_button)
            self.volume_slider: tk.Scale | None = None
            self.volume_text_id = None

            self.hidden_songs_button = RoundedButton(
                self.canvas, text="View Hidden Songs", font=("Poppins Bold", 10, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.hidden_songs_button.pack(anchor=tk.CENTER, pady=(5, 0))
            self.widgets.append(self.hidden_songs_button)

            self.heading = tk.Label(self.canvas, text="Appearance", font=("Poppins Bold", 15, "bold"))
            self.heading.pack(anchor=tk.CENTER, pady=(15, 0))
            self.widgets.append(self.heading)

            self.theme_button = RoundedButton(
                self.canvas, text="", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_change_theme()
            )
            self.theme_button.on_regen = lambda: self.gen_theme_button(self.theme_button)
            self.theme_button.pack(anchor=tk.CENTER, pady=(0, 0))
            self.widgets.append(self.theme_button)

            self.leave_button = RoundedButton(
                self.canvas, text="LEAVE AND APPLY", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_leave_options
            )
            self.leave_button.pack(anchor=tk.CENTER, pady=(30, 0))
            self.widgets.append(self.leave_button)

            self.finish_init()

        def gen_volume_button(self, button):
            text = f"VOLUME: {self.app.volume.get()}%   "
            self.volume_slider = tk.Scale(button, from_=0, to=100, orient="horizontal", variable=self.app.volume, length=100, showvalue=False, bg=button.button_background, bd=0, borderwidth=0, highlightthickness=0)

            bold_font = tk_font.Font(family="Poppins Bold", size=10, weight="bold")

            text_width = bold_font.measure(text)
            total_width = text_width + 100
            start_x = (button.winfo_width() - total_width) / 2
            center_y = button.winfo_height() / 2

            self.volume_text_id = button.create_text((start_x + text_width / 2), center_y, text=text, font=bold_font, anchor="center", tag="button")
            self.volume_slider.place(x=(start_x + text_width + 100 / 2), y=center_y, anchor="center")
            self.volume_slider.configure(command=lambda value: button.itemconfig(self.volume_text_id, text=f"VOLUME: {value}%  "))

        def on_mute(self):
            if self.app.volume.get() != 0:  # Mutes
                self.app.last_volume = self.app.volume.get()
                self.app.volume.set(0)
                self.mute_button.text = "UNMUTE"
            else:  # Unmutes to last volume
                if self.app.last_volume == 0:
                    self.app.last_volume = 50
                self.app.volume.set(self.app.last_volume)
                self.mute_button.text = "MUTE"
            self.volume_button.itemconfig(self.volume_text_id, text=f"VOLUME: {self.app.volume.get()}%  ")
            self.mute_button.generate_button()  # Regenerates mute button to update label (UNMUTE/MUTE)

        def gen_theme_button(self, button):
            first_text = "THEME: "
            second_text = self.app.theme

            bold_font = tk_font.Font(family="Poppins Bold", size=15, weight="bold")
            normal_font = tk_font.Font(family="Poppins Regular", size=13, weight="normal")
            small_font = tk_font.Font(family="Poppins Regular", size=7, weight="normal")

            bold_text_width = bold_font.measure(first_text)
            normal_text_width = normal_font.measure(second_text)
            total_text_width = bold_text_width + normal_text_width
            start_x = (button.winfo_width() - total_text_width) / 2
            center_y = button.winfo_height() / 2

            button.create_text((start_x + bold_text_width / 2), center_y, text=first_text, font=bold_font, anchor="center", tag="button")
            button.create_text((start_x + bold_text_width + normal_text_width / 2), center_y, text=second_text, font=normal_font, anchor="center", tag="button")
            button.create_text(button.winfo_width() - 4, button.winfo_height() + 4, text="Click to cycle", font=small_font, anchor="se", tag="button")

        def on_change_theme(self):
            all_themes = list(self.app.themes.keys())
            current_index = all_themes.index(self.app.theme)
            next_index = current_index + 1 if current_index < len(all_themes) - 1 else 0
            self.app.theme = all_themes[next_index]
            self.app.theme_data = self.app.themes[self.app.theme]

            print(f"Changed theme to: {self.app.theme}")

            self.theme_button.generate_button()  # Regenerates theme button to update theme name

        def save_options(self):
            # Makes sure user is signed in
            if self.app.username is None:
                return

            current_user_data = self.app.get_user_data(self.app.username)
            if current_user_data is None:  # User has no data for some reason
                self.app.username = None  # Log out and allow the user to sign in again
                return

            # Allows support for old accounts (prevents KeyError)
            if "options" not in current_user_data:
                current_user_data['options'] = {}

            current_user_data['options']['volume'] = int(self.app.volume.get())
            current_user_data['options']['theme'] = self.app.theme

            self.app.rewrite_user_data(self.app.username, current_user_data)

        def on_leave_options(self):
            self.save_options()

            if self.caller is not None and self.caller.__class__.__name__ == "PauseMenu":
                self.get().destroy()  # Can't use finish_overlaying_screen since it will pack current screen
                self.caller.canvas.pack(side="top", fill=tk.BOTH, expand=True)  # Packs pause menu
                del self
                return

            # If theme is updated, regenerate last screen (self.caller)
            if self.caller is not None and self.original_theme != self.app.theme:
                # Only update theme if not in game
                self.app.finish_overlaying_screen(self.get(), screen=self.caller.__class__(self.root, self.app).get())  # Recreates class so the themes are updated
                del self
                return

            self.app.finish_overlaying_screen(self.get())  # Screen not specified so screen will not regenerate (saves resources)
            del self

        def on_sign_out(self):
            self.app.username = None
            self.app.finish_overlaying_screen(self.get())
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())
            del self

    class PauseMenu(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, game_name: str, difficulty: str, caller=None):
            super().__init__(root, app, True, False)  # Implements all variables and function from base class "BaseScreen"
            self.caller = caller

            self.logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            self.logo_canvas.pack(pady=(10, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(self.logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            self.logo_label = tk.Label(self.logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": self.logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            self.logo_label.config(image=image_data['updated_image'])
            self.logo_label.pack(anchor="nw", padx=(5, 0), pady=(3, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            self.logo_title = tk.Label(self.logo_canvas, text=f"{game_name} ({difficulty.capitalize()} mode)", font=("Poppins Regular", 15))
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            self.heading = tk.Label(self.canvas, text="GAME PAUSED", font=("Poppins Bold", 17, "bold"))
            self.heading.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(self.heading)

            self.unpause_button = RoundedButton(
                self.canvas, text="UNPAUSE", font=("Poppins Bold", 17, "bold"),
                width=350, height=75, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_unpause_button
            )
            self.unpause_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(self.unpause_button)

            self.options_button = RoundedButton(
                self.canvas, text="OPTIONS", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_options_button
            )
            self.options_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(self.options_button)

            self.leave_game_button = RoundedButton(
                self.canvas, text="LEAVE GAME", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_leave_game_button
            )
            self.leave_game_button.pack(anchor=tk.CENTER, pady=(20, 20))
            self.widgets.append(self.leave_game_button)

            self.song_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            self.song_info_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(self.song_info_canvas)

            self.song_info_row3_canvas = tk.Canvas(self.song_info_canvas, borderwidth=0, highlightthickness=0, bg="#d9d9d9")
            self.song_info_row3_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(self.song_info_row3_canvas)

            self.playing_song_label = tk.Label(self.song_info_row3_canvas, text="Song name - Song Author", font=("Poppins Regular", 12), bg="#d9d9d9")
            self.playing_song_label.pack(anchor="center", side=tk.RIGHT)

            self.skip_button = RoundedButton(
                self.song_info_row3_canvas, font=("", 0, ""),
                width=42, height=42, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/skip.png").convert("RGBA").resize((25, 25))),
                button_background="#737373", button_foreground="#000000",
                button_hover_background="#8c8c8c", button_hover_foreground="#000000",
                button_press_background="#3f3f3f", button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.skip_button.pack(side=tk.RIGHT)
            self.skip_button.generate_button()

            self.skip_label = tk.Label(self.song_info_row3_canvas, text="Skip", font=("Poppins Regular", 12))
            self.skip_label.pack(anchor="center", side=tk.RIGHT, padx=(0, 5))
            self.widgets.append(self.skip_label)

            self.song_info_row2_canvas = tk.Canvas(self.song_info_canvas, borderwidth=0, highlightthickness=0, bg="#d9d9d9")
            self.song_info_row2_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(self.song_info_row2_canvas)

            self.hide_button = RoundedButton(
                self.song_info_row2_canvas, font=("", 0, ""),
                width=42, height=42, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/hide.png").convert("RGBA").resize((25, 25))),
                button_background="#765b5b", button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.hide_button.pack(side=tk.RIGHT)
            self.hide_button.generate_button()

            self.hide_label = tk.Label(self.song_info_row2_canvas, text="Hide Song Permanently", font=("Poppins Regular", 10))
            self.hide_label.pack(anchor="center", side=tk.RIGHT, padx=(0, 5))
            self.widgets.append(self.hide_label)

            self.song_info_row1_canvas = tk.Canvas(self.song_info_canvas, borderwidth=0, highlightthickness=0, bg="#d9d9d9")
            self.song_info_row1_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(self.song_info_row1_canvas)

            self.mute_button = RoundedButton(
                self.song_info_row1_canvas, font=("", 0, ""),
                width=42, height=42, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/mute.png").convert("RGBA").resize((25, 25))),
                button_background="#737373", button_foreground="#000000",
                button_hover_background="#8c8c8c", button_hover_foreground="#000000",
                button_press_background="#3f3f3f", button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            self.mute_button.pack(side=tk.RIGHT)
            self.mute_button.generate_button()

            self.mute_label = tk.Label(self.song_info_row1_canvas, text="Mute", font=("Poppins Regular", 12))
            self.mute_label.pack(anchor="center", side=tk.RIGHT, padx=(0, 5))
            self.widgets.append(self.mute_label)

            self.finish_init()

        def on_unpause_button(self):
            self.app.finish_overlaying_screen(self.get())
            del self

        def on_options_button(self):
            self.canvas.pack_forget()
            self.app.show_overlaying_screen(Screens.SettingsMenu(self.root, self.app, self).get())
            del self

        def on_leave_game_button(self):
            self.app.finish_overlaying_screen(self.get())
            self.app.show_screen(Screens.GameSelection(self.root, self.app).get())
            del self


class Games:
    class MatchingTiles(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, difficulty: str):
            super().__init__(root, app, False, False)  # Implements all variables and function from base class "BaseScreen"

            self.game = "Matching Tiles"
            self.difficulty = difficulty
            print(f"Started Matching Tiles game with difficulty {difficulty}")

            self.canvas.config(bg=self.app.theme_data['accent'])

            self.pause_button = RoundedButton(
                self.canvas, font=("", 0, ""),
                width=50, height=50, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/pause.png").convert("RGBA").resize((35, 35))),
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_pause
            )
            self.pause_button.pack(anchor="ne", pady=(0, 0), side=tk.RIGHT)

            self.finish_init()

        def on_pause(self):
            self.app.show_overlaying_screen(Screens.PauseMenu(self.root, self.app, self.game, self.difficulty).get())


class RoundedButton(tk.Canvas):
    # Adapted from https://stackoverflow.com/a/69092113
    def __init__(self, parent=None, text: str = "", font: tuple = ("Times", 30, "bold"),
                 text_padding: int = 5, radius: int = 25,
                 image: ImageTk = None,
                 button_background="#ffffff", button_foreground="#000000",
                 button_hover_background="#ffffff", button_hover_foreground="#000000",
                 button_press_background="#ffffff", button_press_foreground="#000000",
                 outline_colour: str = "", outline_width: int = 1,
                 command=None, on_regen=None,
                 *args, **kwargs):
        super(RoundedButton, self).__init__(parent, bd=0, highlightthickness=0, *args, **kwargs)
        self.config(bg=self.master["background"])
        self.text = text
        self.font = font
        self.text_padding = text_padding
        self.radius = radius
        self.image = image
        self.button_background = button_background
        self.button_foreground = button_foreground
        self.button_hover_background = button_hover_background
        self.button_hover_foreground = button_hover_foreground
        self.button_press_background = button_press_background
        self.button_press_foreground = button_press_foreground
        self.outline_colour = outline_colour
        self.outline_width = outline_width
        self.command = command
        self.on_regen = on_regen

        self.width = kwargs['width']
        self.height = kwargs['height']

        self.hovering_button = False

        self.button_obj: int | None = None
        self.text_obj: int | None = None
        self.image_obj: int | None = None
        self.generate_button()

        self.game_image = None

        # Binds apply to both button and text
        self.tag_bind("button", "<ButtonPress>", self.on_event)
        self.tag_bind("button", "<ButtonRelease>", self.on_event)
        self.tag_bind("button", "<Enter>", self.on_event)
        self.tag_bind("button", "<Leave>", self.on_event)

        self.bind("<Configure>", self.resize)

    def round_rectangle(self, x1, y1, x2, y2, radius=25, update=False, **kwargs):  # if update is False a new rounded rectangle's id will be returned else updates existing rounded rect.
        # Adapted from https://stackoverflow.com/a/44100075/15993687
        points = [x1 + radius, y1,
                  x1 + radius, y1,
                  x2 - radius, y1,
                  x2 - radius, y1,
                  x2, y1,
                  x2, y1 + radius,
                  x2, y1 + radius,
                  x2, y2 - radius,
                  x2, y2 - radius,
                  x2, y2,
                  x2 - radius, y2,
                  x2 - radius, y2,
                  x1 + radius, y2,
                  x1 + radius, y2,
                  x1, y2,
                  x1, y2 - radius,
                  x1, y2 - radius,
                  x1, y1 + radius,
                  x1, y1 + radius,
                  x1, y1]
        if not update:
            return self.create_polygon(points, **kwargs, smooth=True)
        else:
            self.coords(self.button_obj, points)

    def generate_button(self):
        self.button_obj = self.round_rectangle(
            0, 0, 0, 0, tags="button",
            radius=self.radius, fill=self.button_background,
            outline=self.outline_colour, width=self.outline_width
        )
        self.text_obj = self.create_text(0, 0, text=self.text, tags="button", fill=self.button_foreground, font=self.font, justify=tk.CENTER)
        if self.image is not None:
            self.image_obj = self.create_image(self.width / 2, self.height / 2, image=self.image, tags="button")

        text_rect = self.bbox(self.text_obj)
        if int(self["width"]) < text_rect[2] - text_rect[0]:
            self["width"] = (text_rect[2] - text_rect[0]) + 10
        if int(self["height"]) < text_rect[3] - text_rect[1]:
            self["height"] = (text_rect[3] - text_rect[1]) + 10
        self.resize()

        for widget in self.winfo_children():
            widget.destroy()

        # Custom regen function if provided
        if self.on_regen is not None:
            self.on_regen()

    def resize(self, _=None):
        text_bbox = self.bbox(self.text_obj)
        width = max(self.winfo_width(), text_bbox[2] - text_bbox[0] + self.text_padding) - 1  # -1 pixel size so border is not cut off
        height = max(self.winfo_height(), text_bbox[3] - text_bbox[1] + self.text_padding) - 1  # -1 pixel size so border is not cut off
        self.round_rectangle(0, 0, width, height, self.radius, update=True)
        x = (width - (text_bbox[2] - text_bbox[0])) / 2
        y = (height - (text_bbox[3] - text_bbox[1])) / 2
        self.moveto(self.text_obj, x, y)

    def on_event(self, event):  # Handles all hover and press events
        if event.type == tk.EventType.ButtonPress:
            self.itemconfig(self.button_obj, fill=self.button_press_background)
            self.itemconfig(self.text_obj, fill=self.button_press_foreground)
        elif event.type == tk.EventType.ButtonRelease:
            self.itemconfig(self.button_obj, fill=self.button_hover_background)
            self.itemconfig(self.text_obj, fill=self.button_hover_foreground)
            if self.command is not None and self.hovering_button:  # Only clicks when hovering
                self.command()
        elif event.type == tk.EventType.Enter:
            self.hovering_button = True
            self.itemconfig(self.button_obj, fill=self.button_hover_background)
            self.itemconfig(self.text_obj, fill=self.button_hover_foreground)
        elif event.type == tk.EventType.Leave:
            self.hovering_button = False
            self.itemconfig(self.button_obj, fill=self.button_background)
            self.itemconfig(self.text_obj, fill=self.button_foreground)


if __name__ == "__main__":
    pyglet.options["win32_gdi_font"] = True
    pyglet.font.add_file("assets/fonts/Poppins-Bold.ttf")
    pyglet.font.add_file("assets/fonts/Poppins-Regular.ttf")

    root = tk.Tk()
    RecollectApp(root)
