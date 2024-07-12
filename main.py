import contextlib
import hashlib
import json
from ctypes import windll
import math
import os
import random
import time
import tkinter as tk
import tkinter.font as tk_font
import pygame

# Install from requirements.txt using command: pip install -r requirements.txt
import psutil  # for memory usage only - pip install psutil
import pyglet  # pip install pyglet
from PIL import Image, ImageTk, ImageDraw, ImageOps  # pip install pillow


# https://www.no-copyright-music.com/
# Command to cut and fade out from 0 to 90 sec
# ffmpeg -ss 00:00:00 -to 00:01:30 -i "inputpath" -af "afade=t=out:st=83:d=5" -c:a libmp3lame "outputpath"

# Get memory usage
def get_memory():
    print(f"Memory usage: {psutil.Process(os.getpid()).memory_info().rss / 1e+6} MB")


# Main app that runs including screen management, data handling, etc.
class RecollectApp:
    def __init__(self, root: tk.Tk):
        # Set up root window
        self.root = root
        self.root.title("Recollect")
        self.root.geometry("750x563")  # Same ratio as 1000 x 750
        self.root.minsize(750, 563)
        self.username = None

        pygame.init()
        pygame.mixer.init()
        self.MUSIC_END_EVENT = pygame.USEREVENT + 1
        pygame.mixer.music.set_endevent(self.MUSIC_END_EVENT)
        self.music_playing = None
        self.hidden_music = []

        self.data_file = "data.json"

        # Themes
        self.themes = {
            "Fruity (Default)": {
                "img_bg": "background.png",
                "img_blob": "blob.png",
                "accent": "#53B0C8",
                "accent1": "#5DE6CD",
                "accent2": "#306BBB",
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
                "accent1": "#FF3F3F",
                "accent2": "#FF7F7F",
                "text": "black",
                "outline": "black",
                "btn_bg": "#F85F7B",
                "btn_hvr": "#C44B61",
                "btn_prs": "#772D3B",
                "btn_warn_hvr": "#400c13",
                "btn_warn_prs": "#8d1c2a",
            }
        }

        # Game
        self.games = {
            "Matching Tiles": Games.MatchingTiles
        }

        # Options

        # Volume
        self.volume = tk.IntVar(value=50)
        self.last_volume = 50

        # Current theme
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

        # Screen management
        self.current_screen = None
        # Show homepage
        self.show_screen(Screens.Homepage(self.root, self).get())

        # Main window loop
        self.root.mainloop()

    # Get background image
    def get_background(self) -> Image:
        return Image.open(f"assets/{self.theme_data['img_bg']}")

    # Get blob image and resize and rotate
    def get_blob(self, width, height, angle) -> (ImageTk.PhotoImage, Image):
        blob = Image.open(f"assets/{self.theme_data['img_blob']}").rotate(angle, Image.NEAREST, expand=True).resize((width, height), 1)
        return ImageTk.PhotoImage(blob)

    # Get coordinates relative to the root window
    @staticmethod
    def get_coordinates_relative_window(widget):
        return widget.winfo_rootx() - root.winfo_rootx(), widget.winfo_rooty() - root.winfo_rooty()

    # Encrypt a string
    @staticmethod
    def encrypt_str(raw: str):
        sha256 = hashlib.sha256()
        sha256.update(raw.encode('utf-8'))
        return sha256.hexdigest()

    # Encrypt the password 256 times
    def encrypt_password(self, password: str):
        for _ in range(256):  # Encrypt 256 times
            password = self.encrypt_str(password)
        return password

    # Checks if the data file exists
    def check_if_data_file_exists(self):
        # Check if data file exists
        if not os.path.exists(self.data_file):
            with open("data.json", "w+") as data_file:
                json.dump({"users": {}}, data_file)

    # Gets user data from username
    def get_user_data(self, username):
        self.check_if_data_file_exists()

        try:
            with open("data.json", "r+") as data_file:
                data = json.load(data_file)
                return data['users'][username]
        except KeyError:
            return None

    # Add new user data on account creation
    def add_new_user_data(self, username, password):
        self.check_if_data_file_exists()
        user_data = {
            "password": self.encrypt_password(password),
            "options": {
                "volume": int(self.volume.get()),
                "theme": self.theme
            }
        }
        self.rewrite_user_data(username, user_data)
        return user_data

    # Delete and rewrite the user data
    def rewrite_user_data(self, username, user_data):
        self.check_if_data_file_exists()

        with open("data.json", "r+") as data_file:
            data = json.load(data_file)
            data['users'][username] = user_data
            data_file.seek(0)
            data_file.truncate()
            json.dump(data, data_file, indent=2)

    # Apply changes on sign in for a user
    def apply_user_options(self, user_data):
        # Apply account options (theme, volume, etc.) if any
        try:
            self.volume.set(int(user_data['options']['volume']))
        except KeyError:
            print("User has no volume data, continuing with existing options")
        try:
            self.theme = user_data['options']['theme']
            self.theme_data = self.themes[self.theme]
        except KeyError:
            print("User has no theme data, continuing with existing options")
        try:
            self.hidden_music = user_data['options']['hidden_music']
        except KeyError:
            print("User has no music data, continuing with existing options")

    # Get the game data for a user
    def get_game_data(self, username, game):
        user_data = self.get_user_data(username)
        if user_data is None:
            return  # Cannot save score as not logged in, should not happen

        # Create empty dicts if empty
        if "game_data" not in list(user_data.keys()):
            user_data['game_data'] = {}
        if game not in list(user_data['game_data'].keys()):
            user_data['game_data'][game] = {}

        return user_data['game_data'][game]

    # Change the overall score for a user after a game
    def change_game_user_data(self, username, game, game_data, difficulty, score):
        user_data = self.get_user_data(username)
        if user_data is None:
            return  # Cannot save score as not logged in, should not happen

        # Make overall score if empty
        if "overall_score" not in list(user_data.keys()):
            user_data['overall_score'] = 0
        original_overall_score = user_data['overall_score']
        # Get score relative to "easy mode", since user may be penalised for playing easy mode after hard.
        relative_score = score
        if difficulty == "hard":
            relative_score = score / 4  # Hard should be 4 times harder than easy
        elif difficulty == "normal":
            relative_score = score / 2  # Normal should be 2 times harder than easy
        # Change overall score based on 2 curves
        difference = relative_score - original_overall_score
        print(f"Difference in scores: {difference}")
        if difference < 0:  # If score is worse
            overall_change = round(0.25 * difference, 1)  # Use curve y=0.25x for loss
        else:  # If score is better
            overall_change = round(0.5 * difference, 1)  # Use curve y=0.5x for gain
        print(f"Change of {overall_change} score")
        user_data['overall_score'] = round(user_data['overall_score'] + overall_change, 1)

        # Create empty game_data dicts if empty
        if "game_data" not in list(user_data.keys()):
            user_data['game_data'] = {}
        if game not in list(user_data['game_data'].keys()):
            user_data['game_data'][game] = {}
        # Write game data
        user_data['game_data'][game] = game_data

        self.rewrite_user_data(username, user_data)

        return overall_change, original_overall_score, user_data['overall_score']

    # Destroy the old screen and show the new screen
    def show_screen(self, screen: tk.Canvas):
        if self.current_screen is not None:
            self.current_screen.pack_forget()
            self.current_screen.destroy()
            del self.current_screen
        screen.pack(side="top", fill=tk.BOTH, expand=True)
        self.current_screen = screen

    # Unpack (not destroy) the old screen and show the overlaying screen
    def show_overlaying_screen(self, overlaying_screen: tk.Canvas):
        self.current_screen.pack_forget()
        overlaying_screen.pack(side="top", fill=tk.BOTH, expand=True)

    # Destroy the overlaying screen and repack the old screen
    def finish_overlaying_screen(self, overlaying_screen: tk.Canvas, screen=None):
        overlaying_screen.destroy()
        if screen is None:  # Do not update screen if None
            self.current_screen.pack(side="top", fill=tk.BOTH, expand=True)
        else:  # Update screen if screen is provided
            self.show_screen(screen)

    # Add transparent corners to an image
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


