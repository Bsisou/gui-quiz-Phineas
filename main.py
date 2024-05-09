import tkinter as tk

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

            self.start_button = tk.Button(
                self.canvas, text="START", font=("Calibri", 20, "bold"),
                width=20, height=1,
                bg="#5F7BF8", fg="#000000",
                highlightbackground="#4b61c4",
                activebackground="#2d3b77",
                command=self.on_click
            )
            self.start_button.grid(row=1, column=0, pady=(30, 0), sticky="")

            self.options_button = tk.Button(
                self.canvas, text="OPTIONS", font=("Calibri", 20, "bold"),
                width=16, height=1,
                bg="#5F7BF8", fg="#000000",
                highlightbackground="#4b61c4",
                activebackground="#2d3b77",
                command=self.on_click
            )
            self.options_button.grid(row=2, column=0, pady=(20, 0), sticky="")

            self.quit_button = tk.Button(
                self.canvas, text="QUIT", font=("Calibri", 20, "bold"),
                width=16, height=1,
                bg="#5F7BF8", fg="#000000",
                highlightbackground="#4b61c4",
                activebackground="#2d3b77",
                command=lambda: root.destroy()
            )
            self.quit_button.grid(row=3, column=0, pady=(20, 20), sticky="")

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


if __name__ == "__main__":
    root = tk.Tk()
    RecollectApp(root)
