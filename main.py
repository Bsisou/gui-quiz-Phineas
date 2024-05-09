import tkinter as tk

import pyglet  # pip install pyglet
from PIL import Image, ImageTk  # pip install pillow


class RecollectApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Recollect")
        self.root.geometry("750x563")  # Same ratio as 1000 x 750

        self.current_screen = None
        self.show_screen(Screens.Homepage(self.root, self).get())

        self.root.mainloop()

    def show_screen(self, screen):
        if self.current_screen is not None:
            self.current_screen.pack_forget()
        screen.pack(side="top", fill=tk.BOTH, expand=True)
        self.current_screen = screen


class Screens:
    class Homepage:
        def __init__(self, root: tk.Tk, app: RecollectApp):
            self.root = root
            self.app = app

            self.canvas = tk.Canvas(self.root, bg="#54b5c9", borderwidth=0, highlightthickness=0)
            self.canvas.pack(side="top", fill=tk.BOTH, expand=True)
            self.canvas.grid_columnconfigure(0, weight=1)

            self.logo_image = Image.open("assets/logo.png").convert("RGBA").resize((370, 121))  # Must be multiple of 935 x 306
            self.logo_image_tk = ImageTk.PhotoImage(self.logo_image)
            self.logo_label = tk.Label(self.canvas, image=self.logo_image_tk, bg="#54b5c9", borderwidth=0, highlightthickness=0)
            self.logo_label.grid(row=0, column=0, pady=(50, 0), sticky="")
            self.canvas.update_idletasks()  # Updates canvas coordinates size

            self.buttons = []

            self.start_button = RoundedButton(
                self.canvas, text="START", font=("Poppins Bold", 20, "bold"),
                width=350, height=75, radius=29, text_padding=0,
                button_background="#5F7BF8", button_foreground="#000000",
                button_hover_background="#4b61c4", button_hover_foreground="#000000",
                button_press_background="#2d3b77", button_press_foreground="#000000",
                outline_colour="black", outline_width=1,
                command=self.on_click
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
                command=self.on_click
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

            self.canvas.update_idletasks()  # Updates canvas coordinates size

        def get(self):
            return self.canvas

        def on_click(self):
            self.app.show_screen(Screens.Login(self.root, self.app).get())

    class Login:
        def __init__(self, root: tk.Tk, app: RecollectApp):
            self.root = root
            self.app = app

            self.frame = tk.Frame(self.root, bg="green")

            label = tk.Label(self.frame, text="LOGIN")
            label.pack()

            button = tk.Button(self.frame, text="BACK", command=self.on_click)
            button.pack()

        def get(self):
            return self.frame

        def on_click(self):
            self.app.show_screen(Screens.Homepage(self.root, self.app).get())


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
