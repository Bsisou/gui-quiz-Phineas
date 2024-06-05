import json
import os
import tkinter as tk
import tkinter.font as tk_font
import hashlib
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

        # Overriding default font if custom font does not work
        self.defaultFont = tk_font.nametofont("TkDefaultFont")
        self.defaultFont.configure(family="Calibri")

        self.background_image_full = Image.open("assets/background.png")

        self.blob = Image.open("assets/blob.png")

        self.current_screen = None
        self.show_screen(Screens.Homepage(self.root, self).get())

        self.root.mainloop()

    def get_background(self) -> Image:
        return self.background_image_full

    def get_blob(self, width, height, angle) -> (ImageTk.PhotoImage, Image):
        blob = self.blob.rotate(angle, Image.NEAREST, expand=True).resize((width, height), 1)
        return ImageTk.PhotoImage(blob)

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

        with open("data.json", "r+") as data_file:
            data = json.load(data_file)
            data['users'][username] = {
                "password": self.encrypt_password(password)
            }
            data_file.seek(0)
            data_file.truncate()
            json.dump(data, data_file, indent=2)

    def rewrite_user_data(self, username, user_data):
        self.check_if_data_file_exists()

        with open("data.json", "r+") as data_file:
            data = json.load(data_file)
            data['users'][username] = user_data
            data_file.seek(0)
            data_file.truncate()
            json.dump(data, data_file, indent=2)

    def show_screen(self, screen):
        if self.current_screen is not None:
            self.current_screen.pack_forget()
            self.current_screen.destroy()
            del self.current_screen
        screen.pack(side="top", fill=tk.BOTH, expand=True)
        self.current_screen = screen

    @staticmethod
    def add_corners(image, radius):
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

        # self.canvas.pack(side="top", fill=tk.BOTH, expand=True)  # can be removed? (pack first so coordinates work)
        self.canvas.grid_columnconfigure(0, weight=1)

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
            x1, y1 = widget.winfo_x(), widget.winfo_y()
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
            self.logo_label.grid(row=0, column=0, pady=(50, 0), sticky="")
            self.transparent_images.append(image_data)
            del logo_image

            self.start_button = RoundedButton(
                self.canvas, text="START", font=("Poppins Bold", 20, "bold"),
                width=350, height=75, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_click_start
            )
            self.start_button.grid(row=1, column=0, pady=(30, 0), sticky="")
            self.widgets.append(self.start_button)

            self.options_button = RoundedButton(
                self.canvas, text="OPTIONS", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_click_options
            )
            self.options_button.grid(row=2, column=0, pady=(20, 0), sticky="")
            self.widgets.append(self.options_button)

            self.quit_button = RoundedButton(
                self.canvas, text="QUIT", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=lambda: root.destroy()
            )
            self.quit_button.grid(row=3, column=0, pady=(20, 20), sticky="")
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
            ...
            # self.destroy()

    class Login(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"

            self.logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0, bg="#53afc8")
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

            self.logo_title = tk.Label(self.logo_canvas, text="Sign In", font=("Poppins Regular", 15), bg="#53afc8")
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            self.back_button = RoundedButton(
                self.canvas, text="BACK", font=("Poppins Bold", 15, "bold"),
                width=210, height=50, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_back
            )
            self.back_button.pack(pady=(5, 0), padx=(10, 0), anchor="nw")
            self.widgets.append(self.back_button)

            self.heading = tk.Label(self.canvas, text="Sign In", font=("Poppins Bold", 15, "bold"), bg="#53afc8")
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

            self.error_message = tk.Label(self.canvas, text="", font=("Poppins Regular", 9), fg="red", bg="#53afc8")
            self.error_message.pack(anchor=tk.CENTER, pady=(5, 10))
            self.widgets.append(self.error_message)

            self.sign_in_button = RoundedButton(
                self.canvas, text="SIGN IN", font=("Poppins Bold", 15, "bold"),
                width=250, height=50, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_sign_in
            )
            self.sign_in_button.pack(anchor=tk.CENTER, pady=(5, 5))
            self.widgets.append(self.sign_in_button)

            self.finish_init()

        def on_back(self):
            self.destroy()
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())

        def check_met_criteria(self):
            username_empty = self.username_entry.get().strip() in ["Username", ""]
            password_empty = self.password_entry.get().strip() in ["Password", ""]
            if username_empty or password_empty:
                if username_empty:
                    self.username_entry.config(bg="#f77b7a")
                if password_empty:
                    self.password_entry.config(bg="#f77b7a")
                self.error_message.config(text="Cannot have blank username or password.")
                return False

            if len(self.password_entry.get()) <= 7:
                self.password_entry.config(bg="#f77b7a")
                self.error_message.config(text="Password must be greater than 7 characters.")
                return False

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
                self.password_entry.config(bg="#f77b7a")
                self.error_message.config(text="Password must have a number, uppercase, and lowercase characters.")
                return False

            return True

        def on_sign_in(self):
            self.error_message.config(text="", image="")
            self.root.focus()  # Unselects entry boxes

            if not self.check_met_criteria():
                self.update_widgets_background(specific_widget=self.error_message)
                return

            entered_username = self.username_entry.get().strip().lower()
            entered_password = self.password_entry.get()

            user_data = self.app.get_user_data(entered_username)
            if user_data is None:
                self.app.add_new_user_data(entered_username, entered_password)
            elif self.app.encrypt_password(entered_password) != user_data['password']:
                self.password_entry.config(bg="#f77b7a")
                self.error_message.config(text="Incorrect password.")
                self.update_widgets_background(specific_widget=self.error_message)
                return

            # Password is correct / Account created
            self.app.username = entered_username

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

            self.logo_canvas = tk.Canvas(self.canvas, background="#53afc8", borderwidth=0, highlightthickness=0)
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

            self.logo_title = tk.Label(self.logo_canvas, text="Gamemodes", font=("Poppins Regular", 15), bg="#53afc8")
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            self.settings_button = RoundedButton(
                self.logo_canvas, font=("", 0, ""),
                width=50, height=50, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/settings.png").convert("RGBA").resize((35, 35))),
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_settings_click
            )
            self.settings_button.pack(anchor="ne", pady=(0, 0), side=tk.RIGHT)
            self.widgets.append(self.settings_button)

            self.outer_frame = tk.Frame(self.canvas, bd=0, borderwidth=0, highlightthickness=0, bg="#53b0c8")
            self.outer_frame.pack(fill=tk.BOTH, expand=True)

            self.inner_canvas = tk.Canvas(self.outer_frame, bg="#53b0c8", bd=0, borderwidth=0, highlightthickness=0)
            self.inner_canvas.pack(anchor=tk.CENTER, side=tk.LEFT, fill=tk.Y, expand=True)

            self.scrollbar = tk.Scrollbar(self.outer_frame, orient=tk.VERTICAL, command=self.inner_canvas.yview)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.inner_canvas.configure(yscrollcommand=self.scrollbar.set)
            self.root.update()
            self.inner_canvas.bind("<Configure>", lambda e: self.inner_canvas.configure(scrollregion=self.inner_canvas.bbox("all")))

            self.game_button_canvas = tk.Canvas(self.inner_canvas, bg="#53b0c8", bd=0, borderwidth=0, highlightthickness=0)

            self.game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg="#53b0c8",
                button_background="#617eff", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_settings_click
            )
            self.game_button.on_regen = lambda: self.after_game_button(self.game_button, self.app.get_background())
            self.game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.game_button.on_regen()

            self.game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg="#53b0c8",
                button_background="#617eff", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_settings_click
            )
            self.game_button.on_regen = lambda: self.after_game_button(self.game_button, self.app.get_background())
            self.game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.game_button.on_regen()

            self.game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg="#53b0c8",
                button_background="#617eff", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_settings_click
            )
            self.game_button.on_regen = lambda: self.after_game_button(self.game_button, self.app.get_background())
            self.game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            self.game_button.on_regen()

            self.game_button_window = self.inner_canvas.create_window((0, 0), window=self.game_button_canvas, anchor="nw")

            self.inner_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            self.game_button_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            for child in self.game_button_canvas.children.values():
                child.bind("<MouseWheel>", self.on_mouse_wheel)

            # Fixes game button canvas getting cut off
            self.root.update()
            x1, y1, x2, y2 = self.inner_canvas.bbox("all")
            self.inner_canvas.config(width=x2 - x1, height=y2 - y1)

            self.finish_init()

        def after_game_button(self, button, image: Image):
            button.game_image = ImageTk.PhotoImage(self.app.add_corners(image.convert("RGBA").resize((130, 130)), 9))
            button.create_image(10, 10, image=button.game_image, anchor="nw", tag="button")
            button.create_text(150, 20, text="Game Name", fill="black", font=("Poppins Bold", 15, "bold"), anchor="nw", tag="button")
            button.create_text(150, 60, text="Description", fill="black", font=("Poppins Regular", 12), anchor="nw", tag="button")

        def on_mouse_wheel(self, event):
            self.inner_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_settings_click(self):
            print("Pressed settings button")


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
            self.image_obj = self.create_image(self.winfo_width() / 2, self.winfo_height() / 2, image=self.image, tags="button")

        text_rect = self.bbox(self.text_obj)
        if int(self["width"]) < text_rect[2] - text_rect[0]:
            self["width"] = (text_rect[2] - text_rect[0]) + 10
        if int(self["height"]) < text_rect[3] - text_rect[1]:
            self["height"] = (text_rect[3] - text_rect[1]) + 10
        self.resize()

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

    def on_event(self, event):
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