# Creates a base screen with background and blobs which can be implemented in screens
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

    # Should be called after initialisation is finished
    def finish_init(self):
        self.setup_keypress_listener()  # Sets up listener for key releases
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

    # Returns the screen
    def get(self):
        return self.canvas

    def setup_keypress_listener(self):
        self.root.bind("<KeyRelease>", lambda e: self.on_keyboard_press(e.keysym.lower()))

    def on_keyboard_press(self, key):
        pass

    # Updates the background
    def update_background(self, _=None):
        self.canvas.delete("background")
        # Adjust background stretching etc.
        width, height = self.root.winfo_width(), self.root.winfo_height()
        del self.current_background
        self.current_background = self.app.get_background().resize((width, height), 1)
        self.canvas.bg_image = ImageTk.PhotoImage(self.current_background)  # Must be in class scope
        self.canvas.create_image(0, 0, image=self.canvas.bg_image, anchor="nw", tags="background")  # Don't make one-liner

    # Places blob at coordinates
    def place_blob(self, size: int, angle: int | float, x: int | float, y: int | float, anchor):
        blob_tk = self.app.get_blob(size, size, angle)
        self._blobs_tk.append(blob_tk)  # Must be in class scope
        self.canvas.create_image(x, y, image=self._blobs_tk[-1], anchor=anchor, tags="blob")  # Don't make one-liner

    # Update location/size of blobs
    def update_blobs(self, _=None):
        self.canvas.delete("blob")
        # Clears previous blobs from memory
        del self._blobs_tk
        self._blobs_tk = []

        # all sizes minimum 100px
        self.place_blob(max(int(root.winfo_width() * 0.3333), 100), -30, -60, root.winfo_height() * 0.7, "w")  # size=33% of width, x=60, y=70% of height
        self.place_blob(max(int(root.winfo_width() * 0.2666), 100), 25, root.winfo_width() + 90, root.winfo_height() * 0.25, "e")  # size=27% of width, x=100% of height + 90px, y=25% of height
        self.place_blob(max(int(root.winfo_width() * 0.4), 100), 150, root.winfo_width() + 55, root.winfo_height() - 60, "e")  # size=40% of width, x=100% of height + 55px, y=100% of height - 60%

    # Updates the background of all transparent images
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

    # Updates the background of all widgets that have some transparency
    def update_widgets_background(self, _=None, specific_widget=None):
        if self.has_background is False or self.current_background is None:  # No background or current background not showing
            return

        # Adjust each button background
        self.canvas.update_idletasks()  # Updates coordinates

        update_widgets = self.widgets if specific_widget is None else [specific_widget]
        for widget in update_widgets:
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

    # Destroys the screen
    def destroy(self):
        self.canvas.unbind("<Configure>")
        del self


