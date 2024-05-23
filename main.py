import tkinter as tk
import tkinter.font as tk_font

import pyglet  # pip install pyglet
from PIL import Image, ImageTk  # pip install pillow


class RecollectApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Recollect")
        self.root.geometry("750x563")  # Same ratio as 1000 x 750
        self.root.minsize(750, 563)

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

    def show_screen(self, screen):
        if self.current_screen is not None:
            self.current_screen.pack_forget()
            self.current_screen.destroy()
            del self.current_screen
        screen.pack(side="top", fill=tk.BOTH, expand=True)
        self.current_screen = screen


class BaseScreen:
    def __init__(self, root: tk.Tk, app: RecollectApp, has_background: bool = True):
        self.root = root
        self.app = app
        self.has_background = has_background

        self.current_background: Image = None
        self._background_image_tk: (ImageTk.PhotoImage | None) = None  # Only works when it is inside the class scope not local scope
        self._blobs_tk: list = []  # Only works when it is inside the class scope not local scope

        self.canvas = tk.Canvas(self.root, borderwidth=0, highlightthickness=0)

        if self.has_background:
            root.update_idletasks()  # Updates root background size
            self.update_background()
            self.update_blobs()

        # self.canvas.pack(side="top", fill=tk.BOTH, expand=True)  # can be removed? (pack first so coordinates work)
        self.canvas.grid_columnconfigure(0, weight=1)

        self.transparent_images = []
        self.buttons = []
        self.button_backgrounds = []  # Only works when it is inside the class scope not local scope

    def finish_init(self):
        if self.has_background:
            self.canvas.update_idletasks()  # Updates canvas coordinates size
            self.update_transparent_images()
            self.update_buttons()

            self.canvas.bind("<Configure>", self.update_background, add="+")
            self.canvas.bind("<Configure>", self.update_blobs, add="+")
            self.canvas.bind("<Configure>", self.update_transparent_images, add="+")
            self.canvas.bind("<Configure>", self.update_buttons, add="+")

    def get(self):
        return self.canvas

    def update_background(self, _=None):
        self.canvas.delete("background")
        # Adjust background stretching etc.
        width, height = self.root.winfo_width(), self.root.winfo_height()
        del self.current_background, self._background_image_tk
        self.current_background = self.app.get_background().resize((width, height), 1)
        self._background_image_tk = ImageTk.PhotoImage(self.current_background)  # Must be in class scope
        self.canvas.create_image(0, 0, image=self._background_image_tk, anchor="nw", tags="background")  # Don't make one-liner

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

    def update_buttons(self, _=None):
        if self.has_background is False or self.current_background is None:  # No background or current background not showing
            return

        # Clears previous bottom backgrounds from memory
        del self.button_backgrounds
        self.button_backgrounds = []

        # Adjust each button background
        self.canvas.update_idletasks()  # Updates coordinates
        for button in self.buttons:
            x1, y1 = button.winfo_x(), button.winfo_y()
            x2, y2 = x1 + button.winfo_width(), y1 + button.winfo_height()
            # print(f"button bbox: {x1} {y1}, {x2} {y2}")

            background_at_bbox = self.current_background.crop((x1, y1, x2, y2))
            self.button_backgrounds.append(ImageTk.PhotoImage(background_at_bbox))  # Image needs to be saved to be applied
            button.create_image(0, 0, image=self.button_backgrounds[-1], anchor="nw")

            button.generate_button()  # Remakes polygon and text

    def destroy(self):
        self.canvas.unbind("<Configure>")
        del self


