import tkinter as tk
from PIL import Image, ImageTk


root = tk.Tk()
root.title("apka")
root.geometry("375x915")
root.resizable(False, True)

canvas = tk.Canvas(root, width=375, height=915, highlightthickness=0)
canvas.pack(fill="both", expand=True)


background_img = Image.open("background.png")
background_img = ImageTk.PhotoImage(background_img)

canvas.create_image(0, 0, image=background_img, anchor="nw")

root.mainloop()