class Screens:
    class Homepage(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"

            accessibility_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            accessibility_info_canvas.pack(padx=(0, 3), anchor="nw", fill="x")
            self.widgets.append(accessibility_info_canvas)

            accessibility_info_label = tk.Label(accessibility_info_canvas, text="Accessibility: Press the underlined key for quick navigation", font=("Poppins Regular", 7))
            accessibility_info_label.pack(anchor="n", side=tk.RIGHT)
            self.widgets.append(accessibility_info_label)

            logo_image = Image.open("assets/logo.png").convert("RGBA").resize((370, 121))  # Must be multiple of 935 x 306
            logo_label = tk.Label(self.canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            logo_label.config(image=image_data['updated_image'])
            logo_label.pack(anchor=tk.CENTER, pady=(40, 0))
            self.transparent_images.append(image_data)
            del logo_image

            heading = tk.Label(self.canvas, text="A memory and cognitive skill trainer", font=("Poppins Bold", 15, "bold"))
            heading.pack(anchor=tk.CENTER, pady=(10, 0))
            self.widgets.append(heading)

            start_button = RoundedButton(
                self.canvas, text="START", font=("Poppins Bold", 20, "bold"),
                width=350, height=75, radius=29, text_padding=0, underline_index=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_start_button
            )
            start_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(start_button)

            options_button = RoundedButton(
                self.canvas, text="OPTIONS", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0, underline_index=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_options_button
            )
            options_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(options_button)

            quit_button = RoundedButton(
                self.canvas, text="QUIT", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: root.destroy()
            )
            quit_button.pack(anchor=tk.CENTER, pady=(20, 20))
            self.widgets.append(quit_button)

            self.finish_init()

        def on_keyboard_press(self, key):
            if key == "s":
                self.root.unbind("<KeyRelease>")
                self.on_start_button()
            elif key == "o":
                self.root.unbind("<KeyRelease>")
                self.on_options_button()

        def on_start_button(self):
            self.destroy()
            if self.app.username is None or self.app.get_user_data(self.app.username) is None:  # Not logged in or username not in data for some reason
                self.app.username = None
                self.app.show_screen(Screens.Login(self.root, self.app).get())
            else:  # User is already signed in
                user_data = self.app.get_user_data(self.app.username)
                if user_data is not None:  # Apply user data if it exists
                    self.app.apply_user_options(user_data)
                self.app.show_screen(Screens.GameSelection(self.root, self.app).get())

        def on_options_button(self):
            self.app.show_overlaying_screen(Screens.SettingsMenu(self.root, self.app, self).get())

    class Login(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"

            accessibility_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            accessibility_info_canvas.pack(padx=(0, 3), anchor="nw", fill="x")
            self.widgets.append(accessibility_info_canvas)

            accessibility_info_label = tk.Label(accessibility_info_canvas, text="Accessibility: Use tab and enter for quick navigation", font=("Poppins Regular", 7))
            accessibility_info_label.pack(anchor="n", side=tk.RIGHT)
            self.widgets.append(accessibility_info_label)

            logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            logo_canvas.pack(pady=(0, 0), padx=(10, 0), anchor="nw")
            self.widgets.append(logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            logo_label = tk.Label(logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            logo_label.config(image=image_data['updated_image'])
            logo_label.pack(anchor="nw", padx=(5, 0), pady=(0, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            logo_title = tk.Label(logo_canvas, text="Sign Up or Log In", font=("Poppins Regular", 15))
            logo_title.pack(anchor="nw", pady=(19, 0), side=tk.LEFT)
            self.widgets.append(logo_title)

            back_button = RoundedButton(
                self.canvas, text="BACK", font=("Poppins Bold", 15, "bold"),
                width=210, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_back_button
            )
            back_button.pack(pady=(5, 0), padx=(10, 0), anchor="nw")
            self.widgets.append(back_button)

            self.heading = tk.Label(self.canvas, text="Sign Up or Log In", font=("Poppins Bold", 15, "bold"))
            self.heading.pack(anchor=tk.CENTER, pady=(10, 10))
            self.widgets.append(self.heading)

            self.username_entry = tk.Entry(self.canvas, font=("Poppins Regular", 11), width=25)
            self.username_entry.pack(anchor=tk.CENTER, pady=(5, 5))
            self.username_entry.bind("<FocusIn>", lambda event: self.on_focusin_entry(self.username_entry, "Username"))
            self.username_entry.bind("<FocusOut>", lambda event: self.on_focusout_entry(self.username_entry, "Username"))
            self.username_entry.bind("<Return>", self.on_next)
            self.on_focusout_entry(self.username_entry, "Username")

            self.password_entry = tk.Entry(self.canvas, font=("Poppins Regular", 11), width=25)
            self.password_entry.bind("<FocusIn>", lambda event: self.on_focusin_entry(self.password_entry, "Password"))
            self.password_entry.bind("<FocusOut>", lambda event: self.on_focusout_entry(self.password_entry, "Password"))
            self.password_entry.bind("<Return>", self.on_sign_in)
            self.on_focusout_entry(self.password_entry, "Password")

            self.error_message = tk.Label(self.canvas, text="", font=("Poppins Regular", 9), fg="red")
            self.error_message.pack(anchor=tk.CENTER, pady=(5, 10))
            self.widgets.append(self.error_message)

            self.next_button = RoundedButton(
                self.canvas, text="NEXT", font=("Poppins Bold", 15, "bold"),
                width=250, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_next
            )
            self.next_button.pack(anchor=tk.CENTER, pady=(5, 5))
            self.widgets.append(self.next_button)

            self.finish_init()

        def on_keyboard_press(self, key):
            if key == "escape":
                self.root.unbind("<KeyRelease>")
                self.on_back_button()

        def on_back_button(self):
            self.destroy()
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())

        def check_username_criteria(self):
            # Check if any entry is empty
            username_empty = self.username_entry.get().strip() in ["Username", ""]
            if username_empty:
                self.username_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Cannot have blank username.")
                return False

            # Check username criteria
            criteria_met = True
            for i in self.username_entry.get():
                if not i.isalnum() and i not in ["_"]:  # Invalid character used
                    criteria_met = False
                    break
            if not criteria_met:
                self.username_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Username can only be alpha numerical.")
                return False

            return True

        # Check if username and password criteria are met
        def check_password_criteria(self):
            # Check if any entry is empty
            password_empty = self.password_entry.get().strip() in ["Password", ""]
            if password_empty:
                self.password_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Cannot have blank password.")
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

        # Runs when continue button is pressed
        def on_next(self, _=None):
            self.error_message.config(text="", image="")
            self.update_widgets_background(specific_widget=self.error_message)
            self.root.focus()  # Unselects entry boxes

            entered_username = self.username_entry.get().strip().lower()  # Lowercase usernames only

            user_data = self.app.get_user_data(entered_username)
            if user_data is None:  # Account does not exist
                if not self.check_username_criteria():  # Username criteria is not met
                    self.update_widgets_background(specific_widget=self.error_message)
                    return
                # Username criteria is met
                self.heading.config(text="Create an Account")
                self.next_button.text = "CREATE ACCOUNT"

            else:  # Account exists
                self.heading.config(text="Sign In")
                self.next_button.text = "SIGN IN"
            self.update_widgets_background(specific_widget=self.heading)  # Update heading background

            # Change continue button callback and regen to update text
            self.next_button.command = self.on_sign_in
            self.next_button.generate_button()

            # Unpack widgets below so password entry can be packed
            self.error_message.pack_forget()
            self.next_button.pack_forget()
            self.password_entry.pack(anchor=tk.CENTER, pady=(5, 5))
            self.error_message.pack(anchor=tk.CENTER, pady=(5, 10))
            self.next_button.pack(anchor=tk.CENTER, pady=(5, 5))

            self.password_entry.focus()

        # Runs when sign in button is pressed
        def on_sign_in(self, _=None):
            self.error_message.config(text="", image="")
            self.update_widgets_background(specific_widget=self.error_message)
            self.root.focus()  # Unselects entry boxes

            entered_username = self.username_entry.get().strip().lower()  # Lowercase usernames only
            entered_password = self.password_entry.get()

            user_data = self.app.get_user_data(entered_username)
            if user_data is None:  # Account does not exist
                if not self.check_password_criteria() or not self.check_username_criteria():  # Both criteria are not met
                    self.update_widgets_background(specific_widget=self.error_message)
                    return
                # Both criteria are met
                user_data = self.app.add_new_user_data(entered_username, entered_password)  # Create new account

            elif self.app.encrypt_password(entered_password) != user_data['password']:  # Account exists, but wrong password
                self.password_entry.config(bg=self.app.theme_data['btn_warn_prs'])
                self.error_message.config(text="Incorrect password.")
                self.update_widgets_background(specific_widget=self.error_message)
                return

            # Password is correct / Account created
            self.app.username = entered_username

            # Apply options from user data
            self.app.apply_user_options(user_data)

            # Move to next screen
            self.destroy()
            self.app.show_screen(Screens.GameSelection(self.root, self.app).get())

        # Removes hinting when entry is focused
        def on_focusin_entry(self, entry: tk.Entry, hint: str):
            entry.config(fg="black", bg="white")
            if hint == "Password":
                entry.config(show="*")
            if entry.get().strip() in ["Username", "Password"]:
                entry.delete(0, tk.END)

            if hint == "Username":  # Runs if user decides to change username after continuing
                self.password_entry.pack_forget()  # Unpack password entry

                # Update heading text and background
                self.heading.config(text="Sign Up or Log In")
                self.update_widgets_background(specific_widget=self.heading)  # Update heading background

                # Change continue button callback and regen to update text
                self.next_button.text = "NEXT"
                self.next_button.command = self.on_next
                self.next_button.generate_button()

        # Shows hinting when empty entry is unfocused
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

            accessibility_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            accessibility_info_canvas.pack(padx=(0, 3), anchor="nw", fill="x")
            self.widgets.append(accessibility_info_canvas)

            accessibility_info_label = tk.Label(accessibility_info_canvas, text="Accessibility: Press the corresponding number for quick navigation, press O for options", font=("Poppins Regular", 7))
            accessibility_info_label.pack(anchor="n", side=tk.RIGHT)
            self.widgets.append(accessibility_info_label)

            logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            logo_canvas.pack(pady=(0, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            logo_label = tk.Label(logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            logo_label.config(image=image_data['updated_image'])
            logo_label.pack(anchor="nw", padx=(5, 0), pady=(0, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            self.logo_title = tk.Label(logo_canvas, text="Gamemodes", font=("Poppins Regular", 15))
            self.logo_title.pack(anchor="nw", pady=(19, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            settings_button = RoundedButton(
                logo_canvas, font=("", 0, ""),
                width=50, height=50, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/settings.png").convert("RGBA").resize((35, 35))),
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_settings_click
            )
            settings_button.pack(anchor="ne", pady=(12, 0), side=tk.RIGHT)
            self.widgets.append(settings_button)

            self.game_outer_frame = tk.Frame(self.canvas, bd=0, borderwidth=0, highlightthickness=0, bg=self.app.theme_data['accent'])
            self.game_outer_frame.pack(fill=tk.BOTH, expand=True)

            self.game_inner_canvas = tk.Canvas(self.game_outer_frame, bg=self.app.theme_data['accent'], bd=0, borderwidth=0, highlightthickness=0)
            self.game_inner_canvas.pack(anchor=tk.CENTER, side=tk.LEFT, fill=tk.Y, expand=True)

            scrollbar = tk.Scrollbar(self.game_outer_frame, orient=tk.VERTICAL, command=self.game_inner_canvas.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.game_inner_canvas.configure(yscrollcommand=scrollbar.set)
            self.root.update()
            self.game_inner_canvas.bind("<Configure>", lambda e: self.game_inner_canvas.configure(scrollregion=self.game_inner_canvas.bbox("all")))

            self.game_button_canvas = tk.Canvas(self.game_inner_canvas, bg=self.app.theme_data['accent'], bd=0, borderwidth=0, highlightthickness=0)

            game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_game_select("Matching Tiles")
            )
            game_button.on_regen = lambda: self.after_game_button(game_button, Image.open("assets/matching_tiles/icon.png"), "MATCHING TILES (1)", "Flip over and memorise pairs of cards, trying to find matching images.\nEnhances concentration and memory skills.")
            game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            game_button.on_regen()

            game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            game_button.on_regen = lambda: self.after_game_button(game_button, self.app.get_background(), "Coming soon...", "")
            game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            game_button.on_regen()

            game_button = RoundedButton(
                self.game_button_canvas, font=("", 0, ""),
                width=600, height=150, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=None
            )
            game_button.on_regen = lambda: self.after_game_button(game_button, self.app.get_background(), "Coming soon...", "")
            game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            game_button.on_regen()

            self.game_inner_canvas.create_window((0, 0), window=self.game_button_canvas, anchor="nw")

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

            back_button = RoundedButton(
                self.difficulty_canvas, text="BACK", font=("Poppins Bold", 15, "bold"),
                width=210, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_difficulty_back
            )
            back_button.pack(pady=(5, 0), padx=(10, 0), anchor="nw")

            heading = tk.Label(self.difficulty_canvas, text="Select a difficulty level", font=("Poppins Bold", 15, "bold"), bg=self.app.theme_data['accent'])
            heading.pack(anchor=tk.CENTER, pady=(10, 0))

            difficulty_button = RoundedButton(
                self.difficulty_canvas, font=("", 0, ""),
                width=450, height=85, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_difficulty_select("easy")
            )
            difficulty_button.on_regen = lambda: self.after_difficulty_button(difficulty_button, "Easy", "Match simple images of random categories\nEnhances memory (1x)")
            difficulty_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            difficulty_button.on_regen()

            difficulty_button = RoundedButton(
                self.difficulty_canvas, font=("", 0, ""),
                width=450, height=85, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_difficulty_select("normal")
            )
            difficulty_button.on_regen = lambda: self.after_difficulty_button(difficulty_button, "Normal", "Match images of the same category\nEnhances memory (2x)")
            difficulty_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            difficulty_button.on_regen()

            difficulty_button = RoundedButton(
                self.difficulty_canvas, font=("", 0, ""),
                width=450, height=85, radius=29, text_padding=0,
                bg=self.app.theme_data['accent'],
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_difficulty_select("hard")
            )
            difficulty_button.on_regen = lambda: self.after_difficulty_button(difficulty_button, "Hard", "Match many images of the same category\nEnhances memory (4x)")
            difficulty_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))
            difficulty_button.on_regen()

            self.finish_init()

        def on_keyboard_press(self, key):
            if key == "o":
                self.root.unbind("<KeyRelease>")
                self.on_settings_click()
            elif self.game_button_canvas.winfo_ismapped():
                if key == "1":
                    self.on_game_select("Matching Tiles")
            elif self.difficulty_canvas.winfo_ismapped():  # If difficulty screen is showing
                if key in ["escape", "b"]:
                    self.on_difficulty_back()
                elif key in ["e", "1"]:
                    self.on_difficulty_select("easy")
                elif key in ["n", "2"]:
                    self.on_difficulty_select("normal")
                elif key in ["h", "3"]:
                    self.on_difficulty_select("hard")

        # Generates the game button
        def after_game_button(self, button, image: Image, name: str, description: str):
            button.game_image = ImageTk.PhotoImage(self.app.add_corners(image.convert("RGBA").resize((130, 130)), 9))
            button.create_image(10, 10, image=button.game_image, anchor="nw", tag="button")
            button.create_text(150, 10, text=name, fill=self.app.theme_data['text'], font=("Poppins Bold", 15, "bold"), anchor="nw", tag="button")
            button.create_text(150, 50, text=description, fill=self.app.theme_data['text'], font=("Poppins Regular", 10), width=button.width - 160, anchor="nw", tag="button")

        # Generates the difficulty button
        def after_difficulty_button(self, button, title: str, text: str):
            button.create_text(10, 0, text=title, fill=self.app.theme_data['text'], font=("Poppins Bold", 14, "bold"), anchor="nw", tag="button")
            button.create_text(10, 33, text=text, fill=self.app.theme_data['text'], font=("Poppins Regular", 9), width=button.width - 10, anchor="nw", tag="button")
            button.create_line(10, 30, 25, 30, width=3, tags="button")

        # Scrolls the game canvas
        def on_mouse_wheel(self, event):
            self.game_inner_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Shows options menu
        def on_settings_click(self):
            self.app.show_overlaying_screen(Screens.SettingsMenu(self.root, self.app, self).get())

        # Goes back from difficulty screen to game selection
        def on_difficulty_back(self):
            self.selected_game = None

            # Update title
            self.logo_title.config(text="Gamemodes")
            self.update_widgets_background(self.logo_title)  # Updates the background for title

            # Remove difficulty buttons and show game buttons
            self.difficulty_canvas.pack_forget()
            self.game_outer_frame.pack(fill=tk.BOTH, expand=True)

        # Goes to difficulty screen
        def on_game_select(self, game_name: str):
            self.selected_game = game_name

            # Update title
            self.logo_title.config(text=game_name)
            self.update_widgets_background(self.logo_title)  # Updates the background for title

            # Remove game buttons and show difficulty buttons
            self.game_outer_frame.pack_forget()
            self.difficulty_canvas.pack(fill=tk.BOTH, expand=True)

        # Passes the difficulty to the game and shows the game screen
        def on_difficulty_select(self, difficulty: str):
            self.app.show_screen(self.app.games[self.selected_game](self.root, self.app, difficulty).get())
            del self

    class SettingsMenu(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, caller):
            super().__init__(root, app, True, True)  # Implements all variables and function from base class "BaseScreen"
            self.caller = caller
            self.original_theme = self.app.theme

            accessibility_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            accessibility_info_canvas.pack(padx=(0, 3), anchor="nw", fill="x")
            self.widgets.append(accessibility_info_canvas)

            accessibility_info_label = tk.Label(accessibility_info_canvas, text="Accessibility: Press the underlined key for quick navigation", font=("Poppins Regular", 7))
            accessibility_info_label.pack(anchor="n", side=tk.RIGHT)
            self.widgets.append(accessibility_info_label)

            logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            logo_canvas.pack(pady=(0, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            logo_label = tk.Label(logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            logo_label.config(image=image_data['updated_image'])
            logo_label.pack(anchor="nw", padx=(5, 0), pady=(0, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            logo_title = tk.Label(logo_canvas, text="Options Menu", font=("Poppins Regular", 15))
            logo_title.pack(anchor="nw", pady=(19, 0), side=tk.LEFT)
            self.widgets.append(logo_title)

            if self.app.username is not None and self.caller.__class__.__name__ != "PauseMenu":  # Don't allow sign out when in game
                sign_out_button = RoundedButton(
                    logo_canvas, text="SIGN OUT", font=("Poppins Bold", 15, "bold"),
                    width=210, height=50, radius=29, text_padding=0, underline_index=0,
                    button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                    button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                    button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                    outline_colour=self.app.theme_data['outline'], outline_width=1,
                    command=self.on_sign_out
                )
                sign_out_button.pack(anchor="ne", pady=(12, 0), side=tk.RIGHT)
                self.widgets.append(sign_out_button)

            heading = tk.Label(self.canvas, text="Sound Settings", font=("Poppins Bold", 15, "bold"))
            heading.pack(anchor=tk.CENTER, pady=(0, 0))
            self.widgets.append(heading)

            self.mute_button = RoundedButton(
                self.canvas, text=("MUTE" if self.app.volume.get() != 0 else "UNMUTE"), font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0, underline_index=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=lambda: self.on_mute_button()
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

            hidden_music_button = RoundedButton(
                self.canvas, text="View Hidden Music", font=("Poppins Bold", 10, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.view_hidden_music
            )
            hidden_music_button.pack(anchor=tk.CENTER, pady=(5, 0))
            self.widgets.append(hidden_music_button)

            heading = tk.Label(self.canvas, text="Appearance", font=("Poppins Bold", 15, "bold"))
            heading.pack(anchor=tk.CENTER, pady=(15, 0))
            self.widgets.append(heading)

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

            leave_button = RoundedButton(
                self.canvas, text="LEAVE AND APPLY", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0, underline_index=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_leave_options
            )
            leave_button.pack(anchor=tk.CENTER, pady=(30, 0))
            self.widgets.append(leave_button)

            credit_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            credit_canvas.pack(padx=(3, 0), side=tk.BOTTOM, anchor="w")
            self.widgets.append(credit_canvas)

            image_credit_label = tk.Label(credit_canvas, text="All images and sound effects sourced from Pixabay under CC0 License.", font=("Poppins Regular", 6))
            image_credit_label.pack(anchor="nw")
            self.widgets.append(image_credit_label)

            font_credit_label = tk.Label(credit_canvas, text="Font used \"Poppins\" under SIL Open Font Licence.", font=("Poppins Regular", 6))
            font_credit_label.pack(anchor="nw")
            self.widgets.append(font_credit_label)

            music_credit_label = tk.Label(credit_canvas, text="All Music sourced from no-copyright-music.com", font=("Poppins Regular", 6))
            music_credit_label.pack(anchor="nw")
            self.widgets.append(music_credit_label)

            self.finish_init()

        def on_keyboard_press(self, key):
            if key == "m":
                self.on_mute_button()
            elif key == "t":
                self.on_change_theme()
            elif key in ["l", "o", "escape"]:
                self.on_leave_options()
            elif key == "s":
                self.on_sign_out()

        # Generates volume button
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

        def on_mute_button(self):
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

        def view_hidden_music(self):
            self.canvas.pack_forget()
            self.app.show_overlaying_screen(Screens.HiddenMusicList(self.root, self.app, self).get())
            del self

        # Generates theme button
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
            button.create_line(start_x, 35, start_x + 16, 35, width=3, tag="button")

        def on_change_theme(self):
            all_themes = list(self.app.themes.keys())
            current_index = all_themes.index(self.app.theme)
            next_index = current_index + 1 if current_index < len(all_themes) - 1 else 0
            self.app.theme = all_themes[next_index]
            self.app.theme_data = self.app.themes[self.app.theme]

            print(f"Changed theme to: {self.app.theme}")

            self.theme_button.generate_button()  # Regenerates theme button to update theme name

        # Save the options to the user data file
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
            if "hidden_music" not in current_user_data['options']:
                current_user_data['options']['hidden_music'] = []

            current_user_data['options']['volume'] = int(self.app.volume.get())
            current_user_data['options']['theme'] = self.app.theme

            self.app.rewrite_user_data(self.app.username, current_user_data)

        # Saves and apply the options
        def on_leave_options(self):
            self.save_options()

            if self.caller.__class__.__name__ == "PauseMenu":
                self.get().destroy()  # Can't use finish_overlaying_screen since it will pack current screen
                self.caller.canvas.pack(side="top", fill=tk.BOTH, expand=True)  # Packs pause menu
                self.caller.setup_keypress_listener()
                del self
                return

            # If theme is updated, regenerate last screen (self.caller)
            if self.original_theme != self.app.theme:
                # Only update theme if not in game
                self.app.finish_overlaying_screen(self.get(), screen=self.caller.__class__(self.root, self.app).get())  # Recreates class so the themes are updated
                # Keypress does not need to be re-setup since a new screen will be created
                del self
                return

            self.app.finish_overlaying_screen(self.get())  # Screen not specified so screen will not regenerate (saves resources)
            self.caller.setup_keypress_listener()
            del self

        # Sign out the user and go back to home screen
        def on_sign_out(self):
            self.app.username = None
            self.app.finish_overlaying_screen(self.get())
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())
            del self

    class HiddenMusicList(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, caller):
            super().__init__(root, app, True, False)  # Implements all variables and function from base class "BaseScreen"
            self.caller = caller

            self.selected_game = None

            accessibility_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            accessibility_info_canvas.pack(padx=(0, 3), anchor="nw", fill="x")
            self.widgets.append(accessibility_info_canvas)

            accessibility_info_label = tk.Label(accessibility_info_canvas, text="Accessibility: Press the corresponding number for quick navigation, press O for options", font=("Poppins Regular", 7))
            accessibility_info_label.pack(anchor="n", side=tk.RIGHT)
            self.widgets.append(accessibility_info_label)

            logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            logo_canvas.pack(pady=(0, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            logo_label = tk.Label(logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            logo_label.config(image=image_data['updated_image'])
            logo_label.pack(anchor="nw", padx=(5, 0), pady=(0, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            self.logo_title = tk.Label(logo_canvas, text="Hidden Music List", font=("Poppins Regular", 15))
            self.logo_title.pack(anchor="nw", pady=(19, 0), side=tk.LEFT)
            self.widgets.append(self.logo_title)

            back_button = RoundedButton(
                self.canvas, text="BACK", font=("Poppins Bold", 15, "bold"),
                width=210, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_back
            )
            back_button.pack(pady=(5, 0), padx=(10, 0), anchor="nw")
            self.widgets.append(back_button)

            self.list_outer_frame = tk.Frame(self.canvas, bd=0, borderwidth=0, highlightthickness=0, bg=self.app.theme_data['accent'])
            self.list_outer_frame.pack(fill=tk.BOTH, expand=True)

            self.list_inner_canvas = tk.Canvas(self.list_outer_frame, bg=self.app.theme_data['accent'], bd=0, borderwidth=0, highlightthickness=0)
            self.list_inner_canvas.pack(anchor=tk.CENTER, side=tk.LEFT, fill=tk.Y, expand=True)

            scrollbar = tk.Scrollbar(self.list_outer_frame, orient=tk.VERTICAL, command=self.list_inner_canvas.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            self.list_inner_canvas.configure(yscrollcommand=scrollbar.set)
            self.root.update()
            self.list_inner_canvas.bind("<Configure>", lambda e: self.list_inner_canvas.configure(scrollregion=self.list_inner_canvas.bbox("all")))

            self.list_canvas = tk.Canvas(self.list_inner_canvas, bg=self.app.theme_data['accent'], bd=0, borderwidth=0, highlightthickness=0)

            self.update_hidden_music_list()

            self.list_inner_canvas.create_window((0, 0), window=self.list_canvas, anchor="nw")

            self.list_inner_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            self.list_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            for child in self.list_canvas.children.values():
                child.bind("<MouseWheel>", self.on_mouse_wheel)

            # Fixes game button canvas getting cut off
            self.root.update()
            x1, y1, x2, y2 = self.list_inner_canvas.bbox("all")
            self.list_inner_canvas.config(width=x2 - x1, height=y2 - y1)

            self.finish_init()

        def on_keyboard_press(self, key):
            if key == "b":
                self.root.unbind("<KeyRelease>")
                self.on_back()

        # Scrolls the game canvas
        def on_mouse_wheel(self, event):
            self.list_inner_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def update_hidden_music_list(self):
            for widget in self.list_canvas.winfo_children():
                widget.destroy()

            if not self.app.hidden_music:
                tk.Label(self.list_canvas, text="No Hidden Songs.", bg=self.app.theme_data['accent'], font=("Poppins Regular", 15)).pack(anchor=tk.CENTER, pady=(100, 0))
            else:
                tk.Label(self.list_canvas, text="Click on a music to un-hide it.", bg=self.app.theme_data['accent'], font=("Poppins Regular", 15)).pack(anchor=tk.CENTER, pady=(10, 0))

            for hidden_item in self.app.hidden_music:
                print(hidden_item)
                item_button = RoundedButton(
                    self.list_canvas, text=os.path.splitext(os.path.basename(hidden_item))[0], font=("Poppins Regular", 15),
                    width=450, height=50, radius=29, text_padding=0,
                    bg=self.app.theme_data['accent'],
                    button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                    button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                    button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                    outline_colour=self.app.theme_data['outline'], outline_width=1,
                    command=lambda item=hidden_item: self.remove_hidden_music(item)
                )
                item_button.pack(anchor=tk.CENTER, padx=(5, 5), pady=(10, 10))

        def remove_hidden_music(self, hidden_item):
            if hidden_item in self.app.hidden_music:
                self.app.hidden_music.remove(hidden_item)
                print(f"Removed {hidden_item} from list of hidden items")

            # Save the options to the user data file

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
            if "hidden_music" not in current_user_data['options']:
                current_user_data['options']['hidden_music'] = []

            current_user_data['options']['hidden_music'] = self.app.hidden_music

            self.app.rewrite_user_data(self.app.username, current_user_data)

            self.update_hidden_music_list()

        def on_back(self, _=None):
            self.get().destroy()  # Can't use finish_overlaying_screen since it will pack current screen
            self.caller.canvas.pack(side="top", fill=tk.BOTH, expand=True)  # Packs pause menu
            self.caller.setup_keypress_listener()
            del self

    class PauseMenu(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, game_name: str, difficulty: str, caller):
            super().__init__(root, app, True, False)  # Implements all variables and function from base class "BaseScreen"
            self.caller = caller

            accessibility_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            accessibility_info_canvas.pack(padx=(0, 3), anchor="nw", fill="x")
            self.widgets.append(accessibility_info_canvas)

            accessibility_info_label = tk.Label(accessibility_info_canvas, text="Accessibility: Press the underlined key for quick navigation", font=("Poppins Regular", 7))
            accessibility_info_label.pack(anchor="n", side=tk.RIGHT)
            self.widgets.append(accessibility_info_label)

            logo_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            logo_canvas.pack(pady=(0, 0), padx=(10, 0), anchor="nw", fill="x")
            self.widgets.append(logo_canvas)

            logo_image = Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90))  # Must be multiple of 935 x 306
            logo_label = tk.Label(logo_canvas, borderwidth=0, highlightthickness=0)
            image_data = {
                "label": logo_label,
                "raw_image": logo_image,
                "updated_image": ImageTk.PhotoImage(logo_image)  # Used to save only
            }
            logo_label.config(image=image_data['updated_image'])
            logo_label.pack(anchor="nw", padx=(5, 0), pady=(0, 3), side=tk.LEFT)
            self.transparent_images.append(image_data)
            del logo_image

            logo_title = tk.Label(logo_canvas, text=f"{game_name} ({difficulty.capitalize()} mode)", font=("Poppins Regular", 15))
            logo_title.pack(anchor="nw", pady=(19, 0), side=tk.LEFT)
            self.widgets.append(logo_title)

            heading = tk.Label(self.canvas, text="GAME PAUSED", font=("Poppins Bold", 17, "bold"))
            heading.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(heading)

            unpause_button = RoundedButton(
                self.canvas, text="UNPAUSE", font=("Poppins Bold", 17, "bold"),
                width=350, height=75, radius=29, text_padding=0, underline_index=2,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_unpause_button
            )
            unpause_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(unpause_button)

            options_button = RoundedButton(
                self.canvas, text="OPTIONS", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0, underline_index=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_options_button
            )
            options_button.pack(anchor=tk.CENTER, pady=(20, 0))
            self.widgets.append(options_button)

            leave_game_button = RoundedButton(
                self.canvas, text="LEAVE GAME", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0, underline_index=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_leave_game_button
            )
            leave_game_button.pack(anchor=tk.CENTER, pady=(20, 20))
            self.widgets.append(leave_game_button)

            self.music_info_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0)
            self.music_info_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(self.music_info_canvas)

            self.music_info_row3_canvas = tk.Canvas(self.music_info_canvas, borderwidth=0, highlightthickness=0, bg="#d9d9d9")
            self.music_info_row3_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(self.music_info_row3_canvas)

            self.music_label = tk.Label(self.music_info_row3_canvas, text=os.path.splitext(os.path.basename(self.app.music_playing))[0] if self.app.music_playing is not None else "No music playing", font=("Poppins Regular", 12), bg="#d9d9d9")
            self.music_label.pack(anchor="center", side=tk.RIGHT)

            skip_button = RoundedButton(
                self.music_info_row3_canvas, font=("", 0, ""),
                width=42, height=42, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/skip.png").convert("RGBA").resize((25, 25))),
                button_background="#737373", button_foreground="#000000",
                button_hover_background="#8c8c8c", button_hover_foreground="#000000",
                button_press_background="#3f3f3f", button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_skip_button
            )
            skip_button.pack(side=tk.RIGHT)
            skip_button.generate_button()

            self.skip_label = tk.Label(self.music_info_row3_canvas, text="Skip", font=("Poppins Regular", 12), underline=0)
            self.skip_label.pack(anchor="center", side=tk.RIGHT, padx=(0, 5))
            self.widgets.append(self.skip_label)

            music_info_row2_canvas = tk.Canvas(self.music_info_canvas, borderwidth=0, highlightthickness=0, bg="#d9d9d9")
            music_info_row2_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(music_info_row2_canvas)

            hide_button = RoundedButton(
                music_info_row2_canvas, font=("", 0, ""),
                width=42, height=42, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/hide.png").convert("RGBA").resize((25, 25))),
                button_background="#765b5b", button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_hide_button
            )
            hide_button.pack(side=tk.RIGHT)
            hide_button.generate_button()

            hide_label = tk.Label(music_info_row2_canvas, text="Hide Music Permanently", font=("Poppins Regular", 10))
            hide_label.pack(anchor="center", side=tk.RIGHT, padx=(0, 5))
            self.widgets.append(hide_label)

            music_info_row1_canvas = tk.Canvas(self.music_info_canvas, borderwidth=0, highlightthickness=0, bg="#d9d9d9")
            music_info_row1_canvas.pack(side=tk.BOTTOM, anchor="e")
            self.widgets.append(music_info_row1_canvas)

            self.mute_button = RoundedButton(
                music_info_row1_canvas, font=("", 0, ""),
                width=42, height=42, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/mute.png").convert("RGBA").resize((25, 25))),
                button_background="#737373", button_foreground="#000000",
                button_hover_background="#8c8c8c", button_hover_foreground="#000000",
                button_press_background="#3f3f3f", button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_mute_button
            )
            self.mute_button.pack(side=tk.RIGHT)
            self.mute_button.generate_button()

            self.mute_label = tk.Label(music_info_row1_canvas, text="Mute", font=("Poppins Regular", 12), underline=0)
            self.mute_label.pack(anchor="center", side=tk.RIGHT, padx=(0, 5))
            self.widgets.append(self.mute_label)

            self.finish_init()

        def on_mute_button(self):
            if self.app.volume.get() != 0:  # Mutes
                self.app.last_volume = self.app.volume.get()
                self.app.volume.set(0)
                self.mute_label.config(text="Unmute", underline=2)
                self.mute_button.image = ImageTk.PhotoImage(Image.open("assets/icons/unmute.png").convert("RGBA").resize((25, 25)))
            else:  # Unmutes to last volume
                if self.app.last_volume == 0:
                    self.app.last_volume = 50
                self.app.volume.set(self.app.last_volume)
                self.mute_label.config(text="Mute", underline=0)
                self.mute_button.image = ImageTk.PhotoImage(Image.open("assets/icons/mute.png").convert("RGBA").resize((25, 25)))
            self.update_widgets_background(specific_widget=self.mute_label)  # Update label (UNMUTE/MUTE)
            self.mute_button.generate_button()  # Regenerates mute button to update image

        def on_skip_button(self):
            # Caller should always be the game
            if hasattr(self.caller, "play_music"):  # Check if caller has play_music option
                self.caller.play_music()
                self.music_label.config(text=os.path.splitext(os.path.basename(self.app.music_playing))[0] if self.app.music_playing is not None else "No music playing")
                self.update_widgets_background(specific_widget=self.skip_label)
                self.update_widgets_background(specific_widget=self.music_info_row3_canvas)
                self.update_widgets_background(specific_widget=self.music_info_canvas)
                pygame.mixer.music.pause()

        def on_hide_button(self):
            print(f"Hiding music: {self.app.music_playing}")
            self.app.hidden_music.append(self.app.music_playing) if self.app.music_playing not in self.app.hidden_music else self.app.hidden_music
            print(f"New hidden list of music: {self.app.hidden_music}")

            self.on_skip_button()

            # Save the options to the user data file

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
            if "hidden_music" not in current_user_data['options']:
                current_user_data['options']['hidden_music'] = []

            current_user_data['options']['hidden_music'] = self.app.hidden_music

            self.app.rewrite_user_data(self.app.username, current_user_data)

        def on_keyboard_press(self, key):
            if key in ["escape", "p"]:
                self.root.unbind("<KeyRelease>")
                self.on_unpause_button()
            elif key == "o":
                self.root.unbind("<KeyRelease>")
                self.on_options_button()
            elif key == "l":
                self.root.unbind("<KeyRelease>")
                self.on_leave_game_button()

        # Finish the overlaying screen and unpause
        def on_unpause_button(self):
            self.app.finish_overlaying_screen(self.get())
            self.caller.setup_keypress_listener()
            self.caller.on_unpause()
            del self

        # Go to options menu
        def on_options_button(self):
            self.canvas.pack_forget()
            self.app.show_overlaying_screen(Screens.SettingsMenu(self.root, self.app, self).get())
            del self

        # Leave the game and go to game selection page
        def on_leave_game_button(self):
            self.app.finish_overlaying_screen(self.get())
            self.app.show_screen(Screens.GameSelection(self.root, self.app).get())
            del self


class Games:
    class MatchingTiles(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp, difficulty: str):
            super().__init__(root, app, False, False)  # Implements all variables and function from base class "BaseScreen"

            # Regex for png files: .*(?=\.png)

            self.game = "Matching Tiles"
            self.difficulty = difficulty
            print(f"Started Matching Tiles game with difficulty {difficulty}")
            self.time_penalise_multiplier = 0.2

            self.app.music_playing = None

            self.canvas.config(bg=self.app.theme_data['accent'])

            top_bar_canvas = tk.Canvas(self.canvas, bg=self.app.theme_data['accent'], borderwidth=0, highlightthickness=0)
            top_bar_canvas.pack(anchor="nw", fill="x")

            self.score_label = tk.Label(top_bar_canvas, text="Score: 0", font=("Poppins Bold", 9, "bold"), bg="white")
            self.score_label.pack(anchor="center", side=tk.LEFT, padx=(7, 0))

            self.mistakes_label = tk.Label(top_bar_canvas, text="Mistakes: 0", font=("Poppins Bold", 9, "bold"), bg="white")
            self.mistakes_label.pack(anchor="center", side=tk.LEFT, padx=(5, 0))

            self.time_label = tk.Label(top_bar_canvas, text="Time Elapsed: 00:00", font=("Poppins Bold", 9, "bold"), bg="white")
            self.time_label.pack(anchor="center", side=tk.LEFT, padx=(5, 0))

            pause_button = RoundedButton(
                top_bar_canvas, font=("", 0, ""),
                width=50, height=50, radius=0, text_padding=0,
                image=ImageTk.PhotoImage(Image.open("assets/icons/pause.png").convert("RGBA").resize((35, 35))),
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_pause
            )
            pause_button.pack(anchor="ne", pady=(0, 0), side=tk.RIGHT)

            tk.Label(top_bar_canvas, text="Press Esc to pause", font=("Poppins Regular", 7), bg=self.app.theme_data['accent']).pack(anchor="ne", side=tk.RIGHT)

            self.heading = tk.Label(self.canvas, text="Match pairs of the same cards", font=("Poppins Bold", 15, "bold"), bg=self.app.theme_data['accent'])
            self.heading.pack(anchor=tk.CENTER, pady=(30, 10))

            self.start_button = RoundedButton(
                self.canvas, text="START", font=("Poppins Bold", 20, "bold"),
                width=350, height=75, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_click_start
            )
            self.start_button.pack(anchor=tk.CENTER, pady=(50, 0))

            rows, columns = 4, 4
            if self.difficulty == "hard":
                rows, columns = 5, 6
            elif self.difficulty == "normal":
                columns = 5
            self.grid = [[{} for _ in range(columns)] for _ in range(rows)]

            self.game_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0, bg="white")
            self.create_grid(rows, columns)

            self.base_score = 50
            if self.difficulty == "hard":
                self.base_score = 200
            elif self.difficulty == "normal":
                self.base_score = 100
            self.selected_grids = []
            self.mistakes = 0
            self.game_started = False

            self.time_elapsed = []
            self.last_start_time = 0
            self.schedule_loop_id = None  # Loop handles time updates and music end event

            self.finish_init()

        def on_keyboard_press(self, key):
            if key == "escape":
                self.root.unbind("<KeyRelease>")
                self.on_pause()

        # Selects the photos for the grid and creates it on the canvas
        def create_grid(self, rows, columns):
            list_of_photos = []
            selected_folder = [
                folder
                for folder in os.listdir("assets/matching_tiles")
                if os.path.isdir(f"assets/matching_tiles/{folder}")
            ]
            if self.difficulty in {"normal", "hard"}:
                selected_folder = [random.choice(selected_folder)]  # If normal or hard, only select one category
            print(f"Selected categories: {selected_folder}")

            for folder in selected_folder:
                # Add each item with path to list_of_photos
                list_of_photos.extend([f"assets/matching_tiles/{folder}/{filename}" for filename in os.listdir(f"assets/matching_tiles/{folder}")])

            # Checks if file has ".png"
            list_of_photos = [file for file in list_of_photos if ".png" in file]

            random.shuffle(list_of_photos)  # Shuffles all photos
            list_of_photos = list_of_photos[:(rows * columns) // 2]  # Cuts list to number of squares divided by 2 (round down)
            list_of_photos.extend(list_of_photos)  # Duplicates list, so there is pairs of each
            random.shuffle(list_of_photos)  # Shuffles all photos

            for row in range(len(self.grid)):
                for col in range(len(self.grid[row])):
                    card_button = RoundedButton(
                        self.game_canvas, font=("", 0, ""),
                        width=80, height=80, radius=29, text_padding=0,
                        button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                        button_hover_background=self.app.theme_data['btn_hvr'], button_hover_foreground="#000000",
                        button_press_background=self.app.theme_data['btn_prs'], button_press_foreground="#000000",
                        outline_colour=self.app.theme_data['outline'], outline_width=1,
                        command=lambda r=row, c=col: self.on_click_card(r, c)
                    )
                    card_button.grid(row=row, column=col, padx=(5, (5 if col == columns - 1 else 0)), pady=(5, (5 if row == rows - 1 else 0)))
                    self.grid[row][col]['button'] = card_button
                    self.grid[row][col]['revealed'] = False
                    self.grid[row][col]['found'] = False
                    try:
                        self.grid[row][col]['image'] = list_of_photos.pop(0)
                    except IndexError:  # In case there is not enough images for squares
                        # No image, no callback (disable button), and made already found
                        self.grid[row][col]['image'] = None
                        self.grid[row][col]['button'].command = None
                        self.grid[row][col]['found'] = True
                        self.change_grid_button_bg(row, col, "#6f727b", "#6f727b", "#6f727b")

        def loop_handler(self):
            self.update_time()
            self.check_music_event()

            if self.schedule_loop_id is not None:
                self.game_canvas.after_cancel(self.schedule_loop_id)
            self.schedule_loop_id = self.game_canvas.after(100, self.loop_handler)  # Loops after 100ms or 0.1s

        def play_music(self):
            # Add each item with path to list_of_photos
            list_of_music = [f"assets/music/{self.difficulty}/{filename}" for filename in os.listdir(f"assets/music/{self.difficulty}")]
            # Checks if file has ".mp3" or ".wav"
            list_of_music = [file for file in list_of_music if ".mp3" in file or ".wav" in file]
            print(f"List of music: {list_of_music}")

            if not list_of_music:  # List of music is empty
                print("No music to play, the list is empty")
                self.app.music_playing = None
            elif set(list_of_music).issubset(self.app.hidden_music):  # List of music is all hidden
                print("No music to play, all hidden")
                self.app.music_playing = None
            elif visible_music := [music for music in list_of_music if music not in self.app.hidden_music]:  # Ensures visible music list is not None (assigns variable and checks at once)
                print(f"List of available music: {visible_music}")
                with contextlib.suppress(ValueError):
                    visible_music.remove(self.app.music_playing)  # Prevents looping of the same music
                if visible_music:  # If the only music is not current playing, otherwise it will loop
                    self.app.music_playing = random.choice(visible_music)
            else:
                print("No music to play, all hidden")
                self.app.music_playing = None

            if self.app.music_playing is not None:
                pygame.mixer.music.load(self.app.music_playing)
                pygame.mixer.music.set_volume(((self.app.volume.get() / 100) * 2) / 20)  # Double percentage then divide by 20 since it is too loud
                print(f"Playing music \"{self.app.music_playing}\" with volume: {pygame.mixer.music.get_volume()}")
                pygame.mixer.music.play(fade_ms=3000)  # Fade in in 3s

        def check_music_event(self):
            for event in pygame.event.get():
                if event.type == self.app.MUSIC_END_EVENT:
                    print("Detected music ended, playing next music")
                    self.play_music()

        # Stops timer and goes to pause menu
        def on_pause(self):
            if self.game_started is True:
                self.time_elapsed.append(time.time() - self.last_start_time)
                if self.schedule_loop_id is not None:
                    self.game_canvas.after_cancel(self.schedule_loop_id)

            print("Music paused")
            pygame.mixer.music.pause()

            self.app.show_overlaying_screen(Screens.PauseMenu(self.root, self.app, self.game, self.difficulty, self).get())

        # Continues the timer
        def on_unpause(self):
            pygame.mixer.music.set_volume(((self.app.volume.get() / 100) * 2) / 20)  # Double percentage then divide by 20 since it is too loud
            print(f"Resuming music with volume: {pygame.mixer.music.get_volume()}")
            pygame.mixer.music.unpause()

            if self.game_started is True:
                self.last_start_time = time.time()
                self.loop_handler()  # Starts loop for time update and music end event

        # Starts the game and timer
        def on_click_start(self):
            self.game_started = True
            self.heading.destroy()
            self.start_button.destroy()
            self.game_canvas.pack(anchor="center", pady=(30, 0), expand=True)

            self.play_music()

            self.last_start_time = time.time()
            self.loop_handler()  # Starts loop for time update and music end event

        # Loops and called from self.loop_handler
        def update_time(self):
            seconds_taken = sum(self.time_elapsed) + (time.time() - self.last_start_time)
            if seconds_taken < 3600:
                time_taken = time.strftime("%M:%S", time.gmtime(seconds_taken))
            else:
                time_taken = time.strftime("%H:%M:%S", time.gmtime(seconds_taken))
            self.time_label.config(text=f"Time Elapsed: {time_taken}")

            self.update_score()  # Score may be affected by time elapsed, so it needs to be updated

        # Recalculate score and change label at top bar
        def update_score(self):
            score = self.base_score
            score -= self.mistakes
            seconds_taken = sum(self.time_elapsed) + (time.time() - self.last_start_time)
            score -= math.floor(seconds_taken) * self.time_penalise_multiplier
            score = max(round(score, 1), -100)  # Prevent float point arithmetic, set minimum score -100.
            self.score_label.config(text=f"Score: {score}")
            return score

        # Selects the clicked card and check the selected card if 2 are selected
        def on_click_card(self, row, col):
            grid_num = (row, col)
            if grid_num in self.selected_grids:
                self.selected_grids.remove(grid_num)
                self.change_grid_button_bg(row, col, self.app.theme_data['btn_bg'], self.app.theme_data['btn_hvr'], self.app.theme_data['btn_prs'])
                return

            self.selected_grids.append(grid_num)
            self.change_grid_button_bg(row, col, self.app.theme_data['btn_prs'], self.app.theme_data['btn_prs'], self.app.theme_data['btn_hvr'])  # Makes button appear selected
            if len(self.selected_grids) == 2:
                self.check_selected_cards()

        # Change the background of buttons for hover and press events
        def change_grid_button_bg(self, row, col, bg, hover_bg, press_bg):
            self.grid[row][col]['button'].button_background = bg
            self.grid[row][col]['button'].button_hover_background = hover_bg
            self.grid[row][col]['button'].button_press_background = press_bg
            self.grid[row][col]['button'].generate_button()

        # Shows the cards, checks if the selected cards match, and schedules the change back event
        def check_selected_cards(self):
            row, col = self.selected_grids[0]
            row2, col2 = self.selected_grids[1]
            self.selected_grids.clear()

            self.grid[row][col]['button'].image = ImageTk.PhotoImage(ImageOps.contain(Image.open(self.grid[row][col]['image']).convert("RGBA"), (70, 70)))
            self.grid[row][col]['button'].generate_button()
            self.grid[row2][col2]['button'].image = ImageTk.PhotoImage(ImageOps.contain(Image.open(self.grid[row2][col2]['image']).convert("RGBA"), (70, 70)))
            self.grid[row2][col2]['button'].generate_button()

            correct = self.grid[row][col]['image'] == self.grid[row2][col2]['image']

            # Correct
            if correct:
                self.grid[row][col]['found'] = True
                self.grid[row2][col2]['found'] = True
                # Removes click option
                self.grid[row][col]['button'].command = None
                self.grid[row2][col2]['button'].command = None
                # Makes all options of button background green
                self.change_grid_button_bg(row, col, "#61a252", "#61a252", "#61a252")
                self.change_grid_button_bg(row2, col2, "#61a252", "#61a252", "#61a252")

                sound = pygame.mixer.Sound("assets/sound_effects/correct.mp3")
                sound.set_volume((self.app.volume.get() / 100) * 2)  # Make volume percentage doubled
                sound.play()

            # Incorrect
            else:
                # Makes background red
                self.change_grid_button_bg(row, col, "#ff7f7f", "#ff7f7f", "#ff7f7f")
                self.change_grid_button_bg(row2, col2, "#ff7f7f", "#ff7f7f", "#ff7f7f")

                if self.grid[row][col]['revealed'] and self.grid[row2][col2]['revealed']:
                    self.mistakes += 1
                    self.mistakes_label.config(text=f"Mistakes: {self.mistakes}")
                    self.update_score()

                    sound = pygame.mixer.Sound("assets/sound_effects/wrong.mp3")
                    sound.set_volume((self.app.volume.get() / 100) * 2)  # Make volume percentage doubled
                    sound.play()

            self.grid[row][col]['revealed'] = True
            self.grid[row2][col2]['revealed'] = True

            self.game_canvas.after(750, lambda: self.hide_selected_cards(correct, (row, col), (row2, col2)))

        # Hides the selected cards, should be scheduled
        def hide_selected_cards(self, correct, grid1, grid2):
            row, col = grid1
            row2, col2 = grid2

            self.grid[row][col]['button'].image = None
            self.grid[row2][col2]['button'].image = None
            if correct is False:
                self.change_grid_button_bg(row, col, self.app.theme_data['btn_bg'], self.app.theme_data['btn_hvr'], self.app.theme_data['btn_prs'])
                self.change_grid_button_bg(row2, col2, self.app.theme_data['btn_bg'], self.app.theme_data['btn_hvr'], self.app.theme_data['btn_prs'])

            completed = True
            for grid_row in self.grid:
                for grid_data in grid_row:
                    if grid_data['found'] is False:
                        completed = False
                        break
                if not completed:
                    break

            if completed:
                self.on_finish_game()

        # Destroy the game canvas and shows the summary
        def on_finish_game(self):
            self.game_started = False
            self.time_elapsed.append(time.time() - self.last_start_time)
            if self.schedule_loop_id is not None:
                self.game_canvas.after_cancel(self.schedule_loop_id)
            self.game_canvas.destroy()

            self.score_label.destroy()
            self.mistakes_label.destroy()
            self.time_label.destroy()

            pygame.mixer.music.fadeout(3000)  # Fade out in 3s
            self.app.music_playing = None
            print("Music stopping")

            summary_canvas = tk.Canvas(self.canvas, borderwidth=0, highlightthickness=0, bg="white")
            summary_canvas.pack(anchor="center", expand=True)

            underline_font = tk_font.Font(family="Poppins Regular", size=13, weight="normal")
            underline_font.configure(underline=True)

            tk.Label(summary_canvas, text="Game Completed", font=("Poppins Bold", 15, "bold"), bg="white").pack(anchor=tk.CENTER, pady=(10, 10))

            score = self.base_score
            score_canvas = tk.Canvas(summary_canvas, borderwidth=0, highlightthickness=0, bg="white")
            score_canvas.pack(expand=True)

            tk.Label(score_canvas, text="Base Score", font=("Poppins Regular", 13), bg="white").grid(row=0, column=0, sticky="W", padx=(5, 30), pady=(5, 0))
            tk.Label(score_canvas, text=score, font=("Poppins Regular", 13), bg="white").grid(row=0, column=1, sticky="W", padx=(0, 5), pady=(5, 0))

            score -= self.mistakes
            tk.Label(score_canvas, text=f"Mistakes: {self.mistakes}", font=("Poppins Regular", 13), bg="white").grid(row=1, column=0, sticky="W", padx=(5, 30))
            tk.Label(score_canvas, text=f"-{self.mistakes}", font=("Poppins Regular", 13), fg="red", bg="white").grid(row=1, column=1, sticky="W", padx=(0, 5))

            seconds_taken = round(sum(self.time_elapsed))
            if seconds_taken < 3600:
                time_taken = time.strftime("%M:%S", time.gmtime(seconds_taken))
            else:
                time_taken = time.strftime("%H:%M:%S", time.gmtime(seconds_taken))
            score_difference = round(math.floor(seconds_taken) * self.time_penalise_multiplier, 1)
            score -= score_difference
            score = max(round(score, 1), -100)  # Prevent float point arithmetic, set minimum score -100.
            tk.Label(score_canvas, text=f"Time taken: {time_taken}", font=("Poppins Regular", 13), bg="white").grid(row=2, column=0, sticky="W", padx=(5, 30))
            tk.Label(score_canvas, text=f"-{score_difference} {'(minimum -100 score)' if score == -100 else ''}", font=underline_font, fg="red", bg="white").grid(row=2, column=1, sticky="W", padx=(0, 5))

            # Change account data scores
            user_data = self.app.get_user_data(self.app.username)
            if user_data is None:
                return
            game_data = self.app.get_game_data(self.app.username, self.game)
            if f"record_score_{self.difficulty}" not in list(game_data.keys()):
                game_data[f'record_score_{self.difficulty}'] = score
                new_record = True
            else:
                new_record = score > game_data[f'record_score_{self.difficulty}']
                game_data[f'record_score_{self.difficulty}'] = max(score, game_data[f'record_score_{self.difficulty}'])
            overall_change, original_overall_score, new_overall_score = self.app.change_game_user_data(self.app.username, self.game, game_data, self.difficulty, score)

            tk.Label(score_canvas, text="Game Score", font=("Poppins Regular", 13), bg="white").grid(row=3, column=0, sticky="W", padx=(5, 30))
            tk.Label(score_canvas, text=f"{score}{' (New Record!)' if new_record else ''}", font=("Poppins Regular", 13), bg="white").grid(row=3, column=1, sticky="W", padx=(0, 5))

            tk.Label(score_canvas, text="Account Score", font=("Poppins Regular", 13), bg="white").grid(row=4, column=0, sticky="W", padx=(5, 30), pady=(15, 0))
            tk.Label(score_canvas, text=original_overall_score, font=("Poppins Regular", 13), bg="white").grid(row=4, column=1, sticky="W", padx=(0, 5), pady=(15, 0))

            tk.Label(score_canvas, text="Adjustment", font=("Poppins Regular", 13), bg="white").grid(row=5, column=0, sticky="W", padx=(5, 30))
            tk.Label(score_canvas, text=overall_change, font=underline_font, fg="red" if overall_change < 0 else "green", bg="white").grid(row=5, column=1, sticky="W", padx=(0, 5))

            tk.Label(score_canvas, text="New Account Score", font=("Poppins Bold", 13, "bold"), bg="white").grid(row=6, column=0, sticky="W", padx=(5, 30), pady=(5, 0))
            tk.Label(score_canvas, text=new_overall_score, font=("Poppins Bold", 13, "bold"), bg="white").grid(row=6, column=1, sticky="W", padx=(0, 5), pady=(5, 0))

            tk.Canvas(summary_canvas, borderwidth=0, highlightthickness=0, bg="black", height=1).pack(fill="x")

            leave_game_button = RoundedButton(
                summary_canvas, text="LEAVE GAME", font=("Poppins Bold", 15, "bold"),
                width=300, height=50, radius=29, text_padding=0,
                button_background=self.app.theme_data['btn_bg'], button_foreground="#000000",
                button_hover_background=self.app.theme_data['btn_warn_hvr'], button_hover_foreground="#000000",
                button_press_background=self.app.theme_data['btn_warn_prs'], button_press_foreground="#000000",
                outline_colour=self.app.theme_data['outline'], outline_width=1,
                command=self.on_leave_game_button
            )
            leave_game_button.pack(anchor=tk.CENTER, padx=(10, 10), pady=(10, 10))

        # Goes back to the game selection page
        def on_leave_game_button(self):
            self.app.show_screen(Screens.GameSelection(self.root, self.app).get())
            del self


# A class to create a RoundedButton, acts like a canvas but has button arguments
class RoundedButton(tk.Canvas):
    # Heavily adapted from https://stackoverflow.com/a/69092113
    def __init__(self, parent=None, text: str = "", font: tuple = ("Times", 30, "bold"),
                 text_padding: int = 5, radius: int = 25, underline_index: int = None,
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
        self.underline_index = underline_index
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

    # Generates a rounded rectangle using polygon points
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

    # Generates the text/images on a button
    def generate_button(self):
        self.delete("button")  # Deletes existing button to regenerate

        self.button_obj = self.round_rectangle(
            0, 0, 0, 0, tags="button",
            radius=self.radius, fill=self.button_background,
            outline=self.outline_colour, width=self.outline_width
        )

        self.text_obj = self.create_text(0, 0, text=self.text, tags="button", fill=self.button_foreground, font=self.font, justify=tk.CENTER)

        if self.image is not None:
            self.image_obj = self.create_image(self.width / 2, self.height / 2, image=self.image, tags="button")

        self.update()  # Fixes flickering
        self.resize()

        for widget in self.winfo_children():
            widget.destroy()

        # Custom regen function if provided
        if self.on_regen is not None:
            self.on_regen()

    # Resizes the button
    def resize(self, _=None):
        text_bbox = self.bbox(self.text_obj)
        width = max(self.winfo_width(), text_bbox[2] - text_bbox[0] + self.text_padding) - 1  # -1 pixel size so border is not cut off
        height = max(self.winfo_height(), text_bbox[3] - text_bbox[1] + self.text_padding) - 1  # -1 pixel size so border is not cut off
        self.round_rectangle(0, 0, width, height, self.radius, update=True)
        x = (width - (text_bbox[2] - text_bbox[0])) / 2
        y = (height - (text_bbox[3] - text_bbox[1])) / 2
        self.moveto(self.text_obj, x, y)
        self.draw_underline(x, y, text_bbox[3] - text_bbox[1])

    def draw_underline(self, text_x, text_y, text_height):
        if self.underline_index is not None:
            # Get underline character's width
            chars_text = self.create_text(0, 0, text=self.text[self.underline_index], font=self.font)
            bbox = self.bbox(chars_text)
            self.delete(chars_text)
            underline_width = bbox[2] - bbox[0]

            # Get width of characters before underline
            chars_text = self.create_text(0, 0, text=self.text[:self.underline_index], font=self.font)
            bbox = self.bbox(chars_text)
            self.delete(chars_text)
            prev_chars_width = bbox[2] - bbox[0]

            # Draw underline
            underline_x_start = text_x + prev_chars_width - 2  # Adjust the x-coordinate to be where the text is (with 2 px extra)
            underline_y = text_y + text_height - 12  # Adjust the y-coordinate to be below the text (minus 12px to account for text spacing)
            underline_x_end = underline_x_start + underline_width

            self.create_line(underline_x_start, underline_y, underline_x_end, underline_y, width=3, tags="button")

    # Handles hover and click events
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
    # Adds support for custom fonts
    pyglet.options["win32_gdi_font"] = True
    pyglet.font.add_file("assets/fonts/Poppins-Bold.ttf")
    pyglet.font.add_file("assets/fonts/Poppins-Regular.ttf")

    # Prevents blurring of the window
    windll.shcore.SetProcessDpiAwareness(1)

    # Create the root window
    root = tk.Tk()

    # Start the app
    RecollectApp(root)