class Screens:
    class Homepage(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True)  # Implements all variables and function from base class "BaseScreen"

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
            self.buttons.append(self.start_button)

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
            self.buttons.append(self.options_button)

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
            self.buttons.append(self.quit_button)

            self.finish_init()

        def on_click_start(self):
            self.destroy()
            self.app.show_screen(Screens.Login(self.root, self.app).get())

        def on_click_options(self):
            ...
            # self.destroy()

    class Login(BaseScreen):
        def __init__(self, root: tk.Tk, app: RecollectApp):
            super().__init__(root, app, True)  # Implements all variables and function from base class "BaseScreen"

            self.logo_frame = tk.Frame(self.canvas, background="#53afc8")
            self.logo_frame.pack(pady=(10, 0), padx=(10, 0), anchor="nw")

            self.logo_image = ImageTk.PhotoImage(Image.open("assets/logo_slash.png").convert("RGBA").resize((230, 90)))  # Must be multiple of 1038 x 404
            self.logo_label = tk.Label(self.logo_frame, borderwidth=0, highlightthickness=0, bg="#53afc8", image=self.logo_image)
            self.logo_label.pack(anchor="nw", padx=(5, 0), pady=(3, 3), side=tk.LEFT)

            self.logo_title = tk.Label(self.logo_frame, text="Sign In", font=("Poppins Regular", 15), bg="#53afc8")
            self.logo_title.pack(anchor="nw", pady=(22, 0), side=tk.LEFT)

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
            self.buttons.append(self.back_button)

            self.heading = tk.Label(self.canvas, text="Sign In", font=("Poppins Bold", 15, "bold"), bg="#53afc8")
            self.heading.pack(anchor="center", pady=(10, 10))

            self.username_entry = tk.Entry(self.canvas, font=("Poppins Regular", 11), width=25)
            self.username_entry.pack(anchor="center", pady=(5, 5))
            self.username_entry.bind("<FocusIn>", lambda event: self.on_focusin_entry(self.username_entry))
            self.username_entry.bind("<FocusOut>", lambda event: self.on_focusout_entry(self.username_entry, "Username"))
            self.on_focusout_entry(self.username_entry, "Username")

            self.password_entry = tk.Entry(self.canvas, font=("Poppins Regular", 11), width=25)
            self.password_entry.pack(anchor="center", pady=(5, 5))
            self.password_entry.bind("<FocusIn>", lambda event: self.on_focusin_entry(self.password_entry))
            self.password_entry.bind("<FocusOut>", lambda event: self.on_focusout_entry(self.password_entry, "Password"))
            self.on_focusout_entry(self.password_entry, "Password")

            self.error_message = tk.Label(self.canvas, text="Error message goes here", font=("Poppins Regular", 9), bg="#53afc8", fg="red")
            self.error_message.pack(anchor="center", pady=(5, 10))

            self.sign_in_button = RoundedButton(
                self.canvas, text="SIGN IN", font=("Poppins Bold", 15, "bold"),
                width=250, height=50, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_sign_in
            )
            self.sign_in_button.pack(anchor="center", pady=(5, 5))
            self.buttons.append(self.sign_in_button)

            self.finish_init()

        def on_back(self):
            self.destroy()
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())

        def on_sign_in(self):
            ...

        @staticmethod
        def on_focusin_entry(entry: tk.Entry):
            entry.config(fg="black")
            if entry.get().strip() in ["Username", "Password"]:
                entry.delete(0, tk.END)

        @staticmethod
        def on_focusout_entry(entry: tk.Entry, hint: str):
            if entry.get().strip() == "":
                entry.delete(0, tk.END)
                entry.insert(0, hint)
                entry.config(fg="grey")


class RoundedButton(tk.Canvas):
    # Adapted from https://stackoverflow.com/a/69092113
    def __init__(self, parent=None, text: str = "", font: tuple = ("Times", 30, "bold"),
                 text_padding: int = 5, radius: int = 25,
                 button_background="#ffffff", button_foreground="#000000",
                 button_hover_background="#ffffff", button_hover_foreground="#000000",
                 button_press_background="#ffffff", button_press_foreground="#000000",
                 outline_colour: str = "", outline_width: int = 1,
                 command=None, *args, **kwargs):
        super(RoundedButton, self).__init__(parent, bd=0, highlightthickness=0, *args, **kwargs)
        self.config(bg=self.master["background"])
        self.text = text
        self.font = font
        self.text_padding = text_padding
        self.radius = radius
        self.button_background = button_background
        self.button_foreground = button_foreground
        self.button_hover_background = button_hover_background
        self.button_hover_foreground = button_hover_foreground
        self.button_press_background = button_press_background
        self.button_press_foreground = button_press_foreground
        self.outline_colour = outline_colour
        self.outline_width = outline_width
        self.command = command

        self.hovering_button = False

        self.button_obj: int | None = None
        self.text_obj: int | None = None
        self.generate_button()

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
        self.text_obj = self.create_text(0, 0, text=self.text, tags="button", fill=self.button_foreground, font=self.font, justify="center")

        text_rect = self.bbox(self.text_obj)
        if int(self["width"]) < text_rect[2] - text_rect[0]:
            self["width"] = (text_rect[2] - text_rect[0]) + 10
        if int(self["height"]) < text_rect[3] - text_rect[1]:
            self["height"] = (text_rect[3] - text_rect[1]) + 10
        self.resize()

    def resize(self, _=None):
        # print("resizing")
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
